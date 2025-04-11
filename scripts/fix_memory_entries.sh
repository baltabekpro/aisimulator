#!/bin/bash

# Script to fix memory entries database schema

echo "Fixing memory entries database schema..."

# Go to project root directory
cd "$(dirname "$0")/.."

# Run the Python fix script
python -m scripts.fix_memory_schema

echo "Fix script completed!"