import os
import re
import uuid
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app, render_template
from flask_mail import Message
from models import User, Professional
from extensions import db, mail


# ---------- JWT & Decorators ----------
def generate_jwt(user_id, role):
    payload = {
        'user_id': str(user_id),
        'role': role,
        'exp': datetime.utcnow() + timedelta(seconds=current_app.config['JWT_ACCESS_TOKEN_EXPIRES'])
    }
    return jwt.encode(payload, current_app.config['JWT_SECRET_KEY'], algorithm='HS256')


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        # Debug: print the raw header to console (uncomment if needed)
        # print(f"Auth header: {auth_header}")

        if auth_header:
            # Check if it starts with 'bearer' (case-insensitive)
            if auth_header.lower().startswith('bearer'):
                # Split on any whitespace and take the second part
                parts = auth_header.split(None, 1)
                if len(parts) == 2:
                    token = parts[1]

        if not token:
            return jsonify({'success': False, 'message': 'Token is missing'}), 401

        try:
            data = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            user_uuid = uuid.UUID(data['user_id'])
            current_user = User.query.get(user_uuid)
            if not current_user or not current_user.is_active:
                return jsonify({'success': False, 'message': 'User not found or inactive'}), 401
            request.user = current_user
        except jwt.ExpiredSignatureError:
            return jsonify({'success': False, 'message': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'success': False, 'message': 'Invalid token'}), 401
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'Invalid user ID in token'}), 401

        return f(*args, **kwargs)
    return decorated


def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if request.user.role != required_role:
                return jsonify({'success': False, 'message': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated


def professional_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.user.role != 'professional':
            return jsonify({'success': False, 'message': 'Professional access required'}), 403
        prof = Professional.query.filter_by(user_id=request.user.id).first()
        if not prof or prof.approval_status != 'approved':
            return jsonify({'success': False, 'message': 'Professional not approved'}), 403
        return f(*args, **kwargs)
    return decorated


def client_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.user.role != 'client':
            return jsonify({'success': False, 'message': 'Client access required'}), 403
        return f(*args, **kwargs)
    return decorated


def success_response(message, data=None):
    return jsonify({'success': True, 'message': message, 'data': data}), 200


def error_response(message, status_code=400):
    return jsonify({'success': False, 'error': message}), status_code


def validate_email(email):
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(pattern, email) is not None


def save_uploaded_file(file, subfolder):
    if not file:
        return None
    upload_folder = current_app.config['UPLOAD_FOLDER']
    allowed_extensions = current_app.config['ALLOWED_EXTENSIONS']
    filename = file.filename
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if ext not in allowed_extensions:
        return None
    new_filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}.{ext}"
    folder = os.path.join(upload_folder, subfolder)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, new_filename)
    file.save(path)
    return os.path.join(subfolder, new_filename)


# ---------- Email Functions ----------
def send_email(to, subject, template, **kwargs):
    """
    Send an email using a template file.

    Args:
        to (str): Recipient email address.
        subject (str): Email subject.
        template (str): Template filename (e.g., 'invitation.html').
        **kwargs: Variables to pass to the template.

    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    try:
        html = render_template(template, **kwargs)
        msg = Message(
            subject=subject,
            recipients=[to],
            html=html,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER')
        )
        mail.send(msg)
        return True, None
    except Exception as e:
        current_app.logger.error(f"Email error: {e}")
        return False, str(e)


# ---------- Token Generation ----------
def generate_invitation_token():
    """Generate a random UUID for client invitations."""
    return str(uuid.uuid4())


def generate_password_reset_token(user_id):
    """
    Create a password reset token and store it in the database.

    Args:
        user_id (UUID): The user's ID.

    Returns:
        str: The generated token string.
    """
    from models import PasswordResetToken  # local import to avoid circular dependency
    token = str(uuid.uuid4())
    reset_token = PasswordResetToken(
        user_id=user_id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )
    db.session.add(reset_token)
    db.session.commit()
    return token


def verify_reset_token(token):
    """
    Validate a password reset token.

    Args:
        token (str): The token string.

    Returns:
        UUID or None: The user_id if valid, otherwise None.
    """
    from models import PasswordResetToken  # local import to avoid circular dependency
    reset = PasswordResetToken.query.filter_by(
        token=token,
        used=False
    ).first()
    if not reset or reset.expires_at < datetime.utcnow():
        return None
    return reset.user_id