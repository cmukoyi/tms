#!/usr/bin/env python3
"""
MVC Structure Optimizer for TMS
Provides specific recommendations for Flask MVC architecture
"""

import os
import ast
import json
from pathlib import Path
from collections import defaultdict

class MVCOptimizer:
    def __init__(self, project_root="."):
        self.project_root = Path(project_root)
        self.mvc_analysis = {
            'models': {'current': [], 'issues': [], 'recommendations': []},
            'views': {'current': [], 'issues': [], 'recommendations': []},
            'controllers': {'current': [], 'issues': [], 'recommendations': []},
            'services': {'current': [], 'issues': [], 'recommendations': []},
            'overall': {'score': 0, 'recommendations': []}
        }
    
    def analyze_mvc_structure(self):
        """Analyze current MVC structure"""
        print("🏗️  Analyzing MVC Architecture...")
        
        self._analyze_models()
        self._analyze_views()
        self._analyze_controllers()
        self._analyze_services()
        self._calculate_mvc_score()
        self._generate_overall_recommendations()
        
        return self.mvc_analysis
    
    def _analyze_models(self):
        """Analyze Model layer"""
        models_info = {
            'files': [],
            'classes': [],
            'relationships': [],
            'issues': []
        }
        
        # Find model files
        model_patterns = ['models.py', 'models/', 'model.py']
        
        for pattern in model_patterns:
            pattern_path = self.project_root / pattern
            if pattern_path.exists():
                if pattern_path.is_file():
                    models_info['files'].append(str(pattern_path))
                    self._analyze_model_file(pattern_path, models_info)
                elif pattern_path.is_dir():
                    for model_file in pattern_path.glob('*.py'):
                        models_info['files'].append(str(model_file))
                        self._analyze_model_file(model_file, models_info)
        
        # Analyze model quality
        self._analyze_model_quality(models_info)
        
        self.mvc_analysis['models']['current'] = models_info
    
    def _analyze_model_file(self, file_path, models_info):
        """Analyze individual model file"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it's a database model
                    if self._is_db_model(node, content):
                        model_info = {
                            'name': node.name,
                            'file': str(file_path),
                            'methods': [n.name for n in node.body if isinstance(n, ast.FunctionDef)],
                            'properties': self._extract_model_properties(node, content),
                            'relationships': self._extract_relationships(node, content)
                        }
                        models_info['classes'].append(model_info)
                        models_info['relationships'].extend(model_info['relationships'])
        
        except Exception as e:
            models_info['issues'].append(f"Error analyzing {file_path}: {str(e)}")
    
    def _is_db_model(self, node, content):
        """Check if class is a database model"""
        # Check inheritance
        for base in node.bases:
            if isinstance(base, ast.Attribute) and base.attr == 'Model':
                return True
            elif isinstance(base, ast.Name) and 'Model' in base.id:
                return True
        
        # Check for database columns
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        if 'db.Column' in content or 'Column(' in content:
                            return True
        
        return False
    
    def _extract_model_properties(self, node, content):
        """Extract model properties and columns"""
        properties = []
        
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        # Check if it's a database column
                        if any(keyword in ast.dump(item.value) for keyword in ['Column', 'relationship']):
                            properties.append({
                                'name': target.id,
                                'type': self._infer_column_type(item.value)
                            })
        
        return properties
    
    def _infer_column_type(self, value_node):
        """Infer column type from AST node"""
        dump = ast.dump(value_node)
        if 'Integer' in dump:
            return 'Integer'
        elif 'String' in dump:
            return 'String'
        elif 'Text' in dump:
            return 'Text'
        elif 'DateTime' in dump:
            return 'DateTime'
        elif 'Boolean' in dump:
            return 'Boolean'
        elif 'relationship' in dump:
            return 'Relationship'
        else:
            return 'Unknown'
    
    def _extract_relationships(self, node, content):
        """Extract model relationships"""
        relationships = []
        
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        if 'relationship' in ast.dump(item.value):
                            relationships.append({
                                'name': target.id,
                                'type': 'relationship',
                                'model': node.name
                            })
        
        return relationships
    
    def _analyze_model_quality(self, models_info):
        """Analyze model layer quality"""
        issues = []
        recommendations = []
        
        # Check for large model files
        for file_path in models_info['files']:
            try:
                with open(file_path, 'r') as f:
                    lines = len(f.readlines())
                if lines > 500:
                    issues.append(f"Large model file: {file_path} ({lines} lines)")
                    recommendations.append(f"Split {file_path} into separate model files by entity")
            except:
                pass
        
        # Check for missing relationships
        model_names = [model['name'] for model in models_info['classes']]
        foreign_keys = []
        
        for model in models_info['classes']:
            for prop in model['properties']:
                if 'ForeignKey' in str(prop):
                    foreign_keys.append(prop['name'])
        
        if len(foreign_keys) > len(models_info['relationships']):
            issues.append("Some foreign keys might be missing corresponding relationships")
            recommendations.append("Review model relationships and add missing relationship definitions")
        
        # Check for models without proper methods
        for model in models_info['classes']:
            if len(model['methods']) < 2:  # Should have at least __repr__ and one other
                issues.append(f"Model {model['name']} has few methods")
                recommendations.append(f"Add __repr__, __str__, and business logic methods to {model['name']}")
        
        models_info['issues'] = issues
        self.mvc_analysis['models']['recommendations'] = recommendations
    
    def _analyze_views(self):
        """Analyze View layer (Templates)"""
        views_info = {
            'templates': [],
            'structure': {},
            'issues': []
        }
        
        templates_dir = self.project_root / 'templates'
        if not templates_dir.exists():
            views_info['issues'].append("No templates directory found")
            self.mvc_analysis['views']['current'] = views_info
            return
        
        # Analyze template structure
        template_files = list(templates_dir.glob('**/*.html'))
        
        for template_file in template_files:
            rel_path = template_file.relative_to(templates_dir)
            
            try:
                with open(template_file, 'r') as f:
                    content = f.read()
                
                template_info = {
                    'path': str(rel_path),
                    'full_path': str(template_file),
                    'size': len(content),
                    'lines': len(content.splitlines()),
                    'extends': self._check_template_extends(content),
                    'blocks': self._count_template_blocks(content),
                    'forms': self._count_template_forms(content),
                    'url_fors': self._count_url_fors(content),
                    'includes': self._count_template_includes(content)
                }
                
                views_info['templates'].append(template_info)
                
            except Exception as e:
                views_info['issues'].append(f"Error analyzing template {rel_path}: {str(e)}")
        
        # Analyze template organization
        self._analyze_template_organization(views_info)
        
        self.mvc_analysis['views']['current'] = views_info
    
    def _check_template_extends(self, content):
        """Check if template extends a base template"""
        import re
        return bool(re.search(r'{%\s*extends\s+["\']([^"\']+)["\']', content))
    
    def _count_template_blocks(self, content):
        """Count template blocks"""
        import re
        return len(re.findall(r'{%\s*block\s+\w+\s*%}', content))
    
    def _count_template_forms(self, content):
        """Count HTML forms in template"""
        import re
        return len(re.findall(r'<form[^>]*>', content))
    
    def _count_url_fors(self, content):
        """Count url_for() calls in template"""
        import re
        return len(re.findall(r'url_for\s*\(', content))
    
    def _count_template_includes(self, content):
        """Count template includes"""
        import re
        return len(re.findall(r'{%\s*include\s+["\']([^"\']+)["\']', content))
    
    def _analyze_template_organization(self, views_info):
        """Analyze template organization"""
        issues = []
        recommendations = []
        
        # Check for flat template structure
        root_templates = [t for t in views_info['templates'] if '/' not in t['path']]
        if len(root_templates) > 10:
            issues.append(f"Too many templates in root directory: {len(root_templates)}")
            recommendations.append("Organize templates into feature-based subdirectories (auth/, admin/, etc.)")
        
        # Check for large templates
        large_templates = [t for t in views_info['templates'] if t['lines'] > 200]
        if large_templates:
            issues.append(f"Large templates found: {len(large_templates)}")
            recommendations.append("Break down large templates into smaller, reusable components")
        
        # Check for templates without base extension
        no_extends = [t for t in views_info['templates'] if not t['extends'] and t['lines'] > 20]
        if no_extends:
            issues.append(f"Templates without base extension: {len(no_extends)}")
            recommendations.append("Ensure all major templates extend a base template for consistency")
        
        views_info['issues'] = issues
        self.mvc_analysis['views']['recommendations'] = recommendations
    
    def _analyze_controllers(self):
        """Analyze Controller layer (Routes/Views)"""
        controllers_info = {
            'files': [],
            'routes': [],
            'blueprints': [],
            'issues': []
        }
        
        # Find route files
        python_files = list(self.project_root.glob('**/*.py'))
        
        for py_file in python_files:
            if self._should_skip_file(py_file):
                continue
            
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                
                # Check if file contains routes
                if '@app.route' in content or '@' in content and '.route' in content:
                    controller_info = self._analyze_controller_file(py_file, content)
                    if controller_info['routes'] or controller_info['blueprints']:
                        controllers_info['files'].append(str(py_file))
                        controllers_info['routes'].extend(controller_info['routes'])
                        controllers_info['blueprints'].extend(controller_info['blueprints'])
            
            except Exception as e:
                controllers_info['issues'].append(f"Error analyzing {py_file}: {str(e)}")
        
        # Analyze controller quality
        self._analyze_controller_quality(controllers_info)
        
        self.mvc_analysis['controllers']['current'] = controllers_info
    
    def _analyze_controller_file(self, file_path, content):
        """Analyze individual controller file"""
        controller_info = {
            'routes': [],
            'blueprints': [],
            'functions': []
        }
        
        try:
            tree = ast.parse(content)
            
            # Find blueprints
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if (isinstance(node.func, ast.Name) and node.func.id == 'Blueprint') or \
                       (isinstance(node.func, ast.Attribute) and node.func.attr == 'Blueprint'):
                        if node.args:
                            blueprint_name = ast.literal_eval(node.args[0]) if isinstance(node.args[0], ast.Constant) else 'unknown'
                            controller_info['blueprints'].append({
                                'name': blueprint_name,
                                'file': str(file_path)
                            })
            
            # Find route functions
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    route_info = self._analyze_route_function(node, content)
                    if route_info:
                        route_info['file'] = str(file_path)
                        controller_info['routes'].append(route_info)
                        controller_info['functions'].append({
                            'name': node.name,
                            'lines': getattr(node, 'end_lineno', 0) - getattr(node, 'lineno', 0),
                            'args': len(node.args.args)
                        })
        
        except Exception as e:
            pass
        
        return controller_info
    
    def _analyze_route_function(self, node, content):
        """Analyze a route function"""
        # Check if function has route decorator
        has_route = False
        route_methods = []
        route_path = None
        
        for decorator in node.decorator_list:
            decorator_str = ast.dump(decorator)
            if 'route' in decorator_str:
                has_route = True
                # Try to extract route path and methods
                if hasattr(decorator, 'args') and decorator.args:
                    if isinstance(decorator.args[0], ast.Constant):
                        route_path = decorator.args[0].value
                
                # Extract methods if specified
                if hasattr(decorator, 'keywords'):
                    for keyword in decorator.keywords:
                        if keyword.arg == 'methods' and isinstance(keyword.value, ast.List):
                            route_methods = [elt.value for elt in keyword.value if isinstance(elt, ast.Constant)]
        
        if has_route:
            return {
                'name': node.name,
                'path': route_path,
                'methods': route_methods or ['GET'],
                'lines': getattr(node, 'end_lineno', 0) - getattr(node, 'lineno', 0),
                'complexity': self._calculate_function_complexity(node)
            }
        
        return None
    
    def _calculate_function_complexity(self, node):
        """Calculate cyclomatic complexity of a function"""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        return complexity
    
    def _analyze_controller_quality(self, controllers_info):
        """Analyze controller layer quality"""
        issues = []
        recommendations = []
        
        # Check for large route functions
        large_routes = [r for r in controllers_info['routes'] if r.get('lines', 0) > 50]
        if large_routes:
            issues.append(f"Large route functions found: {len(large_routes)}")
            recommendations.append("Break down large route functions into smaller functions or move logic to services")
        
        # Check for complex routes
        complex_routes = [r for r in controllers_info['routes'] if r.get('complexity', 0) > 10]
        if complex_routes:
            issues.append(f"Complex route functions found: {len(complex_routes)}")
            recommendations.append("Simplify complex route functions by extracting business logic to services")
        
        # Check for missing blueprints
        total_routes = len(controllers_info['routes'])
        total_blueprints = len(controllers_info['blueprints'])
        
        if total_routes > 20 and total_blueprints < 3:
            issues.append("Too many routes without proper blueprint organization")
            recommendations.append("Organize routes into feature-based blueprints")
        
        # Check for routes in main app file
        app_file_routes = [r for r in controllers_info['routes'] if 'app.py' in r.get('file', '')]
        if len(app_file_routes) > 5:
            issues.append("Too many routes in main app.py file")
            recommendations.append("Move routes from app.py to separate blueprint files")
        
        controllers_info['issues'] = issues
        self.mvc_analysis['controllers']['recommendations'] = recommendations
    
    def _analyze_services(self):
        """Analyze Service layer"""
        services_info = {
            'files': [],
            'classes': [],
            'issues': []
        }
        
        # Find service files
        service_patterns = ['services/', 'service.py', '*service*.py']
        
        for pattern in service_patterns:
            if pattern.endswith('/'):
                service_dir = self.project_root / pattern.rstrip('/')
                if service_dir.exists() and service_dir.is_dir():
                    for service_file in service_dir.glob('*.py'):
                        services_info['files'].append(str(service_file))
                        self._analyze_service_file(service_file, services_info)
            else:
                service_files = list(self.project_root.glob(f'**/{pattern}'))
                for service_file in service_files:
                    if self._should_skip_file(service_file):
                        continue
                    services_info['files'].append(str(service_file))
                    self._analyze_service_file(service_file, services_info)
        
        # Analyze service quality
        self._analyze_service_quality(services_info)
        
        self.mvc_analysis['services']['current'] = services_info
    
    def _analyze_service_file(self, file_path, services_info):
        """Analyze individual service file"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    if 'Service' in node.name or 'service' in str(file_path).lower():
                        service_info = {
                            'name': node.name,
                            'file': str(file_path),
                            'methods': [n.name for n in node.body if isinstance(n, ast.FunctionDef)],
                            'static_methods': [n.name for n in node.body 
                                             if isinstance(n, ast.FunctionDef) and 
                                             any(isinstance(d, ast.Name) and d.id == 'staticmethod' 
                                                 for d in n.decorator_list)],
                            'class_methods': [n.name for n in node.body 
                                            if isinstance(n, ast.FunctionDef) and 
                                            any(isinstance(d, ast.Name) and d.id == 'classmethod' 
                                                for d in n.decorator_list)]
                        }
                        services_info['classes'].append(service_info)
        
        except Exception as e:
            services_info['issues'].append(f"Error analyzing service {file_path}: {str(e)}")
    
    def _analyze_service_quality(self, services_info):
        """Analyze service layer quality"""
        issues = []
        recommendations = []
        
        # Check if service layer exists
        if not services_info['files']:
            issues.append("No service layer found")
            recommendations.append("Create service layer to separate business logic from controllers")
        
        # Check for thin service classes
        thin_services = [s for s in services_info['classes'] if len(s['methods']) < 3]
        if thin_services:
            issues.append(f"Thin service classes found: {len(thin_services)}")
            recommendations.append("Consider consolidating thin service classes or adding more business logic")
        
        # Check for missing key services
        service_names = [s['name'].lower() for s in services_info['classes']]
        expected_services = ['authservice', 'userservice', 'tenderservice', 'companyservice']
        missing_services = [srv for srv in expected_services if srv not in service_names]
        
        if missing_services:
            issues.append(f"Missing key services: {', '.join(missing_services)}")
            recommendations.append(f"Create service classes for: {', '.join(missing_services)}")
        
        services_info['issues'] = issues
        self.mvc_analysis['services']['recommendations'] = recommendations
    
    def _calculate_mvc_score(self):
        """Calculate overall MVC architecture score"""
        score = 0
        max_score = 100
        
        # Models score (25 points)
        model_score = 25
        if not self.mvc_analysis['models']['current']['classes']:
            model_score -= 15
        if len(self.mvc_analysis['models']['current']['issues']) > 3:
            model_score -= 10
        
        # Views score (25 points)
        view_score = 25
        if not self.mvc_analysis['views']['current']['templates']:
            view_score -= 15
        if len(self.mvc_analysis['views']['current']['issues']) > 3:
            view_score -= 10
        
        # Controllers score (25 points)
        controller_score = 25
        if not self.mvc_analysis['controllers']['current']['blueprints']:
            controller_score -= 10
        if len(self.mvc_analysis['controllers']['current']['routes']) > 20:
            controller_score -= 5
        if len(self.mvc_analysis['controllers']['current']['issues']) > 3:
            controller_score -= 10
        
        # Services score (25 points)
        service_score = 25
        if not self.mvc_analysis['services']['current']['classes']:
            service_score -= 20
        if len(self.mvc_analysis['services']['current']['issues']) > 2:
            service_score -= 5
        
        total_score = max(0, model_score + view_score + controller_score + service_score)
        self.mvc_analysis['overall']['score'] = total_score
    
    def _generate_overall_recommendations(self):
        """Generate overall MVC recommendations"""
        recommendations = []
        score = self.mvc_analysis['overall']['score']
        
        if score < 50:
            recommendations.append({
                'priority': 'HIGH',
                'title': 'Critical MVC Restructuring Needed',
                'description': 'Your application needs significant architectural improvements',
                'actions': [
                    'Implement proper service layer',
                    'Organize routes into blueprints',
                    'Restructure templates by feature',
                    'Separate business logic from controllers'
                ]
            })
        elif score < 75:
            recommendations.append({
                'priority': 'MEDIUM',
                'title': 'MVC Improvements Recommended',
                'description': 'Your application has good structure but could be optimized',
                'actions': [
                    'Add missing service classes',
                    'Organize large files into smaller modules',
                    'Improve template organization',
                    'Reduce controller complexity'
                ]
            })
        else:
            recommendations.append({
                'priority': 'LOW',
                'title': 'MVC Structure is Good',
                'description': 'Your application follows good MVC practices',
                'actions': [
                    'Continue following current patterns',
                    'Regular code reviews',
                    'Monitor for architectural drift'
                ]
            })
        
        self.mvc_analysis['overall']['recommendations'] = recommendations
    
    def _should_skip_file(self, file_path):
        """Check if file should be skipped"""
        skip_patterns = ['__pycache__', '.git', 'venv', '.venv', 'migrations', 'test_']
        return any(pattern in str(file_path) for pattern in skip_patterns)

