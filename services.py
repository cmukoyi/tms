from models import db, User, Company, Role, Tender, TenderCategory, TenderStatus, TenderDocument, DocumentType, CustomField
from datetime import datetime
import secrets
import string
import os
import json
from werkzeug.utils import secure_filename
from models import db, TenderHistory

from services.module_service import ModuleService



class CompanyService:
    """Company management services"""

    @staticmethod
    def get_company_by_id(company_id):
        """Get company by ID"""
        return Company.query.get(company_id)

    @staticmethod
    def update_company(company_id, name, email, phone=None, address=None, is_active=True):
        """Update company details"""
        try:
            company = Company.query.get(company_id)
            if not company:
                return False, "Company not found."
            
            # Store original status for comparison
            original_status = company.is_active
            
            # Check if email is already taken by another company
            existing_company = Company.query.filter(
                Company.email == email,
                Company.id != company_id
            ).first()
            
            if existing_company:
                return False, f"Email '{email}' is already registered to another company."
            
            # Update company details
            company.name = name
            company.email = email
            company.phone = phone
            company.address = address
            company.is_active = is_active
            
            # If company is being deactivated, deactivate all its users
            if original_status and not is_active:
                User.query.filter_by(company_id=company_id).update({'is_active': False})
            # If company is being reactivated, reactivate all its users
            elif not original_status and is_active:
                User.query.filter_by(company_id=company_id).update({'is_active': True})
            
            db.session.commit()
            
            # Prepare status change message
            status_change = ""
            if original_status != is_active:
                status_change = f" Company has been {'activated' if is_active else 'deactivated'}."
                if not is_active:
                    status_change += " All company users have been deactivated."
                else:
                    status_change += " All company users have been reactivated."
            
            return True, f"Company '{name}' updated successfully.{status_change}"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Error updating company: {str(e)}"

    @staticmethod
    def deactivate_company(company_id):
        """Deactivate a company and its users"""
        try:
            company = Company.query.get(company_id)
            if not company:
                return False, "Company not found"
            
            if not company.is_active:
                return False, "Company is already inactive"
            
            # Deactivate company
            company.is_active = False
            
            # Deactivate all company users
            User.query.filter_by(company_id=company_id).update({'is_active': False})
            
            db.session.commit()
            return True, f"Company '{company.name}' and its users deactivated successfully"
        except Exception as e:
            db.session.rollback()
            return False, f"Error deactivating company: {str(e)}"

    @staticmethod
    def activate_company(company_id):
        """Activate a company and its users"""
        try:
            company = Company.query.get(company_id)
            if not company:
                return False, "Company not found"
            
            if company.is_active:
                return False, "Company is already active"
            
            # Activate company
            company.is_active = True
            
            # Activate all company users
            User.query.filter_by(company_id=company_id).update({'is_active': True})
            
            db.session.commit()
            return True, f"Company '{company.name}' and its users activated successfully"
        except Exception as e:
            db.session.rollback()
            return False, f"Error activating company: {str(e)}"

    @staticmethod
    def get_company_stats(company_id):
        """Get comprehensive company statistics"""
        try:
            company = Company.query.get(company_id)
            if not company:
                return None
            
            # Get all users for this company
            users = User.query.filter_by(company_id=company_id).all()
            
            # Count different types of users
            total_users = len(users)
            active_users = len([u for u in users if u.is_active])
            admin_users = User.query.join(Role).filter(
                User.company_id == company_id,
                Role.name == 'Company Admin'
            ).count()
            
            # Get tender statistics
            total_tenders = Tender.query.filter_by(company_id=company_id).count()
            active_tenders = Tender.query.join(TenderStatus).filter(
                Tender.company_id == company_id,
                TenderStatus.name.in_(['Open', 'Active', 'Published'])
            ).count()
            
            # Count active tenders (non-closed)
            active_tender_count = 0
            try:
                closed_status = TenderStatus.query.filter_by(name='Closed').first()
                if closed_status:
                    active_tender_count = Tender.query.filter(
                        Tender.company_id == company_id,
                        Tender.status_id != closed_status.id
                    ).count()
                else:
                    active_tender_count = total_tenders
            except:
                active_tender_count = total_tenders
            
            return {
                'company_name': company.name,
                'total_users': total_users,
                'active_users': active_users,
                'admins': admin_users,
                'inactive_users': total_users - active_users,
                'total_tenders': total_tenders,
                'active_tenders': active_tenders,
                'active_tender_count': active_tender_count,
                'created_date': company.created_at
            }
            
        except Exception as e:
            print(f"Error getting company stats: {str(e)}")
            return {
                'company_name': 'Unknown',
                'total_users': 0,
                'active_users': 0,
                'admins': 0,
                'inactive_users': 0,
                'total_tenders': 0,
                'active_tenders': 0,
                'active_tender_count': 0,
                'created_date': None
            }

    @staticmethod
    def generate_password(length=12):
        """Generate a secure random password"""
        characters = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(characters) for _ in range(length))
    
    @staticmethod
    def create_company_with_admin(name, email, phone=None, address=None, 
                                admin_first_name=None, admin_last_name=None, 
                                admin_email=None, admin_username=None):
        """Create a new company with its admin user"""
        try:
            # Check if company email already exists
            if Company.query.filter_by(email=email).first():
                return None, None, "Company email already exists"
            
            # Create the company
            company = Company(
                name=name,
                email=email,
                phone=phone,
                address=address
            )
            db.session.add(company)
            db.session.flush()  # Get the company ID without committing
            
            # Prepare admin user details
            if not admin_first_name:
                admin_first_name = "Admin"
            if not admin_last_name:
                admin_last_name = "User"
            if not admin_email:
                admin_email = f"admin@{name.lower().replace(' ', '')}.com"
            if not admin_username:
                admin_username = f"{name.lower().replace(' ', '')}_admin"
            
            # Check if admin username or email already exists
            if User.query.filter_by(username=admin_username).first():
                admin_username = f"{admin_username}_{company.id}"
            
            if User.query.filter_by(email=admin_email).first():
                admin_email = f"admin{company.id}@{name.lower().replace(' ', '')}.com"
            
            # Get Company Admin role
            company_admin_role = RoleService.get_role_by_name('Company Admin')
            if not company_admin_role:
                db.session.rollback()
                return None, None, "Company Admin role not found. Please create default roles first."
            
            # Generate password for admin
            admin_password = CompanyService.generate_password()
            
            # Create admin user
            admin_user = User(
                username=admin_username,
                email=admin_email,
                first_name=admin_first_name,
                last_name=admin_last_name,
                company_id=company.id,
                role_id=company_admin_role.id,
                is_super_admin=False
            )
            admin_user.set_password(admin_password)
            db.session.add(admin_user)
            
            # Commit the transaction
            db.session.commit()
            
            return company, {
                'user': admin_user,
                'password': admin_password,
                'username': admin_username,
                'email': admin_email
            }, "Company and admin user created successfully"
            
        except Exception as e:
            db.session.rollback()
            return None, None, f"Error creating company: {str(e)}"

    @staticmethod
    def create_company_with_admin_and_modules(name, email, phone=None, address=None, 
                                             admin_first_name=None, admin_last_name=None, 
                                             admin_email=None, admin_username=None,
                                             enable_all_features=False, enable_premium=False,
                                             selected_modules=None):
        """
        Create a new company with admin user and setup modules
        Enhanced version that includes module setup
        """
        try:
            # First create the company and admin (your existing logic)
            company, admin_info, message = CompanyService.create_company_with_admin(
                name=name,
                email=email, 
                phone=phone,
                address=address,
                admin_first_name=admin_first_name,
                admin_last_name=admin_last_name,
                admin_email=admin_email,
                admin_username=admin_username
            )
            
            if not company:
                return None, None, message
            
            # Now setup modules
            from services.company_module_service import CompanyModuleService
            
            if selected_modules:
                # Enable specific modules
                for module_name in selected_modules:
                    CompanyModuleService.toggle_company_module(
                        company.id, module_name, True, admin_info['user_id'], 
                        "Enabled during company creation"
                    )
            elif enable_all_features:
                # Enable all features and optionally premium
                CompanyModuleService.setup_company_modules(company.id, include_premium=enable_premium)
            else:
                # Default: only core modules
                CompanyModuleService.setup_company_modules(company.id, include_premium=False)
                
                # Disable feature modules if only core requested
                from models import ModuleDefinition
                feature_modules = ModuleDefinition.query.filter_by(category='feature').all()
                for module_def in feature_modules:
                    CompanyModuleService.toggle_company_module(
                        company.id, module_def.module_name, False, admin_info['user_id'],
                        "Disabled - only core modules requested during creation"
                    )
            
            return company, admin_info, message
            
        except Exception as e:
            db.session.rollback()
            return None, None, f"Error creating company with modules: {str(e)}"

    @staticmethod
    def create_company(name, email, phone=None, address=None):
        """Create a new company (legacy method - kept for compatibility)"""
        try:
            # Check if company email already exists
            if Company.query.filter_by(email=email).first():
                return None, "Company email already exists"
            
            company = Company(
                name=name,
                email=email,
                phone=phone,
                address=address
            )
            db.session.add(company)
            db.session.commit()
            return company, "Company created successfully"
        except Exception as e:
            db.session.rollback()
            return None, f"Error creating company: {str(e)}"
    
    @staticmethod
    def get_all_companies():
        """Get all companies (both active and inactive)"""
        try:
            return Company.query.order_by(Company.created_at.desc()).all()
        except Exception as e:
            print(f"Error getting all companies: {str(e)}")
            return []
    
    @staticmethod
    def get_active_companies():
        """Get all active companies only"""
        try:
            return Company.query.filter_by(is_active=True).order_by(Company.created_at.desc()).all()
        except Exception as e:
            print(f"Error getting active companies: {str(e)}")
            return []

