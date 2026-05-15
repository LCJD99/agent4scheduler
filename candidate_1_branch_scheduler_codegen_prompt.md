# Scheduler Codegen Prompt

- candidate_id: `candidate_1_branch`
- provider_api: `openai`
- model: `gpt-5.4`

## System Prompt

```text
You are an offline scheduler code generation agent.
Return only valid JSON matching the provided schema.
Generate complete Python source for one scheduler candidate.
Input protocol: use the advice branch, workload signature, trace findings, and similar cases as context.
Scheduler interface protocol: Scheduler.decide(observation) -> SchedulerDecision.
The generated module must define create_scheduler(parameters=None).
create_scheduler(parameters=None) must return an instance of scheduler_sim.scheduler.base.Scheduler.
The Scheduler base class has no parameterized constructor; do not call super().__init__.
Allowed scheduler imports: scheduler_sim.scheduler.base and scheduler_sim.domain.resources.
Allowed API symbols: Scheduler, SchedulerDecision, SchedulerObservation, RunnableNode, ScheduledNodeAllocation, ResourceVector.
Import Scheduler, SchedulerDecision, SchedulerObservation, RunnableNode, and ScheduledNodeAllocation from scheduler_sim.scheduler.base.
Import only ResourceVector from scheduler_sim.domain.resources.
Never import RunnableNode from scheduler_sim.domain.resources.
Allowed observation fields: observation.timestamp_us, observation.available_resources, observation.runnable_nodes, observation.running_nodes.
Allowed available_resources fields: cpu_cores, memory_mb, gpu_vram_mb, network_mbps.
Allowed runnable node fields: node_id, node_instance_id, task_instance_id, tool_name, source, criticality, predicted_latency_us, timestamp_us, resource_demand.
Allowed running node extra fields: started_at_us, allocated_resources.
Allowed resource_demand and allocated_resources fields: cpu_cores, memory_mb, gpu_vram_mb, network_mbps.
Do not use gpu_units, gpu_memory_mb, memory, or network_bandwidth_mbps; those fields do not exist.
Use node.resource_demand for requested resources; requested_resources does not exist.
If you are not certain an API or field exists, do not use it.
The scheduler must allocate only resources that fit within remaining observation.available_resources.
The scheduler must express explicit allocated_resources for every selected node.
Do not read or write files.
Do not access network, environment variables, subprocesses, dynamic imports, eval, exec, or compile.
Do not import third-party packages.
Do not mutate the observation or runnable nodes.
Do not include markdown fences; scheduler_source must be raw Python source.
Current scheduler implementation context:
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
Reference scheduler API context:
from dataclasses import dataclass, field

from scheduler_sim.domain.resources import ResourceVector


@dataclass(slots=True)
class RunnableNode:
    node_id: str
    node_instance_id: str
    task_instance_id: str
    tool_name: str
    source: str
    criticality: str
    predicted_latency_us: int = 0
    timestamp_us: int = 0
    resource_demand: ResourceVector = field(default_factory=ResourceVector)


@dataclass(slots=True)
class RunningNode(RunnableNode):
    started_at_us: int = 0
    allocated_resources: ResourceVector = field(default_factory=ResourceVector)


@dataclass(slots=True)
class ScheduledNodeAllocation:
    node: RunnableNode
    allocated_resources: ResourceVector


@dataclass(slots=True)
class SchedulerObservation:
    runnable_nodes: list[RunnableNode]
    running_nodes: list[RunningNode] = field(default_factory=list)
    timestamp_us: int = 0
    available_resources: ResourceVector = field(default_factory=ResourceVector)


@dataclass(slots=True)
class SchedulerDecision:
    allocations: list[ScheduledNodeAllocation]
    timestamp_us: int = 0

    @property
    def selected_nodes(self) -> list[RunnableNode]:
        return [allocation.node for allocation in self.allocations]


class Scheduler:
    def decide(self, observation: SchedulerObservation) -> SchedulerDecision:
        raise NotImplementedError
```

## User Payload

```json
{
  "advice_branch": {
    "branch_id": "branch",
    "parameters": {}
  },
  "candidate_id": "candidate_1_branch",
  "output_contract": {
    "constraints_satisfied": "List of constraints the source satisfies.",
    "rationale": "Short explanation of the scheduling heuristic encoded in the source.",
    "scheduler_source": "Complete Python source for a scheduler candidate."
  },
  "similar_cases": [],
  "trace_findings": [],
  "workload_signature": {}
}
```

## Current Scheduler Source

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

## Reference Scheduler Base Source

```python
from dataclasses import dataclass, field

from scheduler_sim.domain.resources import ResourceVector


@dataclass(slots=True)
class RunnableNode:
    node_id: str
    node_instance_id: str
    task_instance_id: str
    tool_name: str
    source: str
    criticality: str
    predicted_latency_us: int = 0
    timestamp_us: int = 0
    resource_demand: ResourceVector = field(default_factory=ResourceVector)


@dataclass(slots=True)
class RunningNode(RunnableNode):
    started_at_us: int = 0
    allocated_resources: ResourceVector = field(default_factory=ResourceVector)


@dataclass(slots=True)
class ScheduledNodeAllocation:
    node: RunnableNode
    allocated_resources: ResourceVector


@dataclass(slots=True)
class SchedulerObservation:
    runnable_nodes: list[RunnableNode]
    running_nodes: list[RunningNode] = field(default_factory=list)
    timestamp_us: int = 0
    available_resources: ResourceVector = field(default_factory=ResourceVector)


@dataclass(slots=True)
class SchedulerDecision:
    allocations: list[ScheduledNodeAllocation]
    timestamp_us: int = 0

    @property
    def selected_nodes(self) -> list[RunnableNode]:
        return [allocation.node for allocation in self.allocations]


class Scheduler:
    def decide(self, observation: SchedulerObservation) -> SchedulerDecision:
        raise NotImplementedError
```

## Output Schema

```json
{
  "additionalProperties": false,
  "properties": {
    "constraints_satisfied": {
      "items": {
        "type": "string"
      },
      "type": "array"
    },
    "rationale": {
      "type": "string"
    },
    "scheduler_source": {
      "type": "string"
    }
  },
  "required": [
    "scheduler_source",
    "rationale",
    "constraints_satisfied"
  ],
  "type": "object"
}
```
