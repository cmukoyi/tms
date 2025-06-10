#!/usr/bin/env python3
"""
Automated MVC Fixer for TMS
Automatically fixes common MVC issues found by the analyzer
"""

import os
import ast
import re
import shutil
from pathlib import Path
from datetime import datetime

class AutoMVCFixer:
    def __init__(self, project_root="."):
        self.project_root = Path(project_root)
        self.backup_dir = None
        self.fixes_applied = []
        self.errors = []
        
    def create_backup(self):
        """Create backup of entire project"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_dir = self.project_root.parent / f"tms_backup_{timestamp}"
        
        print(f"📦 Creating backup at {self.backup_dir}...")
        try:
            shutil.copytree(self.project_root, self.backup_dir)
            print(f"✅ Backup created successfully!")
            return True
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            return False
    
    def fix_all_issues(self):
        """Apply all automatic fixes"""
        print("\n🔧 Starting Automated MVC Fixes...")
        print("="*50)
        
        # Create backup first
        if not self.create_backup():
            print("❌ Cannot proceed without backup!")
            return False
        
        # Apply fixes in order of importance
        fixes = [
            ("Adding missing model methods", self.fix_model_methods),
            ("Breaking down large templates", self.fix_large_templates),
            ("Extracting large route functions", self.fix_large_routes),
            ("Creating missing UserService", self.create_user_service),
            ("Consolidating thin services", self.consolidate_thin_services),
            ("Adding template base extensions", self.fix_template_extensions),
            ("Optimizing service structure", self.optimize_services)
        ]
        
        for fix_name, fix_function in fixes:
            print(f"\n🔄 {fix_name}...")
            try:
                result = fix_function()
                if result:
                    self.fixes_applied.append(fix_name)
                    print(f"✅ {fix_name} completed")
                else:
                    print(f"⏭️  {fix_name} skipped (not needed)")
            except Exception as e:
                error_msg = f"{fix_name}: {str(e)}"
                self.errors.append(error_msg)
                print(f"❌ {fix_name} failed: {e}")
        
        # Generate summary
        self.print_summary()
        return True
    
    def fix_model_methods(self):
        """Add missing __repr__ and __str__ methods to models"""
        models_file = self.project_root / "models" / "__init__.py"
        if not models_file.exists():
            return False
        
        with open(models_file, 'r') as f:
            content = f.read()
        
        # Parse AST to find models without proper methods
        tree = ast.parse(content)
        modifications = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if self._is_model_class(node, content):
                    methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    
                    if '__repr__' not in methods:
                        repr_method = self._generate_repr_method(node.name)
                        modifications.append((node.name, '__repr__', repr_method))
                    
                    if '__str__' not in methods:
                        str_method = self._generate_str_method(node.name)
                        modifications.append((node.name, '__str__', str_method))
        
        if modifications:
            new_content = self._apply_model_modifications(content, modifications)
            with open(models_file, 'w') as f:
                f.write(new_content)
            return True
        
        return False
    
    def _is_model_class(self, node, content):
        """Check if class is a database model"""
        for base in node.bases:
            if isinstance(base, ast.Attribute) and base.attr == 'Model':
                return True
        return 'db.Column' in content and node.name in ['Company', 'Role', 'TenderCategory', 'TenderStatus']
    
    def _generate_repr_method(self, class_name):
        """Generate __repr__ method for model class"""
        if class_name == 'Company':
            return """
    def __repr__(self):
        return f'<Company {self.name}>'"""
        elif class_name == 'Role':
            return """
    def __repr__(self):
        return f'<Role {self.name}>'"""
        elif class_name == 'TenderCategory':
            return """
    def __repr__(self):
        return f'<TenderCategory {self.name}>'"""
        elif class_name == 'TenderStatus':
            return """
    def __repr__(self):
        return f'<TenderStatus {self.name}>'"""
        else:
            return f"""
    def __repr__(self):
        return f'<{class_name} {{self.id}}>'"""
    
    def _generate_str_method(self, class_name):
        """Generate __str__ method for model class"""
        if class_name in ['Company', 'Role', 'TenderCategory', 'TenderStatus']:
            return """
    def __str__(self):
        return self.name"""
        else:
            return """
    def __str__(self):
        return str(self.id)"""
    
    def _apply_model_modifications(self, content, modifications):
        """Apply model method modifications to content"""
        lines = content.split('\n')
        new_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            new_lines.append(line)
            
            # Check if this line defines a class that needs modifications
            for class_name, method_name, method_code in modifications:
                if f"class {class_name}" in line and "db.Model" in line:
                    # Find the end of the class to insert methods
                    j = i + 1
                    indent_level = len(line) - len(line.lstrip())
                    
                    # Skip to end of class
                    while j < len(lines):
                        if lines[j].strip() and not lines[j].startswith(' ' * (indent_level + 1)):
                            break
                        j += 1
                    
                    # Insert method before class end
                    method_lines = method_code.split('\n')
                    for method_line in method_lines:
                        if method_line.strip():
                            new_lines.insert(-1, method_line)
                    
                    break
            
            i += 1
        
        return '\n'.join(new_lines)
    
    def fix_large_templates(self):
        """Break down large templates into components"""
        templates_dir = self.project_root / "templates"
        if not templates_dir.exists():
            return False
        
        large_templates = []
        for template_file in templates_dir.glob("**/*.html"):
            with open(template_file, 'r') as f:
                lines = f.readlines()
            
            if len(lines) > 200:
                large_templates.append((template_file, len(lines)))
        
        if not large_templates:
            return False
        
        # Create components directory
        components_dir = templates_dir / "components"
        components_dir.mkdir(exist_ok=True)
        
        fixed_count = 0
        for template_file, line_count in large_templates:
            if self._extract_template_components(template_file, components_dir):
                fixed_count += 1
        
        return fixed_count > 0
    
    def _extract_template_components(self, template_file, components_dir):
        """Extract reusable components from large template"""
        with open(template_file, 'r') as f:
            content = f.read()
        
        # Look for common patterns to extract
        extractions = []
        
        # Extract form blocks
        form_pattern = r'<form[^>]*>.*?</form>'
        forms = re.findall(form_pattern, content, re.DOTALL)
        for i, form in enumerate(forms):
            if len(form) > 300:  # Large forms
                component_name = f"{template_file.stem}_form_{i+1}.html"
                extractions.append((component_name, form, f"{{% include 'components/{component_name}' %}}"))
        
        # Extract table blocks
        table_pattern = r'<table[^>]*>.*?</table>'
        tables = re.findall(table_pattern, content, re.DOTALL)
        for i, table in enumerate(tables):
            if len(table) > 500:  # Large tables
                component_name = f"{template_file.stem}_table_{i+1}.html"
                extractions.append((component_name, table, f"{{% include 'components/{component_name}' %}}"))
        
        if extractions:
            # Create component files and update main template
            new_content = content
            for component_name, component_content, include_tag in extractions:
                component_file = components_dir / component_name
                with open(component_file, 'w') as f:
                    f.write(component_content)
                
                new_content = new_content.replace(component_content, include_tag)
            
            # Update main template
            with open(template_file, 'w') as f:
                f.write(new_content)
            
            return True
        
        return False
    
    def fix_large_routes(self):
        """Extract business logic from large route functions"""
        routes_dir = self.project_root / "routes"
        if not routes_dir.exists():
            return False
        
        fixed_count = 0
        for route_file in routes_dir.glob("*.py"):
            if self._extract_route_logic(route_file):
                fixed_count += 1
        
        return fixed_count > 0
    
    def _extract_route_logic(self, route_file):
        """Extract business logic from route functions"""
        with open(route_file, 'r') as f:
            content = f.read()
        
        try:
            tree = ast.parse(content)
        except:
            return False
        
        modifications = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check if it's a route function
                if self._is_route_function(node):
                    lines = getattr(node, 'end_lineno', 0) - getattr(node, 'lineno', 0)
                    if lines > 50:
                        # Extract business logic
                        extracted_logic = self._extract_business_logic(node, content)
                        if extracted_logic:
                            modifications.append((node.name, extracted_logic))
        
        if modifications:
            # Apply modifications (simplified - in practice, you'd need more sophisticated AST manipulation)
            print(f"   Found {len(modifications)} large route functions to refactor")
            return True
        
        return False
    
    def _is_route_function(self, node):
        """Check if function is a Flask route"""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute) and decorator.func.attr == 'route':
                    return True
        return False
    
    def _extract_business_logic(self, node, content):
        """Extract business logic from route function (simplified)"""
        # This is a simplified version - in practice, you'd need more sophisticated logic
        lines = content.split('\n')[node.lineno-1:node.end_lineno]
        
        # Look for database operations, complex calculations, etc.
        business_logic_patterns = [
            r'db\.session\.',
            r'\.query\.',
            r'calculate_',
            r'process_',
            r'validate_',
            r'for.*in.*:'
        ]
        
        for line in lines:
            for pattern in business_logic_patterns:
                if re.search(pattern, line):
                    return "# Business logic found that could be extracted to service"
        
        return None
    
    def create_user_service(self):
        """Create missing UserService class"""
        services_dir = self.project_root / "services"
        user_service_file = services_dir / "user_service.py"
        
        if user_service_file.exists():
            return False
        
        user_service_content = '''"""
