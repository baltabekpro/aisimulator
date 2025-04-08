#!/bin/bash
# Script to fix common Telegram bot container issues

echo "Fixing Telegram bot issues..."

# Install required packages for the Telegram bot
echo "Installing required dependencies..."
pip install --no-cache-dir aiohttp aiogram python-dotenv requests

# Check if other dependencies are needed
echo "Checking for other common dependencies..."
for pkg in sqlalchemy pydantic; do
  if ! python -c "import $pkg" 2>/dev/null; then
    echo "$pkg is required but not installed. Installing..."
    pip install --no-cache-dir $pkg
  fi
done

# Verify installations
echo "Verifying installations..."
for pkg in aiohttp aiogram; do
  if python -c "import $pkg" 2>/dev/null; then
    echo "✅ $pkg successfully installed"
  else
    echo "❌ Failed to install $pkg, trying again with different approach..."
    pip install --no-cache-dir --force-reinstall $pkg
  fi
done

echo "Telegram bot fixes applied."
