#!/bin/bash

echo "🎨 Extracting CSS from base.html to separate file..."

# Create static directories if they don't exist
mkdir -p static/css
mkdir -p static/js

# Create backup
cp templates/base.html templates/base.html.backup_before_css_extract_$(date +%Y%m%d_%H%M%S)

# Extract CSS from base.html
python3 << 'EOF'
import re

# Read the base.html file
with open('templates/base.html', 'r') as f:
    content = f.read()

# Extract CSS between <style> and </style> tags
css_pattern = r'<style>(.*?)</style>'
css_match = re.search(css_pattern, content, re.DOTALL)

if css_match:
    css_content = css_match.group(1).strip()
    
    # Write CSS to separate file
    with open('static/css/style.css', 'w') as f:
        f.write(css_content)
    
    # Remove CSS from base.html and replace with link tag
    new_content = re.sub(css_pattern, 
        '    <link href="{{ url_for(\'static\', filename=\'css/style.css\') }}" rel="stylesheet" />', 
        content, flags=re.DOTALL)
    
    # Write updated base.html
    with open('templates/base.html', 'w') as f:
        f.write(new_content)
    
    print("✅ CSS extracted successfully!")
    print(f"📁 CSS file created: static/css/style.css")
    print(f"📝 Updated base.html with CSS link")
    
    # Get CSS file size
    import os
    css_size = os.path.getsize('static/css/style.css') / 1024
    print(f"📊 CSS file size: {css_size:.1f} KB")
    
else:
    print("❌ No CSS found in base.html")

EOF

echo ""
echo "🚀 Benefits of this change:"
echo "   ✅ Faster page loading (CSS cached by browser)"
echo "   ✅ Better code organization"
echo "   ✅ Easier to maintain styles"
echo "   ✅ Reduced HTML file size"
echo ""
echo "🔧 Test your app: python app.py"
