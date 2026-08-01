import os
import uuid
from datetime import datetime, timezone, timedelta
from flask import current_app
from sqlalchemy import func

from extensions import db, bcrypt
from models import (
    User, UserProfile, Professional, Client, Admin,
    ProfessionalCategory,
    SubscriptionPlan, UserSubscription, Payment, Invoice,
    FoodCategory, Food,
    Recipe, RecipeIngredient, RecipeStep,
    MealPlan, Meal,
    ShoppingList, ShoppingItem,
    WaterLog,
    GoalTracker, GoalProgress,
    HealthCondition, ConditionRecommendation, FoodRestriction,
    Nutriscan,
    AIConversation, AIMessage, AIRecommendation,
    Report,
    Notification, NotificationTemplate, NotificationPreference,
    ContactMessage,
    SystemSetting, ApplicationSetting,
    Language, Theme,
    File,
    AuditLog, ActivityLog,
    PasswordResetToken
)
from utils import generate_jwt, save_uploaded_file, validate_email

# Optional: Flask-Mail for email sending
try:
    from flask_mail import Message
    from extensions import mail
    HAS_MAIL = True
except ImportError:
    HAS_MAIL = False


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def get_user_by_id(user_id):
    if isinstance(user_id, str):
        try:
            user_id = uuid.UUID(user_id)
        except ValueError:
            return None
    return User.query.get(user_id)


def get_user_profile_by_user(user):
    profile = UserProfile.query.filter_by(user_id=user.id).first()
    if not profile:
        profile = UserProfile(user_id=user.id)
        db.session.add(profile)
        db.session.flush()
    return profile


def get_professional_by_user(user):
    return Professional.query.filter_by(user_id=user.id).first()


def get_client_by_user(user):
    return Client.query.filter_by(user_id=user.id).first()


# ----------------------------------------------------------------------
# Email Sending
# ----------------------------------------------------------------------

def send_invitation_email(email, name, token, frontend_url=None):
    """Send an invitation email with a link to set password."""
    if not frontend_url:
        frontend_url = current_app.config.get('FRONTEND_URL', 'http://localhost:5500')
    verify_link = f"{frontend_url}/client/verify.html?token={token}"
    subject = "Invitation to Smart Lishe"
    body = f"""
Hello {name},

You have been invited to join Smart Lishe by your professional.

Please click the link below to set your password and start using the app:

{verify_link}

This link will expire in 7 days.

If you did not expect this invitation, please ignore this email.

Thank you,
Smart Lishe Team
"""
    html = f"""
<p>Hello <strong>{name}</strong>,</p>
<p>You have been invited to join <strong>Smart Lishe</strong> by your professional.</p>
<p>Please click the link below to set your password and start using the app:</p>
<p><a href="{verify_link}">{verify_link}</a></p>
<p>This link will expire in <strong>7 days</strong>.</p>
<p>If you did not expect this invitation, please ignore this email.</p>
<p>Thank you,<br>Smart Lishe Team</p>
"""
    try:
        if HAS_MAIL:
            msg = Message(subject, recipients=[email], body=body, html=html)
            mail.send(msg)
            current_app.logger.info(f"📧 Invitation email sent to {email}")
        else:
            # Fallback: log the link
            current_app.logger.info(f"📧 [MOCK] Invitation email to {email}: {verify_link}")
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send email to {email}: {e}")
        return False


def send_client_message_email(client_email, client_name, subject, message, prof_name):
    """Send an email message from the professional to the client."""
    full_message = f"""
Dear {client_name},

You have received a message from your professional {prof_name}:

Subject: {subject}
Message:
{message}

Please log in to your Smart Lishe account to reply.

Thank you,
Smart Lishe Team
"""
    try:
        if HAS_MAIL:
            msg = Message(subject, recipients=[client_email], body=full_message)
            mail.send(msg)
            current_app.logger.info(f"📧 Message email sent to {client_email}")
        else:
            current_app.logger.info(f"📧 [MOCK] Message to {client_email}: {message}")
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send message to {client_email}: {e}")
        return False


# ----------------------------------------------------------------------
# Authentication
# ----------------------------------------------------------------------

def register_user(data):
    """Register a new user."""
    email = data.get('email')
    password = data.get('password')
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    role = data.get('role', 'user')

    if not all([email, password, first_name, last_name]):
        return None, 'Missing required fields'
    if not validate_email(email):
        return None, 'Invalid email format'
    if User.query.filter_by(email=email).first():
        return None, 'Email already exists'
    if role not in ['user', 'client', 'professional']:
        return None, 'Invalid role'

    hashed = bcrypt.generate_password_hash(password).decode('utf-8')
    user = User(email=email, password_hash=hashed, role=role)
    db.session.add(user)
    db.session.flush()

    profile = UserProfile(user_id=user.id, first_name=first_name, last_name=last_name)
    db.session.add(profile)

    if role == 'professional':
        prof = Professional(user_id=user.id, approval_status='pending')
        db.session.add(prof)
    elif role == 'client':
        client = Client(user_id=user.id)
        db.session.add(client)
    # role == 'user' -> no extra records

    db.session.commit()
    return user, None


def login_user(email, password):
    """Authenticate and return JWT token."""
    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        return None, 'Invalid credentials'
    if not user.is_active:
        return None, 'Account is deactivated'
    user.last_login_at = func.now()
    db.session.commit()
    token = generate_jwt(str(user.id), user.role)
    return token, None


# ----------------------------------------------------------------------
# Password Reset
# ----------------------------------------------------------------------

