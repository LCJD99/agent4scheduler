## 任务描述

我们要解决的问题是：在具身智能系统中，机器人一方面必须稳定执行电机控制、局部避障等安全关键任务，保证实时性与安全性；另一方面，又需要响应用户触发的 Agent 类任务，这些任务会进一步调用本地 CPU/GPU 密集工具或远端 API，形成动态到达、资源需求波动大、执行时延不确定的混合 workload。现有方法通常要么只关注关键任务保底，导致大量资源闲置，要么缺乏对这类 Agent 任务链的系统级调度能力。为此，我们的思路是构建一套“在线稳定执行、离线持续演进”的调度框架：在线阶段始终运行一个固定版本的 scheduler，在保证关键任务安全执行的前提下，尽可能利用实时剩余资源服务 Agent 任务；离线阶段持续收集系统 trace、场景状态和任务执行数据，再利用一个专门的 Agent 基于这些历史数据生成和迭代新的启发式 scheduler，经仿真和回放验证后再部署到在线系统中，从而逐步学会在不同场景下实现更高效、更安全的资源配置。

我们的设定是一个硬件系统中有多个 task， task 由多个 node 组成，每个 node 代表一个 进程，node 可以通过 cgroup 的技术约束，task 分为关键 task 和 agent task，关键任务通常有常驻的 频率要求，非关键任务则要求尽可能快的完成任务链路，

存在竞争的资源是 cpu core， memory, gpu vram, 网络带宽，这些资源都可以 node 级别的资源限制，代价就是 会有 latency 的变化

需要实现出这个模拟器，系统可以通过加载配置启动系统剩余资源，对于关键任务有固定链路和固定的频率，非关键任务由 agent 做工具规划，规划出的是 dag 结构的工具调用

目前考虑到的组件有以下

### 在线部分

将上述背景进行问题抽象，实际上该模拟器所做事情是在 已知接下来 Agent 任务的 DAG 图的情况下，如何在保证关键任务执行频率的情况下，尽可能快的执行 Agent 任务

1. 下层的模拟执行层 runtime，这个执行层按照上层 scheduler control plane 发出的任务进行模拟执行，**这里需要考虑上层没有良好约束的回退竞争问题**，即发生竞争是有竞争惩罚
2. 模拟执行层需要利用 latency 计算组件，这个组件输入 node 的名称和相关配置（包括 cpu core, cpu memory, vram, 最高带宽），得到的执行还节点的 latnecy
3. scheduler control plane 用于接受来自 scheduler 的指令流（包括对 node 的选择和资源配置）并真正触发 node 的执行，提交到 runtime
4. scheduler 接受来自上层 task 的任务，以及现在系统中正在执行的 node，以及执行完的 node ，现在系统的资源情况（来自 runtime的数据），然后对新的上层 task 或者尚未完成的 node 进行配额，并形成调度的指令流，传输给 scheduler control plane，真的运行的 scheduler 是 一个离线scheduler 进化 agent 根据 trace 进化出来的，因此只保留调度选择的权利，而不是直接提交系统任务，BaseScheduler 中维护读入 dag 结构的 agent 任务结构，该任务结构 ，即从 workload 生成器中生成，但是没有发出到系统调度的任务，
5. workload 生成器，这里 workload 包括两类，一类是按一定频率发出的关键任务，关键任务中每个 node 有自己满足关键任务需要的频率，对于 agent任务 workload 生成器由 agent 生成的 dag 结构，只向 scheduler 发出满足执行依赖的任务
6. 全局工具注册表管理，这里的工具注册表中的数据会用于 latency计算模块和在线工具规划 agent选择
7. 在线工具规划 agent ，输入用户请求，可用工具 node，输出 json格式的 工具规划 dag，不用考虑参数解析问题
8. trace monitor 模块，这个模块用于观察 runtime，并输出 trace ,trace 具体记录的信息见 docs/meta/trace.md

### 离线部分

根据 trace 进行进化 scheduler，暂时不需要考虑


## 细节信息

- 对于 node 的元信息需要以配置文件见 docs/meta/config.md
