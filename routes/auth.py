import os
from flask import render_template, session, redirect, url_for, flash
from models import db, User
from utils import get_environment_user_data


def auth_routes(bp):
    """Register authentication routes"""
    
    @bp.route('/login')
    def login():
        """Login page"""
        return render_template('login.html')
    
    
    @bp.route('/logout')
    def logout():
        """Logout"""
        session.clear()
        return redirect(url_for('index'))
    
    
    def load_user_from_environment():
        """Load user from environment variables"""
        username = os.environ.get('REMOTE_USER')
        
        if not username:
            # Allow anonymous access for testing - remove in production
            return None
        
        # Load or create user
        user = User.query.filter_by(username=username).first()
        if not user:
            env_data = get_environment_user_data()
            user = User(
                username=username,
                email=env_data.get('email'),
                first_name=env_data.get('first_name'),
                last_name=env_data.get('last_name')
            )
            db.session.add(user)
            db.session.commit()
        
        return user
