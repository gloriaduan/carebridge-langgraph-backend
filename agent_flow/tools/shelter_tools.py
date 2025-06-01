from typing import Annotated, Any, Dict
from langchain_core.tools import tool
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from agent_flow.models.filters import ShelterFilter
from langchain_core.tools.base import InjectedToolCallId
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from agent_flow.helpers import api_search, geocode_address, haversine_distance, extract_location_spacy, prune_results


# Define essential keys for pruning results within this tool
# These keys should be sufficient for the Evaluator agent and final response generation
EVALUATOR_ESSENTIAL_SHELTER_KEYS = [
    "LOCATION_NAME", "LOCATION_ADDRESS", "OVERNIGHT_SERVICE_TYPE", "SECTOR", "LOCATION_CITY", "PROGRAM_MODEL", "OCCUPANCY_RATE_ROOMS"
]


@tool
def retrieve_shelters(
    user_query: str, tool_call_id: Annotated[str, InjectedToolCallId]
) -> Dict[str, Any]:
    """Use this tool to retrieve shelters based on user query."""

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

    # --- Proximity filtering ---
    user_location_str = extract_location_spacy(user_query)
    user_coords = geocode_address(user_location_str)
    print('user_coords:', user_coords)
    if not user_coords:
        print(f"Could not geocode user location: {user_location_str}")
        filtered_results_by_proximity = response[:10]  # fallback: just first 10
    else:
        # Geocode each result's address and calculate distance
        results_with_distance = []
        for r in response:
            address = r.get('LOCATION_ADDRESS', '')  # <-- update this if your address field is different
            coords = geocode_address(address) if address else None
            if coords:
                dist = haversine_distance(user_coords['lat'], user_coords['lng'], coords['lat'], coords['lng'])
                print('distance:', dist)
                results_with_distance.append((dist, r))
            else:
                # If can't geocode, put at end with high distance
                results_with_distance.append((float('inf'), r))
        # Sort by distance and take top 10
        results_with_distance.sort(key=lambda x: x[0])
        filtered_results_by_proximity = [r for _, r in results_with_distance[:6]]

    # print("Filtered API response (top 10 by proximity):", filtered_results)

    # Prune the filtered results to include only essential keys
    final_pruned_results = prune_results(filtered_results_by_proximity, EVALUATOR_ESSENTIAL_SHELTER_KEYS)
    # print("Pruned shelter results for Evaluator:", final_pruned_results)

    return Command(
        update={
            "api_results": final_pruned_results,
            "messages": [
                ToolMessage(
                    "Successfully looked up shelters from Toronto Open Data",
                    tool_call_id=tool_call_id,
                )
            ],
        }
    )
