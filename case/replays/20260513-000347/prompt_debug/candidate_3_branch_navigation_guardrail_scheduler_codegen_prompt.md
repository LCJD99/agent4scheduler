# Scheduler Codegen Prompt

- candidate_id: `candidate_3_branch_navigation_guardrail`
- provider_api: `openai_chat_completions`
- model: `mimo-v2.5-pro`

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
    "branch_id": "branch_navigation_guardrail",
    "expected_metric_impact": "Improve navigation critical completion rate while allowing controlled degradation of agent latency.",
    "key_trace_refs": [
      {
        "file": "trace_summary.json"
      },
      {
        "file": "selected_trace_windows",
        "windows": [
          {
            "agent_runnable_nodes": [
              "agent-caption-pipeline-00018000-001--image_captioning"
            ],
            "agent_selected_nodes": [
              "agent-caption-pipeline-00018000-001--image_captioning"
            ],
            "center_timestamp_us": 28571,
            "critical_runnable_nodes": [
              "critical-localization_node-00001--localization_node",
              "critical-localization_node-00002--localization_node",
              "critical-localization_node-00003--localization_node",
              "critical-localization_node-00004--localization_node",
              "critical-navigation_algo_node-00001--navigation_algo_node",
              "critical-navigation_algo_node-00002--navigation_algo_node",
              "critical-navigation_algo_node-00003--navigation_algo_node",
              "critical-pointcloud_to_laserscan_node-00001--pointcloud_to_laserscan_node",
              "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node"
            ],
            "critical_selected_nodes": [
              "critical-localization_node-00001--localization_node",
              "critical-localization_node-00002--localization_node",
              "critical-localization_node-00003--localization_node",
              "critical-localization_node-00004--localization_node",
              "critical-navigation_algo_node-00001--navigation_algo_node",
              "critical-navigation_algo_node-00002--navigation_algo_node",
              "critical-navigation_algo_node-00003--navigation_algo_node",
              "critical-pointcloud_to_laserscan_node-00001--pointcloud_to_laserscan_node",
              "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node"
            ],
            "end_timestamp_us": 78571,
            "max_cpu_utilization": 0.8875,
            "max_gpu_utilization": 0.375,
            "reason": "critical_deadline_miss",
            "running_agent_nodes": [
              "agent-caption-pipeline-00018000-001--image_captioning"
            ],
            "start_timestamp_us": 0,
            "target_node_id": "navigation_algo_node",
            "target_node_instance_id": "critical-navigation_algo_node-00001--navigation_algo_node"
          },
          {
            "agent_runnable_nodes": [
              "agent-caption-pipeline-00018000-001--image_captioning"
            ],
            "agent_selected_nodes": [
              "agent-caption-pipeline-00018000-001--image_captioning"
            ],
            "center_timestamp_us": 57571,
            "critical_runnable_nodes": [
              "critical-localization_node-00002--localization_node",
              "critical-localization_node-00003--localization_node",
              "critical-localization_node-00004--localization_node",
              "critical-localization_node-00005--localization_node",
              "critical-localization_node-00006--localization_node",
              "critical-navigation_algo_node-00002--navigation_algo_node",
              "critical-navigation_algo_node-00003--navigation_algo_node",
              "critical-navigation_algo_node-00004--navigation_algo_node",
              "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node",
              "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node"
            ],
            "critical_selected_nodes": [
              "critical-localization_node-00002--localization_node",
              "critical-localization_node-00003--localization_node",
              "critical-localization_node-00004--localization_node",
              "critical-localization_node-00005--localization_node",
              "critical-localization_node-00006--localization_node",
              "critical-navigation_algo_node-00002--navigation_algo_node",
              "critical-navigation_algo_node-00003--navigation_algo_node",
              "critical-navigation_algo_node-00004--navigation_algo_node",
              "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node",
              "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node"
            ],
            "end_timestamp_us": 107571,
            "max_cpu_utilization": 0.8875,
            "max_gpu_utilization": 0.375,
            "reason": "critical_deadline_miss",
            "running_agent_nodes": [
              "agent-caption-pipeline-00018000-001--image_captioning"
            ],
            "start_timestamp_us": 7571,
            "target_node_id": "navigation_algo_node",
            "target_node_instance_id": "critical-navigation_algo_node-00002--navigation_algo_node"
          },
          {
            "agent_runnable_nodes": [],
            "agent_selected_nodes": [],
            "center_timestamp_us": 86571,
            "critical_runnable_nodes": [
              "critical-localization_node-00003--localization_node",
              "critical-localization_node-00004--localization_node",
              "critical-localization_node-00005--localization_node",
              "critical-localization_node-00006--localization_node",
              "critical-localization_node-00007--localization_node",
              "critical-navigation_algo_node-00003--navigation_algo_node",
              "critical-navigation_algo_node-00004--navigation_algo_node",
              "critical-navigation_algo_node-00005--navigation_algo_node",
              "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node",
              "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node"
            ],
            "critical_selected_nodes": [
              "critical-localization_node-00003--localization_node",
              "critical-localization_node-00004--localization_node",
              "critical-localization_node-00005--localization_node",
              "critical-localization_node-00006--localization_node",
              "critical-localization_node-00007--localization_node",
              "critical-navigation_algo_node-00003--navigation_algo_node",
              "critical-navigation_algo_node-00004--navigation_algo_node",
              "critical-navigation_algo_node-00005--navigation_algo_node",
              "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node",
              "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node"
            ],
            "end_timestamp_us": 136571,
            "max_cpu_utilization": 0.9475,
            "max_gpu_utilization": 0.375,
            "reason": "critical_deadline_miss",
            "running_agent_nodes": [
              "agent-caption-pipeline-00018000-001--image_captioning"
            ],
            "start_timestamp_us": 36571,
            "target_node_id": "navigation_algo_node",
            "target_node_instance_id": "critical-navigation_algo_node-00003--navigation_algo_node"
          },
          {
            "agent_runnable_nodes": [],
            "agent_selected_nodes": [],
            "center_timestamp_us": 114571,
            "critical_runnable_nodes": [
              "critical-localization_node-00005--localization_node",
              "critical-localization_node-00006--localization_node",
              "critical-localization_node-00007--localization_node",
              "critical-localization_node-00008--localization_node",
              "critical-localization_node-00009--localization_node",
              "critical-navigation_algo_node-00004--navigation_algo_node",
              "critical-navigation_algo_node-00005--navigation_algo_node",
              "critical-navigation_algo_node-00006--navigation_algo_node",
              "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node",
              "critical-pointcloud_to_laserscan_node-00004--pointcloud_to_laserscan_node"
            ],
            "critical_selected_nodes": [
              "critical-localization_node-00005--localization_node",
              "critical-localization_node-00006--localization_node",
              "critical-localization_node-00007--localization_node",
              "critical-localization_node-00008--localization_node",
              "critical-localization_node-00009--localization_node",
              "critical-navigation_algo_node-00004--navigation_algo_node",
              "critical-navigation_algo_node-00005--navigation_algo_node",
              "critical-navigation_algo_node-00006--navigation_algo_node",
              "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node",
              "critical-pointcloud_to_laserscan_node-00004--pointcloud_to_laserscan_node"
            ],
            "end_timestamp_us": 164571,
            "max_cpu_utilization": 0.9475,
            "max_gpu_utilization": 0.375,
            "reason": "critical_deadline_miss",
            "running_agent_nodes": [
              "agent-caption-pipeline-00018000-001--image_captioning"
            ],
            "start_timestamp_us": 64571,
            "target_node_id": "navigation_algo_node",
            "target_node_instance_id": "critical-navigation_algo_node-00004--navigation_algo_node"
          },
          {
            "agent_runnable_nodes": [],
            "agent_selected_nodes": [],
            "center_timestamp_us": 143571,
            "critical_runnable_nodes": [
              "critical-localization_node-00006--localization_node",
              "critical-localization_node-00007--localization_node",
              "critical-localization_node-00008--localization_node",
              "critical-localization_node-00009--localization_node",
              "critical-localization_node-00010--localization_node",
              "critical-navigation_algo_node-00005--navigation_algo_node",
              "critical-navigation_algo_node-00006--navigation_algo_node",
              "critical-navigation_algo_node-00007--navigation_algo_node",
              "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node",
              "critical-pointcloud_to_laserscan_node-00004--pointcloud_to_laserscan_node"
            ],
            "critical_selected_nodes": [
              "critical-localization_node-00006--localization_node",
              "critical-localization_node-00007--localization_node",
              "critical-localization_node-00008--localization_node",
              "critical-localization_node-00009--localization_node",
              "critical-localization_node-00010--localization_node",
              "critical-navigation_algo_node-00005--navigation_algo_node",
              "critical-navigation_algo_node-00006--navigation_algo_node",
              "critical-navigation_algo_node-00007--navigation_algo_node",
              "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node",
              "critical-pointcloud_to_laserscan_node-00004--pointcloud_to_laserscan_node"
            ],
            "end_timestamp_us": 193571,
            "max_cpu_utilization": 0.9475,
            "max_gpu_utilization": 0.375,
            "reason": "critical_deadline_miss",
            "running_agent_nodes": [
              "agent-caption-pipeline-00018000-001--image_captioning"
            ],
            "start_timestamp_us": 93571,
            "target_node_id": "navigation_algo_node",
            "target_node_instance_id": "critical-navigation_algo_node-00005--navigation_algo_node"
          }
        ]
      }
    ],
    "parameters": {
      "agent_cpu_reservation_cores": 0.75,
      "agent_starvation_boost_after_us": 1000000,
      "high_criticality_only_when_backlogged": true
    },
    "proposed_heuristic_change": "Preserve capacity for high-criticality navigation releases and limit low-criticality admission when navigation backlog is present.",
    "regression_risk": "May reduce agent throughput during sustained critical bursts and under-utilize spare capacity if backlog detection is too conservative.",
    "scheduler_defect_summary": "Critical Deadline Miss: The navigation_algo_node is consistently missing deadlines due to high CPU utilization (up to 94.75%) and contention for resources, likely caused by concurrent execution of the non-critical agent-caption-pipeline task which is also running on the same system.",
    "similar_case_count": 4,
    "workload_characterization": "large workload with critical deadline miss rate 0.238"
  },
  "candidate_id": "candidate_3_branch_navigation_guardrail",
  "output_contract": {
    "constraints_satisfied": "List of constraints the source satisfies.",
    "rationale": "Short explanation of the scheduling heuristic encoded in the source.",
    "scheduler_source": "Complete Python source for a scheduler candidate."
  },
  "similar_cases": [
    {
      "advice": [
        {
          "branch_id": "branch_critical_headroom",
          "expected_metric_impact": "Reduce critical deadline misses with possible agent makespan increase.",
          "key_trace_refs": [
            {
              "file": "trace_summary.json"
            },
            {
              "file": "selected_trace_windows",
              "windows": [
                {
                  "agent_runnable_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "agent_selected_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "center_timestamp_us": 28571,
                  "critical_runnable_nodes": [
                    "critical-localization_node-00001--localization_node",
                    "critical-localization_node-00002--localization_node",
                    "critical-localization_node-00003--localization_node",
                    "critical-localization_node-00004--localization_node",
                    "critical-navigation_algo_node-00001--navigation_algo_node",
                    "critical-navigation_algo_node-00002--navigation_algo_node",
                    "critical-navigation_algo_node-00003--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00001--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node"
                  ],
                  "critical_selected_nodes": [
                    "critical-localization_node-00001--localization_node",
                    "critical-localization_node-00002--localization_node",
                    "critical-localization_node-00003--localization_node",
                    "critical-localization_node-00004--localization_node",
                    "critical-navigation_algo_node-00001--navigation_algo_node",
                    "critical-navigation_algo_node-00002--navigation_algo_node",
                    "critical-navigation_algo_node-00003--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00001--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node"
                  ],
                  "end_timestamp_us": 78571,
                  "max_cpu_utilization": 0.8875,
                  "max_gpu_utilization": 0.375,
                  "reason": "critical_deadline_miss",
                  "running_agent_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "start_timestamp_us": 0,
                  "target_node_id": "navigation_algo_node",
                  "target_node_instance_id": "critical-navigation_algo_node-00001--navigation_algo_node"
                },
                {
                  "agent_runnable_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "agent_selected_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "center_timestamp_us": 57571,
                  "critical_runnable_nodes": [
                    "critical-localization_node-00002--localization_node",
                    "critical-localization_node-00003--localization_node",
                    "critical-localization_node-00004--localization_node",
                    "critical-localization_node-00005--localization_node",
                    "critical-localization_node-00006--localization_node",
                    "critical-navigation_algo_node-00002--navigation_algo_node",
                    "critical-navigation_algo_node-00003--navigation_algo_node",
                    "critical-navigation_algo_node-00004--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node"
                  ],
                  "critical_selected_nodes": [
                    "critical-localization_node-00002--localization_node",
                    "critical-localization_node-00003--localization_node",
                    "critical-localization_node-00004--localization_node",
                    "critical-localization_node-00005--localization_node",
                    "critical-localization_node-00006--localization_node",
                    "critical-navigation_algo_node-00002--navigation_algo_node",
                    "critical-navigation_algo_node-00003--navigation_algo_node",
                    "critical-navigation_algo_node-00004--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node"
                  ],
                  "end_timestamp_us": 107571,
                  "max_cpu_utilization": 0.8875,
                  "max_gpu_utilization": 0.375,
                  "reason": "critical_deadline_miss",
                  "running_agent_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "start_timestamp_us": 7571,
                  "target_node_id": "navigation_algo_node",
                  "target_node_instance_id": "critical-navigation_algo_node-00002--navigation_algo_node"
                },
                {
                  "agent_runnable_nodes": [],
                  "agent_selected_nodes": [],
                  "center_timestamp_us": 86571,
                  "critical_runnable_nodes": [
                    "critical-localization_node-00003--localization_node",
                    "critical-localization_node-00004--localization_node",
                    "critical-localization_node-00005--localization_node",
                    "critical-localization_node-00006--localization_node",
                    "critical-localization_node-00007--localization_node",
                    "critical-navigation_algo_node-00003--navigation_algo_node",
                    "critical-navigation_algo_node-00004--navigation_algo_node",
                    "critical-navigation_algo_node-00005--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node"
                  ],
                  "critical_selected_nodes": [
                    "critical-localization_node-00003--localization_node",
                    "critical-localization_node-00004--localization_node",
                    "critical-localization_node-00005--localization_node",
                    "critical-localization_node-00006--localization_node",
                    "critical-localization_node-00007--localization_node",
                    "critical-navigation_algo_node-00003--navigation_algo_node",
                    "critical-navigation_algo_node-00004--navigation_algo_node",
                    "critical-navigation_algo_node-00005--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node"
                  ],
                  "end_timestamp_us": 136571,
                  "max_cpu_utilization": 0.9475,
                  "max_gpu_utilization": 0.375,
                  "reason": "critical_deadline_miss",
                  "running_agent_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "start_timestamp_us": 36571,
                  "target_node_id": "navigation_algo_node",
                  "target_node_instance_id": "critical-navigation_algo_node-00003--navigation_algo_node"
                },
                {
                  "agent_runnable_nodes": [],
                  "agent_selected_nodes": [],
                  "center_timestamp_us": 114571,
                  "critical_runnable_nodes": [
                    "critical-localization_node-00005--localization_node",
                    "critical-localization_node-00006--localization_node",
                    "critical-localization_node-00007--localization_node",
                    "critical-localization_node-00008--localization_node",
                    "critical-localization_node-00009--localization_node",
                    "critical-navigation_algo_node-00004--navigation_algo_node",
                    "critical-navigation_algo_node-00005--navigation_algo_node",
                    "critical-navigation_algo_node-00006--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00004--pointcloud_to_laserscan_node"
                  ],
                  "critical_selected_nodes": [
                    "critical-localization_node-00005--localization_node",
                    "critical-localization_node-00006--localization_node",
                    "critical-localization_node-00007--localization_node",
                    "critical-localization_node-00008--localization_node",
                    "critical-localization_node-00009--localization_node",
                    "critical-navigation_algo_node-00004--navigation_algo_node",
                    "critical-navigation_algo_node-00005--navigation_algo_node",
                    "critical-navigation_algo_node-00006--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00004--pointcloud_to_laserscan_node"
                  ],
                  "end_timestamp_us": 164571,
                  "max_cpu_utilization": 0.9475,
                  "max_gpu_utilization": 0.375,
                  "reason": "critical_deadline_miss",
                  "running_agent_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "start_timestamp_us": 64571,
                  "target_node_id": "navigation_algo_node",
                  "target_node_instance_id": "critical-navigation_algo_node-00004--navigation_algo_node"
                },
                {
                  "agent_runnable_nodes": [],
                  "agent_selected_nodes": [],
                  "center_timestamp_us": 143571,
                  "critical_runnable_nodes": [
                    "critical-localization_node-00006--localization_node",
                    "critical-localization_node-00007--localization_node",
                    "critical-localization_node-00008--localization_node",
                    "critical-localization_node-00009--localization_node",
                    "critical-localization_node-00010--localization_node",
                    "critical-navigation_algo_node-00005--navigation_algo_node",
                    "critical-navigation_algo_node-00006--navigation_algo_node",
                    "critical-navigation_algo_node-00007--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00004--pointcloud_to_laserscan_node"
                  ],
                  "critical_selected_nodes": [
                    "critical-localization_node-00006--localization_node",
                    "critical-localization_node-00007--localization_node",
                    "critical-localization_node-00008--localization_node",
                    "critical-localization_node-00009--localization_node",
                    "critical-localization_node-00010--localization_node",
                    "critical-navigation_algo_node-00005--navigation_algo_node",
                    "critical-navigation_algo_node-00006--navigation_algo_node",
                    "critical-navigation_algo_node-00007--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00004--pointcloud_to_laserscan_node"
                  ],
                  "end_timestamp_us": 193571,
                  "max_cpu_utilization": 0.9475,
                  "max_gpu_utilization": 0.375,
                  "reason": "critical_deadline_miss",
                  "running_agent_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "start_timestamp_us": 93571,
                  "target_node_id": "navigation_algo_node",
                  "target_node_instance_id": "critical-navigation_algo_node-00005--navigation_algo_node"
                }
              ]
            }
          ],
          "parameters": {
            "agent_cpu_reservation_cores": 1.0,
            "agent_starvation_boost_after_us": 0
          },
          "proposed_heuristic_change": "Reserve CPU headroom for critical releases before admitting low-criticality agent nodes.",
          "regression_risk": "May under-utilize CPU when critical releases are sparse.",
          "scheduler_defect_summary": "deadline_miss: The navigation_algo_node is consistently missing its deadlines (28.6% satisfaction rate) while other critical nodes meet theirs. The selected trace windows show high CPU utilization (up to 94.75%) and the presence of an agent task (image_captioning) running concurrently. This suggests resource contention where the non-critical agent task is consuming CPU time, delaying the critical navigation algorithm execution.",
          "similar_case_count": 2,
          "workload_characterization": "large workload with critical deadline miss rate 0.238"
        },
        {
          "branch_id": "branch_agent_starvation_boost",
          "expected_metric_impact": "Improve agent completion latency without removing critical-first scheduling.",
          "key_trace_refs": [
            {
              "file": "trace_summary.json"
            },
            {
              "file": "selected_trace_windows",
              "windows": [
                {
                  "agent_runnable_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "agent_selected_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "center_timestamp_us": 28571,
                  "critical_runnable_nodes": [
                    "critical-localization_node-00001--localization_node",
                    "critical-localization_node-00002--localization_node",
                    "critical-localization_node-00003--localization_node",
                    "critical-localization_node-00004--localization_node",
                    "critical-navigation_algo_node-00001--navigation_algo_node",
                    "critical-navigation_algo_node-00002--navigation_algo_node",
                    "critical-navigation_algo_node-00003--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00001--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node"
                  ],
                  "critical_selected_nodes": [
                    "critical-localization_node-00001--localization_node",
                    "critical-localization_node-00002--localization_node",
                    "critical-localization_node-00003--localization_node",
                    "critical-localization_node-00004--localization_node",
                    "critical-navigation_algo_node-00001--navigation_algo_node",
                    "critical-navigation_algo_node-00002--navigation_algo_node",
                    "critical-navigation_algo_node-00003--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00001--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node"
                  ],
                  "end_timestamp_us": 78571,
                  "max_cpu_utilization": 0.8875,
                  "max_gpu_utilization": 0.375,
                  "reason": "critical_deadline_miss",
                  "running_agent_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "start_timestamp_us": 0,
                  "target_node_id": "navigation_algo_node",
                  "target_node_instance_id": "critical-navigation_algo_node-00001--navigation_algo_node"
                },
                {
                  "agent_runnable_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "agent_selected_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "center_timestamp_us": 57571,
                  "critical_runnable_nodes": [
                    "critical-localization_node-00002--localization_node",
                    "critical-localization_node-00003--localization_node",
                    "critical-localization_node-00004--localization_node",
                    "critical-localization_node-00005--localization_node",
                    "critical-localization_node-00006--localization_node",
                    "critical-navigation_algo_node-00002--navigation_algo_node",
                    "critical-navigation_algo_node-00003--navigation_algo_node",
                    "critical-navigation_algo_node-00004--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node"
                  ],
                  "critical_selected_nodes": [
                    "critical-localization_node-00002--localization_node",
                    "critical-localization_node-00003--localization_node",
                    "critical-localization_node-00004--localization_node",
                    "critical-localization_node-00005--localization_node",
                    "critical-localization_node-00006--localization_node",
                    "critical-navigation_algo_node-00002--navigation_algo_node",
                    "critical-navigation_algo_node-00003--navigation_algo_node",
                    "critical-navigation_algo_node-00004--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node"
                  ],
                  "end_timestamp_us": 107571,
                  "max_cpu_utilization": 0.8875,
                  "max_gpu_utilization": 0.375,
                  "reason": "critical_deadline_miss",
                  "running_agent_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "start_timestamp_us": 7571,
                  "target_node_id": "navigation_algo_node",
                  "target_node_instance_id": "critical-navigation_algo_node-00002--navigation_algo_node"
                },
                {
                  "agent_runnable_nodes": [],
                  "agent_selected_nodes": [],
                  "center_timestamp_us": 86571,
                  "critical_runnable_nodes": [
                    "critical-localization_node-00003--localization_node",
                    "critical-localization_node-00004--localization_node",
                    "critical-localization_node-00005--localization_node",
                    "critical-localization_node-00006--localization_node",
                    "critical-localization_node-00007--localization_node",
                    "critical-navigation_algo_node-00003--navigation_algo_node",
                    "critical-navigation_algo_node-00004--navigation_algo_node",
                    "critical-navigation_algo_node-00005--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node"
                  ],
                  "critical_selected_nodes": [
                    "critical-localization_node-00003--localization_node",
                    "critical-localization_node-00004--localization_node",
                    "critical-localization_node-00005--localization_node",
                    "critical-localization_node-00006--localization_node",
                    "critical-localization_node-00007--localization_node",
                    "critical-navigation_algo_node-00003--navigation_algo_node",
                    "critical-navigation_algo_node-00004--navigation_algo_node",
                    "critical-navigation_algo_node-00005--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node"
                  ],
                  "end_timestamp_us": 136571,
                  "max_cpu_utilization": 0.9475,
                  "max_gpu_utilization": 0.375,
                  "reason": "critical_deadline_miss",
                  "running_agent_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "start_timestamp_us": 36571,
                  "target_node_id": "navigation_algo_node",
                  "target_node_instance_id": "critical-navigation_algo_node-00003--navigation_algo_node"
                },
                {
                  "agent_runnable_nodes": [],
                  "agent_selected_nodes": [],
                  "center_timestamp_us": 114571,
                  "critical_runnable_nodes": [
                    "critical-localization_node-00005--localization_node",
                    "critical-localization_node-00006--localization_node",
                    "critical-localization_node-00007--localization_node",
                    "critical-localization_node-00008--localization_node",
                    "critical-localization_node-00009--localization_node",
                    "critical-navigation_algo_node-00004--navigation_algo_node",
                    "critical-navigation_algo_node-00005--navigation_algo_node",
                    "critical-navigation_algo_node-00006--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00004--pointcloud_to_laserscan_node"
                  ],
                  "critical_selected_nodes": [
                    "critical-localization_node-00005--localization_node",
                    "critical-localization_node-00006--localization_node",
                    "critical-localization_node-00007--localization_node",
                    "critical-localization_node-00008--localization_node",
                    "critical-localization_node-00009--localization_node",
                    "critical-navigation_algo_node-00004--navigation_algo_node",
                    "critical-navigation_algo_node-00005--navigation_algo_node",
                    "critical-navigation_algo_node-00006--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00004--pointcloud_to_laserscan_node"
                  ],
                  "end_timestamp_us": 164571,
                  "max_cpu_utilization": 0.9475,
                  "max_gpu_utilization": 0.375,
                  "reason": "critical_deadline_miss",
                  "running_agent_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "start_timestamp_us": 64571,
                  "target_node_id": "navigation_algo_node",
                  "target_node_instance_id": "critical-navigation_algo_node-00004--navigation_algo_node"
                },
                {
                  "agent_runnable_nodes": [],
                  "agent_selected_nodes": [],
                  "center_timestamp_us": 143571,
                  "critical_runnable_nodes": [
                    "critical-localization_node-00006--localization_node",
                    "critical-localization_node-00007--localization_node",
                    "critical-localization_node-00008--localization_node",
                    "critical-localization_node-00009--localization_node",
                    "critical-localization_node-00010--localization_node",
                    "critical-navigation_algo_node-00005--navigation_algo_node",
                    "critical-navigation_algo_node-00006--navigation_algo_node",
                    "critical-navigation_algo_node-00007--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00004--pointcloud_to_laserscan_node"
                  ],
                  "critical_selected_nodes": [
                    "critical-localization_node-00006--localization_node",
                    "critical-localization_node-00007--localization_node",
                    "critical-localization_node-00008--localization_node",
                    "critical-localization_node-00009--localization_node",
                    "critical-localization_node-00010--localization_node",
                    "critical-navigation_algo_node-00005--navigation_algo_node",
                    "critical-navigation_algo_node-00006--navigation_algo_node",
                    "critical-navigation_algo_node-00007--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00004--pointcloud_to_laserscan_node"
                  ],
                  "end_timestamp_us": 193571,
                  "max_cpu_utilization": 0.9475,
                  "max_gpu_utilization": 0.375,
                  "reason": "critical_deadline_miss",
                  "running_agent_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "start_timestamp_us": 93571,
                  "target_node_id": "navigation_algo_node",
                  "target_node_instance_id": "critical-navigation_algo_node-00005--navigation_algo_node"
                }
              ]
            }
          ],
          "parameters": {
            "agent_cpu_reservation_cores": 0.5,
            "agent_starvation_boost_after_us": 500000
          },
          "proposed_heuristic_change": "Boost agent nodes after bounded waiting time while keeping critical fit checks.",
          "regression_risk": "Can increase critical contention if the boost threshold is too low.",
          "scheduler_defect_summary": "deadline_miss: The navigation_algo_node is consistently missing its deadlines (28.6% satisfaction rate) while other critical nodes meet theirs. The selected trace windows show high CPU utilization (up to 94.75%) and the presence of an agent task (image_captioning) running concurrently. This suggests resource contention where the non-critical agent task is consuming CPU time, delaying the critical navigation algorithm execution.",
          "similar_case_count": 2,
          "workload_characterization": "large workload with agent completion latency 2986000 us"
        }
      ],
      "distance": 0.0,
      "metrics": {
        "agent_avg_completion_time_us": 2986000,
        "critical_missed_deadline_count": 100
      },
      "scheduler_version": "candidate_1_branch_critical_headroom",
      "trace_run": "case/replays/candidate_1_branch_critical_headroom/20260512-140516",
      "workload_signature": {
        "agent_arrival_density": 0.75,
        "agent_release_count": 3,
        "agent_request_count": 1,
        "avg_agent_completion_time_us": 2986000,
        "avg_cpu_utilization": 0.5475593750000001,
        "avg_critical_period_us": 32857,
        "avg_gpu_utilization": 0.2175,
        "cpu_capacity": 4.0,
        "critical_deadline_miss_rate": 0.23809523809523808,
        "critical_node_count": 3,
        "gpu_capacity": 2048,
        "high_criticality_node_count": 2,
        "memory_capacity": 4096,
        "min_critical_period_us": 20000,
        "network_capacity": 100.0,
        "scenario_name": "home_eqa_scenario_001",
        "scenario_path": "/home/dawnat9/code-workspace/ai4heuristic/agent4scheduler/configs/scenarios/home_eqa_scenario_001.yaml",
        "scene_complexity": "large"
      }
    },
    {
      "advice": [
        {
          "branch_id": "branch_critical_headroom",
          "expected_metric_impact": "Reduce critical deadline misses with possible agent makespan increase.",
          "key_trace_refs": [
            {
              "file": "trace_summary.json",
              "metric": "critical_task_metrics.*.missed_deadline_count",
              "value": 100
            },
            {
              "file": "selected_trace_windows",
              "windows": [
                {
                  "agent_runnable_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "agent_selected_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "center_timestamp_us": 28571,
                  "critical_runnable_nodes": [
                    "critical-localization_node-00001--localization_node",
                    "critical-localization_node-00002--localization_node",
                    "critical-localization_node-00003--localization_node",
                    "critical-localization_node-00004--localization_node",
                    "critical-navigation_algo_node-00001--navigation_algo_node",
                    "critical-navigation_algo_node-00002--navigation_algo_node",
                    "critical-navigation_algo_node-00003--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00001--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node"
                  ],
                  "critical_selected_nodes": [
                    "critical-localization_node-00001--localization_node",
                    "critical-localization_node-00002--localization_node",
                    "critical-localization_node-00003--localization_node",
                    "critical-localization_node-00004--localization_node",
                    "critical-navigation_algo_node-00001--navigation_algo_node",
                    "critical-navigation_algo_node-00002--navigation_algo_node",
                    "critical-navigation_algo_node-00003--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00001--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node"
                  ],
                  "end_timestamp_us": 78571,
                  "max_cpu_utilization": 0.8875,
                  "max_gpu_utilization": 0.375,
                  "reason": "critical_deadline_miss",
                  "running_agent_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "start_timestamp_us": 0,
                  "target_node_id": "navigation_algo_node",
                  "target_node_instance_id": "critical-navigation_algo_node-00001--navigation_algo_node"
                },
                {
                  "agent_runnable_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "agent_selected_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "center_timestamp_us": 57571,
                  "critical_runnable_nodes": [
                    "critical-localization_node-00002--localization_node",
                    "critical-localization_node-00003--localization_node",
                    "critical-localization_node-00004--localization_node",
                    "critical-localization_node-00005--localization_node",
                    "critical-localization_node-00006--localization_node",
                    "critical-navigation_algo_node-00002--navigation_algo_node",
                    "critical-navigation_algo_node-00003--navigation_algo_node",
                    "critical-navigation_algo_node-00004--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node"
                  ],
                  "critical_selected_nodes": [
                    "critical-localization_node-00002--localization_node",
                    "critical-localization_node-00003--localization_node",
                    "critical-localization_node-00004--localization_node",
                    "critical-localization_node-00005--localization_node",
                    "critical-localization_node-00006--localization_node",
                    "critical-navigation_algo_node-00002--navigation_algo_node",
                    "critical-navigation_algo_node-00003--navigation_algo_node",
                    "critical-navigation_algo_node-00004--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node"
                  ],
                  "end_timestamp_us": 107571,
                  "max_cpu_utilization": 0.8875,
                  "max_gpu_utilization": 0.375,
                  "reason": "critical_deadline_miss",
                  "running_agent_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "start_timestamp_us": 7571,
                  "target_node_id": "navigation_algo_node",
                  "target_node_instance_id": "critical-navigation_algo_node-00002--navigation_algo_node"
                },
                {
                  "agent_runnable_nodes": [],
                  "agent_selected_nodes": [],
                  "center_timestamp_us": 86571,
                  "critical_runnable_nodes": [
                    "critical-localization_node-00003--localization_node",
                    "critical-localization_node-00004--localization_node",
                    "critical-localization_node-00005--localization_node",
                    "critical-localization_node-00006--localization_node",
                    "critical-localization_node-00007--localization_node",
                    "critical-navigation_algo_node-00003--navigation_algo_node",
                    "critical-navigation_algo_node-00004--navigation_algo_node",
                    "critical-navigation_algo_node-00005--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node"
                  ],
                  "critical_selected_nodes": [
                    "critical-localization_node-00003--localization_node",
                    "critical-localization_node-00004--localization_node",
                    "critical-localization_node-00005--localization_node",
                    "critical-localization_node-00006--localization_node",
                    "critical-localization_node-00007--localization_node",
                    "critical-navigation_algo_node-00003--navigation_algo_node",
                    "critical-navigation_algo_node-00004--navigation_algo_node",
                    "critical-navigation_algo_node-00005--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node"
                  ],
                  "end_timestamp_us": 136571,
                  "max_cpu_utilization": 0.9475,
                  "max_gpu_utilization": 0.375,
                  "reason": "critical_deadline_miss",
                  "running_agent_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "start_timestamp_us": 36571,
                  "target_node_id": "navigation_algo_node",
                  "target_node_instance_id": "critical-navigation_algo_node-00003--navigation_algo_node"
                },
                {
                  "agent_runnable_nodes": [],
                  "agent_selected_nodes": [],
                  "center_timestamp_us": 114571,
                  "critical_runnable_nodes": [
                    "critical-localization_node-00005--localization_node",
                    "critical-localization_node-00006--localization_node",
                    "critical-localization_node-00007--localization_node",
                    "critical-localization_node-00008--localization_node",
                    "critical-localization_node-00009--localization_node",
                    "critical-navigation_algo_node-00004--navigation_algo_node",
                    "critical-navigation_algo_node-00005--navigation_algo_node",
                    "critical-navigation_algo_node-00006--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00004--pointcloud_to_laserscan_node"
                  ],
                  "critical_selected_nodes": [
                    "critical-localization_node-00005--localization_node",
                    "critical-localization_node-00006--localization_node",
                    "critical-localization_node-00007--localization_node",
                    "critical-localization_node-00008--localization_node",
                    "critical-localization_node-00009--localization_node",
                    "critical-navigation_algo_node-00004--navigation_algo_node",
                    "critical-navigation_algo_node-00005--navigation_algo_node",
                    "critical-navigation_algo_node-00006--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00004--pointcloud_to_laserscan_node"
                  ],
                  "end_timestamp_us": 164571,
                  "max_cpu_utilization": 0.9475,
                  "max_gpu_utilization": 0.375,
                  "reason": "critical_deadline_miss",
                  "running_agent_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "start_timestamp_us": 64571,
                  "target_node_id": "navigation_algo_node",
                  "target_node_instance_id": "critical-navigation_algo_node-00004--navigation_algo_node"
                },
                {
                  "agent_runnable_nodes": [],
                  "agent_selected_nodes": [],
                  "center_timestamp_us": 143571,
                  "critical_runnable_nodes": [
                    "critical-localization_node-00006--localization_node",
                    "critical-localization_node-00007--localization_node",
                    "critical-localization_node-00008--localization_node",
                    "critical-localization_node-00009--localization_node",
                    "critical-localization_node-00010--localization_node",
                    "critical-navigation_algo_node-00005--navigation_algo_node",
                    "critical-navigation_algo_node-00006--navigation_algo_node",
                    "critical-navigation_algo_node-00007--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00004--pointcloud_to_laserscan_node"
                  ],
                  "critical_selected_nodes": [
                    "critical-localization_node-00006--localization_node",
                    "critical-localization_node-00007--localization_node",
                    "critical-localization_node-00008--localization_node",
                    "critical-localization_node-00009--localization_node",
                    "critical-localization_node-00010--localization_node",
                    "critical-navigation_algo_node-00005--navigation_algo_node",
                    "critical-navigation_algo_node-00006--navigation_algo_node",
                    "critical-navigation_algo_node-00007--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00004--pointcloud_to_laserscan_node"
                  ],
                  "end_timestamp_us": 193571,
                  "max_cpu_utilization": 0.9475,
                  "max_gpu_utilization": 0.375,
                  "reason": "critical_deadline_miss",
                  "running_agent_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "start_timestamp_us": 93571,
                  "target_node_id": "navigation_algo_node",
                  "target_node_instance_id": "critical-navigation_algo_node-00005--navigation_algo_node"
                }
              ]
            }
          ],
          "parameters": {
            "agent_cpu_reservation_cores": 1.0,
            "agent_starvation_boost_after_us": 0
          },
          "proposed_heuristic_change": "Reserve CPU headroom for critical releases before admitting low-criticality agent nodes.",
          "regression_risk": "May under-utilize CPU when critical releases are sparse.",
          "scheduler_defect_summary": "critical_deadline_miss: The navigation_algo_node misses deadlines due to CPU contention from a concurrently running agent task (image_captioning), which runs at high CPU utilization (up to 94.75%) and may monopolize CPU resources, preventing the critical navigation node from meeting its timing constraints.",
          "similar_case_count": 3,
          "workload_characterization": "large workload with critical deadline miss rate 0.238"
        },
        {
          "branch_id": "branch_agent_starvation_boost",
          "expected_metric_impact": "Improve agent completion latency without removing critical-first scheduling.",
          "key_trace_refs": [
            {
              "file": "trace_summary.json",
              "metric": "critical_task_metrics.*.missed_deadline_count",
              "value": 100
            },
            {
              "file": "selected_trace_windows",
              "windows": [
                {
                  "agent_runnable_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "agent_selected_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "center_timestamp_us": 28571,
                  "critical_runnable_nodes": [
                    "critical-localization_node-00001--localization_node",
                    "critical-localization_node-00002--localization_node",
                    "critical-localization_node-00003--localization_node",
                    "critical-localization_node-00004--localization_node",
                    "critical-navigation_algo_node-00001--navigation_algo_node",
                    "critical-navigation_algo_node-00002--navigation_algo_node",
                    "critical-navigation_algo_node-00003--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00001--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node"
                  ],
                  "critical_selected_nodes": [
                    "critical-localization_node-00001--localization_node",
                    "critical-localization_node-00002--localization_node",
                    "critical-localization_node-00003--localization_node",
                    "critical-localization_node-00004--localization_node",
                    "critical-navigation_algo_node-00001--navigation_algo_node",
                    "critical-navigation_algo_node-00002--navigation_algo_node",
                    "critical-navigation_algo_node-00003--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00001--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node"
                  ],
                  "end_timestamp_us": 78571,
                  "max_cpu_utilization": 0.8875,
                  "max_gpu_utilization": 0.375,
                  "reason": "critical_deadline_miss",
                  "running_agent_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "start_timestamp_us": 0,
                  "target_node_id": "navigation_algo_node",
                  "target_node_instance_id": "critical-navigation_algo_node-00001--navigation_algo_node"
                },
                {
                  "agent_runnable_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "agent_selected_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "center_timestamp_us": 57571,
                  "critical_runnable_nodes": [
                    "critical-localization_node-00002--localization_node",
                    "critical-localization_node-00003--localization_node",
                    "critical-localization_node-00004--localization_node",
                    "critical-localization_node-00005--localization_node",
                    "critical-localization_node-00006--localization_node",
                    "critical-navigation_algo_node-00002--navigation_algo_node",
                    "critical-navigation_algo_node-00003--navigation_algo_node",
                    "critical-navigation_algo_node-00004--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node"
                  ],
                  "critical_selected_nodes": [
                    "critical-localization_node-00002--localization_node",
                    "critical-localization_node-00003--localization_node",
                    "critical-localization_node-00004--localization_node",
                    "critical-localization_node-00005--localization_node",
                    "critical-localization_node-00006--localization_node",
                    "critical-navigation_algo_node-00002--navigation_algo_node",
                    "critical-navigation_algo_node-00003--navigation_algo_node",
                    "critical-navigation_algo_node-00004--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node"
                  ],
                  "end_timestamp_us": 107571,
                  "max_cpu_utilization": 0.8875,
                  "max_gpu_utilization": 0.375,
                  "reason": "critical_deadline_miss",
                  "running_agent_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "start_timestamp_us": 7571,
                  "target_node_id": "navigation_algo_node",
                  "target_node_instance_id": "critical-navigation_algo_node-00002--navigation_algo_node"
                },
                {
                  "agent_runnable_nodes": [],
                  "agent_selected_nodes": [],
                  "center_timestamp_us": 86571,
                  "critical_runnable_nodes": [
                    "critical-localization_node-00003--localization_node",
                    "critical-localization_node-00004--localization_node",
                    "critical-localization_node-00005--localization_node",
                    "critical-localization_node-00006--localization_node",
                    "critical-localization_node-00007--localization_node",
                    "critical-navigation_algo_node-00003--navigation_algo_node",
                    "critical-navigation_algo_node-00004--navigation_algo_node",
                    "critical-navigation_algo_node-00005--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node"
                  ],
                  "critical_selected_nodes": [
                    "critical-localization_node-00003--localization_node",
                    "critical-localization_node-00004--localization_node",
                    "critical-localization_node-00005--localization_node",
                    "critical-localization_node-00006--localization_node",
                    "critical-localization_node-00007--localization_node",
                    "critical-navigation_algo_node-00003--navigation_algo_node",
                    "critical-navigation_algo_node-00004--navigation_algo_node",
                    "critical-navigation_algo_node-00005--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node"
                  ],
                  "end_timestamp_us": 136571,
                  "max_cpu_utilization": 0.9475,
                  "max_gpu_utilization": 0.375,
                  "reason": "critical_deadline_miss",
                  "running_agent_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "start_timestamp_us": 36571,
                  "target_node_id": "navigation_algo_node",
                  "target_node_instance_id": "critical-navigation_algo_node-00003--navigation_algo_node"
                },
                {
                  "agent_runnable_nodes": [],
                  "agent_selected_nodes": [],
                  "center_timestamp_us": 114571,
                  "critical_runnable_nodes": [
                    "critical-localization_node-00005--localization_node",
                    "critical-localization_node-00006--localization_node",
                    "critical-localization_node-00007--localization_node",
                    "critical-localization_node-00008--localization_node",
                    "critical-localization_node-00009--localization_node",
                    "critical-navigation_algo_node-00004--navigation_algo_node",
                    "critical-navigation_algo_node-00005--navigation_algo_node",
                    "critical-navigation_algo_node-00006--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00004--pointcloud_to_laserscan_node"
                  ],
                  "critical_selected_nodes": [
                    "critical-localization_node-00005--localization_node",
                    "critical-localization_node-00006--localization_node",
                    "critical-localization_node-00007--localization_node",
                    "critical-localization_node-00008--localization_node",
                    "critical-localization_node-00009--localization_node",
                    "critical-navigation_algo_node-00004--navigation_algo_node",
                    "critical-navigation_algo_node-00005--navigation_algo_node",
                    "critical-navigation_algo_node-00006--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00004--pointcloud_to_laserscan_node"
                  ],
                  "end_timestamp_us": 164571,
                  "max_cpu_utilization": 0.9475,
                  "max_gpu_utilization": 0.375,
                  "reason": "critical_deadline_miss",
                  "running_agent_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "start_timestamp_us": 64571,
                  "target_node_id": "navigation_algo_node",
                  "target_node_instance_id": "critical-navigation_algo_node-00004--navigation_algo_node"
                },
                {
                  "agent_runnable_nodes": [],
                  "agent_selected_nodes": [],
                  "center_timestamp_us": 143571,
                  "critical_runnable_nodes": [
                    "critical-localization_node-00006--localization_node",
                    "critical-localization_node-00007--localization_node",
                    "critical-localization_node-00008--localization_node",
                    "critical-localization_node-00009--localization_node",
                    "critical-localization_node-00010--localization_node",
                    "critical-navigation_algo_node-00005--navigation_algo_node",
                    "critical-navigation_algo_node-00006--navigation_algo_node",
                    "critical-navigation_algo_node-00007--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00004--pointcloud_to_laserscan_node"
                  ],
                  "critical_selected_nodes": [
                    "critical-localization_node-00006--localization_node",
                    "critical-localization_node-00007--localization_node",
                    "critical-localization_node-00008--localization_node",
                    "critical-localization_node-00009--localization_node",
                    "critical-localization_node-00010--localization_node",
                    "critical-navigation_algo_node-00005--navigation_algo_node",
                    "critical-navigation_algo_node-00006--navigation_algo_node",
                    "critical-navigation_algo_node-00007--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00004--pointcloud_to_laserscan_node"
                  ],
                  "end_timestamp_us": 193571,
                  "max_cpu_utilization": 0.9475,
                  "max_gpu_utilization": 0.375,
                  "reason": "critical_deadline_miss",
                  "running_agent_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning"
                  ],
                  "start_timestamp_us": 93571,
                  "target_node_id": "navigation_algo_node",
                  "target_node_instance_id": "critical-navigation_algo_node-00005--navigation_algo_node"
                }
              ]
            }
          ],
          "parameters": {
            "agent_cpu_reservation_cores": 0.5,
            "agent_starvation_boost_after_us": 500000
          },
          "proposed_heuristic_change": "Boost agent nodes after bounded waiting time while keeping critical fit checks.",
          "regression_risk": "Can increase critical contention if the boost threshold is too low.",
          "scheduler_defect_summary": "critical_deadline_miss: The navigation_algo_node misses deadlines due to CPU contention from a concurrently running agent task (image_captioning), which runs at high CPU utilization (up to 94.75%) and may monopolize CPU resources, preventing the critical navigation node from meeting its timing constraints.",
          "similar_case_count": 3,
          "workload_characterization": "large workload with agent completion latency 2986000 us"
        }
      ],
      "distance": 0.0,
      "metrics": {
        "agent_avg_completion_time_us": 2987000,
        "critical_missed_deadline_count": 100
      },
      "scheduler_version": "candidate_1_branch_critical_headroom",
      "trace_run": "case/replays/20260512-142444/candidate_1_branch_critical_headroom/20260512-142528",
      "workload_signature": {
        "agent_arrival_density": 0.75,
        "agent_release_count": 3,
        "agent_request_count": 1,
        "avg_agent_completion_time_us": 2986000,
        "avg_cpu_utilization": 0.5475593750000001,
        "avg_critical_period_us": 32857,
        "avg_gpu_utilization": 0.2175,
        "cpu_capacity": 4.0,
        "critical_deadline_miss_rate": 0.23809523809523808,
        "critical_node_count": 3,
        "gpu_capacity": 2048,
        "high_criticality_node_count": 2,
        "memory_capacity": 4096,
        "min_critical_period_us": 20000,
        "network_capacity": 100.0,
        "scenario_name": "home_eqa_scenario_001",
        "scenario_path": "/home/dawnat9/code-workspace/ai4heuristic/agent4scheduler/configs/scenarios/home_eqa_scenario_001.yaml",
        "scene_complexity": "large"
      }
    },
    {
      "advice": [
        {
          "branch_id": "branch_critical_headroom",
          "expected_metric_impact": "Reduce critical deadline misses with possible agent makespan increase.",
          "key_trace_refs": [
            {
              "file": "trace_summary.json"
            },
            {
              "file": "selected_trace_windows",
              "windows": [
                {
                  "agent_runnable_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning",
                    "agent-caption-pipeline-00018000-001--text_to_speech",
                    "agent-caption-pipeline-00018000-001--text_translation"
                  ],
                  "agent_selected_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning",
                    "agent-caption-pipeline-00018000-001--text_to_speech",
                    "agent-caption-pipeline-00018000-001--text_translation"
                  ],
                  "center_timestamp_us": 40000,
                  "critical_runnable_nodes": [
                    "critical-localization_node-00001--localization_node",
                    "critical-localization_node-00004--localization_node",
                    "critical-localization_node-00005--localization_node",
                    "critical-localization_node-00007--localization_node",
                    "critical-localization_node-00008--localization_node",
                    "critical-navigation_algo_node-00003--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00006--pointcloud_to_laserscan_node"
                  ],
                  "critical_selected_nodes": [
                    "critical-localization_node-00001--localization_node",
                    "critical-localization_node-00004--localization_node",
                    "critical-localization_node-00005--localization_node",
                    "critical-localization_node-00007--localization_node",
                    "critical-localization_node-00008--localization_node",
                    "critical-navigation_algo_node-00003--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00006--pointcloud_to_laserscan_node"
                  ],
                  "end_timestamp_us": 90000,
                  "max_cpu_utilization": 0.625,
                  "max_gpu_utilization": 0.0,
                  "reason": "critical_deadline_miss",
                  "running_agent_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning",
                    "agent-caption-pipeline-00018000-001--text_to_speech",
                    "agent-caption-pipeline-00018000-001--text_translation"
                  ],
                  "start_timestamp_us": 0,
                  "target_node_id": "localization_node",
                  "target_node_instance_id": "critical-localization_node-00004--localization_node"
                }
              ]
            }
          ],
          "parameters": {
            "agent_cpu_reservation_cores": 1.0,
            "agent_starvation_boost_after_us": 0
          },
          "proposed_heuristic_change": "Reserve CPU headroom for critical releases before admitting low-criticality agent nodes.",
          "regression_risk": "May under-utilize CPU when critical releases are sparse.",
          "scheduler_defect_summary": "deadline_miss_cpu_contention: The deadline miss for localization_node instance 00004 is likely due to high CPU utilization (62.5%) caused by concurrent execution of multiple critical and agent nodes within the same time window, leading to contention.",
          "similar_case_count": 0,
          "workload_characterization": "large workload with critical deadline miss rate 0.125"
        },
        {
          "branch_id": "branch_agent_starvation_boost",
          "expected_metric_impact": "Improve agent completion latency without removing critical-first scheduling.",
          "key_trace_refs": [
            {
              "file": "trace_summary.json"
            },
            {
              "file": "selected_trace_windows",
              "windows": [
                {
                  "agent_runnable_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning",
                    "agent-caption-pipeline-00018000-001--text_to_speech",
                    "agent-caption-pipeline-00018000-001--text_translation"
                  ],
                  "agent_selected_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning",
                    "agent-caption-pipeline-00018000-001--text_to_speech",
                    "agent-caption-pipeline-00018000-001--text_translation"
                  ],
                  "center_timestamp_us": 40000,
                  "critical_runnable_nodes": [
                    "critical-localization_node-00001--localization_node",
                    "critical-localization_node-00004--localization_node",
                    "critical-localization_node-00005--localization_node",
                    "critical-localization_node-00007--localization_node",
                    "critical-localization_node-00008--localization_node",
                    "critical-navigation_algo_node-00003--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00006--pointcloud_to_laserscan_node"
                  ],
                  "critical_selected_nodes": [
                    "critical-localization_node-00001--localization_node",
                    "critical-localization_node-00004--localization_node",
                    "critical-localization_node-00005--localization_node",
                    "critical-localization_node-00007--localization_node",
                    "critical-localization_node-00008--localization_node",
                    "critical-navigation_algo_node-00003--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00006--pointcloud_to_laserscan_node"
                  ],
                  "end_timestamp_us": 90000,
                  "max_cpu_utilization": 0.625,
                  "max_gpu_utilization": 0.0,
                  "reason": "critical_deadline_miss",
                  "running_agent_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning",
                    "agent-caption-pipeline-00018000-001--text_to_speech",
                    "agent-caption-pipeline-00018000-001--text_translation"
                  ],
                  "start_timestamp_us": 0,
                  "target_node_id": "localization_node",
                  "target_node_instance_id": "critical-localization_node-00004--localization_node"
                }
              ]
            }
          ],
          "parameters": {
            "agent_cpu_reservation_cores": 0.5,
            "agent_starvation_boost_after_us": 500000
          },
          "proposed_heuristic_change": "Boost agent nodes after bounded waiting time while keeping critical fit checks.",
          "regression_risk": "Can increase critical contention if the boost threshold is too low.",
          "scheduler_defect_summary": "deadline_miss_cpu_contention: The deadline miss for localization_node instance 00004 is likely due to high CPU utilization (62.5%) caused by concurrent execution of multiple critical and agent nodes within the same time window, leading to contention.",
          "similar_case_count": 0,
          "workload_characterization": "large workload with agent completion latency 25000 us"
        }
      ],
      "distance": 2961002.3019958558,
      "metrics": {
        "agent_avg_completion_time_us": 25000,
        "critical_missed_deadline_count": 1
      },
      "scheduler_version": "candidate_1_branch_critical_headroom",
      "trace_run": "case/replays/candidate_1_branch_critical_headroom/20260511-232920",
      "workload_signature": {
        "agent_arrival_density": 30.0,
        "agent_release_count": 3,
        "agent_request_count": 1,
        "avg_agent_completion_time_us": 25000,
        "avg_cpu_utilization": 0.1825,
        "avg_critical_period_us": 32866,
        "avg_gpu_utilization": 0.0,
        "cpu_capacity": 4.0,
        "critical_deadline_miss_rate": 0.125,
        "critical_node_count": 3,
        "gpu_capacity": 0,
        "high_criticality_node_count": 2,
        "memory_capacity": 1024,
        "min_critical_period_us": 20000,
        "network_capacity": 100.0,
        "scenario_name": "home_eqa_scenario_001",
        "scenario_path": "/home/dawnat9/code-workspace/ai4heuristic/agent4scheduler/configs/scenarios/home_eqa_scenario_001.yaml",
        "scene_complexity": "large"
      }
    },
    {
      "advice": [
        {
          "branch_id": "branch_critical_headroom",
          "expected_metric_impact": "Reduce critical deadline misses with possible agent makespan increase.",
          "key_trace_refs": [
            {
              "file": "trace_summary.json"
            },
            {
              "file": "selected_trace_windows",
              "windows": [
                {
                  "agent_runnable_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning",
                    "agent-caption-pipeline-00018000-001--text_to_speech",
                    "agent-caption-pipeline-00018000-001--text_translation"
                  ],
                  "agent_selected_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning",
                    "agent-caption-pipeline-00018000-001--text_to_speech",
                    "agent-caption-pipeline-00018000-001--text_translation"
                  ],
                  "center_timestamp_us": 40000,
                  "critical_runnable_nodes": [
                    "critical-localization_node-00001--localization_node",
                    "critical-localization_node-00004--localization_node",
                    "critical-localization_node-00005--localization_node",
                    "critical-localization_node-00007--localization_node",
                    "critical-localization_node-00008--localization_node",
                    "critical-navigation_algo_node-00003--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00006--pointcloud_to_laserscan_node"
                  ],
                  "critical_selected_nodes": [
                    "critical-localization_node-00001--localization_node",
                    "critical-localization_node-00004--localization_node",
                    "critical-localization_node-00005--localization_node",
                    "critical-localization_node-00007--localization_node",
                    "critical-localization_node-00008--localization_node",
                    "critical-navigation_algo_node-00003--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00006--pointcloud_to_laserscan_node"
                  ],
                  "end_timestamp_us": 90000,
                  "max_cpu_utilization": 0.625,
                  "max_gpu_utilization": 0.0,
                  "reason": "critical_deadline_miss",
                  "running_agent_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning",
                    "agent-caption-pipeline-00018000-001--text_to_speech",
                    "agent-caption-pipeline-00018000-001--text_translation"
                  ],
                  "start_timestamp_us": 0,
                  "target_node_id": "localization_node",
                  "target_node_instance_id": "critical-localization_node-00004--localization_node"
                }
              ]
            }
          ],
          "parameters": {
            "agent_cpu_reservation_cores": 1.0,
            "agent_starvation_boost_after_us": 0
          },
          "proposed_heuristic_change": "Reserve CPU headroom for critical releases before admitting low-criticality agent nodes.",
          "regression_risk": "May under-utilize CPU when critical releases are sparse.",
          "scheduler_defect_summary": "deadline_miss: Concurrent execution of agent tasks (image_captioning, text_to_speech, text_translation) increased CPU utilization (max 62.5%), causing the critical localization_node instance 00004 to miss its deadline.",
          "similar_case_count": 1,
          "workload_characterization": "large workload with critical deadline miss rate 0.125"
        },
        {
          "branch_id": "branch_agent_starvation_boost",
          "expected_metric_impact": "Improve agent completion latency without removing critical-first scheduling.",
          "key_trace_refs": [
            {
              "file": "trace_summary.json"
            },
            {
              "file": "selected_trace_windows",
              "windows": [
                {
                  "agent_runnable_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning",
                    "agent-caption-pipeline-00018000-001--text_to_speech",
                    "agent-caption-pipeline-00018000-001--text_translation"
                  ],
                  "agent_selected_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning",
                    "agent-caption-pipeline-00018000-001--text_to_speech",
                    "agent-caption-pipeline-00018000-001--text_translation"
                  ],
                  "center_timestamp_us": 40000,
                  "critical_runnable_nodes": [
                    "critical-localization_node-00001--localization_node",
                    "critical-localization_node-00004--localization_node",
                    "critical-localization_node-00005--localization_node",
                    "critical-localization_node-00007--localization_node",
                    "critical-localization_node-00008--localization_node",
                    "critical-navigation_algo_node-00003--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00006--pointcloud_to_laserscan_node"
                  ],
                  "critical_selected_nodes": [
                    "critical-localization_node-00001--localization_node",
                    "critical-localization_node-00004--localization_node",
                    "critical-localization_node-00005--localization_node",
                    "critical-localization_node-00007--localization_node",
                    "critical-localization_node-00008--localization_node",
                    "critical-navigation_algo_node-00003--navigation_algo_node",
                    "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node",
                    "critical-pointcloud_to_laserscan_node-00006--pointcloud_to_laserscan_node"
                  ],
                  "end_timestamp_us": 90000,
                  "max_cpu_utilization": 0.625,
                  "max_gpu_utilization": 0.0,
                  "reason": "critical_deadline_miss",
                  "running_agent_nodes": [
                    "agent-caption-pipeline-00018000-001--image_captioning",
                    "agent-caption-pipeline-00018000-001--text_to_speech",
                    "agent-caption-pipeline-00018000-001--text_translation"
                  ],
                  "start_timestamp_us": 0,
                  "target_node_id": "localization_node",
                  "target_node_instance_id": "critical-localization_node-00004--localization_node"
                }
              ]
            }
          ],
          "parameters": {
            "agent_cpu_reservation_cores": 0.5,
            "agent_starvation_boost_after_us": 500000
          },
          "proposed_heuristic_change": "Boost agent nodes after bounded waiting time while keeping critical fit checks.",
          "regression_risk": "Can increase critical contention if the boost threshold is too low.",
          "scheduler_defect_summary": "deadline_miss: Concurrent execution of agent tasks (image_captioning, text_to_speech, text_translation) increased CPU utilization (max 62.5%), causing the critical localization_node instance 00004 to miss its deadline.",
          "similar_case_count": 1,
          "workload_characterization": "large workload with agent completion latency 25000 us"
        }
      ],
      "distance": 2961002.3019958558,
      "metrics": {
        "agent_avg_completion_time_us": 25000,
        "critical_missed_deadline_count": 1
      },
      "scheduler_version": "candidate_1_branch_critical_headroom",
      "trace_run": "case/replays/candidate_1_branch_critical_headroom/20260511-233550",
      "workload_signature": {
        "agent_arrival_density": 30.0,
        "agent_release_count": 3,
        "agent_request_count": 1,
        "avg_agent_completion_time_us": 25000,
        "avg_cpu_utilization": 0.1825,
        "avg_critical_period_us": 32866,
        "avg_gpu_utilization": 0.0,
        "cpu_capacity": 4.0,
        "critical_deadline_miss_rate": 0.125,
        "critical_node_count": 3,
        "gpu_capacity": 0,
        "high_criticality_node_count": 2,
        "memory_capacity": 1024,
        "min_critical_period_us": 20000,
        "network_capacity": 100.0,
        "scenario_name": "home_eqa_scenario_001",
        "scenario_path": "/home/dawnat9/code-workspace/ai4heuristic/agent4scheduler/configs/scenarios/home_eqa_scenario_001.yaml",
        "scene_complexity": "large"
      }
    }
  ],
  "trace_findings": [
    {
      "affected_nodes": [
        "critical-navigation_algo_node-00001--navigation_algo_node",
        "critical-navigation_algo_node-00002--navigation_algo_node",
        "critical-navigation_algo_node-00003--navigation_algo_node",
        "critical-navigation_algo_node-00004--navigation_algo_node",
        "critical-navigation_algo_node-00005--navigation_algo_node"
      ],
      "analysis_mode": "openai_llm_agent",
      "defect_type": "Critical Deadline Miss",
      "evidence": [
        {
          "file": "trace_summary.json"
        },
        {
          "file": "selected_trace_windows",
          "windows": [
            {
              "agent_runnable_nodes": [
                "agent-caption-pipeline-00018000-001--image_captioning"
              ],
              "agent_selected_nodes": [
                "agent-caption-pipeline-00018000-001--image_captioning"
              ],
              "center_timestamp_us": 28571,
              "critical_runnable_nodes": [
                "critical-localization_node-00001--localization_node",
                "critical-localization_node-00002--localization_node",
                "critical-localization_node-00003--localization_node",
                "critical-localization_node-00004--localization_node",
                "critical-navigation_algo_node-00001--navigation_algo_node",
                "critical-navigation_algo_node-00002--navigation_algo_node",
                "critical-navigation_algo_node-00003--navigation_algo_node",
                "critical-pointcloud_to_laserscan_node-00001--pointcloud_to_laserscan_node",
                "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node"
              ],
              "critical_selected_nodes": [
                "critical-localization_node-00001--localization_node",
                "critical-localization_node-00002--localization_node",
                "critical-localization_node-00003--localization_node",
                "critical-localization_node-00004--localization_node",
                "critical-navigation_algo_node-00001--navigation_algo_node",
                "critical-navigation_algo_node-00002--navigation_algo_node",
                "critical-navigation_algo_node-00003--navigation_algo_node",
                "critical-pointcloud_to_laserscan_node-00001--pointcloud_to_laserscan_node",
                "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node"
              ],
              "end_timestamp_us": 78571,
              "max_cpu_utilization": 0.8875,
              "max_gpu_utilization": 0.375,
              "reason": "critical_deadline_miss",
              "running_agent_nodes": [
                "agent-caption-pipeline-00018000-001--image_captioning"
              ],
              "start_timestamp_us": 0,
              "target_node_id": "navigation_algo_node",
              "target_node_instance_id": "critical-navigation_algo_node-00001--navigation_algo_node"
            },
            {
              "agent_runnable_nodes": [
                "agent-caption-pipeline-00018000-001--image_captioning"
              ],
              "agent_selected_nodes": [
                "agent-caption-pipeline-00018000-001--image_captioning"
              ],
              "center_timestamp_us": 57571,
              "critical_runnable_nodes": [
                "critical-localization_node-00002--localization_node",
                "critical-localization_node-00003--localization_node",
                "critical-localization_node-00004--localization_node",
                "critical-localization_node-00005--localization_node",
                "critical-localization_node-00006--localization_node",
                "critical-navigation_algo_node-00002--navigation_algo_node",
                "critical-navigation_algo_node-00003--navigation_algo_node",
                "critical-navigation_algo_node-00004--navigation_algo_node",
                "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node",
                "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node"
              ],
              "critical_selected_nodes": [
                "critical-localization_node-00002--localization_node",
                "critical-localization_node-00003--localization_node",
                "critical-localization_node-00004--localization_node",
                "critical-localization_node-00005--localization_node",
                "critical-localization_node-00006--localization_node",
                "critical-navigation_algo_node-00002--navigation_algo_node",
                "critical-navigation_algo_node-00003--navigation_algo_node",
                "critical-navigation_algo_node-00004--navigation_algo_node",
                "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node",
                "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node"
              ],
              "end_timestamp_us": 107571,
              "max_cpu_utilization": 0.8875,
              "max_gpu_utilization": 0.375,
              "reason": "critical_deadline_miss",
              "running_agent_nodes": [
                "agent-caption-pipeline-00018000-001--image_captioning"
              ],
              "start_timestamp_us": 7571,
              "target_node_id": "navigation_algo_node",
              "target_node_instance_id": "critical-navigation_algo_node-00002--navigation_algo_node"
            },
            {
              "agent_runnable_nodes": [],
              "agent_selected_nodes": [],
              "center_timestamp_us": 86571,
              "critical_runnable_nodes": [
                "critical-localization_node-00003--localization_node",
                "critical-localization_node-00004--localization_node",
                "critical-localization_node-00005--localization_node",
                "critical-localization_node-00006--localization_node",
                "critical-localization_node-00007--localization_node",
                "critical-navigation_algo_node-00003--navigation_algo_node",
                "critical-navigation_algo_node-00004--navigation_algo_node",
                "critical-navigation_algo_node-00005--navigation_algo_node",
                "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node",
                "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node"
              ],
              "critical_selected_nodes": [
                "critical-localization_node-00003--localization_node",
                "critical-localization_node-00004--localization_node",
                "critical-localization_node-00005--localization_node",
                "critical-localization_node-00006--localization_node",
                "critical-localization_node-00007--localization_node",
                "critical-navigation_algo_node-00003--navigation_algo_node",
                "critical-navigation_algo_node-00004--navigation_algo_node",
                "critical-navigation_algo_node-00005--navigation_algo_node",
                "critical-pointcloud_to_laserscan_node-00002--pointcloud_to_laserscan_node",
                "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node"
              ],
              "end_timestamp_us": 136571,
              "max_cpu_utilization": 0.9475,
              "max_gpu_utilization": 0.375,
              "reason": "critical_deadline_miss",
              "running_agent_nodes": [
                "agent-caption-pipeline-00018000-001--image_captioning"
              ],
              "start_timestamp_us": 36571,
              "target_node_id": "navigation_algo_node",
              "target_node_instance_id": "critical-navigation_algo_node-00003--navigation_algo_node"
            },
            {
              "agent_runnable_nodes": [],
              "agent_selected_nodes": [],
              "center_timestamp_us": 114571,
              "critical_runnable_nodes": [
                "critical-localization_node-00005--localization_node",
                "critical-localization_node-00006--localization_node",
                "critical-localization_node-00007--localization_node",
                "critical-localization_node-00008--localization_node",
                "critical-localization_node-00009--localization_node",
                "critical-navigation_algo_node-00004--navigation_algo_node",
                "critical-navigation_algo_node-00005--navigation_algo_node",
                "critical-navigation_algo_node-00006--navigation_algo_node",
                "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node",
                "critical-pointcloud_to_laserscan_node-00004--pointcloud_to_laserscan_node"
              ],
              "critical_selected_nodes": [
                "critical-localization_node-00005--localization_node",
                "critical-localization_node-00006--localization_node",
                "critical-localization_node-00007--localization_node",
                "critical-localization_node-00008--localization_node",
                "critical-localization_node-00009--localization_node",
                "critical-navigation_algo_node-00004--navigation_algo_node",
                "critical-navigation_algo_node-00005--navigation_algo_node",
                "critical-navigation_algo_node-00006--navigation_algo_node",
                "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node",
                "critical-pointcloud_to_laserscan_node-00004--pointcloud_to_laserscan_node"
              ],
              "end_timestamp_us": 164571,
              "max_cpu_utilization": 0.9475,
              "max_gpu_utilization": 0.375,
              "reason": "critical_deadline_miss",
              "running_agent_nodes": [
                "agent-caption-pipeline-00018000-001--image_captioning"
              ],
              "start_timestamp_us": 64571,
              "target_node_id": "navigation_algo_node",
              "target_node_instance_id": "critical-navigation_algo_node-00004--navigation_algo_node"
            },
            {
              "agent_runnable_nodes": [],
              "agent_selected_nodes": [],
              "center_timestamp_us": 143571,
              "critical_runnable_nodes": [
                "critical-localization_node-00006--localization_node",
                "critical-localization_node-00007--localization_node",
                "critical-localization_node-00008--localization_node",
                "critical-localization_node-00009--localization_node",
                "critical-localization_node-00010--localization_node",
                "critical-navigation_algo_node-00005--navigation_algo_node",
                "critical-navigation_algo_node-00006--navigation_algo_node",
                "critical-navigation_algo_node-00007--navigation_algo_node",
                "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node",
                "critical-pointcloud_to_laserscan_node-00004--pointcloud_to_laserscan_node"
              ],
              "critical_selected_nodes": [
                "critical-localization_node-00006--localization_node",
                "critical-localization_node-00007--localization_node",
                "critical-localization_node-00008--localization_node",
                "critical-localization_node-00009--localization_node",
                "critical-localization_node-00010--localization_node",
                "critical-navigation_algo_node-00005--navigation_algo_node",
                "critical-navigation_algo_node-00006--navigation_algo_node",
                "critical-navigation_algo_node-00007--navigation_algo_node",
                "critical-pointcloud_to_laserscan_node-00003--pointcloud_to_laserscan_node",
                "critical-pointcloud_to_laserscan_node-00004--pointcloud_to_laserscan_node"
              ],
              "end_timestamp_us": 193571,
              "max_cpu_utilization": 0.9475,
              "max_gpu_utilization": 0.375,
              "reason": "critical_deadline_miss",
              "running_agent_nodes": [
                "agent-caption-pipeline-00018000-001--image_captioning"
              ],
              "start_timestamp_us": 93571,
              "target_node_id": "navigation_algo_node",
              "target_node_instance_id": "critical-navigation_algo_node-00005--navigation_algo_node"
            }
          ]
        }
      ],
      "natural_language_advice": "To mitigate deadline misses, isolate the critical navigation_algo_node onto a dedicated CPU core or reduce the scheduling priority of the agent-caption-pipeline task. Consider implementing priority-based preemption or allocating more CPU resources to the critical task during high-utilization periods.",
      "root_cause_hypothesis": "The navigation_algo_node is consistently missing deadlines due to high CPU utilization (up to 94.75%) and contention for resources, likely caused by concurrent execution of the non-critical agent-caption-pipeline task which is also running on the same system.",
      "severity": "High"
    }
  ],
  "workload_signature": {
    "agent_arrival_density": 0.75,
    "agent_release_count": 3,
    "agent_request_count": 1,
    "avg_agent_completion_time_us": 2986000,
    "avg_cpu_utilization": 0.5475593750000001,
    "avg_critical_period_us": 32857,
    "avg_gpu_utilization": 0.2175,
    "cpu_capacity": 4.0,
    "critical_deadline_miss_rate": 0.23809523809523808,
    "critical_node_count": 3,
    "gpu_capacity": 2048,
    "high_criticality_node_count": 2,
    "memory_capacity": 4096,
    "min_critical_period_us": 20000,
    "network_capacity": 100.0,
    "scenario_name": "home_eqa_scenario_001",
    "scenario_path": "/home/dawnat9/code-workspace/ai4heuristic/agent4scheduler/configs/scenarios/home_eqa_scenario_001.yaml",
    "scene_complexity": "large"
  }
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
