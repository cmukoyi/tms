# scripts/create_db.py

import sys
import os

# Add the root directory (where app.py is) to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db

with app.app_context():
    db.create_all()
    print("Database tables created successfully.")
