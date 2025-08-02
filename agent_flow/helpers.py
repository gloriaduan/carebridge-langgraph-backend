import requests
import json
import os
import math
import re
import spacy
import googlemaps
import sqlite3
from typing import List, Dict, Any
from .cache import cache

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    nlp = None

googlemaps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
gmaps = googlemaps.Client(key=googlemaps_api_key)
print("Using Google Maps with API key authentication in helpers.py")


def api_search(package_id: str, filters: dict) -> dict:
    # Toronto Open Data is stored in a CKAN instance. It's APIs are documented here:
    # https://docs.ckan.org/en/latest/api/

    print("GETTING DATA FROM API...")

    # Only include non-empty filter keys
    if hasattr(filters, "dict"):
        filters_dict = filters.dict()
    else:
        filters_dict = dict(filters)
    filters_clean = {
        key: value
        for key, value in filters_dict.items()
        if value != "" and value is not None
    }

    print(f"Clean filters: {filters_clean}")

    # To hit our API, you'll be making requests to:
    base_url = "https://ckan0.cf.opendata.inter.prod-toronto.ca"

    # Datasets are called "packages". Each package can contain many "resources"
    # To retrieve the metadata for this package and its resources, use the package name in this page's URL:
    url = base_url + "/api/3/action/package_show"
    params = {"id": package_id}
    package = requests.get(url, params=params).json()

    results = []

    if package["result"]["resources"]:
        resource = package["result"]["resources"][0]
        resource_id = resource["id"]

        # Check if we have language filtering - this needs special handling
        languages_filter = filters_clean.get("languages", "")

        if resource["datastore_active"]:
            # If we have language filtering, use full-text search approach
            if languages_filter:
                print(
                    f"Using full-text search for language filtering: {languages_filter}"
                )

                # Parse semicolon-separated languages
                languages_list = [
                    lang.strip() for lang in languages_filter.split(";") if lang.strip()
                ]

                # Method 1: Try full-text search with q parameter
                print("Attempting full-text search method...")
                url = base_url + "/api/3/action/datastore_search"

                # Create search query for languages
                search_query = " OR ".join(languages_list)  # "Mandarin OR Arabic"

                params = {
                    "id": resource_id,
                    "q": search_query,
                    "limit": 200,  # Get more results to filter
                }

                # Add other exact filters
                other_filters = {
                    k: v for k, v in filters_clean.items() if k != "languages"
                }
                if other_filters:
                    params["filters"] = json.dumps(other_filters)

                print(f"Full-text search params: {params}")

                try:
                    resource_response = requests.get(url, params=params)
                    print(f"Full-text response status: {resource_response.status_code}")

                    if resource_response.status_code == 200:
                        response_json = resource_response.json()

                        if response_json.get("success"):
                            all_results = response_json["result"].get("records", [])
                            print(
                                f"Full-text search returned {len(all_results)} total results"
                            )

                            # Post-filter to ensure language matches are in the languages field
                            # (since full-text search might match other fields)
                            filtered_results = []
                            for result in all_results:
                                record_languages = result.get("languages", "")
                                # Check if any of our target languages appear in the languages field
                                if any(
                                    lang.lower() in record_languages.lower()
                                    for lang in languages_list
                                ):
                                    filtered_results.append(result)

                            results = filtered_results[:50]  # Limit final results
                            print(
                                f"After language field filtering: {len(results)} results"
                            )

                            # Debug: show languages in first few results
                            for i, result in enumerate(results[:3]):
                                prog_name = result.get("program_name", "No name")
                                lang_field = result.get("languages", "No languages")
                                print(
                                    f"Filtered Result {i+1}: {prog_name} - Languages: {lang_field}"
                                )
                        else:
                            print(
                                f"Full-text search API returned success=false: {response_json}"
                            )
                            results = []
                    else:
                        print(
                            f"Full-text search HTTP error: {resource_response.status_code}"
                        )
                        print(f"Response content: {resource_response.text[:200]}")
                        results = []

                except Exception as e:
                    print(f"Error in full-text search: {e}")
                    results = []

                # If full-text search didn't work or returned no results, try getting all records and filtering in Python
                if not results:
                    print(
                        "Full-text search failed or returned no results. Trying get-all-and-filter approach..."
                    )
                    url = base_url + "/api/3/action/datastore_search"

                    # Get all records (or a large subset)
                    params = {
                        "id": resource_id,
                        "limit": 1000,  # Get a large number of records
                    }

                    # Add other exact filters
                    if other_filters:
                        params["filters"] = json.dumps(other_filters)

                    try:
                        resource_response = requests.get(url, params=params)
                        if resource_response.status_code == 200:
                            response_json = resource_response.json()
                            if response_json.get("success"):
                                all_results = response_json["result"].get("records", [])
                                print(
                                    f"Get-all approach returned {len(all_results)} total results"
                                )

                                # Filter in Python for language matches
                                filtered_results = []
                                for result in all_results:
                                    record_languages = result.get("languages", "")
                                    if any(
                                        lang.lower() in record_languages.lower()
                                        for lang in languages_list
                                    ):
                                        filtered_results.append(result)

                                results = filtered_results[:50]  # Limit final results
                                print(
                                    f"Python filtering found {len(results)} matching results"
                                )

                                # Debug: show languages in first few results
                                for i, result in enumerate(results[:3]):
                                    prog_name = result.get("program_name", "No name")
                                    lang_field = result.get("languages", "No languages")
                                    print(
                                        f"Python Filtered Result {i+1}: {prog_name} - Languages: {lang_field}"
                                    )
                            else:
                                print(
                                    f"Get-all API returned success=false: {response_json}"
                                )
                                results = []
                        else:
                            print(
                                f"Get-all HTTP error: {resource_response.status_code}"
                            )
                            results = []
                    except Exception as e:
                        print(f"Error in get-all approach: {e}")
                        results = []

            else:
                # No language filtering, use regular datastore_search
                print("Using regular datastore_search (no language filtering)")
                url = base_url + "/api/3/action/datastore_search"

                if len(filters_clean) > 0:
                    p = {
                        "id": resource_id,
                        "limit": 50,
                        "filters": json.dumps(filters_clean),
                    }
                    print(f"Regular search params: {p}")
                else:
                    p = {"id": resource_id, "limit": 50}

                resource_response = requests.get(url, params=p).json()
                print("Regular resource response received")

                if resource_response.get("success"):
                    resource_search_data = resource_response["result"]
                    results = resource_search_data.get("records", [])
                    print(f"Regular search returned {len(results)} results")
                else:
                    print(f"Regular search failed: {resource_response}")
                    results = []

    print("FINISHED GETTING DATA FROM API...")
    print(f"Total results found: {len(results)}")
    return results


