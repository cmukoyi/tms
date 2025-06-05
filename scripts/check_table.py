# Create a simple script to check your table structure
# Save this as check_table.py and run it

from app import app, db
import pymysql

with app.app_context():
    try:
        # Check what tables exist
        result = db.engine.execute("SHOW TABLES")
        print("Available tables:")
        for row in result:
            print(f"  - {row[0]}")
        
        print("\n" + "="*50)
        
        # Check company_features table structure
        try:
            result = db.engine.execute("DESCRIBE company_features")
            print("company_features table structure:")
            for row in result:
                print(f"  {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]}")
        except Exception as e:
            print(f"Error checking company_features: {e}")
            
            # Maybe the table doesn't exist, let's create it
            print("Attempting to create company_features table...")
            create_sql = """
            CREATE TABLE company_features (
                id INT AUTO_INCREMENT PRIMARY KEY,
                company_id INT NOT NULL,
                feature_id INT,
                code VARCHAR(50) NOT NULL,
                name VARCHAR(100),
                is_enabled BOOLEAN DEFAULT FALSE,
                enabled BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                created_by INT,
                updated_by INT,
                enabled_at DATETIME,
                enabled_by INT,
                FOREIGN KEY (company_id) REFERENCES companies(id),
                UNIQUE KEY unique_company_feature (company_id, code)
            )
            """
            db.engine.execute(create_sql)
            print("Table created successfully!")
            
    except Exception as e:
        print(f"Error: {e}")