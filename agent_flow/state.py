from typing import List, TypedDict, Annotated
from langgraph.prebuilt.chat_agent_executor import AgentState
import operator


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
    is_valid_query: str
    use_search: bool
    api_results: Annotated[List, operator.add]
    search_results: List[str]
    structured_response: dict[str, str | list] | None = None
    error_response: str | None = None