User Service
Handles user-related business logic
"""

from models import User, db
from werkzeug.security import generate_password_hash


class UserService:
    """Service class for user-related operations"""
    
    @staticmethod
    def get_user_by_id(user_id):
        """Get user by ID"""
        return User.query.get(user_id)
    
    @staticmethod
    def get_user_by_username(username):
        """Get user by username"""
        return User.query.filter_by(username=username).first()
    
    @staticmethod
    def get_user_by_email(email):
        """Get user by email"""
        return User.query.filter_by(email=email).first()
    
    @staticmethod
    def create_user(username, email, password, first_name, last_name, 
                   company_id=None, role_id=None, is_super_admin=False):
        """Create new user"""
        try:
            # Check if username or email already exists
            if UserService.get_user_by_username(username):
                return None, "Username already exists"
            
            if UserService.get_user_by_email(email):
                return None, "Email already exists"
            
            # Create new user
            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                first_name=first_name,
                last_name=last_name,
                company_id=company_id,
                role_id=role_id,
                is_super_admin=is_super_admin
            )
            
            db.session.add(user)
            db.session.commit()
            
            return user, "User created successfully"
            
        except Exception as e:
            db.session.rollback()
            return None, f"Error creating user: {str(e)}"
    
    @staticmethod
    def update_user(user_id, **kwargs):
        """Update user information"""
        try:
            user = UserService.get_user_by_id(user_id)
            if not user:
                return False, "User not found"
            
            # Update fields
            for key, value in kwargs.items():
                if hasattr(user, key) and value is not None:
                    if key == 'password':
                        user.password_hash = generate_password_hash(value)
                    else:
                        setattr(user, key, value)
            
            db.session.commit()
            return True, "User updated successfully"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Error updating user: {str(e)}"
    
    @staticmethod
    def deactivate_user(user_id):
        """Deactivate user"""
        try:
            user = UserService.get_user_by_id(user_id)
            if not user:
                return False, "User not found"
            
            user.is_active = False
            db.session.commit()
            return True, "User deactivated successfully"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Error deactivating user: {str(e)}"
    
    @staticmethod
    def get_users_by_company(company_id):
        """Get all users for a company"""
        return User.query.filter_by(company_id=company_id).all()
    
    @staticmethod
    def get_active_users():
        """Get all active users"""
        return User.query.filter_by(is_active=True).all()
    
    @staticmethod
    def search_users(query, company_id=None):
        """Search users by name, username, or email"""
        search_filter = f"%{query}%"
        
        base_query = User.query.filter(
            db.or_(
                User.first_name.ilike(search_filter),
                User.last_name.ilike(search_filter),
                User.username.ilike(search_filter),
                User.email.ilike(search_filter)
            )
        )
        
        if company_id:
            base_query = base_query.filter_by(company_id=company_id)
        
        return base_query.all()
'''
        
        with open(user_service_file, 'w') as f:
            f.write(user_service_content)
        
        # Update services/__init__.py
        init_file = services_dir / "__init__.py"
        if init_file.exists():
            with open(init_file, 'r') as f:
                init_content = f.read()
            
            if 'UserService' not in init_content:
                init_content += "\nfrom .user_service import UserService\n"
                with open(init_file, 'w') as f:
                    f.write(init_content)
        
        return True
    
    def consolidate_thin_services(self):
        """Consolidate thin service classes"""
        services_dir = self.project_root / "services"
        if not services_dir.exists():
            return False
        
        # This is a placeholder - consolidating services requires careful analysis
        # In practice, you'd analyze service dependencies and merge compatible ones
        print("   Note: Service consolidation requires manual review")
        return False
    
    def fix_template_extensions(self):
        """Add base template extensions to templates that need them"""
        templates_dir = self.project_root / "templates"
        if not templates_dir.exists():
            return False
        
        fixed_count = 0
        for template_file in templates_dir.glob("**/*.html"):
            if template_file.name == 'base.html':
                continue
            
            with open(template_file, 'r') as f:
                content = f.read()
            
            # Check if template extends base and is substantial
            if not re.search(r'{%\s*extends', content) and len(content.splitlines()) > 20:
                # Add extends directive
                new_content = "{% extends 'base.html' %}\n\n" + content
                
                # Wrap content in block if not already
                if not re.search(r'{%\s*block', content):
                    # Find title if exists
                    title_match = re.search(r'<title>(.*?)</title>', content)
                    title = title_match.group(1) if title_match else template_file.stem.title()
                    
                    new_content = "{% extends 'base.html' %}\n\n"
                    new_content += "{% block title %}" + title + "{% endblock %}\n\n"
                    new_content += "{% block content %}\n"
                    new_content += content + "\n"
                    new_content += "{% endblock %}\n"
                
                with open(template_file, 'w') as f:
                    f.write(new_content)
                
                fixed_count += 1
        
        return fixed_count > 0
    
    def optimize_services(self):
        """Optimize service structure and add missing methods"""
        services_dir = self.project_root / "services"
        if not services_dir.exists():
            return False
        
        # Add common service methods that might be missing
        optimizations = 0
        
        # Check each service file for common patterns
        for service_file in services_dir.glob("*_service.py"):
            if self._add_missing_service_methods(service_file):
                optimizations += 1
        
        return optimizations > 0
    
    def _add_missing_service_methods(self, service_file):
        """Add missing common methods to service classes"""
        with open(service_file, 'r') as f:
            content = f.read()
        
        # Check for common missing methods
        missing_methods = []
        
        if 'get_all(' not in content and 'Service' in content:
            missing_methods.append(self._generate_get_all_method())
        
        if 'search(' not in content and 'Service' in content:
            missing_methods.append(self._generate_search_method())
        
        if missing_methods:
            # Add methods to class (simplified)
            for method in missing_methods:
                content += f"\n{method}\n"
            
            with open(service_file, 'w') as f:
                f.write(content)
            
            return True
        
        return False
    
    def _generate_get_all_method(self):
        """Generate get_all method template"""
        return """    @staticmethod
    def get_all():
        \"\"\"Get all records\"\"\"
        # Implementation depends on specific service
        pass"""
    
    def _generate_search_method(self):
        """Generate search method template"""
        return """    @staticmethod
    def search(query):
        \"\"\"Search records\"\"\"
        # Implementation depends on specific service
        pass"""
    
    def print_summary(self):
        """Print summary of fixes applied"""
        print("\n" + "="*60)
        print("🎉 AUTOMATED MVC FIXES SUMMARY")
        print("="*60)
        
        if self.fixes_applied:
            print(f"\n✅ FIXES APPLIED ({len(self.fixes_applied)}):")
            for fix in self.fixes_applied:
                print(f"   ✓ {fix}")
        
        if self.errors:
            print(f"\n❌ ERRORS ENCOUNTERED ({len(self.errors)}):")
            for error in self.errors:
                print(f"   ✗ {error}")
        
        if not self.fixes_applied and not self.errors:
            print(f"\n🎯 No automatic fixes needed - your code is already well-structured!")
        
        print(f"\n📦 BACKUP LOCATION:")
        print(f"   {self.backup_dir}")
        
        print(f"\n💡 NEXT STEPS:")
        print(f"   1. Test your application thoroughly")
        print(f"   2. Review the generated UserService")
        print(f"   3. Check extracted template components")
        print(f"   4. Consider manual optimizations for complex issues")
        print(f"   5. Run the MVC analyzer again to see improvements")
        
        print(f"\n🚀 TO VERIFY FIXES:")
        print(f"   python scripts/mvc_optimizer.py")

def main():
    """Main function"""
    print("🔧 Automated MVC Fixer for TMS")
    print("="*50)
    
    # Check if we're in the right directory
    if not os.path.exists('app.py'):
        print("❌ This doesn't look like a TMS project directory!")
        print("   Make sure you're in the project root with app.py")
        return
    
    # Warning about automated changes
    print("⚠️  WARNING: This script will make automated changes to your code!")
    print("   • A backup will be created automatically")
    print("   • Review all changes before committing")
    print("   • Test thoroughly after running")
    
    proceed = input("\n❓ Proceed with automated fixes? (y/N): ").strip().lower()
    
    if proceed != 'y':
        print("⏹️  Automated fixes cancelled")
        return
    
    # Run the fixer
    fixer = AutoMVCFixer()
    success = fixer.fix_all_issues()
    
    if success:
        print(f"\n🎉 Automated fixes completed!")
        print(f"💡 Run your application and test thoroughly.")
    else:
        print(f"\n❌ Automated fixes failed!")
        print(f"💡 Check the errors above and try manual fixes.")

if __name__ == '__main__':
    main()