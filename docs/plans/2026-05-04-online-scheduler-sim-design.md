# Online Scheduler Sim Design

**Date:** 2026-05-04

**Source Inputs:**
- `docs/meta/need.md`
- `docs/meta/config.md`
- `docs/meta/trace.md`

## 1. Goal

本设计定义一个仅覆盖在线阶段的调度模拟器，用于验证如下问题：

- 在已知 Agent 任务 DAG 的前提下，如何在保证关键任务频率和安全执行的情况下，尽可能快地完成 Agent 任务链路。
- 如何在多资源受限场景下，模拟 scheduler 决策、资源竞争、回退惩罚和任务完成结果。
- 如何稳定输出可分析的 trace，为后续离线 scheduler 进化预留兼容接口，但本版本不实现任何离线能力。

## 2. Scope

### In Scope

- 在线 workload 生成
- 在线模板化工具规划 Agent
- 基于固定时间步的 runtime 推进
- latency 计算与 contention penalty
- scheduler 与 control plane 解耦
- trace 输出
- 配置驱动启动仿真

### Out of Scope

- 离线 scheduler 训练、进化、回放
- 真实大模型工具规划
- 参数级工具调用语义
- 跨机部署、真实 cgroup 或 OS 级资源控制
- 运行中硬抢占迁移

## 3. Assumptions

- 首版只做在线系统，所有接口设计以在线闭环完整性优先。
- 仿真时间模型采用固定时间步推进，不采用离散事件驱动。
- scheduler 在每个 tick 与 runtime 同步一次，形成单一决策节拍。
- critical task 的约束以周期释放和 deadline 检查表达。
- agent task 由在线规划 Agent 直接生成 DAG 实例，首版采用模板或规则映射，不做复杂推理。
- node 是最小调度单元，资源限制作用于 node 级别。
- 首版允许 agent node 延后启动或暂停进入运行，不支持运行中硬抢占。

## 4. Recommended Architecture

### 4.1 High-Level Flow

每个仿真 tick 执行固定顺序：

1. `WorkloadGenerator` 释放新任务实例
2. `Runtime` 汇总当前系统状态
3. `Scheduler` 基于 observation 生成决策
4. `SchedulerControlPlane` 应用决策
5. `Runtime` 推进一个 tick，结算执行进度和竞争惩罚
6. `TraceMonitor` 记录本 tick 的观测、决策、执行结果与任务结果

### 4.2 Components

#### ScenarioLoader

负责读取并校验以下配置：

- `configs/tools/*.yaml`
- `configs/tasks/*.yaml`
- `configs/scenarios/*.yaml`

输出统一的内存模型，供后续所有组件引用。

#### ToolRegistry

维护工具静态元信息：

- tool / node 名称
- implementation 列表
- resource profiles
- latency model
- contention model
- selection policy

`OnlinePlanningAgent` 和 `LatencyEstimator` 都通过该注册表查询能力。

#### OnlinePlanningAgent

输入用户请求和可用工具列表，输出一个模板化 DAG：

- DAG 中 node 引用 `ToolSpec`
- edge 表达依赖关系
- 不处理具体参数绑定，只保留输入规模、工具选择和依赖结构

首版实现为 rule-based planner：

- 按请求类型映射到预定义 DAG 模板
- 支持本地工具与远端 API 两类 node

#### WorkloadGenerator

负责生成两类 workload：

- critical task：按周期释放 node instance
- agent task：按 arrival 事件生成整张 DAG，再按依赖逐步暴露 runnable nodes

对 scheduler 暴露的是“当前已 runnable 的 node instances”，而非整个任务定义。

#### Scheduler

职责是基于当下状态做资源配额与选择，不直接驱动 runtime：

- 读取 runnable nodes
- 读取系统剩余资源与运行中节点
- 保障 critical task 最小执行需求
- 使用剩余资源加速 agent DAG
- 选择 implementation / profile
- 生成 defer / reject / degrade 原因

Scheduler 输出结构化 `SchedulerDecision`，由 control plane 落地。

#### SchedulerControlPlane

负责把 scheduler 的意图翻译成 runtime 可执行动作：

