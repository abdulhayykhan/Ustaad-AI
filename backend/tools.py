import os
import googlemaps
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

# Initialize the Google Maps client
gmaps = googlemaps.Client(key=API_KEY) if API_KEY else None

def get_coordinates(location_string: str) -> tuple[float, float]:
    """
    Geocodes a natural language location string into latitude and longitude.
    Biased towards Karachi, Pakistan to ensure local results.
    
    Args:
        location_string: A natural language location (e.g., "Shah Faisal Number 2")
        
    Returns:
        tuple: (latitude, longitude)
    """
    if not gmaps:
        raise ValueError("Google Maps API Key not configured in .env")
        
    # Enhance the prompt with Karachi context if not provided
    search_query = location_string
    if "karachi" not in search_query.lower():
        search_query += ", Karachi, Pakistan"
        
    try:
        geocode_result = gmaps.geocode(search_query)
        
        if geocode_result and len(geocode_result) > 0:
            location = geocode_result[0]['geometry']['location']
            return location['lat'], location['lng']
            
        raise ValueError(f"No results found for location: {location_string}")
    except Exception as e:
        raise ValueError(f"Geocoding failed: {str(e)}")


def calculate_real_travel_time(origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float) -> dict:
    """
    Calls the Google Maps Distance Matrix API to find actual driving distance and time.
    
    Args:
        origin_lat, origin_lng: Provider's current coordinates
        dest_lat, dest_lng: User's requested coordinates
        
    Returns:
        dict: {"distance_km": float, "duration_mins": float}
    """
    if not gmaps:
        raise ValueError("Google Maps API Key not configured in .env")
        
    origin = (origin_lat, origin_lng)
    destination = (dest_lat, dest_lng)
    
    try:
        matrix = gmaps.distance_matrix(origins=[origin], destinations=[destination], mode="driving")
        
        if matrix['status'] == 'OK':
            element = matrix['rows'][0]['elements'][0]
            if element['status'] == 'OK':
                # Convert distance from meters to kilometers
                distance_m = element['distance']['value']
                distance_km = distance_m / 1000.0
                
                # Convert duration from seconds to minutes
                duration_s = element['duration']['value']
                duration_mins = duration_s / 60.0
                
                return {
                    "distance_km": round(distance_km, 2),
                    "duration_mins": round(duration_mins, 2)
                }
            else:
                raise ValueError(f"Element status failed: {element['status']}")
                
        raise ValueError(f"Distance Matrix API failed with status: {matrix['status']}")
    except Exception as e:
        raise ValueError(f"Distance calculation failed: {str(e)}")
