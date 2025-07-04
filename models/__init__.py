from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import json
from decimal import Decimal
from sqlalchemy import Numeric

db = SQLAlchemy()

class Company(db.Model):
    __tablename__ = 'companies'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Logo fields
    logo_filename = db.Column(db.String(255))
    logo_file_path = db.Column(db.String(500))
    logo_mime_type = db.Column(db.String(100))
    logo_file_size = db.Column(db.Integer)
    logo_uploaded_at = db.Column(db.DateTime)
    
    # Relationships
    users = db.relationship('User', backref='company', lazy=True)
    tenders = db.relationship('Tender', backref='company', lazy=True)
    
    @property
    def has_logo(self):
        """Check if company has a logo"""
        return bool(self.logo_filename and self.logo_file_path)
    
    def delete_logo(self):
        """Delete company logo from disk and database"""
        import os
        if self.has_logo and os.path.exists(self.logo_file_path):
            try:
                os.remove(self.logo_file_path)
            except Exception as e:
                print(f"Error deleting logo file: {e}")
        
        # Clear logo fields
        self.logo_filename = None
        self.logo_file_path = None
        self.logo_mime_type = None
        self.logo_file_size = None
        self.logo_uploaded_at = None
    
    def get_enabled_modules(self):
        """Get enabled module names for this company"""
        return CompanyModule.get_enabled_modules(self.id)

    def has_module(self, module_name):
        """Check if company has a specific module enabled"""
        return CompanyModule.is_module_enabled(self.id, module_name)

    def get_monthly_cost(self):
        """Get monthly cost for enabled modules"""
        return CompanyModule.get_monthly_cost(self.id)
    
    def __repr__(self):
        return f'<Company {self.name}>'

    def __str__(self):
        return self.name

