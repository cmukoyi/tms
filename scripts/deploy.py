# scripts/deploy.py
import os
import requests
import time
import paramiko
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PythonAnywhereDeployer:
    def __init__(self):
        # Environment variables that should be set in CircleCI
        self.username = 'CarlosMukoyi'  # Your PythonAnywhere username
        self.api_token = os.environ.get('PYTHONANYWHERE_API_TOKEN')
        self.domain_name = 'CarlosMukoyi.pythonanywhere.com'
        
        if not self.api_token:
            raise ValueError("PYTHONANYWHERE_API_TOKEN environment variable is required")
        
        self.api_base = f"https://www.pythonanywhere.com/api/v0/user/{self.username}"
        self.headers = {'Authorization': f'Token {self.api_token}'}
        
        # SSH connection details
        self.ssh_host = 'ssh.pythonanywhere.com'
        self.ssh_username = self.username
        self.ssh_password = os.environ.get('PYTHONANYWHERE_SSH_PASSWORD')
        
        # Project paths
        self.project_path = f'/home/{self.username}/tms'
        self.backup_path = f'/home/{self.username}/tms_backup'
    
    def deploy(self):
        """Main deployment method"""
        try:
            logger.info("Starting deployment to PythonAnywhere...")
            
            # Step 1: Create backup of current deployment
            self.create_backup()
            
            # Step 2: Upload code via SSH
            self.upload_code()
            
            # Step 3: Install dependencies
            self.install_dependencies()
            
            # Step 4: Run database migrations
            self.run_migrations()
            
            # Step 5: Reload web app
            self.reload_webapp()
            
            # Step 6: Test deployment
            self.test_deployment()
            
            logger.info("Deployment completed successfully!")
            
        except Exception as e:
            logger.error(f"Deployment failed: {str(e)}")
            logger.info("Attempting to restore from backup...")
            self.restore_backup()
            raise
    
    def create_backup(self):
        """Create backup of current deployment"""
        logger.info("Creating backup of current deployment...")
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            ssh.connect(
                hostname=self.ssh_host,
                username=self.ssh_username,
                password=self.ssh_password
            )
            
            # Remove old backup and create new one
            commands = [
                f'rm -rf {self.backup_path}',
                f'cp -r {self.project_path} {self.backup_path}'
            ]
            
            for cmd in commands:
                self._execute_ssh_command(ssh, cmd, ignore_errors=True)
                
        finally:
            ssh.close()
    
    def restore_backup(self):
        """Restore from backup in case of deployment failure"""
        logger.info("Restoring from backup...")
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            ssh.connect(
                hostname=self.ssh_host,
                username=self.ssh_username,
                password=self.ssh_password
            )
            
            # Restore from backup
            commands = [
                f'rm -rf {self.project_path}',
                f'cp -r {self.backup_path} {self.project_path}'
            ]
            
            for cmd in commands:
                self._execute_ssh_command(ssh, cmd, ignore_errors=True)
            
            # Reload web app after restore
            self.reload_webapp()
                
        finally:
            ssh.close()
    
    def upload_code(self):
        """Upload code to PythonAnywhere via SSH"""
        logger.info("Uploading code via SSH...")
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            ssh.connect(
                hostname=self.ssh_host,
                username=self.ssh_username,
                password=self.ssh_password
            )
            
            # Create SFTP client
            sftp = ssh.open_sftp()
            
            # Ensure project directory exists
            self._execute_ssh_command(ssh, f'mkdir -p {self.project_path}')
            
            # Upload files (excluding .git, __pycache__, etc.)
            self._upload_directory(sftp, '.', self.project_path, exclude_patterns=[
                '.git', '__pycache__', '*.pyc', '.pytest_cache', 
                'venv', '.env', 'node_modules', '.circleci', '*.log',
                'instance', '.vscode', '.idea', '*.swp', '*.swo'
            ])
            
            sftp.close()
            
        finally:
            ssh.close()
    
    def _upload_directory(self, sftp, local_dir, remote_dir, exclude_patterns=None):
        """Recursively upload directory contents"""
        exclude_patterns = exclude_patterns or []
        
        for item in Path(local_dir).iterdir():
            if any(pattern in str(item) for pattern in exclude_patterns):
                continue
                
            local_path = str(item)
            remote_path = f"{remote_dir}/{item.name}"
            
            if item.is_file():
                logger.info(f"Uploading {local_path} -> {remote_path}")
                try:
                    sftp.put(local_path, remote_path)
                except Exception as e:
                    logger.warning(f"Failed to upload {local_path}: {e}")
            elif item.is_dir():
                try:
                    sftp.mkdir(remote_path)
                except:
                    pass  # Directory might already exist
                self._upload_directory(sftp, local_path, remote_path, exclude_patterns)
    
    def install_dependencies(self):
        """Install Python dependencies"""
        logger.info("Installing dependencies...")
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            ssh.connect(
                hostname=self.ssh_host,
                username=self.ssh_username,
                password=self.ssh_password
            )
            
            commands = [
                f'cd {self.project_path}',
                'python3.9 -m pip install --user --upgrade pip',
                'python3.9 -m pip install --user -r requirements.txt'
            ]
            
            for cmd in commands:
                self._execute_ssh_command(ssh, cmd)
                
        finally:
            ssh.close()
    
    def run_migrations(self):
        """Run database migrations"""
        logger.info("Running database migrations...")
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            ssh.connect(
                hostname=self.ssh_host,
                username=self.ssh_username,
                password=self.ssh_password
            )
            
            # Set environment variables and run migrations
            migration_commands = [
                f'cd {self.project_path}',
                'export FLASK_APP=app.py',
                'export FLASK_ENV=production',
                f'export DATABASE_URL=mysql://{self.username}:${{MYSQL_PASSWORD}}@{self.username}.mysql.pythonanywhere-services.com/{self.username}$tender_management',
                'python3.9 -c "from app import app, db; app.app_context().push(); db.create_all(); print(\'Database tables created/updated successfully\')"'
            ]
            
            for cmd in migration_commands:
                self._execute_ssh_command(ssh, cmd)
                
        finally:
            ssh.close()
    
    def reload_webapp(self):
        """Reload the web application"""
        logger.info("Reloading web application...")
        
        url = f"{self.api_base}/webapps/{self.domain_name}/reload/"
        
        response = requests.post(url, headers=self.headers)
        
        if response.status_code == 200:
            logger.info("Web app reloaded successfully")
            # Wait a moment for the reload to complete
            time.sleep(5)
        else:
            logger.error(f"Failed to reload web app: {response.status_code} - {response.text}")
            raise Exception("Failed to reload web app")
    
    def test_deployment(self):
        """Test if the deployment is working"""
        logger.info("Testing deployment...")
        
        try:
            response = requests.get(f"https://{self.domain_name}", timeout=30)
            if response.status_code == 200:
                logger.info("Deployment test successful - website is responding")
            else:
                logger.warning(f"Deployment test returned status code: {response.status_code}")
        except requests.RequestException as e:
            logger.error(f"Deployment test failed: {e}")
            raise Exception("Deployment test failed")
    
    def _execute_ssh_command(self, ssh, command, ignore_errors=False):
        """Execute SSH command with error handling"""
        logger.info(f"Executing: {command}")
        stdin, stdout, stderr = ssh.exec_command(command)
        
        # Wait for command to complete
        exit_status = stdout.channel.recv_exit_status()
        
        if exit_status != 0 and not ignore_errors:
            error_msg = stderr.read().decode('utf-8')
            logger.error(f"Command failed with exit status {exit_status}: {error_msg}")
            # Don't raise exception for some non-critical failures
            if 'mkdir' not in command and 'rm' not in command:
                raise Exception(f"SSH command failed: {command}")
        else:
            output = stdout.read().decode('utf-8')
            if output.strip():
                logger.info(f"Command output: {output}")

def main():
    """Main deployment function"""
    deployer = PythonAnywhereDeployer()
    deployer.deploy()

if __name__ == '__main__':
    main()