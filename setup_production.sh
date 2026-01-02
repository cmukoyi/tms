#!/bin/bash
# =====================================================
# Production Setup for TMS
# Domain: tms.visightsolutions.co.za
# =====================================================

set -e

echo "🚀 Setting up TMS for production..."

# 1. Create systemd service
echo "📝 Creating systemd service..."
sudo tee /etc/systemd/system/tms.service > /dev/null << 'EOF'
[Unit]
Description=TMS Flask Application
After=network.target mysql.service
Wants=mysql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/tms
Environment="PATH=/var/www/tms/venv/bin"
Environment="FLASK_ENV=production"
ExecStart=/var/www/tms/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5001 --timeout 120 app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 2. Configure Nginx
echo "🌐 Configuring Nginx..."
sudo tee /etc/nginx/sites-available/tms > /dev/null << 'EOF'
server {
    listen 80;
    server_name tms.visightsolutions.co.za;

    # Increase buffer sizes for large requests
    client_max_body_size 50M;
    client_body_buffer_size 128k;

    # Logging
    access_log /var/log/nginx/tms_access.log;
    error_log /var/log/nginx/tms_error.log;

    # Proxy to Flask app
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Static files
    location /static {
        alias /var/www/tms/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Uploads
    location /uploads {
        alias /var/www/tms/uploads;
        expires 30d;
    }
}
EOF

# 3. Enable site and disable default
echo "⚙️  Enabling TMS site..."
sudo ln -sf /etc/nginx/sites-available/tms /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# 4. Set permissions
echo "🔒 Setting permissions..."
sudo chown -R www-data:www-data /var/www/tms
sudo chmod -R 755 /var/www/tms
sudo chmod 755 /var/www/tms/uploads

# 5. Create uploads directory if it doesn't exist
mkdir -p /var/www/tms/uploads/profiles
mkdir -p /var/www/tms/uploads/company_docs
sudo chown -R www-data:www-data /var/www/tms/uploads

# 6. Test Nginx configuration
echo "🧪 Testing Nginx configuration..."
sudo nginx -t

# 7. Restart services
echo "🔄 Restarting services..."
sudo systemctl daemon-reload
sudo systemctl enable tms
sudo systemctl restart tms
sudo systemctl restart nginx

# 8. Check status
echo ""
echo "✅ Production setup complete!"
echo ""
echo "=================================="
echo "Service Status:"
echo "=================================="
sudo systemctl status tms --no-pager -l | head -15
echo ""
sudo systemctl status nginx --no-pager -l | head -10
echo ""
echo "=================================="
echo "🌐 Your app should now be accessible at:"
echo "   http://tms.visightsolutions.co.za"
echo ""
echo "📊 Useful commands:"
echo "   sudo systemctl status tms"
echo "   sudo systemctl restart tms"
echo "   sudo journalctl -u tms -f"
echo "   sudo tail -f /var/log/nginx/tms_error.log"
echo "=================================="
