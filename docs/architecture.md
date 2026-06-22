# Architecture

## System Overview

Wslny is a **polyglot microservices platform** with three application services and two infrastructure services, orchestrated behind a single Django API gateway.

```mermaid
graph TD
    subgraph Client["🖥️ Client (Web / Mobile)"]
        WEB[🌐 Browser]
        MOB[📱 Mobile App]
    end

    subgraph Gateway["🐍 Wslny API (Django + DRF)"]
        AUTH[🔐 Auth Layer<br/>JWT + OAuth]
        ORCH[🎯 Orchestrator<br/>Route Coordination]
        ADMIN[📊 Admin Panel<br/>Analytics]
        TRANSIT[🗺️ Transit Data<br/>Stops, Lines]
        USERS[👤 User Features<br/>Saved, Favorites]
    end

    subgraph Services["⚙️ Application Services"]
        AI[🤖 AI Service<br/>Python + gRPC<br/>Port 50052]
        ROUTING[⚡ RoutingEngine<br/>C++ + gRPC<br/>Port 50051]
    end

    subgraph Infra["📦 Infrastructure"]
        PG[("🗄️ PostgreSQL<br/>Port 5432")]
        REDIS[("📦 Redis<br/>Port 6379")]
    end

    WEB & MOB -->|"HTTP/JSON<br/>JWT Bearer"| AUTH
    AUTH --> ORCH
    ORCH --> TRANSIT
    ORCH --> ADMIN
    ORCH --> USERS

    ORCH --> |"gRPC<br/>Text Flow"| AI
    ORCH --> |"gRPC<br/>All Flows"| ROUTING

    ORCH --> PG
    ORCH --> REDIS

    AI --> |"gRPC Response"| ORCH
    ROUTING --> |"RouteResponse<br/>4 options"| ORCH

    style Client fill:#e1f5fe,stroke:#01579b
    style Gateway fill:#e8f5e9,stroke:#2e7d32
    style Services fill:#fff3e0,stroke:#e65100
    style Infra fill:#f3e5f5,stroke:#6a1b9a
```

---

## Design Principles

### 1. Single Entry Point

All client requests go through the **Wslny API**. Frontends **never** call AI or routing services directly.

```mermaid
graph LR
    A[🖥️ Client] -->|"Single Domain"| B[🐍 Wslny API]
    B -->|"Internal"| C[🤖 AI]
    B -->|"Internal"| D[⚡ Routing]
    B -->|"Internal"| E[🗄️ PostgreSQL]

    style B fill:#e8f5e9,stroke:#2e7d32
    style A fill:#e1f5fe,stroke:#01579b
```

**Benefits of Single Gateway:**
- Authentication & authorization centralized
- Input validation in one place
- Error handling uniform across all endpoints
- Request history & analytics unified
- Rate limiting at one point
- Security enforcement consolidated

### 2. Separation of Concerns

| Service | Responsibility | Does NOT Do |
|---------|---------------|-------------|
| **Wslny API** | Auth, orchestration, persistence, analytics | NLP, pathfinding |
| **AI Service** | NLP extraction, geocoding | Routing, user data |
| **RoutingEngine** | A* pathfinding over GTFS | NLP, HTTP, user data |

### 3. Clean Architecture / DDD-lite (Django API)

```mermaid
graph TD
    subgraph Presentation["📡 Presentation Layer"]
        VIEWS[🖥️ Views<br/>API endpoints]
        URLS[🔗 URL Routing]
        SCHEMAS[📋 Serializers<br/>Swagger docs]
        PERMS[🔐 Permissions<br/>IsAdminUser]
    end

    subgraph Core["🏛️ Core (Business Logic)"]
        APP[📦 Application<br/>Use Cases (CQRS)]
        DOMAIN[📐 Domain<br/>Constants, Errors]
    end

    subgraph Infrastructure["🧱 Infrastructure"]
        GRPC[📡 gRPC Clients<br/>Thread-safe singletons]
        MODELS[🗄️ Models<br/>Django ORM]
    end

    VIEWS -->|"Commands/Queries"| APP
    APP --> DOMAIN
    VIEWS --> GRPC
    APP --> MODELS

    style Presentation fill:#e1f5fe,stroke:#01579b
    style Core fill:#e8f5e9,stroke:#2e7d32
    style Infrastructure fill:#fff3e0,stroke:#e65100
```

---

## Communication Patterns

### Client ↔ API: HTTP/JSON + JWT

```mermaid
sequenceDiagram
    participant C as Client
    participant A as Wslny API

    C->>A: POST /api/v1/auth/register
    A-->>C: { token, refresh_token, user }

    C->>A: POST /api/v1/route (with JWT)
    A-->>C: { request_id, route, ... }
```

### API ↔ Services: gRPC (HTTP/2 + Protobuf)

