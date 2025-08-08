# services/chatbot_service.py

import os
import logging
import re
from sqlalchemy import text

# Avoid circular imports by using Flask's current_app context
from flask import current_app

def get_db():
    """Get database instance from Flask app context"""
    try:
        return current_app.extensions['sqlalchemy']
    except (RuntimeError, KeyError):
        # If we're outside Flask context or no db available
        return None

# Optional: OpenAI integration
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

logger = logging.getLogger(__name__)

class TenderChatbot:
    """AI-powered chatbot for tender management queries"""
    
    def __init__(self, app=None):
        self.app = app
        self.openai_enabled = OPENAI_AVAILABLE and bool(os.environ.get('OPENAI_API_KEY'))
        if self.openai_enabled and openai:
            openai.api_key = os.environ.get('OPENAI_API_KEY')
    
    def process_message(self, message, company_id, user_id):
        """Process user message and return response"""
        try:
            cleaned_message = message.lower().strip()
            
            # Try rule-based responses first
            rule_response = self._get_rule_based_response(cleaned_message, company_id)
            if rule_response:
                return rule_response
            
            # Fall back to AI if enabled
            if self.openai_enabled:
                return self._get_ai_response(message, company_id)
            
            return self._get_default_response()
            
        except Exception as e:
            logger.error(f"Chatbot error: {str(e)}")
            return {
                "response": "I'm having trouble processing your request. Please try again.",
                "type": "error"
            }
    
    def _get_rule_based_response(self, message, company_id):
        """Rule-based responses for common queries"""
        
        # Active tenders count
        if any(phrase in message for phrase in ['active tenders', 'how many tenders', 'tender count']):
            count = self._get_active_tender_count(company_id)
            return {
                "response": f"You currently have **{count} active tenders** in your system.",
                "type": "info",
                "data": {"count": count}
            }
        
        # Tenders by deadline
        if any(phrase in message for phrase in ['deadline', 'closing', 'due']):
            if 'week' in message:
                tenders = self._get_tenders_closing_this_week(company_id)
                return {
                    "response": f"You have **{len(tenders)} tenders closing this week**:",
                    "type": "list",
                    "data": tenders
                }
            elif 'today' in message:
                tenders = self._get_tenders_closing_today(company_id)
                return {
                    "response": f"You have **{len(tenders)} tenders closing today**:",
                    "type": "urgent",
                    "data": tenders
                }
            elif 'overdue' in message:
                tenders = self._get_overdue_tenders(company_id)
                return {
                    "response": f"You have **{len(tenders)} overdue tenders** that need attention:",
                    "type": "warning",
                    "data": tenders
                }
        
        # Status queries
        if any(phrase in message for phrase in ['won', 'lost', 'pending', 'status']):
            status_data = self._get_tender_status_summary(company_id)
            return {
                "response": "Here's your tender status summary:",
                "type": "stats",
                "data": status_data
            }
        
        # Notifications
        if any(phrase in message for phrase in ['notifications', 'alerts', 'reminders']):
            notifications = self._get_recent_notifications(company_id)
            return {
                "response": f"You have **{len(notifications)} recent notifications**:",
                "type": "notifications",
                "data": notifications
            }
        
        return None  # No rule matched
    
    def _get_ai_response(self, message, company_id):
        """Get AI-powered response using OpenAI"""
        try:
            context = self._get_company_context(company_id)
            
            prompt = f"""
You are TenderBot, an AI assistant for a tender management system. 

Company Context:
{context}

User Question: {message}

Provide a helpful response about their tenders. Keep responses concise and actionable.
"""
            
            if openai:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=200,
                    temperature=0.7
                )
                
                ai_response = response.choices[0].message.content.strip()
                
                return {
                    "response": ai_response,
                    "type": "ai",
                    "powered_by": "AI"
                }
            
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            
        return self._get_default_response()
    
    def _get_default_response(self):
        """Default response when no rule matches"""
        suggestions = [
            "How many active tenders?",
            "Show tenders closing this week", 
            "What tenders are overdue?",
            "Show tender status summary"
        ]
        
        return {
            "response": "I can help you with your tender information! Try asking:",
            "type": "suggestions",
            "data": suggestions
        }
    
    # Data retrieval methods
    def _get_active_tender_count(self, company_id):
        """Get count of active tenders"""
        try:
            db = get_db()
            if not db:
                return 0
                
            result = db.session.execute(text("""
                SELECT COUNT(*) FROM tenders 
                WHERE company_id = :company_id 
                AND status_id NOT IN (3, 6)
            """), {"company_id": company_id})
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error getting tender count: {e}")
            return 0
    
    def _get_tenders_closing_this_week(self, company_id):
        """Get tenders closing within 7 days"""
        try:
            db = get_db()
            if not db:
                return []
                
            result = db.session.execute(text("""
                SELECT id, title, submission_deadline
                FROM tenders 
                WHERE company_id = :company_id 
                AND submission_deadline BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 7 DAY)
                AND status_id NOT IN (3, 6)
                ORDER BY submission_deadline ASC
            """), {"company_id": company_id})
            
            tenders = []
            for row in result:
                tenders.append({
                    "id": row[0],
                    "title": row[1],
                    "deadline": row[2].strftime("%Y-%m-%d %H:%M") if row[2] else "No deadline"
                })
            return tenders
        except Exception as e:
            logger.error(f"Error getting weekly tenders: {e}")
            return []
    
    def _get_tenders_closing_today(self, company_id):
        """Get tenders closing today"""
        try:
            db = get_db()
            if not db:
                return []
                
            result = db.session.execute(text("""
                SELECT id, title, submission_deadline
                FROM tenders 
                WHERE company_id = :company_id 
                AND DATE(submission_deadline) = CURDATE()
                AND status_id NOT IN (3, 6)
                ORDER BY submission_deadline ASC
            """), {"company_id": company_id})
            
            return [{"id": row[0], "title": row[1], "deadline": row[2]} for row in result]
        except Exception as e:
            logger.error(f"Error getting today's tenders: {e}")
            return []
    
    def _get_overdue_tenders(self, company_id):
        """Get overdue tenders"""
        try:
            db = get_db()
            if not db:
                return []
                
            result = db.session.execute(text("""
                SELECT id, title, submission_deadline
                FROM tenders 
                WHERE company_id = :company_id 
                AND submission_deadline < NOW()
                AND status_id NOT IN (3, 6)
                ORDER BY submission_deadline ASC
            """), {"company_id": company_id})
            
            tenders = []
            for row in result:
                tenders.append({
                    "id": row[0],
                    "title": row[1],
                    "deadline": row[2].strftime("%Y-%m-%d") if row[2] else "No deadline"
                })
            return tenders
        except Exception as e:
            logger.error(f"Error getting overdue tenders: {e}")
            return []
    
    def _get_tender_status_summary(self, company_id):
        """Get tender status summary"""
        try:
            db = get_db()
            if not db:
                return {}
                
            result = db.session.execute(text("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN status_id = 1 THEN 1 END) as active,
                    COUNT(CASE WHEN status_id = 2 THEN 1 END) as submitted,
                    COUNT(CASE WHEN status_id = 3 THEN 1 END) as won,
                    COUNT(CASE WHEN status_id = 4 THEN 1 END) as lost
                FROM tenders 
                WHERE company_id = :company_id
            """), {"company_id": company_id})
            
            row = result.fetchone()
            return {
                "total": row[0],
                "active": row[1], 
                "submitted": row[2],
                "won": row[3],
                "lost": row[4]
            }
        except Exception as e:
            logger.error(f"Error getting status summary: {e}")
            return {}
    
    def _get_recent_notifications(self, company_id):
        """Get recent notifications"""
        try:
            db = get_db()
            if not db:
                return []
                
            # This assumes you have a notifications table - adjust as needed
            result = db.session.execute(text("""
                SELECT id, message, created_at
                FROM notifications 
                WHERE company_id = :company_id 
                ORDER BY created_at DESC
                LIMIT 5
            """), {"company_id": company_id})
            
            notifications = []
            for row in result:
                notifications.append({
                    "id": row[0],
                    "message": row[1],
                    "created_at": row[2].strftime("%Y-%m-%d %H:%M") if row[2] else ""
                })
            return notifications
        except Exception as e:
            logger.error(f"Error getting notifications: {e}")
            return []
    
    def _get_company_context(self, company_id):
        """Get company context for AI"""
        try:
            stats = self._get_tender_status_summary(company_id)
            return f"""
            Total Tenders: {stats.get('total', 0)}
            Active: {stats.get('active', 0)}
            Won: {stats.get('won', 0)}
            Lost: {stats.get('lost', 0)}
            """
        except Exception as e:
            logger.error(f"Error getting company context: {e}")
            return "Limited context available"

# Helper functions
def get_chatbot_suggestions(company_id):
    """Get suggested questions for the chatbot"""
    return [
        "How many active tenders do I have?",
        "Show me tenders closing this week",
        "Which tenders are overdue?",
        "Show my tender status summary"
    ]

def get_chatbot_quick_stats(company_id):
    """Get quick stats for chatbot dashboard"""
    try:
        chatbot = TenderChatbot()
        
        stats = {
            'active_tenders': chatbot._get_active_tender_count(company_id),
            'closing_this_week': len(chatbot._get_tenders_closing_this_week(company_id)),
            'overdue': len(chatbot._get_overdue_tenders(company_id)),
            'notifications': len(chatbot._get_recent_notifications(company_id))
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting quick stats: {e}")
        return {
            'active_tenders': 0,
            'closing_this_week': 0,
            'overdue': 0,
            'notifications': 0
        }