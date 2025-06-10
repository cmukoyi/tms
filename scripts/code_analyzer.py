#!/usr/bin/env python3
"""
TMS Code Analyzer & Optimizer
Scans your entire TMS project and suggests MVC optimizations
"""

import os
import ast
import re
import json
from collections import defaultdict, Counter
from pathlib import Path

class CodeAnalyzer:
    def __init__(self, project_root="."):
        self.project_root = Path(project_root)
        self.stats = {
            'files': {},
            'models': {},
            'views': {},
            'routes': {},
            'services': {},
            'utils': {},
            'templates': {},
            'issues': [],
            'suggestions': []
        }
        
    def scan_project(self):
        """Scan the entire project structure"""
        print("🔍 Scanning TMS project structure...")
        
        # Scan different types of files
        self._scan_python_files()
        self._scan_template_files()
        self._scan_static_files()
        self._analyze_architecture()
        self._generate_suggestions()
        
        return self.stats
    
    def _scan_python_files(self):
        """Scan all Python files"""
        python_files = list(self.project_root.glob("**/*.py"))
        
        for file_path in python_files:
            if self._should_skip_file(file_path):
                continue
                
            rel_path = file_path.relative_to(self.project_root)
            file_info = self._analyze_python_file(file_path)
            
            if file_info:
                self.stats['files'][str(rel_path)] = file_info
                self._categorize_file(rel_path, file_info)
    
    def _should_skip_file(self, file_path):
        """Skip certain files/directories"""
        skip_patterns = [
            '__pycache__', '.git', 'venv', '.venv', 'env',
            'migrations', '.pytest_cache', 'node_modules'
        ]
        
        for pattern in skip_patterns:
            if pattern in str(file_path):
                return True
        return False
    
    def _analyze_python_file(self, file_path):
        """Analyze a single Python file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Basic file info
            info = {
                'lines': len(content.splitlines()),
                'size_kb': len(content.encode('utf-8')) / 1024,
                'imports': [],
                'classes': [],
                'functions': [],
                'routes': [],
                'models': [],
                'complexity': 0,
                'type': 'unknown'
            }
            
            # Parse AST
            try:
                tree = ast.parse(content)
                self._analyze_ast(tree, info)
            except SyntaxError as e:
                info['syntax_error'] = str(e)
                return info
            
            # Analyze content patterns
            self._analyze_content_patterns(content, info)
            
            return info
            
        except Exception as e:
            return {'error': str(e)}
    
    def _analyze_ast(self, tree, info):
        """Analyze the AST of a Python file"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    info['imports'].append(alias.name)
            
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    info['imports'].append(f"{module}.{alias.name}")
            
            elif isinstance(node, ast.ClassDef):
                class_info = {
                    'name': node.name,
                    'methods': [n.name for n in node.body if isinstance(n, ast.FunctionDef)],
                    'lines': getattr(node, 'end_lineno', 0) - getattr(node, 'lineno', 0)
                }
                info['classes'].append(class_info)
                
                # Check if it's a model
                if self._is_model_class(node):
                    info['models'].append(node.name)
            
            elif isinstance(node, ast.FunctionDef):
                func_info = {
                    'name': node.name,
                    'args': len(node.args.args),
                    'lines': getattr(node, 'end_lineno', 0) - getattr(node, 'lineno', 0),
                    'decorators': [self._get_decorator_name(d) for d in node.decorator_list]
                }
                info['functions'].append(func_info)
                
                # Check if it's a route
                if self._is_route_function(node):
                    info['routes'].append(func_info)
            
            # Complexity calculation (simplified)
            elif isinstance(node, (ast.If, ast.For, ast.While, ast.Try)):
                info['complexity'] += 1
    
    def _analyze_content_patterns(self, content, info):
        """Analyze content patterns"""
        # Count Flask patterns
        flask_patterns = {
            'app.route': len(re.findall(r'@app\.route', content)),
            'bp.route': len(re.findall(r'@\w+_bp\.route', content)),
            'render_template': len(re.findall(r'render_template', content)),
            'redirect': len(re.findall(r'redirect\(', content)),
            'url_for': len(re.findall(r'url_for\(', content)),
            'db.session': len(re.findall(r'db\.session', content)),
            'db.Model': len(re.findall(r'db\.Model', content)),
            'Blueprint': len(re.findall(r'Blueprint\(', content))
        }
        
        info['flask_patterns'] = flask_patterns
        
        # Determine file type based on patterns
        info['type'] = self._determine_file_type(info, content)
    
    def _determine_file_type(self, info, content):
        """Determine the type of Python file"""
        patterns = info.get('flask_patterns', {})
        
        if info['models']:
            return 'model'
        elif patterns.get('bp.route', 0) > 0 or patterns.get('app.route', 0) > 0:
            return 'route'
        elif 'service' in str(info).lower() or any('Service' in cls['name'] for cls in info['classes']):
            return 'service'
        elif 'Blueprint' in content:
            return 'blueprint'
        elif any(word in content.lower() for word in ['decorator', 'helper', 'util']):
            return 'utility'
        elif 'config' in content.lower():
            return 'config'
        elif content.startswith('#!/usr/bin/env python') or 'if __name__ == "__main__"' in content:
            return 'script'
        else:
            return 'unknown'
    
    def _is_model_class(self, node):
        """Check if a class is a database model"""
        # Check if it inherits from db.Model or similar
        for base in node.bases:
            if isinstance(base, ast.Attribute):
                if base.attr == 'Model':
                    return True
            elif isinstance(base, ast.Name):
                if 'Model' in base.id:
                    return True
        return False
    
    def _is_route_function(self, node):
        """Check if a function is a Flask route"""
        for decorator in node.decorator_list:
            decorator_name = self._get_decorator_name(decorator)
            if 'route' in decorator_name or 'bp.route' in decorator_name:
                return True
        return False
    
    def _get_decorator_name(self, decorator):
        """Get the name of a decorator"""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return f"{self._get_decorator_name(decorator.value)}.{decorator.attr}"
        elif isinstance(decorator, ast.Call):
            return self._get_decorator_name(decorator.func)
        return 'unknown'
    
    def _categorize_file(self, rel_path, file_info):
        """Categorize files into different types"""
        file_type = file_info.get('type', 'unknown')
        path_str = str(rel_path)
        
        if file_type == 'model':
            self.stats['models'][path_str] = file_info
        elif file_type in ['route', 'blueprint']:
            self.stats['routes'][path_str] = file_info
        elif file_type == 'service':
            self.stats['services'][path_str] = file_info
        elif file_type == 'utility':
            self.stats['utils'][path_str] = file_info
    
    def _scan_template_files(self):
        """Scan template files"""
        template_files = list(self.project_root.glob("templates/**/*.html"))
        
        for template_file in template_files:
            rel_path = template_file.relative_to(self.project_root)
            
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                info = {
                    'lines': len(content.splitlines()),
                    'size_kb': len(content.encode('utf-8')) / 1024,
                    'url_for_count': len(re.findall(r'url_for\(', content)),
                    'form_count': len(re.findall(r'<form', content)),
                    'extends': bool(re.search(r'{%\s*extends', content)),
                    'blocks': len(re.findall(r'{%\s*block', content)),
                    'includes': len(re.findall(r'{%\s*include', content))
                }
                
                self.stats['templates'][str(rel_path)] = info
                
            except Exception as e:
                self.stats['templates'][str(rel_path)] = {'error': str(e)}
    
    def _scan_static_files(self):
        """Scan static files"""
        static_files = []
        for ext in ['*.css', '*.js', '*.png', '*.jpg', '*.jpeg', '*.gif', '*.svg']:
            static_files.extend(self.project_root.glob(f"static/**/{ext}"))
        
        total_size = sum(f.stat().st_size for f in static_files if f.exists()) / 1024  # KB
        
        self.stats['static'] = {
            'file_count': len(static_files),
            'total_size_kb': total_size,
            'by_type': Counter(f.suffix for f in static_files)
        }
    
    def _analyze_architecture(self):
        """Analyze overall architecture"""
        issues = []
        
        # Check for large files
        for file_path, info in self.stats['files'].items():
            if info.get('lines', 0) > 500:
                issues.append({
                    'type': 'large_file',
                    'file': file_path,
                    'lines': info['lines'],
                    'severity': 'high' if info['lines'] > 1000 else 'medium'
                })
        
        # Check for complex functions
        for file_path, info in self.stats['files'].items():
            for func in info.get('functions', []):
                if func.get('lines', 0) > 50:
                    issues.append({
                        'type': 'large_function',
                        'file': file_path,
                        'function': func['name'],
                        'lines': func['lines'],
                        'severity': 'medium'
                    })
        
        # Check for models in wrong places
        for file_path, info in self.stats['files'].items():
            if info.get('models') and not file_path.startswith('models'):
                issues.append({
                    'type': 'model_location',
                    'file': file_path,
                    'models': info['models'],
                    'severity': 'medium'
                })
        
        # Check for routes in wrong places
        for file_path, info in self.stats['files'].items():
            if info.get('routes') and not any(keyword in file_path for keyword in ['route', 'view', 'app.py']):
                issues.append({
                    'type': 'route_location',
                    'file': file_path,
                    'routes': len(info['routes']),
                    'severity': 'medium'
                })
        
        self.stats['issues'] = issues
    
    def _generate_suggestions(self):
        """Generate optimization suggestions"""
        suggestions = []
        
        # Model organization suggestions
        model_files = [f for f, info in self.stats['files'].items() if info.get('models')]
        if len(model_files) > 1:
            suggestions.append({
                'type': 'model_organization',
                'title': 'Consolidate Model Files',
                'description': f'You have models in {len(model_files)} files. Consider organizing them better.',
                'files': model_files,
                'action': 'Move all models to models/ directory with logical separation'
            })
        
        # Route organization suggestions
        route_files = [f for f, info in self.stats['files'].items() if info.get('routes')]
        total_routes = sum(len(info.get('routes', [])) for info in self.stats['files'].values())
        
        if len(route_files) == 1 and total_routes > 20:
            suggestions.append({
                'type': 'route_organization',
                'title': 'Split Routes into Blueprints',
                'description': f'You have {total_routes} routes in one file. Consider splitting into blueprints.',
                'action': 'Create separate blueprint files for different features'
            })
        
        # Service layer suggestions
        service_files = [f for f, info in self.stats['files'].items() if info.get('type') == 'service']
        if len(service_files) < 3:
            suggestions.append({
                'type': 'service_layer',
                'title': 'Add Service Layer',
                'description': 'Consider adding more service classes to separate business logic from routes.',
                'action': 'Create service classes for complex business operations'
            })
        
        # Template organization
        template_count = len(self.stats['templates'])
        if template_count > 20:
            flat_templates = [t for t in self.stats['templates'].keys() if '/' not in t.replace('templates/', '')]
            if len(flat_templates) > 10:
                suggestions.append({
                    'type': 'template_organization',
                    'title': 'Organize Templates in Subdirectories',
                    'description': f'You have {len(flat_templates)} templates in the root. Consider organizing by feature.',
                    'action': 'Create subdirectories like admin/, auth/, tenders/ etc.'
                })
        
        # Large file suggestions
        large_files = [issue for issue in self.stats['issues'] if issue['type'] == 'large_file']
        if large_files:
            suggestions.append({
                'type': 'file_size',
                'title': 'Break Down Large Files',
                'description': f'You have {len(large_files)} files over 500 lines.',
                'files': [issue['file'] for issue in large_files],
                'action': 'Split large files into smaller, focused modules'
            })
        
        self.stats['suggestions'] = suggestions

