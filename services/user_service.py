"""
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

    @staticmethod
    def get_all():
        """Get all records"""
        # Implementation depends on specific service
        pass

    @staticmethod
    def search(query):
        """Search records"""
        # Implementation depends on specific service
        pass
