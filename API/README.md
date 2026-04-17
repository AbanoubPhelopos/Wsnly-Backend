# Wslny API — Gateway & Orchestrator

The Wslny API is the public backend gateway for the platform. It handles authentication, request validation, service orchestration, persistence, admin analytics, and serves transit data to clients.

## Role In The System

- Exposes HTTP/JSON endpoints to web/mobile clients
- Enforces JWT security and role-based access control (User / Admin)
- Orchestrates internal gRPC calls to AI Service and Routing Engine
- Persists route history, feedback, and serves admin statistics
- Provides cached GTFS transit data (stops, lines, polylines)
- Manages user features (saved locations, favorites, preferences)

This is the control plane of the platform. Frontends must call this service only — never the AI or routing services directly.

## Communication Pattern

```text
Client ──HTTP/JSON──▶ Wslny API ──gRPC──▶ Ai-Service (text flow only)
                         │
                         ├──gRPC──▶ RoutingEngine (all flows)
                         │
                         ├──PostgreSQL (users, history, analytics)
                         │
                         └──Redis (caching)
```

## Flow Logic

### Text Input
1. Receive `POST /api/v1/route` with `text` + `filter`
2. Call AI gRPC `ExtractRoute` to get destination and optional source coordinates
3. If source is missing, use `current_location` if provided
4. Call Routing gRPC `GetRoute` with coordinates
5. Filter to one route by `filter` enum
6. Estimate fare and return standardized JSON
7. Persist to route history

### Map-Pin Input
1. Receive `POST /api/v1/route` with `origin` + `destination` coordinates
2. Skip AI service entirely
3. Call Routing gRPC directly
4. Filter, estimate fare, return JSON, persist history

### Search Flow
1. `POST /api/v1/routes/search` with `destination_text` + `current_location`
2. AI extracts destination coordinates
3. If ambiguous → return "Did you mean?" suggestions
4. `POST /api/v1/routes/search/confirm` with confirmed destination → return route

## API Endpoint Summary

All endpoints are versioned under `/api/v1/`.

### Authentication
| Method | Endpoint | Auth |
|--------|----------|------|
| POST | `/api/v1/auth/register` | Public |
| POST | `/api/v1/auth/login` | Public |
| POST | `/api/v1/auth/google-login` | Public |
| GET | `/api/v1/auth/profile` | JWT |
| PUT | `/api/v1/auth/profile` | JWT |
| POST | `/api/v1/auth/change-password` | JWT |
| POST | `/api/v1/auth/refresh` | Refresh Token |

### Routing
| Method | Endpoint | Auth |
|--------|----------|------|
| POST | `/api/v1/route` | JWT |
| GET | `/api/v1/route/history` | JWT |
| POST | `/api/v1/routes/search` | JWT |
| POST | `/api/v1/routes/search/confirm` | JWT |
| GET | `/api/v1/routes/metadata` | JWT |
| POST | `/api/v1/routes/alternatives` | JWT |
| POST | `/api/v1/routes/feedback` | JWT |

### Transit Data
| Method | Endpoint | Auth |
|--------|----------|------|
| GET | `/api/v1/stops/nearby` | JWT |
| GET | `/api/v1/stops/<id>` | JWT |
| GET | `/api/v1/lines` | JWT |
| GET | `/api/v1/lines/<id>` | JWT |

### User Features
| Method | Endpoint | Auth |
|--------|----------|------|
| GET/POST | `/api/v1/user/saved-locations` | JWT |
| GET/PUT/DELETE | `/api/v1/user/saved-locations/<id>` | JWT |
| GET/POST | `/api/v1/user/favorites` | JWT |
| GET/DELETE | `/api/v1/user/favorites/<id>` | JWT |
| GET/PUT | `/api/v1/user/preferences` | JWT |

### Admin
| Method | Endpoint | Auth |
|--------|----------|------|
| POST | `/api/v1/admin/change-role` | Admin |
| GET | `/api/v1/admin/users` | Admin |
| GET/PUT/DELETE | `/api/v1/admin/users/<id>` | Admin |
| GET | `/api/v1/admin/analytics/routes/overview` | Admin |
| GET | `/api/v1/admin/analytics/routes/top-routes` | Admin |
| GET | `/api/v1/admin/analytics/routes/filters` | Admin |
| GET | `/api/v1/admin/analytics/routes/unresolved` | Admin |
| GET | `/api/v1/admin/analytics/routes/query` | Admin |
| GET | `/api/v1/admin/analytics/users/overview` | Admin |
| GET | `/api/v1/admin/analytics/feedback` | Admin |
| GET | `/api/v1/admin/analytics/feedback/summary` | Admin |

### System
| Method | Endpoint | Auth |
|--------|----------|------|
| GET | `/api/health` | Public |
| GET | `/api/schema/` | Public |
| GET | `/api/docs/` | Public |

## Why This Matters

- Keeps frontend simple and secure (single domain + auth boundary)
- Prevents AI-to-Routing service chaining anti-pattern
- Allows efficient bypass path for map-pin requests (no AI overhead)
- Enables governance and observability (history + analytics) in one place
- Transit data endpoints let clients build stop/line browsers without calling routing

## Runtime Service

The runnable Django project is in `API/Wslny/`. See `API/Wslny/README.md` for startup details.
