#!/usr/bin/env python3
"""
Entry point for the Meeting Dashboard application.
Can be used with Flask development server or Gunicorn in production.
"""

import os
from app import create_app

# Create the Flask application
app = create_app(os.getenv('FLASK_ENV', 'default'))

if __name__ == '__main__':
    # Development server
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    app.run(host='0.0.0.0', port=port, debug=debug)