class Role(db.Model):
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    
    # Relationship
    users = db.relationship('User', backref='role', lazy=True)
    
    def __repr__(self):
        return f'<Role {self.name}>'

    def __str__(self):
        return self.name

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_super_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Foreign Keys
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    
    # Relationships
    tenders = db.relationship('Tender', backref='created_by_user', lazy=True)
    
    def set_password(self, password):
        """Hash and set the password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)
    
    @property
    def full_name(self):
        """Return full name"""
        return f"{self.first_name} {self.last_name}"
    
    def can_access_company(self, company_id):
        """Check if user can access a specific company"""
        if self.is_super_admin:
            return True
        return self.company_id == company_id
    
    def __repr__(self):
        return f'<User {self.username}>'

    def __str__(self):
        return self.username

class TenderCategory(db.Model):
    __tablename__ = 'tender_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    tenders = db.relationship('Tender', backref='category', lazy=True)
    
    def __repr__(self):
        return f'<TenderCategory {self.name}>'

    def __str__(self):
        return self.name

class TenderStatus(db.Model):
    __tablename__ = 'tender_statuses'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200))
    color = db.Column(db.String(7), default='#6c757d')  # Bootstrap color codes
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    
    # Relationships
    tenders = db.relationship('Tender', backref='status', lazy=True)
    
    def __repr__(self):
        return f'<TenderStatus {self.name}>'

    def __str__(self):
        return self.name

class Tender(db.Model):
    __tablename__ = 'tenders'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    reference_number = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    
    # Foreign Keys
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('tender_categories.id'), nullable=False)
    status_id = db.Column(db.Integer, db.ForeignKey('tender_statuses.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Dates
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    submission_deadline = db.Column(db.DateTime)
    opening_date = db.Column(db.DateTime)
    
    # Custom fields (JSON storage for dynamic fields)
    custom_fields = db.Column(db.Text)  # JSON string
    
    # Relationships
    documents = db.relationship('TenderDocument', backref='tender', lazy=True, cascade='all, delete-orphan')
    
    def get_custom_fields(self):
        """Get custom fields as dictionary"""
        if self.custom_fields:
            try:
                return json.loads(self.custom_fields)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_custom_fields(self, fields_dict):
        """Set custom fields from dictionary"""
        self.custom_fields = json.dumps(fields_dict) if fields_dict else None
    
    def __repr__(self):
        return f'<Tender {self.reference_number}>'

    def __str__(self):
        return self.reference_number

class DocumentType(db.Model):
    __tablename__ = 'document_types'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    allowed_extensions = db.Column(db.String(200))  # comma-separated: .pdf,.doc,.docx
    max_size_mb = db.Column(db.Integer, default=10)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    documents = db.relationship('TenderDocument', backref='doc_type', lazy=True)
    
    def get_allowed_extensions_list(self):
        """Get allowed extensions as list"""
        if self.allowed_extensions:
            return [ext.strip() for ext in self.allowed_extensions.split(',')]
        return []
    
    def __repr__(self):
        return f'<DocumentType {self.name}>'

    def __str__(self):
        return self.name

class TenderDocument(db.Model):
    __tablename__ = 'tender_documents'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)  # in bytes
    mime_type = db.Column(db.String(100))
    
    # Foreign Keys
    tender_id = db.Column(db.Integer, db.ForeignKey('tenders.id'), nullable=False)
    document_type_id = db.Column(db.Integer, db.ForeignKey('document_types.id'), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    uploaded_by_user = db.relationship('User', foreign_keys=[uploaded_by])
    
    def get_file_size_mb(self):
        """Get file size in MB"""
        return round(self.file_size / (1024 * 1024), 2) if self.file_size else 0
    
    def __repr__(self):
        return f'<TenderDocument {self.original_filename}>'

    def __str__(self):
        return self.original_filename

class CustomField(db.Model):
    __tablename__ = 'custom_fields'
    
    id = db.Column(db.Integer, primary_key=True)
    field_name = db.Column(db.String(100), nullable=False)
    field_label = db.Column(db.String(100), nullable=False)
    field_type = db.Column(db.String(50), nullable=False)  # text, number, date, select, textarea, checkbox
    field_options = db.Column(db.Text)  # JSON for select options
    is_required = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationships
    created_by_user = db.relationship('User', foreign_keys=[created_by])
    
    def get_field_options(self):
        """Get field options as list"""
        if self.field_options:
            try:
                return json.loads(self.field_options)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_field_options(self, options_list):
        """Set field options from list"""
        self.field_options = json.dumps(options_list) if options_list else None
    
    def __repr__(self):
        return f'<CustomField {self.field_name}>'

    def __str__(self):
        return self.field_label

class TenderNote(db.Model):
    __tablename__ = 'tender_notes'
    
    id = db.Column(db.Integer, primary_key=True)
    tender_id = db.Column(db.Integer, db.ForeignKey('tenders.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tender = db.relationship('Tender', backref=db.backref('notes', lazy=True, order_by='TenderNote.created_at.desc()'))
    created_by_user = db.relationship('User', foreign_keys=[created_by_id], backref='created_tender_notes')
    
    def to_dict(self):
        """Convert note to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'tender_id': self.tender_id,
            'content': self.content,
            'created_by_id': self.created_by_id,
            'created_by_name': f"{self.created_by_user.first_name} {self.created_by_user.last_name}" if self.created_by_user else 'Unknown',
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<TenderNote {self.id}: {self.content[:50]}...>'

    def __str__(self):
        return f"Note #{self.id}"

