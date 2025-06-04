#!/bin/bash

# Rollback script for TMS application
# Restores from backup and replaces current tms directory

set -e  # Exit on any error

# Configuration - can be overridden with environment variables
PROJECT_DIR="${TMS_PROJECT_DIR:-$HOME/tms}"
BACKUP_BASE_DIR="${TMS_BACKUP_DIR:-$HOME}"
BACKUP_DIR="$BACKUP_BASE_DIR/tms_backups"

# Auto-detect if we're running from within the project directory
if [[ "$(basename "$PWD")" == "tms" ]] && [[ -f "app.py" ]]; then
    PROJECT_DIR="$PWD"
    echo -e "${BLUE}ℹ️  Auto-detected project directory: $PROJECT_DIR${NC}"
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to show usage
show_usage() {
    echo -e "${BLUE}Usage: $0 [backup_name]${NC}"
    echo ""
    echo "If no backup_name is provided, the latest backup will be used."
    echo ""
    echo "Examples:"
    echo "  $0                              # Use latest backup"
    echo "  $0 tms_backup_20250604_182500   # Use specific backup"
    echo ""
    echo "Available backups:"
    if [ -d "$BACKUP_DIR" ]; then
        ls -1t "$BACKUP_DIR" | grep "tms_backup_" | head -5 | awk '{print "  " $1}' || echo "  No backups found"
        BACKUP_COUNT=$(ls -1 "$BACKUP_DIR" | grep "tms_backup_" | wc -l)
        if [ "$BACKUP_COUNT" -gt 5 ]; then
            echo "  ... and $((BACKUP_COUNT - 5)) more"
        fi
    else
        echo "  Backup directory does not exist: $BACKUP_DIR"
    fi
}

# Determine which backup to use
if [ $# -eq 0 ]; then
    # No argument provided, use latest backup
    if [ ! -d "$BACKUP_DIR" ]; then
        echo -e "${RED}❌ Error: Backup directory does not exist: $BACKUP_DIR${NC}"
        echo ""
        show_usage
        exit 1
    fi
    
    BACKUP_NAME=$(ls -1t "$BACKUP_DIR" | grep "tms_backup_" | head -n 1)
    if [ -z "$BACKUP_NAME" ]; then
        echo -e "${RED}❌ Error: No backups found in $BACKUP_DIR${NC}"
        echo ""
        show_usage
        exit 1
    fi
    
    echo -e "${BLUE}ℹ️  No backup specified, using latest: $BACKUP_NAME${NC}"
else
    BACKUP_NAME="$1"
fi

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

# Remove current tms directory
echo -e "${YELLOW}🗑️  Removing current tms directory...${NC}"
if [ -d "$PROJECT_DIR" ]; then
    rm -rf "$PROJECT_DIR"
    echo -e "${GREEN}✅ Current tms directory removed${NC}"
fi

# Restore from backup
echo -e "${YELLOW}📦 Restoring from backup...${NC}"

if cp -r "$BACKUP_PATH" "$PROJECT_DIR"; then
    echo -e "${GREEN}✅ Backup restored successfully!${NC}"
else
    echo -e "${RED}❌ Error: Failed to restore from backup!${NC}"
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
echo ""
echo -e "${YELLOW}📝 Next steps:${NC}"
echo "1. Test your application"
echo "2. Reload your web app in PythonAnywhere"

# Show restore info
echo ""
echo -e "${BLUE}📊 Restore Summary:${NC}"
echo "Restored from: $BACKUP_NAME"
echo "Restore time: $(date)"
echo "Project size: $(du -sh "$PROJECT_DIR" | cut -f1)"