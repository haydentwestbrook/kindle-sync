#!/bin/bash
# Deployment monitoring script

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Kindle Sync Deployment Monitor ===${NC}"
echo -e "${CYAN}Monitoring deployment progress...${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop monitoring${NC}"
echo ""

# Function to show log tail with colors
monitor_logs() {
    if [ -f "deployment.log" ]; then
        echo -e "${GREEN}=== Deployment Log (Last 20 lines) ===${NC}"
        tail -20 deployment.log | while read line; do
            if [[ $line == *"[ERROR]"* ]]; then
                echo -e "${RED}$line${NC}"
            elif [[ $line == *"[WARN]"* ]]; then
                echo -e "${YELLOW}$line${NC}"
            elif [[ $line == *"[SUCCESS]"* ]]; then
                echo -e "${GREEN}$line${NC}"
            elif [[ $line == *"[STEP]"* ]]; then
                echo -e "${BLUE}$line${NC}"
            else
                echo "$line"
            fi
        done
        echo ""
    else
        echo -e "${YELLOW}No deployment log found yet...${NC}"
    fi
}

# Function to check deployment status
check_status() {
    local pi_ip="$1"
    if [ -n "$pi_ip" ]; then
        echo -e "${CYAN}=== Pi Connectivity Check ===${NC}"
        if ping -c 1 -W 2 "$pi_ip" >/dev/null 2>&1; then
            echo -e "${GREEN}✓ Pi is reachable at $pi_ip${NC}"
        else
            echo -e "${RED}✗ Pi is not reachable at $pi_ip${NC}"
        fi
        echo ""
    fi
}

# Function to show system resources
show_resources() {
    echo -e "${CYAN}=== System Resources ===${NC}"
    echo -e "CPU Usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
    echo -e "Memory Usage: $(free | grep Mem | awk '{printf("%.1f%%", $3/$2 * 100.0)}')"
    echo -e "Disk Usage: $(df -h . | awk 'NR==2{printf "%s", $5}')"
    echo ""
}

# Main monitoring loop
main() {
    local pi_ip="$1"
    
    while true; do
        clear
        echo -e "${BLUE}=== Kindle Sync Deployment Monitor ===${NC}"
        echo -e "${CYAN}Time: $(date)${NC}"
        echo ""
        
        check_status "$pi_ip"
        show_resources
        monitor_logs
        
        echo -e "${YELLOW}Refreshing in 5 seconds... (Ctrl+C to stop)${NC}"
        sleep 5
    done
}

# Show usage if no arguments
if [ $# -eq 0 ]; then
    echo "Usage: $0 [pi-ip-address]"
    echo "Example: $0 192.168.0.12"
    echo ""
    echo "This script monitors the deployment progress in real-time."
    echo "Run this in a separate terminal while deployment is running."
    exit 1
fi

# Run main function
main "$1"
