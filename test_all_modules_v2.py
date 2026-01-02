#!/usr/bin/env python3
"""
Comprehensive Module Testing Script
Tests all 38 premium modules to ensure they work properly
"""
import requests
import json
from datetime import datetime

class ModuleTester:
    def __init__(self, base_url="http://localhost:5001"):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = []
        
    def login(self, email="testuser@example.com", password="password"):
        """Login to get session cookie"""
        response = self.session.post(
            f"{self.base_url}/login",
            data={"email": email, "password": password},
            allow_redirects=False
        )
        return response.status_code in [200, 302]
    
    def test_url(self, url, module_name, expected_status=200):
        """Test a specific URL and check response"""
        try:
            response = self.session.get(f"{self.base_url}{url}")
            success = response.status_code == expected_status
            
            # Check for common error indicators
            error_indicators = ['TemplateNotFound', 'Internal Server Error', 'Traceback']
            has_error = any(indicator in response.text for indicator in error_indicators)
            
            result = {
                'module': module_name,
                'url': url,
                'status': response.status_code,
                'success': success and not has_error,
                'error': has_error,
                'length': len(response.text)
            }
            
            self.results.append(result)
            return result
            
        except Exception as e:
            result = {
                'module': module_name,
                'url': url,
                'status': 0,
                'success': False,
                'error': True,
                'exception': str(e)
            }
            self.results.append(result)
            return result
    
    def test_all_modules(self):
        """Test all premium modules"""
        print("=" * 80)
        print("COMPREHENSIVE MODULE TEST - ALL 38 PREMIUM FEATURES")
        print("=" * 80)
        print(f"Testing at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Login first
        print("Logging in...")
        if self.login():
            print("✓ Login successful\n")
        else:
            print("✗ Login failed\n")
            return
        
        # Define all modules to test
        modules = [
            # Core Premium Modules
            ("Export Data", "/export/"),
            ("Bulk Operations", "/bulk/"),
            ("Analytics", "/analytics/dashboard"),
            ("Reporting", "/reports/dashboard"),
            ("Win/Loss Analysis", "/win-loss/dashboard"),
            
            # Advanced Modules
            ("Document Management", "/documents/"),
            ("Template Library", "/templates/"),
            ("Collaborative Workspace", "/workspace/"),
            ("CRM", "/crm/"),
            ("BBBEE Tracker", "/bbbee/"),
            
            # AI & Automation
            ("Compliance Q&A", "/compliance/"),
            ("AI Tender Writer", "/ai-writer/"),
            ("Predictive Scoring", "/predictive/"),
            ("Tender Scraper", "/scraper/"),
            ("Resource Planner", "/resources/"),
            
            # Integrations
            ("API Access", "/api/"),
            ("Email/Calendar Integration", "/integrations/"),
            ("Advanced Search", "/search/advanced"),
            
            # Placeholder Modules (may show "coming soon")
            ("Version Control", "/version-control/"),
            ("Mobile App", "/mobile/"),
            ("White Label", "/white-label/"),
            ("Multi-Currency", "/multi-currency/"),
            ("Workflow Automation", "/workflow-automation/"),
            ("Custom Fields", "/custom-fields/"),
            ("Audit Trail", "/audit-trail/"),
            ("Role Permissions", "/role-permissions/"),
            ("Data Backup", "/data-backup/"),
            ("SSO Integration", "/sso/"),
            ("Two-Factor Auth", "/2fa/"),
            ("Email Campaigns", "/email-campaigns/"),
            ("SMS Notifications", "/sms-notifications/"),
            ("Video Conferencing", "/video-conferencing/"),
            ("E-Signature", "/e-signature/"),
            ("Blockchain Verification", "/blockchain/"),
            ("Tender Marketplace", "/marketplace/"),
            ("Supplier Database", "/supplier-database/"),
            ("Contract Management", "/contract-management/"),
        ]
        
        # Test each module
        print("Testing modules...")
        print("-" * 80)
        
        success_count = 0
        error_count = 0
        
        for module_name, url in modules:
            result = self.test_url(url, module_name)
            
            if result['success']:
                print(f"✓ {module_name:.<50} OK (Status: {result['status']})")
                success_count += 1
            else:
                print(f"✗ {module_name:.<50} FAIL (Status: {result['status']})")
                error_count += 1
        
        # Print summary
        print()
        print("=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"Total Modules Tested: {len(modules)}")
        print(f"✓ Successful: {success_count}")
        print(f"✗ Failed: {error_count}")
        print(f"Success Rate: {(success_count/len(modules)*100):.1f}%")
        print()
        
        # List failures
        if error_count > 0:
            print("FAILED MODULES:")
            print("-" * 80)
            for result in self.results:
                if not result['success']:
                    print(f"  • {result['module']} ({result['url']})")
                    if 'exception' in result:
                        print(f"    Error: {result['exception']}")
            print()
        
        print("=" * 80)
        return self.results

def main():
    """Main test function"""
    tester = ModuleTester()
    results = tester.test_all_modules()
    
    # Save results to file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"test_results_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Test results saved to: {filename}")
    print()

if __name__ == "__main__":
    main()
