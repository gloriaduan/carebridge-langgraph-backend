from typing import Any, Dict
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from agent_flow.tools.shelter_tools import retrieve_shelters
from agent_flow.tools.family_center_tools import retrieve_children_family_centers
from agent_flow.models.responses import Evaluator
from agent_flow.state import GraphState


def prompt(state: GraphState):
    api_results = state.get("api_results")
    query = state.get("query")

    system_msg = (
        "Evaluate the API results based on the user's query to determine if further search is needed. "
        "You MUST populate 'should_google' (boolean) and 'is_high_occupancy' (boolean). \n"
        "User Query: {user_query}\n"
        "API Results: {results_summary}\n\n"
        "Decision Criteria:\n"
        "1. If API results are empty OR clearly irrelevant to the user query, set 'should_google' to 'true'. Otherwise, 'false'.\n"
        "2. For shelter-related queries: if MOST shelter results show high occupancy (e.g., OCCUPANCY_RATE_ROOMS > 85% or low availability), set 'is_high_occupancy' to 'true'. Otherwise, 'false'. For non-shelter queries, 'is_high_occupancy' is usually 'false' unless specified by results.\n"
        "3. If 'is_high_occupancy' is 'true', 'should_google' should also generally be 'true' to find alternatives.\n"
        "Provide ONLY the JSON for 'should_google' and 'is_high_occupancy' based on the Evaluator model."
    )

    results_summary_str = "Not available or empty."
    if api_results:
        results_summary_str = str(api_results)

    formatted_system_msg = system_msg.format(
        user_query=query, results_summary=results_summary_str
    )

    return [{"role": "system", "content": formatted_system_msg}] + state["messages"]


def api_call_agent(state: GraphState) -> Dict[str, Any]:
    query = state.get("query")

    model = ChatOpenAI(model="gpt-4o", temperature=0)

    tools = [retrieve_shelters, retrieve_children_family_centers]

    graph = create_react_agent(
        model,
        tools=tools,
        response_format=Evaluator,
        state_schema=GraphState,
        prompt=prompt,
    )

    response = graph.invoke(
        {
            "messages": [{"role": "user", "content": query}],
            "users_location": state.get("users_location", {}),
        }
    )
    should_google = response["structured_response"].should_google
    is_high_occupancy = response["structured_response"].is_high_occupancy
    api_results = response.get("api_results")

    if not api_results:
        should_google = True
        response["messages"] = [
            {
                "role": "assistant",
                "content": "No results found from the API. Initiating search.",
            }
        ]

    return {
        "messages": response["messages"],
        "api_results": api_results,
        "use_search": should_google or is_high_occupancy,
    }
