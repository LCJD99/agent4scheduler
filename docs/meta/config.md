# 1. 推荐文件组织

```text
configs/
├── tools/
│   ├── object_detection.yaml
│   ├── caption_reasoning_remote.yaml
│   ├── local_planner_node.yaml
│   ├── controller_node.yaml
│   └── obstacle_avoidance_node.yaml
│
├── tasks/
│   ├── safe_navigation_task.yaml
│   └── agent_tool_registry.yaml
│
└── scenarios/
    └── home_eqa_scenario_001.yaml
```

其中：

```text
tools/*.yaml
```

描述单个 node / tool 的静态属性。

```text
tasks/*.yaml
```

描述一个 app 由哪些 node 组成、边是什么、关键任务频率要求是什么。

```text
scenarios/*.yaml
```

描述实验场景、系统总资源、任务到达模式、随机种子等。

---

# 2. 单个 node / tool YAML 的核心结构

建议统一成如下结构：

所有图片如果使用 api 默认 720p 模拟

```yaml
api_version: sim.tool/v1
kind: ToolSpec

metadata:
  name: object_detection
  display_name: Object Detection
  description: Detect objects from an input image.

interface:
  input_types:
    - image
  output_types:
    - text

implementations:
  - id: local_gpu
    location: local

    resources:
      min:
        cpu_cores: 1
        memory_mb: 1024
        gpu_vram_mb: 2048
        network_mbps: 0

      default:
        cpu_cores: 4
        memory_mb: 4096
        gpu_vram_mb: 8192
        network_mbps: 0

      max:
        cpu_cores: 8
        memory_mb: 8192
        gpu_vram_mb: 12288
        network_mbps: 0

      profiles:
        - name: low
          cpu_cores: 2
          memory_mb: 2048
          gpu_vram_mb: 4096
          network_mbps: 0

        - name: balanced
          cpu_cores: 4
          memory_mb: 4096
          gpu_vram_mb: 8192
          network_mbps: 0

        - name: fast
          cpu_cores: 6
          memory_mb: 6144
          gpu_vram_mb: 10240
          network_mbps: 0

    latency_model:
      type: lookup_table_v1
      unit: us
      table:
        low: 900000
        balanced: 600000
        fast: 430000

    contention_model:
      enabled: true
      sensitive_resources:
        cpu_cores: 0.5
        memory_mb: 0.2
        gpu_vram_mb: 0.9
        network_mbps: 0.0
      penalty:
        type: multiplicative
        max_multiplier: 3.0

  - id: remote_api
    location: remote

    resources:
      min:
        cpu_cores: 0
        memory_mb: 0
        gpu_vram_mb: 0
        network_mbps: 10

      default:
        cpu_cores: 0
        memory_mb: 0
        gpu_vram_mb: 0
        network_mbps: 50

      max:
        cpu_cores: 0
        memory_mb: 0
        gpu_vram_mb: 0
        network_mbps: 200

      profiles:
        - name: slow
          cpu_cores: 0
          memory_mb: 0
          gpu_vram_mb: 0
          network_mbps: 10

        - name: normal
          cpu_cores: 0
          memory_mb: 0
          gpu_vram_mb: 0
          network_mbps: 50

        - name: fast
          cpu_cores: 0
          memory_mb: 0
          gpu_vram_mb: 0
          network_mbps: 100

    latency_model:
      type: remote_api_v1
      unit: us

      base_service_latency_us: 500000

      network_latency:
        include_request_transfer: true
        include_response_transfer: true
        rtt_us: 80000

      jitter:
        enabled: true
        distribution: lognormal
        std_ratio: 0.15

    contention_model:
      enabled: true
      sensitive_resources:
        cpu_cores: 0.0
        memory_mb: 0.0
        gpu_vram_mb: 0.0
        network_mbps: 1.0
      penalty:
        type: multiplicative
        max_multiplier: 5.0

selection_policy:
  selectable_by_scheduler: true

  default_implementation: local_gpu

  candidate_order:
    - local_gpu
    - remote_api

  constraints:
    - if: "input_size_class == image_1080p and gpu_vram_available_mb < 8192"
      prefer: remote_api

    - if: "network_available_mbps < 20"
      avoid: remote_api

    - if: "critical_resource_pressure.gpu_vram > 0.8"
      prefer: remote_api

    - if: "agent_task_deadline_tight == true and network_available_mbps >= 50"
      allow: remote_api

  fallback:
    enabled: true
    on_reject:
      - try_next_implementation
      - degrade_profile
      - defer_node

scheduling:
  default_priority: 10
  can_degrade: true
  starvation_avoidance: true

observability:
  trace_level: detailed
  metrics:
    - selected_implementation
    - selected_profile
    - allocated_resource
    - predicted_latency_us
    - actual_latency_us
    - contention_penalty_us
    - fallback_reason

```


## 3.4 resources：资源需求与可调资源档位

```yaml
resources:
  min:
    cpu_cores: 1
    memory_mb: 1024
    gpu_vram_mb: 2048
    network_mbps: 0

  default:
    cpu_cores: 4
    memory_mb: 4096
    gpu_vram_mb: 8192
    network_mbps: 0

  profiles:
    - name: low
      cpu_cores: 2
      memory_mb: 2048
      gpu_vram_mb: 4096
      network_mbps: 0
```

# 资源配置

这里建议同时支持两种调度方式：

### 方式一：scheduler 选择离散 profile

```yaml
profile: balanced
```

优点是简单，适合第一版。

### 方式二：scheduler 直接给连续资源配置

```yaml
resource_request:
  cpu_cores: 3
  memory_mb: 3072
  gpu_vram_mb: 6144
  network_mbps: 0
```

优点是灵活，适合后续进化 scheduler。

第一版建议先做 `profiles`，后续再支持连续资源配置。

---

## 3.5 latency_model：资源配置如何影响 latency

你这个模拟器的关键就在这里。

建议每个工具都定义自己的 latency model：

```yaml
latency_model:
  type: polynomial_regression_v1
  unit: us
```

可以支持几类模型：

| type                       | 适用场景                      |
| -------------------------- | ------------------------- |
| `lookup_table_v1`          | 少量离散 profile，对应固定 latency |
| `remote_api_v1`            | 远程 API，主要受网络和 API 延迟影响    |
