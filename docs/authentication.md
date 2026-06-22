# Authentication & Security

## Overview

```mermaid
graph LR
    A["🔐 Auth System"] --> B["JWT Tokens<br/>60min access + 24h refresh"]
    A --> C["🔑 OAuth<br/>Google Sign-In"]
    A --> D["👥 RBAC<br/>User / Admin"]

    style A fill:#e3f5fe,stroke:#0277bd
    style B fill:#e8f5e9,stroke:#2e7d32
    style C fill:#fff3e0,stroke:#e65100
    style D fill:#fce4ec,stroke:#c2185b
```

Wslny uses **JWT (JSON Web Tokens)** for authentication with **role-based access control**. All protected endpoints require a valid Bearer token.

---

## 🔑 Authentication Methods

### Email/Password

```mermaid
sequenceDiagram
    participant U as User
    participant A as Wslny API

    U->>A: POST /api/v1/auth/register
    A-->>U: { token, refresh_token, user }

    U->>A: POST /api/v1/auth/login
    A-->>U: { token, refresh_token, user }
```

1. **Register**: `POST /api/v1/auth/register` with email, password, name, phone
2. **Login**: `POST /api/v1/auth/login` with email and password
3. Both return `{ token, refresh_token, user }`

### Google OAuth

```mermaid
sequenceDiagram
    participant U as User
    participant G as Google
    participant A as Wslny API

    U->>G: Google Sign-In SDK
    G-->>U: Google ID Token
    U->>A: POST /api/v1/auth/google-login { id_token }
    A->>G: Verify token
    G-->>A: Token valid
    A-->>U: { token, refresh_token, user }
```

1. Client obtains Google ID token from Google Sign-In SDK
2. `POST /api/v1/auth/google-login` with `id_token`
3. Server verifies token with Google, creates user if new, returns JWT

---

## 🔐 JWT Configuration

```mermaid
graph LR
    A["JWT Config"] --> B["⏱️ Access Token<br/>60 minutes"]
    A --> C["🔄 Refresh Token<br/>24 hours"]
    A --> D["🔏 Algorithm<br/>HS256"]
    A --> E["🔑 Secret<br/>DJANGO_SECRET_KEY env var"]

    style A fill:#e3f5fe,stroke:#0277bd
    style B fill:#e8f5e9,stroke:#2e7d32
    style C fill:#e8f5e9,stroke:#2e7d32
```

| Setting | Value |
|---------|-------|
| Access token lifetime | 60 minutes |
| Refresh token lifetime | 24 hours |
| Algorithm | HS256 |
| Secret | From `DJANGO_SECRET_KEY` env var |

### Token Refresh

```
POST /api/v1/auth/refresh
Body: { "refresh": "<refresh_token>" }
```

Returns a new access token. Refresh tokens themselves are **not rotated**.

---

## 👥 Roles

```mermaid
graph TD
    A["👥 Roles"] --> B["👤 User<br/>Default role<br/>User endpoints"]
    A --> C["👨‍💼 Admin<br/>Elevated role<br/>User + Admin endpoints"]

    style A fill:#e3f5fe,stroke:#0277bd
    style B fill:#e8f5e9,stroke:#2e7d32
    style C fill:#fce4ec,stroke:#c2185b
```

| Role | Description | Access |
|------|-------------|--------|
| `User` | Default role | All user endpoints |
| `Admin` | Elevated role | All user + admin endpoints |

### Role Assignment

- New users get `User` role by default
- Admin role is assigned via `POST /api/v1/admin/change-role` (admin-only)
- Initial admin is seeded on startup with password from `ADMIN_PASSWORD` env var

### Admin Check

```mermaid
graph LR
    A["Request"] --> B["IsAdminUser<br/>permission class"]
    B --> C{"user.role<br/>== 'Admin'?"}
    C -->|Yes| D["✅ Allow"]
    C -->|No| E["❌ Deny 403"]

    style B fill:#fff3e0,stroke:#e65100
    style D fill:#e8f5e9,stroke:#2e7d32
    style E fill:#ffebee,stroke:#c62828
```

