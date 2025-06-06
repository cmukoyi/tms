# create_feature_tables.py
from app import app, db
from models import Feature, CompanyFeature

def create_feature_tables():
    with app.app_context():
        try:
            # Create only the new tables
            db.create_all()
            print("✅ Feature management tables created!")
            
            # Test table creation
            feature_count = Feature.query.count()
            print(f"📊 Features table ready (current count: {feature_count})")
            
        except Exception as e:
            print(f"❌ Error creating tables: {e}")

if __name__ == "__main__":
    create_feature_tables()