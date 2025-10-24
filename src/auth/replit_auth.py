"""
Replit Auth integration using Flask-Dance and OpenID Connect.
Based on Replit's Python authentication blueprint.
"""
import jwt
import os
import uuid
from functools import wraps
from urllib.parse import urlencode

from flask import g, session, redirect, request, jsonify, url_for, Blueprint
from flask_dance.consumer import OAuth2ConsumerBlueprint, oauth_authorized, oauth_error
from flask_dance.consumer.storage import BaseStorage
from flask_login import LoginManager, login_user, logout_user, current_user
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError
from sqlalchemy.exc import NoResultFound
from werkzeug.local import LocalProxy

login_manager = None
User = None
OAuth = None
db = None


class UserSessionStorage(BaseStorage):
    """Store OAuth tokens in database per browser session"""
    
    def get(self, blueprint):
        global db, OAuth, current_user
        try:
            token = db.session.query(OAuth).filter_by(
                user_id=current_user.get_id(),
                browser_session_key=g.browser_session_key,
                provider=blueprint.name,
            ).one().token
        except NoResultFound:
            token = None
        return token

    def set(self, blueprint, token):
        global db, OAuth, current_user
        db.session.query(OAuth).filter_by(
            user_id=current_user.get_id(),
            browser_session_key=g.browser_session_key,
            provider=blueprint.name,
        ).delete()
        new_model = OAuth()
        new_model.user_id = current_user.get_id()
        new_model.browser_session_key = g.browser_session_key
        new_model.provider = blueprint.name
        new_model.token = token
        db.session.add(new_model)
        db.session.commit()

    def delete(self, blueprint):
        global db, OAuth, current_user
        db.session.query(OAuth).filter_by(
            user_id=current_user.get_id(),
            browser_session_key=g.browser_session_key,
            provider=blueprint.name).delete()
        db.session.commit()


def make_replit_blueprint(app, db_instance, user_model, oauth_model):
    """Create Replit OAuth blueprint"""
    global db, User, OAuth, login_manager
    
    db = db_instance
    User = user_model
    OAuth = oauth_model
    
    try:
        repl_id = os.environ['REPL_ID']
    except KeyError:
        raise SystemExit("REPL_ID environment variable must be set")

    issuer_url = os.environ.get('ISSUER_URL', "https://replit.com/oidc")

    replit_bp = OAuth2ConsumerBlueprint(
        "replit_auth",
        __name__,
        client_id=repl_id,
        client_secret=None,
        base_url=issuer_url,
        authorization_url_params={"prompt": "login consent"},
        token_url=issuer_url + "/token",
        token_url_params={"auth": (), "include_client_id": True},
        auto_refresh_url=issuer_url + "/token",
        auto_refresh_kwargs={"client_id": repl_id},
        authorization_url=issuer_url + "/auth",
        use_pkce=True,
        code_challenge_method="S256",
        scope=["openid", "profile", "email", "offline_access"],
        storage=UserSessionStorage(),
    )

    @replit_bp.before_app_request
    def set_applocal_session():
        """Set browser session key for multi-device support"""
        if '_browser_session_key' not in session:
            session['_browser_session_key'] = uuid.uuid4().hex
        session.modified = True
        g.browser_session_key = session['_browser_session_key']
        g.flask_dance_replit = replit_bp.session

    @replit_bp.route("/logout")
    def logout():
        """Log out user and revoke tokens"""
        del replit_bp.token
        logout_user()

        end_session_endpoint = issuer_url + "/session/end"
        encoded_params = urlencode({
            "client_id": repl_id,
            "post_logout_redirect_uri": request.url_root,
        })
        logout_url = f"{end_session_endpoint}?{encoded_params}"

        return redirect(logout_url)

    @replit_bp.route("/error")
    def error():
        """Handle OAuth errors"""
        return jsonify({'error': 'Authentication failed'}), 403

    def save_user(user_claims):
        """Save or update user in database"""
        user = User()
        user.id = user_claims['sub']
        user.email = user_claims.get('email')
        user.first_name = user_claims.get('first_name')
        user.last_name = user_claims.get('last_name')
        user.profile_image_url = user_claims.get('profile_image_url')
        
        merged_user = db.session.merge(user)
        db.session.commit()
        return merged_user

    ADMIN_EMAILS = os.getenv('ADMIN_EMAILS', '').split(',')
    ADMIN_EMAILS = [email.strip() for email in ADMIN_EMAILS if email.strip()]

    @oauth_authorized.connect_via(replit_bp)
    def logged_in(blueprint, token):
        """Handle successful OAuth login"""
        user_claims = jwt.decode(token['id_token'], options={"verify_signature": False})
        user = save_user(user_claims)
        
        if ADMIN_EMAILS and user.email in ADMIN_EMAILS and user.role != 'admin':
            user.role = 'admin'
            db.session.commit()
            print(f"✅ Auto-promoted {user.email} to admin")
        
        login_user(user)
        blueprint.token = token
        
        next_url = session.pop("next_url", None)
        if next_url is not None:
            return redirect(next_url)

    @oauth_error.connect_via(replit_bp)
    def handle_error(blueprint, error, error_description=None, error_uri=None):
        """Handle OAuth errors"""
        return redirect(url_for('replit_auth.error'))

    return replit_bp


def require_login(f):
    """Decorator to require login (use sparingly - middleware handles most cases)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            session["next_url"] = request.url
            return redirect(url_for('replit_auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def init_login_manager(app, user_model):
    """Initialize Flask-Login"""
    global login_manager, User
    User = user_model
    
    login_manager = LoginManager(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)
    
    return login_manager


replit = LocalProxy(lambda: g.flask_dance_replit)