def print_analysis_report(stats):
    """Print a comprehensive analysis report"""
    print("\n" + "="*60)
    print("📊 TMS PROJECT ANALYSIS REPORT")
    print("="*60)
    
    # Project Overview
    print(f"\n📁 PROJECT OVERVIEW")
    print(f"   Python files: {len(stats['files'])}")
    print(f"   Template files: {len(stats['templates'])}")
    print(f"   Static files: {stats['static']['file_count']}")
    print(f"   Total static size: {stats['static']['total_size_kb']:.1f} KB")
    
    # Code Distribution
    print(f"\n🏗️  CODE DISTRIBUTION")
    type_counts = Counter(info.get('type', 'unknown') for info in stats['files'].values())
    for file_type, count in type_counts.most_common():
        print(f"   {file_type.title()}: {count} files")
    
    # Models Analysis
    if stats['models']:
        print(f"\n📦 MODELS ANALYSIS")
        total_models = sum(len(info.get('models', [])) for info in stats['models'].values())
        print(f"   Total models: {total_models}")
        print(f"   Model files: {len(stats['models'])}")
        
        for file_path, info in stats['models'].items():
            print(f"   📄 {file_path}: {len(info.get('models', []))} models")
    
    # Routes Analysis
    if stats['routes']:
        print(f"\n🛣️  ROUTES ANALYSIS")
        total_routes = sum(len(info.get('routes', [])) for info in stats['routes'].values())
        print(f"   Total routes: {total_routes}")
        print(f"   Route files: {len(stats['routes'])}")
        
        for file_path, info in stats['routes'].items():
            routes_count = len(info.get('routes', []))
            print(f"   📄 {file_path}: {routes_count} routes ({info.get('lines', 0)} lines)")
    
    # Services Analysis
    if stats['services']:
        print(f"\n⚙️  SERVICES ANALYSIS")
        print(f"   Service files: {len(stats['services'])}")
        
        for file_path, info in stats['services'].items():
            classes_count = len(info.get('classes', []))
            print(f"   📄 {file_path}: {classes_count} classes")
    
    # Issues
    if stats['issues']:
        print(f"\n⚠️  ISSUES FOUND")
        
        issue_counts = Counter(issue['type'] for issue in stats['issues'])
        for issue_type, count in issue_counts.items():
            print(f"   {issue_type.replace('_', ' ').title()}: {count}")
        
        # Show high severity issues
        high_issues = [issue for issue in stats['issues'] if issue.get('severity') == 'high']
        if high_issues:
            print(f"\n   🔴 HIGH PRIORITY ISSUES:")
            for issue in high_issues[:5]:  # Show first 5
                if issue['type'] == 'large_file':
                    print(f"      📄 {issue['file']}: {issue['lines']} lines")
    
    # Suggestions
    if stats['suggestions']:
        print(f"\n💡 OPTIMIZATION SUGGESTIONS")
        
        for i, suggestion in enumerate(stats['suggestions'], 1):
            print(f"\n   {i}. {suggestion['title']}")
            print(f"      {suggestion['description']}")
            print(f"      Action: {suggestion['action']}")
            
            if 'files' in suggestion:
                print(f"      Files affected: {len(suggestion['files'])}")

