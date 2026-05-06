# Workload

## critical task

| 节点 / 输出                                       |               建议频率 |        周期 | 关键性 | 说明               |
| --------------------------------------------- | -----------------: | --------: | --- | ---------------- |
| `localization_node`              |           50 Hz | 20–100 ms | 高   | 给导航算法提供当前位姿      |
| `pointcloud_to_laserscan_node`  |           20 Hz | 50–100 ms | 中高  | 通常跟随传感器输入频率      |
| `navigation_algo_node`           | 35 Hz | 约 28.6 ms | 高   | 直接影响机器人运动控制      |

## Agent task

添加一个 agent 任务，现在采用不需要真的 Agent 做规划，而是一个固定的 dag，我的计划是如下 dag，包括 3 个 node
```json
{
  "node": [
    {
      "id": 1,
      "tool": "image_captioning"，
    }
    {
      "id": 2,
      "tool": "text_translation"
    }
    {
      "id": 3,
      "tool": "text_to_speech"
    }
  ]，
  "link": [
    {
      "from": 1,
      "to": 2
    },
    {
      "from": 2,
      "to": 3
    }
  ]

}
```

上述三个node的 yaml 先自主生成
