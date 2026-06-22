# Development Guide

## 🏗️ Project Conventions

### Architecture

```mermaid
graph TD
    A["🏗️ Clean Architecture"] --> B["📦 Core/Application<br/>Use Cases (CQRS)"]
    A --> C["📐 Core/Domain<br/>Constants, Errors"]
    A --> D["🧱 Infrastructure<br/>DB, gRPC, Models"]
    A --> E["📡 Presentation<br/>Views, URLs, Serializers"]

    B -.->|"depends on"| C
    D -.->|"depends on"| C
    E --> B
    E --> D

    style A fill:#e3f5fe,stroke:#0277bd
    style B fill:#e8f5e9,stroke:#2e7d32
    style C fill:#e1f5fe,stroke:#01579b
    style D fill:#fff3e0,stroke:#e65100
    style E fill:#fce4ec,stroke:#c2185b
```

```
Core/          → Domain logic, no framework dependencies
  Application/ → Use cases (CQRS: Commands + Queries)
  Domain/      → Constants, errors, interfaces
Infrastructure/ → External concerns (DB, gRPC, models)
Presentation/  → API layer (views, URLs, serializers, settings)
```

**Dependency rule**: Presentation → Application → Domain ← Infrastructure

---

## 🎨 Code Style

```mermaid
graph LR
    A["🎨 Code Style"] --> B["❌ No comments<br/>Self-documenting code"]
    A --> C["⚡ Async patterns<br/>where applicable"]
    A --> D["💉 Constructor injection<br/>for gRPC clients"]
    A --> E["📝 Structured logging<br/>getLogger(__name__)"]
    A --> F["🔐 All secrets<br/>via environment variables"]
    A --> G["💾 @lru_cache<br/>expensive data loading"]

    style A fill:#e3f5fe,stroke:#0277bd
```

- No comments in production code (self-documenting code preferred)
- Async patterns where applicable
- Constructor injection for gRPC clients (lazy initialization in views)
- Structured logging via `logging.getLogger(__name__)`
- All secrets via environment variables — never hardcoded
- `@lru_cache` for expensive data loading (GTFS)

---

## 🔄 CQRS Pattern

```mermaid
graph LR
    A["🔄 CQRS"] --> B["✏️ Command (Write)"]
    A --> C["📖 Query (Read)"]

    B --> D["ICommand interface"]
    B --> E["CommandHandler"]
    B --> F["Result"]

    C --> G["IQuery<T> interface"]
    C --> H["QueryHandler"]
    C --> F

    style A fill:#e3f5fe,stroke:#0277bd
    style B fill:#fff3e0,stroke:#e65100
    style C fill:#e8f5e9,stroke:#2e7d32
```

**Used for write operations and complex queries:**

```python
# Command (write)
@dataclass
class ChangeUserRoleCommand(ICommand):
    user_id: int
    new_role: str

class ChangeUserRoleCommandHandler:
    def handle(self, command: ChangeUserRoleCommand) -> Result[bool]:
        ...

# Query (read)
@dataclass
class GetUsersQuery(IQuery[List[UserDto]]):
    pass

class GetUsersQueryHandler:
    def handle(self, query: GetUsersQuery) -> Result[List[UserDto]]:
        ...
```

Simple read views (analytics, transit data) use direct ORM queries.

---

## 🔗 URL Routing

```mermaid
graph LR
    A["🔗 URL Routing"] --> B["Single file<br/>root_urls.py"]
    A --> C["Pattern<br/>api/v1/<resource>/<action>"]

    style A fill:#e3f5fe,stroke:#0277bd
    style B fill:#e8f5e9,stroke:#2e7d32
```

All URLs are in a single file: `src/Presentation/root_urls.py` (set as `ROOT_URLCONF`).

Pattern: `api/v1/<resource>/<action>`

---

## 📋 Adding a New Endpoint

### Step 1: Create the View