def geocode_address(address: str) -> dict:
    """Geocode an address using Google Maps Geocoding API via googlemaps client, with Redis caching."""
    print("GEOCODING ADDRESS:", address)

    cache_key = f"geocode:{address.lower().strip()}"

    cached_result = cache.get(cache_key)

    if cached_result:
        print("Using cached geocode result.")
        return cached_result

    print("No cached result found, querying Google Maps API...")

    if not googlemaps_api_key:
        raise ValueError("GOOGLE_MAPS_API_KEY environment variable not set.")

    geocode_result = gmaps.geocode(
        address,
        region="ca",
        components={"country": "CA", "administrative_area": "ON"},
    )

    if geocode_result:
        location = geocode_result[0]["geometry"]["location"]
        lat, lng = location["lat"], location["lng"]

        result = {"lat": lat, "lng": lng}

        cache.set(cache_key, result, expire=86400)

        return result
    return None


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the great-circle distance between two points on the Earth (in kilometers)."""
    R = 6371  # Earth radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def extract_location_from_query(query: str) -> str:
    """Extract location from user query using regex. Looks for 'in <location>' or text in parentheses."""
    # Try to find text in parentheses
    match = re.search(r"\(([^)]+)\)", query)
    if match:
        return match.group(1)
    # Try to find 'in <location>'
    match = re.search(r" in ([^.,;!?]+)", query, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Fallback to the whole query
    return query.strip()


# def extract_location_spacy(query: str) -> str:
#     """Extract location using spaCy NER (GPE/LOC). Fallback to whole query if not found."""
#     global nlp
#     if nlp is None:
#         raise RuntimeError(
#             "spaCy model 'en_core_web_sm' is not installed. Run: python -m spacy download en_core_web_sm"
#         )
#     doc = nlp(query)
#     for ent in doc.ents:
#         if ent.label_ in ("GPE", "LOC"):
#             return ent.text
#     return query.strip()


def prune_results(
    results: List[Dict[str, Any]], essential_keys: List[str]
) -> List[Dict[str, Any]]:
    """
    Prune API results to only include essential keys.
    """
    pruned_list = []
    if not results:
        return []

    for item in results:
        if not isinstance(item, dict):
            continue  # Skip non-dict items

        pruned_item = {}
        for key in essential_keys:
            if (
                key in item and item[key] is not None
            ):  # Keep if key exists and value is not None
                pruned_item[key] = item[key]

        if pruned_item:  # Only add if it has some essential data
            pruned_list.append(pruned_item)

    return pruned_list


def filter_results_by_proximity(
    results: List[Dict[str, Any]],
    user_coords: Dict[str, float],
    address_field: str,
    essential_keys: List[str],
    limit: int = 6,
) -> List[Dict[str, Any]]:
    """
    Filter API results by proximity to user location.
    """
    if not user_coords:
        print(f"Could not geocode user location: {user_coords}")
        filtered_results = results[:limit]
    else:
        # Geocode each result's address and calculate distance
        results_with_distance = []
        for result in results:
            address = result.get(address_field, "")
            coords = geocode_address(address) if address else None
            if coords:
                dist = haversine_distance(
                    user_coords["lat"], user_coords["lng"], coords["lat"], coords["lng"]
                )
                print(f"Distance to {address}: {dist:.2f} km")
                results_with_distance.append((dist, result))
            else:
                # If can't geocode, put at end with high distance
                results_with_distance.append((float("inf"), result))

        # Sort by distance and take top 'limit' results
        results_with_distance.sort(key=lambda x: x[0])
        filtered_results = [result for _, result in results_with_distance[:limit]]

    # Prune the filtered results to include only essential keys
    final_pruned_results = prune_results(filtered_results, essential_keys)

    return final_pruned_results
