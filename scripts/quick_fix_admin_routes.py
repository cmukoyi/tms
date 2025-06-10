#!/usr/bin/env python3
"""
Quick Admin Route Fix
Specifically fixes the admin_companies function and similar issues
"""

import os
import re
from pathlib import Path

def fix_admin_routes():
    """Fix the admin routes that are missing variable definitions"""
    admin_file = Path("routes/admin.py")
    
    if not admin_file.exists():
        print("❌ routes/admin.py not found!")
        return False
    
    print("🔧 Fixing routes/admin.py...")
    
    # Read the current content
    with open(admin_file, 'r') as f:
        content = f.read()
    
    # Create backup
    backup_file = str(admin_file) + '.backup'
    with open(backup_file, 'w') as f:
        f.write(content)
    print(f"✅ Created backup: {backup_file}")
    
    # Apply specific fixes
    fixed_content = content
    fixes_applied = []
    
    # Fix 1: admin_companies function
    if "def admin_companies():" in content and "companies = Company.query.all()" not in content:
        # Find the function and add the missing query
        pattern = r"(def admin_companies\(\):.*?)(\n\s*return render_template)"
        replacement = r"\1\n    companies = Company.query.all()\2"
        if re.search(pattern, fixed_content, re.DOTALL):
            fixed_content = re.sub(pattern, replacement, fixed_content, flags=re.DOTALL)
            fixes_applied.append("Added 'companies = Company.query.all()' to admin_companies()")
    
    # Fix 2: admin_users function (if it has similar issue)
    if "def admin_users():" in content and "return render_template" in content:
        if "users = User.query.all()" not in content:
            pattern = r"(def admin_users\(\):.*?)(\n\s*return render_template)"
            replacement = r"\1\n    users = User.query.all()\2"
            if re.search(pattern, fixed_content, re.DOTALL):
                fixed_content = re.sub(pattern, replacement, fixed_content, flags=re.DOTALL)
                fixes_applied.append("Added 'users = User.query.all()' to admin_users()")
    
    # Fix 3: Any other common patterns
    # Fix functions that return templates with undefined variables
    common_fixes = [
        (r"(def \w*companies\w*\(\):.*?)(\n\s*return render_template.*companies=companies)", 
         r"\1\n    companies = Company.query.all()\2"),
        (r"(def \w*users\w*\(\):.*?)(\n\s*return render_template.*users=users)", 
         r"\1\n    users = User.query.all()\2"),
        (r"(def \w*tenders\w*\(\):.*?)(\n\s*return render_template.*tenders=tenders)", 
         r"\1\n    tenders = Tender.query.all()\2"),
        (r"(def \w*roles\w*\(\):.*?)(\n\s*return render_template.*roles=roles)", 
         r"\1\n    roles = Role.query.all()\2")
    ]
    
    for pattern, replacement in common_fixes:
        if re.search(pattern, fixed_content, re.DOTALL):
            old_content = fixed_content
            fixed_content = re.sub(pattern, replacement, fixed_content, flags=re.DOTALL)
            if fixed_content != old_content:
                fixes_applied.append(f"Fixed undefined variable pattern")
    
    # Check for missing imports
    if "from models import" not in fixed_content and any("Company.query" in fix or "User.query" in fix for fix in fixes_applied):
        # Add import at the top after other imports
        import_line = "from models import Company, User, Role, Tender\n"
        lines = fixed_content.split('\n')
        
        # Find where to insert import (after other imports)
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('from ') or line.strip().startswith('import '):
                insert_idx = i + 1
            elif line.strip() and not line.startswith('#'):
                break
        
        lines.insert(insert_idx, import_line)
        fixed_content = '\n'.join(lines)
        fixes_applied.append("Added missing model imports")
    
    # Write the fixed content
    if fixes_applied:
        with open(admin_file, 'w') as f:
            f.write(fixed_content)
        
        print(f"✅ Applied {len(fixes_applied)} fixes:")
        for fix in fixes_applied:
            print(f"   • {fix}")
        
        return True
    else:
        print("⏭️  No fixes needed or pattern not found")
        return False

def show_admin_companies_function():
    """Show the current admin_companies function"""
    admin_file = Path("routes/admin.py")
    
    if not admin_file.exists():
        print("❌ routes/admin.py not found!")
        return
    
    with open(admin_file, 'r') as f:
        content = f.read()
    
    # Find the admin_companies function
    lines = content.split('\n')
    in_function = False
    function_lines = []
    
    for i, line in enumerate(lines, 1):
        if 'def admin_companies(' in line:
            in_function = True
            function_lines.append((i, line))
        elif in_function:
            if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                # End of function
                break
            function_lines.append((i, line))
    
    if function_lines:
        print(f"\n📄 Current admin_companies() function:")
        print("="*50)
        for line_num, line_content in function_lines:
            print(f"  {line_num:3}: {line_content}")
    else:
        print("❌ admin_companies() function not found")

def main():
    """Main function"""
    print("🔧 Quick Admin Route Fix")
    print("="*30)
    
    # Show current state
    print("🔍 Current state of admin_companies() function:")
    show_admin_companies_function()
    
    # Ask to proceed
    proceed = input("\n❓ Apply fixes to routes/admin.py? (y/N): ").strip().lower()
    
    if proceed != 'y':
        print("⏹️  Fixes cancelled")
        return
    
    # Apply fixes
    success = fix_admin_routes()
    
    if success:
        print(f"\n🎉 Admin route fixes completed!")
        print(f"🚀 Try visiting: http://localhost:5001/admin/companies")
        
        # Show the fixed function
        print(f"\n📄 Fixed admin_companies() function:")
        show_admin_companies_function()
    else:
        print(f"\n⚠️  Could not automatically fix the routes")
        print(f"💡 You may need to manually add: companies = Company.query.all()")

if __name__ == '__main__':
    main()