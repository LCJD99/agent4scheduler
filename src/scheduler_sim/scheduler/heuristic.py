from scheduler_sim.scheduler.base import RunnableNode, Scheduler, SchedulerDecision, SchedulerObservation


class HeuristicScheduler(Scheduler):
    def decide(self, observation: SchedulerObservation) -> SchedulerDecision:
        selected_nodes = sorted(observation.runnable_nodes, key=self._priority_key)
        return SchedulerDecision(
            selected_nodes=selected_nodes,
            timestamp_us=observation.timestamp_us,
        )

    def _priority_key(self, node: RunnableNode) -> tuple[int, str]:
        criticality_rank = {
            "high": 0,
            "medium": 1,
            "low": 2,
        }
        return (criticality_rank.get(node.criticality, 3), node.node_id)
