# services/__init__.py
"""
Services package for the tender management system.
Contains business logic and service layer functions.
"""

# Import from individual service files in the services directory
from .auth_service import AuthService
from .company_module_service import CompanyModuleService, require_company_module

# Import from the root services.py file
try:
    import sys
    import os
    # Get the parent directory path
    parent_dir = os.path.dirname(os.path.dirname(__file__))
    services_file = os.path.join(parent_dir, "services.py")
    
    if os.path.exists(services_file):
        # Import the original services module
        import importlib.util
        spec = importlib.util.spec_from_file_location("original_services", services_file)
        original_services = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(original_services)
        
        # Export all the services from your original services.py
        CompanyService = getattr(original_services, 'CompanyService', None)
        RoleService = getattr(original_services, 'RoleService', None)
        TenantService = getattr(original_services, 'TenantService', None)
        TenderService = getattr(original_services, 'TenderService', None)
        TenderCategoryService = getattr(original_services, 'TenderCategoryService', None)
        TenderStatusService = getattr(original_services, 'TenderStatusService', None)
        DocumentTypeService = getattr(original_services, 'DocumentTypeService', None)
        TenderDocumentService = getattr(original_services, 'TenderDocumentService', None)
        CustomFieldService = getattr(original_services, 'CustomFieldService', None)
        ReportService = getattr(original_services, 'ReportService', None)
        ValidationService = getattr(original_services, 'ValidationService', None)
        SearchService = getattr(original_services, 'SearchService', None)
        TenderHistoryService = getattr(original_services, 'TenderHistoryService', None)
        
        print("✓ Successfully imported services from services.py")
        
    else:
        print("Warning: services.py file not found in root directory")
        # Create placeholder classes if services.py doesn't exist
        class PlaceholderService:
            @staticmethod
            def placeholder_method():
                raise NotImplementedError("This service needs to be implemented")
        
        CompanyService = PlaceholderService
        RoleService = PlaceholderService
        TenantService = PlaceholderService
        TenderService = PlaceholderService
        TenderCategoryService = PlaceholderService
        TenderStatusService = PlaceholderService
        DocumentTypeService = PlaceholderService
        TenderDocumentService = PlaceholderService
        CustomFieldService = PlaceholderService
        ReportService = PlaceholderService
        ValidationService = PlaceholderService
        SearchService = PlaceholderService
        TenderHistoryService = PlaceholderService

except Exception as e:
    print(f"Error importing services from services.py: {e}")
    
    # Create placeholder classes in case of error
    class PlaceholderService:
        @staticmethod
        def placeholder_method():
            raise NotImplementedError("This service needs to be implemented")
    
    CompanyService = PlaceholderService
    RoleService = PlaceholderService
    TenantService = PlaceholderService
    TenderService = PlaceholderService
    TenderCategoryService = PlaceholderService
    TenderStatusService = PlaceholderService
    DocumentTypeService = PlaceholderService
    TenderDocumentService = PlaceholderService
    CustomFieldService = PlaceholderService
    ReportService = PlaceholderService
    ValidationService = PlaceholderService
    SearchService = PlaceholderService
    TenderHistoryService = PlaceholderService

# Print what we successfully imported
print("✓ AuthService imported from services/auth_service.py")
print("✓ CompanyModuleService imported from services/company_module_service.py")

# Make all services easily importable
__all__ = [
    'AuthService',
    'CompanyModuleService',
    'require_company_module',
    'CompanyService', 
    'RoleService',
    'TenantService',
    'TenderService',
    'TenderCategoryService',
    'TenderStatusService',
    'DocumentTypeService',
    'TenderDocumentService',
    'CustomFieldService',
    'ReportService',
    'ValidationService',
    'SearchService',
    'TenderHistoryService'
]
from .user_service import UserService

# services/__init__.py

# Import existing services
try:
    from .auth_service import AuthService
    print("✓ AuthService imported from services/auth_service.py")
except ImportError as e:
    print(f"Error importing AuthService: {e}")

try:
    from .company_module_service import CompanyModuleService
    print("✓ CompanyModuleService imported from services/company_module_service.py")
except ImportError as e:
    print(f"Error importing CompanyModuleService: {e}")

# Import chatbot service
try:
    from .chatbot_service import TenderChatbot, get_chatbot_suggestions, get_chatbot_quick_stats
    print("✓ TenderChatbot imported from services/chatbot_service.py")
except ImportError as e:
    print(f"Error importing TenderChatbot: {e}")

# Export all services
__all__ = [
    'AuthService',
    'CompanyModuleService', 
    'TenderChatbot',
    'get_chatbot_suggestions',
    'get_chatbot_quick_stats'
]