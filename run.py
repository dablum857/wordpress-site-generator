#!/usr/bin/env python
"""
Application entry point
"""

import os
from app import create_app, db


if __name__ == '__main__':
    config_name = os.environ.get('FLASK_ENV', 'development')
    app = create_app(config_name)
    
    # Create tables
    with app.app_context():
        db.create_all()
    
    # Run application
    debug = os.environ.get('FLASK_DEBUG', config_name == 'development')
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=debug, port=port, host='0.0.0.0')
