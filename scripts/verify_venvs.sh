#!/bin/bash

# Verify all virtual environments are set up correctly

PROJECT_ROOT="/Users/yuyu/workspace/crypto-dashboard"

echo "======================================"
echo "Virtual Environment Verification"
echo "======================================"
echo ""

services=(
  "shared"
  "api-gateway"
  "ingestion-service"
  "analytics-service"
  "storage-service"
  "notification-service"
  "stream-processing-service"
)

all_good=true

for service in "${services[@]}"; do
  echo -n "Checking $service... "
  
  venv_path="$PROJECT_ROOT/$service/venv"
  
  if [ ! -d "$venv_path" ]; then
    echo "❌ venv NOT FOUND"
    all_good=false
    continue
  fi
  
  if [ ! -f "$venv_path/bin/python" ]; then
    echo "❌ Python binary NOT FOUND"
    all_good=false
    continue
  fi
  
  if [ ! -f "$venv_path/bin/activate" ]; then
    echo "❌ activate script NOT FOUND"
    all_good=false
    continue
  fi
  
  # Check Python version
  python_version=$("$venv_path/bin/python" --version 2>&1)
  
  echo "✓ OK ($python_version)"
done

echo ""
echo "======================================"

if [ "$all_good" = true ]; then
  echo "✓ All virtual environments are set up correctly!"
else
  echo "⚠️  Some virtual environments need attention"
  echo ""
  echo "To recreate a venv:"
  echo "  cd <service-directory>"
  echo "  rm -rf venv"
  echo "  python3 -m venv venv"
fi

echo "======================================"
echo ""

