# imports.py

# Standard library
import os
import io
import json
import calendar
from decimal import Decimal
from datetime import datetime, timedelta
from functools import wraps
from zoneinfo import ZoneInfo
import tzlocal  # pip install tzlocal

# MySQL
import pymysql
pymysql.install_as_MySQLdb()

# Flask
from flask import (
    Flask, render_template, request, redirect, url_for, flash, session,
    jsonify, send_file, make_response
)
from flask_login import (
    LoginManager, current_user, login_required
)
from flask_migrate import Migrate
from werkzeug.utils import secure_filename

# SQLAlchemy
from sqlalchemy import func, and_, or_

# Configuration and models
from config import Config
from models import *

# Load env
from dotenv import load_dotenv
load_dotenv()

# Services
from services import (
    AuthService, CompanyService, RoleService, TenantService,
    TenderService, TenderCategoryService, TenderStatusService, 
    DocumentTypeService, TenderDocumentService, CustomFieldService, TenderHistoryService
)
from services.billing_service import BillingService
from services.module_service import ModuleService
from services.company_module_service import CompanyModuleService, require_company_module

# Permissions
from permissions import (
    ModulePermissions, require_module, require_company_admin,
    require_permission, require_role_level
)

# Reporting
import xlsxwriter
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
)
from reportlab.lib.units import inch
from flask_login import login_user, logout_user

from flask import render_template_string
from models import Document
from models import TenderDocument, DocumentType

from werkzeug.utils import secure_filename
from werkzeug.utils import secure_filename
from flask import send_file, send_from_directory