def print_mvc_report(mvc_analysis):
    """Print comprehensive MVC analysis report"""
    print("\n" + "="*60)
    print("🏗️  MVC ARCHITECTURE ANALYSIS REPORT")
    print("="*60)
    
    # Overall Score
    score = mvc_analysis['overall']['score']
    score_color = "🟢" if score >= 75 else "🟡" if score >= 50 else "🔴"
    print(f"\n📊 OVERALL MVC SCORE: {score_color} {score}/100")
    
    if score >= 75:
        print("   ✅ Excellent MVC architecture!")
    elif score >= 50:
        print("   ⚠️  Good architecture with room for improvement")
    else:
        print("   ❌ Architecture needs significant improvements")
    
    # Models Analysis
    print(f"\n📦 MODELS ANALYSIS")
    models = mvc_analysis['models']['current']
    print(f"   Model classes: {len(models['classes'])}")
    print(f"   Model files: {len(models['files'])}")
    print(f"   Relationships: {len(models['relationships'])}")
    
    if models['issues']:
        print(f"   ⚠️  Issues ({len(models['issues'])}):")
        for issue in models['issues'][:3]:
            print(f"      • {issue}")
    
    # Views Analysis
    print(f"\n🎨 VIEWS ANALYSIS")
    views = mvc_analysis['views']['current']
    print(f"   Template files: {len(views['templates'])}")
    
    if views['templates']:
        avg_size = sum(t['lines'] for t in views['templates']) / len(views['templates'])
        print(f"   Average template size: {avg_size:.0f} lines")
        
        extending_templates = sum(1 for t in views['templates'] if t['extends'])
        print(f"   Templates extending base: {extending_templates}/{len(views['templates'])}")
    
    if views['issues']:
        print(f"   ⚠️  Issues ({len(views['issues'])}):")
        for issue in views['issues'][:3]:
            print(f"      • {issue}")
    
    # Controllers Analysis
    print(f"\n🎮 CONTROLLERS ANALYSIS")
    controllers = mvc_analysis['controllers']['current']
    print(f"   Route functions: {len(controllers['routes'])}")
    print(f"   Blueprint files: {len(controllers['blueprints'])}")
    print(f"   Controller files: {len(controllers['files'])}")
    
    if controllers['routes']:
        avg_complexity = sum(r.get('complexity', 1) for r in controllers['routes']) / len(controllers['routes'])
        print(f"   Average route complexity: {avg_complexity:.1f}")
        
        large_routes = [r for r in controllers['routes'] if r.get('lines', 0) > 50]
        print(f"   Large routes (>50 lines): {len(large_routes)}")
    
    if controllers['issues']:
        print(f"   ⚠️  Issues ({len(controllers['issues'])}):")
        for issue in controllers['issues'][:3]:
            print(f"      • {issue}")
    
    # Services Analysis
    print(f"\n⚙️  SERVICES ANALYSIS")
    services = mvc_analysis['services']['current']
    print(f"   Service classes: {len(services['classes'])}")
    print(f"   Service files: {len(services['files'])}")
    
    if services['classes']:
        total_methods = sum(len(s['methods']) for s in services['classes'])
        print(f"   Total service methods: {total_methods}")
    
    if services['issues']:
        print(f"   ⚠️  Issues ({len(services['issues'])}):")
        for issue in services['issues'][:3]:
            print(f"      • {issue}")
    
    # Overall Recommendations
    print(f"\n💡 RECOMMENDATIONS")
    for recommendation in mvc_analysis['overall']['recommendations']:
        priority_color = "🔴" if recommendation['priority'] == 'HIGH' else "🟡" if recommendation['priority'] == 'MEDIUM' else "🟢"
        print(f"\n   {priority_color} {recommendation['priority']} PRIORITY")
        print(f"   {recommendation['title']}")
        print(f"   {recommendation['description']}")
        print(f"   Actions:")
        for action in recommendation['actions']:
            print(f"      • {action}")
    
    # Specific Recommendations by Layer
    all_recommendations = []
    for layer in ['models', 'views', 'controllers', 'services']:
        layer_recs = mvc_analysis[layer]['recommendations']
        if layer_recs:
            all_recommendations.extend([(layer.upper(), rec) for rec in layer_recs])
    
    if all_recommendations:
        print(f"\n📋 SPECIFIC RECOMMENDATIONS BY LAYER")
        for layer, rec in all_recommendations[:10]:  # Show top 10
            print(f"   [{layer}] {rec}")

