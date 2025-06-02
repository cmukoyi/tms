import os
from datetime import timedelta

class Config:
    SECRET_KEY = 'SE0391f521c022d28675ac7d9d2a367cf51c1c6e404a69746cface6170efdacd6e'
    
    # DEVELOPMENT DATABASE - Local settings
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://carlos:Mukoyi@localhost/tender_management'
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Database Engine Options
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 3600,
        'pool_pre_ping': True
    }
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # File Upload Configuration
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size
    
    # Allowed file extensions for uploads
    ALLOWED_EXTENSIONS = {
        'pdf', 'doc', 'docx', 'xls', 'xlsx',
        'ppt', 'pptx', 'txt', 'jpg', 'jpeg', 'png', 'gif'
    }
    
    # Pagination
    TENDERS_PER_PAGE = 20
    USERS_PER_PAGE = 20
    COMPANIES_PER_PAGE = 20
    
    # Application Settings
    APP_NAME = "Tender Management System"
    APP_VERSION = "1.0.0"
    
    # Email Configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    
    # Tender Configuration
    TENDER_REFERENCE_PREFIX = os.environ.get('TENDER_REFERENCE_PREFIX') or 'TND'
    
    @staticmethod
    def init_app(app):
        # Create upload folder if it doesn't exist
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        print(f"📁 Upload folder: {app.config['UPLOAD_FOLDER']}")

class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://carlos:Mukoyi@localhost/tender_management'

class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    # This won't be used in development branch
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://localhost/placeholder'

class TestingConfig(Config):
    TESTING = True
    DEBUG = False
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://carlos:Mukoyi@localhost/tender_management_test'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