class TenderHistory(db.Model):
    __tablename__ = 'tender_history'
    
    id = db.Column(db.Integer, primary_key=True)
    tender_id = db.Column(db.Integer, db.ForeignKey('tenders.id'), nullable=False)
    action_type = db.Column(db.String(50), nullable=False)  # CREATE, UPDATE, DELETE, NOTE_ADD, etc.
    action_description = db.Column(db.Text, nullable=False)  # Human readable description
    details = db.Column(db.JSON, nullable=True)  # Additional structured data
    performed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45), nullable=True)  # For audit purposes
    
    # Relationships
    tender = db.relationship('Tender', backref=db.backref('history_entries', lazy=True, order_by='TenderHistory.created_at.desc()'))
    performed_by = db.relationship('User', foreign_keys=[performed_by_id], backref='performed_actions')
    
    def to_dict(self):
        """Convert history entry to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'tender_id': self.tender_id,
            'action_type': self.action_type,
            'action_description': self.action_description,
            'details': self.details,
            'performed_by_id': self.performed_by_id,
            'performed_by_name': f"{self.performed_by.first_name} {self.performed_by.last_name}" if self.performed_by else 'Unknown',
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'ip_address': self.ip_address
        }
    
    def __repr__(self):
        return f'<TenderHistory {self.id}: {self.action_type} on Tender {self.tender_id}>'

    def __str__(self):
        return f"History #{self.id}"

# =====================================================
# MODULE SYSTEM MODELS
# =====================================================

class ModuleDefinition(db.Model):
    """Available modules/features in the system"""
    __tablename__ = 'module_definitions'
    
    id = db.Column(db.Integer, primary_key=True)
    module_name = db.Column(db.String(100), unique=True, nullable=False)  # e.g., 'analytics', 'notifications'
    display_name = db.Column(db.String(100), nullable=False)     # e.g., 'Advanced Analytics'
    description = db.Column(db.Text)
    is_core = db.Column(db.Boolean, default=False)  # Core modules can't be disabled
    category = db.Column(db.String(50), default='feature')
    monthly_price = db.Column(Numeric(10, 2), default=0.00)
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @staticmethod
    def get_all_modules():
        """Get all available modules"""
        return ModuleDefinition.query.filter_by(is_active=True).order_by(ModuleDefinition.sort_order, ModuleDefinition.module_name).all()
    
    @staticmethod
    def get_core_modules():
        """Get core modules that cannot be disabled"""
        return ModuleDefinition.query.filter_by(is_core=True, is_active=True).all()
    
    @staticmethod
    def get_optional_modules():
        """Get optional modules that can be enabled/disabled"""
        return ModuleDefinition.query.filter_by(is_core=False, is_active=True).all()
    
    def __repr__(self):
        return f'<ModuleDefinition {self.display_name}>'

    def __str__(self):
        return self.display_name

class CompanyModule(db.Model):
    """Company module assignments with pricing support"""
    __tablename__ = 'company_modules'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('module_definitions.id'), nullable=False)
    is_enabled = db.Column(db.Boolean, default=True, nullable=False)
    enabled_at = db.Column(db.DateTime, default=datetime.utcnow)
    enabled_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    disabled_at = db.Column(db.DateTime)
    disabled_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    notes = db.Column(db.Text)
    billing_start_date = db.Column(db.DateTime, default=datetime.utcnow)
    billing_end_date = db.Column(db.DateTime)
    monthly_cost = db.Column(Numeric(10, 2), default=0.00)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = db.relationship('Company', backref='company_modules')
    module_definition = db.relationship('ModuleDefinition', backref='company_module_assignments')
    enabled_by_user = db.relationship('User', foreign_keys=[enabled_by])
    disabled_by_user = db.relationship('User', foreign_keys=[disabled_by])
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('company_id', 'module_id', name='unique_company_module'),)
    
    def get_effective_price(self):
        """Get the effective price for this company module (custom or default)"""
        # Check for custom pricing
        custom_pricing = CompanyModulePricing.query.filter_by(
            company_id=self.company_id,
            module_id=self.module_id,
            is_active=True
        ).order_by(CompanyModulePricing.effective_date.desc()).first()
        
        if custom_pricing:
            return float(custom_pricing.custom_price)
        
        # Return default price from module definition
        if self.module_definition:
            return float(self.module_definition.monthly_price) if self.module_definition.monthly_price else 0.0
        
        return 0.0
    
    def has_custom_pricing(self):
        """Check if this company module has custom pricing"""
        return CompanyModulePricing.query.filter_by(
            company_id=self.company_id,
            module_id=self.module_id,
            is_active=True
        ).first() is not None
    
    @staticmethod
    def get_enabled_modules(company_id):
        """Get list of enabled module names for a company"""
        enabled_modules = db.session.query(CompanyModule, ModuleDefinition).join(ModuleDefinition).filter(
            CompanyModule.company_id == company_id,
            CompanyModule.is_enabled == True
        ).all()
        
        return [module_def.module_name for cm, module_def in enabled_modules]
    
    @staticmethod
    def get_monthly_cost(company_id):
        """Get total monthly cost for a company"""
        enabled_modules = db.session.query(CompanyModule, ModuleDefinition).join(ModuleDefinition).filter(
            CompanyModule.company_id == company_id,
            CompanyModule.is_enabled == True
        ).all()
        
        total_cost = 0.0
        for cm, module_def in enabled_modules:
            # Check for custom pricing
            custom_pricing = CompanyModulePricing.query.filter_by(
                company_id=company_id,
                module_id=module_def.id,
                is_active=True
            ).order_by(CompanyModulePricing.effective_date.desc()).first()
            
            if custom_pricing:
                total_cost += float(custom_pricing.custom_price)
            else:
                total_cost += float(module_def.monthly_price) if module_def.monthly_price else 0.0
        
        return total_cost
    
    @staticmethod
    def is_module_enabled(company_id, module_name):
        """Check if a specific module is enabled for a company"""
        result = db.session.query(CompanyModule).join(ModuleDefinition).filter(
            CompanyModule.company_id == company_id,
            ModuleDefinition.module_name == module_name,
            CompanyModule.is_enabled == True
        ).first()
        
        return result is not None
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'company_id': self.company_id,
            'module_id': self.module_id,
            'module_name': self.module_definition.module_name if self.module_definition else None,
            'module_display_name': self.module_definition.display_name if self.module_definition else None,
            'is_enabled': self.is_enabled,
            'enabled_at': self.enabled_at.isoformat() if self.enabled_at else None,
            'monthly_cost': float(self.monthly_cost) if self.monthly_cost else 0.0,
            'effective_price': self.get_effective_price(),
            'has_custom_pricing': self.has_custom_pricing(),
            'billing_start_date': self.billing_start_date.isoformat() if self.billing_start_date else None,
            'notes': self.notes
        }
    
    def __repr__(self):
        return f'<CompanyModule {self.company_id}-{self.module_id}>'

    def __str__(self):
        module_name = self.module_definition.module_name if self.module_definition else f'Module#{self.module_id}'
        return f"Company {self.company_id} - {module_name}"

class CompanyModulePricing(db.Model):
    """Custom pricing for modules per company"""
    __tablename__ = 'company_module_pricing'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('module_definitions.id'), nullable=False)
    custom_price = db.Column(Numeric(10, 2), nullable=False)
    effective_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relationships
    company = db.relationship('Company', backref='custom_pricing')
    module = db.relationship('ModuleDefinition', backref='custom_pricing')
    created_by_user = db.relationship('User')
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'module_id': self.module_id,
            'custom_price': float(self.custom_price),
            'effective_date': self.effective_date.isoformat() if self.effective_date else None,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'notes': self.notes,
            'is_active': self.is_active
        }

    def __repr__(self):
        return f'<CompanyModulePricing {self.company_id}-{self.module_id}>'

# =====================================================
# BILLING MODELS
# =====================================================

class MonthlyBill(db.Model):
    """Monthly bills for companies"""
    __tablename__ = 'monthly_bills'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    bill_year = db.Column(db.Integer, nullable=False)
    bill_month = db.Column(db.Integer, nullable=False)  # 1-12
    total_amount = db.Column(Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default='ZAR', nullable=False)
    bill_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='draft', nullable=False)  # draft, sent, paid, overdue
    generated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    generated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    notes = db.Column(db.Text)
    
    # Relationships
    company = db.relationship('Company', backref='monthly_bills')
    generated_by_user = db.relationship('User', backref='generated_monthly_bills')
    line_items = db.relationship('BillLineItem', backref='monthly_bill', cascade='all, delete-orphan')
    
    @property
    def bill_period(self):
        return f"{self.bill_year}-{self.bill_month:02d}"
    
    @property
    def formatted_amount(self):
        return f"R {self.total_amount:,.2f}"
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'company_name': self.company.name if self.company else None,
            'bill_year': self.bill_year,
            'bill_month': self.bill_month,
            'bill_period': self.bill_period,
            'total_amount': float(self.total_amount),
            'formatted_amount': self.formatted_amount,
            'currency': self.currency,
            'bill_date': self.bill_date.isoformat() if self.bill_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'status': self.status,
            'generated_by': self.generated_by,
            'generated_at': self.generated_at.isoformat() if self.generated_at else None,
            'notes': self.notes
        }
    
    def __repr__(self):
        return f'<MonthlyBill {self.company_id}-{self.bill_year}-{self.bill_month:02d}>'

    def __str__(self):
        return f"Bill {self.id} - {self.bill_period}"

class BillLineItem(db.Model):
    """Individual line items for bills"""
    __tablename__ = 'bill_line_items'
    
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('monthly_bills.id'), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('module_definitions.id'), nullable=False)
    module_name = db.Column(db.String(100), nullable=False)
    module_display_name = db.Column(db.String(200), nullable=False)
    unit_price = db.Column(Numeric(10, 2), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    line_total = db.Column(Numeric(10, 2), nullable=False)
    is_custom_price = db.Column(db.Boolean, default=False, nullable=False)
    pricing_notes = db.Column(db.Text)
    
    # Relationships
    module_definition = db.relationship('ModuleDefinition', backref='bill_line_items')
    
    def to_dict(self):
        return {
            'id': self.id,
            'bill_id': self.bill_id,
            'module_id': self.module_id,
            'module_name': self.module_name,
            'module_display_name': self.module_display_name,
            'unit_price': float(self.unit_price),
            'quantity': self.quantity,
            'line_total': float(self.line_total),
            'is_custom_price': self.is_custom_price,
            'pricing_notes': self.pricing_notes
        }
    
    def __repr__(self):
        return f'<BillLineItem {self.bill_id}-{self.module_id}>'

    def __str__(self):
        return f"BillItem {self.id} - {self.module_display_name}"

# Add this alias for backward compatibility
Bill = MonthlyBill  # This allows existing code to use Bill instead of MonthlyBill

# =====================================================
# DOCUMENT MODELS
# =====================================================

class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    tender_id = db.Column(db.Integer, db.ForeignKey('tenders.id'), nullable=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)
    file_type = db.Column(db.String(100), nullable=True)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships without backrefs to avoid conflicts
    tender = db.relationship('Tender')
    company = db.relationship('Company')
    uploaded_by = db.relationship('User')
    
    def __repr__(self):
        return f'<Document {self.original_filename}>'

    def __str__(self):
        return self.original_filename

class CompanyDocument(db.Model):
    __tablename__ = 'company_documents'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    document_name = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    mime_type = db.Column(db.String(100))
    document_category = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = db.relationship('Company', backref='documents')
    uploader = db.relationship('User', backref='uploaded_company_docs')
    
    @property
    def file_size_human(self):
        """Return human readable file size"""
        if not self.file_size:
            return "Unknown"
        
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def __repr__(self):
        return f'<CompanyDocument {self.document_name}>'

    def __str__(self):
        return self.document_name

# =====================================================
# NOTIFICATION MODELS
# =====================================================

class CompanySettings(db.Model):
    __tablename__ = 'company_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    notification_days = db.Column(db.Integer, default=7)  # Days before deadline to notify
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    company = db.relationship('Company', backref=db.backref('settings', uselist=False))
    
    def __repr__(self):
        return f'<CompanySettings {self.company_id}>'

    def __str__(self):
        return f"Settings for Company {self.company_id}"

class TenderNotification(db.Model):
    __tablename__ = 'tender_notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    tender_id = db.Column(db.Integer, db.ForeignKey('tenders.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    notification_type = db.Column(db.String(50), default='deadline_approaching')
    message = db.Column(db.Text)
    days_remaining = db.Column(db.Integer)
    is_read = db.Column(db.Boolean, default=False)
    is_processed = db.Column(db.Boolean, default=False)
    processed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    processed_at = db.Column(db.DateTime, nullable=True)
    processing_note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    tender = db.relationship('Tender', backref='notifications')
    company = db.relationship('Company')
    processor = db.relationship('User', foreign_keys=[processed_by])
    
    def to_dict(self):
        """Convert notification to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'tender_id': self.tender_id,
            'company_id': self.company_id,
            'notification_type': self.notification_type,
            'message': self.message,
            'days_remaining': self.days_remaining,
            'is_read': self.is_read,
            'is_processed': self.is_processed,
            'processed_by': self.processed_by,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'processing_note': self.processing_note,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<TenderNotification {self.id}: {self.notification_type}>'

    def __str__(self):
        return f"Notification #{self.id}"