def generate_mvc_implementation_plan(mvc_analysis):
    """Generate step-by-step MVC implementation plan"""
    plan = {
        'phase_1': {'title': 'Foundation', 'steps': []},
        'phase_2': {'title': 'Organization', 'steps': []},
        'phase_3': {'title': 'Optimization', 'steps': []}
    }
    
    score = mvc_analysis['overall']['score']
    
    # Phase 1: Foundation (Critical Issues)
    if not mvc_analysis['services']['current']['classes']:
        plan['phase_1']['steps'].append({
            'title': 'Create Service Layer',
            'description': 'Implement service classes for business logic',
            'commands': [
                'mkdir -p services',
                'touch services/__init__.py',
                'Create AuthService, TenderService, CompanyService classes'
            ],
            'priority': 'HIGH'
        })
    
    if len(mvc_analysis['controllers']['current']['routes']) > 20 and not mvc_analysis['controllers']['current']['blueprints']:
        plan['phase_1']['steps'].append({
            'title': 'Implement Blueprints',
            'description': 'Organize routes into feature-based blueprints',
            'commands': [
                'mkdir -p routes',
                'Create blueprint files: auth.py, admin.py, tenders.py',
                'Move routes from app.py to appropriate blueprints'
            ],
            'priority': 'HIGH'
        })
    
    # Phase 2: Organization (Structural Improvements)
    if len(mvc_analysis['models']['current']['files']) > 1:
        plan['phase_2']['steps'].append({
            'title': 'Organize Models',
            'description': 'Consolidate and organize model files',
            'commands': [
                'Review model dependencies',
                'Organize models by domain (User, Company, Tender)',
                'Ensure proper model relationships'
            ],
            'priority': 'MEDIUM'
        })
    
    flat_templates = [t for t in mvc_analysis['views']['current']['templates'] if '/' not in t['path']]
    if len(flat_templates) > 10:
        plan['phase_2']['steps'].append({
            'title': 'Organize Templates',
            'description': 'Group templates by feature',
            'commands': [
                'mkdir -p templates/{auth,admin,tenders,reports}',
                'Move templates to appropriate subdirectories',
                'Update template references in routes'
            ],
            'priority': 'MEDIUM'
        })
    
    # Phase 3: Optimization (Performance and Maintainability)
    large_routes = [r for r in mvc_analysis['controllers']['current']['routes'] if r.get('lines', 0) > 50]
    if large_routes:
        plan['phase_3']['steps'].append({
            'title': 'Refactor Large Route Functions',
            'description': 'Break down complex route functions',
            'commands': [
                'Identify routes with >50 lines of code',
                'Extract business logic to service methods',
                'Simplify route functions to be thin controllers'
            ],
            'priority': 'LOW'
        })
    
    return plan

