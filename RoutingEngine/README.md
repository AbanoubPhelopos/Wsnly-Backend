# RoutingEngine — C++ A* Transit Pathfinding

RoutingEngine is a high-performance C++ gRPC service that computes routes over Greater Cairo's public transit network using the A* algorithm on an in-memory GTFS graph.

## Responsibilities

- Load GTFS CSV data into an in-memory graph at startup
- Build transit edges (bus, metro, microbus) and walking transfer edges
- Compute candidate routes with A*-based search across multiple mode combinations
- Return multi-option routes with segments, metrics, and map polylines
- Shape point slicing between stops for accurate map drawing

RoutingEngine does **not** parse natural language. It operates exclusively on coordinates.

## How It Works

```text
Startup:
    GTFS CSVs (stops, routes, trips, stop_times, shapes)
                │
                ▼
    Parse into in-memory graph
    (nodes = stops, edges = transit + walking transfers)
    Load shape polylines per trip
                │
                ▼
    Ready for queries on port 50051

Per Request:
    Coordinates (origin, destination)
                │
                ▼
    Find nearby stop candidates (origin + destination)
                │
                ▼
    Run A* for each mode combination:
    ├── optimal    (all modes)
    ├── bus_only   (bus + walking)
    ├── metro_only (metro + walking)
    └── microbus_only (microbus + walking)
                │
                ▼
    For each found route:
    ├── Build segments (start/end stops, method, distance, duration)
    ├── Attach polyline points (from GTFS shapes, sliced between stops)
    └── Calculate totals (duration, distance, segment count)
                │
                ▼
    Return gRPC RouteResponse (4 route options)
```

## Communication

```text
Wslny API ──gRPC GetRoute(origin, destination)──▶ RoutingEngine
RoutingEngine ──gRPC RouteResponse(4 routes with segments + polyline)──▶ Wslny API
```

Both text and map-pin user requests end up here after orchestration in the Wslny API.

## gRPC Contract

- Service: `RoutingService`
- RPC: `GetRoute(RouteRequest) -> RouteResponse`
- Proto source: `shared/protos/routing.proto`

### Request

```protobuf
message RouteRequest {
  Point origin = 1;       // lat/lon
  Point destination = 2;  // lat/lon
  string mode = 3;        // "optimal" (all modes are tried internally)
}
```

### Response

```protobuf
message RouteResponse {
  repeated RouteStep steps = 1;           // Legacy single-route
  double total_distance_meters = 2;       // Legacy
  double total_duration_seconds = 3;      // Legacy
  Query query = 10;                       // Resolved input coordinates
  repeated RouteOption routes = 11;       // Multi-option: 4 route types
}

message RouteOption {
  string type = 1;                        // "optimal", "bus_only", etc.
  bool found = 2;
  int32 total_duration_seconds = 3;
  string total_duration_formatted = 4;    // "25 min"
  int32 total_segments = 5;
  repeated RouteSegment segments = 6;
  double total_distance_meters = 7;
}

message RouteSegment {
  Point start_location = 1;
  string start_name = 2;
  Point end_location = 3;
  string end_name = 4;
  string method = 5;                      // "bus", "metro", "microbus", "walk"
  int32 num_stops = 6;
  int32 distance_meters = 7;
  int32 duration_seconds = 8;
  repeated Point polyline = 9;            // GTFS shape points for map drawing
}
```

## GTFS Data Loading

| File | Description | Loaded Into |
|------|-------------|-------------|
| `stops.csv` | ~646 transit stops (id, name, lat, lon) | Graph nodes |
| `routes.csv` | ~441 route definitions (id, agency, type) | Route metadata |
| `trips.csv` | ~445 trips (route, service, shape_id) | Trip → route + shape mapping |
| `stop_times.csv` | Stop sequences per trip | Edges (sequential stops connected) |
| `shapes.csv` | ~242,983 polyline points | Per-trip polylines for map drawing |
| `agency.csv` | Transit agencies | Agency → transport mode mapping |
| `calendar.csv` | Service schedules | Service day filtering |

### Shape Polyline Logic

1. Each trip has a `shape_id` linking to `shapes.csv`
2. `shapes.csv` contains ordered `{lat, lon, sequence}` points per shape
3. During pathfinding, each segment stores its `trip_id`
4. In `service_impl.cpp`, `populatePolyline()` looks up the shape for the segment's trip
5. The shape is sliced between the segment's start and end stops to get only the relevant portion
6. The resulting polyline points are attached to each `RouteSegment` in the response

### Walking Transfers

The engine adds walking edges between stops that are within a configurable radius (~500m). This allows transfers between different transit lines at different stops.

## Project Structure

```text
RoutingEngine/
├── CMakeLists.txt          # CMake build configuration
├── Dockerfile              # Multi-stage build (cmake + runtime)
├── proto/routing.proto     # Local proto copy for C++ codegen
├── include/
│   ├── types.hpp           # Data structures (Stop, Route, Segment, ShapePoint)
│   ├── graph.hpp           # Graph class: GTFS loading, node/edge storage
│   └── pathfinder.hpp      # A* search algorithm
├── src/
│   ├── graph.cpp           # GTFS parsing, graph building, shape loading
│   ├── pathfinder.cpp      # A* implementation with trip_id tracking
│   └── service_impl.cpp    # gRPC service: request handling, polyline population
├── Database/               # GTFS CSV data (Greater Cairo)
│   ├── stops.csv
│   ├── routes.csv
│   ├── trips.csv
│   ├── stop_times.csv
│   ├── shapes.csv
│   ├── agency.csv
│   └── calendar.csv
└── tools/
    └── validate_gtfs.py   # Data quality validation tool
```

## A* Algorithm Details

The pathfinder uses A* search with the haversine distance heuristic:

1. **Origin candidates**: Find all stops within walking distance of the origin coordinates
2. **Destination candidates**: Find all stops within walking distance of the destination coordinates
3. **Graph search**: From each origin candidate, run A* toward destination candidates
4. **Mode filtering**: Different search configurations for bus_only, metro_only, microbus_only, optimal
5. **Path reconstruction**: Trace back from destination to origin, recording each segment's trip_id
6. **Result**: For each mode, return the best route found (lowest duration)

## Data Quality Tool

```bash
python RoutingEngine/tools/validate_gtfs.py --db-path RoutingEngine/Database
```

Checks for:
- Orphan stops not referenced by `stop_times.csv`
- Referential integrity across stops/trips/routes/stop_times
- Exact duplicate stop records
- Suspicious same-name stop clusters with large geographic spread

## Required Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `GTFS_PATH` | `/app/Database` | Path to GTFS CSV files |

## Running

Recommended via root compose:

```bash
docker compose up --build
```

Standalone:

```bash
docker build -t routing-engine RoutingEngine
docker run -p 50051:50051 -e GTFS_PATH=/app/Database routing-engine
```

## Why C++

- Graph search is CPU-intensive — C++ gives deterministic low-latency responses
- In-memory data structure for ~646 nodes and ~242K shape points with zero-copy access
- A* with custom heuristic runs in microseconds per query
- Isolates compute-heavy pathfinding from web/API concerns in Django
