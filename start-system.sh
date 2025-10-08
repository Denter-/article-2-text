#!/bin/bash

# Article Extraction System - Full System Startup Script
# This script starts all required services for the complete system

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
PID_DIR="$PROJECT_ROOT/.pids"

# Create necessary directories
mkdir -p "$LOG_DIR"
mkdir -p "$PID_DIR"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a service is running
check_service() {
    local service_name=$1
    local port=$2
    local pid_file="$PID_DIR/$service_name.pid"
    
    if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
        return 0
    fi
    
    if [ -n "$port" ] && netstat -tlnp 2>/dev/null | grep -q ":$port "; then
        return 0
    fi
    
    return 1
}

# Function to start a service
start_service() {
    local service_name=$1
    local port=$2
    local start_command=$3
    local working_dir=$4
    local pid_file="$PID_DIR/$service_name.pid"
    
    if check_service "$service_name" "$port"; then
        print_warning "$service_name is already running"
        return 0
    fi
    
    print_status "Starting $service_name..."
    
    cd "$working_dir"
    nohup $start_command > "$LOG_DIR/$service_name.log" 2>&1 &
    local pid=$!
    echo $pid > "$pid_file"
    
    # Wait a moment and check if it started successfully
    sleep 2
    if check_service "$service_name" "$port"; then
        print_success "$service_name started successfully (PID: $pid)"
    else
        print_error "$service_name failed to start. Check $LOG_DIR/$service_name.log"
        return 1
    fi
}

# Function to stop a service
stop_service() {
    local service_name=$1
    local pid_file="$PID_DIR/$service_name.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            print_status "Stopping $service_name (PID: $pid)..."
            kill "$pid"
            rm -f "$pid_file"
            print_success "$service_name stopped"
        else
            print_warning "$service_name was not running"
            rm -f "$pid_file"
        fi
    else
        print_warning "$service_name was not running"
    fi
}

# Function to check dependencies
check_dependencies() {
    print_status "Checking system dependencies..."
    
    # Check PostgreSQL
    if ! command -v psql &> /dev/null; then
        print_error "PostgreSQL is not installed or not in PATH"
        exit 1
    fi
    
    # Check Redis
    if ! command -v redis-cli &> /dev/null; then
        print_error "Redis is not installed or not in PATH"
        exit 1
    fi
    
    # Check Go
    if ! command -v go &> /dev/null; then
        print_error "Go is not installed or not in PATH"
        exit 1
    fi
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        print_error "Node.js is not installed or not in PATH"
        exit 1
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed or not in PATH"
        exit 1
    fi
    
    print_success "All dependencies are available"
}

# Function to check if services are accessible
check_services() {
    print_status "Checking service accessibility..."
    
    # Check PostgreSQL
    if ! psql -U postgres -d article_extraction -c "SELECT 1;" &> /dev/null; then
        print_error "Cannot connect to PostgreSQL database 'article_extraction'"
        print_status "Please ensure PostgreSQL is running and the database exists"
        print_status "Run: sudo -u postgres createdb article_extraction"
        exit 1
    fi
    
    # Check Redis
    if ! redis-cli ping &> /dev/null; then
        print_error "Cannot connect to Redis"
        print_status "Please ensure Redis is running"
        print_status "Run: sudo systemctl start redis-server"
        exit 1
    fi
    
    print_success "All services are accessible"
}

# Function to start all services
start_all() {
    print_status "Starting Article Extraction System..."
    echo "================================================"
    
    # Check dependencies first
    check_dependencies
    check_services
    
    # Start services in order
    start_service "go-api" "8080" "go run cmd/api/main.go" "$PROJECT_ROOT/api"
    start_service "go-worker" "" "go run cmd/worker/main.go" "$PROJECT_ROOT/worker-go"
    start_service "python-worker" "8081" "source venv/bin/activate && python app/main.py" "$PROJECT_ROOT/worker-python"
    start_service "react-frontend" "5173" "npm run dev" "$PROJECT_ROOT/frontend"
    
    echo "================================================"
    print_success "All services started successfully!"
    echo ""
    print_status "Service URLs:"
    echo "  - API: http://localhost:8080"
    echo "  - Frontend: http://localhost:5173"
    echo "  - Python Worker: http://localhost:8081"
    echo ""
    print_status "Logs are available in: $LOG_DIR"
    print_status "PID files are stored in: $PID_DIR"
    echo ""
    print_status "To stop all services, run: $0 stop"
    print_status "To check status, run: $0 status"
}

# Function to stop all services
stop_all() {
    print_status "Stopping Article Extraction System..."
    echo "================================================"
    
    stop_service "react-frontend"
    stop_service "python-worker"
    stop_service "go-worker"
    stop_service "go-api"
    
    echo "================================================"
    print_success "All services stopped"
}

# Function to show status
show_status() {
    print_status "Article Extraction System Status"
    echo "================================================"
    
    local services=("go-api:8080" "go-worker:" "python-worker:8081" "react-frontend:5173")
    
    for service_info in "${services[@]}"; do
        IFS=':' read -r service_name port <<< "$service_info"
        if check_service "$service_name" "$port"; then
            print_success "$service_name: Running"
        else
            print_error "$service_name: Not running"
        fi
    done
    
    echo ""
    print_status "Log files:"
    for log_file in "$LOG_DIR"/*.log; do
        if [ -f "$log_file" ]; then
            echo "  - $(basename "$log_file"): $(wc -l < "$log_file") lines"
        fi
    done
}

# Function to show logs
show_logs() {
    local service_name=$1
    local log_file="$LOG_DIR/$service_name.log"
    
    if [ -f "$log_file" ]; then
        print_status "Showing logs for $service_name:"
        echo "================================================"
        tail -f "$log_file"
    else
        print_error "No log file found for $service_name"
    fi
}

# Function to clean up
cleanup() {
    print_status "Cleaning up..."
    stop_all
    rm -rf "$PID_DIR"
    print_success "Cleanup complete"
}

# Main script logic
case "${1:-start}" in
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
    restart)
        stop_all
        sleep 2
        start_all
        ;;
    status)
        show_status
        ;;
    logs)
        if [ -n "$2" ]; then
            show_logs "$2"
        else
            print_error "Please specify a service name (go-api, go-worker, python-worker, react-frontend)"
            exit 1
        fi
        ;;
    cleanup)
        cleanup
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|cleanup}"
        echo ""
        echo "Commands:"
        echo "  start   - Start all services (default)"
        echo "  stop    - Stop all services"
        echo "  restart - Restart all services"
        echo "  status  - Show status of all services"
        echo "  logs    - Show logs for a specific service"
        echo "  cleanup - Stop all services and clean up"
        echo ""
        echo "Examples:"
        echo "  $0 start"
        echo "  $0 logs go-api"
        echo "  $0 status"
        exit 1
        ;;
esac



