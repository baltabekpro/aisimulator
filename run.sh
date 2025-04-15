#!/bin/bash
# AI Simulator Bot - Run Script
# This script provides commands to run and manage the application

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print header
echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}        AI Simulator Bot - Control Script         ${NC}"
echo -e "${BLUE}==================================================${NC}"

# Fix PostgreSQL connection
function fix_postgres_issue {
    echo -e "${YELLOW}Attempting to fix PostgreSQL connection issues...${NC}"
    
    # Check if PostgreSQL container is running
    if docker ps | grep -q aibot-postgres; then
        echo -e "${GREEN}PostgreSQL container is running${NC}"
    else
        echo -e "${RED}PostgreSQL container is not running. Starting it...${NC}"
        docker-compose up -d postgres
        sleep 5
    fi
    
    # Ensure admin_users table exists
    echo -e "${YELLOW}Ensuring admin_users table exists...${NC}"
    docker-compose exec postgres psql -U aibot -d aibot -c "
    CREATE TABLE IF NOT EXISTS admin_users (
        id VARCHAR(36) PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        email VARCHAR(100),
        password_hash VARCHAR(200) NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );"
    
    # Add default admin user
    echo -e "${YELLOW}Adding default admin user...${NC}"
    docker-compose exec postgres psql -U aibot -d aibot -c "
    INSERT INTO admin_users (id, username, password_hash, is_active)
    SELECT 
      'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 
      'admin', 
      'pbkdf2:sha256:150000\$KKgd0xN3\$d57b15c874bd9b5f30d7c1ef6006d1a162970a702e9e76bb51a1f7543b63212b', 
      true
    WHERE NOT EXISTS (
      SELECT 1 FROM admin_users WHERE username = 'admin'
    );"
    
    echo -e "${GREEN}PostgreSQL fixes applied${NC}"
}

# Function to display usage information
function show_help {
    echo -e "${YELLOW}Usage:${NC}"
    echo -e "  ${GREEN}./run.sh [command]${NC}"
    echo -e "\n${YELLOW}Available commands:${NC}"
    echo -e "  ${GREEN}start${NC}         - Start all services using Docker Compose"
    echo -e "  ${GREEN}start-api${NC}     - Start only the API service"
    echo -e "  ${GREEN}start-admin${NC}   - Start only the admin panel"
    echo -e "  ${GREEN}start-bot${NC}     - Start only the Telegram bot"
    echo -e "  ${GREEN}build${NC}         - Build all Docker images"
    echo -e "  ${GREEN}stop${NC}          - Stop all services"
    echo -e "  ${GREEN}restart${NC}       - Restart all services"
    echo -e "  ${GREEN}logs${NC}          - View logs from all services"
    echo -e "  ${GREEN}logs-api${NC}      - View logs from the API service"
    echo -e "  ${GREEN}logs-admin${NC}    - View logs from the admin panel"
    echo -e "  ${GREEN}logs-bot${NC}      - View logs from the Telegram bot"
    echo -e "  ${GREEN}postgres${NC}      - Access PostgreSQL shell"
    echo -e "  ${GREEN}init-db${NC}       - Initialize the database"
    echo -e "  ${GREEN}direct-api${NC}    - Run the API directly (without Docker)"
    echo -e "  ${GREEN}direct-admin${NC}  - Run the admin panel directly"
    echo -e "  ${GREEN}direct-bot${NC}    - Run the Telegram bot directly"
    echo -e "  ${GREEN}status${NC}        - Check status of all services"
    echo -e "  ${GREEN}fix-postgres${NC}  - Fix PostgreSQL connection issues"
    echo -e "  ${GREEN}diagnose${NC}      - Run diagnostics on containers"
    echo -e "  ${GREEN}help${NC}          - Show this help message"
    echo -e "  ${GREEN}create-test-chars${NC} - Create test characters"
}

# Function to start all services using Docker Compose
function start_all {
    echo -e "${BLUE}Starting all services...${NC}"
    docker-compose up -d
    echo -e "${GREEN}Services started! Access:${NC}"
    echo -e "  - API: http://localhost:8000/docs"
    echo -e "  - Admin Panel: http://localhost:5000"
}

# Function to start only the API service
function start_api {
    echo -e "${BLUE}Starting API service...${NC}"
    docker-compose up -d api
    echo -e "${GREEN}API service started! Access:${NC}"
    echo -e "  - API: http://localhost:8000/docs"
}

# Function to start only the admin panel
function start_admin {
    echo -e "${BLUE}Starting Admin Panel...${NC}"
    docker-compose up -d admin
    echo -e "${GREEN}Admin Panel started! Access:${NC}"
    echo -e "  - Admin Panel: http://localhost:5000"
}

# Function to start only the Telegram bot
function start_bot {
    echo -e "${BLUE}Starting Telegram bot...${NC}"
    docker-compose up -d telegram
    echo -e "${GREEN}Telegram bot started!${NC}"
}

# Function to build all Docker images
function build_all {
    echo -e "${BLUE}Building all Docker images...${NC}"
    docker-compose build
    echo -e "${GREEN}Build completed!${NC}"
}

# Function to stop all services
function stop_all {
    echo -e "${BLUE}Stopping all services...${NC}"
    docker-compose down
    echo -e "${GREEN}All services stopped!${NC}"
}

