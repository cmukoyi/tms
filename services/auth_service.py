
from datetime import datetime
from models import User, db

class AuthService:
    """Authentication related services"""
    
    @staticmethod
    def login_user(username, password):
        """Authenticate user with username and password"""
        user = User.query.filter_by(username=username, is_active=True).first()
        if user and user.check_password(password):
            user.last_login = datetime.utcnow()
            db.session.commit()
            return user
        return None
    
    @staticmethod
    def create_user(username, email, password, first_name, last_name, company_id, role_id, is_super_admin=False):
        """Create a new user"""
        try:
            # Check if username or email already exists
            if User.query.filter_by(username=username).first():
                return None, "Username already exists"
            
            if User.query.filter_by(email=email).first():
                return None, "Email already exists"
            
            user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                company_id=company_id if company_id else None,
                role_id=role_id,
                is_super_admin=is_super_admin
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            return user, "User created successfully"
        except Exception as e:
            db.session.rollback()
            return None, f"Error creating user: {str(e)}"
    
    @staticmethod
    def update_user(user_id, username, email, password, first_name, last_name, company_id, role_id, is_super_admin=False):
        """Update existing user"""
        try:
            user = User.query.get(user_id)
            if not user:
                return False, "User not found"
            
            # Check if username is taken by another user
            existing_user = User.query.filter(User.username == username, User.id != user_id).first()
            if existing_user:
                return False, "Username already exists"
            
            # Check if email is taken by another user
            existing_user = User.query.filter(User.email == email, User.id != user_id).first()
            if existing_user:
                return False, "Email already exists"
            
            # Update user fields
            user.username = username
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            user.company_id = company_id if company_id else None
            user.role_id = role_id
            user.is_super_admin = is_super_admin
            
            # Update password only if provided
            if password:
                user.set_password(password)
            
            db.session.commit()
            return True, "User updated successfully"
        except Exception as e:
            db.session.rollback()
            return False, f"Error updating user: {str(e)}"
    
    @staticmethod
    def get_user_by_id(user_id):
        """Get user by ID"""
        return User.query.get(user_id)
    
    @staticmethod
    def get_all_users():
        """Get all users"""
        return User.query.all()
    
    @staticmethod
    def get_users_by_company(company_id):
        """Get all users for a specific company"""
        return User.query.filter_by(company_id=company_id, is_active=True).all()

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
