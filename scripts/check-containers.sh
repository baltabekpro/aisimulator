#!/bin/bash
# This script checks the health of all containers and provides diagnostics

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Checking Docker container status...${NC}"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo -e "\n${YELLOW}Checking PostgreSQL container...${NC}"
if docker exec aibot-postgres pg_isready -U aibot 2>/dev/null; then
  echo -e "${GREEN}PostgreSQL is running and accepting connections${NC}"
else
  echo -e "${RED}PostgreSQL is not responding!${NC}"
  echo -e "${YELLOW}Trying to view PostgreSQL logs:${NC}"
  docker logs --tail 20 aibot-postgres
fi

echo -e "\n${YELLOW}Checking admin_users table...${NC}"
docker exec aibot-postgres psql -U aibot -d aibot -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'admin_users'" || echo -e "${RED}Failed to query PostgreSQL${NC}"

echo -e "\n${YELLOW}Checking admin container...${NC}"
docker logs --tail 20 aibot-admin

echo -e "\n${YELLOW}Checking API container...${NC}"
if curl -s http://localhost:8000/health > /dev/null; then
  echo -e "${GREEN}API is responding${NC}"
  # Check models import
  echo -e "${YELLOW}Checking API database models...${NC}"
  docker exec aibot-api python -c "from core.db.models import AIPartner; print('AIPartner model can be imported')" || echo -e "${RED}AIPartner model import failed${NC}"
else
  echo -e "${RED}API is not responding!${NC}"
  echo -e "${YELLOW}API logs:${NC}"
  docker logs --tail 20 aibot-api
fi

echo -e "\n${YELLOW}Recommended fixes:${NC}"
echo "1. If PostgreSQL is not running, restart it: docker-compose restart postgres"
echo "2. If admin_users table doesn't exist, run: docker-compose exec postgres psql -U aibot -d aibot -c \"CREATE TABLE IF NOT EXISTS admin_users (id VARCHAR(36) PRIMARY KEY, username VARCHAR(50) UNIQUE NOT NULL, password_hash VARCHAR(200) NOT NULL, is_active BOOLEAN DEFAULT TRUE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);\""
echo "3. If admin container is failing, check: docker logs aibot-admin"
echo "4. If API container can't import models, restart it: docker-compose restart api"
