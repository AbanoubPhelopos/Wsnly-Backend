# Architecture

This document describes the system architecture, design decisions, and how services communicate.

## System Overview

Wslny is a microservices platform with three application services and two infrastructure services:

```text
┌─────────────────────────────────────────────────────────────────┐
│                        Client (Web / Mobile)                     │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/JSON + JWT
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Wslny API (Django + DRF)                      │
│                      Port 8000 · Gunicorn                        │
│                                                                  │
│  Layers: Presentation → Application (CQRS) → Infrastructure     │
│                                                                  │
│  Connects to: PostgreSQL, Redis, AI gRPC, Routing gRPC          │
└────────────────────────────┬────────────────────────────────────┘
                             │ gRPC / Protobuf
              ┌──────────────┴──────────────┐
              ▼                             ▼
   ┌──────────────────┐          ┌──────────────────┐
   │   Ai-Service     │          │  RoutingEngine   │
   │   Port 50052     │          │  Port 50051      │
   │   Python + gRPC  │          │  C++ + gRPC      │
   └──────────────────┘          └──────────────────┘
```

## Design Principles

### Single Entry Point

All client requests go through the Wslny API. Frontends never call AI or routing services directly. This centralizes:
- Authentication and authorization
- Input validation
- Error handling and formatting
- Request history and analytics
- Rate limiting and security

### Separation of Concerns

Each service has a single, well-defined responsibility:

| Service | Responsibility | Does Not Do |
|---------|---------------|-------------|
| Wslny API | Auth, orchestration, persistence, analytics | NLP, pathfinding |
| Ai-Service | NLP extraction, geocoding | Routing, user management |
| RoutingEngine | A* pathfinding over GTFS | NLP, HTTP, user data |

### Communication

- **Client ↔ API**: HTTP/JSON with JWT Bearer authentication
- **API ↔ AI**: gRPC (synchronous, used only for text flow)
- **API ↔ Routing**: gRPC (synchronous, used for all flows)
- **API ↔ PostgreSQL**: Django ORM with connection pooling
- **API ↔ Redis**: django-redis for caching

### Why gRPC Internally

gRPC uses HTTP/2 with Protobuf serialization:
- Binary serialization is smaller and faster than JSON
- Strong typing via `.proto` contracts prevents schema drift
- Code generation for both Python and C++ from the same proto files
- HTTP/2 multiplexing reduces connection overhead

## Django API Architecture (Clean Architecture / DDD-lite)

```text
src/
├── Core/                          # Business logic (no framework dependencies)
│   ├── Application/               # Use cases
│   │   ├── Admin/                 # Commands, queries, analytics service
│   │   ├── Authentication/        # Register, login, OAuth commands
│   │   ├── Transit/               # GTFS data service
│   │   └── Common/                # CQRS interfaces, Result type
│   └── Domain/                    # Domain models, constants, errors
│       ├── Constants/             # Roles enum
│       └── Errors/                # Typed domain errors
├── Infrastructure/                # External concerns
│   ├── GrpcClients/               # Thread-safe gRPC client singletons
│   ├── History/                   # RouteHistory, RouteFeedback models
│   └── Identity/                  # User, SavedLocation, FavoriteRoute, UserPreferences
└── Presentation/                  # API layer
    ├── settings.py                # Environment-driven configuration
    ├── root_urls.py               # All URL routing
    ├── schemas.py                 # Shared serializers + constants
    ├── permissions.py             # Role-based access
    ├── logging_formatter.py       # JSON structured logging
    └── views/                     # API view classes
```

### CQRS Pattern

Commands and queries follow the CQRS pattern:

```text
Command (write)     →  ICommand  →  CommandHandler  →  Result
Query (read)        →  IQuery<T> →  QueryHandler    →  Result<T>
```

Used for: registration, login, role changes, user queries.

Analytics views and transit views use direct ORM queries (simpler for read-heavy analytics).

### gRPC Client Singletons

gRPC clients are lazy-initialized, thread-safe singletons in `Infrastructure/GrpcClients/__init__.py`:

```python
_routing_client = None          # Module-level singleton
_routing_lock = threading.Lock() # Thread safety

def get_routing_client():
    with _routing_lock:
        if _routing_client is None and "routing" not in _init_errors:
            _init_routing_client()
        return _routing_client, _init_errors.get("routing")
```

This ensures:
- One connection per service per Django process
- Thread-safe initialization
- Error capture if connection fails (service can still start)

## Data Flow

### Text Route Request

