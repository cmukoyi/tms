# fix_existing_records.py - Fix the existing records with NULL codes

from app import app, db
from sqlalchemy import text

def fix_existing_records():
    with app.app_context():
        try:
            print("Checking existing records...")
            
            # First, let's see what features exist
            features_result = db.session.execute(text("SELECT id, code, name FROM features"))
            features = features_result.fetchall()
            
            print("Available features:")
            feature_map = {}
            for feature in features:
                print(f"  ID: {feature[0]}, Code: {feature[1]}, Name: {feature[2]}")
                feature_map[feature[0]] = feature[1]  # Map feature_id to code
            
            print("\nUpdating company_features records with missing codes...")
            
            # Get all company_features with NULL codes but valid feature_ids
            records_result = db.session.execute(text("""
                SELECT cf.id, cf.company_id, cf.feature_id, f.code 
                FROM company_features cf 
                JOIN features f ON cf.feature_id = f.id 
                WHERE cf.code IS NULL
            """))
            
            records = records_result.fetchall()
            
            if records:
                print(f"Found {len(records)} records to update:")
                
                for record in records:
                    cf_id, company_id, feature_id, feature_code = record
                    print(f"  Updating record {cf_id}: setting code to '{feature_code}'")
                    
                    update_sql = text("""
                        UPDATE company_features 
                        SET code = :code 
                        WHERE id = :id
                    """)
                    
                    db.session.execute(update_sql, {
                        'code': feature_code, 
                        'id': cf_id
                    })
                
                db.session.commit()
                print("✅ Records updated successfully!")
            else:
                print("✅ No records need updating!")
            
            print("\nFinal check - all company_features records:")
            final_result = db.session.execute(text("""
                SELECT cf.id, cf.company_id, cf.feature_id, cf.code, cf.enabled, f.code as feature_code
                FROM company_features cf 
                LEFT JOIN features f ON cf.feature_id = f.id
            """))
            
            for row in final_result:
                print(f"  ID: {row[0]}, Company: {row[1]}, Feature_ID: {row[2]}, Code: {row[3]}, Enabled: {row[4]}, Feature_Code: {row[5]}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            db.session.rollback()

if __name__ == "__main__":
    fix_existing_records()