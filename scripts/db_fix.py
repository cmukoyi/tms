# database_fix.py - Save this file and run it to fix your database

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from sqlalchemy import text

def fix_database():
    with app.app_context():
        try:
            print("Checking current table structure...")
            
            # Check what columns exist
            result = db.session.execute(text("DESCRIBE company_features"))
            existing_columns = []
            print("\nCurrent columns in company_features:")
            for row in result:
                column_name = row[0]
                column_type = row[1]
                existing_columns.append(column_name)
                print(f"  ✓ {column_name} ({column_type})")
            
            print(f"\nFound {len(existing_columns)} existing columns")
            
            # Define required columns
            required_columns = {
                'code': 'VARCHAR(50)',
                'name': 'VARCHAR(100)',
                'is_enabled': 'BOOLEAN DEFAULT FALSE',
                'created_at': 'DATETIME DEFAULT CURRENT_TIMESTAMP',
                'updated_at': 'DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP',
                'created_by': 'INT',
                'updated_by': 'INT'
            }
            
            print("\nAdding missing columns...")
            
            # Add missing columns
            for column_name, column_def in required_columns.items():
                if column_name not in existing_columns:
                    try:
                        sql = f"ALTER TABLE company_features ADD COLUMN {column_name} {column_def}"
                        print(f"  Adding: {column_name}")
                        db.session.execute(text(sql))
                        db.session.commit()
                        print(f"  ✓ Successfully added {column_name}")
                    except Exception as e:
                        print(f"  ✗ Error adding {column_name}: {e}")
                else:
                    print(f"  ✓ {column_name} already exists")
            
            print("\n" + "="*50)
            print("Final table structure:")
            
            # Show final structure
            result = db.session.execute(text("DESCRIBE company_features"))
            for row in result:
                print(f"  {row[0]} | {row[1]} | {row[2]}")
            
            print("\n✅ Database structure fixed!")
            print("\nYou can now restart your Flask app.")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            print("\nTrying to create the table from scratch...")
            
            # Create table if it doesn't exist
            try:
                create_sql = """
                CREATE TABLE IF NOT EXISTS company_features (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    company_id INT NOT NULL,
                    feature_id INT,
                    code VARCHAR(50),
                    name VARCHAR(100),
                    is_enabled BOOLEAN DEFAULT FALSE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    created_by INT,
                    updated_by INT,
                    FOREIGN KEY (company_id) REFERENCES companies(id),
                    UNIQUE KEY unique_company_code (company_id, code)
                )
                """
                db.session.execute(text(create_sql))
                db.session.commit()
                print("✅ Table created successfully!")
                
            except Exception as create_error:
                print(f"❌ Could not create table: {create_error}")

if __name__ == "__main__":
    print("🔧 Fixing company_features table structure...")
    fix_database()