def request_password_reset(email):
    """Generate a reset token and store it (mock email send)."""
    user = User.query.filter_by(email=email).first()
    if not user:
        return True, None

    PasswordResetToken.query.filter_by(user_id=user.id, used=False).update({'used': True})
    db.session.commit()

    token = uuid.uuid4().hex
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    reset_token = PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=expires_at,
        used=False
    )
    db.session.add(reset_token)
    db.session.commit()

    return True, token


def reset_password(token, new_password):
    """Reset the user's password using a valid token."""
    reset_entry = PasswordResetToken.query.filter_by(token=token, used=False).first()
    if not reset_entry:
        return False, 'Invalid or expired token'

    if reset_entry.expires_at < datetime.now(timezone.utc):
        return False, 'Token has expired'

    user = User.query.get(reset_entry.user_id)
    if not user:
        return False, 'User not found'

    user.password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
    reset_entry.used = True
    db.session.commit()
    return True, None


# ----------------------------------------------------------------------
# User Profile
# ----------------------------------------------------------------------

def get_user_profile(user):
    profile = get_user_profile_by_user(user)
    data = {
        'id': str(user.id),
        'email': user.email,
        'first_name': profile.first_name,
        'last_name': profile.last_name,
        'role': user.role,
        'profile_image': profile.profile_picture_url,
        'created_at': user.created_at.isoformat(),
        'phone': profile.phone,
        'date_of_birth': profile.date_of_birth.isoformat() if profile.date_of_birth else None,
        'gender': profile.gender,
        'height_cm': float(profile.height_cm) if profile.height_cm else None,
        'weight_kg': float(profile.weight_kg) if profile.weight_kg else None,
        'bmi': float(profile.bmi) if profile.bmi else None,
        'lifestyle': profile.lifestyle,
        'activity_level': float(profile.activity_level) if profile.activity_level else None,
        'diet_preference': profile.diet_preference,
        'water_goal_ml': profile.water_goal_ml,
        'calorie_goal': profile.calorie_goal,
        'allergies': profile.allergies,
        'medical_conditions': profile.medical_conditions,
        'favorite_foods': profile.favorite_foods,
        'disliked_foods': profile.disliked_foods,
        'bio': profile.bio,
        'settings': profile.settings,
    }

    if user.role == 'professional':
        prof = get_professional_by_user(user)
        if prof:
            data.update({
                'specialty': [cat.name for cat in prof.categories],
                'license_number': prof.license_number,
                'approval_status': prof.approval_status,
                'bio': prof.biography,
                'qualification': prof.qualification,
                'years_experience': prof.years_experience,
                'consultation_fee': float(prof.consultation_fee) if prof.consultation_fee else None,
                'rating': float(prof.rating) if prof.rating else None,
                'is_approved': prof.approval_status == 'approved'
            })
    elif user.role == 'client':
        client = get_client_by_user(user)
        if client:
            data.update({
                'professional_id': str(client.assigned_professional_id) if client.assigned_professional_id else None,
                'professional_name': f"{client.professional.user.profile.first_name} {client.professional.user.profile.last_name}" if client.assigned_professional_id else None
            })
    return data


def update_user_profile(user, data):
    profile = get_user_profile_by_user(user)
    # Common fields
    if 'first_name' in data:
        profile.first_name = data['first_name']
    if 'last_name' in data:
        profile.last_name = data['last_name']
    if 'phone' in data:
        profile.phone = data['phone']
    if 'date_of_birth' in data and data['date_of_birth']:
        profile.date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
    if 'gender' in data:
        gender_val = data['gender']
        if gender_val:
            gender_val = gender_val.lower()
            valid_genders = ['male', 'female', 'other', 'prefer_not_to_say']
            if gender_val not in valid_genders:
                gender_val = None
        profile.gender = gender_val
    if 'height_cm' in data:
        profile.height_cm = data['height_cm']
    if 'weight_kg' in data:
        profile.weight_kg = data['weight_kg']
    if 'bmi' in data:
        profile.bmi = data['bmi']
    if 'lifestyle' in data:
        profile.lifestyle = data['lifestyle'] if data['lifestyle'] else None
    if 'diet_preference' in data:
        profile.diet_preference = data['diet_preference'] if data['diet_preference'] else None
    if 'activity_level' in data:
        profile.activity_level = data['activity_level']
    if 'water_goal_ml' in data:
        profile.water_goal_ml = data['water_goal_ml']
    if 'calorie_goal' in data:
        profile.calorie_goal = data['calorie_goal']
    if 'bio' in data:
        profile.bio = data['bio']
    if 'settings' in data:
        profile.settings = data['settings']

    # Arrays
    if 'allergies' in data:
        profile.allergies = data['allergies'] if data['allergies'] else None
    if 'medical_conditions' in data:
        profile.medical_conditions = data['medical_conditions'] if data['medical_conditions'] else None
    if 'favorite_foods' in data:
        profile.favorite_foods = data['favorite_foods'] if data['favorite_foods'] else None
    if 'disliked_foods' in data:
        profile.disliked_foods = data['disliked_foods'] if data['disliked_foods'] else None

    # Professional-specific
    if user.role == 'professional':
        prof = get_professional_by_user(user)
        if prof:
            if 'specialty' in data:
                categories = []
                for cat_name in data['specialty']:
                    cat = ProfessionalCategory.query.filter_by(name=cat_name).first()
                    if cat:
                        categories.append(cat)
                prof.categories = categories
            if 'qualification' in data:
                prof.qualification = data['qualification']
            if 'years_experience' in data:
                prof.years_experience = data['years_experience']
            if 'biography' in data:
                prof.biography = data['biography']
            if 'consultation_fee' in data:
                prof.consultation_fee = data['consultation_fee']
            if 'availability' in data:
                prof.availability = data['availability']
            if 'license_number' in data:
                prof.license_number = data['license_number']
    elif user.role == 'client':
        client = get_client_by_user(user)
        if client and 'medical_history' in data:
            client.medical_history = data['medical_history']

    db.session.commit()
    return True


