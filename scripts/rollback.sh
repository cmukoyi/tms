#!/bin/bash

# Rollback script for TMS application
# Restores from backup and replaces current tms directory

set -e  # Exit on any error

# Configuration
PROJECT_DIR="$HOME/tms"
BACKUP_DIR="$HOME"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to show usage
show_usage() {
    echo -e "${BLUE}Usage: $0 <backup_name>${NC}"
    echo ""
    echo "Examples:"
    echo "  $0 tms_backup_20250604_182500"
    echo "  $0 tms_backup_20250604_145230"
    echo ""
    echo "Available backups:"
    ls -la "$BACKUP_DIR" | grep "tms_backup_" | awk '{print "  " $9}' || echo "  No backups found"
}

# Check if backup name is provided
if [ $# -eq 0 ]; then
    echo -e "${RED}❌ Error: Backup name not provided!${NC}"
    echo ""
    show_usage
    exit 1
fi

BACKUP_NAME="$1"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

echo -e "${YELLOW}🔄 Starting rollback process...${NC}"
echo "Project directory: $PROJECT_DIR"
echo "Backup to restore: $BACKUP_PATH"
echo ""

# Check if backup exists
if [ ! -d "$BACKUP_PATH" ]; then
    echo -e "${RED}❌ Error: Backup directory $BACKUP_PATH does not exist!${NC}"
    echo ""
    show_usage
    exit 1
fi

# Confirm rollback
echo -e "${YELLOW}⚠️  This will replace your current tms directory with the backup.${NC}"
echo "Current tms directory will be lost!"
echo ""
read -p "Are you sure you want to proceed? (y/N): " confirm

if [[ ! $confirm =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}ℹ️  Rollback cancelled.${NC}"
    exit 0
fi

# Create emergency backup of current state
EMERGENCY_BACKUP="tms_emergency_$(date +"%Y%m%d_%H%M%S")"
echo -e "${YELLOW}💾 Creating emergency backup of current state...${NC}"

if [ -d "$PROJECT_DIR" ]; then
    cd "$BACKUP_DIR"
    if cp -r "$PROJECT_DIR" "$EMERGENCY_BACKUP"; then
        echo -e "${GREEN}✅ Emergency backup created: $EMERGENCY_BACKUP${NC}"
    else
        echo -e "${RED}❌ Error: Failed to create emergency backup!${NC}"
        exit 1
    fi
fi

# Remove current tms directory
echo -e "${YELLOW}🗑️  Removing current tms directory...${NC}"
if [ -d "$PROJECT_DIR" ]; then
    rm -rf "$PROJECT_DIR"
    echo -e "${GREEN}✅ Current tms directory removed${NC}"
fi

# Restore from backup
echo -e "${YELLOW}📦 Restoring from backup...${NC}"
cd "$BACKUP_DIR"

if cp -r "$BACKUP_PATH" "tms"; then
    echo -e "${GREEN}✅ Backup restored successfully!${NC}"
else
    echo -e "${RED}❌ Error: Failed to restore from backup!${NC}"
    echo "Attempting to restore emergency backup..."
    
    if [ -d "$EMERGENCY_BACKUP" ]; then
        cp -r "$EMERGENCY_BACKUP" "tms"
        echo -e "${YELLOW}⚠️  Emergency backup restored${NC}"
    fi
    exit 1
fi

# Set proper permissions
echo -e "${YELLOW}🔧 Setting proper permissions...${NC}"
cd "$PROJECT_DIR"
find . -type f -name "*.py" -exec chmod 644 {} \;
find . -type f -name "*.sh" -exec chmod 755 {} \;

# Check if virtual environment needs to be recreated
if [ -d "venv" ]; then
    echo -e "${YELLOW}🐍 Checking virtual environment...${NC}"
    
    # Test if venv works
    if ! ./venv/bin/python --version > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Virtual environment appears broken. Consider recreating it.${NC}"
        echo "Run these commands to recreate:"
        echo "  cd $PROJECT_DIR"
        echo "  rm -rf venv"
        echo "  python3.13 -m venv venv"
        echo "  source venv/bin/activate"
        echo "  pip install -r requirements.txt"
    else
        echo -e "${GREEN}✅ Virtual environment appears to be working${NC}"
    fi
fi

# Success message
echo ""
echo -e "${GREEN}🎉 Rollback completed successfully!${NC}"
echo "Project restored from: $BACKUP_PATH"
echo "Emergency backup created: $EMERGENCY_BACKUP"
echo ""
echo -e "${YELLOW}📝 Next steps:${NC}"
echo "1. Test your application"
echo "2. Reload your web app in PythonAnywhere"
echo "3. If everything works, you can delete the emergency backup"
echo ""
echo -e "${BLUE}ℹ️  Emergency backup location: $BACKUP_DIR/$EMERGENCY_BACKUP${NC}"

# Show restore info
echo ""
echo -e "${BLUE}📊 Restore Summary:${NC}"
echo "Restored from: $BACKUP_NAME"
echo "Restore time: $(date)"
echo "Project size: $(du -sh "$PROJECT_DIR" | cut -f1)"