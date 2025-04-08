#!/bin/bash
# Enhanced version of run.sh with better error handling

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print header
echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}       AI Simulator Bot - Recovery Script         ${NC}"
echo -e "${BLUE}==================================================${NC}"

# Check if required files exist
echo -e "${YELLOW}Checking for required files...${NC}"

# Fix missing script files
if [ ! -f "./scripts/fix-api.sh" ]; then
    echo -e "${RED}Missing fix-api.sh script. Creating it...${NC}"
    mkdir -p ./scripts
    cat > ./scripts/fix-api.sh << 'EOF'
#!/bin/bash
# Script to fix common API container issues

echo "Fixing API container issues..."

# Check if torch is needed and install if required
if grep -q "import torch" /app/app/main.py; then
  if ! python -c "import torch" 2>/dev/null; then
    echo "PyTorch is required but not installed. Installing minimal version..."
    pip install torch --no-deps
    echo "PyTorch minimal installation complete."
  else
    echo "PyTorch is already installed."
  fi
fi

# Check for other key dependencies
echo "Checking other dependencies..."
for pkg in fastapi uvicorn sqlalchemy pydantic requests; do
  if ! python -c "import $pkg" 2>/dev/null; then
    echo "$pkg is required but not installed. Installing..."
    pip install $pkg
  fi
done

# Update database models if needed
if [ -f /app/core/db/models/ai_partner.py ]; then
  echo "AIPartner model found."
else
  echo "AIPartner model not found, creating it..."
  mkdir -p /app/core/db/models
  cat > /app/core/db/models/ai_partner.py << 'EOFMODEL'
import uuid
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.db.base import Base

class AIPartner(Base):
    """
    AI Partner model
    """
    __tablename__ = "ai_partners"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Define properties for columns that might be accessed but don't exist in DB
    @property
    def partner_id(self):
        return self.id
        
    @property
    def personality_traits(self):
        return None
    
    @property
    def interests(self):
        return None
    
    @property
    def background(self):
        return None
    
    @property
    def current_emotion(self):
        return "neutral"
    
    @property
    def age(self):
        return None
        
    @property
    def gender(self):
        return "female"  # Default value
    
    @property
    def fetishes(self):
        return None
    
    def __repr__(self):
        return f"<AIPartner {self.name}>"
EOFMODEL
fi

# Fix imports in __init__.py
if grep -q "AIPartner" /app/core/db/models/__init__.py; then
  echo "AIPartner is already imported in __init__.py"
else
  echo "Adding AIPartner import to __init__.py..."
  sed -i 's/except ImportError as e:/    from core.db.models.ai_partner import AIPartner  # Add AIPartner import\nexcept ImportError as e:/' /app/core/db/models/__init__.py
fi

echo "API fixes applied. Try restarting the API container."
EOF
    chmod +x ./scripts/fix-api.sh
    echo -e "${GREEN}Created fix-api.sh${NC}"
fi

# Check if the check-containers.sh script exists
if [ ! -f "./scripts/check-containers.sh" ]; then
    echo -e "${RED}Missing check-containers.sh script. Creating it...${NC}"
    cat > ./scripts/check-containers.sh << 'EOF'
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
EOF
    chmod +x ./scripts/check-containers.sh
    echo -e "${GREEN}Created check-containers.sh${NC}"
fi

# Make the entrypoint script executable
if [ -f "./scripts/docker-entrypoint.sh" ]; then
    chmod +x ./scripts/docker-entrypoint.sh
    echo -e "${GREEN}Made docker-entrypoint.sh executable${NC}"
fi

# Function to clean up Docker
cleanup_docker() {
    echo -e "${YELLOW}Cleaning up Docker environment...${NC}"
    
    # Stop all containers
    docker-compose down
    
    # Remove any orphaned containers
    docker-compose down --remove-orphans
    
    # Prune unused volumes (optional)
    echo -e "${YELLOW}Do you want to prune unused Docker volumes? (y/n)${NC}"
    read -r answer
    if [[ "$answer" =~ ^[Yy]$ ]]; then
        docker volume prune -f
        echo -e "${GREEN}Unused volumes pruned${NC}"
    fi
    
    echo -e "${GREEN}Docker cleanup complete${NC}"
}

# Start containers with debugging info
start_with_debug() {
    echo -e "${YELLOW}Starting containers with debugging...${NC}"
    
    # Start PostgreSQL first
    echo -e "${BLUE}Starting PostgreSQL...${NC}"
    docker-compose up -d postgres
    
    # Wait for PostgreSQL to be ready
    echo -e "${YELLOW}Waiting for PostgreSQL to be ready...${NC}"
    sleep 10
    
    # Start API service
    echo -e "${BLUE}Starting API service...${NC}"
    docker-compose up -d api
    
    # Wait for API to be ready
    echo -e "${YELLOW}Waiting for API to be ready...${NC}"
    sleep 10
    
    # Start admin panel
    echo -e "${BLUE}Starting admin panel...${NC}"
    docker-compose up -d admin
    
    # Start Telegram bot
    echo -e "${BLUE}Starting Telegram bot...${NC}"
    docker-compose up -d telegram
    
    echo -e "${GREEN}All services started!${NC}"
    
    # Show logs for debugging
    echo -e "${YELLOW}Showing initial logs for debugging...${NC}"
    docker-compose logs
}

# Fix database
fix_database() {
    echo -e "${YELLOW}Attempting to fix database issues...${NC}"
    
    # Check if PostgreSQL container is running
    if ! docker ps | grep -q aibot-postgres; then
        echo -e "${RED}PostgreSQL container is not running. Starting it...${NC}"
        docker-compose up -d postgres
        sleep 10
    fi
    
    # Create admin_users table
    echo -e "${YELLOW}Creating admin_users table if needed...${NC}"
    docker-compose exec postgres psql -U aibot -d aibot -c "
    CREATE TABLE IF NOT EXISTS admin_users (
        id VARCHAR(36) PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        email VARCHAR(100),
        password_hash VARCHAR(200) NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );" || echo -e "${RED}Could not create admin_users table${NC}"
    
    # Insert default admin user
    echo -e "${YELLOW}Creating default admin user if needed...${NC}"
    docker-compose exec postgres psql -U aibot -d aibot -c "
    INSERT INTO admin_users (id, username, password_hash, is_active)
    SELECT 
      'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 
      'admin', 
      'pbkdf2:sha256:150000\$KKgd0xN3\$d57b15c874bd9b5f30d7c1ef6006d1a162970a702e9e76bb51a1f7543b63212b', 
      true
    WHERE NOT EXISTS (
      SELECT 1 FROM admin_users WHERE username = 'admin'
    );" || echo -e "${RED}Could not create default admin user${NC}"
    
    echo -e "${GREEN}Database fix attempts completed${NC}"
}

# Main menu
echo -e "${YELLOW}What would you like to do?${NC}"
echo "1. Clean up Docker environment and start fresh"
echo "2. Start containers with step-by-step debugging"
echo "3. Fix database issues"
echo "4. Run diagnostic checks"
echo "5. Exit"

read -r choice

case $choice in
    1)
        cleanup_docker
        echo -e "${YELLOW}Starting containers...${NC}"
        docker-compose up -d
        ;;
    2)
        start_with_debug
        ;;
    3)
        fix_database
        ;;
    4)
        if [ -f "./scripts/check-containers.sh" ]; then
            ./scripts/check-containers.sh
        else
            echo -e "${RED}check-containers.sh not found${NC}"
        fi
        ;;
    5)
        echo -e "${GREEN}Exiting...${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo -e "${GREEN}Operation completed.${NC}"
