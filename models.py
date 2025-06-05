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
    
    # Feature Management Methods (PROPERLY INDENTED INSIDE THE CLASS)
    def has_feature(self, feature_code):
        """Check if company has a specific feature enabled"""
        return db.session.query(CompanyFeature).join(Feature).filter(
            CompanyFeature.company_id == self.id,
            Feature.code == feature_code,
            CompanyFeature.enabled == True,
            Feature.is_active == True
        ).first() is not None

    def get_enabled_features(self):
        """Return list of enabled features for this company"""
        try:
            # Use the 'enabled' column since it exists in your table
            return CompanyFeature.query.filter_by(
                company_id=self.id, 
                enabled=True  # Use 'enabled' not 'is_enabled'
            ).all()
        except Exception as e:
            print(f"Error getting enabled features: {e}")
            return []
    
    def enable_feature(self, feature_code, user_id=None):
        """Enable a feature for this company"""
        try:
            from datetime import datetime
            
            # Check if feature already exists
            existing_feature = CompanyFeature.query.filter_by(
                company_id=self.id,
                code=feature_code
            ).first()
            
            if existing_feature:
                # Update existing feature
                existing_feature.enabled = True
                existing_feature.is_enabled = True
                existing_feature.enabled_at = datetime.utcnow()
                existing_feature.enabled_by = user_id
            else:
                # Find or create base feature
                base_feature = Feature.query.filter_by(code=feature_code).first()
                if not base_feature:
                    base_feature = Feature(
                        code=feature_code,
                        name=feature_code.replace('_', ' ').title(),
                        description=f"{feature_code} feature"
                    )
                    db.session.add(base_feature)
                    db.session.flush()
                
                # Create new feature record
                new_feature = CompanyFeature(
                    company_id=self.id,
                    feature_id=base_feature.id,
                    code=feature_code,
                    enabled=True,
                    is_enabled=True,
                    enabled_at=datetime.utcnow(),
                    enabled_by=user_id
                )
                db.session.add(new_feature)
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Error enabling feature {feature_code}: {e}")
            return False
    
    def toggle_feature(self, feature_code, user_id=None):
        """Toggle a feature on/off for this company"""
        try:
            from datetime import datetime
            
            # First, try to find existing company feature by code AND company_id
            feature = CompanyFeature.query.filter_by(
                company_id=self.id,
                code=feature_code
            ).first()
            
            if feature:
                # Toggle existing feature
                feature.enabled = not feature.enabled
                feature.is_enabled = feature.enabled  # Keep both columns in sync
                if feature.enabled:
                    feature.enabled_at = datetime.utcnow()
                    feature.enabled_by = user_id
                else:
                    feature.enabled_at = None
                    feature.enabled_by = None
                action = "enabled" if feature.enabled else "disabled"
                
                db.session.commit()
                return True, action
            else:
                # Check if there's an existing record by feature_id to avoid duplicates
                base_feature = Feature.query.filter_by(code=feature_code).first()
                if base_feature:
                    # Check if there's already a CompanyFeature with this feature_id
                    existing_by_feature_id = CompanyFeature.query.filter_by(
                        company_id=self.id,
                        feature_id=base_feature.id
                    ).first()
                    
                    if existing_by_feature_id:
                        # Update the existing record
                        existing_by_feature_id.enabled = True
                        existing_by_feature_id.is_enabled = True
                        existing_by_feature_id.code = feature_code  # Make sure code is set
                        existing_by_feature_id.enabled_at = datetime.utcnow()
                        existing_by_feature_id.enabled_by = user_id
                        action = "enabled"
                        
                        db.session.commit()
                        return True, action
                
                # If we get here, create a new record
                if not base_feature:
                    # Create base feature if it doesn't exist
                    base_feature = Feature(
                        code=feature_code,
                        name=feature_code.replace('_', ' ').title(),
                        description=f"{feature_code} feature"
                    )
                    db.session.add(base_feature)
                    db.session.flush()  # Get the ID
                
                # Create new company feature as enabled
                new_feature = CompanyFeature(
                    company_id=self.id,
                    feature_id=base_feature.id,
                    code=feature_code,
                    enabled=True,
                    is_enabled=True,
                    enabled_at=datetime.utcnow(),
                    enabled_by=user_id
                )
                
                db.session.add(new_feature)
                action = "enabled"
                
                db.session.commit()
                return True, action
            
        except Exception as e:
            db.session.rollback()
            print(f"Error toggling feature {feature_code}: {e}")
            return False, "error"
    
    def enable_all_features(self, user_id=None):
        """Enable all available features for this company"""
        available_features = [
            'dashboard', 'tenders', 'files', 'reports', 'analytics', 'user_management'
        ]
        
        try:
            for feature_code in available_features:
                self.enable_feature(feature_code, user_id)
            return True
        except Exception as e:
            print(f"Error enabling all features: {e}")
            return False
    
    # Your disable_all_features method should look like this:

    def disable_all_features(self, user_id=None):
        """Disable all features for this company"""
        try:
            print(f"disable_all_features: Starting for company {self.id}")
            
            # Update ALL the boolean columns to make sure it works
            update_count = CompanyFeature.query.filter_by(company_id=self.id).update({
                'enabled': False,        # ← Make sure this is included
                'is_enabled': False,     # ← And this
                'enabled_at': None,
                'enabled_by': None
            })
            
            db.session.commit()
            print(f"disable_all_features: Updated {update_count} records")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Error disabling all features: {e}")
            import traceback
            traceback.print_exc()
            return False

    def __repr__(self):
            return f'<Company {self.name}>'