def save_mvc_analysis(mvc_analysis, filename="mvc_analysis.json"):
    """Save MVC analysis to JSON file"""
    with open(filename, 'w') as f:
        json.dump(mvc_analysis, f, indent=2, default=str)
    print(f"\n💾 MVC analysis saved to {filename}")

def main():
    """Main function"""
    print("🏗️  TMS MVC Architecture Analyzer")
    print("="*50)
    
    # Check if we're in a Flask project
    if not os.path.exists('app.py') and not os.path.exists('run.py'):
        print("❌ This doesn't look like a Flask project!")
        print("   Make sure you're in the project root")
        return
    
    # Analyze MVC structure
    optimizer = MVCOptimizer()
    mvc_analysis = optimizer.analyze_mvc_structure()
    
    # Print comprehensive report
    print_mvc_report(mvc_analysis)
    
    # Generate implementation plan
    plan = generate_mvc_implementation_plan(mvc_analysis)
    
    print(f"\n🗺️  IMPLEMENTATION PLAN")
    print("="*30)
    
    for phase_name, phase_info in plan.items():
        if phase_info['steps']:
            print(f"\n📅 {phase_info['title'].upper()}")
            for i, step in enumerate(phase_info['steps'], 1):
                priority_icon = "🔴" if step['priority'] == 'HIGH' else "🟡" if step['priority'] == 'MEDIUM' else "🟢"
                print(f"\n   {i}. {step['title']} {priority_icon}")
                print(f"      {step['description']}")
                print(f"      Commands:")
                for cmd in step['commands']:
                    print(f"        • {cmd}")
    
    # Offer to save analysis
    save_analysis = input(f"\n❓ Save detailed MVC analysis to JSON? (y/N): ").strip().lower()
    if save_analysis == 'y':
        save_mvc_analysis(mvc_analysis)
    
    print(f"\n🎉 MVC analysis complete!")
    print(f"💡 Use this plan to improve your application architecture!")

if __name__ == '__main__':
    main()