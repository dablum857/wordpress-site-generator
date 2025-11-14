import os
from flask import Flask, render_template, request, session, redirect, url_for, flash
from functools import wraps
from config import config_dict
from models import db, User
from routes import register_blueprints
from utils import get_environment_user_data


def create_app(config_name=None):
    """Application factory"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config_dict[config_name])
    
    # Initialize extensions
    db.init_app(app)
    
    # Create upload folder
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs('instance', exist_ok=True)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register context processors and error handlers
    register_context_processors(app)
    register_error_handlers(app)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Add main routes
    add_main_routes(app)
    
    return app


def register_context_processors(app):
    """Register context processors"""
    @app.before_request
    def load_user():
        """Load user from environment variables"""
        username = os.environ.get('REMOTE_USER')
        
        if not username:
            # Allow anonymous access for testing - remove in production
            if app.debug:
                username = 'testuser'
            else:
                session.clear()
                return
        
        # Store username in session
        session['username'] = username
        
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
        
        session['user_id'] = user.id
        session['user'] = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': user.full_name
        }


def register_error_handlers(app):
    """Register error handlers"""
    @app.errorhandler(404)
    def not_found(error):
        return render_template('error.html', 
                             error_code='404',
                             status_code=404,
                             error_message='Page not found'), 404
    
    @app.errorhandler(403)
    def forbidden(error):
        return render_template('error.html',
                             error_code='403',
                             status_code=403,
                             error_message='Access forbidden'), 403
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('error.html',
                             error_code='500',
                             status_code=500,
                             error_message='Internal server error'), 500


def add_main_routes(app):
    """Add main application routes"""
    
    def require_login(f):
        """Decorator to require user login"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in first', 'error')
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated_function
    
    @app.route('/')
    def index():
        """Landing page / Dashboard"""
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        
        user = User.query.get(session['user_id'])
        sites = user.wordpress_sites if user else []
        
        return render_template('index.html', sites=sites, user=user)


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