```mermaid
graph LR
    A["🐍 Wslny API"] -->|"GetRoute()"| B["⚡ RoutingEngine"]
    A -->|"ExtractRoute()"| C["🤖 AI Service"]

    style A fill:#e8f5e9,stroke:#2e7d32
    style B fill:#fff3e0,stroke:#e65100
    style C fill:#fff3e0,stroke:#e65100
```

**Why gRPC?**
| Benefit | Description |
|---------|-------------|
| **Binary serialization** | Smaller payloads, faster than JSON |
| **Strong typing** | `.proto` contracts prevent schema drift |
| **Code generation** | Python + C++ from same proto files |
| **HTTP/2 multiplexing** | Reduced connection overhead |

---

## Data Flow

### Text Route Request

```mermaid
sequenceDiagram
    participant C as Client
    participant A as Wslny API
    participant AI as AI Service
    participant R as RoutingEngine
    participant DB as PostgreSQL

    C->>A: POST /api/v1/route<br/>{ text: "عايز اروح العباسيه من مسكن", filter: 1 }
    A->>A: Validate JWT + payload

    A->>AI: gRPC ExtractRoute(text)
    AI-->>A: from: "مسكن" (30.05, 31.34)<br/>to: "العباسية" (30.07, 31.28)

    alt Origin missing
        A->>A: Use current_location
    end

    A->>R: gRPC GetRoute(origin, destination)
    R-->>A: 4 routes (optimal, bus, metro, microbus)<br/>each with segments + polylines

    A->>A: Filter by filter enum
    A->>A: Estimate fare (metro tiered, bus/microbus per ride)
    A->>DB: Persist RouteHistory (with latency metrics)
    A-->>C: JSON response { request_id, route, fare }
```

### Map Route Request

```mermaid
sequenceDiagram
    participant C as Client
    participant A as Wslny API
    participant R as RoutingEngine
    participant DB as PostgreSQL

    C->>A: POST /api/v1/route<br/>{ origin: {lat, lon}, destination: {lat, lon}, filter: 3 }
    A->>A: Validate JWT + coordinates

    Note over A: AI Service Bypassed<br/>Direct routing call

    A->>R: gRPC GetRoute(origin, destination)
    R-->>A: 4 route options

    A->>A: Filter (cheapest)
    A->>A: Estimate fare
    A->>DB: Persist RouteHistory
    A-->>C: JSON response
```

### Search + Confirm Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant A as Wslny API
    participant AI as AI Service

    C->>A: POST /api/v1/routes/search<br/>{ destination_text: "العباسية", current_location: {...} }
    A->>AI: gRPC ExtractRoute(text)

    alt Exact match found
        AI-->>A: destination coordinates
        A-->>C: Route response
    else Ambiguous
        AI-->>A: Multiple suggestions
        A-->>C: { suggestions: ["العباسية", "العباسية站"] }
        C->>A: POST /api/v1/routes/search/confirm<br/>{ destination: {name, lat, lon} }
        A-->>C: Route response
    end
