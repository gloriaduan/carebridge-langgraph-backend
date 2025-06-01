from typing import List, TypedDict
from langgraph.prebuilt.chat_agent_executor import AgentState

class GraphState(AgentState):
    """
    State of the graph.

    Attributes:
        query: User's query
        context: User's selected options for more context
        use_search: whether to add search
        api_results: results from API calls
        search_results: results from search
    """

    query: str
    context: dict[str, str | list]
    use_search: bool
    api_results: List[str]
    search_results: List[str]
    structured_response: dict[str, str | list] | None = None