# Offline Scheduler Evolution Case

## Case Inputs

- Baseline trace run: `case/baseline/20260513-000345`
- Offline evolve run: `case/replays/20260513-000347`
- Scenario: `configs/scenarios/home_eqa_scenario_001.yaml`
- Scene complexity: `large`
- System capacity:
  - CPU: `4.0`
  - Memory: `4096 MB`
  - GPU VRAM: `2048 MB`
  - Network: `100 Mbps`
- Critical workload:
  - `localization_node`: `50 Hz` (`period_us=20000`)
  - `pointcloud_to_laserscan_node`: `20 Hz` (`period_us=50000`)
  - `navigation_algo_node`: `35 Hz` (`period_us=28571`)
- Agent workload:
  - one `agent-caption-pipeline` request
  - arrival time: `18000 us`
  - DAG: `image_captioning -> text_translation -> text_to_speech`

## Workload Summary

The baseline trace shows a mixed critical/agent contention case.

- Aggregate critical completion rate: `76.19%`
- Agent average completion latency: `2,986,000 us`
- Critical per-task completion rates:
  - `localization_node`: `100.00%`
  - `pointcloud_to_laserscan_node`: `100.00%`
  - `navigation_algo_node`: `28.57%`

The bottleneck is concentrated on `navigation_algo_node`. The other two critical nodes remain stable under the current workload.

## Offline Diagnosis From Trace

The offline analyzer diagnosed the case as a critical deadline miss problem centered on `navigation_algo_node`.

Diagnosis summary:

- defect type: `Critical Deadline Miss`
- severity: `High`
- affected nodes:
  - `critical-navigation_algo_node-00001--navigation_algo_node`
  - `critical-navigation_algo_node-00002--navigation_algo_node`
  - `critical-navigation_algo_node-00003--navigation_algo_node`
  - `critical-navigation_algo_node-00004--navigation_algo_node`
  - `critical-navigation_algo_node-00005--navigation_algo_node`
- root cause hypothesis:
  - `navigation_algo_node` keeps missing deadlines under high CPU utilization and resource contention
  - the low-criticality `agent-caption-pipeline` overlaps with the critical windows and increases contention

Trace evidence referenced by the analyzer:

- trace summary reports `100` misses on `navigation_algo_node`
- selected missed-deadline windows are centered around:
  - `28571 us`
  - `57571 us`
  - `86571 us`
  - `114571 us`
  - `143571 us`
- max CPU utilization in those windows reaches `0.8875` to `0.9475`
- the agent node `image_captioning` is runnable/selected in the early missed-deadline windows

## Three Suggested Modifications

### 1. `branch_critical_headroom`

- change:
  - reserve CPU headroom for critical releases before admitting low-criticality agent nodes
- expected impact:
  - reduce critical deadline misses, possibly increasing agent makespan
- risk:
  - under-utilized CPU when critical releases are sparse
- parameters:
  - `agent_cpu_reservation_cores = 1.0`
  - `agent_starvation_boost_after_us = 0`

### 2. `branch_agent_starvation_boost`

- change:
  - boost agent nodes after bounded waiting time while keeping critical fit checks
- expected impact:
  - improve agent completion latency without removing critical-first scheduling
- risk:
  - too low a boost threshold can increase critical contention
- parameters:
  - `agent_cpu_reservation_cores = 0.5`
  - `agent_starvation_boost_after_us = 500000`

### 3. `branch_navigation_guardrail`

- change:
  - preserve capacity for high-criticality navigation releases and limit low-criticality admission when navigation backlog is present
- expected impact:
  - improve navigation critical completion rate while allowing controlled degradation of agent latency
- risk:
  - reduced agent throughput during sustained critical bursts
- parameters:
  - `agent_cpu_reservation_cores = 0.75`
  - `agent_starvation_boost_after_us = 1000000`
  - `high_criticality_only_when_backlogged = true`

## Current Scheduler

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

## Evolved Scheduler 1

Source: `case/replays/20260513-000347/candidate_1_branch_critical_headroom/scheduler_candidate.py`