The `IsAdminUser` permission class checks `request.user.role == "Admin"`. Enforced at the view level.

---

## 🔓 Public vs Protected Endpoints

```mermaid
graph TD
    A["Endpoints"] --> B["🔓 Public<br/>No auth required"]
    A --> C["🔐 Protected<br/>JWT required"]

    B --> D["POST /api/v1/auth/register"]
    B --> E["POST /api/v1/auth/login"]
    B --> F["POST /api/v1/auth/google-login"]
    B --> G["GET /api/health"]
    B --> H["GET /api/schema/"]
    B --> I["GET /api/docs/"]

    style B fill:#e8f5e9,stroke:#2e7d32
    style C fill:#ffebee,stroke:#c62828
```

**Public endpoints** (no authentication required):
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/google-login`
- `GET /api/health`
- `GET /api/schema/`
- `GET /api/docs/`

---

## 🛡️ Security Measures

### Secrets Management

```mermaid
graph LR
    A["🔒 Secrets"] --> B["❌ Never in code"]
    A --> C["✅ Always via env vars"]

    style A fill:#ffebee,stroke:#c62828
    style C fill:#e8f5e9,stroke:#2e7d32
```

All sensitive values are read from environment variables:
- `DJANGO_SECRET_KEY`
- `DB_PASSWORD`
- `ADMIN_PASSWORD`
- `GOOGLE_MAPS_API_KEY`

### CORS Configuration

```mermaid
graph LR
    A["🌐 CORS"] --> B["CORS_ALLOWED_ORIGINS<br/>Comma-separated<br/>env var"]
    B --> C["Empty = Allow all<br/>Development mode"]
    B --> D["Credentials allowed<br/>CORS_ALLOW_CREDENTIALS = True"]

    style A fill:#e3f5fe,stroke:#0277bd
```

Configured via `django-cors-headers`:
- `CORS_ALLOWED_ORIGINS`: Comma-separated list of allowed origins (env var)
- If empty, all origins are allowed (development mode)
- Credentials are allowed (`CORS_ALLOW_CREDENTIALS = True`)

### Rate Limiting

```mermaid
graph LR
    A["⚡ Rate Limiting"] --> B["👤 Anonymous<br/>30 req/min"]
    A --> C["🔐 Authenticated<br/>60 req/min"]
    A --> D["🏥 Health<br/>Exempt"]

    style A fill:#e3f5fe,stroke:#0277bd
    style B fill:#fff3e0,stroke:#e65100
    style C fill:#e8f5e9,stroke:#2e7d32
```

Using Django REST Framework's built-in throttling:

| User Type | Limit |
|-----------|-------|
| Anonymous | 30 requests/minute |
| Authenticated | 60 requests/minute |
| Health endpoint | **Exempt** |

### Password Security

```mermaid
graph LR
    A["🔐 Password Security"] --> B["🔏 PBKDF2 hashing"]
    A --> C["✅ Min length validator"]
    A --> D["❌ Common password check"]
    A --> E["🔢 Numeric check"]
    A --> F["🔄 Change requires<br/>current password"]

    style A fill:#ffebee,stroke:#c62828
```

- Passwords are hashed using Django's built-in password hashing (PBKDF2)
- Password validators enforce minimum length, common password check, numeric check
- Password change requires current password verification

### Input Validation

```mermaid
graph LR
    A["✅ Validation"] --> B["📝 All input validated<br/>before processing"]
    A --> C["📍 Coordinates<br/>numeric values"]
    A --> D["🔢 Filter enum<br/>1-6 range"]
    A --> E["⭐ Rating<br/>1-5 integers"]
    A --> F["❌ Invalid = 400<br/>BAD_REQUEST"]

    style A fill:#e3f5fe,stroke:#0277bd
    style F fill:#ffebee,stroke:#c62828
```

- All input is validated at the view level before processing
- Coordinates are validated as numeric values
- Filter enum values are validated against the allowed range (1-6)
- Rating values are validated as integers between 1 and 5
- Invalid input returns `400 BAD_REQUEST` with descriptive error messages