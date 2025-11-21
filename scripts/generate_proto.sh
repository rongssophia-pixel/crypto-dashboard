#!/bin/bash

# Script to generate Python code from Protocol Buffer definitions
# Usage: ./scripts/generate_proto.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PROTO_DIR="$PROJECT_ROOT/proto"
OUTPUT_DIR="$PROJECT_ROOT/proto"

echo "Generating Python code from Protocol Buffers..."
echo "Proto directory: $PROTO_DIR"
echo "Output directory: $OUTPUT_DIR"

# Check if proto directory exists
if [ ! -d "$PROTO_DIR" ]; then
    echo "Error: Proto directory not found at $PROTO_DIR"
    exit 1
fi

# Check if grpcio-tools is installed
if ! python3 -c "import grpc_tools" 2>/dev/null; then
    echo "Error: grpcio-tools not installed. Please run: pip install grpcio-tools"
    exit 1
fi

# Generate Python code for each proto file
for proto_file in "$PROTO_DIR"/*.proto; do
    if [ -f "$proto_file" ]; then
        filename=$(basename "$proto_file")
        echo "Generating code for $filename..."

        python3 -m grpc_tools.protoc \
            -I"$PROTO_DIR" \
            --python_out="$OUTPUT_DIR" \
            --grpc_python_out="$OUTPUT_DIR" \
            --pyi_out="$OUTPUT_DIR" \
            "$proto_file"
    fi
done

# Fix imports in generated files (replace relative imports with absolute)
echo "Fixing imports in generated files..."

# Fix .py files
for generated_file in "$OUTPUT_DIR"/*_pb2*.py; do
    if [ -f "$generated_file" ]; then
        # This sed command works on both Linux and macOS
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' 's/^import \(.*\)_pb2/from proto import \1_pb2/' "$generated_file"
        else
            # Linux
            sed -i 's/^import \(.*\)_pb2/from proto import \1_pb2/' "$generated_file"
        fi
    fi
done

# Fix .pyi files (type hints)
for generated_file in "$OUTPUT_DIR"/*_pb2*.pyi; do
    if [ -f "$generated_file" ]; then
        # This sed command works on both Linux and macOS
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' 's/^import \(.*\)_pb2 as/from proto import \1_pb2 as/' "$generated_file"
        else
            # Linux
            sed -i 's/^import \(.*\)_pb2 as/from proto import \1_pb2 as/' "$generated_file"
        fi
    fi
done

echo "Protocol Buffer code generation complete!"
echo ""
echo "Generated files:"
ls -lh "$OUTPUT_DIR"/*_pb2*.py 2>/dev/null || echo "No generated files found"