class RoleService:
    """Role management services"""
    
    @staticmethod
    def create_default_roles():
        """Create default system roles"""
        default_roles = [
            {'name': 'Super Admin', 'description': 'System administrator with full access'},
            {'name': 'Company Admin', 'description': 'Company administrator with company-wide access'},
            {'name': 'Procurement Manager', 'description': 'Manages tender processes and procurement'},
            {'name': 'Vendor', 'description': 'External vendor user with limited access'},
            {'name': 'Viewer', 'description': 'Read-only access to assigned content'}
        ]
        
        try:
            for role_data in default_roles:
                if not Role.query.filter_by(name=role_data['name']).first():
                    role = Role(**role_data)
                    db.session.add(role)
            
            db.session.commit()
            return True, "Default roles created successfully"
        except Exception as e:
            db.session.rollback()
            return False, f"Error creating default roles: {str(e)}"
    
    @staticmethod
    def get_all_roles():
        """Get all roles"""
        return Role.query.all()
    
    @staticmethod
    def get_role_by_id(role_id):
        """Get role by ID"""
        return Role.query.get(role_id)
    
    @staticmethod
    def get_role_by_name(name):
        """Get role by name"""
        return Role.query.filter_by(name=name).first()
    
    @staticmethod
    def create_role(name, description=None):
        """Create a new role"""
        try:
            if Role.query.filter_by(name=name).first():
                return None, "Role already exists"
            
            role = Role(name=name, description=description)
            db.session.add(role)
            db.session.commit()
            return role, "Role created successfully"
        except Exception as e:
            db.session.rollback()
            return None, f"Error creating role: {str(e)}"
    
    @staticmethod
    def get_company_roles():
        """Get roles suitable for company users (excluding Super Admin)"""
        return Role.query.filter(Role.name != 'Super Admin').all()

