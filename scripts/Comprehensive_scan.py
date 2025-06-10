#!/usr/bin/env python3
"""
Comprehensive HTML Template Scanner
Deep analysis of all HTML files to find duplicate content issues
"""

import os
import re
from pathlib import Path
from collections import defaultdict
import json

class ComprehensiveHTMLScanner:
    def __init__(self, project_root="."):
        self.project_root = Path(project_root)
        self.scan_results = {
            'files': {},
            'base_templates': [],
            'child_templates': [],
            'duplicate_issues': [],
            'block_structure': {},
            'content_analysis': {},
            'template_inheritance': {}
        }
    
    def full_scan(self):
        """Perform comprehensive scan of all HTML files"""
        print("🔍 Starting Comprehensive HTML Template Scan...")
        print("="*60)
        
        # Find all HTML files
        html_files = list(self.project_root.glob("**/*.html"))
        
        if not html_files:
            print("❌ No HTML files found!")
            return self.scan_results
        
        print(f"📁 Found {len(html_files)} HTML files")
        
        # Scan each file
        for html_file in html_files:
            rel_path = str(html_file.relative_to(self.project_root))
            print(f"🔍 Scanning: {rel_path}")
            
            try:
                file_analysis = self._analyze_html_file(html_file)
                self.scan_results['files'][rel_path] = file_analysis
                
                # Categorize files
                if file_analysis['is_base_template']:
                    self.scan_results['base_templates'].append(rel_path)
                elif file_analysis['extends_template']:
                    self.scan_results['child_templates'].append(rel_path)
                
            except Exception as e:
                print(f"❌ Error scanning {rel_path}: {e}")
                self.scan_results['files'][rel_path] = {'error': str(e)}
        
        # Analyze relationships and issues
        self._analyze_template_inheritance()
        self._detect_duplicate_content()
        self._analyze_block_structure()
        
        # Print detailed report
        self._print_detailed_report()
        
        return self.scan_results
    
    def _analyze_html_file(self, html_file):
        """Detailed analysis of a single HTML file"""
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        
        analysis = {
            'file_path': str(html_file),
            'line_count': len(lines),
            'size_bytes': len(content),
            'extends_template': None,
            'is_base_template': False,
            'blocks_defined': [],
            'blocks_used': [],
            'html_structure': {},
            'jinja_structure': {},
            'duplicate_indicators': {},
            'template_issues': [],
            'content_outside_blocks': [],
            'first_10_lines': lines[:10],
            'last_10_lines': lines[-10:] if len(lines) > 10 else []
        }
        
        # Check for extends
        extends_match = re.search(r'{%\s*extends\s+["\']([^"\']+)["\']\s*%}', content)
        if extends_match:
            analysis['extends_template'] = extends_match.group(1)
        else:
            # Check if this looks like a base template
            if ('<!DOCTYPE' in content and '<html' in content and 
                '<head' in content and '<body' in content):
                analysis['is_base_template'] = True
        
        # Find all blocks
        block_definitions = re.findall(r'{%\s*block\s+(\w+)\s*%}', content)
        analysis['blocks_defined'] = block_definitions
        
        block_usages = re.findall(r'{%\s*endblock(?:\s+(\w+))?\s*%}', content)
        analysis['blocks_used'] = [b for b in block_usages if b]
        
        # Analyze HTML structure
        analysis['html_structure'] = {
            'has_doctype': '<!DOCTYPE' in content,
            'has_html_tag': bool(re.search(r'<html[^>]*>', content, re.IGNORECASE)),
            'has_head_tag': bool(re.search(r'<head[^>]*>', content, re.IGNORECASE)),
            'has_body_tag': bool(re.search(r'<body[^>]*>', content, re.IGNORECASE)),
            'has_title_tag': bool(re.search(r'<title[^>]*>', content, re.IGNORECASE)),
            'meta_tags': len(re.findall(r'<meta[^>]*>', content, re.IGNORECASE)),
            'link_tags': len(re.findall(r'<link[^>]*>', content, re.IGNORECASE)),
            'script_tags': len(re.findall(r'<script[^>]*>', content, re.IGNORECASE))
        }
        
        # Analyze navigation and footer content
        analysis['duplicate_indicators'] = {
            'navbar_count': self._count_navbar_elements(content),
            'footer_count': self._count_footer_elements(content),
            'menu_count': self._count_menu_elements(content),
            'header_count': self._count_header_elements(content),
            'navigation_classes': self._find_navigation_classes(content),
            'footer_classes': self._find_footer_classes(content)
        }
        
        # Check for content outside blocks in child templates
        if analysis['extends_template']:
            analysis['content_outside_blocks'] = self._find_content_outside_blocks(content)
        
        # Detect template issues
        analysis['template_issues'] = self._detect_template_issues(content, analysis)
        
        return analysis
    
    def _count_navbar_elements(self, content):
        """Count navigation bar elements"""
        patterns = [
            r'<nav[^>]*>',
            r'class="[^"]*navbar[^"]*"',
            r'class="[^"]*nav-bar[^"]*"',
            r'class="[^"]*navigation[^"]*"',
            r'id="[^"]*navbar[^"]*"',
            r'id="[^"]*nav[^"]*"'
        ]
        return sum(len(re.findall(pattern, content, re.IGNORECASE)) for pattern in patterns)
    
    def _count_footer_elements(self, content):
        """Count footer elements"""
        patterns = [
            r'<footer[^>]*>',
            r'class="[^"]*footer[^"]*"',
            r'id="[^"]*footer[^"]*"',
            r'&copy;',
            r'copyright'
        ]
        return sum(len(re.findall(pattern, content, re.IGNORECASE)) for pattern in patterns)
    
    def _count_menu_elements(self, content):
        """Count menu elements"""
        patterns = [
            r'class="[^"]*menu[^"]*"',
            r'id="[^"]*menu[^"]*"',
            r'<ul[^>]*class="[^"]*nav[^"]*"',
            r'dropdown-menu'
        ]
        return sum(len(re.findall(pattern, content, re.IGNORECASE)) for pattern in patterns)
    
    def _count_header_elements(self, content):
        """Count header elements"""
        patterns = [
            r'<header[^>]*>',
            r'class="[^"]*header[^"]*"',
            r'id="[^"]*header[^"]*"'
        ]
        return sum(len(re.findall(pattern, content, re.IGNORECASE)) for pattern in patterns)
    
    def _find_navigation_classes(self, content):
        """Find all navigation-related classes"""
        nav_classes = []
        class_matches = re.findall(r'class="([^"]*(?:nav|menu|header)[^"]*)"', content, re.IGNORECASE)
        nav_classes.extend(class_matches)
        return nav_classes
    
    def _find_footer_classes(self, content):
        """Find all footer-related classes"""
        footer_classes = []
        class_matches = re.findall(r'class="([^"]*footer[^"]*)"', content, re.IGNORECASE)
        footer_classes.extend(class_matches)
        return footer_classes
    
    def _find_content_outside_blocks(self, content):
        """Find HTML content outside template blocks in child templates"""
        lines = content.split('\n')
        outside_content = []
        
        in_block = False
        extends_line = None
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith('<!--'):
                continue
            
            # Find extends line
            if 'extends' in stripped and '{%' in stripped:
                extends_line = i
                continue
            
            # Track block boundaries
            if re.search(r'{%\s*block\s+\w+\s*%}', stripped):
                in_block = True
                continue
            
            if re.search(r'{%\s*endblock', stripped):
                in_block = False
                continue
            
            # If we're past extends and not in a block, check for HTML content
            if extends_line is not None and not in_block:
                if (stripped and not stripped.startswith('{%') and 
                    not stripped.startswith('{{') and
                    (re.search(r'<[^>]+>', stripped) or len(stripped) > 10)):
                    outside_content.append({
                        'line_number': i + 1,
                        'content': line,
                        'stripped': stripped
                    })
        
        return outside_content
    
    def _detect_template_issues(self, content, analysis):
        """Detect various template issues"""
        issues = []
        
        # Issue 1: Child template with structural HTML tags
        if analysis['extends_template'] and analysis['html_structure']['has_doctype']:
            issues.append('child_has_doctype')
        
        if analysis['extends_template'] and analysis['html_structure']['has_html_tag']:
            issues.append('child_has_html_tag')
        
        if analysis['extends_template'] and analysis['html_structure']['has_head_tag']:
            issues.append('child_has_head_tag')
        
        if analysis['extends_template'] and analysis['html_structure']['has_body_tag']:
            issues.append('child_has_body_tag')
        
        # Issue 2: Multiple navigation/footer elements
        if analysis['duplicate_indicators']['navbar_count'] > 3:
            issues.append('excessive_navbar_elements')
        
        if analysis['duplicate_indicators']['footer_count'] > 3:
            issues.append('excessive_footer_elements')
        
        # Issue 3: Content outside blocks in child templates
        if analysis['extends_template'] and analysis['content_outside_blocks']:
            issues.append('content_outside_blocks')
        
        # Issue 4: Mismatched blocks
        if len(analysis['blocks_defined']) != len(analysis['blocks_used']):
            issues.append('mismatched_blocks')
        
        # Issue 5: Extends not at beginning
        if analysis['extends_template']:
            first_line = content.split('\n')[0].strip()
            if 'extends' not in first_line:
                issues.append('extends_not_first_line')
        
        return issues
    
    def _analyze_template_inheritance(self):
        """Analyze template inheritance chain"""
        inheritance = {}
        
        for file_path, analysis in self.scan_results['files'].items():
            if 'error' in analysis:
                continue
                
            extends = analysis.get('extends_template')
            if extends:
                inheritance[file_path] = {
                    'extends': extends,
                    'blocks_defined': analysis['blocks_defined'],
                    'issues': analysis['template_issues']
                }
        
        self.scan_results['template_inheritance'] = inheritance
    
    def _detect_duplicate_content(self):
        """Detect duplicate content across templates"""
        duplicates = []
        
        for file_path, analysis in self.scan_results['files'].items():
            if 'error' in analysis:
                continue
            
            # Check for problematic patterns in child templates
            if analysis['extends_template']:
                indicators = analysis['duplicate_indicators']
                
                if indicators['navbar_count'] > 0:
                    duplicates.append({
                        'file': file_path,
                        'type': 'duplicate_navbar',
                        'count': indicators['navbar_count'],
                        'details': indicators['navigation_classes']
                    })
                
                if indicators['footer_count'] > 0:
                    duplicates.append({
                        'file': file_path,
                        'type': 'duplicate_footer', 
                        'count': indicators['footer_count'],
                        'details': indicators['footer_classes']
                    })
                
                if analysis['content_outside_blocks']:
                    duplicates.append({
                        'file': file_path,
                        'type': 'content_outside_blocks',
                        'count': len(analysis['content_outside_blocks']),
                        'details': [item['line_number'] for item in analysis['content_outside_blocks']]
                    })
        
        self.scan_results['duplicate_issues'] = duplicates
    
    def _analyze_block_structure(self):
        """Analyze block structure across templates"""
        block_analysis = {}
        
        # Find all blocks in base templates
        base_blocks = set()
        for file_path in self.scan_results['base_templates']:
            if file_path in self.scan_results['files']:
                analysis = self.scan_results['files'][file_path]
                base_blocks.update(analysis['blocks_defined'])
        
        # Analyze child template blocks
        for file_path, analysis in self.scan_results['files'].items():
            if 'error' in analysis or not analysis['extends_template']:
                continue
            
            block_analysis[file_path] = {
                'blocks_defined': analysis['blocks_defined'],
                'blocks_used': analysis['blocks_used'],
                'missing_endblocks': set(analysis['blocks_defined']) - set(analysis['blocks_used']),
                'unknown_blocks': set(analysis['blocks_defined']) - base_blocks
            }
        
        self.scan_results['block_structure'] = block_analysis
    
    def _print_detailed_report(self):
        """Print comprehensive analysis report"""
        print("\n" + "="*80)
        print("📊 COMPREHENSIVE HTML TEMPLATE ANALYSIS REPORT")
        print("="*80)
        
        # Overview
        print(f"\n📁 FILE OVERVIEW:")
        print(f"   Total HTML files: {len(self.scan_results['files'])}")
        print(f"   Base templates: {len(self.scan_results['base_templates'])}")
        print(f"   Child templates: {len(self.scan_results['child_templates'])}")
        print(f"   Duplicate issues: {len(self.scan_results['duplicate_issues'])}")
        
        # Base templates
        if self.scan_results['base_templates']:
            print(f"\n📄 BASE TEMPLATES:")
            for base_template in self.scan_results['base_templates']:
                analysis = self.scan_results['files'][base_template]
                print(f"   📄 {base_template}")
                print(f"      Lines: {analysis['line_count']}")
                print(f"      Blocks: {', '.join(analysis['blocks_defined']) if analysis['blocks_defined'] else 'None'}")
                print(f"      Structure: DOCTYPE={analysis['html_structure']['has_doctype']}, "
                      f"HTML={analysis['html_structure']['has_html_tag']}, "
                      f"HEAD={analysis['html_structure']['has_head_tag']}, "
                      f"BODY={analysis['html_structure']['has_body_tag']}")
        
        # Duplicate content issues
        if self.scan_results['duplicate_issues']:
            print(f"\n🔴 DUPLICATE CONTENT ISSUES:")
            for issue in self.scan_results['duplicate_issues']:
                print(f"   🔴 {issue['file']}")
                print(f"      Type: {issue['type']}")
                print(f"      Count: {issue['count']}")
                if issue['details']:
                    print(f"      Details: {issue['details']}")
        
        # Template inheritance issues
        if self.scan_results['template_inheritance']:
            print(f"\n🔗 TEMPLATE INHERITANCE:")
            for file_path, inheritance in self.scan_results['template_inheritance'].items():
                if inheritance['issues']:
                    print(f"   ⚠️  {file_path}")
                    print(f"      Extends: {inheritance['extends']}")
                    print(f"      Issues: {', '.join(inheritance['issues'])}")
        
        # Block structure issues
        if self.scan_results['block_structure']:
            print(f"\n🧱 BLOCK STRUCTURE ISSUES:")
            for file_path, blocks in self.scan_results['block_structure'].items():
                if blocks['missing_endblocks'] or blocks['unknown_blocks']:
                    print(f"   ⚠️  {file_path}")
                    if blocks['missing_endblocks']:
                        print(f"      Missing endblocks: {', '.join(blocks['missing_endblocks'])}")
                    if blocks['unknown_blocks']:
                        print(f"      Unknown blocks: {', '.join(blocks['unknown_blocks'])}")
        
        # Content outside blocks
        print(f"\n📝 CONTENT OUTSIDE BLOCKS:")
        for file_path, analysis in self.scan_results['files'].items():
            if 'error' not in analysis and analysis['content_outside_blocks']:
                print(f"   📄 {file_path}")
                for content in analysis['content_outside_blocks'][:5]:  # Show first 5
                    print(f"      Line {content['line_number']}: {content['stripped'][:60]}...")
                if len(analysis['content_outside_blocks']) > 5:
                    print(f"      ... and {len(analysis['content_outside_blocks']) - 5} more lines")
        
        # First few lines of problematic files
        print(f"\n🔍 PROBLEMATIC FILE CONTENT PREVIEW:")
        for issue in self.scan_results['duplicate_issues'][:3]:  # Show first 3 problematic files
            file_path = issue['file']
            if file_path in self.scan_results['files']:
                analysis = self.scan_results['files'][file_path]
                print(f"\n   📄 {file_path} (First 10 lines):")
                for i, line in enumerate(analysis['first_10_lines'], 1):
                    print(f"      {i:2}: {line}")
    
    def save_detailed_report(self, filename="html_scan_report.json"):
        """Save detailed scan results to JSON file"""
        with open(filename, 'w') as f:
            json.dump(self.scan_results, f, indent=2, default=str)
        print(f"\n💾 Detailed scan report saved to: {filename}")

def main():
    """Main function"""
    print("🔍 Comprehensive HTML Template Scanner")
    print("="*50)
    
    # Check if we're in the right directory
    if not os.path.exists('templates') and not list(Path('.').glob('**/*.html')):
        print("❌ No HTML files found!")
        return
    
    # Run comprehensive scan
    scanner = ComprehensiveHTMLScanner()
    results = scanner.full_scan()
    
    # Offer to save detailed report
    save_report = input(f"\n❓ Save detailed scan report to JSON? (y/N): ").strip().lower()
    if save_report == 'y':
        scanner.save_detailed_report()
    
    print(f"\n🎯 NEXT STEPS:")
    print(f"   1. Review the duplicate content issues above")
    print(f"   2. Check files with content outside blocks")
    print(f"   3. Fix template inheritance issues")
    print(f"   4. Use the detailed report to create targeted fixes")

if __name__ == '__main__':
    main()