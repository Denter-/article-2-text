#!/bin/bash

# Article Extraction System - Development Startup Script
# Quick start for development with all services in foreground

# Don't exit on errors - we want to continue even if some services fail
# set -e

# Get project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to start service in background
start_bg() {
    local name=$1
    local cmd=$2
    local dir=$3
    local port=$4
    
    print_status "Starting $name..."
    cd "$PROJECT_ROOT/$dir"
    $cmd > "/tmp/${name}.log" 2>&1 &
    local pid=$!
    echo "$name started with PID $pid"
    
    # Store PID for cleanup
    echo $pid > "/tmp/${name}.pid"
    
    # Wait for service to be ready if port is specified
    if [ -n "$port" ]; then
        wait_for_service "$name" "$port" || print_warning "$name may not be ready yet"
    fi
}

# Function to wait for service to be ready
wait_for_service() {
    local name=$1
    local port=$2
    local max_attempts=30
    local attempt=0
    
    print_status "Waiting for $name to be ready..."
    
    while [ $attempt -lt $max_attempts ]; do
        if netstat -tlnp 2>/dev/null | grep -q ":$port "; then
            print_success "$name is ready on port $port"
            return 0
        fi
        sleep 1
        attempt=$((attempt + 1))
    done
    
    print_warning "$name may not be ready yet"
    return 1
}

# Check if services are already running
if netstat -tlnp 2>/dev/null | grep -q ":8080 "; then
    print_warning "Port 8080 is already in use. Please stop existing services first."
    exit 1
fi

if netstat -tlnp 2>/dev/null | grep -q ":5173 "; then
    print_warning "Port 5173 is already in use. Please stop existing services first."
    exit 1
fi

print_status "Starting Article Extraction System for development..."
echo "================================================"

# Start Go API
start_bg "Go API" "go run cmd/api/main.go" "api" "8080"

# Start Go Worker
start_bg "Go Worker" "go run cmd/worker/main.go" "worker-go"

# Start Python AI Worker
start_bg "Python AI Worker" "source venv/bin/activate && python app/main.py" "worker-python" "8081"

# Start React Frontend
start_bg "React Frontend" "npm run dev" "frontend" "5173"

echo "================================================"
print_success "All services started!"
echo ""
print_status "Service URLs:"
echo "  - API: http://localhost:8080"
echo "  - Frontend: http://localhost:5173"
echo "  - Python Worker: http://localhost:8081"
echo ""
print_status "Press Ctrl+C to stop all services"
echo ""

# Wait a moment for all services to fully start
sleep 3

# Function to cleanup all services
cleanup() {
    print_status "Stopping all services..."
    
    # Kill services by PID files
    for pid_file in /tmp/*.pid; do
        if [ -f "$pid_file" ]; then
            local service_name=$(basename "$pid_file" .pid)
            local pid=$(cat "$pid_file")
            if kill -0 "$pid" 2>/dev/null; then
                print_status "Stopping $service_name (PID: $pid)..."
                kill "$pid" 2>/dev/null || true
            fi
            rm -f "$pid_file"
        fi
    done
    
    # Kill any remaining background jobs
    kill $(jobs -p) 2>/dev/null || true
    
    print_success "All services stopped"
    exit 0
}

# Wait for user interrupt
trap cleanup INT

# Keep script running and show logs
print_status "All services are running. Press Ctrl+C to stop all services."
print_status "View logs with: tail -f /tmp/[service-name].log"
echo ""

# Show a rotating view of all logs
while true; do
    sleep 5
    # Check if any service died
    for pid_file in /tmp/*.pid; do
        if [ -f "$pid_file" ]; then
            local pid=$(cat "$pid_file")
            if ! kill -0 "$pid" 2>/dev/null; then
                local service_name=$(basename "$pid_file" .pid)
                print_warning "$service_name has stopped unexpectedly"
            fi
        fi
    done
done
