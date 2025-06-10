#!/usr/bin/env python3
"""
Quick Template URL Fixer
Fixes the most common template URL issues for blueprint migration
"""

import os
import re
from pathlib import Path

def fix_template_urls():
    """Fix template URL references"""
    templates_dir = Path("templates")
    
    if not templates_dir.exists():
        print("❌ templates directory not found!")
        return False
    
    # Common URL mappings for blueprint migration
    url_mappings = {
        "url_for('tenders'": "url_for('tenders.tenders'",
        "url_for('home')": "url_for('main.home')",
        "url_for('login')": "url_for('auth.login')",
        "url_for('logout')": "url_for('auth.logout')",
        "url_for('dashboard')": "url_for('reports.dashboard')",
        "url_for('reports')": "url_for('reports.reports')",
        "url_for('profile')": "url_for('users.profile')",
        "url_for('edit_profile')": "url_for('users.edit_profile')",
        "url_for('create_tender')": "url_for('tenders.create_tender')",
        "url_for('view_tender'": "url_for('tenders.view_tender'",
        "url_for('edit_tender'": "url_for('tenders.edit_tender'",
        "url_for('delete_tender'": "url_for('tenders.delete_tender'",
        "url_for('upload_tender_document'": "url_for('tenders.upload_tender_document'",
        "url_for('add_tender_note'": "url_for('tenders.add_tender_note'",
        "url_for('admin_companies')": "url_for('admin.admin_companies')",
        "url_for('admin_users')": "url_for('admin.admin_users')",
        "url_for('create_company')": "url_for('admin.create_company')",
        "url_for('view_company'": "url_for('admin.view_company'",
        "url_for('documents')": "url_for('documents.documents')",
        "url_for('upload_document')": "url_for('documents.upload_document')",
        "url_for('view_document'": "url_for('documents.view_document'",
        "url_for('active_tenders_report')": "url_for('reports.active_tenders_report')",
        "url_for('closed_tenders_report')": "url_for('reports.closed_tenders_report')",
        "url_for('overdue_tenders_report')": "url_for('reports.overdue_tenders_report')",
        "url_for('tenders_by_category_report')": "url_for('reports.tenders_by_category_report')",
        "url_for('tender_reports')": "url_for('reports.tender_reports')",
        "url_for('my_company_modules')": "url_for('company.my_company_modules')",
        "url_for('company_notes')": "url_for('company.company_notes')",
    }
    
    fixed_files = []
    total_replacements = 0
    
    # Process all HTML files
    for template_file in templates_dir.glob("**/*.html"):
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            file_replacements = 0
            
            # Apply all URL mappings
            for old_url, new_url in url_mappings.items():
                if old_url in content:
                    content = content.replace(old_url, new_url)
                    file_replacements += content.count(new_url) - original_content.count(new_url)
            
            # If changes were made, save the file
            if content != original_content:
                # Create backup
                backup_file = str(template_file) + '.backup'
                with open(backup_file, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                
                # Save updated content
                with open(template_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                fixed_files.append(str(template_file))
                total_replacements += file_replacements
                print(f"✅ Fixed {template_file} ({file_replacements} URLs updated)")
        
        except Exception as e:
            print(f"❌ Error processing {template_file}: {e}")
    
    if fixed_files:
        print(f"\n🎉 Fixed {len(fixed_files)} template files with {total_replacements} URL updates")
        print(f"💾 Backups created with .backup extension")
        return True
    else:
        print("✅ No template URL fixes needed")
        return False

def fix_specific_tender_issue():
    """Fix the specific tenders pagination URL issue"""
    tender_list_template = Path("templates/tenders/list.html")
    
    if not tender_list_template.exists():
        print("❌ templates/tenders/list.html not found!")
        return False
    
    print("🔧 Fixing specific tenders pagination issue...")
    
    with open(tender_list_template, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Look for the specific problematic line and fix it
    # The error shows line 110 has: url_for('tenders', page=page_num, ...)
    
    # Create backup
    backup_file = str(tender_list_template) + '.backup'
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # Fix the specific issue
    original_content = content
    
    # Replace all instances of url_for('tenders' with url_for('tenders.tenders'
    content = re.sub(r"url_for\('tenders'", "url_for('tenders.tenders'", content)
    
    if content != original_content:
        with open(tender_list_template, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ Fixed tenders pagination URLs")
        return True
    
    return False

def scan_remaining_issues():
    """Scan for any remaining template URL issues"""
    templates_dir = Path("templates")
    
    if not templates_dir.exists():
        return []
    
    issues = []
    
    # Patterns that indicate old-style URLs
    old_patterns = [
        r"url_for\('(?!main\.|auth\.|admin\.|users\.|tenders\.|reports\.|documents\.|company\.)[^']*'",
        r"url_for\('home'",
        r"url_for\('login'",
        r"url_for\('dashboard'",
        r"url_for\('tenders'(?!\.)'"
    ]
    
    for template_file in templates_dir.glob("**/*.html"):
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            for i, line in enumerate(content.split('\n'), 1):
                for pattern in old_patterns:
                    if re.search(pattern, line):
                        issues.append({
                            'file': str(template_file),
                            'line': i,
                            'content': line.strip()
                        })
        except:
            pass
    
    return issues

def main():
    """Main function"""
    print("🔧 Quick Template URL Fixer")
    print("="*40)
    
    # Fix the specific tenders issue first
    fix_specific_tender_issue()
    
    # Fix all common template URL issues
    print("\n🔄 Fixing all template URL references...")
    fix_template_urls()
    
    # Scan for any remaining issues
    print("\n🔍 Scanning for remaining URL issues...")
    remaining_issues = scan_remaining_issues()
    
    if remaining_issues:
        print(f"\n⚠️  Found {len(remaining_issues)} remaining URL issues:")
        for issue in remaining_issues[:10]:  # Show first 10
            print(f"   📄 {issue['file']}:{issue['line']}")
            print(f"      {issue['content']}")
        
        if len(remaining_issues) > 10:
            print(f"      ... and {len(remaining_issues) - 10} more")
    else:
        print("✅ No remaining URL issues found!")
    
    print(f"\n🚀 Try running your app now:")
    print(f"   python app.py")
    print(f"   Then visit: http://localhost:5001/tenders")

if __name__ == '__main__':
    main()