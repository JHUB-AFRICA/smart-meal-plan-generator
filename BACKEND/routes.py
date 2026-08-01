import uuid
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app

# All utils functions now come from the single utils.py file
from utils import (
    token_required, role_required, admin_required,
    professional_required, client_required,
    success_response, error_response,
    send_email, generate_password_reset_token
)
from services import *
from extensions import db

# Import models used directly in route handlers
from models import (
    MealPlan, Client, ShoppingList, ShoppingItem, GoalTracker, GoalProgress,
    AIConversation, UserSubscription, ContactMessage, AuditLog,
    UserWeeklyPlan,
    ApplicationSetting, NotificationPreference,
    Professional, User,
    Appointment, Report,
    PasswordResetToken,
    Payment, SubscriptionPlan, Invoice
)

api_bp = Blueprint('api', __name__)

# ---------- Authentication ----------
@api_bp.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    user, err = register_user(data)
    if err:
        return error_response(err, status_code=400)
    return success_response('User registered successfully', {'user_id': str(user.id)})

@api_bp.route('/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if data is None:
            return error_response('Invalid JSON body. Ensure Content-Type is application/json.', status_code=400)
        email = data.get('email')
        password = data.get('password')
        if not email or not password:
            return error_response('Email and password required', status_code=400)
        token, err = login_user(email, password)
        if err:
            return error_response(err, status_code=401)
        return success_response('Login successful', {'access_token': token})
    except Exception as e:
        current_app.logger.error(f'Login error: {e}', exc_info=True)
        return error_response('An internal server error occurred during login.', status_code=500)

# ---------- Password Reset (with email & debugging) ----------
@api_bp.route('/auth/request-reset', methods=['POST'])
def request_reset():
    data = request.get_json()
    email = data.get('email')
    if not email:
        return error_response('Email required', status_code=400)

    user = User.query.filter_by(email=email).first()
    if user:
        try:
            token = generate_password_reset_token(user.id)
            current_app.logger.info(f"Generated reset token for {email}: {token}")
            
            stored = PasswordResetToken.query.filter_by(token=token, used=False).first()
            if stored:
                current_app.logger.info(f"Token successfully stored in DB: {stored.id}")
            else:
                current_app.logger.error(f"Token NOT found in DB after generation!")

            link = f"{current_app.config['FRONTEND_URL']}/auth/reset-password.html?token={token}"
            send_email(
                to=email,
                subject="Reset your Smart Lishe password",
                template='reset_password.html',
                link=link
            )
        except Exception as e:
            current_app.logger.error(f"Error during reset request: {e}", exc_info=True)
            return error_response('Failed to process reset request', 500)
    else:
        current_app.logger.info(f"Reset requested for non-existent email: {email}")

    return success_response('If that email exists, we sent a reset link.')

@api_bp.route('/auth/reset-password', methods=['POST'])
def reset_password_route():
    data = request.get_json()
    token = data.get('token')
    new_password = data.get('new_password')
    if not token or not new_password:
        return error_response('Token and new password required', status_code=400)
    if len(new_password) < 8:
        return error_response('Password must be at least 8 characters', status_code=400)

    token_entry = PasswordResetToken.query.filter_by(token=token).first()
    if token_entry:
        current_app.logger.info(f"Reset attempt for token: {token}, used={token_entry.used}, expires={token_entry.expires_at}")
    else:
        current_app.logger.warning(f"Reset attempt with non-existent token: {token}")

    success, err = reset_password(token, new_password)
    if not success:
        return error_response(err, status_code=400)
    return success_response('Password reset successfully')

# ---------- User Profile ----------
@api_bp.route('/profile', methods=['GET'])
@token_required
def get_profile():
    data = get_user_profile(request.user)
    return success_response('Profile retrieved', data)

@api_bp.route('/profile', methods=['PUT'])
@token_required
def update_profile():
    data = request.get_json()
    if update_user_profile(request.user, data):
        return success_response('Profile updated')
    return error_response('Update failed', status_code=400)

@api_bp.route('/profile/password', methods=['PUT'])
@token_required
def change_password_route():
    data = request.get_json()
    old = data.get('old_password')
    new = data.get('new_password')
    if not old or not new:
        return error_response('Old and new password required', status_code=400)
    ok, err = change_password(request.user, old, new)
    if not ok:
        return error_response(err, status_code=400)
    return success_response('Password changed')

@api_bp.route('/profile/image', methods=['POST'])
@token_required
def upload_profile_image_route():
    if 'image' not in request.files:
        return error_response('No image file provided', status_code=400)
    file = request.files['image']
    path, err = upload_profile_image(request.user, file)
    if err:
        return error_response(err, status_code=400)
    return success_response('Profile image uploaded', {'image_url': path})

@api_bp.route('/profile', methods=['DELETE'])
@token_required
def delete_account():
    user = request.user
    user.is_active = False
    db.session.commit()
    return success_response('Account deactivated')

# ---------- Professional ----------
@api_bp.route('/professional/clients', methods=['POST'])
@token_required
@professional_required
def create_client():
    data = request.get_json()
    user, err = create_client_by_professional(request.user, data)
    if err:
        return error_response(err, status_code=400)
    return success_response('Client created', {'client_id': str(user.id)})

@api_bp.route('/professional/clients', methods=['GET'])
@token_required
@professional_required
def list_clients():
    clients = get_clients_for_professional(request.user)
    return success_response('Clients retrieved', clients)

@api_bp.route('/professional/mealplans', methods=['POST'])
@token_required
@professional_required
def create_meal_plan():
    data = request.get_json()
    plan, err = assign_meal_plan(request.user, data)
    if err:
        return error_response(err, status_code=400)
    return success_response('Meal plan created', {'plan_id': str(plan.id)})

@api_bp.route('/professional/mealplans/<uuid:plan_id>', methods=['GET'])
@token_required
@professional_required
def get_meal_plan_details(plan_id):
    plan = MealPlan.query.get(plan_id)
    if not plan:
        return error_response('Meal plan not found', status_code=404)
    prof = get_professional_by_user(request.user)
    if not prof or plan.professional_id != prof.id:
        return error_response('Unauthorized', status_code=403)
    meals = []
    for meal in plan.meals:
        meals.append({
            'id': str(meal.id),
            'meal_type': meal.meal_type.value,
            'scheduled_date': meal.scheduled_date.isoformat(),
            'scheduled_time': meal.scheduled_time.isoformat() if meal.scheduled_time else None,
            'recipe_id': str(meal.recipe_id) if meal.recipe_id else None,
            'custom_name': meal.custom_name,
            'notes': meal.notes
        })
    return success_response('Meal plan details', {
        'id': str(plan.id),
        'title': plan.title,
        'description': plan.description,
        'start_date': plan.start_date.isoformat() if plan.start_date else None,
        'end_date': plan.end_date.isoformat() if plan.end_date else None,
        'daily_calories': plan.daily_calories,
        'meals': meals,
        'is_ai_generated': plan.is_ai_generated
    })

# ====================================================================
# Professional Meal Plans (hyphenated, null-safe)
# ====================================================================
@api_bp.route('/professional/meal-plans', methods=['GET'])
@token_required
@professional_required
def get_professional_meal_plans_hyphen():
    """Get all meal plans created by the logged-in professional (null-safe)."""
    prof = Professional.query.filter_by(user_id=request.user.id).first()
    if not prof:
        return error_response('Professional not found', 404)

    plans = MealPlan.query.filter_by(professional_id=prof.id).order_by(MealPlan.created_at.desc()).all()
    result = []
    for p in plans:
        client_name = ''
        if p.client_id:
            client = Client.query.get(p.client_id)
            if client and client.user:
                profile = client.user.profile
                if profile and profile.first_name:
                    client_name = f"{profile.first_name} {profile.last_name or ''}".strip()
                else:
                    client_name = client.user.email or 'Unknown'
        result.append({
            'id': str(p.id),
            'title': p.title,
            'description': p.description,
            'client_id': str(p.client_id) if p.client_id else None,
            'client_name': client_name,
            'start_date': p.start_date.isoformat() if p.start_date else None,
            'end_date': p.end_date.isoformat() if p.end_date else None,
            'daily_calories': p.daily_calories,
            'status': p.status or 'active',
            'duration': f"{(p.end_date - p.start_date).days // 7} weeks" if p.start_date and p.end_date else None,
            'created_at': p.created_at.isoformat() if p.created_at else None
        })
    return success_response('Meal plans retrieved', result)


@api_bp.route('/professional/meal-plans', methods=['POST'])
@token_required
@professional_required
def create_professional_meal_plan_hyphen():
    """Create a new meal plan (program) for a client (null-safe)."""
    data = request.get_json()
    if not data:
        return error_response('No data provided', 400)

    title = data.get('title')
    client_id = data.get('client_id')
    if not title or not client_id:
        return error_response('title and client_id are required', 400)

    prof = Professional.query.filter_by(user_id=request.user.id).first()
    if not prof:
        return error_response('Professional not found', 404)

    client = Client.query.filter_by(id=client_id, assigned_professional_id=prof.id).first()
    if not client:
        return error_response('Client not found or not under your care', 404)

    try:
        plan = MealPlan(
            title=title,
            description=data.get('description', ''),
            client_id=client.id,
            professional_id=prof.id,
            created_by_user_id=prof.user_id,
            start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date() if data.get('start_date') else None,
            end_date=datetime.strptime(data['end_date'], '%Y-%m-%d').date() if data.get('end_date') else None,
            daily_calories=data.get('daily_calories', 0),
            status=data.get('status', 'active')
        )
        db.session.add(plan)
        db.session.commit()
        return success_response('Meal plan created', {'plan_id': str(plan.id)})
    except Exception as e:
        db.session.rollback()
        return error_response(f'Database error: {str(e)}', 500)

# ---------- Client ----------
@api_bp.route('/client/mealplans', methods=['GET'])
@token_required
@client_required
def get_client_meal_plans_route():
    client = Client.query.filter_by(user_id=request.user.id).first()
    if not client:
        return error_response('Client profile not found', status_code=404)
    plans = get_client_meal_plans(client.id)
    return success_response('Meal plans retrieved', plans)

@api_bp.route('/client/mealplans/<uuid:plan_id>/shoppinglist', methods=['POST'])
@token_required
@client_required
def generate_shopping_list_route(plan_id):
    client = Client.query.filter_by(user_id=request.user.id).first()
    if not client:
        return error_response('Client not found', status_code=404)
    sl, err = generate_shopping_list(client.id, plan_id)
    if err:
        return error_response(err, status_code=400)
    return success_response('Shopping list generated', {'list_id': str(sl.id)})

@api_bp.route('/client/shoppinglists', methods=['GET'])
@token_required
@client_required
def get_shopping_lists():
    client = Client.query.filter_by(user_id=request.user.id).first()
    if not client:
        return error_response('Client not found', status_code=404)
    lists = ShoppingList.query.filter_by(client_id=client.id).all()
    result = [{
        'id': str(sl.id),
        'title': sl.title,
        'is_completed': sl.is_completed,
        'created_at': sl.created_at.isoformat(),
        'item_count': len(sl.items)
    } for sl in lists]
    return success_response('Shopping lists', result)

@api_bp.route('/client/shoppinglists/<uuid:list_id>', methods=['GET'])
@token_required
@client_required
def get_shopping_list_items(list_id):
    client = Client.query.filter_by(user_id=request.user.id).first()
    if not client:
        return error_response('Client not found', status_code=404)
    sl = ShoppingList.query.filter_by(id=list_id, client_id=client.id).first()
    if not sl:
        return error_response('Shopping list not found', status_code=404)
    items = [{
        'id': str(item.id),
        'item_name': item.item_name,
        'quantity': float(item.quantity) if item.quantity else None,
        'unit': item.unit,
        'is_completed': item.is_completed,
        'food_id': str(item.food_id) if item.food_id else None
    } for item in sl.items]
    return success_response('Shopping list items', {'list': sl.title, 'items': items})

@api_bp.route('/client/shoppinglists/<uuid:list_id>/items/<uuid:item_id>/toggle', methods=['PUT'])
@token_required
@client_required
def toggle_shopping_item(list_id, item_id):
    client = Client.query.filter_by(user_id=request.user.id).first()
    if not client:
        return error_response('Client not found', status_code=404)
    sl = ShoppingList.query.filter_by(id=list_id, client_id=client.id).first()
    if not sl:
        return error_response('Shopping list not found', status_code=404)
    item = ShoppingItem.query.filter_by(id=item_id, shopping_list_id=sl.id).first()
    if not item:
        return error_response('Item not found', status_code=404)
    item.is_completed = not item.is_completed
    db.session.commit()
    return success_response('Item toggled', {'is_completed': item.is_completed})

# ---------- Client Profile & Dashboard ----------
@api_bp.route('/client/me', methods=['GET'])
@token_required
@client_required
def client_me():
    """Get the authenticated client's profile."""
    client = Client.query.filter_by(user_id=request.user.id).first()
    if not client:
        return error_response('Client not found', status_code=404)
    profile = request.user.profile
    data = {
        'id': str(client.id),
        'user_id': str(client.user_id),
        'name': f"{profile.first_name} {profile.last_name}".strip() if profile else request.user.email,
        'email': request.user.email,
        'phone': profile.phone if profile else None,
        'date_of_birth': profile.date_of_birth.isoformat() if profile and profile.date_of_birth else None,
        'gender': profile.gender if profile else None,
        'height_cm': float(profile.height_cm) if profile and profile.height_cm else None,
        'weight_kg': float(profile.weight_kg) if profile and profile.weight_kg else None,
        'bmi': float(profile.bmi) if profile and profile.bmi else None,
        'medical_conditions': profile.medical_conditions if profile else [],
        'allergies': profile.allergies if profile else [],
        'goal': profile.settings.get('goal') if profile and profile.settings else None,
        'target_weight': profile.settings.get('target_weight') if profile and profile.settings else None,
        'target_date': profile.settings.get('target_date') if profile and profile.settings else None,
        'program': profile.settings.get('program') if profile and profile.settings else None,
        'duration': profile.settings.get('duration') if profile and profile.settings else None,
        'assigned_professional_id': str(client.assigned_professional_id) if client.assigned_professional_id else None,
        'password_created': client.password_created,
        'created_at': client.created_at.isoformat() if client.created_at else None
    }
    return success_response('Client profile', data)

@api_bp.route('/client/appointments', methods=['GET'])
@token_required
@client_required
def client_appointments():
    """Get all appointments for the authenticated client."""
    client = Client.query.filter_by(user_id=request.user.id).first()
    if not client:
        return error_response('Client not found', status_code=404)
    appts = Appointment.query.filter_by(client_id=client.id).order_by(Appointment.appointment_date.desc()).all()
    result = [{
        'id': str(a.id),
        'title': a.title,
        'description': a.description,
        'appointment_date': a.appointment_date.isoformat() if a.appointment_date else None,
        'appointment_time': a.appointment_time.strftime('%H:%M') if a.appointment_time else None,
        'duration_minutes': a.duration_minutes,
        'type': a.type,
        'status': a.status,
        'notes': a.notes,
        'created_at': a.created_at.isoformat() if a.created_at else None
    } for a in appts]
    return success_response('Client appointments', result)

@api_bp.route('/client/reports', methods=['GET'])
@token_required
@client_required
def client_reports():
    """Get all reports for the authenticated client."""
    client = Client.query.filter_by(user_id=request.user.id).first()
    if not client:
        return error_response('Client not found', status_code=404)
    reports = Report.query.filter_by(client_id=client.id).order_by(Report.generated_at.desc()).all()
    result = [{
        'id': str(r.id),
        'title': r.title,
        'report_type': r.report_type,
        'content': r.content,
        'file_url': r.file_url,
        'generated_at': r.generated_at.isoformat() if r.generated_at else None,
        'created_at': r.created_at.isoformat() if r.created_at else None
    } for r in reports]
    return success_response('Client reports', result)

# ---------- Goals ----------
@api_bp.route('/client/goals', methods=['GET'])
@token_required
def get_goals():
    goals = get_user_goals(request.user.id)
    result = [{
        'id': str(g.id),
        'goal_type': g.goal_type,
        'target_value': float(g.target_value),
        'current_value': float(g.current_value) if g.current_value else None,
        'unit': g.unit,
        'start_date': g.start_date.isoformat(),
        'target_date': g.target_date.isoformat() if g.target_date else None,
        'status': g.status
    } for g in goals]
    return success_response('Goals retrieved', result)

@api_bp.route('/client/goals', methods=['POST'])
@token_required
def set_goal():
    data = request.get_json()
    goal, err = track_goal(request.user.id, data)
    if err:
        return error_response(err, status_code=400)
    return success_response('Goal updated', {'goal_id': str(goal.id)})

@api_bp.route('/client/goals/<uuid:goal_id>/progress', methods=['POST'])
@token_required
def log_goal_progress_route(goal_id):
    data = request.get_json()
    value = data.get('value')
    notes = data.get('notes')
    if value is None:
        return error_response('Value required', status_code=400)
    progress, err = log_goal_progress(goal_id, value, notes)
    if err:
        return error_response(err, status_code=400)
    return success_response('Progress logged', {'progress_id': str(progress.id)})

# ---------- Water & Weight ----------
@api_bp.route('/client/water', methods=['POST'])
@token_required
def track_water_route():
    data = request.get_json()
    amount = data.get('amount_ml')
    if not amount:
        return error_response('Amount required', status_code=400)
    track, err = track_water(request.user.id, amount)
    if err:
        return error_response(err, status_code=400)
    return success_response('Water tracked', {'track_id': str(track.id)})

@api_bp.route('/client/water/history', methods=['GET'])
@token_required
def get_water_history_route():
    days = request.args.get('days', 7, type=int)
    logs = get_water_history(request.user.id, days)
    result = [{
        'id': str(w.id),
        'amount_ml': w.amount_ml,
        'logged_at': w.logged_at.isoformat(),
        'log_date': w.log_date.isoformat()
    } for w in logs]
    return success_response('Water history', result)

@api_bp.route('/client/weight', methods=['POST'])
@token_required
def track_weight_route():
    data = request.get_json()
    weight = data.get('weight_kg')
    if not weight:
        return error_response('Weight required', status_code=400)
    goal = GoalTracker.query.filter_by(user_id=request.user.id, goal_type='weight').first()
    if not goal:
        goal = GoalTracker(
            user_id=request.user.id,
            goal_type='weight',
            target_value=weight,
            current_value=weight,
            unit='kg',
            start_date=datetime.utcnow().date()
        )
        db.session.add(goal)
        db.session.flush()
    else:
        goal.current_value = weight
    progress = GoalProgress(goal_id=goal.id, value=weight)
    db.session.add(progress)
    db.session.commit()
    return success_response('Weight tracked', {'goal_id': str(goal.id)})

# ---------- Admin ----------
@api_bp.route('/admin/pending-professionals', methods=['GET'])
@token_required
@admin_required
def pending_professionals():
    result = get_pending_professionals()
    return success_response('Pending professionals', result)

@api_bp.route('/admin/professionals/<uuid:professional_id>/approve', methods=['PUT'])
@token_required
@admin_required
def approve_professional_route(professional_id):
    ok, err = approve_professional(request.user, professional_id)
    if not ok:
        return error_response(err, status_code=400)
    return success_response('Professional approved')

@api_bp.route('/admin/professionals/<uuid:professional_id>/reject', methods=['PUT'])
@token_required
@admin_required
def reject_professional_route(professional_id):
    ok, err = reject_professional(request.user, professional_id)
    if not ok:
        return error_response(err, status_code=400)
    return success_response('Professional rejected')

@api_bp.route('/admin/professionals/<uuid:professional_id>/suspend', methods=['PUT'])
@token_required
@admin_required
def suspend_professional_route(professional_id):
    ok, err = suspend_professional(request.user, professional_id)
    if not ok:
        return error_response(err, status_code=400)
    return success_response('Professional suspended')

@api_bp.route('/admin/professionals/<uuid:professional_id>/activate', methods=['PUT'])
@token_required
@admin_required
def activate_professional_route(professional_id):
    ok, err = activate_professional(request.user, professional_id)
    if not ok:
        return error_response(err, status_code=400)
    return success_response('Professional activated')

@api_bp.route('/admin/stats', methods=['GET'])
@token_required
@admin_required
def system_stats():
    stats = get_system_stats()
    return success_response('System statistics', stats)

@api_bp.route('/admin/users', methods=['GET'])
@token_required
@admin_required
def admin_get_users():
    users = get_all_users()
    return success_response('Users retrieved', users)

@api_bp.route('/admin/professionals', methods=['GET'])
@token_required
@admin_required
def admin_get_professionals():
    pros = get_all_professionals()
    return success_response('Professionals retrieved', pros)

@api_bp.route('/admin/clients', methods=['GET'])
@token_required
@admin_required
def admin_get_clients():
    clients = get_all_clients()
    return success_response('Clients retrieved', clients)

# ===== NEW ADMIN CRUD ENDPOINTS =====

# ---- Users ----
@api_bp.route('/admin/users/<uuid:user_id>/suspend', methods=['PUT'])
@token_required
@admin_required
def admin_suspend_user(user_id):
    ok, err = suspend_user_by_admin(request.user, user_id)
    if not ok:
        return error_response(err, status_code=400)
    return success_response('User suspended')

@api_bp.route('/admin/users/<uuid:user_id>/activate', methods=['PUT'])
@token_required
@admin_required
def admin_activate_user(user_id):
    ok, err = activate_user_by_admin(request.user, user_id)
    if not ok:
        return error_response(err, status_code=400)
    return success_response('User activated')

@api_bp.route('/admin/users/<uuid:user_id>', methods=['DELETE'])
@token_required
@admin_required
def admin_delete_user(user_id):
    ok, err = delete_user_by_admin(request.user, user_id)
    if not ok:
        return error_response(err, status_code=400)
    return success_response('User deleted')

@api_bp.route('/admin/users/<uuid:user_id>/upgrade', methods=['PUT'])
@token_required
@admin_required
def admin_upgrade_user(user_id):
    ok, err = upgrade_user_by_admin(request.user, user_id)
    if not ok:
        return error_response(err, status_code=400)
    return success_response('User upgraded to Premium')

@api_bp.route('/admin/users/<uuid:user_id>', methods=['PUT'])
@token_required
@admin_required
def admin_update_user(user_id):
    data = request.get_json()
    ok, err = update_user_by_admin(request.user, user_id, data)
    if not ok:
        return error_response(err, status_code=400)
    return success_response('User updated')

@api_bp.route('/admin/users', methods=['POST'])
@token_required
@admin_required
def admin_create_user():
    data = request.get_json()
    user, err = create_user_by_admin(request.user, data)
    if err:
        return error_response(err, status_code=400)
    return success_response('User created', {'user_id': str(user.id)})

# ---- Professionals ----
@api_bp.route('/admin/professionals/<uuid:professional_id>/suspend', methods=['PUT'])
@token_required
@admin_required
def admin_suspend_professional(professional_id):
    ok, err = suspend_professional_by_admin(request.user, professional_id)
    if not ok:
        return error_response(err, status_code=400)
    return success_response('Professional suspended')

@api_bp.route('/admin/professionals/<uuid:professional_id>/activate', methods=['PUT'])
@token_required
@admin_required
def admin_activate_professional(professional_id):
    ok, err = activate_professional_by_admin(request.user, professional_id)
    if not ok:
        return error_response(err, status_code=400)
    return success_response('Professional activated')

@api_bp.route('/admin/professionals/<uuid:professional_id>', methods=['DELETE'])
@token_required
@admin_required
def admin_delete_professional(professional_id):
    ok, err = delete_professional_by_admin(request.user, professional_id)
    if not ok:
        return error_response(err, status_code=400)
    return success_response('Professional deleted')

@api_bp.route('/admin/professionals/<uuid:professional_id>', methods=['PUT'])
@token_required
@admin_required
def admin_update_professional(professional_id):
    data = request.get_json()
    ok, err = update_professional_by_admin(request.user, professional_id, data)
    if not ok:
        return error_response(err, status_code=400)
    return success_response('Professional updated')

@api_bp.route('/admin/professionals', methods=['POST'])
@token_required
@admin_required
def admin_create_professional():
    data = request.get_json()
    user, err = create_professional_by_admin(request.user, data)
    if err:
        return error_response(err, status_code=400)
    return success_response('Professional created', {'user_id': str(user.id)})

# ---- Clients ----
@api_bp.route('/admin/clients/<uuid:client_id>/suspend', methods=['PUT'])
@token_required
@admin_required
def admin_suspend_client(client_id):
    ok, err = suspend_client_by_admin(request.user, client_id)
    if not ok:
        return error_response(err, status_code=400)
    return success_response('Client suspended')

@api_bp.route('/admin/clients/<uuid:client_id>/activate', methods=['PUT'])
@token_required
@admin_required
def admin_activate_client(client_id):
    ok, err = activate_client_by_admin(request.user, client_id)
    if not ok:
        return error_response(err, status_code=400)
    return success_response('Client activated')

@api_bp.route('/admin/clients/<uuid:client_id>', methods=['DELETE'])
@token_required
@admin_required
def admin_delete_client(client_id):
    ok, err = delete_client_by_admin(request.user, client_id)
    if not ok:
        return error_response(err, status_code=400)
    return success_response('Client deleted')

@api_bp.route('/admin/clients/<uuid:client_id>', methods=['PUT'])
@token_required
@admin_required
def admin_update_client(client_id):
    data = request.get_json()
    ok, err = update_client_by_admin(request.user, client_id, data)
    if not ok:
        return error_response(err, status_code=400)
    return success_response('Client updated')

@api_bp.route('/admin/clients', methods=['POST'])
@token_required
@admin_required
def admin_create_client():
    data = request.get_json()
    user, err = create_client_by_admin(request.user, data)
    if err:
        return error_response(err, status_code=400)
    return success_response('Client created', {'user_id': str(user.id)})

# ---------- Foods ----------
@api_bp.route('/foods/search', methods=['GET'])
def search_foods_route():
    query = request.args.get('q', '')
    category = request.args.get('category')
    limit = request.args.get('limit', 20, type=int)
    foods = search_foods(query, category, limit)
    result = [{
        'id': str(f.id),
        'name': f.name,
        'category': f.category.name if f.category else None,
        'serving_size': f.serving_size,
        'calories': float(f.calories) if f.calories else None
    } for f in foods]
    return success_response('Foods found', result)

@api_bp.route('/foods/<uuid:food_id>', methods=['GET'])
def get_food_route(food_id):
    food = get_food_details(food_id)
    if not food:
        return error_response('Food not found', status_code=404)
    return success_response('Food details', {
        'id': str(food.id),
        'name': food.name,
        'category': food.category.name if food.category else None,
        'serving_size': food.serving_size,
        'calories': float(food.calories) if food.calories else None,
        'protein': float(food.protein) if food.protein else None,
        'carbohydrates': float(food.carbohydrates) if food.carbohydrates else None,
        'fat': float(food.fat) if food.fat else None,
        'fiber': float(food.fiber) if food.fiber else None,
        'sugar': float(food.sugar) if food.sugar else None,
        'sodium': float(food.sodium) if food.sodium else None,
        'calcium': float(food.calcium) if food.calcium else None,
        'iron': float(food.iron) if food.iron else None,
        'potassium': float(food.potassium) if food.potassium else None,
        'vitamin_a': float(food.vitamin_a) if food.vitamin_a else None,
        'vitamin_c': float(food.vitamin_c) if food.vitamin_c else None,
        'image_url': food.image_url,
        'source': food.source,
        'country': food.country
    })

# ---------- Recipes ----------
@api_bp.route('/recipes/search', methods=['GET'])
def search_recipes_route():
    query = request.args.get('q', '')
    category = request.args.get('category')
    recipes = search_recipes(query, category)
    result = [{
        'id': str(r.id),
        'title': r.title,
        'description': r.description[:100] if r.description else None,
        'cuisine': r.cuisine,
        'meal_type': r.meal_type.value if r.meal_type else None,
        'difficulty': r.difficulty.value if r.difficulty else None,
        'image_url': r.image_url
    } for r in recipes]
    return success_response('Recipes found', result)

@api_bp.route('/recipes/<uuid:recipe_id>', methods=['GET'])
def get_recipe_route(recipe_id):
    recipe = get_recipe_details(recipe_id)
    if not recipe:
        return error_response('Recipe not found', status_code=404)
    return success_response('Recipe details', recipe)

# ---------- AI Chat ----------
@api_bp.route('/ai/chat', methods=['POST'])
@token_required
def ai_chat():
    data = request.get_json()
    question = data.get('question')
    conversation_id = data.get('conversation_id')
    if not question:
        return error_response('Question required', status_code=400)
    result, err = get_ai_response(request.user, question, conversation_id)
    if err:
        return error_response(err, status_code=400)
    return success_response('AI response', result)

@api_bp.route('/ai/conversations', methods=['GET'])
@token_required
def get_conversations():
    convs = AIConversation.query.filter_by(user_id=request.user.id).order_by(AIConversation.created_at.desc()).all()
    result = [{
        'id': str(c.id),
        'title': c.title,
        'created_at': c.created_at.isoformat(),
        'message_count': len(c.messages)
    } for c in convs]
    return success_response('Conversations', result)

@api_bp.route('/ai/conversations/<uuid:conversation_id>', methods=['GET'])
@token_required
def get_conversation(conversation_id):
    conv = AIConversation.query.filter_by(id=conversation_id, user_id=request.user.id).first()
    if not conv:
        return error_response('Conversation not found', status_code=404)
    messages = [{
        'id': str(m.id),
        'sender': m.sender,
        'content': m.content,
        'created_at': m.created_at.isoformat()
    } for m in conv.messages]
    return success_response('Conversation details', {
        'id': str(conv.id),
        'title': conv.title,
        'messages': messages,
        'created_at': conv.created_at.isoformat()
    })

# ---------- Notifications ----------
@api_bp.route('/notifications', methods=['GET'])
@token_required
def get_notifications():
    unread_only = request.args.get('unread', 'false').lower() == 'true'
    notifs = get_user_notifications(request.user.id, unread_only)
    result = [{
        'id': str(n.id),
        'title': n.title,
        'message': n.message,
        'type': n.type,
        'is_read': n.is_read,
        'action_url': n.action_url,
        'created_at': n.created_at.isoformat()
    } for n in notifs]
    return success_response('Notifications', result)

@api_bp.route('/notifications/<uuid:notification_id>/read', methods=['PUT'])
@token_required
def mark_read(notification_id):
    ok = mark_notification_read(notification_id, request.user.id)
    if not ok:
        return error_response('Notification not found', status_code=404)
    return success_response('Notification marked read')

@api_bp.route('/notifications/preferences', methods=['GET'])
@token_required
def get_notification_prefs():
    prefs = get_user_notification_preferences(request.user.id)
    return success_response('Preferences', {
        'email_notifications': prefs.email_notifications,
        'push_notifications': prefs.push_notifications,
        'sms_notifications': prefs.sms_notifications,
        'preferences': prefs.preferences
    })

@api_bp.route('/notifications/preferences', methods=['PUT'])
@token_required
def update_notification_prefs():
    data = request.get_json()
    update_notification_preferences(request.user.id, data)
    return success_response('Preferences updated')

# ---------- Subscriptions (Memberships) ----------
@api_bp.route('/subscriptions/plans', methods=['GET'])
def get_plans():
    plans = get_subscription_plans()
    result = [{
        'id': str(p.id),
        'name': p.name,
        'description': p.description,
        'price': float(p.price),
        'currency': p.currency,
        'billing_cycle': p.billing_cycle.value,
        'features': p.features,
        'is_active': p.is_active
    } for p in plans]
    return success_response('Subscription plans', result)

@api_bp.route('/subscriptions/subscribe', methods=['POST'])
@token_required
def subscribe():
    data = request.get_json()
    plan_id = data.get('plan_id')
    payment_data = data.get('payment_data')
    if not plan_id:
        return error_response('Plan ID required', status_code=400)
    try:
        plan_uuid = uuid.UUID(plan_id)
    except ValueError:
        return error_response('Invalid plan ID', status_code=400)
    membership, err = subscribe_user(request.user.id, plan_uuid, payment_data)
    if err:
        return error_response(err, status_code=400)
    return success_response('Subscription created', {'subscription_id': str(membership.id)})

@api_bp.route('/subscriptions/current', methods=['GET'])
@token_required
def get_current_subscription():
    sub = UserSubscription.query.filter_by(user_id=request.user.id, status='active').first()
    if not sub:
        return success_response('No active subscription', None)
    return success_response('Active subscription', {
        'id': str(sub.id),
        'plan_name': sub.plan.name,
        'starts_at': sub.starts_at.isoformat(),
        'expires_at': sub.expires_at.isoformat() if sub.expires_at else None,
        'auto_renew': sub.auto_renew,
        'status': sub.status.value
    })

# ---------- Contact / Support ----------
@api_bp.route('/contact', methods=['POST'])
def contact_support():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    subject = data.get('subject')
    message = data.get('message')
    if not all([name, email, subject, message]):
        return error_response('All fields required', status_code=400)
    contact = ContactMessage(
        user_id=request.user.id if hasattr(request, 'user') else None,
        name=name,
        email=email,
        subject=subject,
        message=message
    )
    db.session.add(contact)
    db.session.commit()
    return success_response('Message sent', {'contact_id': str(contact.id)})

# ---------- Audit logs (admin only) ----------
@api_bp.route('/admin/audit-logs', methods=['GET'])
@token_required
@admin_required
def get_audit_logs():
    limit = request.args.get('limit', 50, type=int)
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    result = [{
        'id': str(log.id),
        'user_id': str(log.user_id) if log.user_id else None,
        'action': log.action,
        'entity_type': log.entity_type,
        'entity_id': str(log.entity_id) if log.entity_id else None,
        'changes': log.changes,
        'ip_address': str(log.ip_address) if log.ip_address else None,
        'created_at': log.created_at.isoformat()
    } for log in logs]
    return success_response('Audit logs', result)

# ====================================================================
# NEW – User Weekly Meal Plan (Frontend Meal Planner)
# ====================================================================
@api_bp.route('/meal-plans/current', methods=['GET'])
@token_required
def get_current_weekly_plan():
    """Get the current week's meal plan for the logged-in user."""
    plan = UserWeeklyPlan.query.filter_by(user_id=request.user.id).first()
    if not plan:
        return jsonify({'data': {}}), 200
    return jsonify({'data': plan.week_data}), 200

@api_bp.route('/meal-plans/current', methods=['POST'])
@token_required
def save_current_weekly_plan():
    """Save the current week's meal plan for the logged-in user."""
    data = request.get_json()
    week_data = data.get('data', {})
    if not isinstance(week_data, dict):
        return jsonify({'error': 'Invalid data format'}), 400

    plan = UserWeeklyPlan.query.filter_by(user_id=request.user.id).first()
    if plan:
        plan.week_data = week_data
    else:
        plan = UserWeeklyPlan(user_id=request.user.id, week_data=week_data)
        db.session.add(plan)
    db.session.commit()
    return jsonify({'status': 'ok'}), 200

# ====================================================================
# NEW – Professional Profile
# ====================================================================
@api_bp.route('/professional/profile', methods=['GET'])
@token_required
@professional_required
def get_professional_profile():
    """Get the professional's full profile (including license, etc.)."""
    prof = Professional.query.filter_by(user_id=request.user.id).first()
    if not prof:
        return error_response('Professional profile not found', 404)
    data = {
        'id': str(prof.id),
        'user_id': str(prof.user_id),
        'license_number': prof.license_number,
        'qualification': prof.qualification,
        'years_experience': prof.years_experience,
        'biography': prof.biography,
        'consultation_fee': float(prof.consultation_fee) if prof.consultation_fee else None,
        'availability': prof.availability,
        'approval_status': prof.approval_status,
        'rating': float(prof.rating) if prof.rating else None,
        'total_ratings': prof.total_ratings,
        'is_subscription_active': prof.is_subscription_active,
        'categories': [cat.name for cat in prof.categories]
    }
    return success_response('Professional profile', data)

@api_bp.route('/professional/profile', methods=['PUT'])
@token_required
@professional_required
def update_professional_profile():
    """Update professional's profile fields."""
    data = request.get_json()
    prof = Professional.query.filter_by(user_id=request.user.id).first()
    if not prof:
        return error_response('Professional profile not found', 404)
    allowed = ['license_number', 'qualification', 'years_experience', 'biography',
               'consultation_fee', 'availability']
    for field in allowed:
        if field in data:
            setattr(prof, field, data[field])
    db.session.commit()
    return success_response('Profile updated')

# ====================================================================
# NEW – Client Meal Plans (for professional)
# ====================================================================
@api_bp.route('/professional/clients/<uuid:client_id>/mealplans', methods=['GET'])
@token_required
@professional_required
def get_client_meal_plans_for_professional(client_id):
    """Get all meal plans for a specific client (professional only)."""
    client = Client.query.filter_by(id=client_id).first()
    if not client:
        return error_response('Client not found', 404)
    prof = Professional.query.filter_by(user_id=request.user.id).first()
    if not prof or client.assigned_professional_id != prof.id:
        return error_response('Unauthorized', 403)
    plans = MealPlan.query.filter_by(client_id=client.id).all()
    result = [{
        'id': str(p.id),
        'title': p.title,
        'description': p.description,
        'start_date': p.start_date.isoformat() if p.start_date else None,
        'end_date': p.end_date.isoformat() if p.end_date else None,
        'daily_calories': p.daily_calories,
        'is_ai_generated': p.is_ai_generated,
        'created_at': p.created_at.isoformat()
    } for p in plans]
    return success_response('Client meal plans', result)

# ====================================================================
# NEW – Update Client (for notes, etc.)
# ====================================================================
@api_bp.route('/professional/clients/<uuid:client_id>', methods=['PUT'])
@token_required
@professional_required
def update_client(client_id):
    """Update client details (including notes)."""
    data = request.get_json()
    client = Client.query.filter_by(id=client_id).first()
    if not client:
        return error_response('Client not found', 404)
    prof = Professional.query.filter_by(user_id=request.user.id).first()
    if not prof or client.assigned_professional_id != prof.id:
        return error_response('Unauthorized', 403)
    allowed = ['notes', 'first_name', 'last_name', 'phone', 'gender', 'age', 'weight_kg', 'target_weight', 'bmi', 'medical_conditions', 'allergies', 'medications', 'dietary_restrictions']
    for field in allowed:
        if field in data:
            setattr(client, field, data[field])
    db.session.commit()
    return success_response('Client updated')

# ====================================================================
# NEW – Send Message to Client (email)
# ====================================================================
@api_bp.route('/professional/clients/<uuid:client_id>/send-message', methods=['POST'])
@token_required
@professional_required
def send_client_message_route(client_id):
    """Send an email message to the client."""
    data = request.get_json()
    subject = data.get('subject', 'Message from your professional')
    message = data.get('message')
    if not message:
        return error_response('Message content is required.', 400)
    success, err = send_client_message(request.user, client_id, subject, message)
    if not success:
        return error_response(err, 400)
    return success_response('Message sent successfully.')

# ====================================================================
# NEW – Client Invitation Verification
# ====================================================================
@api_bp.route('/client/verify/<uuid:token>', methods=['GET'])
def verify_invitation(token):
    """Check if the invitation token is valid."""
    client = Client.query.filter_by(invitation_token=str(token)).first()
    if not client:
        return error_response('Invalid invitation link.', 404)
    if client.invitation_expires_at and client.invitation_expires_at < datetime.utcnow():
        return error_response('Invitation link has expired.', 400)
    if client.password_created:
        return error_response('This account already has a password set.', 400)
    return success_response('Token is valid', {'client_id': str(client.id), 'email': client.user.email})

@api_bp.route('/client/verify', methods=['POST'])
def set_password_from_invitation():
    """Set password for the invited client."""
    data = request.get_json()
    token = data.get('token')
    new_password = data.get('password')
    if not token or not new_password:
        return error_response('Token and password required.', 400)
    if len(new_password) < 8:
        return error_response('Password must be at least 8 characters.', 400)
    client = Client.query.filter_by(invitation_token=token).first()
    if not client:
        return error_response('Invalid invitation token.', 404)
    if client.invitation_expires_at and client.invitation_expires_at < datetime.utcnow():
        return error_response('Invitation link has expired.', 400)
    if client.password_created:
        return error_response('Password already set.', 400)
    from werkzeug.security import generate_password_hash
    user = client.user
    user.password_hash = generate_password_hash(new_password)
    client.password_created = True
    client.invitation_token = None
    db.session.commit()
    return success_response('Password set successfully. You can now log in.')

# ====================================================================
# NEW – Settings (Application & Notification Preferences)
# ====================================================================
@api_bp.route('/settings', methods=['GET'])
@token_required
def get_user_settings():
    app_setting = ApplicationSetting.query.filter_by(user_id=request.user.id).first()
    if not app_setting:
        app_setting = ApplicationSetting(user_id=request.user.id)
        db.session.add(app_setting)
        db.session.commit()

    notif_pref = NotificationPreference.query.filter_by(user_id=request.user.id).first()
    if not notif_pref:
        notif_pref = NotificationPreference(user_id=request.user.id)
        db.session.add(notif_pref)
        db.session.commit()

    settings = {
        'language': app_setting.language,
        'theme': app_setting.theme,
        'timezone': app_setting.timezone,
        'currency': app_setting.currency,
        'country': app_setting.country,
        'preferences': app_setting.preferences or {},
        'email_notifications': notif_pref.email_notifications,
        'push_notifications': notif_pref.push_notifications,
        'sms_notifications': notif_pref.sms_notifications,
        'notification_preferences': notif_pref.preferences or {},
        'compact_view': app_setting.preferences.get('compact_view', False),
        'client_messages': app_setting.preferences.get('client_messages', True),
        'appointment_reminders': app_setting.preferences.get('appointment_reminders', True),
        'two_factor_auth': app_setting.preferences.get('two_factor_auth', False),
        'working_days': app_setting.preferences.get('working_days', 'Mon - Fri'),
        'working_hours': app_setting.preferences.get('working_hours', '8:00 AM - 6:00 PM'),
        'profile_visibility': app_setting.preferences.get('profile_visibility', 'Public'),
    }
    return success_response('Settings retrieved', settings)

@api_bp.route('/settings', methods=['PUT'])
@token_required
def update_user_settings():
    data = request.get_json()
    if not data:
        return error_response('No data provided', 400)

    app_setting = ApplicationSetting.query.filter_by(user_id=request.user.id).first()
    if not app_setting:
        app_setting = ApplicationSetting(user_id=request.user.id)
        db.session.add(app_setting)

    notif_pref = NotificationPreference.query.filter_by(user_id=request.user.id).first()
    if not notif_pref:
        notif_pref = NotificationPreference(user_id=request.user.id)
        db.session.add(notif_pref)

    if 'language' in data:
        app_setting.language = data['language']
    if 'theme' in data:
        app_setting.theme = data['theme']
    if 'timezone' in data:
        app_setting.timezone = data['timezone']
    if 'currency' in data:
        app_setting.currency = data['currency']
    if 'country' in data:
        app_setting.country = data['country']

    if 'email_notifications' in data:
        notif_pref.email_notifications = data['email_notifications']
    if 'push_notifications' in data:
        notif_pref.push_notifications = data['push_notifications']
    if 'sms_notifications' in data:
        notif_pref.sms_notifications = data['sms_notifications']

    custom_keys = ['compact_view', 'client_messages', 'appointment_reminders', 'two_factor_auth',
                   'working_days', 'working_hours', 'profile_visibility']
    if not app_setting.preferences:
        app_setting.preferences = {}
    for key in custom_keys:
        if key in data:
            app_setting.preferences[key] = data[key]

    db.session.commit()
    return success_response('Settings updated')

# ====================================================================
# NEW – Professional Appointments (null-safe)
# ====================================================================
@api_bp.route('/professional/appointments', methods=['GET'])
@token_required
@professional_required
def get_professional_appointments():
    """Get all appointments for the logged-in professional (null-safe)."""
    prof = Professional.query.filter_by(user_id=request.user.id).first()
    if not prof:
        return error_response('Professional not found', 404)

    appointments = Appointment.query.filter_by(professional_id=prof.id).order_by(Appointment.appointment_date.desc()).all()
    result = []
    for a in appointments:
        client_name = ''
        if a.client_id:
            client = Client.query.get(a.client_id)
            if client and client.user:
                profile = client.user.profile
                if profile and profile.first_name:
                    client_name = f"{profile.first_name} {profile.last_name or ''}".strip()
                else:
                    client_name = client.user.email or 'Unknown'
        result.append({
            'id': str(a.id),
            'client_id': str(a.client_id) if a.client_id else None,
            'client_name': client_name,
            'title': a.title,
            'description': a.description,
            'appointment_date': a.appointment_date.isoformat() if a.appointment_date else None,
            'appointment_time': a.appointment_time.strftime('%H:%M') if a.appointment_time else None,
            'duration_minutes': a.duration_minutes,
            'type': a.type,
            'status': a.status,
            'notes': a.notes,
            'created_at': a.created_at.isoformat() if a.created_at else None
        })
    return success_response('Appointments retrieved', result)


@api_bp.route('/professional/appointments', methods=['POST'])
@token_required
@professional_required
def create_professional_appointment():
    """Schedule a new appointment (null-safe)."""
    data = request.get_json()
    if not data:
        return error_response('No data provided', 400)

    client_id = data.get('client_id')
    title = data.get('title')
    appointment_date = data.get('appointment_date')
    appointment_time = data.get('appointment_time')

    if not all([client_id, title, appointment_date, appointment_time]):
        return error_response('client_id, title, date, and time are required', 400)

    prof = Professional.query.filter_by(user_id=request.user.id).first()
    if not prof:
        return error_response('Professional not found', 404)

    client = Client.query.filter_by(id=client_id, assigned_professional_id=prof.id).first()
    if not client:
        return error_response('Client not found or not under your care', 404)

    try:
        appt = Appointment(
            client_id=client.id,
            professional_id=prof.id,
            title=title,
            description=data.get('description', ''),
            appointment_date=datetime.strptime(appointment_date, '%Y-%m-%d').date(),
            appointment_time=datetime.strptime(appointment_time, '%H:%M').time(),
            duration_minutes=data.get('duration_minutes', 30),
            type=data.get('type', 'Virtual'),
            status=data.get('status', 'Scheduled'),
            notes=data.get('notes', '')
        )
        db.session.add(appt)
        db.session.commit()
        return success_response('Appointment scheduled', {'appointment_id': str(appt.id)})
    except Exception as e:
        db.session.rollback()
        return error_response(f'Database error: {str(e)}', 500)


@api_bp.route('/professional/appointments/<uuid:appointment_id>', methods=['PUT'])
@token_required
@professional_required
def update_appointment(appointment_id):
    data = request.get_json()
    prof = Professional.query.filter_by(user_id=request.user.id).first()
    if not prof:
        return error_response('Professional not found', 404)
    appointment = Appointment.query.filter_by(id=appointment_id, professional_id=prof.id).first()
    if not appointment:
        return error_response('Appointment not found', 404)
    allowed = ['title', 'description', 'appointment_date', 'appointment_time', 'duration_minutes', 'type', 'status', 'notes']
    for field in allowed:
        if field in data:
            if field == 'appointment_date':
                setattr(appointment, field, datetime.strptime(data[field], '%Y-%m-%d').date())
            elif field == 'appointment_time':
                setattr(appointment, field, datetime.strptime(data[field], '%H:%M').time())
            else:
                setattr(appointment, field, data[field])
    db.session.commit()
    return success_response('Appointment updated')

@api_bp.route('/professional/appointments/<uuid:appointment_id>', methods=['DELETE'])
@token_required
@professional_required
def delete_appointment(appointment_id):
    prof = Professional.query.filter_by(user_id=request.user.id).first()
    if not prof:
        return error_response('Professional not found', 404)
    appointment = Appointment.query.filter_by(id=appointment_id, professional_id=prof.id).first()
    if not appointment:
        return error_response('Appointment not found', 404)
    db.session.delete(appointment)
    db.session.commit()
    return success_response('Appointment deleted')

# ====================================================================
# NEW – Professional Reports (null-safe)
# ====================================================================
@api_bp.route('/professional/reports', methods=['GET'])
@token_required
@professional_required
def get_professional_reports():
    """Get all reports generated by the logged-in professional (null-safe)."""
    prof = Professional.query.filter_by(user_id=request.user.id).first()
    if not prof:
        return error_response('Professional not found', 404)

    reports = Report.query.filter_by(professional_id=prof.id).order_by(Report.generated_at.desc()).all()
    result = []
    for r in reports:
        client_name = ''
        if r.client_id:
            client = Client.query.get(r.client_id)
            if client and client.user:
                profile = client.user.profile
                if profile and profile.first_name:
                    client_name = f"{profile.first_name} {profile.last_name or ''}".strip()
                else:
                    client_name = client.user.email or 'Unknown'
        result.append({
            'id': str(r.id),
            'client_id': str(r.client_id) if r.client_id else None,
            'client_name': client_name,
            'title': r.title,
            'report_type': r.report_type,
            'content': r.content or {},
            'file_url': r.file_url,
            'generated_at': r.generated_at.isoformat() if r.generated_at else None,
            'created_at': r.created_at.isoformat() if r.created_at else None
        })
    return success_response('Reports retrieved', result)


@api_bp.route('/professional/reports', methods=['POST'])
@token_required
@professional_required
def create_professional_report():
    """Generate a new report for a client (null-safe)."""
    data = request.get_json()
    if not data:
        return error_response('No data provided', 400)

    client_id = data.get('client_id')
    title = data.get('title')
    report_type = data.get('report_type')

    if not all([client_id, title, report_type]):
        return error_response('client_id, title, and report_type are required', 400)

    prof = Professional.query.filter_by(user_id=request.user.id).first()
    if not prof:
        return error_response('Professional not found', 404)

    client = Client.query.filter_by(id=client_id, assigned_professional_id=prof.id).first()
    if not client:
        return error_response('Client not found or not under your care', 404)

    try:
        report = Report(
            user_id=prof.user_id,
            client_id=client.id,
            professional_id=prof.id,
            title=title,
            report_type=report_type,
            content=data.get('content', {}),
            file_url=data.get('file_url', '')
        )
        db.session.add(report)
        db.session.commit()
        return success_response('Report generated', {'report_id': str(report.id)})
    except Exception as e:
        db.session.rollback()
        return error_response(f'Database error: {str(e)}', 500)


@api_bp.route('/professional/reports/<uuid:report_id>', methods=['GET'])
@token_required
@professional_required
def get_report(report_id):
    prof = Professional.query.filter_by(user_id=request.user.id).first()
    if not prof:
        return error_response('Professional not found', 404)
    report = Report.query.filter_by(id=report_id, professional_id=prof.id).first()
    if not report:
        return error_response('Report not found', 404)
    # Get client name safely
    client_name = ''
    if report.client_id:
        client = Client.query.get(report.client_id)
        if client and client.user:
            profile = client.user.profile
            if profile and profile.first_name:
                client_name = f"{profile.first_name} {profile.last_name or ''}".strip()
            else:
                client_name = client.user.email or 'Unknown'
    return success_response('Report details', {
        'id': str(report.id),
        'client_id': str(report.client_id) if report.client_id else None,
        'client_name': client_name,
        'title': report.title,
        'report_type': report.report_type,
        'content': report.content or {},
        'file_url': report.file_url,
        'generated_at': report.generated_at.isoformat() if report.generated_at else None,
        'created_at': report.created_at.isoformat() if report.created_at else None
    })

@api_bp.route('/professional/reports/<uuid:report_id>', methods=['DELETE'])
@token_required
@professional_required
def delete_report(report_id):
    prof = Professional.query.filter_by(user_id=request.user.id).first()
    if not prof:
        return error_response('Professional not found', 404)
    report = Report.query.filter_by(id=report_id, professional_id=prof.id).first()
    if not report:
        return error_response('Report not found', 404)
    db.session.delete(report)
    db.session.commit()
    return success_response('Report deleted')

# ====================================================================
# BILLING – Mock Subscription & Webhook (No Registration Needed)
# ====================================================================

@api_bp.route('/billing/mock-subscribe', methods=['POST'])
@token_required
def mock_subscribe():
    """
    Mock subscription endpoint – no real payment.
    Activates a subscription for the user and creates a mock payment record.
    """
    import uuid
    from datetime import datetime, timedelta
    from models import SubscriptionPlan, UserSubscription, Payment

    data = request.get_json()
    plan_id = data.get('plan_id')
    
    if not plan_id:
        return error_response('Plan ID required', 400)
    
    # Try to find the plan – handle both UUID and string IDs
    plan = None
    
    # First, try to parse as UUID and query
    try:
        plan_uuid = uuid.UUID(plan_id)
        plan = SubscriptionPlan.query.get(plan_uuid)
    except (ValueError, TypeError):
        # Not a valid UUID – treat as a name or skip
        pass
    
    # If not found by UUID, try to find by name
    if not plan:
        plan = SubscriptionPlan.query.filter_by(name=plan_id).first()
    
    # If still not found, get the first active plan
    if not plan:
        plan = SubscriptionPlan.query.filter_by(is_active=True).first()
    
    # If still no plan, create a default one (for testing)
    if not plan:
        try:
            plan = SubscriptionPlan(
                id=uuid.uuid4(),
                name='Premium',
                description='Default premium plan for testing',
                price=2500,
                currency='KES',
                billing_cycle='monthly',
                features={'unlimited_ai': True},
                is_active=True
            )
            db.session.add(plan)
            db.session.commit()
            current_app.logger.info(f"Auto-created plan {plan.id} for mock subscribe.")
        except Exception as e:
            current_app.logger.error(f"Failed to create default plan: {e}")
            return error_response('Payment system not configured. Please contact support.', 500)
    
    # Deactivate any existing active subscription
    existing = UserSubscription.query.filter_by(
        user_id=request.user.id,
        status='active'
    ).first()
    if existing:
        existing.status = 'canceled'
    
    # Create new subscription
    subscription = UserSubscription(
        user_id=request.user.id,
        plan_id=plan.id,
        status='active',
        starts_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=30),
        auto_renew=True
    )
    db.session.add(subscription)
    db.session.flush()
    
    # Create a mock payment record
    payment = Payment(
        user_id=request.user.id,
        subscription_id=subscription.id,
        amount=plan.price,
        currency=plan.currency or 'KES',
        method='mock',
        status='completed',
        transaction_reference=f'mock_{uuid.uuid4().hex[:8]}',
        payment_date=datetime.utcnow()
    )
    db.session.add(payment)
    db.session.commit()
    
    return success_response('Subscription activated (mock)', {
        'subscription_id': str(subscription.id),
        'plan': plan.name,
        'expires_at': subscription.expires_at.isoformat()
    })

@api_bp.route('/billing/webhook', methods=['POST'])
def billing_webhook():
    """
    Generic webhook endpoint to receive payment gateway notifications.
    For mock mode, just acknowledge.
    In production, you'd verify the signature and update subscription status.
    """
    payload = request.get_data(as_text=True)
    current_app.logger.info(f"Webhook received: {payload[:200]}...")
    return jsonify({'status': 'success'}), 200

# ====================================================================
# Legacy /professional/mealplans GET (kept for backward compatibility)
# ====================================================================
@api_bp.route('/professional/mealplans', methods=['GET'])
@token_required
@professional_required
def get_professional_meal_plans_route():
    """Get all meal plans (programs) created by the professional (legacy, no hyphen)."""
    plans = get_professional_meal_plans(request.user)
    return success_response('Meal plans retrieved', plans)