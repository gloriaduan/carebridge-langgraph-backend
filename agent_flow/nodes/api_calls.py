from typing import Any, Dict
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from agent_flow.tools.shelter_tools import retrieve_shelters
from agent_flow.tools.family_center_tools import retrieve_children_family_centers
from agent_flow.state import GraphState
from utils.socket_context import SocketIOContext


async def api_call_agent(state: GraphState) -> Dict[str, Any]:
    await SocketIOContext.emit("update", {"message": "Searching resources"})

    query = state.get("query")

    model = ChatOpenAI(model="gpt-4o", temperature=0)

    tools = [retrieve_shelters, retrieve_children_family_centers]

    graph = create_react_agent(
        model,
        tools=tools,
        state_schema=GraphState,
    )

    response = graph.invoke(
        {
            "messages": [{"role": "user", "content": query}],
            "users_location": state.get("users_location", {}),
        }
    )

    api_results = response.get("api_results")

    return {
        "messages": response["messages"],
        "api_results": api_results,
    }
