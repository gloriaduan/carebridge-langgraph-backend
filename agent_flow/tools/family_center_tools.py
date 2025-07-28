from typing import Annotated, Any, Dict
from langchain_core.tools import tool
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from agent_flow.models.filters import ChildrenFamilyCenterFilter
from langchain_core.tools.base import InjectedToolCallId
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from langgraph.prebuilt import InjectedState
from agent_flow.helpers import (
    api_search,
    filter_results_by_proximity,
)
from utils.socket_context import SocketIOContext


EVALUATOR_ESSENTIAL_FAMILY_CENTER_KEYS = [
    "program_name",
    "full_address",
    "website",
    "consultant_phone",
    "email",
    "phone",
    "contact_email",
]

SUPPORTED_LANGUAGES = [
    "Akan (Twi)",
    "Arabic",
    "Bengali",
    "Cantonese",
    "Chinese - Other",
    "Dari",
    "Edo",
    "French",
    "German",
    "Gujarati",
    "Hindi",
    "Italian",
    "Japanese",
    "Korean",
    "Mandarin",
    "Panjabi (Punjabi)",
    "Pashto",
    "Persian (Farsi)",
    "Portuguese",
    "Russian",
    "Somali",
    "Spanish",
    "Tagalog (Pilipino, Filipino)",
    "Tamil",
    "Urdu",
    "Vietnamese",
]


@tool
def retrieve_children_family_centers(
    user_query: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
    state: Annotated[dict, InjectedState],
):
    """Use this tool to retrieve children centers or family centers based on user query."""
    # await SocketIOContext.emit("update", {"message": "Searching"})
    print("USED CHILDREN AND FAMILY CENTERS TOOL...")
    # user_query = "I'm looking for children and family centers for indegenous people in Toronto."

    model = ChatOpenAI(model="gpt-4o", temperature=0)

    parser = PydanticOutputParser(pydantic_object=ChildrenFamilyCenterFilter)

    prompt = PromptTemplate(
        template="""From the following user query, please extract the relevant information and return it in a json object that contains the following keys: 'french_language_program', 'indigenous_program', 'languages'. 
                    
        Based on the user query, pick the most relevant value for each key from the following list: 
        french_language_program: ["Yes", ""]
        indigenous_program: ["Yes", ""]
        languages: Empty if the language is English or not stated. Otherwise, please provide a semi-colon seperated list of languages if the user query states that the center speaks other languages.
        User query: {query}
        """,
        input_variables=["query"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    llm_with_parser = prompt | model | parser

    print("User query:", user_query)

    output = llm_with_parser.invoke({"query": user_query})

    print("OUTPUT:", output)

    response = api_search("earlyon-child-and-family-centres", output)

    user_coords = state.get("users_location", {})
    final_results = filter_results_by_proximity(
        results=response,
        user_coords=user_coords,
        address_field="full_address",
        essential_keys=EVALUATOR_ESSENTIAL_FAMILY_CENTER_KEYS,
        limit=5,
    )

    return Command(
        update={
            "api_results": final_results,
            "messages": [
                ToolMessage(
                    "Successfully looked up children and family centers",
                    tool_call_id=tool_call_id,
                )
            ],
        }
    )
