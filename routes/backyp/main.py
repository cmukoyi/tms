# routes/main.py
from flask import Blueprint, render_template
from utils.helpers import get_local_time

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    """Home page"""
    current_date = get_local_time()
    return render_template('home.html')