class TenantService:
    """Tenant management services - wrapper around CompanyService for clearer naming"""
    
    @staticmethod
    def create_tenant(name, email, phone=None, address=None, 
                     admin_first_name=None, admin_last_name=None, 
                     admin_email=None, admin_username=None):
        """Create a new tenant (company) with admin user"""
        return CompanyService.create_company_with_admin(
            name=name,
            email=email,
            phone=phone,
            address=address,
            admin_first_name=admin_first_name,
            admin_last_name=admin_last_name,
            admin_email=admin_email,
            admin_username=admin_username
        )
    
    @staticmethod
    def get_all_tenants():
        """Get all active tenants"""
        return CompanyService.get_all_companies()
    
    @staticmethod
    def get_tenant_by_id(tenant_id):
        """Get tenant by ID"""
        return CompanyService.get_company_by_id(tenant_id)
    
    @staticmethod
    def deactivate_tenant(tenant_id):
        """Deactivate a tenant"""
        return CompanyService.deactivate_company(tenant_id)
    
    @staticmethod
    def activate_tenant(tenant_id):
        """Activate a tenant"""
        return CompanyService.activate_company(tenant_id)

class TenderService:
    """Tender management services"""
    
    @staticmethod
    def generate_reference_number(company_id):
        """Generate unique reference number for tender"""
        company = Company.query.get(company_id)
        company_code = company.name[:3].upper() if company else "TND"
        
        # Get current year
        year = datetime.now().year
        
        # Count existing tenders for this company this year
        count = Tender.query.filter(
            Tender.company_id == company_id,
            db.extract('year', Tender.created_at) == year
        ).count() + 1
        
        return f"{company_code}-{year}-{count:04d}"
    
    @staticmethod
    def create_tender(title, description, company_id, category_id, status_id, created_by, 
                     submission_deadline=None, opening_date=None, custom_fields=None):
        """Create a new tender"""
        try:
            # Generate reference number
            reference_number = TenderService.generate_reference_number(company_id)
            
            tender = Tender(
                title=title,
                reference_number=reference_number,
                description=description,
                company_id=company_id,
                category_id=category_id,
                status_id=status_id,
                created_by=created_by,
                submission_deadline=submission_deadline,
                opening_date=opening_date
            )
            
            if custom_fields:
                tender.set_custom_fields(custom_fields)
            
            db.session.add(tender)
            db.session.commit()
            return tender, "Tender created successfully"
        except Exception as e:
            db.session.rollback()
            return None, f"Error creating tender: {str(e)}"
    
    @staticmethod
    def update_tender(tender_id, title, description, category_id, status_id, 
                     submission_deadline=None, opening_date=None, custom_fields=None):
        """Update existing tender"""
        try:
            tender = Tender.query.get(tender_id)
            if not tender:
                return False, "Tender not found"
            
            tender.title = title
            tender.description = description
            tender.category_id = category_id
            tender.status_id = status_id
            tender.submission_deadline = submission_deadline
            tender.opening_date = opening_date
            tender.updated_at = datetime.utcnow()
            
            if custom_fields is not None:
                tender.set_custom_fields(custom_fields)
            
            db.session.commit()
            return True, "Tender updated successfully"
        except Exception as e:
            db.session.rollback()
            return False, f"Error updating tender: {str(e)}"
    
    @staticmethod
    def get_tender_by_id(tender_id):
        """Get tender by ID"""
        return Tender.query.get(tender_id)
    
    @staticmethod
    def get_tenders_by_company(company_id, status_filter=None, category_filter=None):
        """Get tenders for a specific company with optional filters"""
        query = Tender.query.filter_by(company_id=company_id)
        
        if status_filter:
            query = query.filter_by(status_id=status_filter)
        
        if category_filter:
            query = query.filter_by(category_id=category_filter)
        
        return query.order_by(Tender.created_at.desc()).all()
    
    @staticmethod
    def get_all_tenders():
        """Get all tenders (for super admin)"""
        return Tender.query.order_by(Tender.created_at.desc()).all()
    
    @staticmethod
    def delete_tender(tender_id):
        """Delete tender and associated documents"""
        try:
            tender = Tender.query.get(tender_id)
            if not tender:
                return False, "Tender not found"
            
            db.session.delete(tender)
            db.session.commit()
            return True, "Tender deleted successfully"
        except Exception as e:
            db.session.rollback()
            return False, f"Error deleting tender: {str(e)}"
    @staticmethod
    def get_tender_stats(company_id=None):
        """Get tender statistics"""
        try:
            if company_id:
                # Company-specific stats
                total_tenders = Tender.query.filter_by(company_id=company_id).count()
                
                # Get status breakdown for company
                stats = db.session.query(
                    TenderStatus.name,
                    TenderStatus.color,
                    db.func.count(Tender.id).label('count')
                ).join(Tender).filter(
                    Tender.company_id == company_id
                ).group_by(TenderStatus.name, TenderStatus.color).all()
                
            else:
                # System-wide stats (for super admin)
                total_tenders = Tender.query.count()
                
                # Get status breakdown for all tenders
                stats = db.session.query(
                    TenderStatus.name,
                    TenderStatus.color,
                    db.func.count(Tender.id).label('count')
                ).join(Tender).group_by(TenderStatus.name, TenderStatus.color).all()
            
            # Format the status breakdown
            status_breakdown = []
            for stat in stats:
                status_breakdown.append({
                    'name': stat.name,
                    'color': stat.color,
                    'count': stat.count
                })
            
            # Sort by count (highest first)
            status_breakdown.sort(key=lambda x: x['count'], reverse=True)
            
            return {
                'total_tenders': total_tenders,
                'status_breakdown': status_breakdown
            }
            
        except Exception as e:
            print(f"Error getting tender stats: {str(e)}")
            return {
                'total_tenders': 0,
                'status_breakdown': []
            }


   
      
