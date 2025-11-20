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
**Implementation**: 🔄 Ready - See [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) for detailed tickets

## Code Quality

This project uses **pre-commit hooks** for automatic code quality checks:
- **Black** for code formatting (88 char line length)
- **Flake8** for linting (relaxed rules)
- **isort** for import sorting

**Setup once**:
```bash
pip install pre-commit
pre-commit install
```

**Automatic**: Hooks run on every `git commit`

**Manual**:
```bash
pre-commit run --all-files
```

See [CODE_QUALITY.md](CODE_QUALITY.md) for details.

## CI/CD

GitHub Actions workflow runs on every push and PR:
- ✅ Linting with Flake8
- ✅ Basic tests with Pytest

See [.github/workflows/](.github/workflows/) for details.

## Prerequisites

- Docker & Docker Compose
- Python 3.13+

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

## Project Structure

See [crypto-analytics-platform.plan.md](crypto-analytics-platform.plan.md) for detailed architecture and implementation plan.

