# routes/admin_routes.py or add to your main app.py

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import login_required, current_user
from functools import wraps
from services.company_module_service import CompanyModuleService
from models import ModuleDefinition, CompanyModule, Company, db

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def require_super_admin(f):
    """Decorator to require super admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_super_admin'):
            flash('Access denied. Super admin privileges required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/company-modules')
@login_required
@require_super_admin
def company_module_management():
    """Display company module management interface"""
    companies = Company.query.filter_by(is_active=True).all()
    modules = ModuleDefinition.query.filter_by(is_active=True).order_by(ModuleDefinition.sort_order).all()
    
    # Get billing summary
    billing_summary = CompanyModuleService.get_all_companies_billing_summary()
    
    return render_template('admin/company_modules.html', 
                         companies=companies, 
                         modules=modules,
                         billing_summary=billing_summary)

@admin_bp.route('/company-modules/<int:company_id>')
@login_required
@require_super_admin
def company_module_detail(company_id):
    """Display module management for a specific company"""
    company = Company.query.get_or_404(company_id)
    all_modules = ModuleDefinition.query.filter_by(is_active=True).order_by(ModuleDefinition.sort_order).all()
    company_modules = CompanyModuleService.get_company_modules(company_id)
    
    # Create a mapping of module_id to company_module for easy lookup
    company_module_map = {cm.module_id: cm for cm in company_modules}
    
    # Combine all modules with company-specific status
    module_data = []
    for module_def in all_modules:
        company_module = company_module_map.get(module_def.id)
        module_data.append({
            'definition': module_def,
            'company_module': company_module,
            'is_enabled': company_module.is_enabled if company_module else False,
            'can_disable': not module_def.is_core
        })
    
    monthly_cost = CompanyModuleService.get_company_monthly_cost(company_id)
    
    return render_template('admin/company_module_detail.html', 
                         company=company, 
                         module_data=module_data,
                         monthly_cost=monthly_cost)

@admin_bp.route('/api/company-modules/toggle', methods=['POST'])
@login_required
@require_super_admin
def toggle_company_module():
    """Toggle module enabled/disabled status for a company"""
    data = request.get_json()
    company_id = data.get('company_id')
    module_name = data.get('module_name')
    enabled = data.get('enabled', True)
    notes = data.get('notes', '')
    
    if not company_id or not module_name:
        return jsonify({'success': False, 'message': 'Company ID and module name are required'}), 400
    
    user_id = session.get('user_id')
    success, message = CompanyModuleService.toggle_company_module(
        company_id, module_name, enabled, user_id, notes
    )
    
    if success:
        # Calculate new monthly cost
        monthly_cost = CompanyModuleService.get_company_monthly_cost(company_id)
        return jsonify({
            'success': True, 
            'message': message,
            'monthly_cost': monthly_cost
        })
    else:
        return jsonify({'success': False, 'message': message}), 400

@admin_bp.route('/api/company-modules/setup/<int:company_id>', methods=['POST'])
@login_required
@require_super_admin
def setup_company_modules(company_id):
    """Setup default modules for a company"""
    data = request.get_json()
    include_premium = data.get('include_premium', False)
    
    company = Company.query.get(company_id)
    if not company:
        return jsonify({'success': False, 'message': 'Company not found'}), 404
    
    success = CompanyModuleService.setup_company_modules(company_id, include_premium)
    
    if success:
        return jsonify({'success': True, 'message': 'Company modules setup successfully'})
    else:
        return jsonify({'success': False, 'message': 'Error setting up company modules'}), 500

@admin_bp.route('/api/billing/summary')
@login_required
@require_super_admin
def billing_summary():
    """Get billing summary for all companies"""
    summary = CompanyModuleService.get_all_companies_billing_summary()
    return jsonify({'summary': summary})

@admin_bp.route('/initialize-modules')
@login_required
@require_super_admin
def initialize_modules():
    """Initialize module definitions (run once after setup)"""
    success = CompanyModuleService.initialize_module_definitions()
    if success:
        flash('Module definitions initialized successfully!', 'success')
    else:
        flash('Error initializing module definitions. Check logs.', 'error')
    
    return redirect(url_for('admin.company_module_management'))

# User-facing route to check their company's modules
@admin_bp.route('/my-company/modules')
@login_required
def my_company_modules():
    """Display current user's company modules"""
    company_id = session.get('company_id')
    if not company_id:
        flash('No company associated with your account', 'error')
        return redirect(url_for('dashboard'))
    
    company = Company.query.get(company_id)
    enabled_modules = CompanyModuleService.get_enabled_modules_for_company(company_id)
    monthly_cost = CompanyModuleService.get_company_monthly_cost(company_id)
    
    return render_template('company_modules.html', 
                         company=company,
                         enabled_modules=enabled_modules, 
                         monthly_cost=monthly_cost)