class TenderCategoryService:
        """Tender category management services"""
        
        @staticmethod
        def create_default_categories():
            """Create default tender categories"""
            default_categories = [
                {'name': 'Construction', 'description': 'Construction and infrastructure projects'},
                {'name': 'IT Services', 'description': 'Information technology services and solutions'},
                {'name': 'Consulting', 'description': 'Professional consulting services'},
                {'name': 'Supplies', 'description': 'General supplies and materials'},
                {'name': 'Equipment', 'description': 'Equipment purchase and maintenance'},
                {'name': 'Services', 'description': 'General services and support'}
            ]
            
            try:
                for category_data in default_categories:
                    if not TenderCategory.query.filter_by(name=category_data['name']).first():
                        category = TenderCategory(**category_data)
                        db.session.add(category)
                
                db.session.commit()
                return True, "Default categories created successfully"
            except Exception as e:
                db.session.rollback()
                return False, f"Error creating default categories: {str(e)}"
        
        @staticmethod
        def get_all_categories():
            """Get all active categories"""
            return TenderCategory.query.filter_by(is_active=True).all()
        
        @staticmethod
        def create_category(name, description=None):
            """Create new category"""
            try:
                if TenderCategory.query.filter_by(name=name).first():
                    return None, "Category already exists"
                
                category = TenderCategory(name=name, description=description)
                db.session.add(category)
                db.session.commit()
                return category, "Category created successfully"
            except Exception as e:
                db.session.rollback()
                return None, f"Error creating category: {str(e)}"

class TenderStatusService:
    """Tender status management services"""
    
    @staticmethod
    def create_default_statuses():
        """Create default tender statuses"""
        default_statuses = [
            {'name': 'Draft', 'description': 'Tender being prepared', 'color': '#6c757d', 'sort_order': 1},
            {'name': 'Published', 'description': 'Tender published and open for submissions', 'color': '#28a745', 'sort_order': 2},
            {'name': 'Closed', 'description': 'Submission deadline passed', 'color': '#ffc107', 'sort_order': 3},
            {'name': 'Under Review', 'description': 'Submissions being evaluated', 'color': '#17a2b8', 'sort_order': 4},
            {'name': 'Awarded', 'description': 'Tender awarded to successful bidder', 'color': '#007bff', 'sort_order': 5},
            {'name': 'Cancelled', 'description': 'Tender cancelled', 'color': '#dc3545', 'sort_order': 6}
        ]
        
        try:
            for status_data in default_statuses:
                if not TenderStatus.query.filter_by(name=status_data['name']).first():
                    status = TenderStatus(**status_data)
                    db.session.add(status)
            
            db.session.commit()
            return True, "Default statuses created successfully"
        except Exception as e:
            db.session.rollback()
            return False, f"Error creating default statuses: {str(e)}"
    
    @staticmethod
    def get_all_statuses():
        """Get all active statuses"""
        return TenderStatus.query.filter_by(is_active=True).order_by(TenderStatus.sort_order).all()

