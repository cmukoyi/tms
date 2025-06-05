# TMS Feature Management Integration Guide

## 🚀 Quick Setup Steps

### 1. **Update Your Models**
Replace your `models.py` with the complete version provided (includes Feature and CompanyFeature models).

### 2. **Create Admin Forms**
Create `admin_forms.py` with the provided form classes.

### 3. **Add Admin Routes**
Add the admin routes to your Flask app:

```python
# In your app.py or main Flask file
from admin_routes import admin_bp

# Register the blueprint
app.register_blueprint(admin_bp)
```

### 4. **Create Database Tables**
Run this to create the new tables:

```python
# create_feature_tables.py
from app import app, db

with app.app_context():
    db.create_all()
    print("✅ Feature management tables created!")
```

### 5. **Initialize Default Features**
Run the initialization script:

```bash
python init_features.py
```

### 6. **Create Template Directories**
```bash
mkdir -p templates/admin
```

### 7. **Add Templates**
Create these template files in `templates/admin/`:
- `companies.html`
- `company_features.html`
- `features.html`
- `feature_form.html`

### 8. **Update Navigation**
Replace your `base.html` with the updated version that includes feature management menus.

## 📁 File Structure

After setup, you should have:

```
your_project/
├── app.py
├── models.py (updated)
├── admin_forms.py (new)
├── admin_routes.py (new)
├── init_features.py (new)
├── feature_helpers.py (new)
└── templates/
    ├── base.html (updated)
    └── admin/
        ├── companies.html (new)
        ├── company_features.html (new)
        ├── features.html (new)
        └── feature_form.html (new)
```

## 🔧 Using Feature Management in Your Code

### Check if Company Has Feature
```python
from feature_helpers import has_feature

# In your routes
@app.route('/reports')
def reports():
    if not has_feature('reports'):
        flash('Reports feature not available', 'warning')
        return redirect(url_for('dashboard'))
    # Show reports...
```

### Use Feature Decorator
```python
from feature_helpers import feature_required

@app.route('/analytics')
@feature_required('analytics')
def analytics():
    # This route requires analytics feature
    return render_template('analytics.html')
```

### In Templates
```html
<!-- Show menu items based on features -->
{% if session.get('has_reports_feature', True) %}
<a href="{{ url_for('reports') }}">Reports</a>
{% endif %}
```

## 🎯 Admin Access URLs

Once set up, superadmins can access:

- **Company Management**: `/admin/companies`
- **Feature Management**: `/admin/features`
- **Add New Feature**: `/admin/features/new`
- **Manage Company Features**: `/admin/companies/{id}/features`

## 🔑 Key Features

### ✅ **For Superadmins**
- Manage all available features
- Enable/disable features per company
- Bulk operations (enable all/disable all)
- Create new features for upselling
- View feature usage statistics

### ✅ **For Companies**
- Menu items appear/disappear based on enabled features
- Access control at route level
- Seamless user experience

### ✅ **For Business**
- Easy to add new premium features
- Per-company feature control
- Usage tracking and analytics
- Foundation for tiered pricing

## 📊 Default Features Created

The system initializes with these features:

1. **Dashboard** (`dashboard`) - Main dashboard access
2. **Tender Management** (`tenders`) - Create and manage tenders
3. **File Management** (`files`) - Upload and manage documents
4. **Reports** (`reports`) - Generate various reports
5. **Analytics** (`analytics`) - Advanced analytics and insights
6. **User Management** (`user_management`) - Manage company users
7. **API Access** (`api_access`) - REST API endpoints
8. **Email Notifications** (`email_notifications`) - Automated notifications
9. **Tender History** (`tender_history`) - Detailed audit trail
10. **Custom Fields** (`custom_fields`) - Create custom tender fields
11. **Bulk Operations** (`bulk_operations`) - Bulk actions on tenders
12. **Export Data** (`export_data`) - Export to Excel, CSV, PDF

## 🚨 Important Notes

1. **Superadmin Required**: Only users with `is_super_admin=True` can access feature management
2. **Session Updates**: You may need to update your login logic to set feature flags in session
3. **Existing Companies**: Run the initialization script to enable basic features for existing companies
4. **Route Protection**: Add `@feature_required` decorators to routes that need feature control

## 🔧 Session Integration

Update your login route to set feature flags:

```python
@app.route('/login', methods=['POST'])
def login():
    # ... existing login logic ...
    
    if user.company:
        # Set feature flags in session
        session['has_dashboard_feature'] = user.company.has_feature('dashboard')
        session['has_reports_feature'] = user.company.has_feature('reports')
        session['has_files_feature'] = user.company.has_feature('files')
        # ... set other features
    
    return redirect(url_for('dashboard'))
```

## 🎉 Testing the System

1. **Login as superadmin**
2. **Navigate to `/admin/companies`**
3. **Click "Manage Features" for a company**
4. **Enable/disable features and save**
5. **Login as a regular user from that company**
6. **Verify menu items appear/disappear based on features**

Your feature management system is now ready for use! 🎯