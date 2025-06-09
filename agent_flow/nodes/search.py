import os
import json
from typing import List, Dict, Any
from dotenv import load_dotenv
from google.oauth2 import service_account

from langchain.schema import Document
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

import googlemaps

from agent_flow.state import GraphState

load_dotenv()

# Initialize Google Maps client with API key
googlemaps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
gmaps = googlemaps.Client(key=googlemaps_api_key)
print("Using Google Maps with API key authentication")

def web_search(state: GraphState) -> Dict[str, Any]:
    print("SEARCHING GOOGLE MAPS...")
    # print("API RESUTS FROM STATE:", state["api_results"])

    query = state["query"]

    generate_location_prompt = ChatPromptTemplate(
        [
            (
                "system",
                """Your task is to generate a concise google maps search query from the user's query below.""",
            ),
            ("user", "{query}"),
        ]
    )

    llm = ChatOpenAI(temperature=0)

    generate_query_chain = generate_location_prompt | llm

    result = generate_query_chain.invoke({"query": query})

    final_search_query = result.content

    # GTA center point for location bias (Downtown Toronto)
    gta_center = {"lat": 43.6532, "lng": -79.3832}

    # Initial places search with GTA location bias and bounds
    places_result = gmaps.places(
        query=final_search_query,
        location=gta_center,
        radius=50000,  # 50km radius from center
        region="ca",
    )

    places_result = gmaps.places(query=final_search_query)

    detailed_results = []

    for place in places_result["results"]:
        try:
            place_id = place["place_id"]

            place_details = gmaps.place(
                place_id=place_id,
                fields=[
                    "name",
                    "formatted_phone_number",
                    "website",
                    "url",
                    "formatted_address",
                ],
            )

            details = place_details["result"]

            detailed_place = {
                "name": details.get("name"),
                "phone_number": details.get("formatted_phone_number"),
                "website": details.get("website"),
                "url": details.get("url"),
                "address": details.get("formatted_address"),
            }

            detailed_results.append(detailed_place)
        except Exception as e:
            print(
                f"Error getting details for place {place.get('name', 'Unknown')}: {e}"
            )
            detailed_results.append(
                {
                    "name": place.get("name"),
                    "address": place.get("formatted_address"),
                    "rating": place.get("rating"),
                    "place_id": place.get("place_id"),
                    "error": "Could not fetch detailed contact information",
                }
            )

    return {"search_results": detailed_results}
