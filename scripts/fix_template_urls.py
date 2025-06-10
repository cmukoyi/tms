#!/usr/bin/env python3
"""
Template URL Fixer Script
Finds and fixes url_for() references in templates to use blueprint format
"""

import os
import re
import glob

# URL mappings for blueprint migration
URL_MAPPINGS = {
    # Home and main
    "url_for('home')": "url_for('main.home')",
    
    # Authentication
    "url_for('login')": "url_for('auth.login')",
    "url_for('logout')": "url_for('auth.logout')",
    
    # Dashboard and Reports
    "url_for('dashboard')": "url_for('reports.dashboard')",
    "url_for('reports')": "url_for('reports.reports')",
    "url_for('active_tenders_report')": "url_for('reports.active_tenders_report')",
    "url_for('closed_tenders_report')": "url_for('reports.closed_tenders_report')",
    "url_for('overdue_tenders_report')": "url_for('reports.overdue_tenders_report')",
    "url_for('tenders_by_category_report')": "url_for('reports.tenders_by_category_report')",
    "url_for('tender_reports')": "url_for('reports.tender_reports')",
    "url_for('advanced_reports')": "url_for('reports.advanced_reports')",
    
    # Tenders
    "url_for('tenders')": "url_for('tenders.tenders')",
    "url_for('create_tender')": "url_for('tenders.create_tender')",
    "url_for('view_tender'": "url_for('tenders.view_tender'",
    "url_for('edit_tender'": "url_for('tenders.edit_tender'",
    "url_for('delete_tender'": "url_for('tenders.delete_tender'",
    "url_for('upload_tender_document'": "url_for('tenders.upload_tender_document'",
    "url_for('add_tender_note'": "url_for('tenders.add_tender_note'",
    "url_for('edit_tender_note'": "url_for('tenders.edit_tender_note'",
    "url_for('delete_tender_note'": "url_for('tenders.delete_tender_note'",
    
    # Admin
    "url_for('admin_companies')": "url_for('admin.admin_companies')",
    "url_for('create_company')": "url_for('admin.create_company')",
    "url_for('view_company'": "url_for('admin.view_company'",
    "url_for('edit_company'": "url_for('admin.edit_company'",
    "url_for('deactivate_company'": "url_for('admin.deactivate_company'",
    "url_for('admin_users')": "url_for('admin.admin_users')",
    "url_for('create_user')": "url_for('admin.create_user')",
    "url_for('edit_user'": "url_for('admin.edit_user'",
    "url_for('admin_roles')": "url_for('admin.admin_roles')",
    "url_for('admin_custom_fields')": "url_for('admin.admin_custom_fields')",
    "url_for('create_custom_field')": "url_for('admin.create_custom_field')",
    "url_for('edit_custom_field'": "url_for('admin.edit_custom_field'",
    "url_for('delete_custom_field'": "url_for('admin.delete_custom_field'",
    "url_for('view_company_users'": "url_for('admin.view_company_users'",
    "url_for('add_company_user'": "url_for('admin.add_company_user'",
    "url_for('edit_company_user'": "url_for('admin.edit_company_user'",
    "url_for('reset_company_user_password'": "url_for('admin.reset_company_user_password'",
    "url_for('toggle_company_user_status'": "url_for('admin.toggle_company_user_status'",
    "url_for('test_modules')": "url_for('admin.test_modules')",
    "url_for('init_modules')": "url_for('admin.init_modules')",
    "url_for('admin_company_modules')": "url_for('admin.admin_company_modules')",
    "url_for('view_company_modules'": "url_for('admin.view_company_modules'",
    "url_for('update_company_modules'": "url_for('admin.update_company_modules'",
    "url_for('batch_update_company_modules'": "url_for('admin.batch_update_company_modules'",
    "url_for('initialize_company_modules')": "url_for('admin.initialize_company_modules')",
    
    # Users
    "url_for('profile')": "url_for('users.profile')",
    "url_for('edit_profile')": "url_for('users.edit_profile')",
    "url_for('company_users')": "url_for('users.company_users')",
    "url_for('create_company_user')": "url_for('users.create_company_user')",
    "url_for('my_company_profile')": "url_for('users.my_company_profile')",
    "url_for('company_users_redirect')": "url_for('users.company_users_redirect')",
    
    # Company
    "url_for('my_company_modules')": "url_for('company.my_company_modules')",
    "url_for('request_module')": "url_for('company.request_module')",
    "url_for('my_company_modules_alt')": "url_for('company.my_company_modules_alt')",
    "url_for('company_notes')": "url_for('company.company_notes')",
    
    # Documents
    "url_for('documents')": "url_for('documents.documents')",
    "url_for('upload_document')": "url_for('documents.upload_document')",
    "url_for('view_document'": "url_for('documents.view_document'",
    "url_for('download_document'": "url_for('documents.download_document'",
    "url_for('delete_document'": "url_for('documents.delete_document'",
}

