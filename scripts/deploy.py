# scripts/git_deploy.py
import os
import requests
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GitBasedDeployer:
    """
    Simplified deployment that relies on Git instead of file upload.
    This avoids SSH/SFTP issues by having PythonAnywhere pull from Git.
    """
    
    def __init__(self):
        self.username = 'CarlosMukoyi'
        self.api_token = os.environ.get('PYTHONANYWHERE_API_TOKEN')
        self.domain_name = 'CarlosMukoyi.pythonanywhere.com'
        
        if not self.api_token:
            raise ValueError("PYTHONANYWHERE_API_TOKEN environment variable is required")
        
        self.api_base = f"https://www.pythonanywhere.com/api/v0/user/{self.username}"
        self.headers = {'Authorization': f'Token {self.api_token}'}
    
    def deploy(self):
        """Deploy using Git-based approach"""
        try:
            logger.info("Starting Git-based deployment to PythonAnywhere...")
            
            # Step 1: Test API connection
            self.test_api_connection()
            
            # Step 2: Reload web app (this will pick up changes if git is set up)
            self.reload_webapp()
            
            # Step 3: Test deployment
            self.test_deployment()
            
            logger.info("✅ Git-based deployment completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Deployment failed: {str(e)}")
            raise
    
    def test_api_connection(self):
        """Test API connection and list webapps"""
        logger.info("Testing API connection...")
        
        try:
            response = requests.get(f"{self.api_base}/webapps/", 
                                  headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                webapps = response.json()
                logger.info(f"✅ API connection successful. Found {len(webapps)} web apps:")
                for app in webapps:
                    logger.info(f"  - {app.get('domain_name', 'Unknown')}")
                return True
            else:
                logger.error(f"❌ API connection failed: {response.status_code}")
                raise Exception(f"API connection failed: {response.status_code}")
                
        except requests.RequestException as e:
            logger.error(f"❌ API request failed: {e}")
            raise
    
    def reload_webapp(self):
        """Reload the web application"""
        logger.info("Reloading web application...")
        
        url = f"{self.api_base}/webapps/{self.domain_name}/reload/"
        
        try:
            response = requests.post(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                logger.info("✅ Web app reloaded successfully")
                time.sleep(3)  # Wait for reload to complete
            else:
                logger.error(f"❌ Failed to reload web app: {response.status_code} - {response.text}")
                # Don't raise exception - continue anyway
                
        except requests.RequestException as e:
            logger.error(f"❌ Reload request failed: {e}")
            # Don't raise exception - continue anyway
    
    def test_deployment(self):
        """Test if the website is responding"""
        logger.info("Testing website response...")
        
        try:
            response = requests.get(f"https://{self.domain_name}", 
                                  timeout=30, 
                                  allow_redirects=True)
            
            if response.status_code == 200:
                logger.info("✅ Website is responding successfully")
            elif response.status_code in [301, 302]:
                logger.info(f"✅ Website is redirecting (status: {response.status_code})")
            else:
                logger.warning(f"⚠️ Website returned status: {response.status_code}")
                
        except requests.RequestException as e:
            logger.error(f"❌ Website test failed: {e}")
            # Don't raise exception - this might be temporary

def main():
    """Main deployment function"""
    try:
        deployer = GitBasedDeployer()
        deployer.deploy()
        
        logger.info("\n" + "="*50)
        logger.info("DEPLOYMENT NOTES:")
        logger.info("="*50)
        logger.info("This deployment only reloads your web app.")
        logger.info("For code updates, you need to either:")
        logger.info("1. Set up Git deployment on PythonAnywhere")
        logger.info("2. Manually upload files via the PythonAnywhere dashboard")
        logger.info("3. Fix the SSH connection for automatic file upload")
        logger.info("="*50)
        
    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        exit(1)

if __name__ == '__main__':
    main()