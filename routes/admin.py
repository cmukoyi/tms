from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from utils.decorators import super_admin_required
from services.module_service import ModuleService
from services import CompanyService, AuthService, RoleService
from models import Company, User, Role, CustomField, db
from services.company_module_service import CompanyModuleService
from services import CustomFieldService

admin_bp = Blueprint('admin', __name__)

# Module Management Routes
@admin_bp.route('/modules')
@super_admin_required
def test_modules():
    """MOVE: @app.route('/admin/modules')"""
    # Your existing test_modules function code here
    return render_template('test/modules.html')
    pass

@admin_bp.route('/init-modules')
@super_admin_required
def init_modules():
    """MOVE: @app.route('/admin/init-modules')"""
    # Your existing init_modules function code here
    return render_template('init/modules.html')
    pass

@admin_bp.route('/initialize-company-modules')
@super_admin_required
def initialize_company_modules():
    """MOVE: @app.route('/admin/initialize-company-modules')"""
    # Your existing initialize_company_modules function code here
    return render_template('initialize/company/modules.html')
    pass

@admin_bp.route('/company-modules')
@super_admin_required
def admin_company_modules():
    """MOVE: @app.route('/admin/company-modules')"""
    # Your existing admin_company_modules function code here
    return render_template('admin/company/modules.html')
    pass

# Custom Fields Management Routes
@admin_bp.route('/custom-fields')
@super_admin_required
def admin_custom_fields():
    """MOVE: @app.route('/admin/custom-fields')"""
    # Your existing admin_custom_fields function code here
    return render_template('admin/custom/fields.html')
    pass

@admin_bp.route('/custom-fields/create', methods=['GET', 'POST'])
@super_admin_required
def create_custom_field():
    """MOVE: @app.route('/admin/custom-fields/create')"""
    # Your existing create_custom_field function code here
    return render_template('create/custom/field.html')
    pass

@admin_bp.route('/custom-fields/<int:field_id>/edit', methods=['GET', 'POST'])
@super_admin_required
def edit_custom_field(field_id):
    """MOVE: @app.route('/admin/custom-fields/<int:field_id>/edit')"""
    # Your existing edit_custom_field function code here
    return render_template('edit/custom/field.html')
    pass

@admin_bp.route('/custom-fields/<int:field_id>/delete', methods=['POST'])
@super_admin_required
def delete_custom_field(field_id):
    """MOVE: @app.route('/admin/custom-fields/<int:field_id>/delete')"""
    # Your existing delete_custom_field function code here
    return render_template('delete/custom/field.html')
    pass

# Company Management Routes
@admin_bp.route('/companies')
@super_admin_required
def admin_companies():
    """MOVE: @app.route('/admin/companies')"""
    # Your existing admin_companies function code here
    companies = Company.query.all()
    companies = Company.query.all()
    return render_template('admin/companies.html', companies=companies)
    pass

@admin_bp.route('/companies/create', methods=['GET', 'POST'])
@super_admin_required
def create_company():
    """MOVE: @app.route('/admin/companies/create')"""
    # Your existing create_company function code here
    return render_template('create/company.html', companies=companies)
    pass

@admin_bp.route('/companies/<int:company_id>/edit', methods=['GET', 'POST'])
@super_admin_required
def edit_company(company_id):
    """MOVE: @app.route('/admin/companies/<int:company_id>/edit')"""
    # Your existing edit_company function code here
    return render_template('edit/company.html', companies=companies)
    pass

@admin_bp.route('/companies/<int:company_id>/view')
@super_admin_required
def view_company(company_id):
    """MOVE: @app.route('/admin/companies/<int:company_id>/view')"""
    # Your existing view_company function code here
    return render_template('view/company.html', companies=companies)
    pass

@admin_bp.route('/companies/<int:company_id>/update', methods=['POST'])
@super_admin_required
def update_company_details(company_id):
    """MOVE: @app.route('/admin/companies/<int:company_id>/update')"""
    # Your existing update_company_details function code here
    return render_template('update/company/details.html', companies=companies)
    pass

