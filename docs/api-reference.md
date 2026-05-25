# API Reference

> Complete endpoint documentation with request/response examples. All versioned endpoints are prefixed with `/api/v1/`.

---

## 🔐 Authentication

### Register

```
POST /api/v1/auth/register
```

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "first_name": "Ahmed",
  "last_name": "Ali",
  "mobile_number": "+201234567890",
  "gender": "male",
  "address": "Cairo, Egypt"
}
```

**Response (200):**
```json
{
  "token": "eyJhbGciOiJIUzI1...",
  "refresh_token": "eyJhbGciOiJIUzI1...",
  "user": {
    "email": "user@example.com",
    "first_name": "Ahmed",
    "last_name": "Ali"
  }
}
```

---

### Login

```
POST /api/v1/auth/login
```

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response (200):** Same as register.

---

### Google Login

```
POST /api/v1/auth/google-login
```

**Request:**
```json
{
  "id_token": "google-id-token-from-client-sdk"
}
```

**Response (200):** Same as register. Creates user if doesn't exist.

---

### Get Profile

```
GET /api/v1/auth/profile
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "email": "user@example.com",
  "first_name": "Ahmed",
  "last_name": "Ali",
  "mobile_number": "+201234567890",
  "gender": "male",
  "address": "Cairo, Egypt",
  "role": "User"
}
```

---

### Update Profile

```
PUT /api/v1/auth/profile
Authorization: Bearer <token>
```

**Request:** Any subset of profile fields.

---

### Change Password

```
POST /api/v1/auth/change-password
Authorization: Bearer <token>
```

**Request:**
```json
{
  "current_password": "oldpassword",
  "new_password": "newpassword"
}
```

---

### Refresh Token

```
POST /api/v1/auth/refresh
```

**Request:**
```json
{
  "refresh": "eyJhbGciOiJIUzI1..."
}
```

---

## 🛣️ Routing

### Get Route (Main Endpoint)

```
POST /api/v1/route
Authorization: Bearer <token>
```

**Text mode:**
```json
{
  "text": "عايز اروح العباسيه من مسكن",
  "filter": 1,
  "current_location": { "lat": 30.12, "lon": 31.34 }
}
```

**Map mode:**
```json
{
  "origin": { "lat": 30.05, "lon": 31.24 },
  "destination": { "lat": 30.07, "lon": 31.28 },
  "filter": 3
}
```

**Filter values:** `1=optimal`, `2=fastest`, `3=cheapest`, `4=bus_only`, `5=microbus_only`, `6=metro_only`

**Success Response (200):**
```json
{
  "request_id": "a1b2c3d4-...",
  "source": "text",
  "intent": "standard",
  "filter": 1,
  "from_name": "مسكن",
  "to_name": "العباسية",
  "query": {
    "origin": { "lat": 30.05, "lon": 31.34 },
    "destination": { "lat": 30.07, "lon": 31.28 }
  },
  "route": {
    "type": "optimal",
    "found": true,
    "totalDurationSeconds": 1800,
    "totalDurationFormatted": "30 min",
    "totalSegments": 3,
    "totalDistanceMeters": 8500.0,
    "estimatedFare": 30.0,
    "walkDistanceMeters": 450.0,
    "segments": [
      {
        "startLocation": { "lat": 30.05, "lon": 31.34, "name": "مسكن" },
        "endLocation": { "lat": 30.055, "lon": 31.30, "name": "محطة مترو مسكن" },
        "method": "walk",
        "numStops": 0,
        "distanceMeters": 450,
        "durationSeconds": 300,
        "polyline": [
          { "lat": 30.05, "lon": 31.34 },
          { "lat": 30.052, "lon": 31.33 },
          { "lat": 30.055, "lon": 31.30 }
        ]
      },
      {
        "startLocation": { "lat": 30.055, "lon": 31.30, "name": "محطة مترو مسكن" },
        "endLocation": { "lat": 30.072, "lon": 31.28, "name": "محطة مترو العباسية" },
        "method": "metro",
        "numStops": 8,
        "distanceMeters": 7200,
        "durationSeconds": 1200,
        "polyline": [ ... ]
      }
    ]
  }
}
```

**Error Response:**
```json
{
  "request_id": "uuid",
  "error": {
    "code": "NO_ROUTES_FOUND",
    "message": "No routes found between the specified locations."
  }
}
```

---

### Search Destination

```
POST /api/v1/routes/search
Authorization: Bearer <token>
```

**Request:**
```json
{
  "destination_text": "العباسية",
  "current_location": { "lat": 30.12, "lon": 31.34 },
  "filter": 1
}
```

**Direct match response (200):** Returns route directly.

**Suggestion response (200):**
```json
{
  "request_id": "uuid",
  "suggestions": [
    { "name": "العباسية", "lat": 30.0728, "lon": 31.2841 }
  ],
  "message": "Do you mean?"
}
```

---

### Confirm Search

```
POST /api/v1/routes/search/confirm
Authorization: Bearer <token>
```

**Request:**
```json
{
  "current_location": { "lat": 30.12, "lon": 31.34 },
  "destination": { "name": "العباسية", "lat": 30.0728, "lon": 31.2841 },
  "filter": 1
}
```

**Response:** Same as route success response.

---

### Route Metadata

```
GET /api/v1/routes/metadata
Authorization: Bearer <token>
```

Returns available filter options, transport methods, and query parameters.

---

### Route Alternatives

```
POST /api/v1/routes/alternatives
Authorization: Bearer <token>
```

**Request:**
```json
{
  "origin_lat": 30.05,
  "origin_lon": 31.24,
  "destination_lat": 30.07,
  "destination_lon": 31.28
}
```

**Response (200):**
```json
{
  "request_id": "uuid",
  "query": { "origin": {...}, "destination": {...} },
  "alternatives": [
    {
      "type": "metro_only",
      "totalDurationSeconds": 1500,
      "totalDurationFormatted": "25 min",
      "totalSegments": 2,
      "totalDistanceMeters": 7200,
      "segments": [ ... ]
    },
    {
      "type": "bus_only",
      "totalDurationSeconds": 2400,
      "totalDurationFormatted": "40 min",
      "totalSegments": 1,
      "totalDistanceMeters": 8500,
      "segments": [ ... ]
    }
  ],
  "count": 2
}
```

---

### Route Feedback

```
POST /api/v1/routes/feedback
Authorization: Bearer <token>
```

**Request:**
```json
{
  "request_id": "a1b2c3d4-...",
  "rating": 4,
  "comment": "Route was accurate, slight delay at transfer."
}
```

**Response (201):**
```json
{
  "message": "Feedback submitted.",
  "request_id": "a1b2c3d4-...",
  "rating": 4
}
```

Submitting feedback for the same request_id again updates the existing feedback.

---

### Route History

```
GET /api/v1/route/history
Authorization: Bearer <token>
```

**Response (200):** Array of route history items for the authenticated user.

---

## 🗺️ Transit Data

### Nearby Stops

```
GET /api/v1/stops/nearby?lat=30.05&lon=31.24&radius=500
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "stops": [
    {
      "stop_id": "stop_123",
      "stop_name": "مسكن",
      "lat": 30.05,
      "lon": 31.24,
      "distance_meters": 150.3,
      "lines": [
        { "route_id": "route_456", "route_short_name": "97", "transport_mode": "bus" }
      ]
    }
  ]
}
```

---

### Stop Detail

```
GET /api/v1/stops/<stop_id>
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "stop_id": "stop_123",
  "stop_name": "مسكن",
  "lat": 30.05,
  "lon": 31.24,
  "lines": [
    { "route_id": "route_456", "route_short_name": "97", "transport_mode": "bus" }
  ]
}
```

---

### All Lines

```
GET /api/v1/lines
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "lines": [
    {
      "route_id": "route_456",
      "route_short_name": "97",
      "transport_mode": "bus",
      "route_long_name": "مسكن - التحرير",
      "route_color": "FF0000"
    }
  ]
}
```

---

### Line Detail

```
GET /api/v1/lines/<route_id>
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "route_id": "route_456",
  "route_short_name": "97",
  "transport_mode": "bus",
  "route_long_name": "مسكن - التحرير",
  "route_color": "FF0000",
  "stops": [
    { "stop_id": "s1", "stop_name": "مسكن", "lat": 30.05, "lon": 31.34, "sequence": 1 },
    { "stop_id": "s2", "stop_name": "العباسية", "lat": 30.07, "lon": 31.28, "sequence": 2 }
  ],
  "polyline": [
    { "lat": 30.05, "lon": 31.34 },
    { "lat": 30.06, "lon": 31.31 },
    { "lat": 30.07, "lon": 31.28 }
  ]
}
```

---

## 👤 User Features

### Saved Locations

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/user/saved-locations` | List all |
| POST | `/api/v1/user/saved-locations` | Create |
| GET | `/api/v1/user/saved-locations/<id>` | Get one |
| PUT | `/api/v1/user/saved-locations/<id>` | Update |
| DELETE | `/api/v1/user/saved-locations/<id>` | Delete |

