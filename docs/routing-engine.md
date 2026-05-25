# Routing Engine

## Overview

The **Routing Engine** is a C++ gRPC service that computes public transit routes using the A* algorithm over an in-memory graph built from GTFS data for Greater Cairo.

```mermaid
graph TD
    subgraph Startup["🚀 Startup"]
        A["📁 GTFS CSVs"] --> B["🔧 Parse CSVs"]
        B --> C["📊 Build Graph<br/>nodes = stops<br/>edges = transit + walking"]
        C --> D["🗺️ Load Shape Polylines<br/>~242K points"]
        D --> E["✅ Ready on Port 50051"]
    end

    subgraph Request["📥 Per Request"]
        F["📍 Coordinates"] --> G["🔍 Find Nearby Stops"]
        G --> H["⭐ A* Search<br/>for each mode"]
        H --> I["📋 Build Segments"]
        I --> J["✂️ Attach Polylines<br/>from GTFS shapes"]
        J --> K["📦 RouteResponse"]
    end

    style Startup fill:#e8f5e9,stroke:#2e7d32
    style Request fill:#fff3e0,stroke:#e65100
```

---

## Graph Construction

### Nodes (Stops)

```mermaid
graph LR
    A["stops.csv"] --> B["🚏 ~646 Nodes"]
    B --> C["🆔 stop_id"]
    B --> D["📝 stop_name"]
    B --> E["📍 lat, lon"]

    style A fill:#e3f2fd,stroke:#01579b
    style B fill:#e8f5e9,stroke:#2e7d32
```

Each transit stop becomes a graph node with: ID, name, latitude, longitude.

### Edges

```mermaid
graph TD
    A["Transit Edges"] --> B["Sequential stops in same trip"]
    A --> C["Weight: travel time"]
    A --> D["Attributes: route_id, trip_id,<br/>transport method"]

    E["Walking Transfer Edges"] --> F["Stops within ~500m radius"]
    E --> G["Weight: walking time<br/>(haversine distance)"]
    E --> H["Attribute: method = 'walk'"]

    style A fill:#e8f5e9,stroke:#2e7d32
    style E fill:#fff3e0,stroke:#e65100
```

| Edge Type | Source | Weight | Attributes |
|-----------|--------|--------|------------|
| **Transit** | `stop_times.csv` + `trips.csv` | Travel time | route_id, trip_id, transport method |
| **Walking** | Generated at startup | Walking time | method = "walk" |

### Transport Mode Classification

```mermaid
graph TD
    A["Route Type 1"] -->|"Metro"| B["🚇 Metro"]
    C["Agency ID contains 'METRO'"] -->|"Metro"| B
    D["Agency ID starts with 'MB_'"] -->|"Microbus"| E["🚐 Microbus"]
    F["Default"] -->|"Bus"| G["🚌 Bus"]

    style B fill:#e1f5fe,stroke:#01579b
    style E fill:#fff3e0,stroke:#e65100
    style G fill:#e8f5e9,stroke:#2e7d32
```

| Source | Mode |
|--------|------|
| Route type 1 | Metro |
| Agency ID contains "METRO" | Metro |
| Agency ID starts with "MB_" | Microbus |
| Default | Bus |

---

## A* Algorithm

### Heuristic

**Haversine distance** divided by a maximum speed constant. This is:
- **Admissible**: Never overestimates actual travel time
- **Consistent**: Satisfies triangle inequality for optimal path finding

### Search Process

```mermaid
graph TD
    A["📍 Origin Coordinates"] --> B["🚏 Find Origin<br/>Stop Candidates"]
    A -->|"repeat for each"| B

    C["📍 Destination Coordinates"] --> D["🚏 Find Destination<br/>Stop Candidates"]
    C -->|"repeat for each"| D

    B --> E["⭐ A* Search from<br/>each origin candidate"]
    D --> E

    E --> F{"Mode?"}
    F -->|optimal| G["All edges<br/>bus + metro + microbus + walk"]
    F -->|bus_only| H["Bus edges + walk only"]
    F -->|metro_only| I["Metro edges + walk only"]
    F -->|microbus_only| J["Microbus edges + walk only"]

    G & H & I & J --> K["✅ Select lowest<br/>duration path"]
    K --> L["🔄 Path reconstruction<br/>via parent pointers"]
    L --> M["📋 Record segment info<br/>trip_id, stops, distance"]

    style A fill:#e3f2fd,stroke:#01579b
    style C fill:#e3f2fd,stroke:#01579b
    style E fill:#fff3e0,stroke:#e65100
    style K fill:#e8f5e9,stroke:#2e7d32
```

### Path Reconstruction

```mermaid
graph LR
    A["✅ Best Path Found"] --> B["🔄 Trace back<br/>destination → origin"]
    B --> C["📋 For each segment"]
    C --> D["🚏 start/end stop<br/>location + name"]
    C --> E["🚌 transport method"]
    C --> F["📏 stops, distance, duration"]
    C --> G["🆔 trip_id"]

    style A fill:#e8f5e9,stroke:#2e7d32
    style G fill:#fff3e0,stroke:#e65100
```

---

## Polyline System

### Shape Loading

At startup, `graph.cpp::loadShapes()` reads all shape points:

```cpp
std::unordered_map<shape_id, vector<ShapePoint>> shapes;
```

Points are sorted by sequence number for accurate slicing.

### Trip-Shape Mapping

```mermaid
graph LR
    A["🆔 trip_id"] --> B["📁 trips.csv"]
    B --> C["🗺️ shape_id"]
    C --> D["📍 shapes.csv<br/>~242,983 points"]
    D --> E["✂️ Slice between<br/>stop sequences"]
    E --> F["🗺️ Polyline points<br/>for RouteSegment"]

    style A fill:#e3f2fd,stroke:#01579b
    style F fill:#e8f5e9,stroke:#2e7d32
```