def change_password(user, old_password, new_password):
    if not bcrypt.check_password_hash(user.password_hash, old_password):
        return False, 'Incorrect old password'
    user.password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
    db.session.commit()
    return True, None


def upload_profile_image(user, file):
    if not file:
        return None, 'No file provided'
    filepath = save_uploaded_file(file, 'profiles')
    if not filepath:
        return None, 'Invalid file type'
    profile = get_user_profile_by_user(user)
    if profile.profile_picture_url:
        old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], profile.profile_picture_url)
        if os.path.exists(old_path):
            os.remove(old_path)
    profile.profile_picture_url = filepath
    db.session.commit()
    return filepath, None


# ----------------------------------------------------------------------
# Professional – Client Management
# ----------------------------------------------------------------------

def create_client_by_professional(professional_user, data):
    """
    Create a client account, send invitation email.
    Accepts: first_name, last_name, email, phone, gender, date_of_birth,
             weight_kg, height_cm, medical_conditions, allergies,
             goal, target_weight, target_date, program, duration.
    """
    prof = get_professional_by_user(professional_user)
    if not prof or prof.approval_status != 'approved':
        return None, 'Professional not approved'

    first_name = data.get('first_name')
    last_name = data.get('last_name')
    email = data.get('email')
    phone = data.get('phone', '')
    gender = data.get('gender', '')
    date_of_birth = data.get('date_of_birth')
    weight_kg = data.get('weight_kg')
    height_cm = data.get('height_cm')
    medical_conditions = data.get('medical_conditions', [])
    allergies = data.get('allergies', [])
    goal = data.get('goal', 'General Wellness')
    target_weight = data.get('target_weight')
    target_date = data.get('target_date')
    program = data.get('program', 'General Wellness Plan')
    duration = data.get('duration', '12 Weeks')

    if not all([email, first_name, last_name]):
        return None, 'Missing required fields'
    if not validate_email(email):
        return None, 'Invalid email'
    if User.query.filter_by(email=email).first():
        return None, 'Email already exists'

    # Convert gender to lowercase for ENUM
    if gender:
        gender = gender.lower()
        valid_genders = ['male', 'female', 'other', 'prefer_not_to_say']
        if gender not in valid_genders:
            gender = None

    # Create user with empty password (will be set via invitation)
    user = User(email=email, password_hash='', role='client', is_active=True)
    db.session.add(user)
    db.session.flush()

    # Profile
    profile = UserProfile(user_id=user.id, first_name=first_name, last_name=last_name)
    profile.phone = phone
    profile.gender = gender
    if date_of_birth:
        profile.date_of_birth = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
    profile.height_cm = height_cm
    profile.weight_kg = weight_kg
    if height_cm and weight_kg:
        profile.bmi = weight_kg / ((height_cm / 100) ** 2)
    profile.medical_conditions = medical_conditions if medical_conditions else None
    profile.allergies = allergies if allergies else None

    # Store extra fields in settings JSON
    profile.settings = {
        'goal': goal,
        'target_weight': target_weight,
        'target_date': target_date,
        'program': program,
        'duration': duration,
        'compliance': 80
    }
    db.session.add(profile)

    # Generate invitation token
    token = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    client = Client(
        user_id=user.id,
        assigned_professional_id=prof.id,
        invitation_token=token,
        invitation_expires_at=expires_at,
        password_created=False
    )
    db.session.add(client)
    db.session.commit()

    # Send invitation email
    full_name = f"{first_name} {last_name}".strip()
    send_invitation_email(email, full_name, token)

    return user, None


def get_clients_for_professional(professional_user):
    """Return enriched client data for professional dashboard and pages."""
    prof = get_professional_by_user(professional_user)
    if not prof:
        return []

    clients = Client.query.filter_by(assigned_professional_id=prof.id).all()
    result = []
    for c in clients:
        user = c.user
        profile = user.profile if user.profile else get_user_profile_by_user(user)
        settings = profile.settings or {}

        # Compute status
        if not c.password_created and c.invitation_expires_at and c.invitation_expires_at > datetime.now(timezone.utc):
            status = 'pending'
        elif c.password_created and user.is_active:
            status = 'active'
        elif not user.is_active:
            status = 'inactive'
        else:
            status = 'active'

        # Extract fields from settings
        goal = settings.get('goal', 'General Wellness')
        program = settings.get('program', 'General Wellness Plan')
        target_weight = settings.get('target_weight')
        target_date = settings.get('target_date')
        duration = settings.get('duration', '12 Weeks')
        medical_conditions = profile.medical_conditions or []
        allergies = profile.allergies or []

        # Mock compliance (can be computed from meal logs later)
        compliance = settings.get('compliance', 80) if settings else 80

        result.append({
            'id': str(c.id),
            'user_id': str(user.id),
            'name': f"{profile.first_name} {profile.last_name}".strip() or user.email,
            'email': user.email,
            'phone': profile.phone,
            'gender': profile.gender,
            'date_of_birth': profile.date_of_birth.isoformat() if profile.date_of_birth else None,
            'age': None,  # compute later if needed
            'weight_kg': float(profile.weight_kg) if profile.weight_kg else None,
            'height_cm': float(profile.height_cm) if profile.height_cm else None,
            'bmi': float(profile.bmi) if profile.bmi else None,
            'medical_conditions': medical_conditions,
            'allergies': allergies,
            'goal': goal,
            'target_weight': target_weight,
            'target_date': target_date,
            'program': program,
            'duration': duration,
            'status': status,
            'compliance': compliance,
            'created_at': c.created_at.isoformat() if c.created_at else None,
            'updated_at': c.updated_at.isoformat() if c.updated_at else None,
            'password_created': c.password_created,
            'invitation_expires_at': c.invitation_expires_at.isoformat() if c.invitation_expires_at else None,
        })
    return result


