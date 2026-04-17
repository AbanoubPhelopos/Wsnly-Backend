import csv
import math
from functools import lru_cache
from pathlib import Path

from django.conf import settings


def _gtfs_path():
    p = getattr(settings, "GTFS_PATH", "")
    return Path(p) if p else None


def _strip_quotes(value):
    return value.strip().strip('"').strip()


@lru_cache(maxsize=1)
def _load_stops():
    gtfs = _gtfs_path()
    if not gtfs:
        return []
    stops_file = gtfs / "stops.csv"
    if not stops_file.exists():
        stops_file = gtfs / "stops.txt"
    if not stops_file.exists():
        return []

    stops = []
    with open(stops_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                lat = float(_strip_quotes(row.get("stop_lat", "")))
                lon = float(_strip_quotes(row.get("stop_lon", "")))
            except (ValueError, TypeError):
                continue
            stops.append(
                {
                    "stop_id": _strip_quotes(row.get("stop_id", "")),
                    "stop_name": _strip_quotes(row.get("stop_name", "")),
                    "lat": lat,
                    "lon": lon,
                }
            )
    return stops


@lru_cache(maxsize=1)
def _load_routes():
    gtfs = _gtfs_path()
    if not gtfs:
        return []
    routes_file = gtfs / "routes.csv"
    if not routes_file.exists():
        routes_file = gtfs / "routes.txt"
    if not routes_file.exists():
        return []

    routes = []
    with open(routes_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            routes.append(
                {
                    "route_id": _strip_quotes(row.get("route_id", "")),
                    "agency_id": _strip_quotes(row.get("agency_id", "")),
                    "route_short_name": _strip_quotes(row.get("route_short_name", "")),
                    "route_type": _strip_quotes(row.get("route_type", "3")),
                    "route_long_name": _strip_quotes(row.get("route_long_name", "")),
                    "route_color": _strip_quotes(row.get("route_color", "")),
                }
            )
    return routes


@lru_cache(maxsize=1)
def _load_trips():
    gtfs = _gtfs_path()
    if not gtfs:
        return []
    trips_file = gtfs / "trips.csv"
    if not trips_file.exists():
        trips_file = gtfs / "trips.txt"
    if not trips_file.exists():
        return []

    trips = []
    with open(trips_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            trips.append(
                {
                    "route_id": _strip_quotes(row.get("route_id", "")),
                    "service_id": _strip_quotes(row.get("service_id", "")),
                    "trip_id": _strip_quotes(row.get("trip_id", "")),
                    "shape_id": _strip_quotes(row.get("shape_id", "")),
                }
            )
    return trips


@lru_cache(maxsize=1)
def _load_stop_times():
    gtfs = _gtfs_path()
    if not gtfs:
        return []
    st_file = gtfs / "stop_times.csv"
    if not st_file.exists():
        st_file = gtfs / "stop_times.txt"
    if not st_file.exists():
        return []

    entries = []
    with open(st_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                seq = int(_strip_quotes(row.get("stop_sequence", "0")))
            except (ValueError, TypeError):
                continue
            entries.append(
                {
                    "trip_id": _strip_quotes(row.get("trip_id", "")),
                    "stop_id": _strip_quotes(row.get("stop_id", "")),
                    "stop_sequence": seq,
                }
            )
    entries.sort(key=lambda e: (e["trip_id"], e["stop_sequence"]))
    return entries


@lru_cache(maxsize=1)
def _load_shapes():
    gtfs = _gtfs_path()
    if not gtfs:
        return {}
    shapes_file = gtfs / "shapes.csv"
    if not shapes_file.exists():
        shapes_file = gtfs / "shapes.txt"
    if not shapes_file.exists():
        return {}

    shapes = {}
    with open(shapes_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                lat = float(_strip_quotes(row.get("shape_pt_lat", "")))
                lon = float(_strip_quotes(row.get("shape_pt_lon", "")))
                seq = int(_strip_quotes(row.get("shape_pt_sequence", "0")))
            except (ValueError, TypeError):
                continue
            shape_id = _strip_quotes(row.get("shape_id", ""))
            shapes.setdefault(shape_id, []).append(
                {
                    "lat": lat,
                    "lon": lon,
                    "sequence": seq,
                }
            )

    for pts in shapes.values():
        pts.sort(key=lambda p: p["sequence"])
    return shapes


def _haversine(lat1, lon1, lat2, lon2):
    R = 6371000.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


def _agency_to_mode(agency_id):
    if "METRO" in agency_id.upper():
        return "metro"
    if agency_id.startswith("MB_"):
        return "microbus"
    return "bus"


def _route_type_to_transport(route_type):
    try:
        rt = int(route_type)
    except (ValueError, TypeError):
        return "bus"
    if rt == 1:
        return "metro"
    return "bus"


def _build_stop_routes():
    trips = _load_trips()
    stop_times = _load_stop_times()
    routes = _load_routes()

    route_map = {r["route_id"]: r for r in routes}

    trip_route_ids = {}
    for t in trips:
        trip_route_ids[t["trip_id"]] = t["route_id"]

    stop_routes = {}
    for entry in stop_times:
        route_id = trip_route_ids.get(entry["trip_id"])
        if not route_id:
            continue
        route = route_map.get(route_id)
        if not route:
            continue
        stop_id = entry["stop_id"]
        if stop_id not in stop_routes:
            stop_routes[stop_id] = {}
        stop_routes[stop_id][route_id] = {
            "route_id": route_id,
            "route_short_name": route["route_short_name"],
            "transport_mode": _agency_to_mode(route["agency_id"]),
        }

    return stop_routes


def get_nearby_stops(lat, lon, radius=500):
    stops = _load_stops()
    stop_routes = _build_stop_routes()
    results = []
    for s in stops:
        dist = _haversine(lat, lon, s["lat"], s["lon"])
        if dist <= radius:
            routes = list(stop_routes.get(s["stop_id"], {}).values())
            results.append(
                {
                    "stop_id": s["stop_id"],
                    "stop_name": s["stop_name"],
                    "lat": s["lat"],
                    "lon": s["lon"],
                    "distance_meters": round(dist, 1),
                    "lines": routes,
                }
            )
    results.sort(key=lambda x: x["distance_meters"])
    return results


def get_stop_detail(stop_id):
    stops = _load_stops()
    stop_routes = _build_stop_routes()

    for s in stops:
        if s["stop_id"] == stop_id:
            routes = list(stop_routes.get(stop_id, {}).values())
            return {
                "stop_id": s["stop_id"],
                "stop_name": s["stop_name"],
                "lat": s["lat"],
                "lon": s["lon"],
                "lines": routes,
            }
    return None


def get_all_lines():
    routes = _load_routes()
    results = []
    for r in routes:
        results.append(
            {
                "route_id": r["route_id"],
                "route_short_name": r["route_short_name"],
                "transport_mode": _agency_to_mode(r["agency_id"]),
                "route_long_name": r["route_long_name"],
                "route_color": r["route_color"],
            }
        )
    return results


def get_line_detail(route_id):
    routes = _load_routes()
    route = None
    for r in routes:
        if r["route_id"] == route_id:
            route = r
            break
    if not route:
        return None

    trips = _load_trips()
    stop_times = _load_stop_times()
    stops = _load_stops()
    shapes = _load_shapes()

    route_trips = [t for t in trips if t["route_id"] == route_id]

    stop_map = {s["stop_id"]: s for s in stops}

    representative_trip = route_trips[0] if route_trips else None
    ordered_stops = []
    polyline = []

    if representative_trip:
        trip_stops = [
            e for e in stop_times if e["trip_id"] == representative_trip["trip_id"]
        ]
        seen = set()
        for entry in trip_stops:
            sid = entry["stop_id"]
            if sid in seen:
                continue
            seen.add(sid)
            stop = stop_map.get(sid)
            if stop:
                ordered_stops.append(
                    {
                        "stop_id": stop["stop_id"],
                        "stop_name": stop["stop_name"],
                        "lat": stop["lat"],
                        "lon": stop["lon"],
                        "sequence": entry["stop_sequence"],
                    }
                )

        shape_id = representative_trip.get("shape_id", "")
        shape_pts = shapes.get(shape_id, [])
        polyline = [{"lat": p["lat"], "lon": p["lon"]} for p in shape_pts]

    return {
        "route_id": route["route_id"],
        "route_short_name": route["route_short_name"],
        "transport_mode": _agency_to_mode(route["agency_id"]),
        "route_long_name": route["route_long_name"],
        "route_color": route["route_color"],
        "stops": ordered_stops,
        "polyline": polyline,
    }


def clear_cache():
    _load_stops.cache_clear()
    _load_routes.cache_clear()
    _load_trips.cache_clear()
    _load_stop_times.cache_clear()
    _load_shapes.cache_clear()
