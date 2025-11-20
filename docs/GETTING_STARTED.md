# Getting Started with Crypto Analytics Platform

## Overview

This project is a real-time streaming analytics platform for cryptocurrency market data using a microservices architecture.

## Architecture

### Microservices
- **API Gateway** (port 8000) - Unified REST API with JWT authentication
- **Ingestion Service** (port 50051) - Real-time data collection from Binance API
- **Analytics Service** (port 50052) - Real-time queries on ClickHouse
- **Storage Service** (port 50053) - S3 archival and Athena queries
- **Notification Service** (port 50054) - Alert delivery (email + extensible)
- **Stream Processing Service** (port 50055) - Flink-based data transformation

### Infrastructure
- **Kafka** (KRaft mode, no Zookeeper) - Message queue
- **PostgreSQL** - Metadata storage (tenants, users, tickers, alerts)
- **ClickHouse** - Time-series analytics database
- **LocalStack** - AWS services emulation (S3, Athena, Flink)
- **Prometheus** - Metrics collection
- **Grafana** - Monitoring dashboards

### Communication
- **External**: REST API via API Gateway
- **Internal**: gRPC between services
- **Authentication**: JWT with multi-tenant support

## Project Structure

```
crypto-dashboard/
├── proto/                    # gRPC proto definitions (interface-first design)
├── shared/                   # Shared utilities (auth, gRPC, Kafka, models)
├── api-gateway/              # REST API Gateway
├── ingestion-service/        # Data ingestion from exchanges
├── analytics-service/        # Real-time queries
├── storage-service/          # S3 archival
├── notification-service/     # Alert delivery
├── stream-processing-service/# Flink jobs
├── db/                       # Database init scripts
├── monitoring/               # Prometheus & Grafana configs
├── scripts/                  # Utility scripts
└── docker-compose.yml        # Infrastructure setup
```

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.13+
- pip

### 1. Initial Setup

```bash
# Run the setup script
./scripts/setup_local.sh
```

This will:
- Create `.env` file from template
- Generate gRPC Python code from proto files
- Start infrastructure services (Kafka, PostgreSQL, ClickHouse, etc.)

### 2. Configure Environment

Edit `.env` file with your configuration:
- Database credentials
- Binance API keys
- Email provider settings (SendGrid/Mailgun)
- JWT secret key

### 3. Create and Activate Virtual Environment

**Always use a virtual environment** to avoid dependency conflicts:

```bash
# Create venv in project root
cd /Users/yuyu/workspace/crypto-dashboard
python3 -m venv venv

# Activate venv
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate     # On Windows
```

Your prompt should now show `(venv)` prefix.

### 4. Install Dependencies

With venv activated, install development tools:

```bash
pip install --upgrade pip
pip install pre-commit flake8 black isort pytest pytest-asyncio
```

For each service you want to run locally:

```bash
cd <service-directory>
pip install -r requirements.txt
```

**Note**: Install dependencies one by one and pin versions as instructed in the plan.

### 5. Generate gRPC Code

```bash
./scripts/generate_proto.sh
```

### 6. Initialize Databases

The database schemas will be automatically initialized when Docker containers start.
Check the logs to ensure initialization completed successfully:

```bash
docker compose logs postgres
docker compose logs clickhouse
```

### 7. Run Services Locally

Each service can be run independently for development.

**Important**: Always activate venv first!

```bash
# Activate venv (if not already activated)
source venv/bin/activate  # From project root

# Terminal 1: API Gateway
cd api-gateway
python main.py

# Terminal 2: Ingestion Service
cd ingestion-service
source venv/bin/activate
python main.py

# ... and so on for other services
```

Or use Docker Compose to run all services:

```bash
# Uncomment service definitions in docker-compose.yml first
docker compose up --build
```

## Access Points

Once everything is running:

- **API Gateway**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **ClickHouse UI**: http://localhost:8123/play

## Development Workflow

### Interface-First Design

This project follows an interface-first approach:

1. **Proto definitions** define gRPC service contracts
2. **Models** define data structures (Pydantic)
3. **Interfaces** are defined in each layer (API → Service → Repository)
4. **Implementation** happens within these interfaces

### Layer Pattern

Each service follows: **API → Service → Repository**

- **API Layer**: gRPC servicers / REST endpoints
- **Service Layer**: Business logic
- **Repository Layer**: Data access (DB, Kafka, external APIs)

### Adding a New Feature

1. Update proto definitions if needed
2. Regenerate gRPC code: `./scripts/generate_proto.sh`
3. Implement in appropriate service layers
4. Add tests
5. Update monitoring metrics

## Multi-Tenancy

All data is isolated by `tenant_id`:
- Row-level isolation in PostgreSQL and ClickHouse
- JWT tokens include `tenant_id` in claims
- All queries automatically filter by tenant

## Data Flow

```
Binance API → Ingestion Service → Kafka (raw topic)
                                     ↓
                                  Flink Jobs (enrichment, aggregation, alerts)
                                     ↓
                        ├─→ Kafka (processed topic)
                        ├─→ ClickHouse (hot storage, 30 days)
                        └─→ S3 (cold storage, indefinite)
                                     ↓
                              Analytics Service ← API Gateway ← Users
```

## Monitoring

### Prometheus Metrics

Each service exposes metrics on its designated port (see `config.py`):
- Request counts and latencies
- Error rates
- Custom business metrics

### Grafana Dashboards

Access Grafana at http://localhost:3000:
- Service health overview
- Data ingestion rates
- Query performance
- Alert statistics

## Testing

**Note**: Testing framework to be implemented (marked as pending todo).

Planned test structure:
- Unit tests for each service layer
- Integration tests for gRPC communication
- End-to-end tests for complete data flow

## Troubleshooting

### Service can't connect to infrastructure

Check if infrastructure services are running:
```bash
docker compose ps
```

Restart if needed:
```bash
docker compose restart
```

### Proto generation fails

Ensure `grpcio-tools` is installed:
```bash
pip install grpcio-tools
```

### Kafka connection errors

Kafka may take 10-20 seconds to fully start. Check logs:
```bash
docker compose logs kafka
```

## Next Steps

1. **Implement actual business logic** - All services have TODO markers for implementation
2. **Add authentication logic** - JWT creation and verification in shared/auth
3. **Implement Binance connector** - WebSocket and REST API integration
4. **Create Flink jobs** - Data transformation and aggregation
5. **Add tests** - Unit and integration tests
6. **Deploy to Railway + AWS** - Production deployment configurations

## Resources


- [Code Quality Guide](CODE_QUALITY.md) - Pre-commit hooks and best practices
- [Proto Definitions](../proto/) - gRPC service contracts
- [Database Schemas](../db/) - PostgreSQL and ClickHouse table definitions

## Support

For issues or questions, refer to the detailed implementation notes in each service's files (marked with TODO comments).

