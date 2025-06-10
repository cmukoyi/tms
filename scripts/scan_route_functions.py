#!/usr/bin/env python3
"""
Route Function Scanner
Scans existing route functions to identify issues before applying fixes
"""

import os
import ast
import re
from pathlib import Path

class RouteFunctionScanner:
    def __init__(self, project_root="."):
        self.project_root = Path(project_root)
        self.route_functions = []
        self.issues = []
        
    def scan_all_routes(self):
        """Scan all route functions and identify issues"""
        print("🔍 Scanning All Route Functions...")
        print("="*50)
        
        # Find route files
        route_files = list(self.project_root.glob("routes/**/*.py"))
        route_files.extend([f for f in self.project_root.glob("*.py") if 'app' in f.name])
        
        print(f"📁 Found {len(route_files)} Python files to scan")
        
        for route_file in route_files:
            if self._should_skip_file(route_file):
                continue
                
            print(f"\n📄 Scanning: {route_file}")
            try:
                self._scan_route_file(route_file)
            except Exception as e:
                print(f"❌ Error scanning {route_file}: {e}")
        
        # Print detailed analysis
        self._print_detailed_analysis()
        
        return self.route_functions, self.issues
    
    def _should_skip_file(self, file_path):
        """Skip certain files"""
        skip_patterns = ['__pycache__', '.git', 'venv', '.venv', 'test_', 'backup']
        return any(pattern in str(file_path) for pattern in skip_patterns)
    
    def _scan_route_file(self, route_file):
        """Scan individual route file"""
        with open(route_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            print(f"   ❌ Syntax error: {e}")
            return
        
        # Find route functions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if self._is_route_function(node, content):
                    route_info = self._analyze_route_function(node, content, route_file)
                    self.route_functions.append(route_info)
                    print(f"   📍 Found route: {node.name}() - {route_info['status']}")
                    
                    if route_info['issues']:
                        for issue in route_info['issues']:
                            print(f"      ⚠️  {issue}")
    
    def _is_route_function(self, node, content):
        """Check if function is a Flask route"""
        for decorator in node.decorator_list:
            decorator_str = ast.dump(decorator)
            if 'route' in decorator_str.lower():
                return True
        return False
    
    def _analyze_route_function(self, node, content, route_file):
        """Analyze individual route function"""
        lines = content.split('\n')
        func_start = node.lineno - 1
        func_end = getattr(node, 'end_lineno', len(lines))
        func_lines = lines[func_start:func_end]
        func_content = '\n'.join(func_lines)
        
        route_info = {
            'file': str(route_file),
            'name': node.name,
            'line': node.lineno,
            'content': func_content,
            'issues': [],
            'status': 'unknown',
            'decorators': [],
            'returns': [],
            'variables': [],
            'imports_used': []
        }
        
        # Extract decorators
        for decorator in node.decorator_list:
            route_info['decorators'].append(ast.dump(decorator))
        
        # Find return statements
        return_statements = re.findall(r'return\s+([^\n]+)', func_content)
        route_info['returns'] = return_statements
        
        # Find variable assignments
        var_assignments = re.findall(r'(\w+)\s*=\s*([^\n]+)', func_content)
        route_info['variables'] = var_assignments
        
        # Find model queries
        model_queries = re.findall(r'(\w+)\.query\.', func_content)
        route_info['model_queries'] = list(set(model_queries))
        
        # Check for issues
        issues = self._check_route_issues(route_info, func_content)
        route_info['issues'] = issues
        
        # Determine status
        if not issues:
            route_info['status'] = '✅ OK'
        elif any('missing return' in issue for issue in issues):
            route_info['status'] = '❌ No Return'
        elif any('undefined variable' in issue for issue in issues):
            route_info['status'] = '❌ Undefined Variable'
        elif any('no template context' in issue for issue in issues):
            route_info['status'] = '⚠️  Missing Context'
        else:
            route_info['status'] = '⚠️  Issues Found'
        
        return route_info
    
    def _check_route_issues(self, route_info, func_content):
        """Check for various issues in route function"""
        issues = []
        
        # Check 1: Missing return statement
        if not route_info['returns']:
            issues.append("Missing return statement")
        
        # Check 2: Return with undefined variables
        for return_stmt in route_info['returns']:
            if 'render_template' in return_stmt:
                # Extract variables passed to template
                template_vars = re.findall(r'(\w+)=\w+', return_stmt)
                for var in template_vars:
                    # Check if variable is defined in function
                    if not any(var in assignment[0] for assignment in route_info['variables']):
                        issues.append(f"Undefined variable '{var}' in return statement")
        
        # Check 3: Using model queries but not passing to template
        if route_info['model_queries'] and route_info['returns']:
            for return_stmt in route_info['returns']:
                if 'render_template' in return_stmt:
                    # Check if model data is passed to template
                    has_model_context = any(model.lower() in return_stmt.lower() 
                                          for model in route_info['model_queries'])
                    if not has_model_context:
                        issues.append("Model queries found but no template context passed")
        
        # Check 4: Return render_template without template file
        for return_stmt in route_info['returns']:
            if 'render_template' in return_stmt:
                template_match = re.search(r"render_template\(['\"]([^'\"]+)['\"]", return_stmt)
                if template_match:
                    template_path = template_match.group(1)
                    full_template_path = self.project_root / 'templates' / template_path
                    if not full_template_path.exists():
                        issues.append(f"Template '{template_path}' does not exist")
        
        return issues
    
    def _print_detailed_analysis(self):
        """Print detailed analysis of all route functions"""
        print("\n" + "="*80)
        print("📊 ROUTE FUNCTION ANALYSIS REPORT")
        print("="*80)
        
        # Summary statistics
        total_routes = len(self.route_functions)
        ok_routes = len([r for r in self.route_functions if r['status'] == '✅ OK'])
        problem_routes = total_routes - ok_routes
        
        print(f"\n📈 SUMMARY:")
        print(f"   Total route functions: {total_routes}")
        print(f"   Working correctly: {ok_routes}")
        print(f"   Have issues: {problem_routes}")
        
        # Group by status
        status_groups = {}
        for route in self.route_functions:
            status = route['status']
            if status not in status_groups:
                status_groups[status] = []
            status_groups[status].append(route)
        
        # Print by status
        for status, routes in status_groups.items():
            if status != '✅ OK':
                print(f"\n{status} ROUTES ({len(routes)}):")
                for route in routes:
                    print(f"   📄 {route['file']}:{route['line']} - {route['name']}()")
                    for issue in route['issues']:
                        print(f"      ⚠️  {issue}")
        
        # Show problematic functions in detail
        problem_functions = [r for r in self.route_functions if r['issues']]
        if problem_functions:
            print(f"\n🔍 DETAILED ANALYSIS OF PROBLEM FUNCTIONS:")
            
            for route in problem_functions[:5]:  # Show first 5 problem functions
                print(f"\n📄 {route['name']}() in {route['file']}:{route['line']}")
                print(f"   Status: {route['status']}")
                print(f"   Issues: {', '.join(route['issues'])}")
                print(f"   Variables: {route['variables'][:3]}...")  # Show first 3 variables
                print(f"   Returns: {route['returns']}")
                print(f"   Function preview:")
                func_lines = route['content'].split('\n')[:10]  # First 10 lines
                for i, line in enumerate(func_lines, route['line']):
                    print(f"      {i:3}: {line}")
                if len(route['content'].split('\n')) > 10:
                    print(f"      ... (truncated)")
        
        # Specific focus on the admin_companies function mentioned in error
        admin_companies_route = None
        for route in self.route_functions:
            if route['name'] == 'admin_companies':
                admin_companies_route = route
                break
        
        if admin_companies_route:
            print(f"\n🎯 SPECIFIC ANALYSIS: admin_companies() function")
            print(f"   File: {admin_companies_route['file']}:{admin_companies_route['line']}")
            print(f"   Status: {admin_companies_route['status']}")
            print(f"   Issues: {admin_companies_route['issues']}")
            print(f"   Variables defined: {admin_companies_route['variables']}")
            print(f"   Return statements: {admin_companies_route['returns']}")
            print(f"   Full function content:")
            for i, line in enumerate(admin_companies_route['content'].split('\n'), admin_companies_route['line']):
                print(f"      {i:3}: {line}")

def main():
    """Main function"""
    print("🔍 Route Function Scanner")
    print("="*30)
    
    scanner = RouteFunctionScanner()
    routes, issues = scanner.scan_all_routes()
    
    if issues:
        print(f"\n💡 RECOMMENDED ACTIONS:")
        print(f"   1. Fix undefined variables in return statements")
        print(f"   2. Add missing variable definitions")
        print(f"   3. Ensure template files exist")
        print(f"   4. Add proper database queries where needed")
    else:
        print(f"\n✅ All route functions look good!")

if __name__ == '__main__':
    main()