# models/saved_search.py
from models import db
from datetime import datetime
import json

class SavedSearch(db.Model):
    __tablename__ = 'saved_searches'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    filters = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime)
    
    # Relationships
    user = db.relationship('User', backref='saved_searches')
    
    def __repr__(self):
        return f'<SavedSearch {self.name}>'