```text
POST /api/v1/route { text: "عايز اروح العباسيه من مسكن", filter: 1 }
    │
    ├── 1. Validate JWT + payload
    ├── 2. gRPC → Ai-Service: ExtractRoute(text)
    │       Returns: from="مسكن" (30.05, 31.34), to="العباسية" (30.07, 31.28)
    ├── 3. gRPC → RoutingEngine: GetRoute(origin, destination)
    │       Returns: 4 routes (optimal, bus_only, metro_only, microbus_only)
    │       Each route has segments with polyline points
    ├── 4. Filter to requested type (filter=1 → optimal)
    ├── 5. Estimate fare (metro tiered, bus/microbus per ride)
    ├── 6. Persist to RouteHistory (with latency metrics)
    └── 7. Return JSON response
```

### Map Route Request

```text
POST /api/v1/route { origin: {lat, lon}, destination: {lat, lon}, filter: 3 }
    │
    ├── 1. Validate JWT + coordinates
    ├── 2. Skip AI service (bypass)
    ├── 3. gRPC → RoutingEngine: GetRoute(origin, destination)
    ├── 4. Filter to cheapest (filter=3)
    ├── 5. Estimate fare
    ├── 6. Persist to RouteHistory
    └── 7. Return JSON response
```

### Search + Confirm Flow

```text
POST /api/v1/routes/search { destination_text: "العباسية", current_location: {...} }
    │
    ├── AI extracts destination
    ├── Ambiguous → return suggestions
    │
POST /api/v1/routes/search/confirm { destination: {name, lat, lon}, current_location: {...} }
    │
    ├── gRPC → RoutingEngine
    └── Return route
```

## Database Schema

### Users & Identity

```text
User (AbstractBaseUser)
├── email (unique, USERNAME_FIELD)
├── first_name, last_name
├── mobile_number
├── gender, address
├── role (Admin / User)
├── is_active, is_staff
└── date_joined

SavedLocation ──FK──▶ User
├── name, lat, lon, type (home/work/custom)
└── created_at

FavoriteRoute ──FK──▶ User
├── name, origin_lat/lon, destination_lat/lon
├── origin_name, destination_name
├── route_filter (integer enum)
└── created_at

UserPreferences ──OneToOne──▶ User
├── default_filter
├── max_walk_distance
└── accessibility_mode
```

### History & Analytics

```text
RouteHistory ──FK──▶ User (nullable)
├── request_id (UUID, indexed)
├── source_type (text/map)
├── input_text
├── preference, selected_route_type
├── origin_name/lat/lon, destination_name/lat/lon
├── status (success/failed)
├── error_code, error_message
├── total_distance_meters, total_duration_seconds
├── step_count, estimated_fare, walk_distance_meters
├── has_result, unresolved_reason
├── ai_latency_ms, routing_latency_ms, total_latency_ms
└── created_at (indexed)

RouteFeedback ──FK──▶ User
├── request_id (indexed)
├── rating (1-5)
├── comment
├── created_at
└── unique_together: (user, request_id)
```

## Caching Strategy

| Layer | Technology | What's Cached | TTL |
|-------|-----------|---------------|-----|
| GTFS data | Python `@lru_cache` | Stops, routes, trips, stop_times, shapes | Process lifetime |
| API responses | Redis (django-redis) | Configurable per endpoint | 300s (routes), 86400s (GTFS) |
| Geocoding | Python in-memory | Place name → coordinates | Process lifetime |

## Security Architecture

| Concern | Implementation |
|---------|---------------|
| Authentication | JWT (access 60min + refresh 24h) |
| OAuth | Google ID token verification |
| Authorization | Role-based (User / Admin) via `IsAdminUser` permission |
| Rate limiting | 30/min anonymous, 60/min authenticated |
| CORS | Configurable origins via env var |
| Secrets | All via environment variables (never in code) |
| Admin seeding | Password from `ADMIN_PASSWORD` env var |
| Password change | Requires current password verification |

## Error Handling

The API uses a consistent error response format:

```json
{
    "request_id": "uuid",
    "error": {
        "code": "ERROR_CODE",
        "message": "Human-readable description"
    }
}
```

Error codes include:
- `INVALID_REQUEST_MODE` — Both text and coordinates provided
- `INVALID_COORDINATES` — Missing or non-numeric coordinates
- `AI_EXTRACTION_FAILED` — AI service could not extract locations
- `ROUTING_ERROR` — Routing engine returned an error
- `NO_ROUTES_FOUND` — No viable routes between locations
- `SERVICE_CONFIGURATION_ERROR` — gRPC client not initialized
- `DESTINATION_AMBIGUOUS` — Multiple matches for destination text

All route requests (success and failure) are recorded in `RouteHistory` with latency metrics for observability.
