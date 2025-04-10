#!/bin/bash
# prepare_scripts.sh - Make script files executable for Docker

echo "Making script files executable for Docker..."

# Check if scripts directory exists
if [ ! -d "./scripts" ]; then
    echo "Error: scripts directory not found!"
    exit 1
fi

# Make all shell scripts in the scripts directory executable
find ./scripts -name "*.sh" -exec chmod +x {} \;

echo "All shell scripts are now executable!"
echo "You can now run docker-compose up -d to start all containers."