```mermaid
graph TD
    A["📝 Create View"] --> B["📍 Add to<br/>src/Presentation/views/"]
    B --> C["✏️ Implement<br/>APIView class"]
    C --> D["📋 Add @extend_schema<br/>for Swagger"]

    style A fill:#e3f5fe,stroke:#0277bd
```

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, inline_serializer

class MyNewView(APIView):
    permission_classes = [IsAuthenticated]  # or [IsAdminUser]

    @extend_schema(
        tags=["Tag Name"],
        summary="Short description",
        request=inline_serializer(name="Request", fields={...}),
        responses={200: None},
    )
    def post(self, request):
        return Response({"result": "data"})
```

### Step 2: Register the URL

```mermaid
graph TD
    A["🔗 Register URL"] --> B["📝 Add to<br/>root_urls.py"]
    B --> C["path('api/v1/...', MyNewView.as_view())"]

    style A fill:#e3f5fe,stroke:#0277bd
```

```python
from src.Presentation.views.my_views import MyNewView

urlpatterns = [
    path("api/v1/my-endpoint", MyNewView.as_view(), name="my-endpoint"),
]
```

### Step 3: Add Serializers (if needed)

Add to `src/Presentation/schemas.py` if the request/response needs Swagger documentation.

### Step 4: Add Models (if needed)

```mermaid
graph TD
    A["🗄️ Add Models"] --> B["Identity models<br/>src/Infrastructure/Identity/models.py"]
    A --> C["History models<br/>src/Infrastructure/History/models.py"]
    C --> D["📝 makemigrations && migrate"]

    style A fill:#e3f5fe,stroke:#0277bd
```

---

## 📡 Adding a New gRPC Method

### Step 1: Update the Proto

```mermaid
graph LR
    A["📝 Update Proto"] --> B["shared/protos/routing.proto"]
    A --> C["shared/protos/interpreter.proto"]

    style A fill:#e3f5fe,stroke:#0277bd
```

### Step 2: Sync to Service-Local Copies

```mermaid
graph LR
    A["🔄 Sync"] --> B["RoutingEngine/proto/routing.proto"]
    A --> C["Ai-Service/protos/interpreter.proto"]

    style A fill:#e3f5fe,stroke:#0277bd
```

### Step 3: Generate Stubs

| Environment | Generation |
|-------------|------------|
| **Django API** | `entrypoint.sh` auto-generates on container build |
| **C++ RoutingEngine** | CMake generates during build |

### Step 4: Implement

```mermaid
graph LR
    A["🛠️ Implement"] --> B["Server: service_impl.cpp<br/>or Server.py"]
    A --> C["Client: routing_client.py<br/>or ai_client.py"]

    style A fill:#e3f5fe,stroke:#0277bd
```

---

## 🧪 Testing

### Unit Tests

```mermaid
graph LR
    A["🧪 Unit Tests"] --> B["📍 Located in<br/>src/Presentation/tests/"]
    B --> C["pytest or<br/>python manage.py test"]

    style A fill:#e3f5fe,stroke:#0277bd
```

```bash
docker compose exec web python manage.py test
```

### Static Analysis (CI Pipeline)

```mermaid
graph TD
    A["🔍 Static Analysis"] --> B["🐍 Ruff linting"]
    A --> C["📝 py_compile<br/>syntax validation"]
    A --> D["🐳 Docker build<br/>all services"]

    style A fill:#e3f5fe,stroke:#0277bd
```

- **Ruff**: `ruff check API/Wslny/src/`
- **py_compile**: Syntax validation on all source files
- **Docker build**: All three services

### Manual Testing (Swagger UI)

```mermaid
graph TD
    A["🧪 Manual Testing"] --> B["1. Register/login<br/>get JWT token"]
    A --> C["2. Authorize<br/>Bearer <token>"]
    A --> D["3. Test endpoints<br/>interactively"]

    style A fill:#e3f5fe,stroke:#0277bd
```

Use Swagger UI at `http://localhost:8000/api/docs/`

---

## 📁 Key Files to Know