**Create Request:**
```json
{
  "name": "Home",
  "lat": 30.05,
  "lon": 31.24,
  "type": "home"
}
```

Types: `home`, `work`, `custom`

---

### Favorite Routes

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/user/favorites` | List all |
| POST | `/api/v1/user/favorites` | Create |
| GET | `/api/v1/user/favorites/<id>` | Get one |
| DELETE | `/api/v1/user/favorites/<id>` | Delete |

**Create Request:**
```json
{
  "name": "Home to Work",
  "origin_lat": 30.05,
  "origin_lon": 31.24,
  "origin_name": "Home",
  "destination_lat": 30.07,
  "destination_lon": 31.28,
  "destination_name": "Work",
  "route_filter": 1
}
```

---

### User Preferences

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/user/preferences` | Get preferences |
| PUT | `/api/v1/user/preferences` | Update preferences |

**Response:**
```json
{
  "default_filter": 1,
  "max_walk_distance": 1500,
  "accessibility_mode": false
}
```

---

## 👨‍💼 Admin Endpoints

> **Note**: All admin endpoints require `Admin` role.

### User Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/users` | List all users |
| GET | `/api/v1/admin/users/<id>` | User detail + stats |
| PUT | `/api/v1/admin/users/<id>` | Update user |
| DELETE | `/api/v1/admin/users/<id>` | Deactivate user |
| POST | `/api/v1/admin/change-role` | Change user role |

---

### Route Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/analytics/routes/overview` | Route analytics summary |
| GET | `/api/v1/admin/analytics/routes/top-routes` | Top requested O→D pairs |
| GET | `/api/v1/admin/analytics/routes/filters` | Filter usage statistics |
| GET | `/api/v1/admin/analytics/routes/unresolved` | Failed queries analysis |
| GET | `/api/v1/admin/analytics/routes/query` | Generic composable analytics |
| GET | `/api/v1/admin/analytics/users/overview` | User growth + activity |

---

### Feedback Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/analytics/feedback` | Paginated feedback list |
| GET | `/api/v1/admin/analytics/feedback/summary` | Rating distribution + averages |

---

## 🔧 System

### Health Check

```
GET /api/health
```

No auth required. Not rate-limited.

```json
{
  "status": "healthy",
  "checks": {
    "database": "healthy",
    "ai_service": "healthy",
    "routing_engine": "healthy"
  }
}
```

Returns `503` with `status: "degraded"` if any dependency is unhealthy.

---

### API Documentation

| Endpoint | Description |
|----------|-------------|
| `GET /api/schema/` | OpenAPI 3 schema (JSON) |
| `GET /api/docs/` | Swagger UI (interactive) |