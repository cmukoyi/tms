from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

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
    
    # Relationships
    users = db.relationship('User', backref='company', lazy=True)
    tenders = db.relationship('Tender', backref='company', lazy=True)
    
    def __repr__(self):
        return f'<Company {self.name}>'

class TenderHistory(db.Model):
    __tablename__ = 'tender_history'
    
    id = db.Column(db.Integer, primary_key=True)
    tender_id = db.Column(db.Integer, db.ForeignKey('tenders.id'), nullable=False)
    action_type = db.Column(db.String(50), nullable=False)  # CREATE, UPDATE, DELETE, NOTE_ADD, NOTE_EDIT, NOTE_DELETE, DOCUMENT_UPLOAD, DOCUMENT_DELETE, etc.
    action_description = db.Column(db.Text, nullable=False)  # Human readable description
    details = db.Column(db.JSON, nullable=True)  # Additional structured data
    performed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45), nullable=True)  # For audit purposes
    
    # Relationships
    tender = db.relationship('Tender', backref=db.backref('history_entries', lazy=True, order_by='TenderHistory.created_at.desc()'))
    performed_by = db.relationship('User', foreign_keys=[performed_by_id], backref='performed_actions')
    
    def __repr__(self):
        return f'<TenderHistory {self.id}: {self.action_type} on Tender {self.tender_id}>'
    
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


class TenderNote(db.Model):
    __tablename__ = 'tender_notes'
    
    id = db.Column(db.Integer, primary_key=True)
    tender_id = db.Column(db.Integer, db.ForeignKey('tenders.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships - IMPORTANT: Make sure the foreign key references match your actual table names
    tender = db.relationship('Tender', backref=db.backref('notes', lazy=True, order_by='TenderNote.created_at.desc()'))
    created_by_user = db.relationship('User', foreign_keys=[created_by_id], backref='created_tender_notes')
    
    def __repr__(self):
        return f'<TenderNote {self.id}: {self.content[:50]}...>'
    
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

class Role(db.Model):
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    
    # Relationship
    users = db.relationship('User', backref='role', lazy=True)
    
    def __repr__(self):
        return f'<Role {self.name}>'

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
    
    def __repr__(self):
        return f'<User {self.username}>'

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