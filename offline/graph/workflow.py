from langgraph.graph import END, StateGraph

from offline.graph import nodes
from offline.memory.schemas import EvolutionState


def compile_workflow():
    graph = StateGraph(EvolutionState)
    graph.add_node("load_trace", nodes.load_trace)
    graph.add_node("profile_workload", nodes.profile_workload)
    graph.add_node("retrieve_similar_workloads", nodes.retrieve_similar_workloads)
    graph.add_node("analyze_scheduler_defects", nodes.analyze_scheduler_defects)
    graph.add_node("generate_advice_branches", nodes.generate_advice_branches)
    graph.add_node("generate_scheduler_candidates", nodes.generate_scheduler_candidates)
    graph.add_node("replay_candidates", nodes.replay_candidates)
    graph.add_node("compare_candidates", nodes.compare_candidates)
    graph.add_node("persist_memory", nodes.persist_memory)
    graph.set_entry_point("load_trace")
    graph.add_edge("load_trace", "profile_workload")
    graph.add_edge("profile_workload", "retrieve_similar_workloads")
    graph.add_edge("retrieve_similar_workloads", "analyze_scheduler_defects")
    graph.add_edge("analyze_scheduler_defects", "generate_advice_branches")
    graph.add_edge("generate_advice_branches", "generate_scheduler_candidates")
    graph.add_edge("generate_scheduler_candidates", "replay_candidates")
    graph.add_edge("replay_candidates", "compare_candidates")
    graph.add_edge("compare_candidates", "persist_memory")
    graph.add_edge("persist_memory", END)
    return graph.compile()
