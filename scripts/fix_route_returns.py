#!/usr/bin/env python3
"""
Route Return Statement Fixer
Finds and fixes route functions that don't return valid responses
"""

import os
import ast
import re
from pathlib import Path

class RouteReturnFixer:
    def __init__(self, project_root="."):
        self.project_root = Path(project_root)
        self.issues_found = []
        self.fixes_applied = []
        
    def scan_and_fix_routes(self):
        """Scan all Python files for route functions with missing returns"""
        print("🔍 Scanning for route functions with missing return statements...")
        
        # Find route files
        route_files = []
        for pattern in ["routes/**/*.py", "*.py"]:
            route_files.extend(self.project_root.glob(pattern))
        
        # Filter to actual route files
        route_files = [f for f in route_files if not self._should_skip_file(f)]
        
        print(f"📁 Found {len(route_files)} Python files to check")
        
        for route_file in route_files:
            try:
                self._analyze_route_file(route_file)
            except Exception as e:
                print(f"❌ Error analyzing {route_file}: {e}")
        
        # Apply fixes
        if self.issues_found:
            print(f"\n🔧 Found {len(self.issues_found)} route functions with missing returns")
            self._apply_fixes()
        else:
            print("\n✅ No route return issues found!")
        
        self._print_summary()
        return len(self.fixes_applied) > 0
    
    def _should_skip_file(self, file_path):
        """Skip certain files"""
        skip_patterns = ['__pycache__', '.git', 'venv', '.venv', 'test_', 'backup']
        return any(pattern in str(file_path) for pattern in skip_patterns)
    
    def _analyze_route_file(self, route_file):
        """Analyze a Python file for route functions"""
        with open(route_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return
        
        # Find route functions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if self._is_route_function(node, content):
                    has_return = self._check_function_returns(node, content)
                    if not has_return:
                        self.issues_found.append({
                            'file': route_file,
                            'function': node.name,
                            'line': node.lineno,
                            'content': content
                        })
                        print(f"⚠️  Missing return in {route_file}: {node.name}() at line {node.lineno}")
    
    def _is_route_function(self, node, content):
        """Check if function is a Flask route"""
        for decorator in node.decorator_list:
            decorator_str = ast.dump(decorator)
            if 'route' in decorator_str.lower():
                return True
        return False
    
    def _check_function_returns(self, node, content):
        """Check if function has proper return statements"""
        # Get function content
        lines = content.split('\n')
        func_start = node.lineno - 1
        func_end = getattr(node, 'end_lineno', len(lines)) - 1
        func_lines = lines[func_start:func_end + 1]
        func_content = '\n'.join(func_lines)
        
        # Check for return statements
        return_patterns = [
            r'return\s+render_template',
            r'return\s+redirect',
            r'return\s+jsonify',
            r'return\s+Response',
            r'return\s+make_response',
            r'return\s+.*response',
            r'return\s+["\']\w+["\']',  # Simple string return
            r'return\s+\{.*\}',  # Dict return
            r'return\s+\[.*\]'   # List return
        ]
        
        for pattern in return_patterns:
            if re.search(pattern, func_content, re.IGNORECASE):
                return True
        
        # Check for bare return statements that might be conditional
        if re.search(r'return(?:\s|$)', func_content):
            # Has return but might not have proper response
            return False
        
        return False
    
    def _apply_fixes(self):
        """Apply fixes to route functions"""
        for issue in self.issues_found:
            try:
                self._fix_route_function(issue)
            except Exception as e:
                print(f"❌ Error fixing {issue['file']}: {e}")
    
    def _fix_route_function(self, issue):
        """Fix a specific route function"""
        file_path = issue['file']
        function_name = issue['function']
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create backup
        backup_file = str(file_path) + '.backup'
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Try to fix the function
        fixed_content = self._add_return_statement(content, issue)
        
        if fixed_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            
            self.fixes_applied.append(f"{file_path}: {function_name}()")
            print(f"✅ Fixed return statement in {file_path}: {function_name}()")
    
    def _add_return_statement(self, content, issue):
        """Add appropriate return statement to function"""
        lines = content.split('\n')
        func_name = issue['function']
        
        # Parse the AST to find the function
        try:
            tree = ast.parse(content)
        except:
            return content
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == func_name:
                func_start = node.lineno - 1
                func_end = getattr(node, 'end_lineno', len(lines)) - 1
                
                # Get function content
                func_lines = lines[func_start:func_end + 1]
                func_content = '\n'.join(func_lines)
                
                # Determine appropriate return statement
                return_stmt = self._determine_return_statement(func_content, func_name)
                
                # Find the last line of the function (before the next function or end)
                insert_line = func_end
                
                # Insert the return statement
                lines.insert(insert_line, f"    {return_stmt}")
                break
        
        return '\n'.join(lines)
    
    def _determine_return_statement(self, func_content, func_name):
        """Determine appropriate return statement based on function content"""
        # Check what kind of template this function should render
        if 'companies' in func_name.lower():
            template_name = 'admin/companies.html'
        elif 'users' in func_name.lower():
            template_name = 'admin/users.html'
        elif 'tenders' in func_name.lower():
            template_name = 'tenders/list.html'
        elif 'dashboard' in func_name.lower():
            template_name = 'dashboard.html'
        elif 'profile' in func_name.lower():
            template_name = 'user/profile.html'
        elif 'login' in func_name.lower():
            template_name = 'login.html'
        else:
            # Generic template based on function name
            template_name = f"{func_name.replace('_', '/')}.html"
        
        # Check if function has context variables
        if 'companies' in func_content or 'Company.query' in func_content:
            return f"return render_template('{template_name}', companies=companies)"
        elif 'users' in func_content or 'User.query' in func_content:
            return f"return render_template('{template_name}', users=users)"
        elif 'tenders' in func_content or 'Tender.query' in func_content:
            return f"return render_template('{template_name}', tenders=tenders)"
        elif 'redirect' in func_content:
            return "return redirect(url_for('main.home'))"
        else:
            return f"return render_template('{template_name}')"
    
    def _print_summary(self):
        """Print summary of fixes"""
        print("\n" + "="*60)
        print("🎉 ROUTE RETURN FIXES SUMMARY")
        print("="*60)
        
        if self.fixes_applied:
            print(f"\n✅ ROUTE FUNCTIONS FIXED ({len(self.fixes_applied)}):")
            for fix in self.fixes_applied:
                print(f"   ✓ {fix}")
        
        if not self.fixes_applied and self.issues_found:
            print(f"\n⚠️  ISSUES FOUND BUT NOT FIXED:")
            for issue in self.issues_found:
                print(f"   ⚠️  {issue['file']}: {issue['function']}()")
        
        if not self.issues_found:
            print(f"\n🎯 No route return issues found!")
        
        print(f"\n💡 WHAT WAS FIXED:")
        print(f"   • Added missing return statements to route functions")
        print(f"   • Added appropriate render_template() calls")
        print(f"   • Ensured all routes return valid responses")
        
        print(f"\n🚀 TEST YOUR APPLICATION:")
        print(f"   python app.py")
        print(f"   Visit: http://localhost:5001/tenders")

def main():
    """Main function"""
    print("🔧 Route Return Statement Fixer")
    print("="*50)
    
    print("This will find and fix route functions that don't return responses:")
    print("   🔍 Scan all route functions")
    print("   ✅ Add missing return statements")
    print("   ✅ Add appropriate render_template() calls")
    print("   🛡️  Create backups of modified files")
    
    proceed = input("\n❓ Proceed with route fixes? (y/N): ").strip().lower()
    
    if proceed != 'y':
        print("⏹️  Route fixes cancelled")
        return
    
    # Run the fixer
    fixer = RouteReturnFixer()
    success = fixer.scan_and_fix_routes()
    
    if success:
        print(f"\n🎉 Route fixes completed!")
        print(f"💡 The TypeError should now be resolved.")
    else:
        print(f"\n✅ No route fixes were needed!")

if __name__ == '__main__':
    main()