# routes/__init__.py - Admin blueprint for module management

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from services.module_service import ModuleService
from models import db

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def require_super_admin(f):
    """Decorator to require super admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_super_admin:
            flash('Access denied. Super admin privileges required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/modules')
@login_required
@require_super_admin
def module_management():
    """Display module management interface"""
    modules = ModuleService.get_all_modules()
    return render_template('admin/modules.html', modules=modules)

@admin_bp.route('/api/modules/toggle', methods=['POST'])
@login_required
@require_super_admin
def toggle_module():
    """Toggle module enabled/disabled status"""
    data = request.get_json()
    module_name = data.get('module_name')
    enabled = data.get('enabled', True)
    
    if not module_name:
        return jsonify({'success': False, 'message': 'Module name is required'}), 400
    
    success, message = ModuleService.toggle_module(module_name, enabled, current_user.id)
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'message': message}), 400

@admin_bp.route('/api/modules/reorder', methods=['POST'])
@login_required
@require_super_admin
def reorder_modules():
    """Update module display order"""
    data = request.get_json()
    module_orders = data.get('module_orders', {})
    
    success, message = ModuleService.update_module_order(module_orders)
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'message': message}), 400

@admin_bp.route('/api/modules/status')
@login_required
@require_super_admin
def module_status():
    """Get current status of all modules"""
    modules = ModuleService.get_all_modules()
    return jsonify({
        'modules': [module.to_dict() for module in modules]
    })

@admin_bp.route('/initialize-modules')
@login_required
@require_super_admin
def initialize_modules():
    """Initialize default modules (run once after setup)"""
    success = ModuleService.initialize_modules()
    if success:
        flash('Modules initialized successfully!', 'success')
    else:
        flash('Error initializing modules. Check logs.', 'error')
    
    return redirect(url_for('admin.module_management'))

# Don't forget to register the blueprint in your main app
# app.register_blueprint(admin_bp)