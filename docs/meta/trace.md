# trace 记录原则

把 trace 设计成 **可回放、可归因、可进化 scheduler** 的记录，

> trace 必须能回答：当时系统看到了什么？scheduler 做了什么决定？runtime 实际发生了什么？这个决定对关键任务和 Agent 任务造成了什么影响？

因此 trace 至少要分成四类信息：

1. **输入状态**：系统当时有什么任务、资源、DAG、依赖、频率要求。
2. **调度决策**：scheduler 选择了哪些 node，给了多少资源，为什么被接受或拒绝。
3. **执行结果**：runtime 中 node 实际执行了多久，资源是否竞争，是否产生惩罚。
4. **任务级结果**：关键任务是否满足频率 / deadline，非关键任务链路完成得多快。

---

## 1. 实验与系统元信息 trace

这部分用于保证 trace 可复现。

建议记录为 `experiment_meta.json`。

```json
{
  "experiment_id": "exp_001",
  "scenario_id": "home_eqa_001",
  "start_time_us": 0,
  "simulator_version": "0.1.0",
  "scheduler_name": "heuristic_scheduler_v3",
  "scheduler_version": "2026_05_02_a",
  "latency_model_version": "latency_model_v1",
  "random_seed": 42,

  "system_capacity": {
    "cpu_cores": 16,
    "memory_mb": 32768,
    "gpu_vram_mb": 24576,
    "network_mbps": 1000
  }
}
```

这一类信息主要用于离线回放时确认：同一个 workload、同一个 scheduler、同一个 latency model 下，是否能复现相同执行结果。
同时作为实验数据管理的元信息。

---

## 2. Task / DAG 定义 trace

这部分记录 workload 本身，尤其是关键 task 和 Agent task 的结构差异。

建议记录为 `task_definition.jsonl`。

### 关键 task

关键 task 的重点是：**周期、频率、deadline、链路结构、每个 node 的资源需求范围**。

```json
{
  "event_type": "task_definition",
  "task_id": "safe_navigation_app",
  "task_type": "critical",

  "nodes": [
    {
      "node_id": "local_planner_node",
      "node_name": "local_planner",
      "process_name": "local_planner_proc",
      "period_us": 50000,
      "deadline_us": 50000,
      "criticality": "high",
      "resource_min": {
        "cpu_cores": 1,
        "memory_mb": 512,
        "gpu_vram_mb": 0,
        "network_mbps": 0
      },
      "resource_default": {
        "cpu_cores": 2,
        "memory_mb": 1024,
        "gpu_vram_mb": 0,
        "network_mbps": 0
      }
    }
  ],

  "edges": [
    {
      "src": "sensor_input_node",
      "dst": "local_planner_node",
    },
    {
      "src": "local_planner_node",
      "dst": "controller_node",
    }
  ]
}
```

### Agent Task

Agent Task 的重点是：**DAG 结构、依赖关系、工具调用、输入规模、完成时间**。

```json
{
  "event_type": "task_definition",
  "app_id": "agent_task_017",
  "app_type": "agent",
  "release_policy": "arrival",
  "user_request": "What objects are on the table?",

  "nodes": [
    {
      "node_id": "n1",
      "tool_name": "object_detection",
      "input_size": "image_720p",
      "can_remote": false,
      "resource_options": [
        {
          "cpu_cores": 2,
          "memory_mb": 2048,
          "gpu_vram_mb": 4096,
          "network_mbps": 0
        },
        {
          "cpu_cores": 4,
          "memory_mb": 4096,
          "gpu_vram_mb": 8192,
          "network_mbps": 0
        }
      ]
    },
    {
      "node_id": "n2",
      "tool_name": "caption_reasoning",
      "input_size": "short_text",
      "is_remote": true,
      "resource_options": [
        {
          "cpu_cores": 0,
          "memory_mb": 0,
          "gpu_vram_mb": 0,
          "network_mbps": 50
        }
      ]
    }
  ],

  "edges": [
    {
      "src": "n1",
      "dst": "n2",
      "edge_type": "data"
    }
  ]
}
```

---

## 3. Workload 释放事件 trace

这一部分记录任务什么时候进入系统。

建议记录为 `workload_events.jsonl`。