- 启动 node
- 更新 node 资源配额
- 标记延后执行
- 记录决策是否被 runtime 接受

这样可以把“调度策略”和“执行机制”解耦，便于后续替换 heuristic scheduler。

#### Runtime

Runtime 负责维护系统真实执行态：

- 运行中节点集合
- 每个节点的剩余工作量
- 当前资源分配与可用余量
- contention penalty
- 完成 / deadline miss / 失败事件

首版 runtime 不需要真实执行进程，只需基于模型推进状态。

#### LatencyEstimator

输入：

- node / tool 名称
- implementation
- profile
- 输入规模
- 当前资源配置
- 当前 contention 状态

输出：

- predicted latency
- per-tick effective progress
- contention penalty multiplier

#### TraceMonitor

按 `docs/meta/trace.md` 定义输出至少以下 trace：

- `experiment_meta.json`
- `task_definition.jsonl`
- `workload_events.jsonl`
- `scheduler_observation.jsonl`
- `scheduler_decision.jsonl`
- `runtime_execution.jsonl`
- `task_outcome.jsonl`

## 5. Time Model

### 5.1 Tick Semantics

定义全局时间：

- `tick_index = 0, 1, 2, ...`
- `timestamp_us = tick_index * tick_us`

建议 scenario 中显式配置 `tick_us`，例如 `1000` 或 `5000` 微秒。

### 5.2 Execution Progress

每个运行中 node 都维护：

- `predicted_total_latency_us`
- `remaining_work_us`
- `effective_progress_us_per_tick`

runtime 在每个 tick 用如下逻辑推进：

`remaining_work_us -= tick_us / penalty_multiplier`

其中 `penalty_multiplier >= 1.0`，由 contention model 决定。

### 5.3 Why Fixed-Step

选择固定时间步而非离散事件驱动，原因是：

- scheduler 与 runtime 观察点严格同步
- easier trace alignment
- 更容易表达“每个 tick 重新分配资源”的控制逻辑
- 更适合首版对比不同 heuristic scheduler

代价是 tick 过大时精度下降，因此必须在 scenario 中显式控制时间粒度。

## 6. Resource and Contention Model

### 6.1 Resource Dimensions

系统统一考虑四类资源：

- `cpu_cores`
- `memory_mb`
- `gpu_vram_mb`
- `network_mbps`

资源模型分两层：

- capacity：系统总容量
- allocation：node 当前获得的配额

### 6.2 Allocation Rule

scheduler 只能分配配置中允许的 profile 或显式资源向量，不能任意超出 `ToolSpec.resources.max`。

### 6.3 Contention Rule

若 runtime 检测到以下任一情况，应引入 penalty：

- 同一时刻分配总和超过系统 capacity
- node 获得低于其有效运行最低要求的资源
- 多个 node 在敏感资源上高度重叠

首版 penalty 建议统一采用乘性惩罚：

`actual_latency = predicted_latency * penalty_multiplier`

其中 multiplier 来源于：

- tool 自身 `contention_model.sensitive_resources`
- 全局超卖比例

## 7. Scheduling Policy Boundary

首版 scheduler 的边界应保持简单、可替换：

- 优先保障 critical task 周期实例
- agent task 只消费剩余资源
- agent node 允许降级 profile
- critical task 不因 agent task 被饿死
- 不做运行中抢占迁移

### Recommended Baseline Heuristic

critical nodes：

- 按最早 deadline 优先
- 至少分配满足任务保底的最小 profile

agent nodes：

- 只在依赖满足后进入 runnable
- 优先级可采用关键路径剩余长度或简单 FIFO
- 先尝试 default profile，不足时降级为 lower profile

## 8. Data Model

建议统一以下核心对象：

### ResourceVector

```text
cpu_cores
memory_mb
gpu_vram_mb
network_mbps
```

### ToolSpec

来自 `docs/meta/config.md` 的单工具定义，包含：

- metadata
- interface
- implementations
- selection_policy
- scheduling
- observability

### TaskSpec

描述一类任务模板：

- task id
- task type
- DAG nodes
- edges
- critical task 的 period / deadline

