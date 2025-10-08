#!/bin/bash

# Article Extraction System - Simple Development Startup Script
# Starts all services and keeps them running

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

# Get project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to cleanup all services
cleanup() {
    print_status "Stopping all services..."
    pkill -f "go run cmd/api/main.go" 2>/dev/null || true
    pkill -f "go run cmd/worker/main.go" 2>/dev/null || true
    pkill -f "python app/main.py" 2>/dev/null || true
    pkill -f "npm run dev" 2>/dev/null || true
    print_success "All services stopped"
    exit 0
}

# Set up cleanup on interrupt
trap cleanup INT

print_status "Starting Article Extraction System for development..."
echo "================================================"

# Start Go API
print_status "Starting Go API..."
cd "$PROJECT_ROOT/api"
go run cmd/api/main.go &
GO_API_PID=$!
echo "Go API started with PID $GO_API_PID"

# Start Go Worker
print_status "Starting Go Worker..."
cd "$PROJECT_ROOT/worker-go"
go run cmd/worker/main.go &
GO_WORKER_PID=$!
echo "Go Worker started with PID $GO_WORKER_PID"

# Start Python AI Worker
print_status "Starting Python AI Worker..."
cd "$PROJECT_ROOT/worker-python"
source venv/bin/activate && python app/main.py &
PYTHON_WORKER_PID=$!
echo "Python AI Worker started with PID $PYTHON_WORKER_PID"

# Start React Frontend
print_status "Starting React Frontend..."
cd "$PROJECT_ROOT/frontend"
npm run dev &
FRONTEND_PID=$!
echo "React Frontend started with PID $FRONTEND_PID"

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

# Wait for services to start
sleep 5

# Check if services are running
print_status "Checking service status..."
if netstat -tlnp 2>/dev/null | grep -q ":8080 "; then
    print_success "Go API is running on port 8080"
else
    print_warning "Go API may not be running"
fi

if netstat -tlnp 2>/dev/null | grep -q ":8081 "; then
    print_success "Python AI Worker is running on port 8081"
else
    print_warning "Python AI Worker may not be running"
fi

if netstat -tlnp 2>/dev/null | grep -q ":5173 "; then
    print_success "React Frontend is running on port 5173"
else
    print_warning "React Frontend may not be running"
fi

echo ""
print_status "All services are running. Press Ctrl+C to stop all services."

# Keep script running
while true; do
    sleep 10
    # Check if any service died
    if ! kill -0 $GO_API_PID 2>/dev/null; then
        print_warning "Go API has stopped unexpectedly"
    fi
    if ! kill -0 $GO_WORKER_PID 2>/dev/null; then
        print_warning "Go Worker has stopped unexpectedly"
    fi
    if ! kill -0 $PYTHON_WORKER_PID 2>/dev/null; then
        print_warning "Python AI Worker has stopped unexpectedly"
    fi
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        print_warning "React Frontend has stopped unexpectedly"
    fi
done



