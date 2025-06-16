from dotenv import load_dotenv
from langgraph.graph import END, StateGraph
from agent_flow.nodes.search import web_search
from agent_flow.nodes.api_calls import api_call_agent
from agent_flow.nodes.generate import generate_final_response
from agent_flow.state import GraphState
import json
import os

load_dotenv()


def debug_state(state, location):
    """Enhanced debugging function"""
    print(f"\n=== DEBUG {location} ===")
    print(
        f"Full state keys: {list(state.keys()) if hasattr(state, 'keys') else 'Not a dict'}"
    )
    print(f"State type: {type(state)}")

    # Check each key individually
    for key in [
        "use_search",
        "is_high_occupancy",
        "api_results",
        "search_results",
        "query",
    ]:
        try:
            value = state.get(key)
            print(f"{key}: {value} (type: {type(value)})")
        except Exception as e:
            print(f"{key}: ERROR - {e}")

    # Check if state is properly structured
    print(f"State.__dict__: {getattr(state, '__dict__', 'No __dict__')}")
    print(f"Environment: {'LOCAL' if os.getenv('FLY_APP_NAME') is None else 'FLY.IO'}")
    print("=" * 50)


def decide_to_search(state):
    debug_state(state, "DECIDE_TO_SEARCH_START")

    use_search = state.get("use_search")
    is_high_occupancy = state.get("is_high_occupancy")
    api_results = state.get("api_results")

    print(f"Decision variables:")
    print(f"  use_search: {use_search} (bool: {type(use_search)})")
    print(f"  is_high_occupancy: {is_high_occupancy} (bool: {type(is_high_occupancy)})")
    print(
        f"  api_results: {api_results} (length: {len(api_results) if api_results else 0})"
    )

    # Check the actual logic
    should_search = bool(use_search) or bool(is_high_occupancy)
    print(f"  should_search: {should_search}")

    if should_search:
        print("DECISION: SEARCHING... (will trigger google_maps_search)")
        return "google_maps_search"
    else:
        print("DECISION: NOT SEARCHING... (will trigger generate)")
        return "generate"


# Wrap the original nodes with debugging
def debug_api_call_agent(state):
    debug_state(state, "API_CALL_AGENT_START")
    result = api_call_agent(state)
    debug_state(result, "API_CALL_AGENT_END")
    return result


def debug_web_search(state):
    debug_state(state, "WEB_SEARCH_START")
    result = web_search(state)
    debug_state(result, "WEB_SEARCH_END")
    return result


def debug_generate_final_response(state):
    debug_state(state, "GENERATE_FINAL_RESPONSE_START")
    result = generate_final_response(state)
    debug_state(result, "GENERATE_FINAL_RESPONSE_END")
    return result


graph = StateGraph(GraphState)

graph.add_node("google_maps_search", debug_web_search)
graph.add_node("api_call", debug_api_call_agent)
graph.add_node("generate", debug_generate_final_response)

graph.set_entry_point("api_call")
graph.add_conditional_edges("api_call", decide_to_search)
graph.add_edge("google_maps_search", "generate")
graph.add_edge("generate", END)

app = graph.compile()
