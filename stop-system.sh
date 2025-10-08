#!/bin/bash

# Article Extraction System - Stop Script
# Stops all running services

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to kill processes by port
kill_by_port() {
    local port=$1
    local service_name=$2
    
    local pids=$(netstat -tlnp 2>/dev/null | grep ":$port " | awk '{print $7}' | cut -d'/' -f1 | sort -u)
    
    if [ -n "$pids" ]; then
        print_status "Stopping $service_name (port $port)..."
        for pid in $pids; do
            if [ "$pid" != "-" ] && [ -n "$pid" ]; then
                kill "$pid" 2>/dev/null || true
            fi
        done
        print_success "$service_name stopped"
    else
        print_status "$service_name was not running"
    fi
}

# Function to kill processes by name
kill_by_name() {
    local name=$1
    local pids=$(pgrep -f "$name" 2>/dev/null || true)
    
    if [ -n "$pids" ]; then
        print_status "Stopping $name processes..."
        echo "$pids" | xargs kill 2>/dev/null || true
        print_success "$name stopped"
    else
        print_status "$name was not running"
    fi
}

print_status "Stopping Article Extraction System..."
echo "================================================"

# Stop services by port
kill_by_port "8080" "Go API"
kill_by_port "8081" "Python AI Worker"
kill_by_port "5173" "React Frontend"

# Stop Go worker (no specific port)
kill_by_name "go run cmd/worker/main.go"

# Clean up any remaining processes
kill_by_name "article_extraction"

echo "================================================"
print_success "All services stopped"

# Check if any services are still running
remaining=$(netstat -tlnp 2>/dev/null | grep -E ":(8080|8081|5173) " || true)
if [ -n "$remaining" ]; then
    print_error "Some services may still be running:"
    echo "$remaining"
else
    print_success "All services successfully stopped"
fi



