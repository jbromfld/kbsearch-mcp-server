#!/bin/bash
# ============================================================================
# MCP Demo System Startup Script
# ============================================================================
# This script starts the complete MCP demo system including:
# - PostgreSQL with pgvector (both databases)
# - RAG Service (knowledge base search)
# - NL2SQL Service (CI/CD queries)
# - MCP Server (main API)
# ============================================================================

set -e  # Exit on error

echo "======================================================================"
echo "  MCP Demo System - Startup Script"
echo "======================================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

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

# Check if Docker is running
echo "Checking prerequisites..."
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi
print_status "Docker is running"

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    print_error "docker-compose is not installed. Please install docker-compose and try again."
    exit 1
fi
print_status "docker-compose is available"

# Check if required directories exist
if [ ! -d "../rag-mcp" ]; then
    print_error "RAG MCP directory not found at ../rag-mcp"
    print_warning "Make sure the rag-mcp repository is cloned in the parent directory"
    exit 1
fi

if [ ! -d "../nl2sql-mcp" ]; then
    print_error "NL2SQL MCP directory not found at ../nl2sql-mcp"
    print_warning "Make sure the nl2sql-mcp repository is cloned in the parent directory"
    exit 1
fi
print_status "All required directories found"

echo ""
echo "======================================================================"
echo "  Building and Starting Services"
echo "======================================================================"
echo ""

# Stop any existing containers
print_status "Stopping any existing containers..."
docker-compose -f docker-compose-all.yml down 2>/dev/null || true

# Build and start services
print_status "Building Docker images (this may take a few minutes)..."
docker-compose -f docker-compose-all.yml build --no-cache

print_status "Starting services..."
docker-compose -f docker-compose-all.yml up -d

echo ""
echo "======================================================================"
echo "  Waiting for Services to be Ready"
echo "======================================================================"
echo ""

# Wait for PostgreSQL
print_status "Waiting for PostgreSQL to be ready..."
timeout=60
counter=0
until docker exec demo-postgres pg_isready -U testuser > /dev/null 2>&1; do
    sleep 1
    counter=$((counter + 1))
    if [ $counter -gt $timeout ]; then
        print_error "PostgreSQL failed to start within ${timeout} seconds"
        docker-compose -f docker-compose-all.yml logs postgres
        exit 1
    fi
done
print_status "PostgreSQL is ready"

# Wait for RAG service
print_status "Waiting for RAG service to be ready..."
counter=0
until curl -sf http://localhost:8000/health > /dev/null 2>&1; do
    sleep 2
    counter=$((counter + 2))
    if [ $counter -gt $timeout ]; then
        print_warning "RAG service health check timeout (this may be normal if the service doesn't have a /health endpoint)"
        break
    fi
done
print_status "RAG service is ready"

# Wait for NL2SQL service
print_status "Waiting for NL2SQL service to be ready..."
counter=0
until curl -sf http://localhost:8088/health > /dev/null 2>&1; do
    sleep 2
    counter=$((counter + 2))
    if [ $counter -gt $timeout ]; then
        print_error "NL2SQL service failed to start within ${timeout} seconds"
        docker-compose -f docker-compose-all.yml logs nl2sql-service
        exit 1
    fi
done
print_status "NL2SQL service is ready"

# Wait for MCP server
print_status "Waiting for MCP server to be ready..."
counter=0
until curl -sf http://localhost:8080/mcp > /dev/null 2>&1; do
    sleep 2
    counter=$((counter + 2))
    if [ $counter -gt $timeout ]; then
        print_error "MCP server failed to start within ${timeout} seconds"
        docker-compose -f docker-compose-all.yml logs mcp-server
        exit 1
    fi
done
print_status "MCP server is ready"

echo ""
echo "======================================================================"
echo "  System Status"
echo "======================================================================"
echo ""

# Show running containers
docker-compose -f docker-compose-all.yml ps

echo ""
echo "======================================================================"
echo "  Service Endpoints"
echo "======================================================================"
echo ""
echo "  PostgreSQL:    localhost:5434"
echo "    - RAG DB:      rag_service"
echo "    - CI/CD DB:    cicd_service"
echo "    - User:        testuser"
echo "    - Password:    testpass"
echo ""
echo "  RAG Service:   http://localhost:8000"
echo "  NL2SQL Service: http://localhost:8088"
echo "  MCP Server:    http://localhost:8080/mcp"
echo ""
echo "======================================================================"
echo "  Testing the System"
echo "======================================================================"
echo ""

# Test RAG service (if it has sample data)
print_status "Testing RAG service..."
if curl -s -X POST http://localhost:8000/query \
    -H "Content-Type: application/json" \
    -d '{"query": "test"}' > /dev/null 2>&1; then
    print_status "RAG service responding"
else
    print_warning "RAG service may need initialization or data ingestion"
fi

# Test NL2SQL service
print_status "Testing NL2SQL service..."
if curl -s -X POST http://localhost:8088/prepare \
    -H "Content-Type: application/json" \
    -d '{"query": "Show me deployments"}' > /dev/null 2>&1; then
    print_status "NL2SQL service responding"
else
    print_warning "NL2SQL service test failed"
fi

# Check database contents
print_status "Checking database contents..."
DEPLOYMENT_COUNT=$(docker exec demo-postgres psql -U testuser -d cicd_service -t -c "SELECT COUNT(*) FROM deployment_data;" 2>/dev/null | tr -d ' \n')
if [ -n "$DEPLOYMENT_COUNT" ] && [ "$DEPLOYMENT_COUNT" -gt 0 ]; then
    print_status "Found $DEPLOYMENT_COUNT deployment records in CI/CD database"
else
    print_warning "No deployment data found (database may still be initializing)"
fi

echo ""
echo "======================================================================"
echo "  Success! MCP Demo System is Running"
echo "======================================================================"
echo ""
echo "Configure your MCP client to connect to:"
echo "  URL: http://localhost:8080/mcp"
echo ""
echo "Useful commands:"
echo "  View logs:       docker-compose -f docker-compose-all.yml logs -f"
echo "  Stop system:     docker-compose -f docker-compose-all.yml down"
echo "  Restart system:  docker-compose -f docker-compose-all.yml restart"
echo "  View status:     docker-compose -f docker-compose-all.yml ps"
echo ""
echo "Database access:"
echo "  psql -h localhost -p 5434 -U testuser -d rag_service"
echo "  psql -h localhost -p 5434 -U testuser -d cicd_service"
echo ""
