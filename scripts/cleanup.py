#!/usr/bin/env python3
"""
Script to delete all .backup files in TMS folder
Usage: python script.py
"""

import os
import glob
from pathlib import Path

def find_and_delete_backup_files():
    """Find and delete all .backup files in current directory and subdirectories"""
    
    # Get current directory (should be TMS folder)
    current_dir = Path.cwd()
    print(f"🔍 Searching for .backup files in: {current_dir}")
    print("=" * 50)
    
    # Find all .backup files recursively
    backup_files = []
    
    # Pattern 1: Files ending with .backup
    backup_files.extend(glob.glob("**/*.backup", recursive=True))
    
    # Pattern 2: Files with .backup in the middle (like file.backup.html)
    backup_files.extend(glob.glob("**/*.backup.*", recursive=True))
    
    # Remove duplicates
    backup_files = list(set(backup_files))
    
    if not backup_files:
        print("✅ No .backup files found!")
        return
    
    print(f"Found {len(backup_files)} backup files:")
    print("-" * 30)
    
    # List all backup files
    for i, backup_file in enumerate(backup_files, 1):
        file_size = os.path.getsize(backup_file) if os.path.exists(backup_file) else 0
        size_mb = file_size / (1024 * 1024)
        print(f"{i:2d}. {backup_file} ({size_mb:.2f} MB)")
    
    # Calculate total size
    total_size = sum(os.path.getsize(f) for f in backup_files if os.path.exists(f))
    total_mb = total_size / (1024 * 1024)
    
    print("-" * 30)
    print(f"📊 Total size: {total_mb:.2f} MB")
    print()
    
    # Ask for confirmation
    response = input("🗑️  Delete all these backup files? (y/N): ").strip().lower()
    
    if response in ['y', 'yes']:
        deleted_count = 0
        failed_count = 0
        
        print("\n🚀 Deleting backup files...")
        print("-" * 30)
        
        for backup_file in backup_files:
            try:
                if os.path.exists(backup_file):
                    os.remove(backup_file)
                    print(f"✅ Deleted: {backup_file}")
                    deleted_count += 1
                else:
                    print(f"⚠️  Not found: {backup_file}")
                    failed_count += 1
            except Exception as e:
                print(f"❌ Failed to delete {backup_file}: {e}")
                failed_count += 1
        
        print("-" * 30)
        print(f"🎉 Cleanup complete!")
        print(f"   ✅ Deleted: {deleted_count} files")
        if failed_count > 0:
            print(f"   ❌ Failed: {failed_count} files")
        print(f"   💾 Space freed: {total_mb:.2f} MB")
        
    else:
        print("❌ Operation cancelled. No files were deleted.")

def find_backup_directories():
    """Also find and optionally delete backup directories"""
    print("\n🔍 Searching for backup directories...")
    print("=" * 50)
    
    backup_dirs = []
    
    # Find directories with 'backup' in name
    for root, dirs, files in os.walk('.'):
        for dir_name in dirs:
            if 'backup' in dir_name.lower():
                dir_path = os.path.join(root, dir_name)
                backup_dirs.append(dir_path)
    
    if not backup_dirs:
        print("✅ No backup directories found!")
        return
    
    print(f"Found {len(backup_dirs)} backup directories:")
    print("-" * 30)
    
    for i, backup_dir in enumerate(backup_dirs, 1):
        # Calculate directory size
        dir_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(backup_dir):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        dir_size += os.path.getsize(filepath)
        except:
            dir_size = 0
        
        size_mb = dir_size / (1024 * 1024)
        print(f"{i:2d}. {backup_dir} ({size_mb:.2f} MB)")
    
    response = input("\n🗑️  Delete backup directories too? (y/N): ").strip().lower()
    
    if response in ['y', 'yes']:
        import shutil
        deleted_dirs = 0
        
        for backup_dir in backup_dirs:
            try:
                shutil.rmtree(backup_dir)
                print(f"✅ Deleted directory: {backup_dir}")
                deleted_dirs += 1
            except Exception as e:
                print(f"❌ Failed to delete {backup_dir}: {e}")
        
        print(f"🎉 Deleted {deleted_dirs} backup directories!")

if __name__ == "__main__":
    print("🧹 TMS Backup Files Cleanup Script")
    print("=" * 50)
    
    try:
        # Clean backup files
        find_and_delete_backup_files()
        
        # Clean backup directories
        find_backup_directories()
        
        print("\n✨ Cleanup script completed!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Script interrupted by user.")
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")