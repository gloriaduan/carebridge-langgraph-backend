from dotenv import load_dotenv
from langgraph.graph import END, StateGraph
from agent_flow.nodes.search import web_search
from agent_flow.nodes.api_calls import api_call_agent
from agent_flow.nodes.generate import generate_final_response
from agent_flow.nodes.query_validation import query_validation
from agent_flow.state import GraphState
import json
import os

load_dotenv()


def decide_to_proceed(state):
    is_valid_query = state.get("is_valid_query")
    print(f"  is_valid_query: {is_valid_query}")

    should_proceed = True if is_valid_query == "VALID" else False
    print(f"  should_proceed: {should_proceed}")

    if should_proceed:
        print("DECISION: PROCEEDING... (will trigger api_call)")
        return "api_call"
    else:
        print("DECISION: NOT PROCEEDING... (will trigger generate)")
        return "generate"


def decide_to_search(state):
    use_search = state.get("use_search")
    is_high_occupancy = state.get("is_high_occupancy")

    should_search = bool(use_search) or bool(is_high_occupancy)
    print(f"  should_search: {should_search}")

    if should_search:
        print("DECISION: SEARCHING... (will trigger google_maps_search)")
        return "google_maps_search"
    else:
        print("DECISION: NOT SEARCHING... (will trigger generate)")
        return "generate"


graph = StateGraph(GraphState)

graph.add_node("validate_query", query_validation)
graph.add_node("google_maps_search", web_search)
graph.add_node("api_call", api_call_agent)
graph.add_node("generate", generate_final_response)

graph.set_entry_point("validate_query")
graph.add_conditional_edges("validate_query", decide_to_proceed)
graph.add_conditional_edges("api_call", decide_to_search)
graph.add_edge("google_maps_search", "generate")
graph.add_edge("generate", END)

app = graph.compile()
