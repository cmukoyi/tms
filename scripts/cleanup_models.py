#!/usr/bin/env python3
"""
Script to clean up duplicate model definitions in models/__init__.py
"""

import os
import re
from pathlib import Path

def cleanup_models_file():
    """Remove duplicate model definitions from models/__init__.py"""
    
    models_file = Path('models/__init__.py')
    
    if not models_file.exists():
        print("❌ models/__init__.py not found!")
        return False
    
    print("🔧 Reading models/__init__.py...")
    
    with open(models_file, 'r') as f:
        content = f.read()
    
    # Find all class definitions
    class_pattern = r'^class\s+(\w+)\s*\([^)]+\):'
    classes = re.findall(class_pattern, content, re.MULTILINE)
    
    print(f"📋 Found {len(classes)} model classes:")
    for class_name in classes:
        count = content.count(f'class {class_name}(')
        if count > 1:
            print(f"   ⚠️  {class_name} - DUPLICATE ({count} times)")
        else:
            print(f"   ✅ {class_name}")
    
    # Check for specific problematic duplicates
    duplicates_found = []
    
    problematic_classes = ['CompanyModule', 'ModuleDefinition', 'MonthlyBill', 'Bill', 'BillLineItem', 'BillItem']
    
    for class_name in problematic_classes:
        count = content.count(f'class {class_name}(')
        if count > 1:
            duplicates_found.append(class_name)
            print(f"🚨 Found {count} definitions of {class_name}")
    
    if duplicates_found:
        print(f"\n❌ Found duplicate classes: {', '.join(duplicates_found)}")
        print("\n🔧 MANUAL FIX REQUIRED:")
        print("1. Open models/__init__.py")
        print("2. Search for duplicate class definitions")
        print("3. Remove all but ONE definition of each class")
        print("4. Make sure the remaining definitions match your database structure")
        
        return False
    else:
        print("\n✅ No duplicate classes found!")
        return True

def backup_models_file():
    """Create a backup of the models file"""
    models_file = Path('models/__init__.py')
    backup_file = Path('models/__init__.py.backup')
    
    if models_file.exists():
        import shutil
        shutil.copy2(models_file, backup_file)
        print(f"✅ Backup created: {backup_file}")
        return True
    
    return False

def main():
    print("🧹 Cleaning up models file...")
    
    # Create backup first
    if backup_models_file():
        print("✅ Backup created")
    
    # Check for duplicates
    if not cleanup_models_file():
        print("\n📝 STEPS TO FIX:")
        print("1. Open models/__init__.py in your editor")
        print("2. Search for 'class CompanyModule(' - remove duplicates")
        print("3. Search for 'class ModuleDefinition(' - remove duplicates") 
        print("4. Search for 'class MonthlyBill(' or 'class Bill(' - keep only MonthlyBill")
        print("5. Search for 'class BillLineItem(' or 'class BillItem(' - keep only BillLineItem")
        print("6. Add at the end: Bill = MonthlyBill and BillItem = BillLineItem")
        print("\n🔄 Then run: python app.py")
    else:
        print("✅ Models file looks clean!")

if __name__ == '__main__':
    main()