import requests
from bs4 import BeautifulSoup
import json
import hashlib
import os
import time
from datetime import datetime, timedelta
import re

# Configuration
DATA_URL = "https://119dts.fdkc.gov.tw/tyfdapp/webControlKC?page=Tfqve7Vz8sjTOllavM2iqQ==&f=IC2SZJqIMDj1EwKMezrgvw=="
DATA_FILE = "data.json"
LOCATION_CACHE_FILE = "location_cache.json"

# Headers to mimic a browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def load_json(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return [] if "data.json" in filepath else {}
    return [] if "data.json" in filepath else {}

def save_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def generate_id(timestamp, address, incident_type):
    raw_str = f"{timestamp}{address}{incident_type}"
    return hashlib.md5(raw_str.encode('utf-8')).hexdigest()

def clean_text(text):
    if not text:
        return ""
    return text.strip().replace('\n', '').replace('\t', '')

def fetch_data():
    try:
        response = requests.get(DATA_URL, headers=HEADERS, timeout=30)
        # The site specifies <meta charset="UTF-8" />, so we trust it.
        # Fallback to apparent_encoding if needed, but usually manual assignment is safer for mixed headers.
        response.encoding = 'utf-8' 
        return response.text
    except Exception as e:
        print(f"Error fetching URL: {e}")
        return None

def parse_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table', class_='tablelist')
    if not table:
        print("Table not found")
        return []

    incidents = []
    # Skip header row, and look for rows with class table_tr1 or table_tr2
    rows = table.find_all('tr', class_=['table_tr1', 'table_tr2'])
    
    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 7:
            continue
            
        # Extract columns based on user investigation
        # Index 1: Timestamp
        # Index 2: Category
        # Index 3: Type
        # Index 4: Address
        # Index 5: Dispatch Unit (Optional)
        # Index 6: Status
        
        timestamp_str = clean_text(cols[1].text)
        category = clean_text(cols[2].text)
        incident_type = clean_text(cols[3].text)
        address = clean_text(cols[4].text)
        status = clean_text(cols[6].text)
        
        incident_id = generate_id(timestamp_str, address, incident_type)
        
        incidents.append({
            "id": incident_id,
            "timestamp": timestamp_str,
            "category": category,
            "type": incident_type,
            "address": address,
            "status": status,
            "lat": None, # To be filled
            "lng": None, # To be filled
            "precision": None # "point" or "area"
        })
    
    return incidents

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

# Initialize Geocoder
geolocator = Nominatim(user_agent="kaohsiung_fire_map_v1")

def get_coordinates(address, cache):
    if address in cache:
        return cache[address]
    
    # Clean address for better hit rate
    # Remove floor numbers or extra details if needed, but Nominatim is usually okay.
    
    queries_to_try = [address]
    
    # 1. Intersection Handling (e.g., "鼎強街和鼎正街")
    # Matches "Road A" + "和/&/與" + "Road B"
    intersection_match = re.search(r'(.+?[路街道])(?:和|&|與|、)(.+?[路街道])', address)
    if intersection_match:
        road1 = intersection_match.group(1).replace('高雄市', '').replace('區', '') # Cleanup if prefix captured
        road2 = intersection_match.group(2)
        # Try both "Road A & Road B, Kaohsiung" patterns
        queries_to_try.insert(0, f"{road1} & {road2}, 高雄市")
        print(f"Detected intersection: {road1} & {road2}")

    # 2. Road Backoff (e.g., "高雄市苓雅區建國一路" -> "高雄市建國一路")
    match = re.search(r'(高雄市)(.+?[區])?(.+?[路街道])', address)
    if match and not intersection_match: # Only fallback to road if not an intersection
        city = match.group(1)
        # district = match.group(2)
        road = match.group(3)
        if road:
            # Try City + Road (Cleaner for Nominatim than City + District + Road sometimes)
            queries_to_try.append(f"{city}{road}")

    for query in queries_to_try:
        try:
            print(f"Geocoding query: {query}...")
            location = geolocator.geocode(query, timeout=10)
            if location:
                # Basic check: Is it roughly in Kaohsiung? (Lat ~22.6)
                if 22.0 <= location.latitude <= 23.5 and 120.0 <= location.longitude <= 121.5:
                     coords = [location.latitude, location.longitude]
                     cache[address] = coords # Cache using original address key
                     time.sleep(1.1) 
                     return coords
                else:
                     print(f"Skipping result out of bounds: {location}")
        except Exception as e:
            print(f"Geocoding error for {query}: {e}")
            time.sleep(1) # Sleep even on error to be safe
    
    print(f"Failed to geocode: {address}")
    return None

def main():
    print("Starting scraper...")
    
    # Load existing data
    existing_data = load_json(DATA_FILE)
    existing_ids = {item['id'] for item in existing_data}
    
    # Load location cache
    location_cache = load_json(LOCATION_CACHE_FILE)
    
    # Fetch and parse
    html = fetch_data()
    if not html:
        return

    new_incidents = parse_html(html)
    print(f"Found {len(new_incidents)} incidents on page.")
    
    added_count = 0
    for incident in new_incidents:
        if incident['id'] not in existing_ids:
            # New incident
            
            # Geocoding Step
            coords = get_coordinates(incident['address'], location_cache)
            if coords:
                incident['lat'] = coords[0]
                incident['lng'] = coords[1]
            
            # Check precision
            if "區" in incident['address'] and not any(k in incident['address'] for k in ["路", "街", "號", "段", "巷", "弄"]):
                incident['precision'] = "area"
            else:
                incident['precision'] = "point"

            existing_data.append(incident)
            added_count += 1
    
    # Sort by timestamp descending
    existing_data.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Save back
    save_json(DATA_FILE, existing_data)
    save_json(LOCATION_CACHE_FILE, location_cache)
    
    print(f"Scraping complete. Added {added_count} new incidents.")

if __name__ == "__main__":
    main()