```mermaid
graph TD
    A["📁 Key Files"] --> B["settings.py<br/>All configuration (env-driven)"]
    A --> C["root_urls.py<br/>URL routing (ROOT_URLCONF)"]
    A --> D["schemas.py<br/>Shared serializers + filter enum"]
    A --> E["orchestrator.py<br/>Main routing orchestration"]
    A --> F["GrpcClients/__init__.py<br/>Thread-safe gRPC client singletons"]
    A --> G["GtfsDataService.py<br/>Cached GTFS data service"]
    A --> H["RouteAnalyticsService.py<br/>Analytics query engine"]

    style A fill:#e3f5fe,stroke:#0277bd
```

| File | Purpose |
|------|---------|
| `src/Presentation/settings.py` | All configuration (env-driven) |
| `src/Presentation/root_urls.py` | URL routing (ROOT_URLCONF) |
| `src/Presentation/schemas.py` | Shared serializers + filter enum |
| `src/Presentation/views/orchestrator.py` | Main routing orchestration (~1500 lines) |
| `src/Infrastructure/GrpcClients/__init__.py` | Thread-safe gRPC client singletons |
| `src/Core/Application/Transit/GtfsDataService.py` | Cached GTFS data service |
| `src/Core/Application/Admin/Services/RouteAnalyticsService.py` | Analytics query engine |

---

## 🗄️ Database Migrations

```mermaid
graph LR
    A["🗄️ Migrations"] --> B["📝 Create migration"]
    A --> C["✅ Apply migration"]
    A --> D["👀 Check status"]

    style A fill:#e3f5fe,stroke:#0277bd
```

```bash
# Create migration
docker compose exec web python manage.py makemigrations

# Apply migration
docker compose exec web python manage.py migrate

# Check migration status
docker compose exec web python manage.py showmigrations
```

---

## 🔧 Common Development Tasks

### Update GTFS Data

```mermaid
graph LR
    A["🗺️ Update GTFS"] --> B["1. Replace CSV files<br/>RoutingEngine/Database/"]
    B --> C["2. Rebuild routing engine"]
    C --> D["3. Restart service"]
    D --> E["4. Clear Django GTFS cache"]

    style A fill:#e3f5fe,stroke:#0277bd
```

1. Replace CSV files in `RoutingEngine/Database/`
2. Rebuild routing engine: `docker compose build routing-engine`
3. Restart: `docker compose up -d routing-engine`
4. Clear Django GTFS cache: restart the web service

### Change Fare Configuration

```mermaid
graph LR
    A["💰 Change Fares"] --> B["📝 Update env vars<br/>docker-compose.yml or .env"]

    style A fill:#e3f5fe,stroke:#0277bd
```

Update environment variables:
- `FARE_BUS_PER_RIDE`
- `FARE_MICROBUS_PER_RIDE`
- `FARE_METRO_UP_TO_9`, etc.

**No code changes needed** — fares are read from settings at runtime.

### Add a New Admin Analytics Endpoint

```mermaid
graph LR
    A["📊 New Analytics"] --> B["1. Add view to<br/>admin_views.py"]
    B --> C["2. Extend RouteAnalyticsBaseView"]
    C --> D["3. Register URL<br/>root_urls.py"]

    style A fill:#e3f5fe,stroke:#0277bd
```

1. Add the view to `src/Presentation/views/admin_views.py` or `admin_management_views.py`
2. Extend `RouteAnalyticsBaseView` for shared filter/pagination utilities
3. Register URL in `root_urls.py`

### Modify the Proto Contract

```mermaid
graph LR
    A["📝 Modify Proto"] --> B["1. Edit shared/protos/"]
    B --> C["2. Copy to RoutingEngine/proto/"]
    B --> D["3. Update server + client"]
    D --> E["4. Rebuild services"]

    style A fill:#e3f5fe,stroke:#0277bd
```

1. Edit `shared/protos/routing.proto`
2. Copy to `RoutingEngine/proto/routing.proto`
3. Update both server (C++ `service_impl.cpp`) and client (Python `routing_client.py`)
4. Rebuild both services