```

---

## Database Schema

### Users & Identity

```mermaid
erDiagram
    User {
        int id PK
        string email UK
        string first_name
        string last_name
        string mobile_number
        string gender
        string address
        string role
        bool is_active
        bool is_staff
        datetime date_joined
    }

    SavedLocation {
        int id PK
        int user_id FK
        string name
        float lat
        float lon
        string type
        datetime created_at
    }

    FavoriteRoute {
        int id PK
        int user_id FK
        string name
        float origin_lat
        float origin_lon
        float destination_lat
        float destination_lon
        string origin_name
        string destination_name
        int route_filter
        datetime created_at
    }

    UserPreferences {
        int id PK
        int user_id FK UK
        int default_filter
        int max_walk_distance
        bool accessibility_mode
    }

    User ||--o{ SavedLocation : "has"
    User ||--o{ FavoriteRoute : "has"
    User ||--|| UserPreferences : "has"
```

### History & Analytics

```mermaid
erDiagram
    RouteHistory {
        int id PK
        uuid request_id UK INDEX
        int user_id FK NULL
        string source_type
        string input_text
        int preference
        string selected_route_type
        string origin_name
        float origin_lat
        float origin_lon
        string destination_name
        float destination_lat
        float destination_lon
        string status
        string error_code
        string error_message
        float total_distance_meters
        int total_duration_seconds
        int step_count
        float estimated_fare
        int walk_distance_meters
        bool has_result
        string unresolved_reason
        float ai_latency_ms
        float routing_latency_ms
        float total_latency_ms
        datetime created_at INDEX
    }

    RouteFeedback {
        int id PK
        int user_id FK
        uuid request_id INDEX
        int rating
        string comment
        datetime created_at
    }

    User ||--o{ RouteHistory : "generates"
    User ||--o{ RouteFeedback : "submits"
    RouteHistory ||--|| RouteFeedback : "has"
```

---

## Caching Strategy

```mermaid
graph LR
    subgraph Layers["Cache Layers"]
        GTFS["📦 GTFS Data<br/>@lru_cache (process)"]
        API["🐍 API Responses<br/>Redis (django-redis)"]
        GEO["🗺️ Geocoding<br/>In-memory dict (process)"]
    end

    subgraph Data["Cached Data"]
        STOPS["~646 Stops"]
        ROUTES["~441 Routes"]
        SHAPES["~242K Polylines"]
        PLACES["Place → lat/lon"]
    end

    GTFS --> STOPS & ROUTES & SHAPES
    API --> STOPS
    GEO --> PLACES

    style GTFS fill:#e1f5fe,stroke:#01579b
    style API fill:#e8f5e9,stroke:#2e7d32
    style GEO fill:#fff3e0,stroke:#e65100
```

| Layer | Technology | What's Cached | TTL |
|-------|-----------|---------------|-----|
| **GTFS data** | Python `@lru_cache` | Stops, routes, trips, stop_times, shapes | Process lifetime |
| **API responses** | Redis (django-redis) | Configurable per endpoint | 300s (routes), 86400s (GTFS) |
| **Geocoding** | Python in-memory | Place name → coordinates | Process lifetime |

---

## Security Architecture

```mermaid
graph TD
    subgraph Security["🔐 Security Layers"]
        AUTH["JWT Auth<br/>60min access + 24h refresh"]
        OAUTH["Google OAuth<br/>ID token verification"]
        RATE["Rate Limiting<br/>30/min anon, 60/min auth"]
        CORS["CORS Policy<br/>Env-based origins"]
        RBAC["Role-Based Access<br/>User / Admin"]
    end

    subgraph Secrets["🔒 Secrets Management"]
        ENV["Environment Variables<br/>Never in code"]
        KEYS["API Keys, DB passwords<br/>ADMIN_PASSWORD, DJANGO_SECRET"]
    end

    style Security fill:#ffebee,stroke:#c62828
    style Secrets fill:#fff3e0,stroke:#e65100
```

| Concern | Implementation |
|---------|---------------|
| **Authentication** | JWT (access 60min + refresh 24h) |
| **OAuth** | Google ID token verification |
| **Authorization** | Role-based (User / Admin) via `IsAdminUser` |
| **Rate limiting** | 30/min anonymous, 60/min authenticated |
| **CORS** | Configurable origins via env var |
| **Secrets** | All via environment variables (never in code) |
| **Password** | PBKDF2 hashing, change requires current password |

---

## Error Handling

```mermaid
graph LR
    subgraph Errors["Error Codes"]
        E1["INVALID_REQUEST_MODE<br/>Both text & coords provided"]
        E2["INVALID_COORDINATES<br/>Missing or non-numeric"]
        E3["AI_EXTRACTION_FAILED<br/>AI couldn't extract locations"]
        E4["ROUTING_ERROR<br/>Routing engine error"]
        E5["NO_ROUTES_FOUND<br/>No viable route between points"]
        E6["DESTINATION_AMBIGUOUS<br/>Multiple matches for text"]
    end

    subgraph Response["Standard Error Response"]
        JSON["""request_id": "uuid"<br/>"error": {<br/>  "code": "...",<br/>  "message": "..."<br/>}"]
    end

    E1 & E2 & E3 & E4 & E5 & E6 --> JSON

    style Errors fill:#ffebee,stroke:#c62828
    style Response fill:#e1f5fe,stroke:#01579b
```

All route requests (success and failure) are recorded in `RouteHistory` with latency metrics for observability.

---

## Environment Variables

| Category | Variable | Default | Description |
|----------|----------|---------|-------------|
| **Security** | `DJANGO_SECRET_KEY` | insecure | Django secret key |
| **Security** | `DEBUG` | True | Debug mode |
| **Security** | `ALLOWED_HOSTS` | * | Comma-separated hosts |
| **Database** | `DB_NAME` | wslny | PostgreSQL database |
| **Database** | `DB_USER` | postgres | Database user |
| **Database** | `DB_PASSWORD` | postgres | Database password |
| **Database** | `DB_HOST` | db | Database host |
| **gRPC** | `AI_GRPC_HOST` | ai-service | AI service host |
| **gRPC** | `AI_GRPC_PORT` | 50052 | AI service port |
| **gRPC** | `ROUTING_GRPC_HOST` | routing-engine | Routing engine host |
| **gRPC** | `ROUTING_GRPC_PORT` | 50051 | Routing engine port |
| **Cache** | `REDIS_URL` | redis://redis:6379/0 | Redis connection |
| **Fares** | `FARE_BUS_PER_RIDE` | 20 | Bus fare (EGP) |
| **Fares** | `FARE_MICROBUS_PER_RIDE` | 10 | Microbus fare (EGP) |
| **Fares** | `FARE_METRO_UP_TO_9` | 8 | Metro ≤9 stops |
| **Server** | `GUNICORN_WORKERS` | 4 | Gunicorn workers |
| **Server** | `GUNICORN_THREADS` | 2 | Threads per worker |