def find_template_files(directory="templates"):
    """Find all HTML template files"""
    if not os.path.exists(directory):
        print(f"❌ Templates directory '{directory}' not found!")
        return []
    
    template_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(('.html', '.htm', '.j2')):
                template_files.append(os.path.join(root, file))
    
    return template_files

def analyze_file(filepath):
    """Analyze a template file for url_for references"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Error reading {filepath}: {e}")
        return []
    
    # Find all url_for patterns
    url_pattern = r"url_for\(['\"][^'\"]+['\"][^)]*\)"
    matches = re.findall(url_pattern, content)
    
    issues = []
    for match in matches:
        # Check if this needs to be updated
        for old_pattern, new_pattern in URL_MAPPINGS.items():
            if old_pattern in match:
                issues.append({
                    'original': match,
                    'suggested': match.replace(old_pattern, new_pattern),
                    'line': None  # We'll find line numbers separately
                })
                break
    
    return issues

def fix_file(filepath, dry_run=True):
    """Fix url_for references in a template file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            original_content = f.read()
    except Exception as e:
        print(f"❌ Error reading {filepath}: {e}")
        return False
    
    content = original_content
    changes_made = 0
    
    # Apply all mappings
    for old_pattern, new_pattern in URL_MAPPINGS.items():
        if old_pattern in content:
            content = content.replace(old_pattern, new_pattern)
            changes_made += 1
    
    if changes_made > 0:
        if not dry_run:
            # Create backup
            backup_path = f"{filepath}.backup"
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(original_content)
            
            # Write fixed content
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ Fixed {changes_made} URL references in {filepath}")
            print(f"   💾 Backup saved as {backup_path}")
        else:
            print(f"🔄 Would fix {changes_made} URL references in {filepath}")
    
    return changes_made > 0

def main():
    """Main function"""
    print("🔧 Template URL Fixer for Blueprint Migration")
    print("=" * 50)
    
    # Find all template files
    template_files = find_template_files()
    
    if not template_files:
        print("❌ No template files found!")
        return
    
    print(f"📁 Found {len(template_files)} template files")
    
    # Analyze all files
    total_issues = 0
    files_with_issues = []
    
    for template_file in template_files:
        issues = analyze_file(template_file)
        if issues:
            files_with_issues.append((template_file, issues))
            total_issues += len(issues)
    
    if total_issues == 0:
        print("🎉 No URL issues found! All templates are already using blueprint format.")
        return
    
    print(f"\n📊 Analysis Results:")
    print(f"   🔍 Files with issues: {len(files_with_issues)}")
    print(f"   ⚠️  Total URL references to fix: {total_issues}")
    
    # Show details
    print(f"\n📋 Files that need fixing:")
    for filepath, issues in files_with_issues:
        print(f"\n📄 {filepath} ({len(issues)} issues)")
        for i, issue in enumerate(issues[:3], 1):  # Show first 3 issues
            print(f"   {i}. {issue['original']}")
            print(f"      → {issue['suggested']}")
        if len(issues) > 3:
            print(f"      ... and {len(issues) - 3} more")
    
    # Ask user what to do
    print(f"\n❓ What would you like to do?")
    print(f"   1. Fix all files automatically (with backups)")
    print(f"   2. Show dry run (what would be changed)")
    print(f"   3. Fix just the critical file (base.html)")
    print(f"   4. Exit")
    
    choice = input(f"\nEnter your choice (1-4): ").strip()
    
    if choice == '1':
        print(f"\n🔄 Fixing all files...")
        fixed_count = 0
        for filepath, _ in files_with_issues:
            if fix_file(filepath, dry_run=False):
                fixed_count += 1
        print(f"\n🎉 Fixed {fixed_count} files!")
        print(f"💡 Backups saved with .backup extension")
        
    elif choice == '2':
        print(f"\n🔄 Dry run - showing what would be changed...")
        for filepath, _ in files_with_issues:
            fix_file(filepath, dry_run=True)
            
    elif choice == '3':
        # Find base.html and fix it
        base_files = [f for f in template_files if 'base.html' in f]
        if base_files:
            print(f"\n🔄 Fixing critical template: {base_files[0]}")
            fix_file(base_files[0], dry_run=False)
            print(f"✅ Fixed! Try running your app again.")
        else:
            print(f"❌ base.html not found!")
            
    elif choice == '4':
        print(f"⏹️  Exiting without changes")
        
    else:
        print(f"❌ Invalid choice")

if __name__ == '__main__':
    main()