class DocumentTypeService:
    """Document type management services"""
    
    @staticmethod
    def create_default_document_types():
        """Create default document types"""
        default_types = [
            {'name': 'RFQ', 'description': 'Request for Quotation', 'allowed_extensions': '.pdf,.doc,.docx', 'max_size_mb': 10},
            {'name': 'RFP', 'description': 'Request for Proposal', 'allowed_extensions': '.pdf,.doc,.docx', 'max_size_mb': 10},
            {'name': 'Technical Specification', 'description': 'Technical specifications document', 'allowed_extensions': '.pdf,.doc,.docx,.xls,.xlsx', 'max_size_mb': 15},
            {'name': 'Quote', 'description': 'Vendor quotation', 'allowed_extensions': '.pdf,.doc,.docx,.xls,.xlsx', 'max_size_mb': 10},
            {'name': 'Proposal', 'description': 'Vendor proposal', 'allowed_extensions': '.pdf,.doc,.docx,.ppt,.pptx', 'max_size_mb': 25},
            {'name': 'Supporting Document', 'description': 'Additional supporting documents', 'allowed_extensions': '.pdf,.doc,.docx,.jpg,.png', 'max_size_mb': 5}
        ]
        
        try:
            for doc_type_data in default_types:
                if not DocumentType.query.filter_by(name=doc_type_data['name']).first():
                    doc_type = DocumentType(**doc_type_data)
                    db.session.add(doc_type)
            
            db.session.commit()
            return True, "Default document types created successfully"
        except Exception as e:
            db.session.rollback()
            return False, f"Error creating document types: {str(e)}"
    
    @staticmethod
    def get_all_document_types():
        """Get all active document types"""
        return DocumentType.query.filter_by(is_active=True).all()

class TenderDocumentService:
    """Tender document management services"""
    
    @staticmethod
    def save_document(file, tender_id, document_type_id, uploaded_by, upload_folder):
        """Save uploaded document"""
        try:
            # Validate file
            if not file or file.filename == '':
                return None, "No file selected"
            
            # Get document type for validation
            doc_type = DocumentType.query.get(document_type_id)
            if not doc_type:
                return None, "Invalid document type"
            
            # Validate file extension
            file_ext = os.path.splitext(file.filename)[1].lower()
            allowed_extensions = doc_type.get_allowed_extensions_list()
            if allowed_extensions and file_ext not in allowed_extensions:
                return None, f"File type {file_ext} not allowed. Allowed types: {', '.join(allowed_extensions)}"
            
            # Generate secure filename
            original_filename = file.filename
            filename = secure_filename(f"{tender_id}_{document_type_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{original_filename}")
            
            # Create upload directory if it doesn't exist
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            
            # Save file
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Validate file size
            max_size_bytes = doc_type.max_size_mb * 1024 * 1024
            if file_size > max_size_bytes:
                os.remove(file_path)  # Remove the uploaded file
                return None, f"File size exceeds maximum allowed size of {doc_type.max_size_mb}MB"
            
            # Create document record
            document = TenderDocument(
                filename=filename,
                original_filename=original_filename,
                file_path=file_path,
                file_size=file_size,
                mime_type=file.mimetype,
                tender_id=tender_id,
                document_type_id=document_type_id,
                uploaded_by=uploaded_by
            )
            
            db.session.add(document)
            db.session.commit()
            return document, "Document uploaded successfully"
            
        except Exception as e:
            db.session.rollback()
            return None, f"Error uploading document: {str(e)}"
    
    @staticmethod
    def get_tender_documents(tender_id):
        """Get all documents for a tender"""
        return TenderDocument.query.filter_by(tender_id=tender_id).all()
    
    @staticmethod
    def delete_document(document_id):
        """Delete document"""
        try:
            document = TenderDocument.query.get(document_id)
            if not document:
                return False, "Document not found"
            
            # Remove file from filesystem
            if os.path.exists(document.file_path):
                os.remove(document.file_path)
            
            db.session.delete(document)
            db.session.commit()
            return True, "Document deleted successfully"
        except Exception as e:
            db.session.rollback()
            return False, f"Error deleting document: {str(e)}"
        
