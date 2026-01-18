#!/bin/bash

set -e  # Exit on any error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICES=(
    "rag-mcp"
    "nl2sql-mcp"
    "kbsearch-mcp-server"
)

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_port() {
    # Find and stop Docker containers using these ports
    for port in 8088 8080 8000; do
        echo "Checking port $port..."
        
        # Find container using this port
        container=$(docker ps --format '{{.ID}} {{.Ports}}' | grep ":$port->" | awk '{print $1}')
        
        if [ ! -z "$container" ]; then
            echo "Stopping Docker container $container on port $port"
            docker stop $container
        else
            # Not a Docker container, check for other processes
            if lsof -t -i:$port > /dev/null 2>&1; then
                pid=$(lsof -t -i:$port)
                proc_name=$(ps -p $pid -o comm=)
                echo "Found non-Docker process '$proc_name' (PID: $pid) on port $port"
                echo "Kill it? (y/n)"
                read answer
                if [ "$answer" = "y" ]; then
                    kill $pid
                    echo "Killed PID $pid"
                fi
            else
                echo "No process found on port $port"
            fi
        fi
    done
}
# Function to set up a virtual environment
setup_venv() {
    local service_name=$1
    local service_path="${SCRIPT_DIR}/../${service_name}"
    
    if [ ! -d "$service_path" ]; then
        log_error "Service directory not found: $service_path"
        return 1
    fi
    
    log_info "Setting up virtual environment for $service_name..."
    
    cd "$service_path"
    
    # Check if venv exists
    if [ ! -d ".venv" ]; then
        log_warn "Virtual environment not found. Creating new venv..."
        python3 -m venv .venv
    fi
    
    # Activate and install dependencies
    source .venv/bin/activate
    
    # Upgrade pip first
    pip install --upgrade pip > /dev/null 2>&1
    
    # Install requirements
    if [ -f "requirements.txt" ]; then
        log_info "Installing dependencies for $service_name..."
        pip install -r requirements.txt --quiet
    else
        log_warn "No requirements.txt found for $service_name"
    fi
    
    deactivate
    
    log_info "✓ $service_name virtual environment ready"
}

# Function to reset database for a service
reset_db() {
    local service_name=$1
    local service_path="${SCRIPT_DIR}/../${service_name}"
    local reset_script="${service_path}/scripts/reset_db.py"
    
    if [ ! -f "$reset_script" ]; then
        log_warn "No reset script found for $service_name, skipping..."
        return 0
    fi
    
    log_info "Resetting database for $service_name..."
    
    cd "$service_path"
    source .venv/bin/activate
    
    if python3 "$reset_script"; then
        log_info "✓ Database reset complete for $service_name"
    else
        log_error "Failed to reset database for $service_name"
        return 1
    fi
    
    deactivate
}

# Function to start a service
start_service() {
    local service_name=$1
    local service_path="${SCRIPT_DIR}/../${service_name}"
    local compose_file="${service_path}/docker-compose.yml"
    
    if [ ! -f "$compose_file" ]; then
        log_error "docker-compose.yml not found for $service_name"
        return 1
    fi
    
    log_info "Starting $service_name..."
    
    if docker-compose -f "$compose_file" up -d; then
        log_info "✓ $service_name started successfully"
    else
        log_error "Failed to start $service_name"
        return 1
    fi
}

# Function to stop a service
stop_service() {
    local service_name=$1
    local service_path="${SCRIPT_DIR}/../${service_name}"
    local compose_file="${service_path}/docker-compose.yml"
    
    if [ ! -f "$compose_file" ]; then
        log_warn "docker-compose.yml not found for $service_name, skipping..."
        return 0
    fi
    
    log_info "Stopping $service_name..."
    docker-compose -f "$compose_file" down
}

# Function to show service status
show_status() {
    log_info "Service Status:"
    echo ""
    
    for service in "${SERVICES[@]}"; do
        local service_path="${SCRIPT_DIR}/../${service}"
        local compose_file="${service_path}/docker-compose.yml"
        
        if [ -f "$compose_file" ]; then
            echo "=== $service ==="
            docker-compose -f "$compose_file" ps
            echo ""
        fi
    done
}

# Parse command line arguments
COMMAND=${1:-"start"}
RESET_DB=false

case "$COMMAND" in
    start)
        RESET_DB=false
        ;;
    reset)
        RESET_DB=true
        ;;
    stop)
        log_info "Stopping all services..."
        for service in "${SERVICES[@]}"; do
            stop_service "$service"
        done
        log_info "All services stopped"
        exit 0
        ;;
    restart)
        log_info "Restarting all services..."
        for service in "${SERVICES[@]}"; do
            stop_service "$service"
        done
        sleep 2
        RESET_DB=false
        ;;
    status)
        show_status
        exit 0
        ;;
    help|--help|-h)
        echo "Usage: $0 [COMMAND]"
        echo ""
        echo "Commands:"
        echo "  start     - Start all services (default)"
        echo "  reset     - Reset databases and start services"
        echo "  stop      - Stop all services"
        echo "  restart   - Restart all services"
        echo "  status    - Show status of all services"
        echo "  help      - Show this help message"
        exit 0
        ;;
    *)
        log_error "Unknown command: $COMMAND"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac

# Main execution
main() {
    log_info "Starting setup process..."
    
    # Check prerequisites
    if ! command -v docker-compose &> /dev/null; then
        log_error "docker-compose not found. Please install it first."
        exit 1
    fi
    
    if ! command -v python3 &> /dev/null; then
        log_error "python3 not found. Please install it first."
        exit 1
    fi
    
    # Set up virtual environments
    log_info "Setting up virtual environments..."
    check_port
    for service in "${SERVICES[@]}"; do
        setup_venv "$service" || {
            log_error "Failed to set up venv for $service"
            exit 1
        }
    done
    
    # Reset databases if requested
    if [ "$RESET_DB" = true ]; then
        log_info "Resetting databases..."
        for service in "${SERVICES[@]}"; do
            reset_db "$service" || {
                log_error "Failed to reset database for $service"
                exit 1
            }
        done
    fi
    
    # Start services
    log_info "Starting services..."
    for service in "${SERVICES[@]}"; do
        start_service "$service" || {
            log_error "Failed to start $service"
            exit 1
        }
    done
    
    # Wait a moment for services to initialize
    sleep 3
    
    # Show status
    show_status
    
    log_info "All services started successfully!"
    log_info "Use '$0 status' to check service status"
    log_info "Use '$0 stop' to stop all services"
}

# Run main function
main