def generate_restructure_plan(stats):
    """Generate a detailed restructuring plan"""
    plan = {
        'current_structure': {},
        'recommended_structure': {},
        'migration_steps': []
    }
    
    # Analyze current structure
    current_dirs = set()
    for file_path in stats['files'].keys():
        dir_path = '/'.join(file_path.split('/')[:-1]) if '/' in file_path else 'root'
        current_dirs.add(dir_path)
    
    plan['current_structure'] = {
        'directories': list(current_dirs),
        'total_files': len(stats['files']),
        'largest_files': sorted(
            [(f, info.get('lines', 0)) for f, info in stats['files'].items()],
            key=lambda x: x[1], reverse=True
        )[:5]
    }
    
    # Recommended structure
    plan['recommended_structure'] = {
        'models/': {
            'description': 'All database models',
            'files': ['__init__.py', 'user.py', 'company.py', 'tender.py', 'document.py'],
            'current_files': list(stats['models'].keys())
        },
        'routes/': {
            'description': 'Blueprint route definitions',
            'files': ['__init__.py', 'auth.py', 'admin.py', 'tenders.py', 'reports.py', 'users.py'],
            'current_files': list(stats['routes'].keys())
        },
        'services/': {
            'description': 'Business logic services',
            'files': ['__init__.py', 'auth_service.py', 'tender_service.py', 'company_service.py'],
            'current_files': list(stats['services'].keys())
        },
        'utils/': {
            'description': 'Utility functions and helpers',
            'files': ['__init__.py', 'decorators.py', 'helpers.py', 'validators.py'],
            'current_files': list(stats['utils'].keys())
        },
        'templates/': {
            'description': 'Jinja2 templates organized by feature',
            'subdirs': ['auth/', 'admin/', 'tenders/', 'reports/', 'users/'],
            'current_count': len(stats['templates'])
        }
    }
    
    # Migration steps
    steps = []
    
    # Step 1: Backup
    steps.append({
        'step': 1,
        'title': 'Create Backup',
        'description': 'Backup current codebase',
        'commands': ['cp -r . ../tms_backup_$(date +%Y%m%d)']
    })
    
    # Step 2: Models
    if len(stats['models']) > 1:
        steps.append({
            'step': 2,
            'title': 'Consolidate Models',
            'description': 'Move all models to models/ directory',
            'commands': [
                'mkdir -p models',
                'Create models/__init__.py with proper imports',
                'Split large model files by entity type'
            ]
        })
    
    # Step 3: Services
    if len(stats['services']) < 3:
        steps.append({
            'step': 3,
            'title': 'Create Service Layer',
            'description': 'Extract business logic into service classes',
            'commands': [
                'mkdir -p services',
                'Create service classes for each major feature',
                'Move business logic from routes to services'
            ]
        })
    
    # Step 4: Routes
    route_count = sum(len(info.get('routes', [])) for info in stats['files'].values())
    if route_count > 20:
        steps.append({
            'step': 4,
            'title': 'Split Routes into Blueprints',
            'description': 'Organize routes by feature',
            'commands': [
                'mkdir -p routes',
                'Create blueprint files for each feature area',
                'Update app.py to register blueprints'
            ]
        })
    
    # Step 5: Templates
    flat_templates = [t for t in stats['templates'].keys() if '/' not in t.replace('templates/', '')]
    if len(flat_templates) > 10:
        steps.append({
            'step': 5,
            'title': 'Organize Templates',
            'description': 'Group templates by feature',
            'commands': [
                'mkdir -p templates/{auth,admin,tenders,reports,users}',
                'Move templates to appropriate subdirectories',
                'Update template references in routes'
            ]
        })
    
    plan['migration_steps'] = steps
    
    return plan

