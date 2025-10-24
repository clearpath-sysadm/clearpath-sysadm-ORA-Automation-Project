"""
Authentication middleware decorators for Flask routes.

Provides:
- @login_required: Requires any authenticated user (viewer or admin)
- @admin_required: Requires admin role
"""

from functools import wraps
from flask import jsonify, request, redirect, url_for
from flask_login import current_user


def login_required(f):
    """
    Decorator that requires user to be authenticated.
    Returns 401 Unauthorized if not logged in.
    Works for both JSON API endpoints and HTML pages.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({
                    'error': 'Authentication required',
                    'authenticated': False
                }), 401
            else:
                return redirect('/landing.html')
        
        return f(*args, **kwargs)
    
    return decorated_function


def admin_required(f):
    """
    Decorator that requires user to be authenticated AND have admin role.
    Returns 403 Forbidden if user is authenticated but not an admin.
    Returns 401 Unauthorized if not logged in.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({
                    'error': 'Authentication required',
                    'authenticated': False
                }), 401
            else:
                return redirect('/landing.html')
        
        if current_user.role != 'admin':
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({
                    'error': 'Admin access required',
                    'authenticated': True,
                    'role': current_user.role
                }), 403
            else:
                return '''
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Access Denied - ORA Automation</title>
                    <link rel="stylesheet" href="/static/css/global-styles.css">
                </head>
                <body>
                    <div style="max-width: 600px; margin: 100px auto; padding: 40px; text-align: center;">
                        <h1>🔒 Access Denied</h1>
                        <p style="font-size: 1.125rem; margin: 20px 0;">
                            Admin privileges required to access this resource.
                        </p>
                        <p style="margin: 20px 0;">
                            Your current role: <strong>{}</strong>
                        </p>
                        <a href="/" class="btn btn-primary" style="display: inline-block; margin-top: 20px;">
                            Return to Dashboard
                        </a>
                    </div>
                </body>
                </html>
                '''.format(current_user.role), 403
        
        return f(*args, **kwargs)
    
    return decorated_function


def get_current_user():
    """
    Helper function to get the current authenticated user.
    Returns the Flask-Login current_user proxy.
    Use current_user.is_authenticated to check if logged in.
    """
    return current_user
