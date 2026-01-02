# Azure DevOps CI/CD Setup Guide for TMS

## Overview
This guide helps you set up automated deployment from GitHub to Staging and Production environments using Azure DevOps.

## Prerequisites
- Azure DevOps account
- GitHub repository (cmukoyi/tms)
- Staging server (optional)
- Production server (52.238.208.198)

## Setup Steps

### 1. Create Azure DevOps Project
1. Go to https://dev.azure.com
2. Click **New Project**
3. Name: `TMS-Application`
4. Visibility: Private
5. Click **Create**

### 2. Connect GitHub Repository
1. In your project, go to **Project Settings** → **Service connections**
2. Click **New service connection** → **GitHub**
3. Authorize Azure DevOps to access your GitHub account
4. Select repository: `cmukoyi/tms`
5. Name the connection: `GitHub-TMS`

### 3. Create SSH Service Connections

#### For Staging Server (if you have one):
1. Go to **Project Settings** → **Service connections**
2. Click **New service connection** → **SSH**
3. Configure:
   - **Host name:** staging-server-ip
   - **Port:** 22
   - **User name:** adminTelematics
   - **Password/Private key:** [Your SSH key or password]
   - **Service connection name:** TMS-Staging-SSH
4. Click **Save**

#### For Production Server:
1. Repeat above steps with:
   - **Host name:** 52.238.208.198
   - **Port:** 22
   - **User name:** adminTelematics
   - **Password/Private key:** [Your SSH key or password]
   - **Service connection name:** TMS-Production-SSH

### 4. Create Environments with Approvals

#### Create Staging Environment:
1. Go to **Pipelines** → **Environments**
2. Click **New environment**
3. Name: `TMS-Staging`
4. Description: "TMS Staging Environment"
5. Click **Create**

#### Create Production Environment with Approval:
1. Go to **Pipelines** → **Environments**
2. Click **New environment**
3. Name: `TMS-Production`
4. Description: "TMS Production Environment"
5. Click **Create**
6. After created, click on **TMS-Production**
7. Click **⋮** (three dots) → **Approvals and checks**
8. Click **+** → **Approvals**
9. Add approvers (your email)
10. Set timeout: 30 days
11. Instructions: "Review staging deployment before approving production"
12. Click **Create**

### 5. Create the Pipeline

1. Go to **Pipelines** → **Pipelines**
2. Click **New pipeline**
3. Select **GitHub**
4. Select repository: `cmukoyi/tms`
5. Select **Existing Azure Pipelines YAML file**
6. Path: `/azure-pipelines.yml`
7. Click **Continue**
8. Review the pipeline
9. Click **Save** or **Run**

### 6. Configure Variables (Optional)

1. Go to your pipeline → **Edit**
2. Click **Variables** (top right)
3. Add variables:
   - `STAGING_SERVER`: staging-ip-address
   - `PRODUCTION_SERVER`: 52.238.208.198
   - `PYTHON_VERSION`: 3.6

### 7. Prepare Servers

#### On Production Server (and Staging if applicable):

```bash
# Create backup directory
sudo mkdir -p /var/www/tms/backups

# Ensure adminTelematics user has sudo permissions for systemctl
sudo visudo -f /etc/sudoers.d/azuredevops
# Add this line:
adminTelematics ALL=(ALL) NOPASSWD: /bin/systemctl start tms, /bin/systemctl stop tms, /bin/systemctl restart tms, /bin/systemctl status tms, /bin/chown, /bin/chmod

# Ensure .env file is secure and in place
sudo chmod 600 /var/www/tms/.env
```

## How It Works

### Automatic Deployment Flow:

1. **Push to GitHub** → Pipeline triggers automatically
2. **Build Stage** → Validates app, installs dependencies, creates artifact
3. **Deploy to Staging** → Automatically deploys to staging server
4. **Staging Tests** → Health checks run
5. **Wait for Approval** → Email sent to approvers
6. **Deploy to Production** → After approval, deploys to production
7. **Production Tests** → Final health checks

### Manual Triggers:

You can also run the pipeline manually:
1. Go to **Pipelines** → **Pipelines**
2. Click on your pipeline
3. Click **Run pipeline**
4. Select branch (main)
5. Click **Run**

## Pipeline Features

✅ **Automatic backups** before each deployment  
✅ **Health checks** after deployment  
✅ **Rollback capability** using backups  
✅ **Approval gates** for production  
✅ **Keeps last 5 backups** automatically  
✅ **Deployment logging**  

## Rollback Procedure

If deployment fails or issues are found:

```bash
# On the server, list backups
ls -lth /var/www/tms/backups/

# Restore from backup
cd /var/www/tms
sudo systemctl stop tms
tar -xzf backups/tms-backup-YYYYMMDD-HHMMSS.tar.gz -C /
sudo systemctl start tms
```

## Notifications

Configure notifications in Azure DevOps:
1. Go to **Project Settings** → **Notifications**
2. **New subscription**
3. Select events:
   - Build completed
   - Release deployment approval pending
   - Release deployment completed
   - Release deployment failed

## Alternative: Simple Deployment (Without Staging)

If you only want to deploy to production without staging:

1. Remove the `DeployStaging` stage from `azure-pipelines.yml`
2. Change `DeployProduction` to depend on `Build`:
   ```yaml
   dependsOn: Build
   ```

## Monitoring

After deployment, monitor:
- Application logs: `/var/www/tms/logs/tms.log`
- Service status: `sudo systemctl status tms`
- Deployment log: `/var/www/tms/deployment.log`
- Apache logs: `/var/log/apache2/tms_error.log`

## Troubleshooting

### Pipeline Fails on SSH Connection:
- Verify SSH service connection credentials
- Test SSH manually: `ssh adminTelematics@52.238.208.198`

### Deployment Succeeds but App Doesn't Start:
- Check `.env` file exists and has correct permissions
- Check systemd service: `sudo journalctl -u tms -n 50`
- Verify database connectivity

### Health Check Fails:
- Service might need more time to start
- Increase sleep time in health check step
- Check if port 5001 is actually listening

## Cost Optimization

Azure DevOps free tier includes:
- 1 Microsoft-hosted job (1,800 minutes/month)
- 1 self-hosted job (unlimited minutes)
- Unlimited private repos

For production use, consider:
- Using self-hosted agents on your VM
- Parallel jobs for faster builds ($40/month per parallel job)

## Next Steps

1. ✅ Commit `azure-pipelines.yml` to your repo
2. ✅ Follow setup steps above
3. ✅ Test with a small change (update README)
4. ✅ Monitor the pipeline run
5. ✅ Approve production deployment
6. ✅ Verify application works

---

**Questions?** Check Azure DevOps docs: https://docs.microsoft.com/en-us/azure/devops/
