# Routing System

## Overview

The routing system is the core feature of Wslny. It computes public transit routes across Greater Cairo's bus, microbus, and metro networks using the A* algorithm running in a C++ gRPC service.

## Route Filter Types

Users can request routes filtered by transport mode:

| Enum | Name | Description |
|------|------|-------------|
| 1 | optimal | Best overall route across all transport modes |
| 2 | fastest | Shortest total duration |
| 3 | cheapest | Lowest estimated fare |
| 4 | bus_only | Uses only bus + walking |
| 5 | microbus_only | Uses only microbus + walking |
| 6 | metro_only | Uses only metro + walking |

## Request Modes

### Text Mode

User describes their trip in natural language (Arabic or English). The AI service extracts locations and geocodes them.

```json
POST /api/v1/route
{
  "text": "عايز اروح العباسيه من مسكن",
  "filter": 1,
  "current_location": { "lat": 30.12, "lon": 31.34 }
}
```

The `current_location` is optional — used as fallback when the AI can't extract origin from text.

### Map Pin Mode

User drops pins on a map. Coordinates go directly to the routing engine — the AI service is bypassed entirely for lower latency.

```json
POST /api/v1/route
{
  "origin": { "lat": 30.05, "lon": 31.24 },
  "destination": { "lat": 30.07, "lon": 31.28 },
  "filter": 3
}
```

### Search + Confirm Mode

For cases where the destination text is ambiguous:

1. `POST /api/v1/routes/search` — AI extracts destination; if ambiguous, returns suggestions
2. User selects a suggestion
3. `POST /api/v1/routes/search/confirm` — Confirmed coordinates produce the route

## How Routing Works

### 1. Coordinate Input

The routing engine receives origin and destination coordinates.

### 2. Stop Candidate Search

The engine finds all transit stops within walking distance (~500m) of both the origin and destination coordinates. These become candidate start/end nodes for the A* search.

### 3. A* Graph Search

For each requested mode combination:
- **optimal**: All edges (bus + metro + microbus + walking)
- **bus_only**: Only bus edges + walking transfers
- **metro_only**: Only metro edges + walking transfers
- **microbus_only**: Only microbus edges + walking transfers

The A* algorithm uses haversine distance as the heuristic. It searches from each origin candidate toward each destination candidate, finding the path with the lowest total duration.

### 4. Path Reconstruction

The best path is reconstructed from the search results. Each segment records:
- Start/end stop locations and names
- Transport method (bus, metro, microbus, walk)
- Number of stops
- Distance and duration
- The `trip_id` (used for polyline attachment)

### 5. Polyline Attachment

GTFS shapes provide the actual geographic path of each transit line. For each transit segment:

1. The segment's `trip_id` maps to a `shape_id` in the trips data
2. The shape's ordered `{lat, lon}` points are loaded from `shapes.csv` (~242,983 points)
3. The shape is sliced between the segment's start and end stops
4. The resulting polyline is attached to the `RouteSegment` in the gRPC response

This gives mobile clients the exact path to draw on a map.

### 6. Fare Estimation

After receiving the route from the engine, the Django API estimates fares:

| Transport | Calculation |
|-----------|-------------|
| Metro | Tiered by total metro stops across all metro segments: ≤9=8 EGP, ≤16=10, ≤23=15, ≤39=20, 40+=20 |
| Bus | 20 EGP per bus ride segment |
| Microbus | 10 EGP per microbus ride segment |

Fare values are configurable via environment variables.

## Route Response Structure

Every successful route response contains:

```json
{
  "request_id": "uuid",
  "source": "text | map",
  "filter": 1,
  "from_name": "origin name",
  "to_name": "destination name",
  "query": { "origin": {...}, "destination": {...} },
  "route": {
    "type": "optimal",
    "found": true,
    "totalDurationSeconds": 1800,
    "totalDurationFormatted": "30 min",
    "totalSegments": 3,
    "totalDistanceMeters": 8500.0,
    "estimatedFare": 30.0,
    "walkDistanceMeters": 450.0,
    "segments": [
      {
        "startLocation": { "lat": ..., "lon": ..., "name": "..." },
        "endLocation": { "lat": ..., "lon": ..., "name": "..." },
        "method": "walk | bus | metro | microbus",
        "numStops": 0,
        "distanceMeters": 450,
        "durationSeconds": 300,
        "polyline": [{ "lat": ..., "lon": ... }, ...]
      }
    ]
  }
}
```

## Route Alternatives

`POST /api/v1/routes/alternatives` returns **all found** route types (not just the selected one), sorted by duration. This lets users compare options:

```json
{
  "alternatives": [
    { "type": "metro_only", "totalDurationSeconds": 1500, ... },
    { "type": "bus_only", "totalDurationSeconds": 2400, ... },
    { "type": "optimal", "totalDurationSeconds": 1800, ... }
  ],
  "count": 3
}
```

## Route Feedback

After completing a route, users can submit feedback:

```json
POST /api/v1/routes/feedback
{
  "request_id": "uuid-from-route-response",
  "rating": 4,
  "comment": "Mostly accurate but transfer was confusing"
}
```

- Rating: 1 (poor) to 5 (excellent)
- One feedback per user per request_id (resubmission updates existing)
- Feedback is queryable by admins via analytics endpoints

## History

Every route request is persisted to `RouteHistory` with:
- Input data (text, coordinates, filter)
- Result data (route type, duration, distance, fare)
- Latency metrics (AI time, routing time, total time)
- Status (success/failed) and error information

This powers the admin analytics dashboard.
