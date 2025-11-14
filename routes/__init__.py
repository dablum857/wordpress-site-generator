from flask import Blueprint

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
site_bp = Blueprint('site', __name__, url_prefix='/site')
wizard_bp = Blueprint('wizard', __name__, url_prefix='/wizard')
export_bp = Blueprint('export', __name__, url_prefix='/export')


def register_blueprints(app):
    """Register all blueprints with the app"""
    from routes.auth import auth_routes
    from routes.site import site_routes
    from routes.wizard import wizard_routes
    from routes.export import export_routes
    
    auth_routes(auth_bp)
    site_routes(site_bp)
    wizard_routes(wizard_bp)
    export_routes(export_bp)
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(site_bp)
    app.register_blueprint(wizard_bp)
    app.register_blueprint(export_bp)