```json
{
  "event_type": "app_arrival",
  "timestamp_us": 1200000,
  "app_id": "agent_task_017",
  "app_type": "agent",
  "source": "online_planning_agent"
}
```

关键任务周期释放可以这样记录：

```json
{
  "event_type": "periodic_node_release",
  "timestamp_us": 1500000,
  "app_id": "safe_navigation_app",
  "node_id": "local_planner_node",
  "release_seq": 31,
  "period_us": 50000,
  "deadline_us": 1550000
}
```

这很重要，因为后续判断 deadline miss 时，需要知道每个周期实例的 release time 和 deadline。

---

## 4. Scheduler 观测输入 trace

这是离线进化 scheduler 最重要的数据之一。

它记录的是：**scheduler 当时看到的系统状态是什么**。

建议记录为 `scheduler_observation.jsonl`。

```json
{
  "event_type": "scheduler_observation",
  "timestamp_us": 1500000,
  "decision_id": "dec_000321",

  "runnable_nodes": [
    {
      "app_id": "safe_navigation_app",
      "node_id": "local_planner_node",
      "criticality": "high",
      "deadline_us": 1550000,
      "waiting_time_us": 0
    },
    {
      "app_id": "agent_task_017",
      "node_id": "n1",
      "criticality": "low",
      "dependencies_satisfied": true,
      "waiting_time_us": 200000
    }
  ],

  "running_nodes": [
    {
      "app_id": "agent_task_016",
      "node_id": "m2",
      "start_time_us": 1430000,
      "allocated_resource": {
        "cpu_cores": 4,
        "memory_mb": 4096,
        "gpu_vram_mb": 8192,
        "network_mbps": 0
      }
    }
  ],

  "resource_state": {
    "cpu_cores_total": 16,
    "cpu_cores_used": 8,
    "memory_mb_total": 32768,
    "memory_mb_used": 12288,
    "gpu_vram_mb_total": 24576,
    "gpu_vram_mb_used": 8192,
    "network_mbps_total": 1000,
    "network_mbps_used": 100
  }
}
```

这部分的作用是让离线 agent 能学习：

> 在这种状态下，原 scheduler 做了什么？这个决定好不好？有没有更好的替代方案？

---

## 5. Scheduler 决策 trace

这部分记录 scheduler 的输出，也就是它决定要运行什么 node，以及给多少资源。

建议记录为 `scheduler_decision.jsonl`。

```json
{
  "event_type": "scheduler_decision",
  "timestamp_us": 1500100,
  "decision_id": "dec_000321",
  "scheduler_name": "heuristic_scheduler_v3",

  "actions": [
    {
      "action_type": "launch_node",
      "app_id": "safe_navigation_app",
      "node_id": "local_planner_node",
      "resource_request": {
        "cpu_cores": 2,
        "memory_mb": 1024,
        "gpu_vram_mb": 0,
        "network_mbps": 0
      },
      "priority": 100
    },
    {
      "action_type": "defer_node",
      "app_id": "agent_task_017",
      "node_id": "n1",
      "reason": "insufficient_gpu_vram_after_critical_reservation"
    }
  ]
}
```

建议保留 `reason` 字段，即使一开始是规则 scheduler，也可以记录简单原因。后续离线进化 scheduler 时，这个字段可以帮助分析策略行为。

---

## 6. Control Plane 执行结果 trace

scheduler 的决策不一定能被 runtime 接受。中间还有 control plane。

它需要记录：

* action 是否被接受；
* 是否被 clamp；
* 是否被拒绝；
* 是否被延迟；
* 是否因为资源不足被改写；
* 是否触发 fallback。

建议记录为 `control_plane_events.jsonl`。

```json
{
  "event_type": "control_plane_event",
  "timestamp_us": 1500200,
  "decision_id": "dec_000321",
  "action_id": "act_000321_0",

  "app_id": "safe_navigation_app",
  "node_id": "local_planner_node",

  "status": "accepted",
  "requested_resource": {
    "cpu_cores": 2,
    "memory_mb": 1024,
    "gpu_vram_mb": 0,
    "network_mbps": 0
  },
  "granted_resource": {
    "cpu_cores": 2,
    "memory_mb": 1024,
    "gpu_vram_mb": 0,
    "network_mbps": 0
  }
}
```

如果发生资源 clamp：

