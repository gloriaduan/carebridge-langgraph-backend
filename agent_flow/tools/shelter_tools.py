from typing import Annotated, Any, Dict
from langchain_core.tools import tool
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from agent_flow.models.filters import ShelterFilter
from langchain_core.tools.base import InjectedToolCallId
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from langgraph.prebuilt import InjectedState
from agent_flow.helpers import api_search, filter_results_by_proximity
from utils.socket_context import SocketIOContext


EVALUATOR_ESSENTIAL_SHELTER_KEYS = [
    "LOCATION_NAME",
    "LOCATION_ADDRESS",
    "OVERNIGHT_SERVICE_TYPE",
    "SECTOR",
    "LOCATION_CITY",
    "PROGRAM_MODEL",
    "OCCUPANCY_RATE_ROOMS",
]


@tool
def retrieve_shelters(
    user_query: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
    state: Annotated[dict, InjectedState],
) -> Dict[str, Any]:
    """Use this tool to retrieve shelters based on user query."""
    # await SocketIOContext.emit("update", {"message": "Searching"})

    print("USED SHELTERS TOOL...")

    model = ChatOpenAI(model="gpt-4o", temperature=0)

    parser = PydanticOutputParser(pydantic_object=ShelterFilter)

    prompt = PromptTemplate(
        template="""From the following user query, please extract the relevant information and return it in a json object that contains the following keys: 'SECTOR', 'OVERNIGHT_SERVICE_TYPE'. 
                    
        Based on the user query, pick the most relevant value for each key from the following list: 
        SECTOR: ["Families", "Mixed Adult", "Men", "Women", "Youth", ""]
        OVERNIGHT_SERVICE_TYPE: ["Motel/Hotel Shelter", "Shelter", "24-Hour Respite Site", "Top Bunk Contingency Space", "Isolation/Recovery Site", "Alternative Space Protocol", ""]

        User query: {query}
        """,
        input_variables=["query"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    llm_with_parser = prompt | model | parser

    print("User query:", user_query)

    output = llm_with_parser.invoke({"query": user_query})

    print("OUTPUT:", output)

    response = api_search("daily-shelter-overnight-service-occupancy-capacity", output)

    user_coords = state.get("users_location", {})
    final_results = filter_results_by_proximity(
        results=response,
        user_coords=user_coords,
        address_field="LOCATION_ADDRESS",
        essential_keys=EVALUATOR_ESSENTIAL_SHELTER_KEYS,
        limit=5,
    )

    return Command(
        update={
            "api_results": final_results,
            "messages": [
                ToolMessage(
                    "Successfully looked up shelters from Toronto Open Data",
                    tool_call_id=tool_call_id,
                )
            ],
        }
    )
