#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Service directories
RAG_DIR="/Users/jbromfield/workspace/rag-mcp"
NL2SQL_DIR="/Users/jbromfield/workspace/nl2sql-mcp"
MCP_DIR="/Users/jbromfield/workspace/kbsearch-mcp-server"

# PID files
PID_DIR="$MCP_DIR/.pids"
RAG_PID="$PID_DIR/rag.pid"
NL2SQL_PID="$PID_DIR/nl2sql.pid"
MCP_PID="$PID_DIR/mcp.pid"

# Log files
LOG_DIR="$MCP_DIR/.logs"
RAG_LOG="$LOG_DIR/rag.log"
NL2SQL_LOG="$LOG_DIR/nl2sql.log"
MCP_LOG="$LOG_DIR/mcp.log"

# Create directories
mkdir -p "$PID_DIR"
mkdir -p "$LOG_DIR"

# Function to print colored output
print_status() {
    echo -e "${BLUE}==>${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Function to check if a port is in use
check_port() {
    local port=$1
    lsof -i :$port -sTCP:LISTEN >/dev/null 2>&1
}

# Function to check if a service is running
is_running() {
    local pid_file=$1
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p $pid > /dev/null 2>&1; then
            return 0
        else
            rm -f "$pid_file"
            return 1
        fi
    fi
    return 1
}

# Function to start RAG service
start_rag() {
    print_status "Starting RAG service (port 8000)..."

    if check_port 8000; then
        print_warning "Port 8000 already in use"
        return 1
    fi

    cd "$RAG_DIR"
    # Use RAG's own venv to start uvicorn
    nohup .venv/bin/python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 > "$RAG_LOG" 2>&1 &
    echo $! > "$RAG_PID"

    # Wait for service to be ready
    sleep 3
    if check_port 8000; then
        print_success "RAG service started (PID: $(cat $RAG_PID))"
    else
        print_error "RAG service failed to start (check $RAG_LOG)"
        return 1
    fi
}

# Function to start NL2SQL API
start_nl2sql() {
    print_status "Starting NL2SQL API (port 8088)..."

    if check_port 8088; then
        print_warning "Port 8088 already in use"
        return 1
    fi

    cd "$NL2SQL_DIR"
    nohup python3 app/api_server.py > "$NL2SQL_LOG" 2>&1 &
    echo $! > "$NL2SQL_PID"

    # Wait for service to be ready
    sleep 3
    if check_port 8088; then
        print_success "NL2SQL API started (PID: $(cat $NL2SQL_PID))"
    else
        print_error "NL2SQL API failed to start (check $NL2SQL_LOG)"
        return 1
    fi
}

# Function to start MCP server
start_mcp() {
    print_status "Starting MCP server (port 8080)..."

    if check_port 8080; then
        print_warning "Port 8080 already in use"
        return 1
    fi

    cd "$MCP_DIR"
    nohup .venv/bin/python server.py > "$MCP_LOG" 2>&1 &
    echo $! > "$MCP_PID"

    # Wait for service to be ready
    sleep 2
    if check_port 8080; then
        print_success "MCP server started (PID: $(cat $MCP_PID))"
    else
        print_error "MCP server failed to start (check $MCP_LOG)"
        return 1
    fi
}

# Function to stop a service
stop_service() {
    local name=$1
    local pid_file=$2

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p $pid > /dev/null 2>&1; then
            print_status "Stopping $name (PID: $pid)..."
            kill $pid
            sleep 1

            # Force kill if still running
            if ps -p $pid > /dev/null 2>&1; then
                kill -9 $pid 2>/dev/null || true
            fi

            rm -f "$pid_file"
            print_success "$name stopped"
        else
            rm -f "$pid_file"
            print_warning "$name was not running"
        fi
    else
        print_warning "$name PID file not found"
    fi
}

# Function to stop all services
stop_all() {
    echo ""
    print_status "Stopping all services..."
    stop_service "MCP server" "$MCP_PID"
    stop_service "NL2SQL API" "$NL2SQL_PID"
    stop_service "RAG service" "$RAG_PID"
    echo ""
    print_success "All services stopped"
}

# Function to show status
show_status() {
    echo ""
    print_status "Service Status:"
    echo ""

    # RAG service
    if is_running "$RAG_PID"; then
        print_success "RAG service running (PID: $(cat $RAG_PID), Port: 8000)"
    else
        print_error "RAG service not running"
    fi

    # NL2SQL API
    if is_running "$NL2SQL_PID"; then
        print_success "NL2SQL API running (PID: $(cat $NL2SQL_PID), Port: 8088)"
    else
        print_error "NL2SQL API not running"
    fi

    # MCP server
    if is_running "$MCP_PID"; then
        print_success "MCP server running (PID: $(cat $MCP_PID), Port: 8080)"
    else
        print_error "MCP server not running"
    fi

    echo ""
}

# Function to show logs
show_logs() {
    local service=$1

    case $service in
        rag)
            tail -f "$RAG_LOG"
            ;;
        nl2sql)
            tail -f "$NL2SQL_LOG"
            ;;
        mcp)
            tail -f "$MCP_LOG"
            ;;
        all)
            tail -f "$RAG_LOG" "$NL2SQL_LOG" "$MCP_LOG"
            ;;
        *)
            print_error "Unknown service: $service"
            print_status "Available services: rag, nl2sql, mcp, all"
            exit 1
            ;;
    esac
}

# Function to restart all services
restart_all() {
    stop_all
    sleep 2
    start_all
}

# Function to start all services
start_all() {
    echo ""
    print_status "Starting all services..."
    echo ""

    # Start services in order
    start_rag || true
    start_nl2sql || true
    start_mcp || true

    echo ""
    show_status

    print_status "Logs are available at:"
    echo "  RAG:     $RAG_LOG"
    echo "  NL2SQL:  $NL2SQL_LOG"
    echo "  MCP:     $MCP_LOG"
    echo ""
    print_status "Use '$0 logs <service>' to tail logs"
    print_status "Use '$0 stop' to stop all services"
    echo ""
}

# Main script
case "${1:-start}" in
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
    restart)
        restart_all
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "${2:-all}"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs [rag|nl2sql|mcp|all]}"
        exit 1
        ;;
esac
