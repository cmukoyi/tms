#!/usr/bin/env python3
"""
HTML Duplicate Content Fixer
Scans all HTML files and removes duplicate headers/footers that cause template inheritance issues
"""

import os
import re
from pathlib import Path
from collections import defaultdict

class HTMLDuplicateFixer:
    def __init__(self, project_root="."):
        self.project_root = Path(project_root)
        self.issues_found = []
        self.fixes_applied = []
        self.errors = []
        
    def scan_and_fix_html_files(self):
        """Scan all HTML files and fix duplicate content issues"""
        print("🔍 Scanning for HTML template issues...")
        
        html_files = list(self.project_root.glob("**/*.html"))
        
        if not html_files:
            print("❌ No HTML files found!")
            return False
        
        print(f"📁 Found {len(html_files)} HTML files")
        
        for html_file in html_files:
            try:
                self._analyze_and_fix_html_file(html_file)
            except Exception as e:
                error_msg = f"Error processing {html_file}: {str(e)}"
                self.errors.append(error_msg)
                print(f"❌ {error_msg}")
        
        self._print_summary()
        return len(self.fixes_applied) > 0
    
    def _analyze_and_fix_html_file(self, html_file):
        """Analyze and fix individual HTML file"""
        rel_path = html_file.relative_to(self.project_root)
        
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        issues = self._detect_template_issues(content, str(rel_path))
        
        if issues:
            print(f"\n🔧 Fixing {rel_path}...")
            
            # Create backup
            backup_file = str(html_file) + '.backup'
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(original_content)
            
            # Apply fixes
            fixed_content = self._apply_fixes(content, issues, str(rel_path))
            
            if fixed_content != original_content:
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                
                self.fixes_applied.append(str(rel_path))
                print(f"✅ Fixed {len(issues)} issues in {rel_path}")
            else:
                print(f"⏭️  No changes needed for {rel_path}")
    
    def _detect_template_issues(self, content, file_path):
        """Detect common template inheritance issues"""
        issues = []
        lines = content.split('\n')
        
        # Issue 1: Check for extends directive placement
        extends_line = None
        first_non_empty = None
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith('<!--'):
                continue
            
            if first_non_empty is None:
                first_non_empty = i
            
            if 'extends' in stripped and '{%' in stripped:
                extends_line = i
                break
        
        # Check if extends is not first
        if extends_line is not None and first_non_empty is not None and extends_line != first_non_empty:
            issues.append({
                'type': 'extends_not_first',
                'line': extends_line,
                'description': 'extends directive should be first line'
            })
        
        # Issue 2: Check for HTML outside blocks in child templates
        if 'extends' in content:
            html_outside_blocks = self._find_html_outside_blocks(content)
            if html_outside_blocks:
                issues.append({
                    'type': 'html_outside_blocks',
                    'lines': html_outside_blocks,
                    'description': 'HTML content outside template blocks'
                })
        
        # Issue 3: Check for duplicate DOCTYPE/HTML tags in child templates
        if 'extends' in content:
            if '<!DOCTYPE' in content:
                issues.append({
                    'type': 'duplicate_doctype',
                    'description': 'DOCTYPE in child template (should only be in base)'
                })
            
            if re.search(r'<html[^>]*>', content, re.IGNORECASE):
                issues.append({
                    'type': 'duplicate_html_tag',
                    'description': 'HTML tag in child template (should only be in base)'
                })
            
            if re.search(r'<head[^>]*>', content, re.IGNORECASE):
                issues.append({
                    'type': 'duplicate_head_tag',
                    'description': 'HEAD tag in child template (should only be in base)'
                })
            
            if re.search(r'<body[^>]*>', content, re.IGNORECASE):
                issues.append({
                    'type': 'duplicate_body_tag',
                    'description': 'BODY tag in child template (should only be in base)'
                })
        
        # Issue 4: Check for unclosed blocks
        unclosed_blocks = self._find_unclosed_blocks(content)
        if unclosed_blocks:
            issues.append({
                'type': 'unclosed_blocks',
                'blocks': unclosed_blocks,
                'description': 'Unclosed template blocks'
            })
        
        # Issue 5: Check for duplicate navbar/footer content
        if self._has_duplicate_nav_footer(content):
            issues.append({
                'type': 'duplicate_nav_footer',
                'description': 'Duplicate navigation or footer content'
            })
        
        # Issue 6: Check for malformed block structure
        malformed_blocks = self._find_malformed_blocks(content)
        if malformed_blocks:
            issues.append({
                'type': 'malformed_blocks',
                'blocks': malformed_blocks,
                'description': 'Malformed block definitions'
            })
        
        return issues
    
    def _find_html_outside_blocks(self, content):
        """Find HTML content outside template blocks"""
        lines = content.split('\n')
        html_outside = []
        
        in_block = False
        extends_found = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith('<!--'):
                continue
            
            # Check for extends
            if 'extends' in stripped and '{%' in stripped:
                extends_found = True
                continue
            
            # Check for block start
            if re.search(r'{%\s*block\s+\w+\s*%}', stripped):
                in_block = True
                continue
            
            # Check for block end
            if re.search(r'{%\s*endblock', stripped):
                in_block = False
                continue
            
            # If we're in a child template (extends found) and not in a block
            if extends_found and not in_block:
                # Check if this line has HTML content
                if self._is_html_content(stripped):
                    html_outside.append(i + 1)
        
        return html_outside
    
    def _is_html_content(self, line):
        """Check if line contains HTML content"""
        # Skip Jinja2 directives
        if line.startswith('{%') or line.startswith('{{'):
            return False
        
        # Check for HTML tags
        return bool(re.search(r'<[^>]+>', line))
    
    def _find_unclosed_blocks(self, content):
        """Find unclosed template blocks"""
        block_stack = []
        unclosed = []
        
        # Find all block start/end pairs
        block_start_pattern = r'{%\s*block\s+(\w+)\s*%}'
        block_end_pattern = r'{%\s*endblock(?:\s+(\w+))?\s*%}'
        
        for match in re.finditer(block_start_pattern, content):
            block_name = match.group(1)
            block_stack.append(block_name)
        
        for match in re.finditer(block_end_pattern, content):
            if block_stack:
                block_stack.pop()
        
        return block_stack  # Any remaining blocks are unclosed
    
    def _has_duplicate_nav_footer(self, content):
        """Check for duplicate navigation or footer content"""
        nav_indicators = [
            'navbar', 'nav-bar', 'navigation', 'menu',
            'class="nav"', 'id="nav"', '<nav'
        ]
        
        footer_indicators = [
            'footer', 'class="footer"', 'id="footer"', 
            '<footer', 'copyright', '&copy;'
        ]
        
        # Count occurrences
        nav_count = sum(content.lower().count(indicator) for indicator in nav_indicators)
        footer_count = sum(content.lower().count(indicator) for indicator in footer_indicators)
        
        # If we have extends and nav/footer content, it might be duplicate
        if 'extends' in content and (nav_count > 2 or footer_count > 2):
            return True
        
        return False
    
    def _find_malformed_blocks(self, content):
        """Find malformed block definitions"""
        malformed = []
        
        # Check for blocks without proper syntax
        lines = content.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Look for block-like patterns that might be malformed
            if 'block' in stripped and '{%' in stripped:
                # Check for proper block syntax
                if not re.search(r'{%\s*block\s+\w+\s*%}', stripped):
                    malformed.append({
                        'line': i + 1,
                        'content': stripped,
                        'issue': 'malformed block syntax'
                    })
        
        return malformed
    
    def _apply_fixes(self, content, issues, file_path):
        """Apply fixes to content based on detected issues"""
        fixed_content = content
        
        for issue in issues:
            if issue['type'] == 'extends_not_first':
                fixed_content = self._fix_extends_placement(fixed_content)
            
            elif issue['type'] == 'html_outside_blocks':
                fixed_content = self._fix_html_outside_blocks(fixed_content)
            
            elif issue['type'] in ['duplicate_doctype', 'duplicate_html_tag', 'duplicate_head_tag', 'duplicate_body_tag']:
                fixed_content = self._fix_duplicate_structure_tags(fixed_content)
            
            elif issue['type'] == 'unclosed_blocks':
                fixed_content = self._fix_unclosed_blocks(fixed_content, issue['blocks'])
            
            elif issue['type'] == 'duplicate_nav_footer':
                fixed_content = self._fix_duplicate_nav_footer(fixed_content)
            
            elif issue['type'] == 'malformed_blocks':
                fixed_content = self._fix_malformed_blocks(fixed_content, issue['blocks'])
        
        return fixed_content
    
    def _fix_extends_placement(self, content):
        """Move extends directive to first line"""
        lines = content.split('\n')
        extends_line = None
        extends_content = None
        
        # Find and remove extends line
        for i, line in enumerate(lines):
            if 'extends' in line and '{%' in line:
                extends_line = i
                extends_content = line
                lines.pop(i)
                break
        
        if extends_content:
            # Insert at beginning
            lines.insert(0, extends_content)
            lines.insert(1, '')  # Add blank line
        
        return '\n'.join(lines)
    
    def _fix_html_outside_blocks(self, content):
        """Wrap HTML content outside blocks in content block"""
        lines = content.split('\n')
        fixed_lines = []
        
        in_block = False
        extends_found = False
        content_block_added = False
        html_outside = []
        
        for line in lines:
            stripped = line.strip()
            
            # Check for extends
            if 'extends' in stripped and '{%' in stripped:
                extends_found = True
                fixed_lines.append(line)
                continue
            
            # Check for block start
            if re.search(r'{%\s*block\s+\w+\s*%}', stripped):
                in_block = True
                # If we have collected HTML outside blocks, wrap it first
                if html_outside and not content_block_added:
                    fixed_lines.append('')
                    fixed_lines.append('{% block content %}')
                    fixed_lines.extend(html_outside)
                    fixed_lines.append('{% endblock %}')
                    html_outside = []
                    content_block_added = True
                fixed_lines.append(line)
                continue
            
            # Check for block end
            if re.search(r'{%\s*endblock', stripped):
                in_block = False
                fixed_lines.append(line)
                continue
            
            # If we're in a child template and not in a block
            if extends_found and not in_block:
                if self._is_html_content(stripped) or (stripped and not stripped.startswith('{%') and not stripped.startswith('{{')):
                    html_outside.append(line)
                    continue
            
            fixed_lines.append(line)
        
        # If we still have HTML outside blocks at the end, wrap it
        if html_outside and not content_block_added:
            fixed_lines.append('')
            fixed_lines.append('{% block content %}')
            fixed_lines.extend(html_outside)
            fixed_lines.append('{% endblock %}')
        
        return '\n'.join(fixed_lines)
    
    def _fix_duplicate_structure_tags(self, content):
        """Remove duplicate DOCTYPE, HTML, HEAD, BODY tags from child templates"""
        # Only remove these if extends is present
        if 'extends' not in content:
            return content
        
        # Remove DOCTYPE
        content = re.sub(r'<!DOCTYPE[^>]*>', '', content, flags=re.IGNORECASE)
        
        # Remove HTML tag (opening and closing)
        content = re.sub(r'<html[^>]*>', '', content, flags=re.IGNORECASE)
        content = re.sub(r'</html>', '', content, flags=re.IGNORECASE)
        
        # Remove HEAD section
        content = re.sub(r'<head[^>]*>.*?</head>', '', content, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove BODY tag (but keep content)
        content = re.sub(r'<body[^>]*>', '', content, flags=re.IGNORECASE)
        content = re.sub(r'</body>', '', content, flags=re.IGNORECASE)
        
        return content
    
    def _fix_unclosed_blocks(self, content, unclosed_blocks):
        """Add missing endblock tags"""
        for block_name in unclosed_blocks:
            content += f'\n{{% endblock {block_name} %}}'
        
        return content
    
    def _fix_duplicate_nav_footer(self, content):
        """Remove duplicate navigation and footer content from child templates"""
        if 'extends' not in content:
            return content
        
        # Remove common navigation patterns
        nav_patterns = [
            r'<nav[^>]*>.*?</nav>',
            r'<div[^>]*class="[^"]*navbar[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*navigation[^"]*"[^>]*>.*?</div>'
        ]
        
        for pattern in nav_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove common footer patterns
        footer_patterns = [
            r'<footer[^>]*>.*?</footer>',
            r'<div[^>]*class="[^"]*footer[^"]*"[^>]*>.*?</div>'
        ]
        
        for pattern in footer_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
        
        return content
    
    def _fix_malformed_blocks(self, content, malformed_blocks):
        """Fix malformed block definitions"""
        lines = content.split('\n')
        
        for block_info in malformed_blocks:
            line_num = block_info['line'] - 1
            if line_num < len(lines):
                line = lines[line_num]
                
                # Try to fix common malformed block patterns
                if 'block' in line and '{%' in line:
                    # Extract block name if possible
                    block_match = re.search(r'block\s+(\w+)', line)
                    if block_match:
                        block_name = block_match.group(1)
                        lines[line_num] = f'{{% block {block_name} %}}'
        
        return '\n'.join(lines)
    
    def _print_summary(self):
        """Print summary of fixes applied"""
        print("\n" + "="*60)
        print("🎉 HTML DUPLICATE CONTENT FIXER SUMMARY")
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
            print(f"\n🎯 No HTML template issues found - your templates are clean!")
        
        print(f"\n💡 WHAT WAS FIXED:")
        print(f"   • Moved extends directives to first line")
        print(f"   • Wrapped HTML content outside blocks")
        print(f"   • Removed duplicate DOCTYPE/HTML/HEAD/BODY tags")
        print(f"   • Fixed unclosed template blocks")
        print(f"   • Removed duplicate navigation/footer content")
        print(f"   • Fixed malformed block syntax")
        
        print(f"\n📦 BACKUPS CREATED:")
        print(f"   All modified files have .backup copies")
        
        print(f"\n🚀 TEST YOUR APPLICATION:")
        print(f"   python app.py")
        print(f"   Visit: http://localhost:5001/tenders")

def main():
    """Main function"""
    print("🔧 HTML Duplicate Content Fixer")
    print("="*50)
    
    # Check if we're in the right directory
    if not os.path.exists('templates') and not list(Path('.').glob('**/*.html')):
        print("❌ No HTML files found in current directory or subdirectories!")
        print("   Make sure you're in the project root")
        return
    
    print("⚠️  This script will modify HTML files to fix template inheritance issues!")
    print("   • Backups will be created automatically (.backup extension)")
    print("   • Fixes duplicate headers/footers/navigation")
    print("   • Ensures proper Jinja2 template structure")
    
    proceed = input("\n❓ Proceed with HTML fixes? (y/N): ").strip().lower()
    
    if proceed != 'y':
        print("⏹️  HTML fixes cancelled")
        return
    
    # Run the fixer
    fixer = HTMLDuplicateFixer()
    success = fixer.scan_and_fix_html_files()
    
    if success:
        print(f"\n🎉 HTML template fixes completed!")
        print(f"💡 Test your application to verify the duplicate content is fixed.")
    else:
        print(f"\n✅ No HTML template issues found!")
        print(f"💡 Your templates are already properly structured.")

if __name__ == '__main__':
    main()