```json
{
  "event_type": "control_plane_event",
  "timestamp_us": 1500200,
  "decision_id": "dec_000322",
  "action_id": "act_000322_1",

  "app_id": "agent_task_017",
  "node_id": "n1",

  "status": "clamped",
  "reason": "gpu_vram_exceeds_available_capacity",

  "requested_resource": {
    "cpu_cores": 4,
    "memory_mb": 4096,
    "gpu_vram_mb": 12000,
    "network_mbps": 0
  },
  "granted_resource": {
    "cpu_cores": 4,
    "memory_mb": 4096,
    "gpu_vram_mb": 8192,
    "network_mbps": 0
  }
}
```

这一层非常关键，因为它区分了：

> scheduler 想做什么
> 系统实际允许它做什么

这对离线归因非常重要。

---

## 7. Runtime 执行事件 trace

这是最核心的执行层 trace。

建议记录为 `runtime_node_events.jsonl`。

### node start

```json
{
  "event_type": "node_start",
  "timestamp_us": 1500300,
  "run_id": "run_local_planner_31",

  "app_id": "safe_navigation_app",
  "node_id": "local_planner_node",
  "release_seq": 31,

  "allocated_resource": {
    "cpu_cores": 2,
    "memory_mb": 1024,
    "gpu_vram_mb": 0,
    "network_mbps": 0
  },

  "runtime_context": {
    "concurrent_nodes": [
      {
        "app_id": "agent_task_016",
        "node_id": "m2"
      }
    ],
    "resource_contention": {
      "cpu_overcommit_ratio": 1.0,
      "memory_pressure_ratio": 0.72,
      "gpu_vram_pressure_ratio": 0.33,
      "network_pressure_ratio": 0.10
    }
  }
}
```

### node finish

```json
{
  "event_type": "node_finish",
  "timestamp_us": 1539000,
  "run_id": "run_local_planner_31",

  "app_id": "safe_navigation_app",
  "node_id": "local_planner_node",
  "release_seq": 31,

  "start_time_us": 1500300,
  "finish_time_us": 1539000,
  "latency_us": 38700,

  "latency_breakdown": {
    "base_latency_us": 32000,
    "resource_config_penalty_us": 4000,
    "contention_penalty_us": 2700,
    "network_penalty_us": 0
  },

  "status": "succeeded"
}
```

如果失败：

```json
{
  "event_type": "node_finish",
  "timestamp_us": 2300000,
  "run_id": "run_object_detection_017",

  "app_id": "agent_task_017",
  "node_id": "n1",

  "start_time_us": 1800000,
  "finish_time_us": 2300000,
  "latency_us": 500000,

  "status": "failed",
  "failure_reason": "oom"
}
```

---

## 8. 资源快照 trace

除了 node 级别事件，还需要周期性记录全局资源状态，方便分析竞争过程。

建议记录为 `resource_snapshots.jsonl`。

```json
{
  "event_type": "resource_snapshot",
  "timestamp_us": 1520000,

  "resource_usage": {
    "cpu_cores_used": 12,
    "cpu_cores_total": 16,

    "memory_mb_used": 18432,
    "memory_mb_total": 32768,

    "gpu_vram_mb_used": 16384,
    "gpu_vram_mb_total": 24576,

    "network_mbps_used": 250,
    "network_mbps_total": 1000
  },

  "pressure": {
    "cpu_pressure": 0.75,
    "memory_pressure": 0.56,
    "gpu_vram_pressure": 0.67,
    "network_pressure": 0.25
  }
}
```

这部分用于观察系统是否长期处于高压状态，以及 scheduler 是否过于保守或过于激进。

---

## 9. 竞争惩罚 trace

你特别提到：

> 上层没有良好约束时，需要考虑回退竞争问题，即发生竞争是有竞争惩罚。

所以建议单独记录 `contention_events.jsonl`。

```json
{
  "event_type": "contention_event",
  "timestamp_us": 1520000,

  "affected_run_id": "run_object_detection_017",
  "app_id": "agent_task_017",
  "node_id": "n1",

  "contention_type": "gpu_vram_pressure",
  "resource": "gpu_vram",

  "expected_usage": 8192,
  "actual_available": 4096,
  "pressure_ratio": 1.35,

  "penalty": {
    "latency_multiplier": 1.42,
    "extra_latency_us": 120000
  },

  "competing_nodes": [
    {
      "app_id": "agent_task_016",
      "node_id": "m2"
    },
    {
      "app_id": "agent_task_018",
      "node_id": "k1"
    }
  ]
}
```

