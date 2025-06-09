import requests
import json
import os
import math
import re
import spacy
import googlemaps
import sqlite3
from typing import List, Dict, Any, Optional
from google.oauth2 import service_account

# Load spaCy model globally to avoid repeated loading
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    nlp = None  # Will raise error if used without model installed

googlemaps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
gmaps = googlemaps.Client(key=googlemaps_api_key)
print("Using Google Maps with API key authentication in helpers.py")

# Initialize SQLite cache in the persistent volume directory
DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
# Create the directory if it doesn't exist
os.makedirs(DATA_DIR, exist_ok=True)
GEOCODE_DB_PATH = os.path.join(DATA_DIR, "geocode_cache.db")


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

    # To hit our API, you'll be making requests to:
    base_url = "https://ckan0.cf.opendata.inter.prod-toronto.ca"

    # Datasets are called "packages". Each package can contain many "resources"
    # To retrieve the metadata for this package and its resources, use the package name in this page's URL:
    url = base_url + "/api/3/action/package_show"
    params = {"id": package_id}
    package = requests.get(url, params=params).json()

    # print(len(package["result"]["resources"]))

    results = []

    if package["result"]["resources"]:
        resource = package["result"]["resources"][0]
        # To selectively pull records and attribute-level metadata:
        if resource["datastore_active"]:
            url = base_url + "/api/3/action/datastore_search"
            if len(filters_clean) > 0:
                p = {
                    "id": resource["id"],
                    "limit": 50,
                    "filters": json.dumps(filters_clean),
                }
            else:
                p = {"id": resource["id"], "limit": 50}
            resource_response = requests.get(url, params=p).json()
            resource_search_data = resource_response["result"]
            print("FINISHED GETTING DATA FROM API...")
            results = resource_search_data["records"]

    # print("RESULTS: ", results)
    return results


def geocode_address(address: str) -> dict:
    """Geocode an address using Google Maps Geocoding API via googlemaps client, with SQLite caching."""
    print("GEOCODING ADDRESS:", address)
    # Open a new connection for this thread
    conn = sqlite3.connect(GEOCODE_DB_PATH)
    c = conn.cursor()
    try:
        # Ensure table exists (safe to run multiple times)
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS geocode_cache (
                address TEXT PRIMARY KEY,
                lat REAL,
                lng REAL
            )
        """
        )
        conn.commit()
        c.execute("SELECT lat, lng FROM geocode_cache WHERE address = ?", (address,))
        row = c.fetchone()
        # print("ROW:", row)
        if row:
            print("FETCHED FROM CACHE", row)
            return {"lat": row[0], "lng": row[1]}
        if not googlemaps_api_key:
            raise ValueError("GOOGLE_MAPS_API_KEY environment variable not set.")
        geocode_result = gmaps.geocode(
            address,
            region="ca",
            components={"country": "CA", "administrative_area": "ON"},
        )
        # print("GEOCODING RESPONSE:", geocode_result)
        if geocode_result:
            location = geocode_result[0]["geometry"]["location"]
            lat, lng = location["lat"], location["lng"]
            # Store in cache
            c.execute(
                "INSERT OR REPLACE INTO geocode_cache (address, lat, lng) VALUES (?, ?, ?)",
                (address, lat, lng),
            )
            conn.commit()
            return {"lat": lat, "lng": lng}
        return None
    finally:
        conn.close()


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


def extract_location_spacy(query: str) -> str:
    """Extract location using spaCy NER (GPE/LOC). Fallback to whole query if not found."""
    global nlp
    if nlp is None:
        raise RuntimeError(
            "spaCy model 'en_core_web_sm' is not installed. Run: python -m spacy download en_core_web_sm"
        )
    doc = nlp(query)
    for ent in doc.ents:
        if ent.label_ in ("GPE", "LOC"):
            return ent.text
    return query.strip()


def prune_results(
    results: List[Dict[str, Any]], essential_keys: List[str]
) -> List[Dict[str, Any]]:
    """
    Prune API results to only include essential keys.

    Args:
        results: List of dictionary results from API calls
        essential_keys: List of keys to keep in each result

    Returns:
        List of dictionaries with only the essential keys
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