def assign_meal_plan(professional_user, data):
    prof = get_professional_by_user(professional_user)
    if not prof:
        return None, 'Professional not found'

    client_id = data.get('client_id')
    client = Client.query.filter_by(id=client_id, assigned_professional_id=prof.id).first()
    if not client:
        return None, 'Client not found or not under this professional'

    plan = MealPlan(
        client_id=client.id,
        professional_id=prof.id,
        title=data.get('name'),
        description=data.get('description'),
        start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date() if data.get('start_date') else None,
        end_date=datetime.strptime(data['end_date'], '%Y-%m-%d').date() if data.get('end_date') else None,
        daily_calories=data.get('daily_calories'),
        notes=data.get('notes'),
        created_by_user_id=professional_user.id,
        is_ai_generated=False
    )
    db.session.add(plan)
    db.session.flush()

    meals_data = data.get('meals', [])
    for meal_data in meals_data:
        meal = Meal(
            meal_plan_id=plan.id,
            recipe_id=meal_data.get('recipe_id'),
            meal_type=meal_data.get('meal_type'),
            scheduled_date=datetime.strptime(meal_data['scheduled_date'], '%Y-%m-%d').date(),
            scheduled_time=datetime.strptime(meal_data['scheduled_time'], '%H:%M').time() if meal_data.get('scheduled_time') else None,
            custom_name=meal_data.get('custom_name'),
            notes=meal_data.get('notes')
        )
        db.session.add(meal)

    db.session.commit()
    return plan, None


# ----------------------------------------------------------------------
# Send client message (email)
# ----------------------------------------------------------------------

def send_client_message(professional_user, client_id, subject, message):
    """Send an email message to the client."""
    client = Client.query.get(client_id)
    if not client:
        return False, 'Client not found'
    prof = get_professional_by_user(professional_user)
    if not prof or client.assigned_professional_id != prof.id:
        return False, 'Unauthorized'

    client_user = client.user
    client_profile = client_user.profile
    client_name = f"{client_profile.first_name} {client_profile.last_name}".strip() or client_user.email
    prof_name = f"{professional_user.profile.first_name} {professional_user.profile.last_name}".strip() or professional_user.email

    success = send_client_message_email(
        client_user.email,
        client_name,
        subject,
        message,
        prof_name
    )
    if success:
        create_notification(
            user_id=client_user.id,
            title=f"Message from {prof_name}",
            message=message,
            type='message',
            action_url=None
        )
        return True, None
    return False, 'Failed to send email'


# ----------------------------------------------------------------------
# Professional – Programs (Meal Plans) for the Programs tab
# ----------------------------------------------------------------------

def get_professional_meal_plans(professional_user):
    """
    Get all meal plans (programs) created by this professional.
    Used for the Programs tab in the frontend.
    """
    prof = get_professional_by_user(professional_user)
    if not prof:
        return []

    plans = MealPlan.query.filter_by(professional_id=prof.id).order_by(MealPlan.created_at.desc()).all()
    result = []
    for p in plans:
        client_name = None
        if p.client:
            client_profile = p.client.user.profile
            if client_profile:
                client_name = f"{client_profile.first_name} {client_profile.last_name}".strip()
        result.append({
            'id': str(p.id),
            'title': p.title,
            'description': p.description,
            'client_id': str(p.client_id) if p.client_id else None,
            'client_name': client_name,
            'start_date': p.start_date.isoformat() if p.start_date else None,
            'end_date': p.end_date.isoformat() if p.end_date else None,
            'daily_calories': p.daily_calories,
            'is_ai_generated': p.is_ai_generated,
            'created_at': p.created_at.isoformat()
        })
    return result


# ----------------------------------------------------------------------
# Admin
# ----------------------------------------------------------------------

def get_pending_professionals():
    profs = Professional.query.filter_by(approval_status='pending').all()
    result = []
    for p in profs:
        profile = get_user_profile_by_user(p.user)
        result.append({
            'professional_id': str(p.id),
            'user_id': str(p.user_id),
            'email': p.user.email,
            'name': f"{profile.first_name} {profile.last_name}",
            'specialty': [cat.name for cat in p.categories],
            'license_number': p.license_number,
            'qualification': p.qualification,
            'years_experience': p.years_experience,
            'bio': p.biography,
            'created_at': p.created_at.isoformat()
        })
    return result


def approve_professional(admin_user, professional_id):
    prof = Professional.query.get(professional_id)
    if not prof:
        return False, 'Professional not found'
    prof.approval_status = 'approved'
    db.session.commit()
    return True, None


def reject_professional(admin_user, professional_id):
    prof = Professional.query.get(professional_id)
    if not prof:
        return False, 'Professional not found'
    prof.approval_status = 'rejected'
    db.session.commit()
    return True, None


def suspend_professional(admin_user, professional_id):
    prof = Professional.query.get(professional_id)
    if not prof:
        return False, 'Professional not found'
    user = User.query.get(prof.user_id)
    if user:
        user.is_active = False
        db.session.commit()
    return True, None


def activate_professional(admin_user, professional_id):
    prof = Professional.query.get(professional_id)
    if not prof:
        return False, 'Professional not found'
    user = User.query.get(prof.user_id)
    if user:
        user.is_active = True
    db.session.commit()
    return True, None


def get_system_stats():
    return {
        'total_users': User.query.count(),
        'total_professionals': Professional.query.count(),
        'total_clients': Client.query.count(),
        'total_foods': Food.query.count(),
        'total_recipes': Recipe.query.count(),
        'pending_professionals': Professional.query.filter_by(approval_status='pending').count()
    }


