"""
Authentication models for Replit Auth integration.
Uses Flask-SQLAlchemy for auth tables ONLY.
Business logic continues using psycopg2.

IMPORTANT: These models must be imported AFTER db is initialized in app.py
"""
from datetime import datetime
from flask_login import UserMixin
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from sqlalchemy import UniqueConstraint


def create_auth_models(db):
    """
    Factory function to create auth models with db instance.
    Call this after db is initialized in app.py.
    
    Returns:
        tuple: (User, OAuth) model classes
    """
    
    class User(UserMixin, db.Model):
        """User accounts from Replit Auth"""
        __tablename__ = 'users'
        
        id = db.Column(db.String, primary_key=True)
        email = db.Column(db.String, unique=True, nullable=True)
        first_name = db.Column(db.String, nullable=True)
        last_name = db.Column(db.String, nullable=True)
        profile_image_url = db.Column(db.String, nullable=True)
        role = db.Column(db.String, default='viewer')
        created_at = db.Column(db.DateTime, default=datetime.now)
        updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    class OAuth(OAuthConsumerMixin, db.Model):
        """OAuth tokens for Replit Auth"""
        __tablename__ = 'oauth'
        
        user_id = db.Column(db.String, db.ForeignKey(User.id))
        browser_session_key = db.Column(db.String, nullable=False)
        user = db.relationship(User)
        
        __table_args__ = (
            UniqueConstraint('user_id', 'browser_session_key', 'provider',
                            name='uq_user_browser_session_key_provider'),
        )
    
    return User, OAuth