这个 trace 对离线 scheduler 进化非常重要，因为它能告诉 agent：

> 哪些调度决策导致了资源竞争？竞争发生在哪类资源？对哪个 node 造成了多大惩罚？

---

## 10. 关键任务周期执行 trace

关键任务不应该只记录 node start / finish，还应该专门记录周期级指标。

建议记录为 `critical_node_cycles.jsonl`。

```json
{
  "event_type": "critical_cycle",
  "app_id": "safe_navigation_app",
  "node_id": "local_planner_node",
  "release_seq": 31,

  "release_time_us": 1500000,
  "start_time_us": 1500300,
  "finish_time_us": 1539000,
  "deadline_us": 1550000,

  "period_us": 50000,
  "response_time_us": 39000,
  "deadline_miss": false,
  "jitter_us": 300,

  "allocated_resource": {
    "cpu_cores": 2,
    "memory_mb": 1024,
    "gpu_vram_mb": 0,
    "network_mbps": 0
  }
}
```

如果 deadline miss：

```json
{
  "event_type": "critical_cycle",
  "app_id": "safe_navigation_app",
  "node_id": "controller_node",
  "release_seq": 102,

  "release_time_us": 2000000,
  "start_time_us": 2012000,
  "finish_time_us": 2027000,
  "deadline_us": 2020000,

  "period_us": 20000,
  "response_time_us": 27000,
  "deadline_miss": true,
  "deadline_miss_us": 7000,
  "jitter_us": 12000
}
```

这里建议以 **node 周期实例** 作为关键任务的最小记录粒度，因为你的设定里每个关键 node 都可能有自己的频率要求。

---

## 11. Agent 任务 DAG 进度 trace

非关键任务关注的是整条链路的完成速度，所以需要记录 DAG 级别状态。

建议记录为 `agent_task_progress.jsonl`。

```json
{
  "event_type": "agent_task_progress",
  "timestamp_us": 2400000,
  "app_id": "agent_task_017",

  "dag_status": {
    "total_nodes": 4,
    "finished_nodes": 2,
    "running_nodes": 1,
    "ready_nodes": 1,
    "blocked_nodes": 0
  },

  "critical_path_estimate_us": 780000,
  "elapsed_time_us": 1200000
}
```

任务完成时记录：

```json
{
  "event_type": "agent_task_finish",
  "timestamp_us": 3100000,
  "app_id": "agent_task_017",

  "arrival_time_us": 1200000,
  "finish_time_us": 3100000,
  "makespan_us": 1900000,

  "status": "succeeded",
  "num_nodes": 4,
  "num_failed_nodes": 0,
  "num_retries": 0
}
```

这部分用于评估：

* Agent 任务平均完成时间；
* p95 完成时间；
* DAG 中哪些 node 经常成为瓶颈；
* scheduler 是否过度偏向关键任务，导致 Agent 任务长期饥饿。

---

## 12. Latency Model 调用 trace

因为你的 runtime 是模拟执行，latency 不是实际运行出来的，而是由 latency 计算组件估算出来的，所以建议记录每次 latency model 的输入和输出。

建议记录为 `latency_model_calls.jsonl`。

```json
{
  "event_type": "latency_model_call",
  "timestamp_us": 1500250,
  "run_id": "run_object_detection_017",

  "node_name": "object_detection",
  "input_size": "image_720p",

  "resource_config": {
    "cpu_cores": 4,
    "memory_mb": 4096,
    "gpu_vram_mb": 8192,
    "network_mbps": 0
  },

  "contention_context": {
    "cpu_pressure": 0.75,
    "memory_pressure": 0.56,
    "gpu_vram_pressure": 0.67,
    "network_pressure": 0.25
  },

  "latency_result": {
    "base_latency_us": 450000,
    "predicted_latency_us": 630000,
    "latency_multiplier": 1.4
  }
}
```

这有两个好处：

1. 方便 debug latency model 是否合理；
2. 离线进化 scheduler 时，可以学习资源配置与 latency 变化的关系。

---

## 13. 建议的 trace 文件组织

可以先不要做得太复杂，建议采用 JSONL，每行一个事件。

