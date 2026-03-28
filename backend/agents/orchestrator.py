from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
from agents.monitor import monitor_agent
from agents.root_cause import root_cause_agent
from agents.healer import healer_agent
from agents.notifier import notifier_agent

# Define the state to pass between agents
class PipelineState(TypedDict):
    pipeline_issues: List[Dict[str, Any]]
    healed_results: List[Dict[str, Any]]
    notifications: List[str]
    status: str

# Conditional edge to decide routing
def should_continue(state: PipelineState) -> str:
    """Return the name of the next node based on state."""
    # If monitor didn't find issues, we stop
    if state.get("status") == "ok":
        return END
    # Otherwise go to root cause analysis
    return "root_cause"

def build_orchestrator():
    """Builds and returns the LangGraph orchestrator."""
    workflow = StateGraph(PipelineState)

    # Add agent nodes
    workflow.add_node("monitor", monitor_agent)
    workflow.add_node("root_cause", root_cause_agent)
    workflow.add_node("healer", healer_agent)
    workflow.add_node("notifier", notifier_agent)

    # Define the execution edges
    workflow.set_entry_point("monitor")

    # The monitor routes conditionally
    workflow.add_conditional_edges(
        "monitor",
        should_continue,
        {
            "root_cause": "root_cause",
            END: END
        }
    )

    # Standard linear flow after root cause
    workflow.add_edge("root_cause", "healer")
    workflow.add_edge("healer", "notifier")
    workflow.add_edge("notifier", END)

    # Compile Graph
    return workflow.compile()