# =====================================================
# LEGACY MODELS (for backward compatibility)
# =====================================================

class Feature(db.Model):
    """Legacy feature model"""
    __tablename__ = 'features'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    company_features = db.relationship('CompanyFeature', backref='feature', lazy=True)
    
    def __repr__(self):
        return f'<Feature {self.code}>'

    def __str__(self):
        return self.name

class CompanyFeature(db.Model):
    """Legacy company-feature relationship model"""
    __tablename__ = 'company_features'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    feature_id = db.Column(db.Integer, db.ForeignKey('features.id'), nullable=False)
    enabled = db.Column(db.Boolean, default=True)
    enabled_at = db.Column(db.DateTime)
    enabled_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    code = db.Column(db.String(50))  # Duplicate of feature.code for performance
    is_enabled = db.Column(db.Boolean, default=True)  # Another enabled field
    
    # Relationships
    company = db.relationship('Company', backref='legacy_company_features')
    enabled_by_user = db.relationship('User', foreign_keys=[enabled_by])
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('company_id', 'feature_id', name='unique_company_feature'),)
    
    def __repr__(self):
        return f'<CompanyFeature {self.company_id}-{self.feature_id}>'

    def __str__(self):
        return f"Company {self.company_id} - Feature {self.feature_id}"

# =====================================================
# NOTIFICATION SERVICE
# =====================================================

