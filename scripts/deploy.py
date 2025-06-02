# scripts/git_deploy.py
import os
import requests
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GitBasedDeployer:
    def __init__(self):
        self.username = 'CarlosMukoyi'
        self.api_token = os.environ.get('PYTHONANYWHERE_API_TOKEN')
        self.domain_name = 'CarlosMukoyi.pythonanywhere.com'
        
        if not self.api_token:
            raise ValueError("PYTHONANYWHERE_API_TOKEN environment variable is required")
        
        self.api_base = f"https://www.pythonanywhere.com/api/v0/user/{self.username}"
        self.headers = {'Authorization': f'Token {self.api_token}'}
    
    def deploy(self):
        logger.info("🔁 Starting deployment...")
        self.reload_webapp()
        self.test_website()
        logger.info("✅ Deployment complete.")

    def reload_webapp(self):
        logger.info("📦 Reloading web app on PythonAnywhere...")
        url = f"{self.api_base}/webapps/{self.domain_name}/reload/"
        try:
            response = requests.post(url, headers=self.headers, timeout=30)
            if response.status_code == 200:
                logger.info("✅ Web app reloaded successfully")
                time.sleep(3)
            else:
                logger.warning(f"⚠️ Reload failed: {response.status_code} - {response.text}")
        except requests.RequestException as e:
            logger.error(f"❌ Reload request failed: {e}")

    def test_website(self):
        logger.info("🌐 Testing website response...")
        try:
            response = requests.get(f"https://{self.domain_name}", timeout=30)
            if response.status_code == 200:
                logger.info("✅ Website is responding")
            elif response.status_code in [301, 302]:
                logger.info(f"✅ Website is redirecting (status: {response.status_code})")
            else:
                logger.warning(f"⚠️ Website returned status: {response.status_code}")
        except requests.RequestException as e:
            logger.warning(f"❌ Website test failed: {e}")

def main():
    try:
        deployer = GitBasedDeployer()
        deployer.deploy()
    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        exit(1)

if __name__ == '__main__':
    main()