def save_analysis_json(stats, filename="tms_analysis.json"):
    """Save analysis to JSON file"""
    # Convert to JSON-serializable format
    json_stats = json.loads(json.dumps(stats, default=str))
    
    with open(filename, 'w') as f:
        json.dump(json_stats, f, indent=2)
    
    print(f"\n💾 Analysis saved to {filename}")

def main():
    """Main function"""
    print("🔧 TMS Code Analyzer & Optimizer")
    print("="*50)
    
    # Check if we're in the right directory
    if not os.path.exists('app.py') and not os.path.exists('models'):
        print("❌ This doesn't look like a TMS project directory!")
        print("   Make sure you're in the project root with app.py")
        return
    
    # Analyze the project
    analyzer = CodeAnalyzer()
    stats = analyzer.scan_project()
    
    # Print report
    print_analysis_report(stats)
    
    # Generate restructure plan
    plan = generate_restructure_plan(stats)
    
    print(f"\n🏗️  RESTRUCTURING PLAN")
    print("="*30)
    
    print(f"\n📁 Recommended Directory Structure:")
    for dir_name, dir_info in plan['recommended_structure'].items():
        print(f"   {dir_name}")
        print(f"      {dir_info['description']}")
        if 'current_files' in dir_info and dir_info['current_files']:
            print(f"      Current files: {len(dir_info['current_files'])}")
    
    print(f"\n📋 Migration Steps:")
    for step in plan['migration_steps']:
        print(f"\n   Step {step['step']}: {step['title']}")
        print(f"      {step['description']}")
    
    # Ask if user wants detailed JSON
    save_json = input(f"\n❓ Save detailed analysis to JSON file? (y/N): ").strip().lower()
    if save_json == 'y':
        save_analysis_json(stats)
    
    print(f"\n🎉 Analysis complete!")
    print(f"💡 Use this information to plan your code optimization.")

if __name__ == '__main__':
    main()