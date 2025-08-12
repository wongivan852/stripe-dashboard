#!/bin/bash
# Stripe Dashboard Monitor - Prevents Hanging Issues
# This script monitors the Stripe Dashboard and restarts it if it hangs

DASHBOARD_PORT=8081
DASHBOARD_IP="192.168.0.104"
LOG_FILE="/home/user/krystal-company-apps/stripe-dashboard/monitor.log"
PYTHON_PATH="/home/user/krystal-company-apps/claude-env/bin/python"
SERVER_FILE="/home/user/krystal-company-apps/stripe-dashboard/stable_server.py"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

check_server() {
    # Check if port is listening
    if ! netstat -tlnp 2>/dev/null | grep -q ":$DASHBOARD_PORT "; then
        return 1
    fi
    
    # Check if server responds within 5 seconds
    if ! timeout 5 curl -s "http://$DASHBOARD_IP:$DASHBOARD_PORT/" > /dev/null 2>&1; then
        return 1
    fi
    
    return 0
}

restart_server() {
    log_message "🔄 Restarting Stripe Dashboard server..."
    
    # Kill existing processes
    pkill -f "stable_server.py" 2>/dev/null
    pkill -f "app_simple.py" 2>/dev/null
    pkill -f "run.py" 2>/dev/null
    pkill -f "server.py" 2>/dev/null
    
    sleep 3
    
    # Start fresh server
    cd /home/user/krystal-company-apps/stripe-dashboard
    nohup $PYTHON_PATH $SERVER_FILE > /dev/null 2>&1 &
    
    sleep 3
    
    if check_server; then
        log_message "✅ Stripe Dashboard restarted successfully on port $DASHBOARD_PORT"
        return 0
    else
        log_message "❌ Failed to restart Stripe Dashboard"
        return 1
    fi
}

main() {
    log_message "🚀 Starting Stripe Dashboard Monitor"
    
    # Initial check and start if needed
    if ! check_server; then
        log_message "⚠️  Stripe Dashboard not running, starting..."
        restart_server
    else
        log_message "✅ Stripe Dashboard is running normally"
    fi
    
    # Monitor loop
    while true; do
        sleep 30  # Check every 30 seconds
        
        if ! check_server; then
            log_message "❌ Stripe Dashboard is not responding (hanging detected)"
            restart_server
        else
            log_message "✅ Stripe Dashboard health check passed"
        fi
    done
}

# Handle interrupt signals
trap 'log_message "🛑 Monitor stopped"; exit 0' INT TERM

main
