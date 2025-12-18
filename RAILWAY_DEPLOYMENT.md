# Railway Deployment Guide

This project is configured to be deployed as a **single container monolith** on Railway using Docker and Supervisord. This runs the Next.js Frontend and all Python Microservices in one place.

## Prerequisites

1.  **Railway Account**: Sign up at [railway.app](https://railway.app).
2.  **Railway CLI** (Optional): `npm i -g @railway/cli`

## Setup Steps

### 1. Create a Project on Railway

1.  Go to your Dashboard.
2.  Click "New Project".
3.  Select "Deploy from GitHub repo".
4.  Select this repository.

### 2. Configure Variables

You must add the required environment variables in the Railway "Variables" tab. Use the values from `.env.example` as a template, but **update them for production/Railway**.

**Important Service Configs:**

*   **Database**: Add a PostgreSQL service in Railway and link it. Use the provided `DATABASE_URL` or set `POSTGRES_HOST`, `POSTGRES_USER`, etc.
*   **Redis** (Optional): Add a Redis service if needed.
*   **ClickHouse**: Railway doesn't have native ClickHouse. You may need an external provider (e.g., ClickHouse Cloud) or run a ClickHouse Docker image service in the same Railway project.
*   **Kafka**: Similarly, use Upstash (available in Railway) or Confluent Cloud.

**Environment Variables to Set:**

```bash
# Frontend
FRONTEND_URL=https://<your-railway-app-url>
NEXT_PUBLIC_API_URL=https://<your-railway-app-url>/api

# Backend Services (Internal localhost networking works because they are in the same container)
POSTGRES_HOST=${{Postgres.HOST}}
POSTGRES_PORT=${{Postgres.PORT}}
POSTGRES_USER=${{Postgres.USER}}
POSTGRES_PASSWORD=${{Postgres.PASSWORD}}
POSTGRES_DB=${{Postgres.DATABASE}}

# Secrets
JWT_SECRET_KEY=<generate-random-secret>
```

### 3. Ports

Railway exposes only **one** port publicly by default.

*   By default, the `Dockerfile` exposes `8000` (API Gateway) and `3000` (Frontend).
*   **Recommendation**: Since Railway only proxies one port (the one defined in `$PORT` or the first EXPOSE), you might need a reverse proxy (Nginx) inside the container if you want both Frontend and Backend on the same domain without `/api` routing issues.
*   **Current Setup**: The Frontend is listening on `3000` and API on `8000`.
    *   If you set Railway `PORT` variable to `3000`, the public URL hits the Frontend. The Frontend must talk to `localhost:8000` (server-side calls) or public URL (client-side calls).
    *   **Fix**: Update `next.config.js` to rewrite `/api/*` requests to `http://localhost:8000/api/*` so you only need to expose port 3000.

### 4. Deploy

Railway will automatically detect the `Dockerfile` and `railway.toml` and start the build.

## Architecture Note

Running all services in one container ("Monolith mode") is great for cost savings and simplicity (1 replica), but effectively turns your microservices back into a monolith.
- **Pros**: Cheap, simple, no network latency between services.
- **Cons**: Scaling one service scales them all; restart affects all; logs are mixed.