# Function to restart all services
function restart_all {
    echo -e "${BLUE}Restarting all services...${NC}"
    docker-compose restart
    echo -e "${GREEN}All services restarted!${NC}"
}

# Function to view logs from all services
function view_logs {
    echo -e "${BLUE}Viewing logs from all services...${NC}"
    echo -e "${YELLOW}Press Ctrl+C to exit logs${NC}"
    docker-compose logs -f
}

# Function to view logs from the API service
function view_api_logs {
    echo -e "${BLUE}Viewing logs from API service...${NC}"
    echo -e "${YELLOW}Press Ctrl+C to exit logs${NC}"
    docker-compose logs -f api
}

# Function to view logs from the admin panel
function view_admin_logs {
    echo -e "${BLUE}Viewing logs from Admin Panel...${NC}"
    echo -e "${YELLOW}Press Ctrl+C to exit logs${NC}"
    docker-compose logs -f admin
}

# Function to view logs from the Telegram bot
function view_bot_logs {
    echo -e "${BLUE}Viewing logs from Telegram bot...${NC}"
    echo -e "${YELLOW}Press Ctrl+C to exit logs${NC}"
    docker-compose logs -f telegram
}

# Function to access PostgreSQL shell
function postgres_shell {
    echo -e "${BLUE}Accessing PostgreSQL shell...${NC}"
    docker-compose exec postgres psql -U aibot -d aibot
}

# Function to initialize the database
function initialize_db {
    echo -e "${BLUE}Initializing database...${NC}"
    # First, ensure admin_users table exists
    fix_postgres_issue
    # Then run initialization scripts
    docker-compose exec admin python -m admin_panel.init_db
    echo -e "${GREEN}Database initialized!${NC}"
}

# Function to run the API directly (without Docker)
function run_api_direct {
    echo -e "${BLUE}Running API directly...${NC}"
    echo -e "${YELLOW}Make sure you have all dependencies installed!${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop the API${NC}"
    cd app && uvicorn main:app --reload --host 0.0.0.0 --port 8000
}

# Function to run the admin panel directly
function run_admin_direct {
    echo -e "${BLUE}Running Admin Panel directly...${NC}"
    echo -e "${YELLOW}Make sure you have all dependencies installed!${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop the Admin Panel${NC}"
    cd admin_panel && python app.py
}

# Function to run the Telegram bot directly
function run_bot_direct {
    echo -e "${BLUE}Running Telegram bot directly...${NC}"
    echo -e "${YELLOW}Make sure you have all dependencies installed!${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop the Telegram bot${NC}"
    cd bots && python bot.py
}

# Function to run diagnostics
function run_diagnostics {
    if [ -f ./scripts/check-containers.sh ]; then
        echo -e "${BLUE}Running container diagnostics...${NC}"
        chmod +x ./scripts/check-containers.sh
        ./scripts/check-containers.sh
    else
        echo -e "${RED}Diagnostic script not found!${NC}"
        echo -e "${YELLOW}Showing container status instead:${NC}"
        docker-compose ps
    fi
}

# Function to check status of all services
function check_status {
    echo -e "${BLUE}Checking status of all services...${NC}"
    docker-compose ps
    
    echo -e "\n${BLUE}Checking PostgreSQL...${NC}"
    if docker-compose exec postgres pg_isready -U aibot 2>/dev/null; then
        echo -e "${GREEN}PostgreSQL is ready!${NC}"
    else
        echo -e "${RED}PostgreSQL is not ready!${NC}"
    fi
    
    echo -e "\n${BLUE}Checking API...${NC}"
    if curl -s http://localhost:8000/health > /dev/null; then
        echo -e "${GREEN}API is running!${NC}"
    else
        echo -e "${RED}API is not responding!${NC}"
    fi
    
    echo -e "\n${BLUE}Checking Admin Panel...${NC}"
    if curl -s http://localhost:5000 > /dev/null; then
        echo -e "${GREEN}Admin Panel is running!${NC}"
    else
        echo -e "${RED}Admin Panel is not responding!${NC}"
    fi
}

# Function to create test characters
function create_test_chars {
    echo -e "${BLUE}Creating test characters...${NC}"
    python scripts/create_test_characters.py
    echo -e "${GREEN}Test characters created!${NC}"
}

# Parse command line arguments
case "$1" in
    start)
        start_all
        ;;
    start-api)
        start_api
        ;;
    start-admin)
        start_admin
        ;;
    start-bot)
        start_bot
        ;;
    build)
        build_all
        ;;
    stop)
        stop_all
        ;;
    restart)
        restart_all
        ;;
    logs)
        view_logs
        ;;
    logs-api)
        view_api_logs
        ;;
    logs-admin)
        view_admin_logs
        ;;
    logs-bot)
        view_bot_logs
        ;;
    postgres)
        postgres_shell
        ;;
    init-db)
        initialize_db
        ;;
    direct-api)
        run_api_direct
        ;;
    direct-admin)
        run_admin_direct
        ;;
    direct-bot)
        run_bot_direct
        ;;
    status)
        check_status
        ;;
    fix-postgres)
        fix_postgres_issue
        ;;
    diagnose)
        run_diagnostics
        ;;
    create-test-chars)
        create_test_chars
        ;;
    help)
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        show_help
        exit 1
        ;;
esac

exit 0
