#!/bin/bash

# Deploy script for TMS application
# Creates backup and pulls latest changes from git

set -e  # Exit on any error

# Configuration - can be overridden with environment variables
PROJECT_DIR="${TMS_PROJECT_DIR:-$HOME/tms}"
BACKUP_DIR="${TMS_BACKUP_DIR:-$HOME}"

# Auto-detect if we're running from within the project directory
if [[ "$(basename "$PWD")" == "tms" ]] && [[ -f "app.py" ]]; then
    PROJECT_DIR="$PWD"
    echo -e "${BLUE}ℹ️  Auto-detected project directory: $PROJECT_DIR${NC}"
fi
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

# Step 1: Create backup directory if it doesn't exist
echo -e "${YELLOW}📁 Ensuring backup directory exists...${NC}"
if [ ! -d "$BACKUP_DIR" ]; then
    mkdir -p "$BACKUP_DIR"
    echo -e "${GREEN}✅ Created backup directory: $BACKUP_DIR${NC}"
else
    echo -e "${BLUE}ℹ️  Using existing backup directory: $BACKUP_DIR${NC}"
fi

# Step 2: Create new backup
echo -e "${YELLOW}📦 Creating backup...${NC}"
cd "$(dirname "$BACKUP_DIR")"

if cp -r "$PROJECT_DIR" "$BACKUP_DIR/$BACKUP_NAME"; then
    echo -e "${GREEN}✅ Backup created successfully: $BACKUP_DIR/$BACKUP_NAME${NC}"
    echo "Backup size: $(du -sh "$BACKUP_DIR/$BACKUP_NAME" | cut -f1)"
    
    # Step 3: Remove old backup (keep only the newest one)
    echo -e "${YELLOW}🧹 Removing old backups...${NC}"
    OLD_BACKUPS=$(ls -1t "$BACKUP_DIR" | grep "tms_backup_" | tail -n +2)
    
    if [ -n "$OLD_BACKUPS" ]; then
        echo "Removing old backups:"
        while IFS= read -r old_backup; do
            echo "  - $old_backup"
            rm -rf "$BACKUP_DIR/$old_backup"
        done <<< "$OLD_BACKUPS"
        echo -e "${GREEN}✅ Old backups removed${NC}"
    else
        echo -e "${BLUE}ℹ️  No old backups to remove${NC}"
    fi
else
    echo -e "${RED}❌ Error: Failed to create backup!${NC}"
    exit 1
fi

# Step 4: Navigate to project directory
echo -e "${YELLOW}📁 Navigating to project directory...${NC}"
cd "$PROJECT_DIR"

# Step 5: Check git status before pulling
echo -e "${YELLOW}🔍 Checking git status...${NC}"
if ! git status > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Not a git repository or git not available!${NC}"
    echo "Rolling back..."
    cd "$(dirname "$BACKUP_DIR")"
    rm -rf "$PROJECT_DIR"
    # Restore from the latest backup
    LATEST_BACKUP=$(ls -1t "$BACKUP_DIR" | grep "tms_backup_" | head -n 1)
    if [ -n "$LATEST_BACKUP" ]; then
        cp -r "$BACKUP_DIR/$LATEST_BACKUP" "$PROJECT_DIR"
        echo -e "${GREEN}✅ Rollback completed using: $LATEST_BACKUP${NC}"
    else
        echo -e "${RED}❌ No backup found for rollback!${NC}"
    fi
    exit 1
fi

# Show current branch and status
echo "Current branch: $(git branch --show-current)"
echo "Git status:"
git status --porcelain

# Step 6: Stash any local changes
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${YELLOW}💾 Stashing local changes...${NC}"
    git stash push -m "Auto-stash before deployment $DATE"
fi

# Step 7: Pull latest changes
echo -e "${YELLOW}⬇️  Pulling latest changes from git...${NC}"
if git pull origin main; then
    echo -e "${GREEN}✅ Git pull completed successfully!${NC}"
else
    echo -e "${RED}❌ Error: Git pull failed!${NC}"
    echo "Rolling back..."
    cd "$(dirname "$BACKUP_DIR")"
    rm -rf "$PROJECT_DIR"
    # Restore from the latest backup
    LATEST_BACKUP=$(ls -1t "$BACKUP_DIR" | grep "tms_backup_" | head -n 1)
    if [ -n "$LATEST_BACKUP" ]; then
        cp -r "$BACKUP_DIR/$LATEST_BACKUP" "$PROJECT_DIR"
        echo -e "${GREEN}✅ Rollback completed using: $LATEST_BACKUP${NC}"
    else
        echo -e "${RED}❌ No backup found for rollback!${NC}"
    fi
    exit 1
fi

# Step 8: Install/update dependencies if requirements.txt exists
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

# Step 9: Success message
echo ""
echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo "Backup location: $BACKUP_DIR/$BACKUP_NAME"
echo "To rollback, run: ./rollback.sh"
echo ""
echo -e "${YELLOW}📝 Next steps:${NC}"
echo "1. Test your application"
echo "2. Reload your web app in PythonAnywhere"
echo "3. If everything works, you can delete old backups to save space"

# Create rollback command file for easy access
echo "#!/bin/bash" > rollback_$DATE.sh
echo "# Rollback to backup created on $DATE" >> rollback_$DATE.sh
echo "./rollback.sh" >> rollback_$DATE.sh
chmod +x rollback_$DATE.sh

echo "Quick rollback script created: rollback_$DATE.sh"