@admin_bp.route('/companies/<int:company_id>/deactivate', methods=['POST'])
@super_admin_required
def deactivate_company(company_id):
    """MOVE: @app.route('/admin/companies/<int:company_id>/deactivate')"""
    # Your existing deactivate_company function code here
    return render_template('deactivate/company.html', companies=companies)
    pass

@admin_bp.route('/companies/<int:company_id>/modules')
@super_admin_required
def view_company_modules(company_id):
    """MOVE: @app.route('/admin/companies/<int:company_id>/modules')"""
    # Your existing view_company_modules function code here
    return render_template('view/company/modules.html', companies=companies)
    pass

@admin_bp.route('/companies/<int:company_id>/modules/batch-update', methods=['POST'])
@super_admin_required
def update_company_modules(company_id):
    """MOVE: @app.route('/admin/companies/<int:company_id>/modules/batch-update')"""
    # Your existing update_company_modules function code here
    return render_template('update/company/modules.html', companies=companies)
    pass

@admin_bp.route('/companies/<int:company_id>/modules/batch-update', methods=['POST'])
@super_admin_required
def batch_update_company_modules(company_id):
    """MOVE: @app.route('/admin/companies/<int:company_id>/modules/batch-update')"""
    # Your existing batch_update_company_modules function code here
    return render_template('batch/update/company/modules.html', companies=companies)
    pass

# User Management Routes
@admin_bp.route('/users')
@super_admin_required
def admin_users():
    """MOVE: @app.route('/admin/users')"""
    # Your existing admin_users function code here
    users = User.query.all()
    users = User.query.all()
    return render_template('admin/users.html', users=users)
    pass

@admin_bp.route('/users/create', methods=['GET', 'POST'])
@super_admin_required
def create_user():
    """MOVE: @app.route('/admin/users/create')"""
    # Your existing create_user function code here
    return render_template('create/user.html', users=users)
    pass

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@super_admin_required
def edit_user(user_id):
    """MOVE: @app.route('/admin/users/<int:user_id>/edit')"""
    # Your existing edit_user function code here
    return render_template('edit/user.html', users=users)
    pass

@admin_bp.route('/roles')
@super_admin_required
def admin_roles():
    """MOVE: @app.route('/admin/roles')"""
    # Your existing admin_roles function code here
    return render_template('admin/roles.html')
    pass

# Company User Management Routes
@admin_bp.route('/companies/<int:company_id>/users')
@super_admin_required
def view_company_users(company_id):
    """MOVE: @app.route('/admin/companies/<int:company_id>/users')"""
    # Your existing view_company_users function code here
    return render_template('admin/users.html', companies=companies)
    pass

@admin_bp.route('/companies/<int:company_id>/users/add', methods=['GET', 'POST'])
@super_admin_required
def add_company_user(company_id):
    """MOVE: @app.route('/admin/companies/<int:company_id>/users/add')"""
    # Your existing add_company_user function code here
    return render_template('add/company/user.html', companies=companies)
    pass

@admin_bp.route('/companies/<int:company_id>/users/<int:user_id>/edit', methods=['GET', 'POST'])
@super_admin_required
def edit_company_user(company_id, user_id):
    """MOVE: @app.route('/admin/companies/<int:company_id>/users/<int:user_id>/edit')"""
    # Your existing edit_company_user function code here
    return render_template('edit/company/user.html', companies=companies)
    pass

@admin_bp.route('/companies/<int:company_id>/users/<int:user_id>/reset-password', methods=['POST'])
@super_admin_required
def reset_company_user_password(company_id, user_id):
    """MOVE: @app.route('/admin/companies/<int:company_id>/users/<int:user_id>/reset-password')"""
    # Your existing reset_company_user_password function code here
    return render_template('reset/company/user/password.html', companies=companies)
    pass

@admin_bp.route('/companies/<int:company_id>/users/<int:user_id>/toggle-status', methods=['POST'])
@super_admin_required
def toggle_company_user_status(company_id, user_id):
    """MOVE: @app.route('/admin/companies/<int:company_id>/users/<int:user_id>/toggle-status')"""
    # Your existing toggle_company_user_status function code here
    return render_template('toggle/company/user/status.html', companies=companies)
    pass