def disable_feature(self, feature_code, user_id=None):
    """Disable a feature for this company"""
    try:
        feature = CompanyFeature.query.filter_by(
            company_id=self.id,
            code=feature_code
        ).first()
        
        if feature:
            feature.enabled = False
            feature.is_enabled = False
            feature.enabled_at = None
            feature.enabled_by = None
            
            db.session.commit()
            return True
        else:
            # Feature doesn't exist, consider it already disabled
            return True
            
    except Exception as e:
        db.session.rollback()
        print(f"Error disabling feature {feature_code}: {e}")
        return False

def enable_all_features(self, user_id=None):
    """Enable all available features for this company"""
    available_features = [
        'dashboard', 'tenders', 'files', 'reports', 'analytics', 'user_management'
    ]
    
    try:
        for feature_code in available_features:
            self.enable_feature(feature_code, user_id)
        return True
    except Exception as e:
        print(f"Error enabling all features: {e}")
        return False



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
    
    @property
    def is_superadmin(self):
        """Check if user is super admin - for feature management compatibility"""
        return self.is_super_admin
    
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

# NEW FEATURE MANAGEMENT MODELS

class Feature(db.Model):
    """Available features that can be enabled/disabled for companies"""
    __tablename__ = 'features'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)  # Used in code
    description = db.Column(db.Text)
    category = db.Column(db.String(50))  # Dashboard, Reports, Files, etc.
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Feature {self.name}>'


# Replace your CompanyFeature model with this one that matches your actual table:

class CompanyFeature(db.Model):
    __tablename__ = 'company_features'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    feature_id = db.Column(db.Integer, db.ForeignKey('features.id'))
    enabled = db.Column(db.Boolean, default=False)
    enabled_at = db.Column(db.DateTime)
    enabled_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    code = db.Column(db.String(50))
    is_enabled = db.Column(db.Boolean, default=False)
    
    # Relationships
    company = db.relationship('Company', backref='company_features')
    feature = db.relationship('Feature', backref='company_features')
    enabled_by_user = db.relationship('User', foreign_keys=[enabled_by])
    
    # Add a property for name since templates expect it
    @property
    def name(self):
        """Get feature name from related Feature or generate from code"""
        if self.feature and self.feature.name:
            return self.feature.name
        elif self.code:
            return self.code.replace('_', ' ').title()
        else:
            return 'Unknown Feature'
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('company_id', 'code'),)