#!/bin/bash
# Quick setup and test script for TICKET-007

set -e

echo "================================================"
echo "Ingestion Service Tests - TICKET-007"
echo "================================================"

cd /Users/yuyu/workspace/crypto-dashboard

# Start infrastructure
echo ""
echo "1. Starting infrastructure (PostgreSQL + Kafka)..."
docker compose up -d postgres kafka

# Wait for services
echo ""
echo "2. Waiting for services to be ready..."
sleep 5

# Create database
echo ""
echo "3. Setting up test database..."
docker exec -i crypto-postgres psql -U postgres -c "CREATE DATABASE crypto_dashboard;" 2>/dev/null || echo "Database already exists"

# Apply schema
echo ""
echo "4. Applying database schema..."
docker exec -i crypto-postgres psql -U postgres -d crypto_dashboard < ingestion-service/tests/setup_test_db.sql

# Activate venv
echo ""
echo "5. Activating virtual environment..."
source shared/venv/bin/activate

# Install test dependencies
echo ""
echo "6. Installing test dependencies..."
pip install -q pytest pytest-asyncio 2>/dev/null || true

# Run tests
echo ""
echo "7. Running tests..."
echo "================================================"
python -m pytest ingestion-service/tests/ -v -s

echo ""
echo "================================================"
echo "✓ All tests completed!"
echo "================================================"
