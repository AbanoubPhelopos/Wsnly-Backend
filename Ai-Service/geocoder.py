import googlemaps
import os
import logging


CAIRO_BOUNDS = {
    "min_lat": 29.8,
    "max_lat": 30.3,
    "min_lon": 30.9,
    "max_lon": 31.7,
}

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GoogleMapsGeocoder:
    def __init__(self, api_key=None):
        if not api_key:
            api_key = os.getenv("GOOGLE_MAPS_API_KEY")

        if not api_key:
            logger.warning("No Google Maps API Key provided. Geocoding will fail.")
            self.client = None
        else:
            try:
                self.client = googlemaps.Client(key=api_key)
                logger.info("Google Maps Client initialized.")
            except ValueError as exc:
                # The library rejects malformed / non-Maps keys with ValueError
                # at construction time. Don't crash the container — surface a
                # clear warning and let per-request geocoding fail gracefully.
                logger.error(
                    "Invalid GOOGLE_MAPS_API_KEY (%s). Geocoding will be disabled "
                    "until a valid key is provided.",
                    exc,
                )
                self.client = None

        self.cache = {}

    def _is_in_cairo_bounds(self, lat, lon):
        return (
            CAIRO_BOUNDS["min_lat"] <= lat <= CAIRO_BOUNDS["max_lat"]
            and CAIRO_BOUNDS["min_lon"] <= lon <= CAIRO_BOUNDS["max_lon"]
        )

    def _pick_best_result(self, geocode_results):
        if not geocode_results:
            return None

        # Prefer results that are physically inside Cairo bounds.
        for result in geocode_results:
            location = result.get("geometry", {}).get("location")
            if not location:
                continue
            lat = location.get("lat")
            lon = location.get("lng")
            if lat is None or lon is None:
                continue
            if self._is_in_cairo_bounds(lat, lon):
                return result

        # Fallback to first result if none match Cairo bounds.
        return geocode_results[0]

    def get_coordinates(self, location_name):
        """
        Resolves a location name to (latitude, longitude).
        Returns None if not found or error.
        """
        # Check cache
        if location_name in self.cache:
            logger.info(f"Cache hit for '{location_name}'")
            return self.cache[location_name]

        # 1. Try Google Maps first if client is initialized
        if self.client:
            try:
                # Egypt bias + Cairo-focused fallback query.
                primary_results = self.client.geocode(
                    location_name,
                    components={"country": "EG"},
                    language="ar",
                )

                best_result = self._pick_best_result(primary_results)

                # If first query doesn't return Cairo-biased point, try adding Cairo context.
                if best_result:
                    location = best_result.get("geometry", {}).get("location", {})
                    lat = location.get("lat")
                    lng = location.get("lng")
                    if (
                        lat is not None
                        and lng is not None
                        and not self._is_in_cairo_bounds(lat, lng)
                    ):
                        cairo_query = f"{location_name}, القاهرة, مصر"
                        cairo_results = self.client.geocode(
                            cairo_query,
                            components={"country": "EG"},
                            language="ar",
                        )
                        cairo_best = self._pick_best_result(cairo_results)
                        if cairo_best:
                            best_result = cairo_best

                if best_result:
                    location = best_result["geometry"]["location"]
                    lat = location["lat"]
                    lng = location["lng"]

                    logger.info(f"Geocoded '{location_name}' to ({lat}, {lng}) via Google Maps")
                    self.cache[location_name] = (lat, lng)
                    return (lat, lng)
            except Exception as e:
                logger.error(f"Google Maps geocoding error for '{location_name}': {e}")

        # 2. Fallback to Nominatim (OpenStreetMap) if Google Maps is not available or fails
        logger.info(f"Attempting Nominatim fallback for '{location_name}'...")
        try:
            import urllib.request
            import urllib.parse
            import json

            # Bias the search query for Cairo, Egypt
            query_str = f"{location_name}, Cairo, Egypt" if "القاهرة" not in location_name else location_name
            query = urllib.parse.urlencode({
                'q': query_str,
                'format': 'json',
                'countrycodes': 'eg',
                'limit': 3
            })
            url = f"https://nominatim.openstreetmap.org/search?{query}"
            
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'WslnyApp/1.0 (contact@wslny.com)'}
            )
            
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                
                best_result = None
                if data:
                    # Prefer results inside Cairo bounds
                    for item in data:
                        lat = float(item['lat'])
                        lon = float(item['lon'])
                        if self._is_in_cairo_bounds(lat, lon):
                            best_result = (lat, lon)
                            break
                    if not best_result:
                        best_result = (float(data[0]['lat']), float(data[0]['lon']))
                        
                if best_result:
                    logger.info(f"Geocoded '{location_name}' to {best_result} via Nominatim")
                    self.cache[location_name] = best_result
                    return best_result
                else:
                    logger.warning(f"No Nominatim results found for '{location_name}'")
        except Exception as e:
            logger.error(f"Nominatim geocoding error for '{location_name}': {e}")

        return None
