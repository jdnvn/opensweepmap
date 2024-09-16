import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import time
import random
import pandas as pd
import numpy as np
import re

from sqlalchemy import create_engine, text


with open('/Users/joey/Documents/sweepmaps/boston_sidewalks.geojson', 'r') as f:
    data = json.load(f)

location_data = []

for feature in data["features"]:
    coords_list = feature["geometry"]["coordinates"]
    if feature["geometry"]["type"] == "LineString":
        coords = coords_list[len(coords_list) // 2]  # Use the middle point
    elif feature["geometry"]["type"] == "MultiLineString":
        coords = coords_list[0][len(coords_list[0]) // 2]  # First segment's midpoint

    lat = coords[1]
    lng = coords[0]
    location = {"id": feature["properties"]["OBJECTID"], "lat": lat, "lng": lng}
    location_data.append(location)


# For quick access
location_dict = {}
for location in location_data:
    location_dict[location['id']] = {"lat": location["lat"], "lng": location["lng"]}


def reverse_geocode(location_data):
    print(f'reverse geocoding request for id: {location_data["id"]}')
    attempts = 0
    max_retries = 1000
    retry_delay = 1
    while attempts <= max_retries:
        try:
            response = requests.get(f'http://localhost:8080/reverse?lat={location_data["lat"]}&lon={location_data["lng"]}&format=json')
            # response = requests.get(f'https://maps.googleapis.com/maps/api/geocode/json?latlng={location_data["lat"]},{location_data["lng"]}&key={API_KEY}')
            break
        except Exception as e:
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)  # Cap delay to 60 seconds
            retry_delay += random.uniform(0, 1)  # Add jitter
            attempts += 1
            print(f"Error getting reverse geolocation: {e}, attempt {attempts}/{max_retries}")
    if not response:
        raise Exception(f'max retries exceeded for node id {location_data["id"]}')
    response_body = response.json()
    print(f'done id: {location_data["id"]}')

    if "address" in response_body:
        print(f'done id: {location_data["id"]}')
        return {**location_data, "results": response_body["address"]}
    else:
        print(f'No address found for id: {location_data["id"]}')
        return {**location_data, "results": None}


geocoded_data = []
with ThreadPoolExecutor(max_workers=5) as t:
    futures = {t.submit(reverse_geocode, loc): loc for loc in location_data}
    # Use tqdm to track progress
    for future in tqdm(as_completed(futures), total=len(futures)):
        geocoded_data.append(future.result())


output_geojson = data
for feature in output_geojson["features"]:
    feature_id = feature["properties"]["OBJECTID"]
    matching_result = next((d for d in geocoded_data if d["id"] == feature_id), None)
    if matching_result:
        feature["properties"]["address"] = matching_result.get("results", {})


for feature in output_geojson["features"]:
    feature["properties"] = {**feature["properties"], **feature['properties']['address']}
    del feature["properties"]["address"]


with open('/Users/joey/Documents/sweepmaps/boston_sidewalks_geocoded.geojson', 'w') as outfile:
    json.dump(output_geojson, outfile)

