#!/bin/bash
# Simple monitoring dashboard for Kindle Sync service

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    if [ "$status" = "OK" ]; then
        echo -e "${GREEN}✓${NC} $message"
    elif [ "$status" = "WARNING" ]; then
        echo -e "${YELLOW}⚠${NC} $message"
    elif [ "$status" = "ERROR" ]; then
        echo -e "${RED}✗${NC} $message"
    else
        echo -e "${BLUE}ℹ${NC} $message"
    fi
}

# Function to get service status
get_service_status() {
    if systemctl is-active --quiet kindle-sync.service; then
        echo "running"
    else
        echo "stopped"
    fi
}

# Function to get service uptime
get_service_uptime() {
    systemctl show kindle-sync.service --property=ActiveEnterTimestamp --value | xargs -I {} date -d {} +%s 2>/dev/null || echo "0"
}

# Function to format uptime
format_uptime() {
    local start_time=$1
    local current_time=$(date +%s)
    local uptime=$((current_time - start_time))

    if [ $uptime -lt 60 ]; then
        echo "${uptime}s"
    elif [ $uptime -lt 3600 ]; then
        echo "$((uptime / 60))m $((uptime % 60))s"
    else
        echo "$((uptime / 3600))h $(((uptime % 3600) / 60))m"
    fi
}

# Function to get file count
get_file_count() {
    local sync_dir="/home/hayden/obsidian-vault/Kindle Sync"
    if [ -d "$sync_dir" ]; then
        find "$sync_dir" -type f | wc -l
    else
        echo "0"
    fi
}

# Function to get recent activity
get_recent_activity() {
    journalctl -u kindle-sync.service --no-pager -n 5 --since "5 minutes ago" | grep -E "(INFO|ERROR|WARNING)" | tail -3
}

# Main dashboard
clear
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    KINDLE SYNC DASHBOARD                    ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo

# Service Status
echo -e "${BLUE}📊 SERVICE STATUS${NC}"
echo "────────────────────────────────────────────────────────────────"
service_status=$(get_service_status)
if [ "$service_status" = "running" ]; then
    print_status "OK" "Kindle Sync Service is running"
    uptime_start=$(get_service_uptime)
    uptime_formatted=$(format_uptime $uptime_start)
    print_status "INFO" "Uptime: $uptime_formatted"
else
    print_status "ERROR" "Kindle Sync Service is stopped"
fi
echo

# File Statistics
echo -e "${BLUE}📁 FILE STATISTICS${NC}"
echo "────────────────────────────────────────────────────────────────"
file_count=$(get_file_count)
print_status "INFO" "Files in sync folder: $file_count"

sync_dir="/home/hayden/obsidian-vault/Kindle Sync"
if [ -d "$sync_dir" ]; then
    md_count=$(find "$sync_dir" -name "*.md" | wc -l)
    pdf_count=$(find "$sync_dir" -name "*.pdf" | wc -l)
    print_status "INFO" "Markdown files: $md_count"
    print_status "INFO" "PDF files: $pdf_count"
fi
echo

# System Resources
echo -e "${BLUE}💻 SYSTEM RESOURCES${NC}"
echo "────────────────────────────────────────────────────────────────"
cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
memory_usage=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
disk_usage=$(df -h / | awk 'NR==2{print $5}' | cut -d'%' -f1)

print_status "INFO" "CPU Usage: ${cpu_usage}%"
print_status "INFO" "Memory Usage: ${memory_usage}%"
print_status "INFO" "Disk Usage: ${disk_usage}%"
echo

# Recent Activity
echo -e "${BLUE}📋 RECENT ACTIVITY${NC}"
echo "────────────────────────────────────────────────────────────────"
recent_activity=$(get_recent_activity)
if [ -n "$recent_activity" ]; then
    echo "$recent_activity"
else
    print_status "INFO" "No recent activity in the last 5 minutes"
fi
echo

# Quick Actions
echo -e "${BLUE}🔧 QUICK ACTIONS${NC}"
echo "────────────────────────────────────────────────────────────────"
echo "1. View live logs: sudo journalctl -u kindle-sync.service -f"
echo "2. Restart service: sudo systemctl restart kindle-sync.service"
echo "3. Check service status: sudo systemctl status kindle-sync.service"
echo "4. View sync folder: ls -la '/home/hayden/obsidian-vault/Kindle Sync/'"
echo

# Service Health
echo -e "${BLUE}🏥 SERVICE HEALTH${NC}"
echo "────────────────────────────────────────────────────────────────"
if [ "$service_status" = "running" ]; then
    # Check for errors in recent logs
    error_count=$(journalctl -u kindle-sync.service --no-pager -n 50 | grep -c "ERROR" || echo "0")
    if [ "$error_count" -gt 0 ]; then
        print_status "WARNING" "Found $error_count errors in recent logs"
    else
        print_status "OK" "No recent errors found"
    fi

    # Check if service is responding
    if pgrep -f "simple_sync.py" > /dev/null; then
        print_status "OK" "Service process is active"
    else
        print_status "ERROR" "Service process not found"
    fi
else
    print_status "ERROR" "Service is not running"
fi
echo

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Dashboard updated: $(date '+%Y-%m-%d %H:%M:%S')                    ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