class CustomFieldService:
    """Custom field management services"""
    
    @staticmethod
    def create_custom_field(field_name, field_label, field_type, created_by, 
                           field_options=None, is_required=False):
        """Create new custom field"""
        try:
            if CustomField.query.filter_by(field_name=field_name).first():
                return None, "Field name already exists"
            
            custom_field = CustomField(
                field_name=field_name,
                field_label=field_label,
                field_type=field_type,
                is_required=is_required,
                created_by=created_by
            )
            
            if field_options:
                custom_field.set_field_options(field_options)
            
            db.session.add(custom_field)
            db.session.commit()
            return custom_field, "Custom field created successfully"
        except Exception as e:
            db.session.rollback()
            return None, f"Error creating custom field: {str(e)}"
    
    @staticmethod
    def get_all_custom_fields():
        """Get all active custom fields"""
        return CustomField.query.filter_by(is_active=True).order_by(CustomField.sort_order).all()
    
    @staticmethod
    def update_custom_field(field_id, field_label, field_type, field_options=None, is_required=False):
        """Update custom field"""
        try:
            custom_field = CustomField.query.get(field_id)
            if not custom_field:
                return False, "Custom field not found"
            
            custom_field.field_label = field_label
            custom_field.field_type = field_type
            custom_field.is_required = is_required
            
            if field_options is not None:
                custom_field.set_field_options(field_options)
            
            db.session.commit()
            return True, "Custom field updated successfully"
        except Exception as e:
            db.session.rollback()
            return False, f"Error updating custom field: {str(e)}"
    
    @staticmethod
    def delete_custom_field(field_id):
        """Delete custom field"""
        try:
            custom_field = CustomField.query.get(field_id)
            if not custom_field:
                return False, "Custom field not found"
            
            custom_field.is_active = False
            db.session.commit()
            return True, "Custom field deleted successfully"
        except Exception as e:
            db.session.rollback()
            return False, f"Error deleting custom field: {str(e)}"
    
    @staticmethod
    def get_custom_field_by_id(field_id):
        """Get custom field by ID"""
        return CustomField.query.get(field_id)
    
@staticmethod
def reorder_custom_fields(field_orders):
        """Update the sort order of custom fields"""
        try:
            for field_id, sort_order in field_orders.items():
                custom_field = CustomField.query.get(field_id)
                if custom_field:
                    custom_field.sort_order = sort_order
            
            db.session.commit()
            return True, "Custom field order updated successfully"
        except Exception as e:
            db.session.rollback()
            return False, f"Error updating field order: {str(e)}"

# Additional utility functions that might be useful

class ReportService:
    """Report generation services"""
    
    @staticmethod
    def generate_tender_summary_report(company_id=None, start_date=None, end_date=None):
        """Generate a comprehensive tender summary report"""
        try:
            # Base query
            query = Tender.query
            
            # Apply company filter if provided
            if company_id:
                query = query.filter(Tender.company_id == company_id)
            
            # Apply date filters if provided
            if start_date:
                query = query.filter(Tender.created_at >= start_date)
            if end_date:
                query = query.filter(Tender.created_at <= end_date)
            
            tenders = query.all()
            
            # Calculate statistics
            total_tenders = len(tenders)
            
            # Status breakdown
            status_counts = {}
            category_counts = {}
            monthly_counts = {}
            
            for tender in tenders:
                # Status breakdown
                status_name = tender.status.name
                status_counts[status_name] = status_counts.get(status_name, 0) + 1
                
                # Category breakdown
                category_name = tender.category.name
                category_counts[category_name] = category_counts.get(category_name, 0) + 1
                
                # Monthly breakdown
                month_key = tender.created_at.strftime('%Y-%m')
                monthly_counts[month_key] = monthly_counts.get(month_key, 0) + 1
            
            return {
                'total_tenders': total_tenders,
                'status_breakdown': status_counts,
                'category_breakdown': category_counts,
                'monthly_breakdown': monthly_counts,
                'tenders': tenders
            }
            
        except Exception as e:
            return None, f"Error generating report: {str(e)}"
    
    @staticmethod
    def get_tender_analytics(company_id=None):
        """Get tender analytics data for charts and graphs"""
        try:
            # Base query for tenders
            if company_id:
                tenders = Tender.query.filter_by(company_id=company_id).all()
            else:
                tenders = Tender.query.all()
            
            # Calculate completion rates
            total_tenders = len(tenders)
            if total_tenders == 0:
                return {
                    'completion_rate': 0,
                    'average_duration': 0,
                    'status_distribution': {},
                    'category_performance': {}
                }
            
            # Status distribution for pie charts
            status_distribution = {}
            for tender in tenders:
                status = tender.status.name
                if status not in status_distribution:
                    status_distribution[status] = {
                        'count': 0,
                        'color': tender.status.color
                    }
                status_distribution[status]['count'] += 1
            
            # Category performance
            category_performance = {}
            for tender in tenders:
                category = tender.category.name
                if category not in category_performance:
                    category_performance[category] = {
                        'total': 0,
                        'completed': 0,
                        'in_progress': 0
                    }
                
                category_performance[category]['total'] += 1
                
                if tender.status.name in ['Awarded', 'Completed']:
                    category_performance[category]['completed'] += 1
                elif tender.status.name in ['Published', 'Under Review']:
                    category_performance[category]['in_progress'] += 1
            
            # Calculate average tender duration (for completed tenders)
            completed_tenders = [t for t in tenders if t.status.name in ['Awarded', 'Completed']]
            average_duration = 0
            if completed_tenders:
                total_duration = 0
                count = 0
                for tender in completed_tenders:
                    if tender.submission_deadline and tender.created_at:
                        duration = (tender.submission_deadline - tender.created_at).days
                        if duration > 0:
                            total_duration += duration
                            count += 1
                
                if count > 0:
                    average_duration = total_duration / count
            
            # Completion rate
            completed_count = len([t for t in tenders if t.status.name in ['Awarded', 'Completed']])
            completion_rate = (completed_count / total_tenders) * 100 if total_tenders > 0 else 0
            
            return {
                'completion_rate': round(completion_rate, 2),
                'average_duration': round(average_duration, 1),
                'status_distribution': status_distribution,
                'category_performance': category_performance,
                'total_tenders': total_tenders,
                'completed_tenders': completed_count
            }
            
        except Exception as e:
            return None, f"Error generating analytics: {str(e)}"

