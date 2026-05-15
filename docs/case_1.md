# Case 1: Navigation-Focused Scheduler Evolution

## Workload

- Baseline trace run: `case/baseline/20260513-000345`
- Scenario: `configs/scenarios/home_eqa_scenario_001.yaml`
- Scene complexity: `large`
- System capacity:
  - CPU: `4.0`
  - Memory: `4096 MB`
  - GPU VRAM: `2048 MB`
  - Network: `100 Mbps`
- Critical tasks:
  - `localization_node`: `50 Hz`, `period_us=20000`
  - `pointcloud_to_laserscan_node`: `20 Hz`, `period_us=50000`
  - `navigation_algo_node`: `35 Hz`, `period_us=28571`
- Agent task:
  - one `agent-caption-pipeline`
  - arrival time: `18000 us`
  - DAG: `image_captioning -> text_translation -> text_to_speech`

Baseline metrics from `case/baseline/20260513-000345/trace_summary.json`:

- aggregate critical completion rate: `76.19%`
- agent average completion latency: `2,986,000 us`
- critical per-task completion rates:
  - `localization_node`: `100.00%`
  - `pointcloud_to_laserscan_node`: `100.00%`
  - `navigation_algo_node`: `28.57%`

This means the failure is concentrated on `navigation_algo_node`. The other two critical tasks are already stable.

## Original Scheduler

Source: `src/scheduler_sim/scheduler/heuristic.py`

```python
from scheduler_sim.domain.resources import ResourceVector
from scheduler_sim.scheduler.base import (
    RunnableNode,
    ScheduledNodeAllocation,
    Scheduler,
    SchedulerDecision,
    SchedulerObservation,
)


class HeuristicScheduler(Scheduler):
    def decide(self, observation: SchedulerObservation) -> SchedulerDecision:
        remaining_capacity = observation.available_resources
        allocations: list[ScheduledNodeAllocation] = []
        for node in sorted(observation.runnable_nodes, key=self._priority_key):
            if node.resource_demand.fits_within(remaining_capacity):
                allocations.append(
                    ScheduledNodeAllocation(
                        node=node,
                        allocated_resources=node.resource_demand,
                    )
                )
                remaining_capacity = remaining_capacity - node.resource_demand
        return SchedulerDecision(
            allocations=allocations,
            timestamp_us=observation.timestamp_us,
        )

    def _priority_key(self, node: RunnableNode) -> tuple[int, str]:
        criticality_rank = {
            "high": 0,
            "medium": 1,
            "low": 2,
        }
        return (criticality_rank.get(node.criticality, 3), node.node_instance_id)
```

## Evolution Idea

The baseline heuristic always allocates each runnable node exactly its `resource_demand`, and only uses static criticality ordering.

For this workload, that is not enough for `navigation_algo_node`.

Observed bottleneck:

- `navigation_algo_node` has the tightest effective margin under runtime pressure.
- It competes with the agent workload after `18000 us`.
- Under the baseline scheduler, it only receives its nominal allocation:
  - `1.0 CPU`
  - `256 MB`

Targeted evolution idea:

1. Move `navigation_algo_node` to the front of the runnable-node ordering.
2. Over-allocate CPU for `navigation_algo_node` when capacity exists.
3. Keep the rest of the scheduler simple and deterministic.

The key assumption is that `navigation_algo_node` is the dominant failure point, and spending more CPU on it is more valuable than preserving the exact baseline balance.

## New Scheduler

Source: `case/nav_focus_experiment/nav_focus_b.py`

```python
from scheduler_sim.domain.resources import ResourceVector
from scheduler_sim.scheduler.base import RunnableNode, ScheduledNodeAllocation, Scheduler, SchedulerDecision, SchedulerObservation

class NavFocusB(Scheduler):
    def decide(self, observation: SchedulerObservation) -> SchedulerDecision:
        remaining = observation.available_resources
        allocations = []
        nodes = sorted(observation.runnable_nodes, key=lambda n: (0 if n.node_id=='navigation_algo_node' else 1 if n.criticality=='high' else 2 if n.criticality=='medium' else 3, n.node_instance_id))
        for node in nodes:
            alloc = node.resource_demand
            if node.node_id == 'navigation_algo_node':
                alloc = ResourceVector(cpu_cores=min(1.5, remaining.cpu_cores), memory_mb=max(node.resource_demand.memory_mb, 320), gpu_vram_mb=node.resource_demand.gpu_vram_mb, network_mbps=node.resource_demand.network_mbps)
            if alloc.fits_within(remaining):
                allocations.append(ScheduledNodeAllocation(node=node, allocated_resources=alloc))
                remaining = remaining - alloc
        return SchedulerDecision(allocations=allocations, timestamp_us=observation.timestamp_us)

def create_scheduler(parameters=None):
    return NavFocusB()
```

## Why This Scheduler Works Better

Compared with the baseline:

- baseline gives `navigation_algo_node` only `1.0 CPU`
- this evolved scheduler can give it up to `1.5 CPU`

That reduces its profiled runtime enough to survive the resource-pressure multiplier during agent overlap. The scheduler does not need to change the task graph or runtime model. It only changes:

- ordering
- allocated resources for the navigation node

## Metrics

Baseline metrics:

- source: `case/baseline/20260513-000345/trace_summary.json`

New scheduler metrics:

- source: `case/nav_focus_experiment/run_b/20260513-002020/trace_summary.json`

| Scheduler | Critical completion rate | localization | navigation | pointcloud | Agent latency (us) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Baseline heuristic | 76.19% | 100.00% | 28.57% | 100.00% | 2,986,000 |
| `NavFocusB` | 100.00% | 100.00% | 100.00% | 100.00% | 3,059,000 |

## Result

This targeted evolution is effective on the current workload.

- `navigation_algo_node` completion rate improves from `28.57%` to `100.00%`
- aggregate critical completion rate improves from `76.19%` to `100.00%`
- `localization_node` and `pointcloud_to_laserscan_node` stay at `100.00%`
- agent latency increases from `2,986,000 us` to `3,059,000 us`

This is a clear tradeoff:

- critical-task performance becomes perfect on this case
- the cost is a small increase in agent completion latency

For this workload, that tradeoff is favorable.
