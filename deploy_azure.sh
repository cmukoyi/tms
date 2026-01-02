#!/bin/bash
# =====================================================
# Azure VM Deployment Script for TMS
# Run this script on your Azure VM
# =====================================================

set -e  # Exit on error

echo "🚀 Starting TMS Deployment on Azure VM..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_DIR="/var/www/tms"
DB_NAME="tms_db"
DB_USER="tms_user"
DB_PASS="YourSecurePassword123!"  # CHANGE THIS!

echo -e "${YELLOW}📋 Step 1: Installing system dependencies...${NC}"
sudo apt update
sudo apt install -y python3-pip python3-venv mysql-server nginx

echo -e "${YELLOW}📋 Step 2: Setting up virtual environment...${NC}"
cd $APP_DIR
python3 -m venv venv
source venv/bin/activate

echo -e "${YELLOW}📋 Step 3: Installing Python packages...${NC}"
pip install --upgrade pip
pip install python-dotenv
pip install -r requirements.txt

echo -e "${YELLOW}📋 Step 4: Running database scripts...${NC}"
cd $APP_DIR/database_scripts

for script in *.sql; do 
    echo "  ▶️  Running $script..."
    sudo mysql < "$script"
done

echo -e "${GREEN}✅ Database setup complete!${NC}"

echo -e "${YELLOW}📋 Step 5: Creating .env file...${NC}"
cat > $APP_DIR/.env << EOL
# Flask Configuration
FLASK_APP=app.py
FLASK_ENV=production
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')

# Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASS

# MySQL Connection String
DATABASE_URL=mysql+pymysql://$DB_USER:$DB_PASS@localhost:3306/$DB_NAME

# OpenAI (Optional - for chatbot)
OPENAI_API_KEY=your-api-key-here

# Server Configuration
HOST=0.0.0.0
PORT=5001
EOL

echo -e "${GREEN}✅ .env file created!${NC}"

echo -e "${YELLOW}📋 Step 6: Setting permissions...${NC}"
sudo chown -R www-data:www-data $APP_DIR
sudo chmod -R 755 $APP_DIR

echo -e "${YELLOW}📋 Step 7: Creating systemd service...${NC}"
sudo tee /etc/systemd/system/tms.service > /dev/null << EOL
[Unit]
Description=TMS Flask Application
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
ExecStart=$APP_DIR/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:5001 app:app

[Install]
WantedBy=multi-user.target
EOL

echo -e "${YELLOW}📋 Step 8: Configuring Nginx...${NC}"
sudo tee /etc/nginx/sites-available/tms > /dev/null << 'EOL'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /var/www/tms/static;
        expires 30d;
    }

    location /uploads {
        alias /var/www/tms/uploads;
        expires 30d;
    }
}
EOL

sudo ln -sf /etc/nginx/sites-available/tms /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

echo -e "${YELLOW}📋 Step 9: Starting services...${NC}"
sudo systemctl daemon-reload
sudo systemctl enable tms
sudo systemctl start tms
sudo systemctl restart nginx

echo -e "${GREEN}✅ TMS Deployment Complete!${NC}"
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}🎉 Your application is now running!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "📱 Access your app at: http://YOUR_VM_IP"
echo ""
echo "🔐 Default Login:"
echo "   Username: admin"
echo "   Password: Admin@2026"
echo "   ⚠️  CHANGE PASSWORD IMMEDIATELY!"
echo ""
echo "🔧 Useful Commands:"
echo "   Check status:  sudo systemctl status tms"
echo "   View logs:     sudo journalctl -u tms -f"
echo "   Restart app:   sudo systemctl restart tms"
echo "   Restart nginx: sudo systemctl restart nginx"
echo ""
echo -e "${YELLOW}⚠️  Remember to:${NC}"
echo "   1. Change database password in .env"
echo "   2. Change admin password after first login"
echo "   3. Configure firewall to allow port 80"
echo "   4. Set up SSL certificate (Let's Encrypt)"
echo ""