class ValidationService:
    """Data validation services"""
    
    @staticmethod
    def validate_tender_data(title, category_id, status_id, submission_deadline=None, opening_date=None):
        """Validate tender data before creation/update"""
        errors = []
        
        # Title validation
        if not title or len(title.strip()) < 3:
            errors.append("Title must be at least 3 characters long")
        
        if len(title) > 200:
            errors.append("Title cannot exceed 200 characters")
        
        # Category validation
        if not category_id:
            errors.append("Category is required")
        else:
            category = TenderCategory.query.get(category_id)
            if not category or not category.is_active:
                errors.append("Invalid or inactive category selected")
        
        # Status validation
        if not status_id:
            errors.append("Status is required")
        else:
            status = TenderStatus.query.get(status_id)
            if not status or not status.is_active:
                errors.append("Invalid or inactive status selected")
        
        # Date validation
        if submission_deadline and opening_date:
            if submission_deadline <= opening_date:
                errors.append("Submission deadline must be after opening date")
        
        if opening_date and opening_date < datetime.now():
            errors.append("Opening date cannot be in the past")
        
        return errors
    
    @staticmethod
    def validate_custom_field_data(field_name, field_label, field_type, field_options=None):
        """Validate custom field data"""
        errors = []
        
        # Field name validation
        if not field_name or len(field_name.strip()) < 2:
            errors.append("Field name must be at least 2 characters long")
        
        # Check for valid field name format (no spaces, special chars)
        import re
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', field_name):
            errors.append("Field name must start with a letter and contain only letters, numbers, and underscores")
        
        # Field label validation
        if not field_label or len(field_label.strip()) < 2:
            errors.append("Field label must be at least 2 characters long")
        
        # Field type validation
        valid_types = ['text', 'number', 'date', 'textarea', 'select', 'checkbox']
        if field_type not in valid_types:
            errors.append(f"Field type must be one of: {', '.join(valid_types)}")
        
        # Options validation for select fields
        if field_type == 'select':
            if not field_options or len(field_options) < 2:
                errors.append("Select fields must have at least 2 options")
        
        return errors
    
    @staticmethod
    def validate_file_upload(file, document_type_id):
        """Validate file upload"""
        errors = []
        
        if not file or file.filename == '':
            errors.append("No file selected")
            return errors
        
        # Get document type
        doc_type = DocumentType.query.get(document_type_id)
        if not doc_type:
            errors.append("Invalid document type")
            return errors
        
        # Check file extension
        file_ext = os.path.splitext(file.filename)[1].lower()
        allowed_extensions = doc_type.get_allowed_extensions_list()
        
        if allowed_extensions and file_ext not in allowed_extensions:
            errors.append(f"File type {file_ext} not allowed. Allowed types: {', '.join(allowed_extensions)}")
        
        # File size validation would need to be done after saving temporarily
        # This is handled in the TenderDocumentService.save_document method
        
        return errors

class SearchService:
    """Search and filtering services"""
    
    @staticmethod
    def search_tenders(search_term, company_id=None, status_id=None, category_id=None, limit=50):
        """Search tenders with various filters"""
        try:
            query = Tender.query
            
            # Apply company filter if provided
            if company_id:
                query = query.filter(Tender.company_id == company_id)
            
            # Apply status filter if provided
            if status_id:
                query = query.filter(Tender.status_id == status_id)
            
            # Apply category filter if provided
            if category_id:
                query = query.filter(Tender.category_id == category_id)
            
            # Apply search term if provided
            if search_term:
                search_pattern = f"%{search_term}%"
                query = query.filter(
                    db.or_(
                        Tender.title.ilike(search_pattern),
                        Tender.description.ilike(search_pattern),
                        Tender.reference_number.ilike(search_pattern)
                    )
                )
            
            # Order by creation date (newest first) and limit results
            tenders = query.order_by(Tender.created_at.desc()).limit(limit).all()
            
            return tenders
            
        except Exception as e:
            return []
    
    @staticmethod
    def get_tender_suggestions(partial_title, company_id=None, limit=10):
        """Get tender title suggestions for autocomplete"""
        try:
            query = Tender.query
            
            if company_id:
                query = query.filter(Tender.company_id == company_id)
            
            if partial_title:
                search_pattern = f"%{partial_title}%"
                query = query.filter(Tender.title.ilike(search_pattern))
            
            suggestions = query.with_entities(Tender.title).distinct().limit(limit).all()
            return [suggestion[0] for suggestion in suggestions]
            
        except Exception as e:
            return []