```python
from scheduler_sim.domain.resources import ResourceVector
from scheduler_sim.scheduler.base import (
    RunnableNode,
    ScheduledNodeAllocation,
    Scheduler,
    SchedulerDecision,
    SchedulerObservation,
)


class CriticalHeadroomScheduler(Scheduler):
    def decide(self, observation: SchedulerObservation) -> SchedulerDecision:
        # Separate nodes by criticality
        critical_nodes = []
        agent_nodes = []
        for node in observation.runnable_nodes:
            if node.criticality == "high":
                critical_nodes.append(node)
            else:
                agent_nodes.append(node)
        
        # Sort critical nodes by priority (criticality rank, then instance id)
        critical_nodes.sort(key=self._priority_key)
        # Sort agent nodes by priority (same key, but they will be considered after critical)
        agent_nodes.sort(key=self._priority_key)
        
        remaining = observation.available_resources
        allocations = []
        
        # First pass: allocate all critical nodes that fit
        for node in critical_nodes:
            if node.resource_demand.fits_within(remaining):
                allocations.append(
                    ScheduledNodeAllocation(
                        node=node,
                        allocated_resources=node.resource_demand,
                    )
                )
                remaining = remaining - node.resource_demand
        
        # Second pass: allocate agent nodes only if there is enough headroom
        # Use reservation logic: reserve 1 CPU core for critical tasks before admitting agent nodes
        # Check if after reserving 1 CPU core, there is enough capacity for the agent node
        for node in agent_nodes:
            # Reserve headroom: ensure at least 1.0 CPU core remains available for future critical tasks
            reserved_cpu = min(1.0, remaining.cpu_cores)
            # Create a resource vector that reflects the remaining capacity after reservation
            headroom = ResourceVector(
                cpu_cores=remaining.cpu_cores - reserved_cpu,
                memory_mb=remaining.memory_mb,
                gpu_vram_mb=remaining.gpu_vram_mb,
                network_mbps=remaining.network_mbps,
            )
            # Only allocate if the node fits within the headroom (i.e., after reservation)
            if node.resource_demand.fits_within(headroom):
                allocations.append(
                    ScheduledNodeAllocation(
                        node=node,
                        allocated_resources=node.resource_demand,
                    )
                )
                remaining = remaining - node.resource_demand
        
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


def create_scheduler(parameters=None):
    return CriticalHeadroomScheduler()
```

## Evolved Scheduler 2

Source: `case/replays/20260513-000347/candidate_2_branch_agent_starvation_boost/scheduler_candidate.py`

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
    def __init__(self, parameters=None):
        # Extract parameters if provided, otherwise use defaults
        if parameters is None:
            parameters = {}
        self.agent_cpu_reservation_cores = parameters.get("agent_cpu_reservation_cores", 0.5)
        self.agent_starvation_boost_after_us = parameters.get("agent_starvation_boost_after_us", 500000)
    
    def decide(self, observation: SchedulerObservation) -> SchedulerDecision:
        remaining_capacity = observation.available_resources
        allocations: list[ScheduledNodeAllocation] = []
        
        # Separate runnable nodes into critical and agent categories
        critical_nodes = []
        agent_nodes = []
        for node in observation.runnable_nodes:
            if node.source.startswith("critical-"):
                critical_nodes.append(node)
            else:
                agent_nodes.append(node)
        
        # Sort critical nodes by their priority (criticality, then instance ID)
        critical_nodes.sort(key=self._critical_priority_key)
        
        # Sort agent nodes by waiting time (longest waiting first), then by instance ID
        # For now, we use timestamp_us as a proxy for arrival time; lower timestamp means longer waiting
        agent_nodes.sort(key=lambda node: (-node.timestamp_us, node.node_instance_id))
        
        # First pass: schedule all critical nodes that fit
        for node in critical_nodes:
            if node.resource_demand.fits_within(remaining_capacity):
                allocations.append(
                    ScheduledNodeAllocation(
                        node=node,
                        allocated_resources=node.resource_demand,
                    )
                )
                remaining_capacity = remaining_capacity - node.resource_demand
        
        # Compute remaining capacity after critical nodes
        # For agent scheduling, we may need to reserve some CPU for future critical releases
        # But we don't have future knowledge, so we use a reservation heuristic based on parameters
        # However, the advice branch suggests boosting agent nodes after a waiting time,
        # not necessarily reserving capacity. We'll implement a starvation-boost mechanism:
        # If an agent node has been waiting longer than the threshold, we prioritize it
        # among other agent nodes, but still after critical nodes.
        
        # We'll sort agent nodes by whether they have waited longer than threshold,
        # then by waiting time descending.
        def agent_sort_key(node):
            # Wait time can be approximated by current time minus node.timestamp_us
            # But we don't have the creation time; node.timestamp_us is when it became runnable?
            # We'll assume node.timestamp_us is the time it became runnable.
            wait_time_us = observation.timestamp_us - node.timestamp_us
            # If wait_time_us > threshold, give it a boost (lower sort key)
            boosted = 0 if wait_time_us >= self.agent_starvation_boost_after_us else 1
            # Among boosted or non-boosted, sort by longest waiting first (descending wait_time_us)
            return (boosted, -wait_time_us, node.node_instance_id)
        
        agent_nodes.sort(key=agent_sort_key)
        
        # Second pass: schedule agent nodes that fit
        for node in agent_nodes:
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
    
    def _critical_priority_key(self, node: RunnableNode) -> tuple[int, str]:
        # Critical nodes are scheduled first; among them, higher criticality (high > medium > low)
        criticality_rank = {
            "high": 0,
            "medium": 1,
            "low": 2,
        }
        return (criticality_rank.get(node.criticality, 3), node.node_instance_id)

def create_scheduler(parameters=None):
    return HeuristicScheduler(parameters=parameters)
```

## Evolved Scheduler 3

Source: `case/replays/20260513-000347/candidate_3_branch_navigation_guardrail/scheduler_candidate.py`

```python
from scheduler_sim.domain.resources import ResourceVector
from scheduler_sim.scheduler.base import (
    RunnableNode,
    ScheduledNodeAllocation,
    Scheduler,
    SchedulerDecision,
    SchedulerObservation,
)


