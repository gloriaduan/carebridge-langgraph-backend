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
    geocode_address,
    haversine_distance,
    extract_location_spacy,
    prune_results,
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


@tool
async def retrieve_children_family_centers(
    user_query: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
    state: Annotated[dict, InjectedState],
):
    """Use this tool to retrieve children centers or family centers based on user query."""
    await SocketIOContext.emit("update", {"message": "Searching"})
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

    # --- Proximity filtering ---
    print("STATE:", state)
    user_location_str = extract_location_spacy(user_query)

    # user_coords = geocode_address(user_location_str)
    user_coords = state.get("users_location", {})
    if not user_coords:
        print(f"Could not geocode user location: {user_location_str}")
        filtered_results_by_proximity = response[:6]  # fallback: just first 10
    else:
        # Geocode each result's address and calculate distance
        results_with_distance = []
        for r in response:
            address = r.get(
                "full_address", ""
            )  # <-- update this if your address field is different
            coords = geocode_address(address) if address else None
            if coords:
                dist = haversine_distance(
                    user_coords["lat"], user_coords["lng"], coords["lat"], coords["lng"]
                )
                print("distance:", dist)
                results_with_distance.append((dist, r))
            else:
                # If can't geocode, put at end with high distance
                results_with_distance.append((float("inf"), r))
        # Sort by distance and take top 10
        results_with_distance.sort(key=lambda x: x[0])
        filtered_results_by_proximity = [r for _, r in results_with_distance[:6]]

    # print("Filtered API response (top 10 by proximity):", filtered_results)

    # Prune the filtered results to include only essential keys
    final_pruned_results = prune_results(
        filtered_results_by_proximity, EVALUATOR_ESSENTIAL_FAMILY_CENTER_KEYS
    )
    # print("Pruned family center results for Evaluator:", final_pruned_results)

    return Command(
        update={
            "api_results": final_pruned_results,
            "messages": [
                ToolMessage(
                    "Successfully looked up children and family centers",
                    tool_call_id=tool_call_id,
                )
            ],
        }
    )