class NotificationService:
    
    @staticmethod
    def generate_deadline_notifications():
        """Generate notifications for tenders approaching deadline"""
        # Get all companies and their notification settings
        companies = Company.query.filter_by(is_active=True).all()
        
        for company in companies:
            # Get company notification days setting
            settings = CompanySettings.query.filter_by(company_id=company.id).first()
            notification_days = settings.notification_days if settings else 7
            
            # Calculate cutoff date
            cutoff_date = datetime.now() + timedelta(days=notification_days)
            
            # Find tenders approaching deadline (not closed/cancelled)
            approaching_tenders = Tender.query.filter(
                Tender.company_id == company.id,
                Tender.submission_deadline <= cutoff_date,
                Tender.submission_deadline >= datetime.now(),
                ~Tender.status_id.in_([3, 6])  # Not closed or cancelled
            ).all()
            
            for tender in approaching_tenders:
                # Check if notification already exists
                existing = TenderNotification.query.filter_by(
                    tender_id=tender.id,
                    company_id=company.id,
                    notification_type='deadline_approaching'
                ).first()
                
                if not existing:
                    days_remaining = (tender.submission_deadline - datetime.now()).days
                    
                    # Create notification
                    notification = TenderNotification(
                        tender_id=tender.id,
                        company_id=company.id,
                        notification_type='deadline_approaching',
                        message=f"Tender '{tender.title}' deadline in {days_remaining} days",
                        days_remaining=days_remaining
                    )
                    db.session.add(notification)
        
        db.session.commit()
    
    @staticmethod
    def get_company_notifications(company_id, unread_only=True):
        """Get notifications for a specific company"""
        query = TenderNotification.query.filter_by(
            company_id=company_id,
            is_processed=False
        ).join(Tender).filter(
            ~Tender.status_id.in_([3, 6])  # Exclude closed/cancelled tenders
        )
        
        if unread_only:
            query = query.filter_by(is_read=False)
            
        return query.order_by(TenderNotification.created_at.desc()).all()
    
    @staticmethod
    def get_notification_count(company_id):
        """Get count of unread notifications for a company"""
        return TenderNotification.query.filter_by(
            company_id=company_id,
            is_read=False,
            is_processed=False
        ).join(Tender).filter(
            ~Tender.status_id.in_([3, 6])
        ).count()
    
    @staticmethod
    def mark_notification_read(notification_id):
        """Mark a notification as read"""
        notification = TenderNotification.query.get(notification_id)
        if notification:
            notification.is_read = True
            db.session.commit()
    
    @staticmethod
    def process_notification(notification_id, user_id, note=None):
        """Process/close a notification"""
        notification = TenderNotification.query.get(notification_id)
        if notification:
            notification.is_processed = True
            notification.processed_by = user_id
            notification.processed_at = datetime.utcnow()
            notification.processing_note = note
            notification.is_read = True
            db.session.commit()
            return True
        return False
    
    @staticmethod
    def process_all_notifications(company_id, user_id, note=None):
        """Process all notifications for a company"""
        notifications = TenderNotification.query.filter_by(
            company_id=company_id,
            is_processed=False
        ).all()
        
        for notification in notifications:
            notification.is_processed = True
            notification.processed_by = user_id
            notification.processed_at = datetime.utcnow()
            notification.processing_note = note
            notification.is_read = True
        
        db.session.commit()
        return len(notifications)