# ===== ADMIN DATA & CRUD FUNCTIONS =====

def get_all_users():
    """Return only users with role='user'."""
    users = User.query.filter_by(role='user').all()
    result = []
    for u in users:
        profile = u.profile
        result.append({
            'id': str(u.id),
            'email': u.email,
            'first_name': profile.first_name if profile else None,
            'last_name': profile.last_name if profile else None,
            'role': u.role,
            'status': u.status,
            'is_active': u.is_active,
            'plan': profile.settings.get('plan', 'Free') if profile and profile.settings else 'Free',
            'created_at': u.created_at.isoformat() if u.created_at else None
        })
    return result


def get_all_professionals():
    """Return only users with role='professional', joined with Professional table."""
    users = User.query.filter_by(role='professional').all()
    result = []
    for u in users:
        profile = u.profile
        p = Professional.query.filter_by(user_id=u.id).first()
        result.append({
            'id': str(p.id) if p else None,
            'user_id': str(u.id),
            'name': f"{profile.first_name} {profile.last_name}" if profile else u.email,
            'email': u.email,
            'profession': p.qualification if p else 'Nutritionist',
            'specialization': [cat.name for cat in p.categories] if p else [],
            'license_number': p.license_number if p else None,
            'approval_status': p.approval_status if p else 'pending',
            'years_experience': p.years_experience if p else 0,
            'is_active': u.is_active,
            'created_at': p.created_at.isoformat() if p and p.created_at else None
        })
    return result


def get_all_clients():
    """Return only users with role='client', joined with Client table."""
    users = User.query.filter_by(role='client').all()
    result = []
    for u in users:
        profile = u.profile
        c = Client.query.filter_by(user_id=u.id).first()
        assigned_pro = c.professional if c else None
        pro_name = None
        if assigned_pro and assigned_pro.user and assigned_pro.user.profile:
            pro_name = f"{assigned_pro.user.profile.first_name} {assigned_pro.user.profile.last_name}"
        result.append({
            'id': str(c.id) if c else None,
            'user_id': str(u.id),
            'name': f"{profile.first_name} {profile.last_name}" if profile else u.email,
            'email': u.email,
            'assigned_professional': pro_name,
            'assigned_professional_id': str(c.assigned_professional_id) if c and c.assigned_professional_id else None,
            'medical_history': c.medical_history if c else None,
            'goal': profile.settings.get('goal', 'General') if profile and profile.settings else 'General',
            'progress': profile.settings.get('progress', 0) if profile and profile.settings else 0,
            'status': 'Active' if u.is_active else 'Inactive',
            'created_at': c.created_at.isoformat() if c and c.created_at else None
        })
    return result


# ---- Users Admin CRUD ----
def get_user_by_id_for_admin(user_id):
    return User.query.get(user_id)


def suspend_user_by_admin(admin_user, user_id):
    user = User.query.get(user_id)
    if not user:
        return False, 'User not found'
    user.is_active = False
    db.session.commit()
    return True, None


def activate_user_by_admin(admin_user, user_id):
    user = User.query.get(user_id)
    if not user:
        return False, 'User not found'
    user.is_active = True
    db.session.commit()
    return True, None


def delete_user_by_admin(admin_user, user_id):
    user = User.query.get(user_id)
    if not user:
        return False, 'User not found'
    user.is_active = False  # soft delete
    db.session.commit()
    return True, None


def upgrade_user_by_admin(admin_user, user_id):
    user = User.query.get(user_id)
    if not user:
        return False, 'User not found'
    profile = get_user_profile_by_user(user)
    if not profile:
        return False, 'User profile not found'
    if not profile.settings:
        profile.settings = {}
    profile.settings['plan'] = 'Premium'
    db.session.commit()
    return True, None


def update_user_by_admin(admin_user, user_id, data):
    user = User.query.get(user_id)
    if not user:
        return False, 'User not found'
    profile = get_user_profile_by_user(user)
    if 'first_name' in data:
        profile.first_name = data['first_name']
    if 'last_name' in data:
        profile.last_name = data['last_name']
    if 'email' in data:
        user.email = data['email']
    if 'plan' in data:
        if not profile.settings:
            profile.settings = {}
        profile.settings['plan'] = data['plan']
    if 'is_active' in data:
        user.is_active = data['is_active']
    db.session.commit()
    return True, None


def create_user_by_admin(admin_user, data):
    email = data.get('email')
    password = data.get('password') or 'TempPass123!'
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    role = data.get('role', 'user')
    if not all([email, first_name, last_name]):
        return None, 'Missing required fields'
    if not validate_email(email):
        return None, 'Invalid email format'
    if User.query.filter_by(email=email).first():
        return None, 'Email already exists'
    hashed = bcrypt.generate_password_hash(password).decode('utf-8')
    user = User(email=email, password_hash=hashed, role=role)
    db.session.add(user)
    db.session.flush()
    profile = UserProfile(user_id=user.id, first_name=first_name, last_name=last_name)
    db.session.add(profile)
    db.session.commit()
    return user, None


# ---- Professionals Admin CRUD ----
def suspend_professional_by_admin(admin_user, professional_id):
    prof = Professional.query.get(professional_id)
    if not prof:
        return False, 'Professional not found'
    user = User.query.get(prof.user_id)
    if user:
        user.is_active = False
    db.session.commit()
    return True, None


def activate_professional_by_admin(admin_user, professional_id):
    prof = Professional.query.get(professional_id)
    if not prof:
        return False, 'Professional not found'
    user = User.query.get(prof.user_id)
    if user:
        user.is_active = True
    db.session.commit()
    return True, None


