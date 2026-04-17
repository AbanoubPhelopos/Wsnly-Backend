# Deployment Guide

## Docker Compose (Recommended)

The entire stack runs via Docker Compose with 5 services:

```text
docker-compose.yml
├── db          → PostgreSQL 15
├── redis       → Redis 7 (caching)
├── routing-engine → C++ gRPC (port 50051)
├── ai-service  → Python gRPC (port 50052)
└── web         → Django + Gunicorn (port 8000)
```

### Quick Start

```bash
# Clone
git clone https://github.com/AbanoubPhelopos/Wsnly-Backend.git
cd Wsnly-Backend

# Set required env vars
export GOOGLE_MAPS_API_KEY=your_key_here
export ADMIN_PASSWORD=your_secure_admin_password

# Build and start
docker compose up --build

# Verify
curl http://localhost:8000/api/health
```

### Service Dependencies

Services start in dependency order with health checks:

```text
db (healthy) → web (depends on db, redis, ai-service, routing-engine)
redis (healthy) → web
routing-engine (healthy) → ai-service (depends on routing-engine)
ai-service (healthy) → web
```

Each service has a health check:
- `db`: `pg_isready`
- `redis`: `redis-cli ping`
- `routing-engine`: `nc -z` on port 50051
- `ai-service`: Python socket connection on port 50052
- `web`: Python socket connection on port 8000

## Production Configuration

### Environment Variables

Create a `.env` file or set environment variables:

```bash
# Security (REQUIRED)
DJANGO_SECRET_KEY=your-long-random-secret-key
DEBUG=False
ALLOWED_HOSTS=api.yourdomain.com
ADMIN_PASSWORD=secure-admin-password

# Database
DB_NAME=wslny
DB_USER=postgres
DB_PASSWORD=secure-db-password
DB_HOST=db
DB_PORT=5432
DB_CONN_MAX_AGE=60

# gRPC Services
AI_GRPC_HOST=ai-service
AI_GRPC_PORT=50052
ROUTING_GRPC_HOST=routing-engine
ROUTING_GRPC_PORT=50051

# Redis
REDIS_URL=redis://redis:6379/0

# CORS
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Gunicorn
GUNICORN_WORKERS=4
GUNICORN_THREADS=2
GUNICORN_TIMEOUT=120

# Logging
LOG_LEVEL=INFO
APP_LOG_LEVEL=INFO

# AI Service
GOOGLE_MAPS_API_KEY=your-google-maps-key
```

### Gunicorn Configuration

The API runs on Gunicorn with configurable workers:

```python
# gunicorn.conf.py
workers = 4        # GUNICORN_WORKERS env var
threads = 2        # GUNICORN_THREADS env var
timeout = 120      # GUNICORN_TIMEOUT env var
max_requests = 1000    # Restart workers after 1000 requests (prevents memory leaks)
max_requests_jitter = 100  # Randomize to prevent all workers restarting at once
```

Rule of thumb: `(2 × CPU cores) + 1` workers.

### Database Connection Pooling

PostgreSQL connections are pooled with:
- `CONN_MAX_AGE=60` — Connections persist for 60 seconds
- `CONN_HEALTH_CHECKS=True` — Stale connections are checked before use

### Redis Caching

GTFS data and route results are cached in Redis:
- `GTFS_CACHE_TIMEOUT=86400` (24 hours for static transit data)
- `ROUTE_CACHE_TIMEOUT=300` (5 minutes for route results)

### Structured Logging

All logs are JSON-formatted for production log aggregation:

```json
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "level": "INFO",
  "logger": "src.Presentation.views.orchestrator",
  "message": "Route request completed",
  "module": "orchestrator",
  "function": "_record_history",
  "line": 380,
  "request_id": "a1b2c3d4-...",
  "user_id": 5,
  "status": "success",
  "total_latency_ms": 580.7
}
```

## CI/CD Pipeline

GitHub Actions runs on every push/PR to `main`:

### Lint Job
- Python 3.11 setup
- Install dependencies
- Ruff linting
- Python syntax check (py_compile on all source files)

### Docker Build Job
- Build Django API image
- Build Routing Engine image
- Build AI Service image

The workflow file is at `.github/workflows/ci.yml`.

## Startup Process

The Django API's `entrypoint.sh` runs on container start:

```bash
1. Generate gRPC Python stubs from proto files
2. Run database migrations (python manage.py migrate)
3. Seed admin user (python manage.py seed_admin)
4. Start Gunicorn (gunicorn -c gunicorn.conf.py)
```

The admin user is seeded with:
- Email: `admin@wslny.com`
- Password: from `ADMIN_PASSWORD` env var
- Role: Admin

## Scaling Considerations

### Horizontal Scaling

- The Django API is stateless — scale by adding more web containers
- gRPC client singletons are per-process (each Gunicorn worker has its own)
- Redis provides shared state across API instances

### Database

- PostgreSQL connection pooling reduces connection overhead
- For high load, consider PgBouncer as a connection pooler
- Route history can grow large — consider partitioning by date

### GTFS Data

- Loaded once at routing engine startup (~242K shape points, ~646 stops)
- GTFS data changes infrequently — engine restart required for updates
- Django API also caches GTFS data in-process via `@lru_cache`

### Cache Invalidation

- GTFS cache: Cleared on process restart
- Route cache: TTL-based (5 minutes default)
- Geocoding cache: In-process, cleared on AI service restart

## Monitoring

### Health Check

```bash
curl http://localhost:8000/api/health
```

Returns status of all dependencies (database, AI service, routing engine).

### Metrics from Route History

The `RouteHistory` model records per-request metrics:
- `ai_latency_ms` — Time spent in AI service
- `routing_latency_ms` — Time spent in routing engine
- `total_latency_ms` — Total request processing time
- `status` — Success or failure
- `error_code` — Specific error type

These can be queried via the admin analytics endpoints or directly from the database.

### Swagger UI

Interactive API documentation at `http://localhost:8000/api/docs/`. Supports JWT authorization for testing protected endpoints.
