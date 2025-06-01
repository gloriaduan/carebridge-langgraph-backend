from dotenv import load_dotenv
from langgraph.graph import END, StateGraph
from agent_flow.nodes.search import web_search
from agent_flow.nodes.api_calls import api_call_agent
from agent_flow.nodes.generate import generate_final_response
from agent_flow.state import GraphState

load_dotenv()


def decide_to_search(state):
    print("DECIDING WHETHER TO SEARCH...")

    if state.get("use_search") or state.get("is_high_occupancy"):
        print("SEARCHING...")
        return "google_maps_search"
    else:
        print("NOT SEARCHING...")
        return "generate"


graph = StateGraph(GraphState)

graph.add_node("google_maps_search", web_search)
graph.add_node("api_call", api_call_agent)
graph.add_node("generate", generate_final_response)

graph.set_entry_point("api_call")
graph.add_conditional_edges("api_call", decide_to_search)
graph.add_edge("google_maps_search", "generate")
graph.add_edge("generate", END)


app = graph.compile()
