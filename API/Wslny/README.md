# Wslny Runtime Service

This folder contains the runnable Django service for the Wslny API.

## Responsibilities

- HTTP API for authentication, routing, transit data, user features, and admin analytics
- gRPC clients for `Ai-Service` and `RoutingEngine` (thread-safe singletons)
- Route orchestration for text and map modes
- Route history and feedback persistence
- Fare estimation (metro tiered, bus/microbus per-ride)
- GTFS transit data service (cached CSV reader)
- OpenAPI/Swagger documentation

## Architecture Within This Service

```text
src/
├── Core/                    # Domain + Application (business logic)
│   ├── Application/
│   │   ├── Admin/           # Commands, queries, route analytics service
│   │   ├── Authentication/  # Register, login, Google OAuth, change password
│   │   ├── Transit/         # GTFS data service (cached CSV reader)
│   │   └── Common/          # CQRS interfaces (ICommand, IQuery), Result type
│   └── Domain/
│       ├── Constants/       # Roles (Admin, User)
│       └── Errors/          # Domain error definitions
├── Infrastructure/          # Persistence + external clients
│   ├── GrpcClients/         # Thread-safe gRPC client singletons
│   │   ├── __init__.py      # Lazy initialization with error capture
│   │   ├── ai_client.py     # AI service adapter
│   │   ├── routing_client.py # Routing engine adapter + polyline parsing
│   │   └── stubs/           # Auto-generated protobuf stubs (entrypoint.sh)
│   ├── History/             # RouteHistory + RouteFeedback models
│   └── Identity/            # User, SavedLocation, FavoriteRoute, UserPreferences
└── Presentation/            # API layer (views, URLs, settings, serializers)
    ├── settings.py          # All config driven by environment variables
    ├── root_urls.py         # Single ROOT_URLCONF for all endpoints
    ├── schemas.py           # Shared serializers + filter enum constants
    ├── permissions.py       # IsAdminUser permission class
    ├── logging_formatter.py # JSON structured logging formatter
    ├── views/
    │   ├── orchestrator.py           # Main route orchestration
    │   ├── auth_views.py             # Auth endpoints
    │   ├── admin_views.py            # Analytics views
    │   ├── admin_management_views.py # User CRUD + feedback analytics
    │   ├── route_views.py            # Alternatives + feedback
    │   ├── transit_views.py          # Stops + lines
    │   ├── user_views.py             # Saved locations, favorites, preferences
    │   └── health_views.py           # Health check (throttle-exempt)
    └── tests/
        └── test_routing_and_analytics.py
```

## Communication Design

```text
HTTP Client
    │
    ▼
Django View (Presentation layer)
    │
    ├── Uses CQRS Commands/Queries (Core/Application)
    │       │
    │       └── Handlers use Infrastructure models
    │
    ├── gRPC Client Singletons (Infrastructure/GrpcClients)
    │       ├── Ai-Service (text flow only)
    │       └── RoutingEngine (all flows)
    │
    └── PostgreSQL via Django ORM
            ├── Users, SavedLocations, Favorites, Preferences
            └── RouteHistory, RouteFeedback
```

## Environment Variables

### Database
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- `DB_CONN_MAX_AGE` (default: 60) — persistent connection lifetime

### gRPC Services
- `AI_GRPC_HOST`, `AI_GRPC_PORT`, `AI_GRPC_TIMEOUT_SECONDS`
- `ROUTING_GRPC_HOST`, `ROUTING_GRPC_PORT`, `ROUTING_GRPC_TIMEOUT_SECONDS`

### Cache
- `REDIS_URL` (default: `redis://redis:6379/0`)
- `GTFS_CACHE_TIMEOUT` (default: 86400 seconds)
- `ROUTE_CACHE_TIMEOUT` (default: 300 seconds)

### Fare Configuration
- `FARE_BUS_PER_RIDE` (default: 20 EGP)
- `FARE_MICROBUS_PER_RIDE` (default: 10 EGP)
- `FARE_METRO_UP_TO_9`, `FARE_METRO_UP_TO_16`, `FARE_METRO_UP_TO_23`, `FARE_METRO_ABOVE_39`

### Security
- `DJANGO_SECRET_KEY` — Django secret key
- `DEBUG` — Debug mode (default: True)
- `ALLOWED_HOSTS` — Comma-separated hosts (default: *)
- `CORS_ALLOWED_ORIGINS` — Comma-separated origins (empty = allow all)
- `ADMIN_PASSWORD` — Initial admin password (seeded on startup)

### Server
- `GUNICORN_WORKERS` (default: 4)
- `GUNICORN_THREADS` (default: 2)
- `GUNICORN_TIMEOUT` (default: 120)
- `LOG_LEVEL`, `APP_LOG_LEVEL` (default: INFO)

### GTFS Data
- `GTFS_PATH` — Path to GTFS CSV files (volume-mounted from RoutingEngine/Database)

## Startup

From repository root (recommended):

```bash
docker compose up --build
```

The `entrypoint.sh` script:
1. Generates gRPC Python stubs from proto files
2. Runs database migrations
3. Seeds admin user (email: admin@wslny.com, password from `ADMIN_PASSWORD` env var)
4. Starts Gunicorn

### API Docs

- Schema: `http://localhost:8000/api/schema/`
- Swagger UI: `http://localhost:8000/api/docs/`

Use `Bearer <jwt_token>` in Swagger Authorize to test protected endpoints.

## Route Filter Enum

| Value | Name | Description |
|-------|------|-------------|
| 1 | optimal | Best overall route |
| 2 | fastest | Shortest duration |
| 3 | cheapest | Lowest fare |
| 4 | bus_only | Bus routes only |
| 5 | microbus_only | Microbus routes only |
| 6 | metro_only | Metro routes only |

## Fare Calculation

| Transport | Method |
|-----------|--------|
| Metro | Tiered by total metro stops: ≤9=8 EGP, ≤16=10, ≤23=15, ≤39=20, 40+=20 |
| Bus | 20 EGP per bus ride segment |
| Microbus | 10 EGP per microbus ride segment |

## Rate Limiting

- Anonymous users: 30 requests/minute
- Authenticated users: 60 requests/minute
- Health endpoint: exempt from rate limiting

## Client Integration Examples

```bash
# Health check
curl http://localhost:8000/api/health

# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"pass123","first_name":"Test","last_name":"User","mobile_number":"+201234567890"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"pass123"}'

# Route by text
curl -X POST http://localhost:8000/api/v1/route \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"text": "عايز اروح العباسيه من مسكن", "filter": 1}'

# Route by coordinates
curl -X POST http://localhost:8000/api/v1/route \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"origin":{"lat":30.05,"lon":31.24},"destination":{"lat":30.07,"lon":31.28},"filter":3}'

# Search destination
curl -X POST http://localhost:8000/api/v1/routes/search \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"destination_text":"العباسية","current_location":{"lat":30.12,"lon":31.34},"filter":1}'

# Nearby stops
curl -X GET "http://localhost:8000/api/v1/stops/nearby?lat=30.05&lon=31.24&radius=500" \
  -H "Authorization: Bearer <token>"

# Route alternatives
curl -X POST http://localhost:8000/api/v1/routes/alternatives \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"origin_lat":30.05,"origin_lon":31.24,"destination_lat":30.07,"destination_lon":31.28}'
```
