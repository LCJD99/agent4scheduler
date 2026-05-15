# Offline Scheduler Evolution

1. 生成或选择 trace

   在线仿真先运行一个场景，输出可回放的 trace 目录。该目录包含实验元数据、任务定义、调度观测、调度决策、运行时执行、任务结果和汇总指标。离线流程以这个 trace 目录作为输入。

2. 加载 trace 与 workload 信息

   `offline.graph` 负责串联离线流程。`offline.analysis.workload_profiler` 从 trace 中提取 workload 特征，例如场景复杂度、关键任务数量、agent 请求数量、资源压力和任务完成指标。

3. 检索历史相似 workload

   `offline.memory` 负责保存历史 trace、workload 签名、候选 scheduler 和 replay 结果。`WorkloadIndex` 根据当前 workload 签名检索相似历史案例，为后续进化提供参考。

4. 分析当前 scheduler 缺陷

   `offline.analysis.trace_analyzer` 读取 trace summary 和关键 trace window，并调用配置的 LLM 分析器生成 scheduler 缺陷报告。报告描述 deadline miss、资源竞争、agent 启动时机、starvation 等问题及对应 trace 证据。

5. 生成进化建议分支

   `offline.analysis.advice` 将 workload 特征、缺陷报告和相似历史案例整理成多个 advice branch。每个分支描述一个候选进化方向，例如关键任务资源预留、agent starvation boost 或资源压力下的 agent 限流。

6. 生成候选 scheduler 代码

   `offline.evolution` 将 advice branch、workload 签名、trace findings、历史案例、scheduler 接口协议和执行约束作为上下文交给 LLM。LLM 返回候选 scheduler 源码、设计理由和满足的约束列表。离线模块会先校验源码是否符合 scheduler 接口和安全约束。

7. replay 候选 scheduler

   `offline.replay.runner` 将候选 scheduler 写成 `scheduler_candidate.py`，并调用在线 simulator 以相同场景重新运行。replay 输出新的 trace run，用于和 baseline trace 对比。

8. 评估候选结果

   `offline.replay.evaluator` 对比 baseline trace 和候选 replay trace。评估重点包括关键任务 deadline miss、agent 任务完成延迟和候选是否满足接受条件。

9. 选择候选 scheduler

   离线流程根据评估分数选择最佳候选。若候选未改善关键指标，结果仍会被记录，供后续分析和下一轮进化使用。

10. 持久化离线记忆

    `offline.memory.trace_store` 将本轮 workload 签名、trace findings、advice branches、候选 scheduler、replay 结果和 selected candidate 写入本地记忆库。最终结果同时输出到 `offline_evolution_result.json`。

11. 人工审查与部署

    离线流程只负责生成、验证和评估候选 scheduler。是否将候选 scheduler 合入在线系统或作为新的默认 scheduler，需要人工审查后显式执行。
