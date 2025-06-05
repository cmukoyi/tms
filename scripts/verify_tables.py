# verify_tables.py
from app import app, db

with app.app_context():
    # Check if tables exist
    inspector = db.inspect(db.engine)
    tables = inspector.get_table_names()
    
    required_tables = ['features', 'company_features']
    
    for table in required_tables:
        if table in tables:
            print(f"✅ Table '{table}' exists")
        else:
            print(f"❌ Table '{table}' missing")
    
    # Check columns
    if 'features' in tables:
        columns = [col['name'] for col in inspector.get_columns('features')]
        print(f"Features columns: {columns}")