# services/chatbot_service.py

import os
import logging
import re
from datetime import datetime, timedelta
from sqlalchemy import text, and_, or_

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
        
        # Conversation context storage
        self.conversation_contexts = {}
        
        # Enhanced keyword patterns
        self.patterns = self._initialize_patterns()
    
    def _initialize_patterns(self):
        """Initialize enhanced NLP patterns"""
        return {
            'greetings': ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening'],
            'thanks': ['thank', 'thanks', 'appreciate', 'cheers'],
            'count': ['how many', 'count', 'number of', 'total'],
            'deadline': ['deadline', 'closing', 'due', 'expires', 'expiring', 'submission date'],
            'status': ['status', 'state', 'progress', 'condition'],
            'search': ['find', 'search', 'look for', 'locate', 'show me'],
            'compare': ['compare', 'difference', 'versus', 'vs', 'better'],
            'analytics': ['analyze', 'analysis', 'report', 'statistics', 'trends', 'insights'],
            'value': ['value', 'worth', 'amount', 'price', 'cost', 'budget'],
            'category': ['category', 'type', 'department', 'sector'],
            'urgent': ['urgent', 'critical', 'priority', 'asap', 'immediately'],
            'recent': ['recent', 'latest', 'new', 'this month', 'this week'],
            'help': ['help', 'assist', 'guide', 'how to', 'what can']
        }
    
    def process_message(self, message, company_id, user_id, conversation_id=None):
        """Process user message with context awareness"""
        try:
            cleaned_message = message.lower().strip()
            
            # Handle greetings
            if self._is_greeting(cleaned_message):
                return self._get_greeting_response(user_id)
            
            # Handle thanks
            if self._is_thanks(cleaned_message):
                return {
                    "response": "You're welcome! Let me know if you need anything else. 😊",
                    "type": "info"
                }
            
            # Handle help requests
            if self._is_help_request(cleaned_message):
                return self._get_help_response()
            
            # Store context
            if conversation_id:
                if conversation_id not in self.conversation_contexts:
                    self.conversation_contexts[conversation_id] = []
                self.conversation_contexts[conversation_id].append({
                    'message': message,
                    'timestamp': datetime.now()
                })
            
            # Try enhanced rule-based responses
            rule_response = self._get_rule_based_response(cleaned_message, company_id, user_id)
            if rule_response:
                return rule_response
            
            # Fall back to AI if enabled
            if self.openai_enabled:
                return self._get_ai_response(message, company_id, conversation_id)
            
            return self._get_default_response()
            
        except Exception as e:
            logger.error(f"Chatbot error: {str(e)}")
            return {
                "response": "I'm having trouble processing your request. Please try again.",
                "type": "error"
            }
    
    def _is_greeting(self, message):
        """Check if message is a greeting"""
        return any(greet in message for greet in self.patterns['greetings'])
    
    def _is_thanks(self, message):
        """Check if message is thanking"""
        return any(thank in message for thank in self.patterns['thanks'])
    
    def _is_help_request(self, message):
        """Check if message is asking for help"""
        return any(help_word in message for help_word in self.patterns['help'])
    
    def _get_greeting_response(self, user_id):
        """Get personalized greeting"""
        try:
            db = get_db()
            if db:
                result = db.session.execute(text(
                    "SELECT name FROM users WHERE id = :user_id"
                ), {"user_id": user_id})
                row = result.fetchone()
                if row and row[0]:
                    name = row[0].split()[0]  # First name
                    return {
                        "response": f"👋 Hi {name}! I'm TenderBot, your AI assistant for tender management. How can I help you today?",
                        "type": "welcome",
                        "suggestions": [
                            "Show active tenders",
                            "What's closing this week?",
                            "Tender performance summary",
                            "Search for IT tenders"
                        ]
                    }
        except Exception as e:
            logger.error(f"Error getting user name: {e}")
        
        return {
            "response": "👋 Hello! I'm TenderBot. How can I assist you with your tenders today?",
            "type": "welcome",
            "suggestions": [
                "Show active tenders",
                "What's closing this week?",
                "Tender performance summary",
                "Search for IT tenders"
            ]
        }
    
    def _get_help_response(self):
        """Get comprehensive help response"""
        return {
            "response": """**I can help you with:**
            
📊 **Analytics & Reports**
• Tender performance analysis
• Success rate statistics
• Category breakdowns
• Value trends

🔍 **Search & Filter**
• Find tenders by keyword
• Filter by category/department
• Search by value range
• Date-based searches

⏰ **Deadlines & Alerts**
• Upcoming deadlines
• Overdue tenders
• Tenders closing today/this week

📈 **Status & Tracking**
• Active tender count
• Won/Lost summaries
• Pending submissions
• Overall statistics

Try asking questions naturally, like:
• "Show me IT tenders closing this month"
• "What's my success rate for construction tenders?"
• "Find tenders worth more than R500K"
• "Compare this month vs last month"
""",
            "type": "help",
            "suggestions": [
                "Show analytics",
                "Find tenders",
                "What's closing soon?",
                "Performance summary"
            ]
        }
    
    def _get_rule_based_response(self, message, company_id, user_id):
        """Enhanced rule-based responses with multi-intent handling"""
        
        # Extract potential filters
        filters = self._extract_filters(message)
        
        # User-specific queries (check first as they're very specific)
        if 'assigned to' in message or 'for user' in message:
            # Extract username
            username = self._extract_username(message)
            if username:
                user_tenders = self._get_tenders_for_user(company_id, username, filters)
                if user_tenders is not None:
                    return {
                        "response": f"**{user_tenders['count']} tenders** are assigned to **{username}**:",
                        "type": "list",
                        "data": user_tenders['tenders'],
                        "suggestions": ["Show details", "Filter by status", "Upcoming deadlines"]
                    }
        
        # Deadline queries (very specific, check early)
        if any(word in message for word in ['deadline', 'closing', 'due', 'expires', 'expiring']):
            if 'today' in message:
                tenders = self._get_tenders_closing_today(company_id, filters)
                return {
                    "response": f"🚨 You have **{len(tenders)} tenders closing today**:",
                    "type": "urgent",
                    "data": tenders
                }
            elif 'tomorrow' in message:
                tenders = self._get_tenders_closing_tomorrow(company_id, filters)
                return {
                    "response": f"⏰ You have **{len(tenders)} tenders closing tomorrow**:",
                    "type": "warning",
                    "data": tenders
                }
            elif 'week' in message or 'next 7' in message:
                tenders = self._get_tenders_closing_this_week(company_id, filters)
                return {
                    "response": f"📅 You have **{len(tenders)} tenders closing this week**:",
                    "type": "list",
                    "data": tenders,
                    "suggestions": ["Show today's deadlines", "Next month", "Overdue tenders"]
                }
            elif 'overdue' in message:
                tenders = self._get_overdue_tenders(company_id, filters)
                return {
                    "response": f"⚠️ You have **{len(tenders)} overdue tenders** that need attention:",
                    "type": "warning",
                    "data": tenders,
                    "suggestions": ["Extend deadlines", "Mark as lost", "Update status"]
                }
            elif 'month' in message or 'next 30' in message:
                tenders = self._get_tenders_closing_this_month(company_id, filters)
                return {
                    "response": f"📅 **{len(tenders)} tenders closing this month**:",
                    "type": "list",
                    "data": tenders
                }
        
        # Analytics and trends (before general queries)
        if any(phrase in message for phrase in ['analytics', 'analyze', 'analysis', 'report', 'statistics', 'trends', 'insights']):
            if 'success' in message or 'win' in message or 'rate' in message:
                analytics = self._get_success_rate_analytics(company_id, filters)
                return {
                    "response": "📊 **Success Rate Analysis:**",
                    "type": "analytics",
                    "data": analytics,
                    "suggestions": ["Show by category", "Monthly trends", "Compare to last year"]
                }
            elif 'performance' in message or 'trend' in message:
                trends = self._get_performance_trends(company_id, filters)
                return {
                    "response": "📈 **Performance Trends:**",
                    "type": "analytics",
                    "data": trends
                }
            else:
                summary = self._get_comprehensive_analytics(company_id, filters)
                return {
                    "response": "📊 **Comprehensive Analytics Summary:**",
                    "type": "analytics",
                    "data": summary
                }
        
        # Search/Find tenders (check before count)
        if any(phrase in message for phrase in ['find', 'search', 'look for', 'locate']):
            # Don't trigger on count/stats queries
            if not any(word in message for word in ['how many', 'count', 'stats', 'summary', 'analytics', 'rate']):
                tenders = self._search_tenders(message, company_id, filters)
                return {
                    "response": f"I found **{len(tenders)} tenders** matching your criteria:",
                    "type": "list",
                    "data": tenders,
                    "suggestions": ["Show more details", "Filter by value", "Sort by deadline"]
                }
        
        # "Show me" queries - be specific
        if 'show me' in message or 'show' in message:
            if 'won' in message:
                tenders = self._get_tenders_by_status(company_id, 'won', filters)
                return {
                    "response": f"🎉 **{len(tenders)} tenders won**:",
                    "type": "success",
                    "data": tenders,
                    "suggestions": ["Total value won", "Success rate", "Top categories"]
                }
            elif 'lost' in message:
                tenders = self._get_tenders_by_status(company_id, 'lost', filters)
                return {
                    "response": f"📉 **{len(tenders)} tenders lost**:",
                    "type": "info",
                    "data": tenders,
                    "suggestions": ["Analyze why", "Success rate", "Improvement areas"]
                }
            elif 'active' in message:
                count = self._get_active_tender_count(company_id, filters)
                tenders = self._search_tenders('', company_id, filters)  # Get actual list
                return {
                    "response": f"📋 **{count} active tenders**:",
                    "type": "list",
                    "data": tenders[:10],  # Limit to 10
                    "suggestions": ["Filter by category", "Sort by value", "Upcoming deadlines"]
                }
        
        # Comparison queries
        if any(phrase in message for phrase in ['compare', 'comparison', 'difference', 'versus', 'vs', 'better']):
            comparison = self._get_comparison_data(message, company_id)
            return {
                "response": "🔄 **Comparison Analysis:**",
                "type": "comparison",
                "data": comparison
            }
        
        # Category/Department queries
        if any(phrase in message for phrase in ['category', 'categories', 'department', 'breakdown', 'by type']):
            breakdown = self._get_category_breakdown(company_id, filters)
            return {
                "response": "📂 **Category Breakdown:**",
                "type": "breakdown",
                "data": breakdown,
                "suggestions": ["Show top category", "Success by category", "Value by category"]
            }
        
        # Value-based queries
        if any(phrase in message for phrase in ['value', 'worth', 'amount', 'price', 'cost', 'budget']):
            # Make sure it's not asking for count
            if not any(word in message for word in ['how many', 'count']):
                value_stats = self._get_value_statistics(company_id, filters)
                return {
                    "response": "💰 **Value Statistics:**",
                    "type": "stats",
                    "data": value_stats,
                    "suggestions": ["Show highest value tenders", "Average by category", "Monthly totals"]
                }
        
        # Status/Summary queries (not count-specific)
        if any(phrase in message for phrase in ['status', 'summary', 'overview']):
            # Exclude if asking "how many"
            if not any(word in message for word in ['how many', 'count']):
                status_data = self._get_tender_status_summary(company_id)
                return {
                    "response": "📊 **Tender Status Summary:**",
                    "type": "stats",
                    "data": status_data,
                    "suggestions": ["Show won tenders", "Show lost tenders", "Performance trends"]
                }
        
        # Notifications
        if any(phrase in message for phrase in ['notifications', 'notification', 'alerts', 'reminders']):
            notifications = self._get_recent_notifications(company_id)
            return {
                "response": f"🔔 You have **{len(notifications)} recent notifications**:",
                "type": "notifications",
                "data": notifications
            }
        
        # Count queries (check these LAST and be very specific)
        if 'how many' in message or 'count of' in message or 'number of' in message:
            # Check for specific status in the query
            if 'won' in message:
                tenders = self._get_tenders_by_status(company_id, 'won', filters)
                return {
                    "response": f"🎉 **{len(tenders)} tenders won**:",
                    "type": "success",
                    "data": tenders,
                    "suggestions": ["Total value won", "Success rate", "Top categories"]
                }
            elif 'lost' in message:
                tenders = self._get_tenders_by_status(company_id, 'lost', filters)
                return {
                    "response": f"📉 **{len(tenders)} tenders lost**:",
                    "type": "info",
                    "data": tenders,
                    "suggestions": ["Analyze why", "Success rate", "Improvement areas"]
                }
            elif 'active' in message or 'open' in message:
                count = self._get_active_tender_count(company_id, filters)
                filter_text = self._format_filter_text(filters)
                return {
                    "response": f"You currently have **{count} active tenders** {filter_text}.",
                    "type": "info",
                    "data": {"count": count},
                    "suggestions": ["Show me these tenders", "What's the total value?", "Category breakdown"]
                }
            else:
                # Only for very general "how many tenders" without any other context
                count = self._get_total_tender_count(company_id, filters)
                filter_text = self._format_filter_text(filters)
                return {
                    "response": f"You have **{count} total tenders** {filter_text}.",
                    "type": "info",
                    "data": {"count": count},
                    "suggestions": ["Show active only", "Status breakdown", "Category analysis"]
                }
        
        return None  # No rule matched
    
    def _extract_filters(self, message):
        """Extract filters from natural language query"""
        filters = {}
        
        # Category/Department extraction
        categories = ['it', 'construction', 'consulting', 'services', 'supplies', 
                     'maintenance', 'software', 'hardware', 'infrastructure']
        for cat in categories:
            if cat in message:
                filters['category'] = cat
                break
        
        # Value range extraction
        value_match = re.search(r'(over|above|more than|greater than)\s*r?\s*(\d+[km]?)', message, re.I)
        if value_match:
            value_str = value_match.group(2).lower()
            multiplier = 1000 if 'k' in value_str else 1000000 if 'm' in value_str else 1
            filters['min_value'] = int(re.sub(r'[km]', '', value_str)) * multiplier
        
        value_match = re.search(r'(under|below|less than)\s*r?\s*(\d+[km]?)', message, re.I)
        if value_match:
            value_str = value_match.group(2).lower()
            multiplier = 1000 if 'k' in value_str else 1000000 if 'm' in value_str else 1
            filters['max_value'] = int(re.sub(r'[km]', '', value_str)) * multiplier
        
        # Time period extraction
        if 'this month' in message:
            filters['period'] = 'this_month'
        elif 'last month' in message:
            filters['period'] = 'last_month'
        elif 'this year' in message:
            filters['period'] = 'this_year'
        elif 'quarter' in message:
            filters['period'] = 'this_quarter'
        
        return filters
    
    def _format_filter_text(self, filters):
        """Format filters into readable text"""
        if not filters:
            return "in your system"
        
        parts = []
        if 'category' in filters:
            parts.append(f"in {filters['category'].upper()}")
        if 'min_value' in filters:
            parts.append(f"worth over R{filters['min_value']:,}")
        if 'max_value' in filters:
            parts.append(f"under R{filters['max_value']:,}")
        if 'period' in filters:
            parts.append(filters['period'].replace('_', ' '))
        
        return ' '.join(parts) if parts else "in your system"
    
    def _get_ai_response(self, message, company_id, conversation_id=None):
        """Enhanced AI-powered response using OpenAI with context"""
        try:
            context = self._get_company_context(company_id)
            conversation_history = self._get_conversation_history(conversation_id)
            
            prompt = f"""
You are TenderBot, an intelligent AI assistant for a tender management system. You help users manage, track, and analyze their business tenders.

Company Context:
{context}

Recent Conversation:
{conversation_history}

User Question: {message}

Provide a helpful, concise response about their tenders. Be specific with numbers and actionable advice. 
Use emojis where appropriate. Keep responses under 150 words unless detailed analysis is requested.
If the user asks about specific data, provide concrete numbers from the context.
"""
            
            if openai:
                try:
                    # Use new API (openai >= 1.0.0)
                    from openai import OpenAI
                    client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are TenderBot, a helpful AI assistant for tender management."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=250,
                        temperature=0.7
                    )
                    ai_response = response.choices[0].message.content.strip()
                except ImportError:
                    # Fallback for old API (openai < 1.0.0) - only if OpenAI class doesn't exist
                    try:
                        response = openai.ChatCompletion.create(
                            model="gpt-3.5-turbo",
                            messages=[
                                {"role": "system", "content": "You are TenderBot, a helpful AI assistant for tender management."},
                                {"role": "user", "content": prompt}
                            ],
                            max_tokens=250,
                            temperature=0.7
                        )
                        ai_response = response.choices[0].message.content.strip()
                    except Exception as old_api_error:
                        logger.error(f"Old OpenAI API error: {str(old_api_error)}")
                        raise
                except Exception as api_error:
                    logger.error(f"OpenAI API error: {str(api_error)}")
                    raise
                
                # Generate contextual suggestions
                suggestions = self._generate_contextual_suggestions(message)
                
                return {
                    "response": ai_response,
                    "type": "ai",
                    "powered_by": "AI",
                    "suggestions": suggestions
                }
            
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            
        return self._get_default_response()
    
    def _get_conversation_history(self, conversation_id):
        """Get recent conversation history for context"""
        if not conversation_id or conversation_id not in self.conversation_contexts:
            return "No previous conversation"
        
        history = self.conversation_contexts[conversation_id][-5:]  # Last 5 messages
        return "\n".join([f"User: {msg['message']}" for msg in history])
    
    def _generate_contextual_suggestions(self, message):
        """Generate smart suggestions based on current query"""
        suggestions = []
        
        if 'deadline' in message or 'closing' in message:
            suggestions = ["Show overdue tenders", "Next month deadlines", "Set deadline alerts"]
        elif 'value' in message or 'worth' in message:
            suggestions = ["Show highest value", "Average by category", "Total value this month"]
        elif 'status' in message:
            suggestions = ["Success rate", "Won vs Lost", "Pending actions"]
        elif 'category' in message or 'department' in message:
            suggestions = ["Top performing category", "Category comparison", "Budget by category"]
        else:
            suggestions = ["Show analytics", "Upcoming deadlines", "Performance summary", "Search tenders"]
        
        return suggestions
    
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
    
    # Enhanced Data retrieval methods
    def _get_active_tender_count(self, company_id, filters=None):
        """Get count of active tenders with optional filters"""
        try:
            db = get_db()
            if not db:
                return 0
            
            query = "SELECT COUNT(*) FROM tenders WHERE company_id = :company_id AND status_id NOT IN (3, 6)"
            params = {"company_id": company_id}
            
            # Apply filters
            if filters:
                if 'category' in filters:
                    query += " AND LOWER(category) LIKE :category"
                    params['category'] = f"%{filters['category']}%"
                if 'min_value' in filters:
                    query += " AND estimated_value >= :min_value"
                    params['min_value'] = filters['min_value']
                if 'max_value' in filters:
                    query += " AND estimated_value <= :max_value"
                    params['max_value'] = filters['max_value']
            
            result = db.session.execute(text(query), params)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error getting tender count: {e}")
            return 0
    
    def _search_tenders(self, message, company_id, filters=None):
        """Search tenders based on natural language query"""
        try:
            db = get_db()
            if not db:
                return []
            
            # Extract search terms
            search_terms = self._extract_search_terms(message)
            
            query = """
                SELECT id, tender_number, title, category, estimated_value, 
                       submission_deadline, status_id
                FROM tenders 
                WHERE company_id = :company_id
            """
            params = {"company_id": company_id}
            
            if search_terms:
                query += " AND (LOWER(title) LIKE :search OR LOWER(description) LIKE :search OR LOWER(category) LIKE :search)"
                params['search'] = f"%{search_terms}%"
            
            # Apply additional filters
            if filters:
                if 'category' in filters:
                    query += " AND LOWER(category) LIKE :category"
                    params['category'] = f"%{filters['category']}%"
                if 'min_value' in filters:
                    query += " AND estimated_value >= :min_value"
                    params['min_value'] = filters['min_value']
                if 'max_value' in filters:
                    query += " AND estimated_value <= :max_value"
                    params['max_value'] = filters['max_value']
            
            query += " ORDER BY submission_deadline ASC LIMIT 10"
            
            result = db.session.execute(text(query), params)
            
            tenders = []
            for row in result:
                tenders.append({
                    "id": row[0],
                    "number": row[1],
                    "title": row[2],
                    "category": row[3] or "General",
                    "value": row[4] or 0,
                    "deadline": row[5].strftime("%Y-%m-%d") if row[5] else "No deadline",
                    "status": self._get_status_name(row[6])
                })
            return tenders
        except Exception as e:
            logger.error(f"Error searching tenders: {e}")
            return []
    
    def _extract_search_terms(self, message):
        """Extract search terms from message"""
        # Remove common words
        stop_words = ['show', 'me', 'find', 'search', 'for', 'the', 'a', 'an', 'tenders', 'tender']
        words = message.lower().split()
        search_terms = ' '.join([w for w in words if w not in stop_words and len(w) > 2])
        return search_terms if len(search_terms) > 2 else None
    
    def _extract_username(self, message):
        """Extract username from message"""
        # Common patterns: "assigned to username", "for user username", "user username"
        patterns = [
            r'assigned to (\w+)',
            r'for user (\w+)',
            r'user (\w+)',
            r'to (\w+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.I)
            if match:
                return match.group(1)
        return None
    
    def _get_tenders_for_user(self, company_id, username, filters=None):
        """Get tenders assigned to a specific user"""
        try:
            db = get_db()
            if not db:
                return None
            
            # First, find the user ID from username
            user_result = db.session.execute(text("""
                SELECT id FROM users 
                WHERE company_id = :company_id 
                AND (LOWER(username) = LOWER(:username) OR LOWER(name) LIKE LOWER(:name_pattern))
            """), {
                "company_id": company_id,
                "username": username,
                "name_pattern": f"%{username}%"
            })
            
            user_row = user_result.fetchone()
            if not user_row:
                return None  # User not found
            
            user_id = user_row[0]
            
            # Get tenders assigned to this user
            query = """
                SELECT id, tender_number, title, category, estimated_value, 
                       submission_deadline, status_id
                FROM tenders 
                WHERE company_id = :company_id 
                AND assigned_to = :user_id
            """
            params = {"company_id": company_id, "user_id": user_id}
            
            # Apply additional filters
            if filters:
                if 'category' in filters:
                    query += " AND LOWER(category) LIKE :category"
                    params['category'] = f"%{filters['category']}%"
                if filters.get('period') == 'this_month':
                    query += " AND MONTH(created_at) = MONTH(NOW()) AND YEAR(created_at) = YEAR(NOW())"
            
            query += " ORDER BY submission_deadline ASC LIMIT 20"
            
            result = db.session.execute(text(query), params)
            
            tenders = []
            for row in result:
                tenders.append({
                    "id": row[0],
                    "number": row[1] or f"T-{row[0]}",
                    "title": row[2],
                    "category": row[3] or "General",
                    "value": f"R{(row[4] or 0):,.0f}",
                    "deadline": row[5].strftime("%Y-%m-%d") if row[5] else "No deadline",
                    "status": self._get_status_name(row[6])
                })
            
            return {
                "count": len(tenders),
                "tenders": tenders
            }
        except Exception as e:
            logger.error(f"Error getting tenders for user: {e}")
            return None
    
    def _get_total_tender_count(self, company_id, filters=None):
        """Get total count of all tenders (not just active)"""
        try:
            db = get_db()
            if not db:
                return 0
            
            query = "SELECT COUNT(*) FROM tenders WHERE company_id = :company_id"
            params = {"company_id": company_id}
            
            # Apply filters
            if filters:
                if 'category' in filters:
                    query += " AND LOWER(category) LIKE :category"
                    params['category'] = f"%{filters['category']}%"
                if 'min_value' in filters:
                    query += " AND estimated_value >= :min_value"
                    params['min_value'] = filters['min_value']
                if 'max_value' in filters:
                    query += " AND estimated_value <= :max_value"
                    params['max_value'] = filters['max_value']
                if filters.get('period') == 'this_month':
                    query += " AND MONTH(created_at) = MONTH(NOW()) AND YEAR(created_at) = YEAR(NOW())"
            
            result = db.session.execute(text(query), params)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error getting total tender count: {e}")
            return 0
    
    def _get_success_rate_analytics(self, company_id, filters=None):
        """Get success rate analytics"""
        try:
            db = get_db()
            if not db:
                return {}
            
            query = """
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN status_id = 3 THEN 1 END) as won,
                    COUNT(CASE WHEN status_id = 4 THEN 1 END) as lost,
                    ROUND(COUNT(CASE WHEN status_id = 3 THEN 1 END) * 100.0 / 
                          NULLIF(COUNT(CASE WHEN status_id IN (3,4) THEN 1 END), 0), 2) as success_rate
                FROM tenders 
                WHERE company_id = :company_id
            """
            params = {"company_id": company_id}
            
            if filters and 'category' in filters:
                query += " AND LOWER(category) LIKE :category"
                params['category'] = f"%{filters['category']}%"
            
            result = db.session.execute(text(query), params)
            row = result.fetchone()
            
            return {
                "total_evaluated": row[0] or 0,
                "won": row[1] or 0,
                "lost": row[2] or 0,
                "success_rate": f"{row[3] or 0}%",
                "message": f"You've won {row[1]} out of {row[0]} evaluated tenders"
            }
        except Exception as e:
            logger.error(f"Error getting success analytics: {e}")
            return {}
    
    def _get_performance_trends(self, company_id, filters=None):
        """Get performance trends over time"""
        try:
            db = get_db()
            if not db:
                return []
            
            query = """
                SELECT 
                    DATE_FORMAT(created_at, '%Y-%m') as month,
                    COUNT(*) as total,
                    COUNT(CASE WHEN status_id = 3 THEN 1 END) as won,
                    SUM(estimated_value) as total_value
                FROM tenders 
                WHERE company_id = :company_id
                AND created_at >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
                GROUP BY month
                ORDER BY month DESC
                LIMIT 6
            """
            
            result = db.session.execute(text(query), {"company_id": company_id})
            
            trends = []
            for row in result:
                trends.append({
                    "period": row[0],
                    "total": row[1],
                    "won": row[2],
                    "value": f"R{(row[3] or 0):,.0f}"
                })
            return trends
        except Exception as e:
            logger.error(f"Error getting performance trends: {e}")
            return []
    
    def _get_comprehensive_analytics(self, company_id, filters=None):
        """Get comprehensive analytics summary"""
        try:
            status_summary = self._get_tender_status_summary(company_id)
            value_stats = self._get_value_statistics(company_id, filters)
            success_rate = self._get_success_rate_analytics(company_id, filters)
            
            return {
                **status_summary,
                **value_stats,
                **success_rate
            }
        except Exception as e:
            logger.error(f"Error getting comprehensive analytics: {e}")
            return {}
    
    def _get_value_statistics(self, company_id, filters=None):
        """Get value-based statistics"""
        try:
            db = get_db()
            if not db:
                return {}
            
            query = """
                SELECT 
                    SUM(estimated_value) as total_value,
                    AVG(estimated_value) as avg_value,
                    MAX(estimated_value) as max_value,
                    MIN(estimated_value) as min_value
                FROM tenders 
                WHERE company_id = :company_id
                AND estimated_value IS NOT NULL
            """
            params = {"company_id": company_id}
            
            if filters:
                if 'period' in filters:
                    if filters['period'] == 'this_month':
                        query += " AND MONTH(created_at) = MONTH(NOW()) AND YEAR(created_at) = YEAR(NOW())"
                    elif filters['period'] == 'this_year':
                        query += " AND YEAR(created_at) = YEAR(NOW())"
            
            result = db.session.execute(text(query), params)
            row = result.fetchone()
            
            return {
                "total_value": f"R{(row[0] or 0):,.0f}",
                "average_value": f"R{(row[1] or 0):,.0f}",
                "highest_value": f"R{(row[2] or 0):,.0f}",
                "lowest_value": f"R{(row[3] or 0):,.0f}"
            }
        except Exception as e:
            logger.error(f"Error getting value statistics: {e}")
            return {}
    
    def _get_category_breakdown(self, company_id, filters=None):
        """Get breakdown by category"""
        try:
            db = get_db()
            if not db:
                return []
            
            query = """
                SELECT 
                    COALESCE(category, 'Uncategorized') as category,
                    COUNT(*) as count,
                    SUM(estimated_value) as total_value,
                    COUNT(CASE WHEN status_id = 3 THEN 1 END) as won
                FROM tenders 
                WHERE company_id = :company_id
                GROUP BY category
                ORDER BY count DESC
                LIMIT 10
            """
            
            result = db.session.execute(text(query), {"company_id": company_id})
            
            breakdown = []
            for row in result:
                success_rate = (row[3] / row[1] * 100) if row[1] > 0 else 0
                breakdown.append({
                    "category": row[0],
                    "count": row[1],
                    "value": f"R{(row[2] or 0):,.0f}",
                    "won": row[3],
                    "success_rate": f"{success_rate:.1f}%"
                })
            return breakdown
        except Exception as e:
            logger.error(f"Error getting category breakdown: {e}")
            return []
    
    def _get_comparison_data(self, message, company_id):
        """Get comparison data based on query"""
        try:
            # Simple this month vs last month comparison
            db = get_db()
            if not db:
                return {}
            
            query = """
                SELECT 
                    'This Month' as period,
                    COUNT(*) as count,
                    SUM(estimated_value) as value
                FROM tenders 
                WHERE company_id = :company_id
                AND MONTH(created_at) = MONTH(NOW())
                AND YEAR(created_at) = YEAR(NOW())
                
                UNION ALL
                
                SELECT 
                    'Last Month' as period,
                    COUNT(*) as count,
                    SUM(estimated_value) as value
                FROM tenders 
                WHERE company_id = :company_id
                AND MONTH(created_at) = MONTH(DATE_SUB(NOW(), INTERVAL 1 MONTH))
                AND YEAR(created_at) = YEAR(DATE_SUB(NOW(), INTERVAL 1 MONTH))
            """
            
            result = db.session.execute(text(query), {"company_id": company_id})
            
            comparison = []
            for row in result:
                comparison.append({
                    "period": row[0],
                    "count": row[1],
                    "value": f"R{(row[2] or 0):,.0f}"
                })
            return comparison
        except Exception as e:
            logger.error(f"Error getting comparison: {e}")
            return {}
    
    def _get_tenders_closing_tomorrow(self, company_id, filters=None):
        """Get tenders closing tomorrow"""
        try:
            db = get_db()
            if not db:
                return []
            
            query = """
                SELECT id, title, submission_deadline
                FROM tenders 
                WHERE company_id = :company_id 
                AND DATE(submission_deadline) = DATE_ADD(CURDATE(), INTERVAL 1 DAY)
                AND status_id NOT IN (3, 6)
                ORDER BY submission_deadline ASC
            """
            
            result = db.session.execute(text(query), {"company_id": company_id})
            
            tenders = []
            for row in result:
                tenders.append({
                    "id": row[0],
                    "title": row[1],
                    "deadline": row[2].strftime("%Y-%m-%d %H:%M") if row[2] else "No deadline"
                })
            return tenders
        except Exception as e:
            logger.error(f"Error getting tomorrow's tenders: {e}")
            return []
    
    def _get_tenders_closing_this_month(self, company_id, filters=None):
        """Get tenders closing this month"""
        try:
            db = get_db()
            if not db:
                return []
            
            query = """
                SELECT id, title, submission_deadline, category
                FROM tenders 
                WHERE company_id = :company_id 
                AND MONTH(submission_deadline) = MONTH(NOW())
                AND YEAR(submission_deadline) = YEAR(NOW())
                AND status_id NOT IN (3, 6)
                ORDER BY submission_deadline ASC
                LIMIT 20
            """
            
            result = db.session.execute(text(query), {"company_id": company_id})
            
            tenders = []
            for row in result:
                tenders.append({
                    "id": row[0],
                    "title": row[1],
                    "deadline": row[2].strftime("%Y-%m-%d") if row[2] else "No deadline",
                    "category": row[3] or "General"
                })
            return tenders
        except Exception as e:
            logger.error(f"Error getting monthly tenders: {e}")
            return []
    
    def _get_tenders_by_status(self, company_id, status, filters=None):
        """Get tenders by specific status"""
        try:
            db = get_db()
            if not db:
                return []
            
            status_map = {
                'won': 3,
                'lost': 4,
                'active': 1,
                'submitted': 2,
                'pending': 5
            }
            
            status_id = status_map.get(status.lower(), 1)
            
            query = """
                SELECT id, tender_number, title, category, estimated_value, 
                       submission_deadline
                FROM tenders 
                WHERE company_id = :company_id 
                AND status_id = :status_id
                ORDER BY created_at DESC
                LIMIT 10
            """
            
            result = db.session.execute(text(query), {
                "company_id": company_id,
                "status_id": status_id
            })
            
            tenders = []
            for row in result:
                tenders.append({
                    "id": row[0],
                    "number": row[1],
                    "title": row[2],
                    "category": row[3] or "General",
                    "value": f"R{(row[4] or 0):,.0f}",
                    "deadline": row[5].strftime("%Y-%m-%d") if row[5] else "No deadline"
                })
            return tenders
        except Exception as e:
            logger.error(f"Error getting tenders by status: {e}")
            return []
    
    def _get_status_name(self, status_id):
        """Get status name from ID"""
        status_names = {
            1: "Active",
            2: "Submitted",
            3: "Won",
            4: "Lost",
            5: "Pending",
            6: "Closed"
        }
        return status_names.get(status_id, "Unknown")
    
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