```text
traces/
├── experiment_meta.json
├── app_definition.jsonl
├── workload_events.jsonl
├── scheduler_observation.jsonl
├── scheduler_decision.jsonl
├── control_plane_events.jsonl
├── runtime_node_events.jsonl
├── resource_snapshots.jsonl
├── contention_events.jsonl
├── critical_node_cycles.jsonl
├── agent_task_progress.jsonl
├── latency_model_calls.jsonl
└── summary_metrics.json
```

如果想简化，第一版可以合并成 4 个核心文件：

```text
traces/
├── experiment_meta.json
├── workload_trace.jsonl
├── scheduler_trace.jsonl
├── runtime_trace.jsonl
└── summary_metrics.json
```

其中：

* `workload_trace.jsonl`：记录 app、DAG、任务释放；
* `scheduler_trace.jsonl`：记录 observation、decision、control plane response；
* `runtime_trace.jsonl`：记录 node start、node finish、resource snapshot、contention event；
* `summary_metrics.json`：记录最终指标。

---

## 14. 最终 summary metrics

每次实验结束后，建议生成一个汇总文件 `summary_metrics.json`。

```json
{
  "experiment_id": "exp_001",

  "critical_metrics": {
    "total_cycles": 10000,
    "deadline_miss_count": 12,
    "deadline_miss_rate": 0.0012,
    "avg_response_time_us": 18300,
    "p95_response_time_us": 42100,
    "p99_response_time_us": 48700,
    "max_response_time_us": 61200
  },

  "agent_metrics": {
    "num_agent_tasks": 100,
    "completed_tasks": 96,
    "failed_tasks": 4,
    "avg_makespan_us": 2100000,
    "p95_makespan_us": 5300000,
    "avg_waiting_time_us": 620000
  },

  "resource_metrics": {
    "avg_cpu_utilization": 0.68,
    "avg_memory_utilization": 0.51,
    "avg_gpu_vram_utilization": 0.74,
    "avg_network_utilization": 0.22,

    "cpu_overcommit_events": 8,
    "memory_pressure_events": 3,
    "gpu_vram_pressure_events": 14,
    "network_pressure_events": 2
  },

  "scheduler_metrics": {
    "num_decisions": 3200,
    "num_actions": 5400,
    "num_rejected_actions": 17,
    "num_clamped_actions": 42,
    "num_deferred_agent_nodes": 380
  }
}
```

---

## 15. 第一版最小必要 trace

如果你现在要先实现模拟器，我建议最小闭环先记录这些：

| 类型                    | 必须记录                                               |
| --------------------- | -------------------------------------------------- |
| 实验配置                  | 系统资源总量、scheduler 版本、latency model 版本、random seed   |
| workload              | app_id、app_type、DAG、node 资源选项、关键 node 周期和 deadline |
| scheduler observation | runnable nodes、running nodes、当前资源状态                |
| scheduler decision    | 选择运行哪些 node、分配多少资源、defer 哪些 node                   |
| control plane         | accepted / rejected / clamped，以及原因                 |
| runtime               | node start、node finish、latency、status、失败原因         |
| resource              | 每个时间窗口的资源使用率                                       |
| contention            | 竞争资源、竞争节点、latency penalty                          |
| critical result       | 每个周期是否 deadline miss                               |
| agent result          | 每个 Agent DAG 的 makespan                            |

最重要的是这条链路：

```text
workload release
→ scheduler observation
→ scheduler decision
→ control plane response
→ runtime execution
→ node finish / deadline miss / DAG finish
```

只要这条链路完整，后面离线 scheduler 进化就有数据基础。

---

## 16. 推荐的核心事件模型

最后可以抽象成统一事件格式：

```json
{
  "timestamp_us": 1500000,
  "event_type": "...",
  "experiment_id": "exp_001",
  "app_id": "...",
  "node_id": "...",
  "payload": {}
}
```

这样新增事件类型会比较容易。

我建议第一版重点实现以下 8 类事件：

```text
app_arrival
node_release
scheduler_observation
scheduler_decision
control_plane_event
node_start
node_finish
resource_snapshot
```

然后第二版再补充：

```text
contention_event
critical_cycle
agent_task_progress
latency_model_call
```

这样实现负担不会太大，但 trace 语义是完整的。
