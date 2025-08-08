# services/tender_scraping_manager.py

import logging
import schedule
import time
import threading
from datetime import datetime, timedelta
from sqlalchemy import text

# Import database using your existing models structure
try:
    from models import db
except ImportError:
    try:
        from flask import current_app
        db = current_app.extensions['sqlalchemy']
    except:
        print("Warning: Could not import database. Using mock mode.")
        db = None

logger = logging.getLogger(__name__)

class TenderScrapingManager:
    """Manages automated tender scraping and database integration"""
    
    def __init__(self, app=None):
        self.app = app
        self.scraping_active = False
        self.last_scrape_time = None
        self.total_scraped = 0
        
    def start_scheduled_scraping(self):
        """Start the scheduled scraping process"""
        try:
            # Schedule daily scraping at 6 AM
            schedule.every().day.at("06:00").do(self.daily_tender_scraping)
            
            # Schedule updates every 4 hours during business hours
            schedule.every().day.at("08:00").do(self.update_tender_status)
            schedule.every().day.at("12:00").do(self.update_tender_status)
            schedule.every().day.at("16:00").do(self.update_tender_status)
            
            # Start scheduler in background thread
            scheduler_thread = threading.Thread(target=self._run_scheduler)
            scheduler_thread.daemon = True
            scheduler_thread.start()
            
            logger.info("Tender scraping scheduler started")
            
        except Exception as e:
            logger.error(f"Error starting scraping scheduler: {e}")
    
    def _run_scheduler(self):
        """Run the scheduler continuously"""
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in scheduler: {e}")
                time.sleep(300)  # Wait 5 minutes on error
    
    def daily_tender_scraping(self):
        """Run daily tender scraping"""
        try:
            logger.info("Starting daily tender scraping...")
            self.scraping_active = True
            
            # Scrape all municipalities
            tenders = real_tender_scraper.scrape_all_municipalities()
            
            # Save to database
            saved_count = 0
            updated_count = 0
            
            for tender in tenders:
                try:
                    if self.save_tender_to_database(tender):
                        saved_count += 1
                    else:
                        updated_count += 1
                except Exception as e:
                    logger.error(f"Error saving tender {tender.get('tenderNumber', 'Unknown')}: {e}")
            
            self.last_scrape_time = datetime.now()
            self.total_scraped = len(tenders)
            self.scraping_active = False
            
            # Log scraping results
            self.log_scraping_results(len(tenders), saved_count, updated_count)
            
            logger.info(f"Daily scraping completed: {saved_count} new, {updated_count} updated")
            
            return len(tenders)
            
        except Exception as e:
            logger.error(f"Error in daily tender scraping: {e}")
            self.scraping_active = False
            return 0
    
    def save_tender_to_database(self, tender_data):
        """Save scraped tender to database"""
        try:
            # Check if tender already exists
            existing = db.session.execute(text("""
                SELECT id FROM municipal_tenders 
                WHERE tender_number = :tender_number
            """), {'tender_number': tender_data['tenderNumber']}).fetchone()
            
            if existing:
                # Update existing tender
                db.session.execute(text("""
                    UPDATE municipal_tenders SET
                    municipality = :municipality,
                    province = :province,
                    title = :title,
                    description = :description,
                    category = :category,
                    value = :value,
                    closing_date = :closing_date,
                    status = :status,
                    requirements = :requirements,
                    source_url = :source_url,
                    scraped_at = NOW(),
                    updated_at = NOW()
                    WHERE tender_number = :tender_number
                """), {
                    'municipality': tender_data['municipality'],
                    'province': tender_data['province'],
                    'title': tender_data['title'],
                    'description': tender_data.get('description', ''),
                    'category': tender_data.get('category', ''),
                    'value': tender_data.get('value', 0),
                    'closing_date': tender_data.get('closingDate'),
                    'status': tender_data.get('status', 'new'),
                    'requirements': str(tender_data.get('requirements', [])),
                    'source_url': tender_data.get('sourceUrl', ''),
                    'tender_number': tender_data['tenderNumber']
                })
                
                db.session.commit()
                return False  # Updated existing
                
            else:
                # Insert new tender
                result = db.session.execute(text("""
                    INSERT INTO municipal_tenders 
                    (municipality, province, title, description, category, value, tender_number,
                     published_date, closing_date, status, requirements, contact_person, 
                     contact_email, source_url, scraped_at, created_at)
                    VALUES 
                    (:municipality, :province, :title, :description, :category, :value, :tender_number,
                     :published_date, :closing_date, :status, :requirements, :contact_person,
                     :contact_email, :source_url, NOW(), NOW())
                """), {
                    'municipality': tender_data['municipality'],
                    'province': tender_data['province'],
                    'title': tender_data['title'],
                    'description': tender_data.get('description', ''),
                    'category': tender_data.get('category', ''),
                    'value': tender_data.get('value', 0),
                    'tender_number': tender_data['tenderNumber'],
                    'published_date': datetime.now().date(),
                    'closing_date': tender_data.get('closingDate'),
                    'status': tender_data.get('status', 'new'),
                    'requirements': str(tender_data.get('requirements', [])),
                    'contact_person': tender_data.get('contactInfo', {}).get('person', ''),
                    'contact_email': tender_data.get('contactInfo', {}).get('email', ''),
                    'source_url': tender_data.get('sourceUrl', '')
                })
                
                db.session.commit()
                return True  # New tender saved
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving tender to database: {e}")
            raise
    
    def update_tender_status(self):
        """Update tender statuses based on closing dates"""
        try:
            # Update urgent tenders (closing within 2 days)
            db.session.execute(text("""
                UPDATE municipal_tenders 
                SET status = 'urgent'
                WHERE closing_date BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 2 DAY)
                AND status != 'closed'
            """))
            
            # Update closing tenders (closing within 7 days)
            db.session.execute(text("""
                UPDATE municipal_tenders 
                SET status = 'closing'
                WHERE closing_date BETWEEN DATE_ADD(NOW(), INTERVAL 2 DAY) AND DATE_ADD(NOW(), INTERVAL 7 DAY)
                AND status != 'closed'
                AND status != 'urgent'
            """))
            
            # Close expired tenders
            db.session.execute(text("""
                UPDATE municipal_tenders 
                SET status = 'closed'
                WHERE closing_date < NOW()
                AND status != 'closed'
            """))
            
            db.session.commit()
            logger.info("Tender statuses updated successfully")
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating tender statuses: {e}")
    
    def log_scraping_results(self, total_found, new_saved, updated):
        """Log scraping results to database"""
        try:
            db.session.execute(text("""
                INSERT INTO tender_scraping_log 
                (scrape_started_at, scrape_completed_at, status, tenders_found, 
                 new_tenders, updated_tenders, errors_encountered)
                VALUES 
                (:started, NOW(), 'completed', :found, :new, :updated, 0)
            """), {
                'started': self.last_scrape_time or datetime.now(),
                'found': total_found,
                'new': new_saved,
                'updated': updated
            })
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error logging scraping results: {e}")
    
    def get_scraping_status(self):
        """Get current scraping status"""
        return {
            'scraping_active': self.scraping_active,
            'last_scrape_time': self.last_scrape_time,
            'total_scraped': self.total_scraped,
            'next_scrape': self.get_next_scheduled_scrape()
        }
    
    def get_next_scheduled_scrape(self):
        """Get next scheduled scrape time"""
        try:
            jobs = schedule.jobs
            if jobs:
                return min(job.next_run for job in jobs)
            return None
        except:
            return None
    
    def manual_scrape_municipality(self, municipality_name):
        """Manually scrape a specific municipality"""
        try:
            logger.info(f"Manual scraping: {municipality_name}")
            
            # Get municipality config
            config = real_tender_scraper.municipal_configs.get(municipality_name)
            if not config:
                return {'success': False, 'error': 'Municipality not configured'}
            
            # Scrape the municipality
            tenders = real_tender_scraper.scrape_municipality(municipality_name, config)
            
            # Save to database
            saved_count = 0
            for tender in tenders:
                if self.save_tender_to_database(tender):
                    saved_count += 1
            
            return {
                'success': True,
                'tenders_found': len(tenders),
                'tenders_saved': saved_count
            }
            
        except Exception as e:
            logger.error(f"Error in manual scraping: {e}")
            return {'success': False, 'error': str(e)}

# Initialize scraping manager
tender_scraping_manager = TenderScrapingManager()