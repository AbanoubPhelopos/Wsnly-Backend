# Shared Protobuf Contracts

This directory is the canonical source for gRPC contract files used by all services.

## Files

### `interpreter.proto` — AI Service Contract

- Service: `TransitInterpreter`
- RPC: `ExtractRoute(RouteRequest) -> RouteResponse`
- Used by: `Ai-Service` (server), `Wslny API` (client)
- Key fields:
  - `to_coordinates` is required for a usable extraction result
  - `from_coordinates` may be omitted for destination-only text; API uses client current location
  - `intent` indicates the type of extraction (e.g., "standard")

### `routing.proto` — Routing Engine Contract

- Service: `RoutingService`
- RPC: `GetRoute(RouteRequest) -> RouteResponse`
- Used by: `RoutingEngine` (server), `Wslny API` (client)
- Key fields:
  - Legacy single-route fields (steps, distance, duration) kept for backward compatibility
  - `query` and `routes[]` provide multi-option outputs (optimal, bus_only, metro_only, microbus_only)
  - `RouteSegment.polyline` contains GTFS shape points for map drawing (added in Phase 3)

## Synchronization

Service-local proto copies exist in:
- `Ai-Service/protos/interpreter.proto`
- `RoutingEngine/proto/routing.proto`

These must stay byte-compatible with the shared copies. The Django `entrypoint.sh` generates Python stubs from the shared copies at build time. The C++ engine generates stubs from its local copy during CMake build.

**When modifying protos**: Update the shared copy first, then sync to service-local copies.
