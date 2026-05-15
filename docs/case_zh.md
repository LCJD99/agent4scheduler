# Case 1：面向 `navigation_algo_node` 的定向调度器进化

## Workload

- baseline trace：`case/baseline/20260513-000345`
- scenario：`configs/scenarios/home_eqa_scenario_001.yaml`
- 场景复杂度：`large`
- 系统资源：
  - CPU：`4.0`
  - 内存：`4096 MB`
  - GPU VRAM：`2048 MB`
  - 网络：`100 Mbps`
- 关键任务：
  - `localization_node`：`50 Hz`，`period_us=20000`
  - `pointcloud_to_laserscan_node`：`20 Hz`，`period_us=50000`
  - `navigation_algo_node`：`35 Hz`，`period_us=28571`
- Agent 任务：
  - 一个 `agent-caption-pipeline`
  - 到达时间：`18000 us`
  - DAG：`image_captioning -> text_translation -> text_to_speech`

baseline 指标来自 `case/baseline/20260513-000345/trace_summary.json`：

- 关键任务整体完成率：`76.19%`
- Agent 平均完成时延：`2,986,000 us`
- 关键任务分项完成率：
  - `localization_node`：`100.00%`
  - `pointcloud_to_laserscan_node`：`100.00%`
  - `navigation_algo_node`：`28.57%`

可以看到，瓶颈几乎完全落在 `navigation_algo_node` 上，另外两个关键任务在当前 workload 下已经稳定。

## 原本 Scheduler

来源：`src/scheduler_sim/scheduler/heuristic.py`

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

这个启发式的特点是：

- 先按 `criticality` 和 `node_instance_id` 排序
- 只要任务的 `resource_demand` 能放下，就按需求量原样分配
- 不会针对某个关键节点做额外资源倾斜

## 进化思路

这次进化不是泛化地“微调所有关键任务”，而是只针对 `navigation_algo_node` 的失败模式做定向优化。

核心观察：

1. baseline 下真正失效的是 `navigation_algo_node`
2. 它的周期最紧，只有 `28571 us`
3. Agent 任务在 `18000 us` 到达后，会和关键任务形成资源竞争
4. baseline scheduler 只给它分配名义资源：
   - `1.0 CPU`
   - `256 MB`

因此进化思路是：

1. 把 `navigation_algo_node` 提前到最高调度优先级
2. 在资源允许时，给它比 `resource_demand` 更激进的 CPU 分配
3. 其余节点尽量保持简单、确定性的调度逻辑

换句话说，这次进化的目标不是“整体更平均”，而是明确地牺牲一小部分 Agent 时延，去换取 `navigation_algo_node` 的 deadline 满足率。

## 新 Scheduler

来源：`case/nav_focus_experiment/nav_focus_b.py`

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

## 为什么这个 Scheduler 更有效

相对 baseline，这个版本做了两件关键事：

1. 调度顺序上，把 `navigation_algo_node` 放到最前面
2. 资源分配上，对 `navigation_algo_node` 超配 CPU

baseline：

- `navigation_algo_node` 只拿 `1.0 CPU`

新 scheduler：

- `navigation_algo_node` 最多拿到 `1.5 CPU`
- 内存也至少拉到 `320 MB`

这会直接缩短它的 profile latency，使其在 runtime pressure 存在时仍然能守住 `28571 us` 周期。

这次改动没有碰：

- task DAG
- runtime model
- profiling 估计器

只修改了：

- 节点排序
- `navigation_algo_node` 的分配资源

## Metrics 表

baseline 指标来源：

- `case/baseline/20260513-000345/trace_summary.json`

新 scheduler 指标来源：

- `case/nav_focus_experiment/run_b/20260513-002020/trace_summary.json`

| Scheduler | 关键任务整体完成率 | localization | navigation | pointcloud | Agent 时延（us） |
| --- | ---: | ---: | ---: | ---: | ---: |
| 原始 heuristic | 76.19% | 100.00% | 28.57% | 100.00% | 2,986,000 |
| `NavFocusB` | 100.00% | 100.00% | 100.00% | 100.00% | 3,059,000 |

## 结果分析

这次定向进化是有效的。

- `navigation_algo_node` 完成率从 `28.57%` 提升到 `100.00%`
- 关键任务整体完成率从 `76.19%` 提升到 `100.00%`
- `localization_node` 和 `pointcloud_to_laserscan_node` 保持 `100.00%`
- Agent 时延从 `2,986,000 us` 增加到 `3,059,000 us`

因此这是一个非常明确的 tradeoff：

- 好处：
  - 所有关键任务都满足 deadline
- 代价：
  - Agent 完成时延上升了约 `73,000 us`

对于这个 workload，这个 tradeoff 是合理的，因为关键任务 deadline 满足率的提升远大于 Agent 时延的小幅变差。