Each trip has a `shape_id` (from `trips.csv`). During pathfinding, segments store their `trip_id`.

### Polyline Slicing

In `service_impl.cpp::populatePolyline()`:

1. Get segment's `trip_id` → find its `shape_id`
2. Load shape points from `shapes.csv`
3. Find sequence numbers for segment's start and end stops
4. Slice shape points between those sequences
5. Attach resulting `{lat, lon}` array to `RouteSegment`

---

## GTFS Data Files

```mermaid
graph TD
    A["📁 GTFS Files"] --> B["stops.csv<br/>~646 stops"]
    A --> C["routes.csv<br/>~441 routes"]
    A --> D["trips.csv<br/>~445 trips"]
    A --> E["stop_times.csv<br/>sequential edges"]
    A --> F["shapes.csv<br/>~242K polyline points"]
    A --> G["agency.csv<br/>transit agencies"]
    A --> H["calendar.csv<br/>service schedules"]

    style A fill:#e3f2fd,stroke:#01579b
    style F fill:#fff3e0,stroke:#e65100
```

| File | Records | Used For |
|------|---------|----------|
| `stops.csv` | ~646 | Graph nodes (stop locations) |
| `routes.csv` | ~441 | Route metadata + transport mode |
| `trips.csv` | ~445 | Trip → route + shape mapping |
| `stop_times.csv` | — | Sequential stop edges |
| `shapes.csv` | ~242,983 | Polyline points for map drawing |
| `agency.csv` | — | Agency → transport mode mapping |
| `calendar.csv` | — | Service schedules |

---

## Project Structure

```
RoutingEngine/
├── CMakeLists.txt          # CMake build (protobuf + grpc codegen)
├── Dockerfile              # Multi-stage build
├── proto/routing.proto     # Service definition (local proto copy)
├── include/
│   ├── types.hpp           # Data structures (Stop, Edge, ShapePoint)
│   ├── graph.hpp           # Graph class: loading, node/edge storage
│   └── pathfinder.hpp      # A* algorithm
├── src/
│   ├── graph.cpp           # GTFS parsing, graph building, shape loading
│   ├── pathfinder.cpp      # A* implementation with trip_id tracking
│   └── service_impl.cpp    # gRPC service + polyline population
├── Database/               # GTFS CSV data (Cairo transit)
│   ├── stops.csv           # ~646 stops
│   ├── routes.csv          # ~441 routes
│   ├── trips.csv           # ~445 trips
│   ├── stop_times.csv      # Sequential edges
│   ├── shapes.csv          # ~242K polyline points
│   ├── agency.csv          # Transit agencies
│   └── calendar.csv        # Service schedules
└── tools/
    └── validate_gtfs.py   # Data quality checker
```

---

## Data Quality Tool

```mermaid
graph LR
    A["python validate_gtfs.py"] --> B["📁 Check Database"]
    B --> C["❌ Orphan stops"]
    B --> D["🔗 Referential integrity"]
    B --> E["🔄 Duplicate records"]
    B --> F["⚠️ Suspicious clusters"]

    style A fill:#e3f2fd,stroke:#01579b
    style C & D & E & F fill:#ffebee,stroke:#c62828
```

```bash
python tools/validate_gtfs.py --db-path Database
```

**Checks:**
- Orphan stops (in `stops.csv` but not in `stop_times.csv`)
- Referential integrity (stop_ids, route_ids, trip_ids)
- Duplicate stop records
- Suspicious same-name clusters with large geographic spread

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GTFS_PATH` | `/app/Database` | Path to GTFS CSV files |

---

## Performance Characteristics

```mermaid
graph TD
    A["⚡ Performance"] --> B["🚀 Startup<br/>~1-2 seconds"]
    A --> C["⚡ Per Query<br/>Microseconds"]
    A --> D["💾 Memory<br/>~50MB"]
    A --> E["🔢 Concurrency<br/>Single-threaded gRPC"]

    style A fill:#e3f2fd,stroke:#01579b
    style B fill:#e8f5e9,stroke:#2e7d32
    style C fill:#e8f5e9,stroke:#2e7d32
    style D fill:#e8f5e9,stroke:#2e7d32
    style E fill:#e8f5e9,stroke:#2e7d32
```

| Metric | Value |
|--------|-------|
| **Startup** | ~1-2 seconds for Cairo dataset |
| **Per query** | Microseconds (small graph, ~646 nodes) |
| **Memory** | ~50MB (graph + shapes + indexes) |
| **Concurrency** | Single-threaded gRPC (sufficient for load) |

---

## Why C++

```mermaid
graph TD
    A["🛠️ Why C++?"] --> B["⚡ Deterministic Latency<br/>No GC pauses"]
    A --> C["💾 Zero-Copy Access<br/>In-memory data structures"]
    A --> D["🧠 Cache-Friendly<br/>Control memory layout"]
    A --> E["🔒 Type-Safe<br/>Protobuf codegen integration"]

    style A fill:#e3f2fd,stroke:#01579b
    style B fill:#e8f5e9,stroke:#2e7d32
    style C fill:#e8f5e9,stroke:#2e7d32
    style D fill:#e8f5e9,stroke:#2e7d32
    style E fill:#e8f5e9,stroke:#2e7d32
```

| Reason | Explanation |
|--------|-------------|
| **Deterministic latency** | CPU-intensive graph search without garbage collection pauses |
| **Zero-copy access** | In-memory data structures with direct pointer access |
| **Cache-friendly** | Control over memory layout for hot path optimization |
| **Type-safe** | Easy integration with protobuf C++ codegen |