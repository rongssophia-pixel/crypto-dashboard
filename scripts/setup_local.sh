#!/bin/bash

# Local development setup script
# Sets up the development environment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "==================================="
echo "Crypto Analytics Platform Setup"
echo "==================================="
echo ""

# Check for .env file
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo "Creating .env file from .env.example..."
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
    echo "✓ .env file created. Please update with your configuration."
else
    echo "✓ .env file already exists"
fi

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "✗ Docker not found. Please install Docker first."
    exit 1
fi
echo "✓ Docker found"

# Check for Docker Compose
if ! docker compose version &> /dev/null; then
    echo "✗ Docker Compose not found. Please install Docker Compose first."
    exit 1
fi
echo "✓ Docker Compose found"

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "✗ Python 3 not found. Please install Python 3.13+."
    exit 1
fi
echo "✓ Python 3 found"

# Install pre-commit if not already installed
if ! command -v pre-commit &> /dev/null; then
    echo ""
    echo "Installing pre-commit..."
    pip install pre-commit
fi

# Install pre-commit hooks
echo ""
echo "Installing pre-commit hooks..."
pre-commit install
echo "✓ Pre-commit hooks installed"

# Generate proto files
echo ""
echo "Generating Protocol Buffer code..."
bash "$SCRIPT_DIR/generate_proto.sh"

# Start infrastructure
echo ""
echo "Starting infrastructure services..."
cd "$PROJECT_ROOT"
docker compose up -d kafka postgres clickhouse localstack prometheus grafana

echo ""
echo "Waiting for services to be healthy..."
sleep 10

# Check service health
echo ""
echo "Checking service health..."
docker compose ps

echo ""
echo "==================================="
echo "Setup Complete!"
echo "==================================="
echo ""
echo "Services running:"
echo "  - Kafka (KRaft):      localhost:9092"
echo "  - PostgreSQL:         localhost:5432"
echo "  - ClickHouse:         localhost:9000, localhost:8123"
echo "  - LocalStack:         localhost:4566"
echo "  - Prometheus:         http://localhost:9090"
echo "  - Grafana:            http://localhost:3000 (admin/admin)"
echo ""
echo "Next steps:"
echo "  1. Review and update .env file with your configuration"
echo "  2. Install Python dependencies for each service"
echo "  3. Pre-commit hooks are installed and ready"
echo "  4. Run individual services for development"
echo ""
echo "Code quality:"
echo "  - Pre-commit hooks will run automatically on 'git commit'"
echo "  - Run manually: pre-commit run --all-files"
echo ""
echo "To stop all services:"
echo "  docker compose down"
echo ""