### TaskInstance

表示一次真实进入系统的任务实例：

- agent request instance
- 或 critical 周期实例

### NodeInstance

最小调度单元，包含：

- node id
- parent task instance
- current state
- dependencies
- selected implementation
- selected profile
- allocated resources
- timing fields

### SchedulerDecision

用于连接 scheduler 和 control plane，包含：

- decision id
- timestamp
- selected nodes
- allocations
- rejected nodes
- degrade / defer reasons

## 9. State Machine

建议 node 生命周期状态统一为：

- `pending`
- `runnable`
- `scheduled`
- `running`
- `completed`
- `failed`
- `dropped`

状态流转：

- dependency satisfied: `pending -> runnable`
- scheduler selected: `runnable -> scheduled`
- control plane accepted: `scheduled -> running`
- runtime finish: `running -> completed`
- unrecoverable error: `running -> failed`
- policy discard: `runnable -> dropped`

## 10. Config Mapping

### Tool Specs

直接复用 `docs/meta/config.md` 的结构，不另起 schema。

### Task Specs

critical task：

- 需要固定 DAG
- node 级周期 / deadline
- 可选保底 profile

agent task template：

- 需要 DAG 模板
- node 引用 tool name
- edge 表达依赖

### Scenario Specs

建议增加以下字段：

- `tick_us`
- `duration_us`
- `system_capacity`
- `critical_tasks`
- `agent_arrivals`
- `random_seed`
- `trace_output_dir`

## 11. Trace Contract

首版 trace 目标不是“最全”，而是“对调度归因闭环足够”。

至少满足三个问题：

- scheduler 当时看到了什么
- scheduler 做了什么决定
- runtime 实际发生了什么以及影响了哪些任务

因此 observation、decision、execution、outcome 四段必须一一对应，可通过 `decision_id`、`node_instance_id` 和 `task_instance_id` 关联。

## 12. Error Handling

首版需要明确区分三类错误：

### Config Errors

- YAML 缺字段
- tool 引用不存在
- DAG 有环
- scenario 引用非法 task

这些错误应在加载阶段直接 fail fast。

### Scheduling Errors

- profile 不可选
- 资源超出 max
- critical 保底无法满足

这些错误应记录到 trace，并返回结构化原因。

### Runtime Errors

- decision 无法应用
- node 在非法状态启动
- 资源结算出现负值

这些错误应终止仿真并给出上下文。

## 13. Testing Strategy

建议测试分四层：

- schema tests：配置解析与校验
- unit tests：latency、contention、state machine
- integration tests：scheduler -> control plane -> runtime 闭环
- scenario tests：一整个小场景 end-to-end 回归

首版至少应覆盖：

- critical task 不被 agent 饥饿
- contention 会放大 latency
- agent DAG 依赖按顺序释放
- trace 文件结构完整

## 14. Recommended Initial File Layout

```text
configs/
  tools/
  tasks/
  scenarios/
src/scheduler_sim/
  config/
  domain/
  planner/
  workload/
  latency/
  runtime/
  scheduler/
  trace/
  app.py
tests/
  config/
  domain/
  planner/
  workload/
  latency/
  runtime/
  scheduler/
  integration/
```

## 15. Implementation Order

推荐落地顺序：

1. 配置 schema 与基础领域模型
2. critical / agent workload 生成
3. fixed-step runtime
4. latency 与 contention
5. baseline scheduler
6. control plane
7. trace 输出
8. end-to-end scenario runner

## 16. Open Decisions Resolved for V1

- 只做在线部分：已确定
- 时间推进采用固定 tick：已确定
- planner 采用模板化 DAG：已确定
- 不做运行中硬抢占：本设计已确定
- 不做离线演化接口实现：只保留 trace 兼容性

## 17. Success Criteria

满足以下条件即可视为首版设计达标：

- 能从配置加载一个完整 scenario
- 能释放 critical task 和 agent task
- 能在 fixed-step runtime 中推进 node 执行
- 能体现 contention penalty
- 能运行一个 baseline scheduler 并生成可分析 trace
- 能回答关键任务是否满足频率，以及 agent task 完成用了多久
