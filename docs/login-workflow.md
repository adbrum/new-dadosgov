# Login Workflow

Authentication flow between the Next.js frontend and the udata (Flask) backend.

## Architecture Overview

```
Client (Browser/Postman)
    │
    ▼
Next.js Frontend (port 3000)
    │
    ├── GET  /get-csrf        ──► rewrite ──► Backend /get-csrf
    ├── POST /login           ──► Route Handler (src/app/login/route.ts) ──► Backend /login/
    ├── POST /logout/         ──► rewrite ──► Backend /logout/
    ├── GET  /reset/          ──► rewrite ──► Backend /reset/
    └── *    /api/*           ──► rewrite ──► Backend /api/*
    │
    ▼
udata Backend (port 7000)
```

## Authentication Flow

### 1. Get CSRF Token

The backend requires a CSRF token for all POST requests. The frontend proxies this via a Next.js rewrite.

```
GET http://localhost:3000/get-csrf
```

**Response (200):**
```json
{
  "response": {
    "csrf_token": "IjEwOGI4YmIz..."
  }
}
```

A `session` cookie is also set — it must be sent in the login request.

### 2. Login

```
POST http://localhost:3000/login
Content-Type: application/x-www-form-urlencoded
```

**Body parameters:**

| Parameter    | Type   | Required | Description          |
|--------------|--------|----------|----------------------|
| `email`      | string | Yes      | User email address   |
| `password`   | string | Yes      | User password        |
| `csrf_token` | string | Yes      | Token from step 1    |

**Important:** Use `/login` (no trailing slash). Next.js will 308 redirect `/login/` to `/login`.

#### Success Response (200)

```json
{
  "message": "Login successful",
  "redirect": "/"
}
```

The response includes `Set-Cookie` headers with the authenticated session cookie.

#### Error Response (400)

```json
{
  "message": "Palavra-passe inválida"
}
```

Common error messages:
- `Palavra-passe inválida` — wrong password
- `The CSRF token is missing.` — missing or invalid CSRF token
- `Password must be changed for security reasons` — password rotation required

### 3. Verify Authentication

After login, use the session cookie to access authenticated endpoints:

```
GET http://localhost:3000/api/1/me/
Cookie: session=<session_cookie>
```

**Response (200):**
```json
{
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "apikey": "eyJhbGciOi...",
  "organizations": [...]
}
```

### 4. Logout

```
POST http://localhost:3000/logout/
```

## Implementation Details

### Frontend Route Handler (`src/app/login/route.ts`)

The login endpoint uses a Next.js Route Handler instead of a rewrite because:
- Next.js rewrites conflict with page routing for POST requests
- The Route Handler converts the backend's HTML form responses into JSON
- It translates the backend's 302 redirect (login success) into a 200 JSON response

Flow:
1. Receives POST with form data from the client
2. Forwards the request to the backend (`POST /login/`)
3. Backend returns 302 (success) or 400 (error)
4. Route Handler converts the response to JSON and forwards cookies

### Next.js Rewrites (`next.config.ts`)

Other auth endpoints use Next.js rewrites configured in `beforeFiles` (run before page routing):
- `/get-csrf` → backend CSRF endpoint
- `/logout/` → backend logout
- `/reset/` and `/reset/:token` → password reset
- `/api/*` → all API calls (configured as `fallback`)

### Backend Auth (`udata/auth/`)

- **Form**: `ExtendedLoginForm` (extends Flask-Security `LoginForm`)
  - Validates email + password
  - Checks `password_rotation_demanded` flag
- **CSRF**: Flask-WTF CSRF protection, token tied to the Flask session
- **Session**: Flask session cookie (HttpOnly)
- **Login URL**: `SECURITY_LOGIN_URL = "/login/"` (defined in `udata/settings.py`)

## Postman Setup

### Environment Variables

| Variable      | Value                      |
|---------------|----------------------------|
| `base_url`    | `http://localhost:3000`    |
| `backend_url` | `http://localhost:7000`    |

### Request Configuration

1. **Get CSRF Token**
   - Method: `GET`
   - URL: `{{base_url}}/get-csrf`
   - Save `csrf_token` from response and `session` cookie

2. **Login**
   - Method: `POST`
   - URL: `{{base_url}}/login`
   - Body: `x-www-form-urlencoded`
     - `email`: user email
     - `password`: user password
     - `csrf_token`: token from step 1
   - Settings: Follow Redirects **ON**

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| 308 redirect | Trailing slash in URL | Use `/login` not `/login/` |
| 404 Not Found | Wrong host/port | Use `localhost:3000` (frontend), not `localhost:7000` |
| CSRF token missing | Session cookie not sent | Ensure cookies are enabled and the `session` cookie from `/get-csrf` is included |
| HTML instead of JSON | Hitting backend directly | Use `localhost:3000` to go through the Route Handler |

## Development Setup

### Required Services

| Service   | Port | Purpose           |
|-----------|------|-------------------|
| Frontend  | 3000 | `npm run dev`     |
| Backend   | 7000 | `inv serve`       |
| MongoDB   | 27017| Database          |
| Redis     | 6379 | Cache + Celery    |

### Environment Variables

**Frontend (`.env.local`):**
```
NEXT_PUBLIC_API_BASE=http://localhost:7000/api/1
```

**Backend (`.env`):**
```
SERVER_NAME=dev.local:7000
```
