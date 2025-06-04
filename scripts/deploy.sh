#!/bin/bash

# Deploy script for TMS application
# Creates backup and pulls latest changes from git

set -e  # Exit on any error

# Configuration
PROJECT_DIR="$HOME/tms"
BACKUP_DIR="$HOME"
DATE=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="tms_backup_$DATE"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🚀 Starting deployment process...${NC}"
echo "Project directory: $PROJECT_DIR"
echo "Backup directory: $BACKUP_DIR"
echo "Backup name: $BACKUP_NAME"
echo ""

# Check if project directory exists
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}❌ Error: Project directory $PROJECT_DIR does not exist!${NC}"
    exit 1
fi

# Step 1: Create backup
echo -e "${YELLOW}📦 Creating backup...${NC}"
cd "$BACKUP_DIR"

if cp -r "$PROJECT_DIR" "$BACKUP_NAME"; then
    echo -e "${GREEN}✅ Backup created successfully: $BACKUP_DIR/$BACKUP_NAME${NC}"
    echo "Backup size: $(du -sh "$BACKUP_NAME" | cut -f1)"
else
    echo -e "${RED}❌ Error: Failed to create backup!${NC}"
    exit 1
fi

# Step 2: Navigate to project directory
echo -e "${YELLOW}📁 Navigating to project directory...${NC}"
cd "$PROJECT_DIR"

# Step 3: Check git status before pulling
echo -e "${YELLOW}🔍 Checking git status...${NC}"
if ! git status > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Not a git repository or git not available!${NC}"
    echo "Rolling back..."
    cd "$BACKUP_DIR"
    rm -rf "$PROJECT_DIR"
    mv "$BACKUP_NAME" "tms"
    exit 1
fi

# Show current branch and status
echo "Current branch: $(git branch --show-current)"
echo "Git status:"
git status --porcelain

# Step 4: Stash any local changes
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${YELLOW}💾 Stashing local changes...${NC}"
    git stash push -m "Auto-stash before deployment $DATE"
fi

# Step 5: Pull latest changes
echo -e "${YELLOW}⬇️  Pulling latest changes from git...${NC}"
if git pull origin main; then
    echo -e "${GREEN}✅ Git pull completed successfully!${NC}"
else
    echo -e "${RED}❌ Error: Git pull failed!${NC}"
    echo "Rolling back..."
    cd "$BACKUP_DIR"
    rm -rf "$PROJECT_DIR"
    mv "$BACKUP_NAME" "tms"
    echo -e "${GREEN}✅ Rollback completed. Project restored from backup.${NC}"
    exit 1
fi

# Step 6: Install/update dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo -e "${YELLOW}📦 Installing/updating dependencies...${NC}"
    if [ -d "venv" ]; then
        source venv/bin/activate
        pip install -r requirements.txt
        echo -e "${GREEN}✅ Dependencies updated successfully!${NC}"
    else
        echo -e "${YELLOW}⚠️  No virtual environment found. Skipping dependency installation.${NC}"
    fi
fi

# Step 7: Success message
echo ""
echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo "Backup location: $BACKUP_DIR/$BACKUP_NAME"
echo "To rollback, run: ./rollback.sh $BACKUP_NAME"
echo ""
echo -e "${YELLOW}📝 Next steps:${NC}"
echo "1. Test your application"
echo "2. Reload your web app in PythonAnywhere"
echo "3. If everything works, you can delete old backups to save space"

# Create rollback command file for easy access
echo "#!/bin/bash" > rollback_$DATE.sh
echo "# Rollback to backup created on $DATE" >> rollback_$DATE.sh
echo "./rollback.sh $BACKUP_NAME" >> rollback_$DATE.sh
chmod +x rollback_$DATE.sh

echo "Quick rollback script created: rollback_$DATE.sh"