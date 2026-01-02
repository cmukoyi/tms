# Azure VM Deployment Guide - TMS

Complete step-by-step guide to deploy TMS on Azure Ubuntu VM.

## ⚠️ Python Version Issue

Your VM has **Python 3.6.9** which is too old. You need **Python 3.8+** (preferably 3.9+).

### Option 1: Upgrade Python (Recommended)

```bash
# Install Python 3.9
sudo apt update
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.9 python3.9-venv python3.9-dev

# Use Python 3.9 for the project
cd /var/www/tms
python3.9 -m venv venv
source venv/bin/activate
```

### Option 2: Use Compatibility Mode (Current Code Fixed)

The code has been updated to work with Python 3.6, but it's still recommended to upgrade.

## Quick Deployment

### 1. Upload Files to VM

From your local machine:

```bash
# Upload entire project
scp -r /Users/carl/Documents/VSS-Projects/tms adminTelematics@YOUR_VM_IP:/var/www/

# Or if already on VM, pull from git
ssh adminTelematics@YOUR_VM_IP
cd /var/www/tms
git pull origin main
```

### 2. Run Deployment Script

```bash
cd /var/www/tms
chmod +x deploy_azure.sh
sudo ./deploy_azure.sh
```

That's it! The script handles everything.

## Manual Deployment (If Script Fails)

### Step 1: Install Python Packages

```bash
cd /var/www/tms
source venv/bin/activate
pip install --upgrade pip
pip install python-dotenv
pip install -r requirements.txt
```

### Step 2: Fix Python 3.6 Compatibility (If Needed)

```bash
pip install pytz backports.zoneinfo
```

### Step 3: Create .env File

```bash
nano .env
```

Paste this:

```bash
# Flask Configuration
FLASK_APP=app.py
FLASK_ENV=production
SECRET_KEY=change-this-to-random-secret-key

# Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_NAME=tms_db
DB_USER=tms_user
DB_PASSWORD=YourSecurePassword123!

# MySQL Connection String
DATABASE_URL=mysql+pymysql://tms_user:YourSecurePassword123!@localhost:3306/tms_db

# OpenAI (Optional)
OPENAI_API_KEY=

# Server
HOST=0.0.0.0
PORT=5001
```

Save: `Ctrl+X`, `Y`, `Enter`

### Step 4: Run Database Scripts

```bash
cd /var/www/tms/database_scripts

# Run each script in order
sudo mysql < 01_create_database.sql
sudo mysql < 02_create_user.sql
sudo mysql < 03_create_core_tables.sql
sudo mysql < 04_create_tender_tables.sql
sudo mysql < 05_create_module_billing_tables.sql
sudo mysql < 06_create_workflow_permissions_tables.sql
sudo mysql < 07_create_notification_accounting_tables.sql
sudo mysql < 08_insert_initial_data.sql
sudo mysql < 09_create_admin_user.sql
```

### Step 5: Verify Database

```bash
sudo mysql -u tms_user -p tms_db
# Enter password: YourSecurePassword123!

# Inside MySQL:
SHOW TABLES;
SELECT * FROM users WHERE username='admin';
EXIT;
```

### Step 6: Test the App

```bash
cd /var/www/tms
source venv/bin/activate
python3 app.py
```

Visit: `http://YOUR_VM_IP:5001`

### Step 7: Set Up Production (Gunicorn + Nginx)

#### Create systemd Service

```bash
sudo nano /etc/systemd/system/tms.service
```

Paste:

```ini
[Unit]
Description=TMS Flask Application
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/tms
Environment="PATH=/var/www/tms/venv/bin"
ExecStart=/var/www/tms/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:5001 app:app

[Install]
WantedBy=multi-user.target
```

Save and enable:

```bash
sudo systemctl daemon-reload
sudo systemctl enable tms
sudo systemctl start tms
sudo systemctl status tms
```

#### Configure Nginx

```bash
sudo nano /etc/nginx/sites-available/tms
```

Paste:

```nginx
server {
    listen 80;
    server_name YOUR_DOMAIN_OR_IP;

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
```

Enable and restart:

```bash
sudo ln -s /etc/nginx/sites-available/tms /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

### Step 8: Set Permissions

```bash
sudo chown -R www-data:www-data /var/www/tms
sudo chmod -R 755 /var/www/tms
sudo chmod 755 /var/www/tms/uploads
```

## Troubleshooting

### "No module named 'zoneinfo'"

```bash
pip install backports.zoneinfo pytz
```

Or upgrade Python to 3.9+

### "No module named 'dotenv'"

```bash
pip install python-dotenv
```

### Database Connection Error

Check `.env` file has correct credentials:
```bash
cat /var/www/tms/.env
```

Test connection:
```bash
mysql -u tms_user -p tms_db
```

### App Won't Start

Check logs:
```bash
sudo journalctl -u tms -f
```

### Nginx Error

Check logs:
```bash
sudo tail -f /var/log/nginx/error.log
```

Test configuration:
```bash
sudo nginx -t
```

## Useful Commands

```bash
# Restart app
sudo systemctl restart tms

# View app logs
sudo journalctl -u tms -f

# Restart Nginx
sudo systemctl restart nginx

# Check status
sudo systemctl status tms
sudo systemctl status nginx

# Database backup
mysqldump -u tms_user -p tms_db > backup_$(date +%Y%m%d).sql

# Update code from git
cd /var/www/tms
git pull origin main
sudo systemctl restart tms
```

## Security Checklist

- [ ] Change database password in .env
- [ ] Change admin password after first login
- [ ] Generate new SECRET_KEY in .env
- [ ] Configure firewall (allow port 80, 443, deny direct 5001)
- [ ] Set up SSL certificate (Let's Encrypt)
- [ ] Restrict MySQL remote access
- [ ] Set up regular backups
- [ ] Enable fail2ban

## Firewall Configuration

```bash
# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow SSH
sudo ufw allow 22/tcp

# Block direct app access
sudo ufw deny 5001/tcp

# Enable firewall
sudo ufw enable
```

## SSL Certificate (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
sudo systemctl reload nginx
```

## First Login

- **URL:** http://YOUR_VM_IP
- **Username:** admin
- **Password:** Admin@2026

**⚠️ CRITICAL: Change password immediately!**

---

**Need Help?** Check the logs first:
```bash
sudo journalctl -u tms -f
sudo tail -f /var/log/nginx/error.log
```
