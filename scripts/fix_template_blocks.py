#!/usr/bin/env python3
"""
Targeted Template Block Fixer
Fixes the critical template block issues causing duplicate content
"""

import os
import re
from pathlib import Path

class TargetedTemplateFixer:
    def __init__(self, project_root="."):
        self.project_root = Path(project_root)
        self.fixes_applied = []
        self.errors = []
        
    def fix_all_template_issues(self):
        """Fix all critical template issues"""
        print("🔧 Fixing Critical Template Issues...")
        print("="*50)
        
        # Skip backup directories
        skip_dirs = ['tms_backup_', '__pycache__', '.git']
        
        # Get all HTML files in main templates directory only
        html_files = []
        for html_file in self.project_root.glob("templates/**/*.html"):
            skip_file = False
            for skip_dir in skip_dirs:
                if skip_dir in str(html_file):
                    skip_file = True
                    break
            if not skip_file:
                html_files.append(html_file)
        
        print(f"📁 Found {len(html_files)} HTML files to fix")
        
        for html_file in html_files:
            try:
                self._fix_template_file(html_file)
            except Exception as e:
                error_msg = f"Error fixing {html_file}: {str(e)}"
                self.errors.append(error_msg)
                print(f"❌ {error_msg}")
        
        self._print_summary()
        return len(self.fixes_applied) > 0
    
    def _fix_template_file(self, html_file):
        """Fix individual template file"""
        rel_path = html_file.relative_to(self.project_root)
        
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Determine file type and apply appropriate fixes
        if 'components/' in str(rel_path):
            fixed_content = self._fix_component_file(content, str(rel_path))
        else:
            fixed_content = self._fix_regular_template(content, str(rel_path))
        
        # Save if changes were made
        if fixed_content != original_content:
            # Create backup
            backup_file = str(html_file) + '.backup'
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(original_content)
            
            # Save fixed content
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            
            self.fixes_applied.append(str(rel_path))
            print(f"✅ Fixed {rel_path}")
    
    def _fix_regular_template(self, content, file_path):
        """Fix regular template files"""
        lines = content.split('\n')
        
        # Check if template extends base.html
        extends_base = any('extends' in line and 'base.html' in line for line in lines)
        
        if not extends_base:
            # This might be a base template or standalone template
            return content
        
        # Fix missing endblock tags
        fixed_content = self._add_missing_endblocks(content)
        
        # Ensure proper block structure
        fixed_content = self._ensure_proper_block_structure(fixed_content)
        
        return fixed_content
    
    def _fix_component_file(self, content, file_path):
        """Fix component files - these should NOT extend base.html"""
        lines = content.split('\n')
        
        # Remove extends directive from components
        fixed_lines = []
        for line in lines:
            if 'extends' in line and 'base.html' in line:
                # Remove this line - components shouldn't extend base
                continue
            fixed_lines.append(line)
        
        # Remove any block definitions that wrap the entire content
        content = '\n'.join(fixed_lines)
        
        # Remove wrapping blocks but keep the content
        content = self._unwrap_component_blocks(content)
        
        return content
    
    def _add_missing_endblocks(self, content):
        """Add missing endblock tags"""
        lines = content.split('\n')
        
        # Track blocks that need closing
        open_blocks = []
        block_pattern = r'{%\s*block\s+(\w+)\s*%}'
        endblock_pattern = r'{%\s*endblock(?:\s+\w+)?\s*%}'
        
        # Find all block starts and ends
        for line in lines:
            # Check for block start
            block_match = re.search(block_pattern, line)
            if block_match:
                block_name = block_match.group(1)
                open_blocks.append(block_name)
            
            # Check for block end
            if re.search(endblock_pattern, line):
                if open_blocks:
                    open_blocks.pop()
        
        # Add missing endblocks at the end
        if open_blocks:
            lines.append('')  # Add blank line
            for block_name in reversed(open_blocks):
                lines.append(f'{{% endblock {block_name} %}}')
        
        return '\n'.join(lines)
    
    def _ensure_proper_block_structure(self, content):
        """Ensure proper block structure"""
        lines = content.split('\n')
        fixed_lines = []
        
        extends_found = False
        in_block = False
        content_outside_blocks = []
        
        for line in lines:
            stripped = line.strip()
            
            # Handle extends directive
            if 'extends' in stripped and 'base.html' in stripped:
                extends_found = True
                fixed_lines.append(line)
                continue
            
            # Handle block start
            if re.search(r'{%\s*block\s+\w+\s*%}', stripped):
                # If we have content outside blocks, add it first
                if content_outside_blocks:
                    if not any('block content' in l for l in fixed_lines):
                        fixed_lines.append('')
                        fixed_lines.append('{% block content %}')
                        fixed_lines.extend(content_outside_blocks)
                        fixed_lines.append('{% endblock content %}')
                        fixed_lines.append('')
                    content_outside_blocks = []
                
                in_block = True
                fixed_lines.append(line)
                continue
            
            # Handle block end
            if re.search(r'{%\s*endblock', stripped):
                in_block = False
                fixed_lines.append(line)
                continue
            
            # Handle content
            if extends_found and not in_block:
                # This is content outside blocks - collect it
                if stripped and not stripped.startswith('{%') and not stripped.startswith('{{'):
                    content_outside_blocks.append(line)
                    continue
            
            # Regular line
            fixed_lines.append(line)
        
        # If we still have content outside blocks, wrap it
        if content_outside_blocks:
            fixed_lines.append('')
            fixed_lines.append('{% block content %}')
            fixed_lines.extend(content_outside_blocks)
            fixed_lines.append('{% endblock content %}')
        
        return '\n'.join(fixed_lines)
    
    def _unwrap_component_blocks(self, content):
        """Remove block wrappers from components"""
        # Remove wrapping content and title blocks
        content = re.sub(r'{%\s*block\s+content\s*%}\s*\n?', '', content)
        content = re.sub(r'{%\s*block\s+title\s*%}.*?{%\s*endblock\s*(?:title)?\s*%}\s*\n?', '', content, flags=re.DOTALL)
        content = re.sub(r'\n?\s*{%\s*endblock\s*(?:content)?\s*%}', '', content)
        
        # Clean up multiple blank lines
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = content.strip()
        
        return content
    
    def _print_summary(self):
        """Print summary of fixes"""
        print("\n" + "="*60)
        print("🎉 TEMPLATE BLOCK FIXES SUMMARY")
        print("="*60)
        
        if self.fixes_applied:
            print(f"\n✅ FILES FIXED ({len(self.fixes_applied)}):")
            for file_path in self.fixes_applied:
                print(f"   ✓ {file_path}")
        
        if self.errors:
            print(f"\n❌ ERRORS ENCOUNTERED ({len(self.errors)}):")
            for error in self.errors:
                print(f"   ✗ {error}")
        
        if not self.fixes_applied and not self.errors:
            print(f"\n🎯 No template fixes needed!")
        
        print(f"\n💡 WHAT WAS FIXED:")
        print(f"   • Added missing endblock tags")
        print(f"   • Fixed template block structure")
        print(f"   • Removed extends from component files")
        print(f"   • Wrapped content outside blocks")
        
        print(f"\n📦 BACKUPS CREATED:")
        print(f"   All modified files have .backup copies")
        
        print(f"\n🚀 TEST YOUR APPLICATION:")
        print(f"   python app.py")
        print(f"   Visit: http://localhost:5001/tenders")

def main():
    """Main function"""
    print("🔧 Targeted Template Block Fixer")
    print("="*50)
    
    print("This will fix the critical template issues found by the scanner:")
    print("   ✅ Add missing endblock tags")
    print("   ✅ Fix component files that shouldn't extend base.html")
    print("   ✅ Ensure proper template block structure")
    print("   ✅ Wrap content outside blocks")
    
    proceed = input("\n❓ Proceed with template fixes? (y/N): ").strip().lower()
    
    if proceed != 'y':
        print("⏹️  Template fixes cancelled")
        return
    
    # Run the fixer
    fixer = TargetedTemplateFixer()
    success = fixer.fix_all_template_issues()
    
    if success:
        print(f"\n🎉 Template fixes completed!")
        print(f"💡 The duplicate header/footer issue should now be resolved.")
        print(f"🚀 Test your application at: http://localhost:5001/tenders")
    else:
        print(f"\n✅ No template fixes were needed!")

if __name__ == '__main__':
    main()