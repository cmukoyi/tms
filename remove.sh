#!/bin/bash

# Script to fix all component files by removing template inheritance
echo "🔧 Fixing all component files..."

# List of all component files that need fixing
COMPONENTS=(
    "templates/components/tender_list_table_1.html"
    "templates/components/dashboard_table_2.html"
    "templates/components/edit_profile_form_1.html"
    "templates/components/list_form_1.html"
    "templates/components/edit_company_form_1.html"
    "templates/components/view_table_1.html"
    "templates/components/list_table_1.html"
    "templates/components/create_company_form_1.html"
    "templates/components/view_form_2.html"
    "templates/components/company_users_table_1.html"
    "templates/components/dashboard_table_1.html"
    "templates/components/documents_table_1.html"
    "templates/components/edit_form_1.html"
    "templates/components/tender_list_table_2.html"
    "templates/components/login_form_1.html"
)

# Create backup directory
mkdir -p templates/components/backup_$(date +%Y%m%d_%H%M%S)

echo "📁 Created backup directory"

# Fix each component file
for component in "${COMPONENTS[@]}"; do
    if [ -f "$component" ]; then
        echo "🔄 Processing: $component"
        
        # Create backup
        cp "$component" "templates/components/backup_$(date +%Y%m%d_%H%M%S)/$(basename $component)"
        
        # Remove template inheritance lines and extract content
        # This removes:
        # - {% extends 'base.html' %}
        # - {% block title %}...{% endblock %}
        # - {% block content %}
        # - {% endblock %} (at the end)
        
        # Create temporary file
        temp_file=$(mktemp)
        
        # Extract content between {% block content %} and final {% endblock %}
        awk '
        BEGIN { in_content = 0; content_started = 0 }
        /{% *block +content +%}/ { in_content = 1; next }
        /{% *endblock *%}$/ && in_content { 
            if (content_started) {
                in_content = 0
                next
            }
        }
        /{% *extends/ { next }
        /{% *block +title/ { 
            while (getline && !/{% *endblock *%}/) continue
            next 
        }
        in_content { 
            content_started = 1
            print 
        }
        !in_content && !/{% *(extends|block)/ && content_started == 0 { print }
        ' "$component" > "$temp_file"
        
        # If extraction successful and file has content, replace original
        if [ -s "$temp_file" ]; then
            mv "$temp_file" "$component"
            echo "✅ Fixed: $component"
        else
            echo "❌ Failed to process: $component (keeping original)"
            rm "$temp_file"
        fi
    else
        echo "⚠️  File not found: $component"
    fi
done

echo ""
echo "🎉 Component fix complete!"
echo "📁 Backups saved in: templates/components/backup_$(date +%Y%m%d_%H%M%S)/"
echo ""
echo "🧪 Test your pages now - you should see only 1 footer per page!"
echo ""
echo "🔍 To verify the fix worked:"
echo "   grep -r 'extends.*base' templates/components/ || echo 'All components fixed!'"
