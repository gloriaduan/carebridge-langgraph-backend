from typing import Any, Dict
from langchain_openai import ChatOpenAI
from agent_flow.models.responses import Evaluator
from agent_flow.state import GraphState
from utils.socket_context import SocketIOContext
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate


async def evaluate_api_results(state: GraphState) -> Dict[str, Any]:
    """Evaluates API results to decide if a web search is needed."""
    await SocketIOContext.emit("update", {"message": "Evaluating results"})

    api_results = state.get("api_results")
    print(f"API results from evaluator: {api_results}")
    query = state.get("query")

    # Handle case where the previous node found nothing
    if not api_results:
        print("No API results found. Forcing web search.")
        return {"use_search": True, "is_high_occupancy": False}

    system_msg = (
        "Evaluate the API results based on the user's query to determine if further search is needed. "
        "You MUST populate 'should_google' (boolean) and 'is_high_occupancy' (boolean). \n"
        "User Query: {user_query}\n"
        "API Results: {api_results}\n\n"
        "Decision Criteria:\n"
        "1. SHOULD_GOOGLE RULES:\n"
        "   - If API results contain relevant matches for the user query, set 'should_google' to 'false'\n"
        "2. IS_HIGH_OCCUPANCY RULES:\n"
        "   - Only applies to shelter queries (not family centers)\n"
        "   - If MOST shelter results show OCCUPANCY_RATE_ROOMS > 85%, set 'is_high_occupancy' to 'true'\n"
        "\nProvide ONLY the JSON for 'should_google' and 'is_high_occupancy' based on the Evaluator model."
    )

    model = ChatOpenAI(model="gpt-4o", temperature=0)
    parser = PydanticOutputParser(pydantic_object=Evaluator)

    prompt = PromptTemplate(
        template=system_msg,
        input_variables=["user_query", "api_results"],
    )

    llm_with_parser = prompt | model | parser

    response = llm_with_parser.invoke({"user_query": query, "api_results": api_results})

    should_google = response.should_google
    is_high_occupancy = response.is_high_occupancy

    print(
        f"Evaluation complete. Should Google: {should_google}, Is High Occupancy: {is_high_occupancy}"
    )

    return {
        "use_search": should_google or is_high_occupancy,
        "is_high_occupancy": is_high_occupancy,
    }