def delete_professional_by_admin(admin_user, professional_id):
    prof = Professional.query.get(professional_id)
    if not prof:
        return False, 'Professional not found'
    user = User.query.get(prof.user_id)
    if user:
        user.is_active = False
    db.session.commit()
    return True, None


def update_professional_by_admin(admin_user, professional_id, data):
    prof = Professional.query.get(professional_id)
    if not prof:
        return False, 'Professional not found'
    user = User.query.get(prof.user_id)
    if not user:
        return False, 'User not found'
    profile = get_user_profile_by_user(user)
    if 'name' in data:
        parts = data['name'].split(' ', 1)
        profile.first_name = parts[0]
        profile.last_name = parts[1] if len(parts) > 1 else ''
    if 'email' in data:
        user.email = data['email']
    if 'profession' in data:
        prof.qualification = data['profession']
    if 'specialization' in data:
        prof.biography = data['specialization']
    if 'status' in data:
        prof.approval_status = data['status']
    if 'is_active' in data:
        user.is_active = data['is_active']
    db.session.commit()
    return True, None


def create_professional_by_admin(admin_user, data):
    email = data.get('email')
    password = data.get('password') or 'TempPass123!'
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    if not all([email, first_name, last_name]):
        return None, 'Missing required fields'
    if not validate_email(email):
        return None, 'Invalid email format'
    if User.query.filter_by(email=email).first():
        return None, 'Email already exists'
    hashed = bcrypt.generate_password_hash(password).decode('utf-8')
    user = User(email=email, password_hash=hashed, role='professional')
    db.session.add(user)
    db.session.flush()
    profile = UserProfile(user_id=user.id, first_name=first_name, last_name=last_name)
    db.session.add(profile)
    prof = Professional(user_id=user.id, approval_status='pending')
    db.session.add(prof)
    db.session.commit()
    return user, None


# ---- Clients Admin CRUD ----
def suspend_client_by_admin(admin_user, client_id):
    client = Client.query.get(client_id)
    if not client:
        return False, 'Client not found'
    user = User.query.get(client.user_id)
    if user:
        user.is_active = False
    db.session.commit()
    return True, None


def activate_client_by_admin(admin_user, client_id):
    client = Client.query.get(client_id)
    if not client:
        return False, 'Client not found'
    user = User.query.get(client.user_id)
    if user:
        user.is_active = True
    db.session.commit()
    return True, None


def delete_client_by_admin(admin_user, client_id):
    client = Client.query.get(client_id)
    if not client:
        return False, 'Client not found'
    user = User.query.get(client.user_id)
    if user:
        user.is_active = False
    db.session.commit()
    return True, None


def update_client_by_admin(admin_user, client_id, data):
    client = Client.query.get(client_id)
    if not client:
        return False, 'Client not found'
    user = User.query.get(client.user_id)
    if not user:
        return False, 'User not found'
    profile = get_user_profile_by_user(user)
    if 'name' in data:
        parts = data['name'].split(' ', 1)
        profile.first_name = parts[0]
        profile.last_name = parts[1] if len(parts) > 1 else ''
    if 'email' in data:
        user.email = data['email']
    if 'assigned_professional' in data and data['assigned_professional']:
        pro = Professional.query.join(User).join(UserProfile).filter(
            db.func.concat(UserProfile.first_name, ' ', UserProfile.last_name) == data['assigned_professional']
        ).first()
        if pro:
            client.assigned_professional_id = pro.id
    if 'goal' in data:
        if not profile.settings:
            profile.settings = {}
        profile.settings['goal'] = data['goal']
    if 'progress' in data:
        if not profile.settings:
            profile.settings = {}
        profile.settings['progress'] = data['progress']
    if 'status' in data:
        user.is_active = (data['status'] == 'Active')
    db.session.commit()
    return True, None


def create_client_by_admin(admin_user, data):
    email = data.get('email')
    password = data.get('password') or 'TempPass123!'
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    assigned_professional_name = data.get('assigned_professional')
    if not all([email, first_name, last_name]):
        return None, 'Missing required fields'
    if not validate_email(email):
        return None, 'Invalid email format'
    if User.query.filter_by(email=email).first():
        return None, 'Email already exists'
    hashed = bcrypt.generate_password_hash(password).decode('utf-8')
    user = User(email=email, password_hash=hashed, role='client')
    db.session.add(user)
    db.session.flush()
    profile = UserProfile(user_id=user.id, first_name=first_name, last_name=last_name)
    db.session.add(profile)
    client = Client(user_id=user.id)
    if assigned_professional_name:
        pro = Professional.query.join(User).join(UserProfile).filter(
            db.func.concat(UserProfile.first_name, ' ', UserProfile.last_name) == assigned_professional_name
        ).first()
        if pro:
            client.assigned_professional_id = pro.id
    db.session.add(client)
    db.session.commit()
    return user, None


# ----------------------------------------------------------------------
# Foods
# ----------------------------------------------------------------------

def search_foods(query, category=None, limit=20):
    q = Food.query
    if query:
        q = q.filter(Food.name.ilike(f'%{query}%'))
    if category:
        q = q.join(FoodCategory).filter(FoodCategory.name == category)
    return q.limit(limit).all()


def get_food_details(food_id):
    return Food.query.get(food_id)


# ----------------------------------------------------------------------
# Recipes
# ----------------------------------------------------------------------

def search_recipes(query, category=None):
    q = Recipe.query
    if query:
        q = q.filter(Recipe.title.ilike(f'%{query}%'))
    if category:
        q = q.filter(Recipe.cuisine == category)
    return q.all()


