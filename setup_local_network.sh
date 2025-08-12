#!/bin/bash

# Local Network Setup Script for Stripe Dashboard
# This script helps configure the app for local network sharing

echo "🌐 Stripe Dashboard - Local Network Setup"
echo "========================================"

# Get network information
LOCAL_IP=$(hostname -I | awk '{print $1}')
PORT=${APP_PORT:-8081}

echo ""
echo "📍 Network Information:"
echo "   • Your IP Address: $LOCAL_IP"
echo "   • App Port: $PORT"
echo "   • Network URLs:"
echo "     - Local: http://localhost:$PORT"
echo "     - Network: http://$LOCAL_IP:$PORT"
echo ""

# Check if port is available
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port $PORT is already in use!"
    echo "   Run: sudo lsof -i :$PORT to see what's using it"
    echo "   Or change APP_PORT in .env file"
    echo ""
else
    echo "✅ Port $PORT is available"
    echo ""
fi

# Check firewall status (if ufw is installed)
if command -v ufw >/dev/null 2>&1; then
    echo "🔥 Firewall Check:"
    if ufw status | grep -q "Status: active"; then
        echo "   • UFW is active"
        if ufw status | grep -q "$PORT"; then
            echo "   • Port $PORT is already allowed"
        else
            echo "   • Port $PORT is NOT allowed in firewall"
            echo "   • To fix, run: sudo ufw allow $PORT"
        fi
    else
        echo "   • UFW firewall is inactive"
    fi
    echo ""
fi

# Create a test HTML file
cat > test_network_access.html << EOF
<!DOCTYPE html>
<html>
<head>
    <title>Network Access Test</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f0f8ff; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }
        .success { background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 15px; border-radius: 5px; }
        .info { background: #d1ecf1; border: 1px solid #bee5eb; color: #0c5460; padding: 15px; border-radius: 5px; margin: 15px 0; }
        a { display: inline-block; margin: 10px 5px; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🌐 Network Access Test</h1>
        
        <div class="success">
            <h3>✅ Connection Successful!</h3>
            <p>You can access the Stripe Dashboard from this device</p>
        </div>
        
        <div class="info">
            <h3>📱 Access URLs:</h3>
            <p><strong>Local:</strong> <a href="http://localhost:$PORT">http://localhost:$PORT</a></p>
            <p><strong>Network:</strong> <a href="http://$LOCAL_IP:$PORT">http://$LOCAL_IP:$PORT</a></p>
        </div>
        
        <div class="info">
            <h3>📋 Share with Other Devices:</h3>
            <p>Give this URL to other devices on your network:</p>
            <p><strong><code>http://$LOCAL_IP:$PORT</code></strong></p>
        </div>
        
        <a href="http://$LOCAL_IP:$PORT">🚀 Open Stripe Dashboard</a>
    </div>
</body>
</html>
EOF

echo "📝 Created test file: test_network_access.html"
echo ""

echo "🚀 Next Steps:"
echo "1. Start the app: python run.py"
echo "2. Test locally: http://localhost:$PORT"
echo "3. Share network URL: http://$LOCAL_IP:$PORT"
echo ""

echo "📱 For Mobile/Other Devices:"
echo "• Make sure they're on the same WiFi network"
echo "• Use URL: http://$LOCAL_IP:$PORT"
echo "• If it doesn't work, check firewall settings"
echo ""

echo "🔧 Troubleshooting:"
echo "• If port is blocked: sudo ufw allow $PORT"
echo "• If still issues: ./network_debug.sh"
echo "• Check router firewall settings if needed"
echo ""

# Make the script executable
chmod +x "$0"
