# Routing Engine

## Overview

The Routing Engine is a C++ gRPC service that computes public transit routes using the A* algorithm over an in-memory graph built from GTFS data for Greater Cairo.

## Architecture

```text
Startup:
    GTFS CSVs → Parse → Build Graph (nodes + edges) → Load Shapes → Ready

Per Request:
    Coordinates → Find Nearby Stops → A* Search → Build Segments → Attach Polylines → Response
```

## Graph Construction

### Nodes

Each transit stop becomes a graph node:
- ID, name, latitude, longitude
- Loaded from `stops.csv` (~646 stops)

### Edges

Three types of edges connect nodes:

1. **Transit edges**: Sequential stops in the same trip are connected
   - Loaded from `stop_times.csv` + `trips.csv`
   - Weight: estimated travel time between stops
   - Attributes: route_id, trip_id, transport method (bus/metro/microbus)

2. **Walking transfer edges**: Nearby stops from different routes are connected
   - Generated during graph building (within ~500m radius)
   - Weight: walking time based on haversine distance
   - Attribute: method = "walk"

### Transport Mode Classification

The engine maps GTFS route data to transport modes:

| Source | Mode |
|--------|------|
| Route type 1 | Metro |
| Agency ID contains "METRO" | Metro |
| Agency ID starts with "MB_" | Microbus |
| Default | Bus |

## A* Algorithm

### Heuristic

Haversine distance divided by a maximum speed constant. This gives an optimistic estimate that never overestimates actual travel time.

### Search Process

1. **Origin candidates**: All stops within walking distance of origin coordinates
2. **Destination candidates**: All stops within walking distance of destination coordinates
3. **Search**: From each origin candidate, run A* toward destination candidates
4. **Mode filtering**: Different edge sets for each mode combination:
   - `optimal`: All edges (bus + metro + microbus + walk)
   - `bus_only`: Bus edges + walk edges only
   - `metro_only`: Metro edges + walk edges only
   - `microbus_only`: Microbus edges + walk edges only
5. **Selection**: For each mode, return the route with lowest total duration

### Path Reconstruction

After A* finds the optimal path:
1. Trace back from destination to origin through parent pointers
2. Record each segment's:
   - Start/end stop (location, name)
   - Transport method
   - Number of stops
   - Distance and duration
   - **trip_id** (used for polyline attachment)

## Polyline System

### Data Source

GTFS `shapes.csv` contains ~242,983 ordered `{lat, lon, sequence}` points grouped by `shape_id`.

### Shape Loading

At startup, `graph.cpp::loadShapes()` reads all shape points into a `std::unordered_map<shape_id, vector<ShapePoint>>`, sorted by sequence number.

### Trip-Shape Mapping

Each trip has a `shape_id` (from `trips.csv`). During pathfinding, segments store their `trip_id`, which maps to a `shape_id`.

### Polyline Slicing

In `service_impl.cpp::populatePolyline()`:
1. Get the segment's trip → find its shape_id → load shape points
2. Find the sequence numbers for the segment's start and end stops
3. Slice the shape points between those sequences
4. Attach the resulting `{lat, lon}` array to the `RouteSegment` proto message

This gives the frontend exact path data for drawing routes on a map.

## GTFS Data Files

| File | Records | Used For |
|------|---------|----------|
| `stops.csv` | ~646 | Graph nodes (stop locations) |
| `routes.csv` | ~441 | Route metadata + transport mode |
| `trips.csv` | ~445 | Trip → route + shape mapping |
| `stop_times.csv` | — | Sequential stop edges |
| `shapes.csv` | ~242,983 | Polyline points for map drawing |
| `agency.csv` | — | Agency → transport mode mapping |
| `calendar.csv` | — | Service schedules |

## Project Structure

```text
RoutingEngine/
├── CMakeLists.txt          # CMake build (protobuf + grpc codegen)
├── Dockerfile              # Multi-stage build
├── proto/routing.proto     # Service definition
├── include/
│   ├── types.hpp           # Data structures (Stop, Edge, ShapePoint, RouteSegment)
│   ├── graph.hpp           # Graph class: loading, node/edge storage, shape access
│   └── pathfinder.hpp      # A* algorithm
├── src/
│   ├── graph.cpp           # GTFS parsing, graph building, shape loading
│   ├── pathfinder.cpp      # A* implementation with trip_id tracking
│   └── service_impl.cpp    # gRPC service + polyline population
├── Database/               # GTFS CSV data
└── tools/
    └── validate_gtfs.py   # Data quality checker
```

## Data Quality Tool

```bash
python tools/validate_gtfs.py --db-path Database
```

Checks:
- Orphan stops (in `stops.csv` but not in `stop_times.csv`)
- Referential integrity (stop_ids, route_ids, trip_ids)
- Duplicate stop records
- Suspicious same-name clusters with large geographic spread

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GTFS_PATH` | `/app/Database` | Path to GTFS CSV files |

## Performance Characteristics

- **Startup**: Loads and indexes all GTFS data (~1-2 seconds for Cairo dataset)
- **Per query**: A* search completes in microseconds (small graph, ~646 nodes)
- **Memory**: ~50MB for Cairo dataset (graph + shapes + indexes)
- **Concurrency**: Single-threaded gRPC server (sufficient for expected load)

## Why C++

- Deterministic low-latency for CPU-intensive graph search
- Zero-copy access to in-memory data structures
- No garbage collection pauses
- Direct control over memory layout for cache-friendly data access
- Easy integration with protobuf C++ codegen