def get_recipe_details(recipe_id):
    recipe = Recipe.query.get(recipe_id)
    if not recipe:
        return None
    ingredients = [{
        'food_id': str(ri.food_id) if ri.food_id else None,
        'food_name': ri.food.name if ri.food else ri.ingredient_name,
        'quantity': float(ri.quantity) if ri.quantity else None,
        'unit': ri.unit,
        'notes': ri.notes
    } for ri in recipe.ingredients]
    steps = [{'step_number': s.step_number, 'instruction': s.instruction} for s in recipe.steps]
    return {
        'id': str(recipe.id),
        'title': recipe.title,
        'description': recipe.description,
        'cuisine': recipe.cuisine,
        'meal_type': recipe.meal_type,
        'difficulty': recipe.difficulty,
        'prep_time': recipe.prep_time_minutes,
        'cook_time': recipe.cook_time_minutes,
        'total_time': recipe.total_time_minutes,
        'servings': recipe.servings,
        'image_url': recipe.image_url,
        'nutrition_summary': recipe.nutrition_summary,
        'ingredients': ingredients,
        'steps': steps,
        'created_at': recipe.created_at.isoformat()
    }


# ----------------------------------------------------------------------
# Meal Planning
# ----------------------------------------------------------------------

def get_client_meal_plans(client_id):
    plans = MealPlan.query.filter_by(client_id=client_id).all()
    return [{
        'id': str(p.id),
        'title': p.title,
        'start_date': p.start_date.isoformat() if p.start_date else None,
        'end_date': p.end_date.isoformat() if p.end_date else None,
        'daily_calories': p.daily_calories,
        'is_ai_generated': p.is_ai_generated
    } for p in plans]


# ----------------------------------------------------------------------
# Goals
# ----------------------------------------------------------------------

def track_goal(user_id, data):
    goal_type = data.get('goal_type')
    target_value = data.get('target_value')
    current_value = data.get('current_value')
    unit = data.get('unit', 'kg')
    target_date = data.get('target_date')
    if not goal_type or target_value is None:
        return None, 'Missing required fields'

    goal = GoalTracker.query.filter_by(user_id=user_id, goal_type=goal_type).first()
    if not goal:
        goal = GoalTracker(user_id=user_id, goal_type=goal_type, start_date=datetime.utcnow().date())
    goal.target_value = target_value
    if current_value is not None:
        goal.current_value = current_value
    goal.unit = unit
    if target_date:
        goal.target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
    db.session.add(goal)
    db.session.commit()
    return goal, None


def get_user_goals(user_id):
    return GoalTracker.query.filter_by(user_id=user_id).all()


def log_goal_progress(goal_id, value, notes=None):
    goal = GoalTracker.query.get(goal_id)
    if not goal:
        return None, 'Goal not found'
    progress = GoalProgress(goal_id=goal.id, value=value, notes=notes)
    db.session.add(progress)
    goal.current_value = value
    db.session.commit()
    return progress, None


# ----------------------------------------------------------------------
# Water Tracking
# ----------------------------------------------------------------------

def track_water(user_id, amount_ml):
    if amount_ml <= 0:
        return None, 'Amount must be positive'
    log = WaterLog(user_id=user_id, amount_ml=amount_ml)
    db.session.add(log)
    db.session.commit()
    return log, None


def get_water_history(user_id, days=7):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    return WaterLog.query.filter_by(user_id=user_id)\
                         .filter(WaterLog.logged_at >= since)\
                         .order_by(WaterLog.logged_at.desc()).all()


# ----------------------------------------------------------------------
# Shopping Lists
# ----------------------------------------------------------------------

def generate_shopping_list(client_id, meal_plan_id):
    plan = MealPlan.query.get(meal_plan_id)
    if not plan or plan.client_id != client_id:
        return None, 'Invalid meal plan'

    shopping_list = ShoppingList(
        client_id=client_id,
        meal_plan_id=meal_plan_id,
        title=f"Shopping List for {plan.title}"
    )
    db.session.add(shopping_list)
    db.session.flush()

    ingredient_map = {}
    meals = Meal.query.filter_by(meal_plan_id=plan.id).all()
    for meal in meals:
        if meal.recipe:
            for ing in meal.recipe.ingredients:
                if ing.food_id:
                    key = ing.food_id
                    if key in ingredient_map:
                        ingredient_map[key]['quantity'] += ing.quantity or 0
                    else:
                        ingredient_map[key] = {
                            'food_id': key,
                            'ingredient_name': ing.food.name if ing.food else ing.ingredient_name,
                            'quantity': ing.quantity or 0,
                            'unit': ing.unit
                        }

    for food_id, data in ingredient_map.items():
        item = ShoppingItem(
            shopping_list_id=shopping_list.id,
            food_id=food_id,
            item_name=data['ingredient_name'],
            quantity=data['quantity'],
            unit=data['unit']
        )
        db.session.add(item)

    db.session.commit()
    return shopping_list, None


# ----------------------------------------------------------------------
# Notifications
# ----------------------------------------------------------------------

def create_notification(user_id, title, message, type='general', action_url=None):
    notif = Notification(
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        action_url=action_url
    )
    db.session.add(notif)
    db.session.commit()
    return notif


def get_user_notifications(user_id, unread_only=False):
    q = Notification.query.filter_by(user_id=user_id)
    if unread_only:
        q = q.filter_by(is_read=False)
    return q.order_by(Notification.created_at.desc()).all()


def mark_notification_read(notification_id, user_id):
    notif = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
    if notif:
        notif.is_read = True
        db.session.commit()
        return True
    return False


def get_user_notification_preferences(user_id):
    pref = NotificationPreference.query.filter_by(user_id=user_id).first()
    if not pref:
        pref = NotificationPreference(user_id=user_id)
        db.session.add(pref)
        db.session.commit()
    return pref


