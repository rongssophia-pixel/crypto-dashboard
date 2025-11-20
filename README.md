# Crypto Real-Time Analytics Platform

![CI](https://github.com/YOUR_USERNAME/crypto-dashboard/workflows/CI/badge.svg)

A microservices-based real-time streaming analytics platform for cryptocurrency market data.

## Architecture

- **API Gateway**: Unified REST API with JWT authentication
- **Ingestion Service**: Real-time data collection from Binance API
- **Stream Processing Service**: Flink-based data transformation and aggregation
- **Analytics Service**: ClickHouse-powered real-time queries
- **Storage Service**: S3 archival with Athena queries
- **Notification Service**: Alert delivery (email, extensible to SNS/SMS)

## Tech Stack

- **Message Queue**: Kafka with KRaft (no Zookeeper)
- **Stream Processing**: Apache Flink
- **Analytics DB**: ClickHouse
- **Metadata DB**: PostgreSQL
- **Storage**: AWS S3 + Athena
- **API Framework**: FastAPI
- **Inter-service**: gRPC
- **Auth**: JWT
- **Monitoring**: Prometheus + Grafana

## Local Development

### Implementation Status

**Structure**: ✅ Complete - All directories, files, and interfaces created
**Implementation**: 🔄 Ready - See [TICKETS_IMPLEMENTATION_GUIDE.md](TICKETS_IMPLEMENTATION_GUIDE.md) for detailed tickets

## Code Quality

This project uses **pre-commit hooks** for automatic code quality checks:
- **Black** for code formatting (88 char line length)
- **Flake8** for linting (relaxed rules)
- **isort** for import sorting

**Setup once** (in virtual environment):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install pre-commit
pre-commit install
```

**Automatic**: Hooks run on every `git commit`

**Manual**:
```bash
pre-commit run --all-files
```

See [docs/CODE_QUALITY.md](docs/CODE_QUALITY.md) for details.

## CI/CD

GitHub Actions workflow runs on every push and PR:
- ✅ Linting with Flake8
- ✅ Basic tests with Pytest

See [.github/workflows/](.github/workflows/) for details.

## Prerequisites

- Docker & Docker Compose
- Python 3.13+
- Virtual environment (venv) - **Always use venv!**

### Setup

1. Clone the repository
2. Copy environment variables: `cp .env.example .env`
3. Start infrastructure: `docker-compose up -d`
4. Generate gRPC code: `./scripts/generate_proto.sh`
5. Install dependencies for each service

### Running Services

Each service can be run independently:

```bash
cd <service-name>
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Documentation

- **[docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)** - Complete setup and development guide
- **[docs/CODE_QUALITY.md](docs/CODE_QUALITY.md)** - Code quality tools, pre-commit hooks, and best practices
- **[TICKETS.md](TICKETS.md)** - Implementation tickets (Part 1: Infrastructure & Core Services)
- **[TICKETS_PART2.md](TICKETS_PART2.md)** - Implementation tickets (Part 2: Advanced Features)
- **[TICKETS_IMPLEMENTATION_GUIDE.md](TICKETS_IMPLEMENTATION_GUIDE.md)** - Implementation overview and progress tracking

## Project Structure

```
crypto-dashboard/
├── api-gateway/           # Unified REST API with JWT auth
├── ingestion-service/     # Data collection from Binance & Twitter
├── stream-processing-service/  # Flink jobs for transformations
├── analytics-service/     # ClickHouse real-time queries
├── storage-service/       # S3 archival & Athena queries
├── notification-service/  # Alert delivery (email, extensible)
├── shared/               # Common utilities (auth, gRPC, Kafka)
├── proto/                # gRPC protocol definitions
├── db/                   # Database schemas (PostgreSQL, ClickHouse)
├── docker-compose.yml    # Local infrastructure
└── scripts/              # Setup and utility scripts
```

## Contributing

1. **Always use virtual environment**: `source venv/bin/activate`
2. **Pre-commit hooks will run automatically** on `git commit`
3. **Follow the implementation tickets** in TICKETS.md and TICKETS_PART2.md
4. **Write tests** for all new features
5. **Update documentation** as needed

## License

[Add your license here]

