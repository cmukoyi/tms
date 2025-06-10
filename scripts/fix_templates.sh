#!/bin/bash

# Template Fix Script for Flask Tender Management System
# This script fixes all blueprint routing issues in templates

echo "🔧 Starting Template Fix Process..."
echo "=================================="

# Create backup directory
echo "📁 Creating backups..."
mkdir -p template_fixes_backup
cp -r templates/ template_fixes_backup/templates_$(date +%Y%m%d_%H%M%S)/

# Function to fix blueprint references in a file
fix_blueprint_references() {
    local file="$1"
    echo "🔨 Fixing: $file"
    
    # Remove non-existent endpoints
    sed -i '' '/url_for.*advanced_reports/d' "$file"
    sed -i '' '/url_for.*company_notes/d' "$file"
    
    # Fix admin blueprint references
    sed -i '' 's/admin\.admin_companies/admin_companies/g' "$file"
    sed -i '' 's/admin\.admin_users/admin_users/g' "$file"
    sed -i '' 's/admin\.create_company/create_company/g' "$file"
    sed -i '' 's/admin\.edit_company/edit_company/g' "$file"
    sed -i '' 's/admin\.create_user/create_user/g' "$file"
    sed -i '' 's/admin\.edit_user/edit_user/g' "$file"
    sed -i '' 's/admin\.view_company_users/view_company_users/g' "$file"
    sed -i '' 's/admin\.add_company_user/add_company_user/g' "$file"
    sed -i '' 's/admin\.edit_company_user/edit_company_user/g' "$file"
    sed -i '' 's/admin\.deactivate_company/deactivate_company/g' "$file"
    sed -i '' 's/admin\.admin_custom_fields/admin_custom_fields/g' "$file"
    sed -i '' 's/admin\.initialize_company_modules/initialize_company_modules/g' "$file"

    # Fix tenders blueprint references
    sed -i '' 's/tenders\.tenders/tenders/g' "$file"
    sed -i '' 's/tenders\.create_tender/create_tender/g' "$file"
    sed -i '' 's/tenders\.view_tender/view_tender/g' "$file"
    sed -i '' 's/tenders\.edit_tender/edit_tender/g' "$file"
    sed -i '' 's/tenders\.delete_tender/delete_tender/g' "$file"
    sed -i '' 's/tenders\.add_tender_note/add_tender_note/g' "$file"
    sed -i '' 's/tenders\.upload_tender_document/upload_tender_document/g' "$file"

    # Fix reports blueprint references
    sed -i '' 's/reports\.reports/reports/g' "$file"
    sed -i '' 's/reports\.tender_reports/tender_reports/g' "$file"
    sed -i '' 's/reports\.dashboard/dashboard/g' "$file"

    # Fix users blueprint references
    sed -i '' 's/users\.profile/profile/g' "$file"
    sed -i '' 's/users\.edit_profile/edit_profile/g' "$file"

    # Fix documents blueprint references
    sed -i '' 's/documents\.upload_document/upload_document/g' "$file"
    sed -i '' 's/documents\.download_document/download_document/g' "$file"
    sed -i '' 's/documents\.delete_document/delete_document/g' "$file"
    sed -i '' 's/documents\.view_document/view_document/g' "$file"

    # Fix auth blueprint references
    sed -i '' 's/auth\.login/login/g' "$file"
    sed -i '' 's/auth\.logout/logout/g' "$file"

    # Fix main blueprint references
    sed -i '' 's/main\.home/home/g' "$file"

    # Fix any remaining malformed url_for calls
    sed -i '' "s/url_for(''/url_for('/g" "$file"
    sed -i '' "s/'')/'/g" "$file"
}

# Fix all HTML templates
echo "🎯 Fixing template files..."
find templates/ -name "*.html" -not -name "*.backup" | while read template_file; do
    fix_blueprint_references "$template_file"
done

# Special handling for base.html to remove duplicate admin dropdown
echo "🧹 Cleaning up base.html duplicates..."
if [ -f "templates/base.html" ]; then
    # Create a temp file with duplicate admin dropdown removed
    python3 -c "
import re

with open('templates/base.html', 'r') as f:
    content = f.read()

# Remove duplicate admin dropdown (keep first occurrence)
pattern = r'(\{% if session\.is_super_admin %\}.*?<div class=\"nav-item dropdown\">.*?<i class=\"fas fa-cog me-1\"></i>Admin.*?</div>.*?\{% endif %\})'
matches = list(re.finditer(pattern, content, re.DOTALL))

if len(matches) > 1:
    # Remove all but the first match
    for match in reversed(matches[1:]):
        content = content[:match.start()] + content[match.end():]

# Remove references to non-existent endpoints
content = re.sub(r'<li>.*?url_for\(['\''\"]*advanced_reports['\''\"]*\).*?</li>\s*', '', content, flags=re.DOTALL)
content = re.sub(r'<li>.*?url_for\(['\''\"]*company_notes['\''\"]*\).*?</li>\s*', '', content, flags=re.DOTALL)

with open('templates/base.html', 'w') as f:
    f.write(content)
"
fi

# Verify fixes
echo ""
echo "🔍 Verification Report"
echo "======================"

# Check for remaining blueprint references
echo "Checking for remaining blueprint issues..."
blueprint_issues=$(find templates/ -name "*.html" -not -name "*.backup" -exec grep -l "url_for.*\." {} \; | grep -v "url_for('static")
if [ -z "$blueprint_issues" ]; then
    echo "✅ No blueprint reference issues found"
else
    echo "⚠️  Files still containing blueprint references:"
    echo "$blueprint_issues"
fi

# Check for malformed url_for calls
echo ""
echo "Checking for malformed url_for calls..."
malformed=$(find templates/ -name "*.html" -not -name "*.backup" -exec grep -l "url_for(''" {} \;)
if [ -z "$malformed" ]; then
    echo "✅ No malformed url_for calls found"
else
    echo "⚠️  Files with malformed url_for calls:"
    echo "$malformed"
fi

# Check for non-existent endpoints
echo ""
echo "Checking for non-existent endpoints..."
non_existent=$(find templates/ -name "*.html" -not -name "*.backup" -exec grep -l "advanced_reports\|company_notes" {} \;)
if [ -z "$non_existent" ]; then
    echo "✅ No references to non-existent endpoints found"
else
    echo "⚠️  Files still referencing non-existent endpoints:"
    echo "$non_existent"
fi

echo ""
echo "🎉 Template fix process completed!"
echo "📁 Backups saved in: template_fixes_backup/"
echo "🚀 Try starting your Flask app now: python app.py"
echo ""
echo "If you still get errors, run:"
echo "   grep -r 'url_for.*\\.' templates/ | grep -v 'url_for('static'"