def update_notification_preferences(user_id, data):
    pref = get_user_notification_preferences(user_id)
    if 'email_notifications' in data:
        pref.email_notifications = data['email_notifications']
    if 'push_notifications' in data:
        pref.push_notifications = data['push_notifications']
    if 'sms_notifications' in data:
        pref.sms_notifications = data['sms_notifications']
    if 'preferences' in data:
        pref.preferences = data['preferences']
    db.session.commit()
    return pref


# ----------------------------------------------------------------------
# AI Chat
# ----------------------------------------------------------------------

def get_ai_response(user, question, conversation_id=None):
    if conversation_id:
        conversation = AIConversation.query.get(conversation_id)
        if not conversation or conversation.user_id != user.id:
            return None, 'Conversation not found'
    else:
        conversation = AIConversation(
            user_id=user.id,
            title=f"Chat {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
        )
        db.session.add(conversation)
        db.session.flush()

    user_msg = AIMessage(
        conversation_id=conversation.id,
        sender='user',
        content=question
    )
    db.session.add(user_msg)

    provider = current_app.config.get('AI_PROVIDER', 'mock')
    if provider == 'mock':
        ai_reply = _mock_ai_response(user, question)
    elif provider == 'openai':
        ai_reply = _openai_ai_response(user, question)
    else:
        ai_reply = "AI service not configured."

    ai_msg = AIMessage(
        conversation_id=conversation.id,
        sender='ai',
        content=ai_reply,
        prompt=question
    )
    db.session.add(ai_msg)
    db.session.commit()

    return {
        'conversation_id': str(conversation.id),
        'response': ai_reply,
        'message_id': str(ai_msg.id)
    }, None


def _mock_ai_response(user, question):
    return f"Mock AI: I received your question: '{question}'. I will analyze your profile and provide nutrition advice."


def _openai_ai_response(user, question):
    import openai
    openai.api_key = current_app.config.get('OPENAI_API_KEY')
    if not openai.api_key:
        return "OpenAI API key not set."

    profile = get_user_profile_by_user(user)
    context = f"User: {profile.first_name} {profile.last_name}, role: {user.role}.\n"
    if user.role == 'client':
        client = get_client_by_user(user)
        if client:
            context += f"Health conditions: {', '.join([c.name for c in user.health_conditions]) or 'None'}\n"
            context += f"Diet preference: {profile.diet_preference if profile.diet_preference else 'Not set'}\n"
            context += f"Allergies: {', '.join(profile.allergies) if profile.allergies else 'None'}\n"
            goals = GoalTracker.query.filter_by(user_id=user.id).all()
            if goals:
                context += "Goals:\n"
                for g in goals:
                    context += f"- {g.goal_type}: target {g.target_value} {g.unit}, current {g.current_value}\n"

    prompt = f"You are a nutritionist for the Smart Lishe platform. Given the following user context:\n{context}\nAnswer the following question:\n{question}\nProvide personalized advice."
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are a helpful nutrition assistant."},
                      {"role": "user", "content": prompt}],
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"AI error: {str(e)}"


# ----------------------------------------------------------------------
# Subscriptions (Memberships)
# ----------------------------------------------------------------------

def get_subscription_plans():
    return SubscriptionPlan.query.filter_by(is_active=True).all()


def subscribe_user(user_id, plan_id, payment_data=None):
    plan = SubscriptionPlan.query.get(plan_id)
    if not plan:
        return None, 'Plan not found'

    existing = UserSubscription.query.filter_by(user_id=user_id, status='active').first()
    if existing:
        existing.status = 'canceled'

    now = datetime.now(timezone.utc)
    if plan.billing_cycle == 'monthly':
        duration = timedelta(days=30)
    elif plan.billing_cycle == 'quarterly':
        duration = timedelta(days=90)
    else:
        duration = timedelta(days=365)

    subscription = UserSubscription(
        user_id=user_id,
        plan_id=plan.id,
        status='pending',
        starts_at=now,
        expires_at=now + duration,
        auto_renew=False
    )
    db.session.add(subscription)
    db.session.flush()

    gateway = current_app.config.get('PAYMENT_GATEWAY', 'mock')
    payment_result = _process_payment(gateway, plan.price, plan.currency, payment_data)
    if payment_result['success']:
        subscription.status = 'active'
        payment = Payment(
            user_id=user_id,
            subscription_id=subscription.id,
            amount=plan.price,
            currency=plan.currency,
            method=payment_data.get('method') if payment_data else None,
            status='completed',
            transaction_reference=payment_result.get('transaction_id'),
            payment_date=datetime.now(timezone.utc)
        )
        db.session.add(payment)
    else:
        subscription.status = 'canceled'
        payment = Payment(
            user_id=user_id,
            subscription_id=subscription.id,
            amount=plan.price,
            currency=plan.currency,
            status='failed',
            transaction_reference=payment_result.get('transaction_id')
        )
        db.session.add(payment)

    db.session.commit()
    return subscription, None


def _process_payment(gateway, amount, currency, data):
    if gateway == 'mock':
        return {'success': True, 'transaction_id': f'mock_{uuid.uuid4().hex[:8]}'}
    elif gateway == 'stripe':
        return {'success': False, 'error': 'Stripe not implemented'}
    elif gateway == 'mpesa':
        return {'success': False, 'error': 'M-Pesa not implemented'}
    else:
        return {'success': False, 'error': 'Payment gateway not configured'}


# ----------------------------------------------------------------------
# Contact / Support
# ----------------------------------------------------------------------

def create_contact_message(data, user=None):
    name = data.get('name')
    email = data.get('email')
    subject = data.get('subject')
    message = data.get('message')
    if not all([name, email, subject, message]):
        return None, 'All fields required'

    contact = ContactMessage(
        user_id=user.id if user else None,
        name=name,
        email=email,
        subject=subject,
        message=message
    )
    db.session.add(contact)
    db.session.commit()
    return contact, None