class NavigationGuardrailScheduler(Scheduler):
    def __init__(self, parameters=None):
        self.agent_cpu_reservation_cores = 0.75
        self.agent_starvation_boost_after_us = 1000000
        self.high_criticality_only_when_backlogged = True
        if parameters:
            self.agent_cpu_reservation_cores = parameters.get('agent_cpu_reservation_cores', self.agent_cpu_reservation_cores)
            self.agent_starvation_boost_after_us = parameters.get('agent_starvation_boost_after_us', self.agent_starvation_boost_after_us)
            self.high_criticality_only_when_backlogged = parameters.get('high_criticality_only_when_backlogged', self.high_criticality_only_when_backlogged)

    def decide(self, observation: SchedulerObservation) -> SchedulerDecision:
        runnable_nodes = observation.runnable_nodes
        running_nodes = observation.running_nodes
        remaining_capacity = observation.available_resources
        allocations = []

        # Classify nodes
        critical_nodes = []
        agent_nodes = []
        for node in runnable_nodes:
            if node.criticality == 'high' and 'navigation_algo_node' in node.tool_name:
                critical_nodes.append(node)
            else:
                agent_nodes.append(node)

        # Determine if backlog condition exists
        backlog_detected = len(critical_nodes) > 0

        # Sort critical nodes by instance id for deterministic ordering
        critical_nodes.sort(key=lambda x: x.node_instance_id)

        # Allocate critical nodes first (always prioritize)
        for node in critical_nodes:
            if node.resource_demand.fits_within(remaining_capacity):
                allocations.append(ScheduledNodeAllocation(
                    node=node,
                    allocated_resources=node.resource_demand,
                ))
                remaining_capacity = remaining_capacity - node.resource_demand

        # Apply guardrail: reserve CPU capacity for future critical releases when backlog is detected
        if backlog_detected and self.high_criticality_only_when_backlogged:
            # Reserve agent CPU reservation cores
            agent_reservation = ResourceVector(cpu_cores=self.agent_cpu_reservation_cores)
            if remaining_capacity.cpu_cores < self.agent_cpu_reservation_cores:
                # Not enough capacity to reserve, skip agent nodes
                return SchedulerDecision(
                    allocations=allocations,
                    timestamp_us=observation.timestamp_us,
                )
            # Reduce remaining capacity by reservation
            remaining_capacity = remaining_capacity - agent_reservation

        # Sort agent nodes by starvation boost time (older first)
        agent_nodes.sort(key=lambda x: -x.timestamp_us)

        # Allocate agent nodes if they fit
        for node in agent_nodes:
            if node.resource_demand.fits_within(remaining_capacity):
                allocations.append(ScheduledNodeAllocation(
                    node=node,
                    allocated_resources=node.resource_demand,
                ))
                remaining_capacity = remaining_capacity - node.resource_demand

        return SchedulerDecision(
            allocations=allocations,
            timestamp_us=observation.timestamp_us,
        )


def create_scheduler(parameters=None):
    return NavigationGuardrailScheduler(parameters=parameters)
```

## Metrics Comparison

Metric definition:

- critical completion rate:
  - `(sum of met_deadline_count across all critical releases) / (sum of total_release_count across all critical releases)`
- agent latency:
  - `avg_total_completion_time_us`

| Scheduler | Critical completion rate | Agent latency (us) |
| --- | ---: | ---: |
| Current heuristic | 76.19% | 2,986,000 |
| Evolved 1: `candidate_1_branch_critical_headroom` | 76.19% | 2,987,000 |
| Evolved 2: `candidate_2_branch_agent_starvation_boost` | 76.19% | 2,986,000 |
| Evolved 3: `candidate_3_branch_navigation_guardrail` | 76.19% | 2,986,000 |

Additional critical per-task completion rates:

| Scheduler | `localization_node` | `pointcloud_to_laserscan_node` | `navigation_algo_node` |
| --- | ---: | ---: | ---: |
| Current heuristic | 100.00% | 100.00% | 28.57% |
| Evolved 1 | 100.00% | 100.00% | 28.57% |
| Evolved 2 | 100.00% | 100.00% | 28.57% |
| Evolved 3 | 100.00% | 100.00% | 28.57% |

## Result

This case produced three concrete scheduler variants, but none of them improved the baseline metrics on this workload.

- The failure mode remained concentrated on `navigation_algo_node`.
- The baseline heuristic and all three evolved schedulers produced the same aggregate critical completion rate.
- Agent latency also remained effectively unchanged.
- The selected candidate in this run was `candidate_2_branch_agent_starvation_boost`, but it was selected under a tie rather than because it improved the metrics.

This case is still useful because it shows:

- the workload and trace are suitable for offline diagnosis
- the analyzer can isolate the dominant failing critical node
- the evolution loop can generate multiple runnable scheduler implementations
- the replay/evaluation pipeline can prove when proposed heuristic changes do not actually improve the target metrics
