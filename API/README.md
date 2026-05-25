# Wslny API — Gateway & Orchestrator

<!-- Badges -->
![Django](https://img.shields.io/badge/django-4.2-green)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![gRPC](https://img.shields.io/badge/gRPC-HTTP%2F2-orange)
![JWT](https://img.shields.io/badge/JWT-auth-yellow)

The Wslny API is the **public backend gateway** for the platform. It handles authentication, request validation, service orchestration, persistence, admin analytics, and serves transit data to clients.

> **Important**: Frontends must call this service only — never the AI or routing services directly.

---

## 🎯 Role In The System

```mermaid
graph LR
    Client["🖥️ Client"] -->|"HTTP/JSON + JWT"| API["🐍 Wslny API"]
    API --> |gRPC| AI["🤖 AI Service"]
    API --> |gRPC| Routing["⚡ RoutingEngine"]
    API --> PG[("🗄️ PostgreSQL")]
    API --> Redis[("📦 Redis")]

    style API fill:#e1f5fe
    style Client fill:#f3e5f5
```

| Responsibility | Description |
|----------------|-------------|
| **HTTP Gateway** | Exposes HTTP/JSON endpoints to web/mobile clients |
| **Auth & Security** | Enforces JWT security and role-based access control (User / Admin) |
| **Orchestration** | Coordinates internal gRPC calls to AI Service and Routing Engine |
| **Persistence** | Persists route history, feedback, and serves admin statistics |
| **Transit Data** | Provides cached GTFS transit data (stops, lines, polylines) |
| **User Features** | Manages saved locations, favorites, preferences |

---

## 🔄 Flow Logic

### Text Input (Natural Language)

```mermaid
sequenceDiagram
    participant C as Client
    participant A as Wslny API
    participant AI as AI Service
    participant R as RoutingEngine

    C->>A: POST /api/v1/route { text, filter }
    A->>AI: gRPC ExtractRoute(text)
    AI-->>A: from, to + coordinates
    alt Origin missing
        A->>A: Use current_location
    end
    A->>R: gRPC GetRoute(origin, destination)
    R-->>A: 4 route options
    A->>A: Filter by filter enum
    A->>A: Estimate fare
    A->>A: Persist RouteHistory
    A-->>C: JSON response
```

### Map-Pin Input (Coordinates Only)

```mermaid
sequenceDiagram
    participant C as Client
    participant A as Wslny API
    participant R as RoutingEngine

    C->>A: POST /api/v1/route { origin, destination, filter }
    Note over A: AI Service Bypassed
    A->>R: gRPC GetRoute(origin, destination)
    R-->>A: 4 route options
    A->>A: Filter, estimate fare, persist
    A-->>C: JSON response
```

### Search Flow (Destination Suggestions)

```mermaid
sequenceDiagram
    participant C as Client
    participant A as Wslny API
    participant AI as AI Service

    C->>A: POST /api/v1/routes/search { destination_text }
    A->>AI: gRPC ExtractRoute(text)
    AI-->>A: destination + coordinates

    alt Ambiguous
        A-->>C: "Did you mean?" suggestions
        C->>A: POST /api/v1/routes/search/confirm
    end
    A-->>C: Route response
```

---

## 📡 API Endpoint Summary

All endpoints are versioned under `/api/v1/`.

### Authentication

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/auth/register` | Public | Register new user |
| POST | `/api/v1/auth/login` | Public | Email/password login |
| POST | `/api/v1/auth/google-login` | Public | Google OAuth login |
| GET | `/api/v1/auth/profile` | JWT | Get user profile |
| PUT | `/api/v1/auth/profile` | JWT | Update user profile |
| POST | `/api/v1/auth/change-password` | JWT | Change password |
| POST | `/api/v1/auth/refresh` | Refresh Token | Refresh access token |

### Routing

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/route` | JWT | Get route by text or coordinates |
| GET | `/api/v1/route/history` | JWT | User's route history |
| POST | `/api/v1/routes/search` | JWT | Search destination with suggestions |
| POST | `/api/v1/routes/search/confirm` | JWT | Confirm destination and get route |
| GET | `/api/v1/routes/metadata` | JWT | Filter options and transport methods |
| POST | `/api/v1/routes/alternatives` | JWT | All viable route alternatives |
| POST | `/api/v1/routes/feedback` | JWT | Submit route rating (1-5) |

### Transit Data

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/stops/nearby` | JWT | Nearby stops with lines |
| GET | `/api/v1/stops/<id>` | JWT | Stop detail with passing lines |
| GET | `/api/v1/lines` | JWT | All transit lines |
| GET | `/api/v1/lines/<id>` | JWT | Line detail with stops + polyline |

### User Features

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET/POST | `/api/v1/user/saved-locations` | JWT | List / create saved locations |
| GET/PUT/DELETE | `/api/v1/user/saved-locations/<id>` | JWT | Retrieve / update / delete |
| GET/POST | `/api/v1/user/favorites` | JWT | List / create favorite routes |
| GET/DELETE | `/api/v1/user/favorites/<id>` | JWT | Retrieve / delete |
| GET/PUT | `/api/v1/user/preferences` | JWT | Get / update preferences |

### Admin

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/admin/change-role` | Admin | Change user role |
| GET | `/api/v1/admin/users` | Admin | List all users |
| GET/PUT/DELETE | `/api/v1/admin/users/<id>` | Admin | User detail + stats / update / deactivate |
| GET | `/api/v1/admin/analytics/routes/overview` | Admin | Route analytics summary |
| GET | `/api/v1/admin/analytics/routes/top-routes` | Admin | Most requested O→D pairs |
| GET | `/api/v1/admin/analytics/routes/filters` | Admin | Filter usage statistics |
| GET | `/api/v1/admin/analytics/routes/unresolved` | Admin | Failed queries analysis |
| GET | `/api/v1/admin/analytics/routes/query` | Admin | Generic composable analytics |
| GET | `/api/v1/admin/analytics/users/overview` | Admin | User growth + activity |
| GET | `/api/v1/admin/analytics/feedback` | Admin | Feedback list with filters |
| GET | `/api/v1/admin/analytics/feedback/summary` | Admin | Rating distribution + averages |

### System

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/health` | Public | Health check (DB + gRPC deps) |
| GET | `/api/schema/` | Public | OpenAPI 3 schema |
| GET | `/api/docs/` | Public | Swagger UI |

---

## 🏗️ Architecture

The Django API follows Clean Architecture / DDD-lite principles:

```text
src/
├── Core/                    # Domain + Application (business logic)
│   ├── Application/         # Use cases (CQRS pattern)
│   │   ├── Admin/          # Analytics commands & queries
│   │   ├── Authentication/ # Register, login, OAuth handlers
│   │   ├── Transit/        # GTFS data service (cached CSV)
│   │   └── Common/         # CQRS interfaces (ICommand, IQuery), Result type
│   └── Domain/             # Constants (Roles), Domain errors
├── Infrastructure/         # External concerns
│   ├── GrpcClients/        # Thread-safe gRPC client singletons
│   ├── History/            # RouteHistory, RouteFeedback models
│   └── Identity/           # User, SavedLocation, FavoriteRoute, UserPreferences
└── Presentation/           # API layer
    ├── settings.py         # All configuration (env-driven)
    ├── root_urls.py        # Single ROOT_URLCONF for all endpoints
    ├── schemas.py          # Shared serializers + filter enum
    ├── permissions.py      # IsAdminUser permission class
    ├── logging_formatter.py # JSON structured logging
    └── views/              # API view classes
```

---

## 🔧 Why This Design

| Benefit | Explanation |
|---------|-------------|
| **Single auth boundary** | Frontend only needs to manage one authentication domain |
| **Bypass path for map-pin** | Map-pin requests skip AI service entirely for lower latency |
| **Observability** | All requests logged with latency metrics for analytics |
| **Transit data independence** | Clients can browse stops/lines without calling routing |
| **Scalability** | Stateless API can scale horizontally behind a load balancer |

---

## 🚀 Running

**Recommended via root compose:**

```bash
docker compose up --build
```

The runnable Django project is in `API/Wslny/`. See [`API/Wslny/README.md`](Wslny/README.md) for startup details and environment variables.