class TenderHistoryService:
    """Service for managing tender history and audit logs"""
    
    @staticmethod
    def log_action(tender_id, action_type, action_description, performed_by_id, details=None):
        """
        Log a tender action to the history
        
        Args:
            tender_id (int): ID of the tender
            action_type (str): Type of action (CREATE, UPDATE, DELETE, etc.)
            action_description (str): Human readable description
            performed_by_id (int): ID of user who performed the action
            details (dict, optional): Additional structured data
        """
        try:
            # Get client IP address
            ip_address = request.remote_addr if request else None
            
            history_entry = TenderHistory(
                tender_id=tender_id,
                action_type=action_type,
                action_description=action_description,
                details=details,
                performed_by_id=performed_by_id,
                ip_address=ip_address
            )
            
            db.session.add(history_entry)
            db.session.commit()
            
            return history_entry, "Action logged successfully"
        except Exception as e:
            db.session.rollback()
            return None, f"Error logging action: {str(e)}"
    
    # Specific logging methods for different actions
    @staticmethod
    def log_tender_created(tender_id, performed_by_id, tender_title):
        """Log tender creation"""
        return TenderHistoryService.log_action(
            tender_id=tender_id,
            action_type="TENDER_CREATED",
            action_description=f"Tender '{tender_title}' was created",
            performed_by_id=performed_by_id,
            details={"tender_title": tender_title}
        )
    
    @staticmethod
    def log_tender_updated(tender_id, performed_by_id, changes):
        """Log tender updates"""
        change_descriptions = []
        for field, change in changes.items():
            if field == 'status':
                change_descriptions.append(f"Status changed from '{change['old']}' to '{change['new']}'")
            elif field == 'category':
                change_descriptions.append(f"Category changed from '{change['old']}' to '{change['new']}'")
            else:
                change_descriptions.append(f"{field.title()} was updated")
        
        description = "Tender updated: " + ", ".join(change_descriptions)
        
        return TenderHistoryService.log_action(
            tender_id=tender_id,
            action_type="TENDER_UPDATED",
            action_description=description,
            performed_by_id=performed_by_id,
            details={"changes": changes}
        )
    
    @staticmethod
    def log_tender_deleted(tender_id, performed_by_id, tender_title):
        """Log tender deletion"""
        return TenderHistoryService.log_action(
            tender_id=tender_id,
            action_type="TENDER_DELETED",
            action_description=f"Tender '{tender_title}' was deleted",
            performed_by_id=performed_by_id,
            details={"tender_title": tender_title}
        )
    
    @staticmethod
    def log_note_added(tender_id, performed_by_id, note_content):
        """Log note addition"""
        preview = note_content[:100] + "..." if len(note_content) > 100 else note_content
        return TenderHistoryService.log_action(
            tender_id=tender_id,
            action_type="NOTE_ADDED",
            action_description=f"Added note: {preview}",
            performed_by_id=performed_by_id,
            details={"note_content": note_content}
        )
    
    @staticmethod
    def log_note_edited(tender_id, performed_by_id, old_content, new_content):
        """Log note editing"""
        preview = new_content[:100] + "..." if len(new_content) > 100 else new_content
        return TenderHistoryService.log_action(
            tender_id=tender_id,
            action_type="NOTE_EDITED",
            action_description=f"Edited note: {preview}",
            performed_by_id=performed_by_id,
            details={"old_content": old_content, "new_content": new_content}
        )
    
    @staticmethod
    def log_note_deleted(tender_id, performed_by_id, note_content):
        """Log note deletion"""
        preview = note_content[:100] + "..." if len(note_content) > 100 else note_content
        return TenderHistoryService.log_action(
            tender_id=tender_id,
            action_type="NOTE_DELETED",
            action_description=f"Deleted note: {preview}",
            performed_by_id=performed_by_id,
            details={"note_content": note_content}
        )
    
    @staticmethod
    def log_document_uploaded(tender_id, performed_by_id, document_name, document_type):
        """Log document upload"""
        return TenderHistoryService.log_action(
            tender_id=tender_id,
            action_type="DOCUMENT_UPLOADED",
            action_description=f"Uploaded document: {document_name} ({document_type})",
            performed_by_id=performed_by_id,
            details={"document_name": document_name, "document_type": document_type}
        )
    
    @staticmethod
    def log_document_deleted(tender_id, performed_by_id, document_name, document_type):
        """Log document deletion"""
        return TenderHistoryService.log_action(
            tender_id=tender_id,
            action_type="DOCUMENT_DELETED",
            action_description=f"Deleted document: {document_name} ({document_type})",
            performed_by_id=performed_by_id,
            details={"document_name": document_name, "document_type": document_type}
        )
    
    @staticmethod
    def get_tender_history(tender_id, limit=None):
        """Get history for a specific tender"""
        query = TenderHistory.query.filter_by(tender_id=tender_id).order_by(TenderHistory.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @staticmethod
    def get_user_actions(user_id, limit=None):
        """Get all actions performed by a specific user"""
        query = TenderHistory.query.filter_by(performed_by_id=user_id).order_by(TenderHistory.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @staticmethod
    def get_action_stats(tender_id=None):
        """Get statistics about actions"""
        query = TenderHistory.query
        
        if tender_id:
            query = query.filter_by(tender_id=tender_id)
        
        from sqlalchemy import func
        stats = db.session.query(
            TenderHistory.action_type,
            func.count(TenderHistory.id).label('count')
        ).group_by(TenderHistory.action_type).all()
        
        return {stat.action_type: stat.count for stat in stats}



# End of services.py file
