# Shared Protobuf Contracts

<!-- Badges -->
![Protobuf](https://img.shields.io/badge/protobuf-v3-blue)
![gRPC](https://img.shields.io/badge/gRPC-HTTP%2F2-orange)

This directory is the **canonical source** for gRPC contract files used by all services.

---

## 📁 Files

### `interpreter.proto` — AI Service Contract

**Service**: `TransitInterpreter`
**RPC**: `ExtractRoute(RouteRequest) -> RouteResponse`
**Used by**: `Ai-Service` (server), `Wslny API` (client)

```protobuf
service TransitInterpreter {
  rpc ExtractRoute (RouteRequest) returns (RouteResponse) {}
}

message RouteRequest {
  string text = 1;
}

message RouteResponse {
  string from_location = 1;
  string to_location = 2;
  Location from_coordinates = 6;
  Location to_coordinates = 7;
  string intent = 8;
}
```

| Field | Description |
|-------|-------------|
| `to_coordinates` | **Required** for usable extraction result |
| `from_coordinates` | May be omitted for destination-only text; API uses client `current_location` |
| `intent` | Indicates extraction type (e.g., "standard") |

### `routing.proto` — Routing Engine Contract

**Service**: `RoutingService`
**RPC**: `GetRoute(RouteRequest) -> RouteResponse`
**Used by**: `RoutingEngine` (server), `Wslny API` (client)

```protobuf
service RoutingService {
  rpc GetRoute (RouteRequest) returns (RouteResponse) {}
}

message RouteRequest {
  Point origin = 1;       // lat/lon
  Point destination = 2;  // lat/lon
  string mode = 3;        // "optimal" (all modes tried internally)
}

message RouteResponse {
  repeated RouteStep steps = 1;           // Legacy single-route
  double total_distance_meters = 2;       // Legacy
  double total_duration_seconds = 3;      // Legacy
  Query query = 10;                       // Resolved input coordinates
  repeated RouteOption routes = 11;        // Multi-option: 4 route types
}

message RouteOption {
  string type = 1;                        // "optimal", "bus_only", etc.
  bool found = 2;
  int32 total_duration_seconds = 3;
  string total_duration_formatted = 4;
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

| Field | Description |
|-------|-------------|
| Legacy fields (`steps`, `distance`, `duration`) | Kept for backward compatibility |
| `query` + `routes[]` | Multi-option output (optimal, bus_only, metro_only, microbus_only) |
| `RouteSegment.polyline` | GTFS shape points for map drawing (added in Phase 3) |

---

## 🔄 Synchronization

Service-local proto copies exist in:

| Service | Proto Path |
|---------|------------|
| `Ai-Service` | `Ai-Service/protos/interpreter.proto` |
| `RoutingEngine` | `RoutingEngine/proto/routing.proto` |

**Important**: These must stay byte-compatible with the shared copies.

| Environment | Generation |
|-------------|------------|
| **Django API** | `entrypoint.sh` generates Python stubs at build time |
| **RoutingEngine** | CMake generates C++ stubs during build |
| **Ai-Service** | Docker build uses local proto copy |

---

## 🛠️ When Modifying Protos

1. **Update the shared copy first** (`shared/protos/`)
2. **Sync to service-local copies**:
   - `RoutingEngine/proto/routing.proto`
   - `Ai-Service/protos/interpreter.proto`
3. **Rebuild affected services** to regenerate stubs