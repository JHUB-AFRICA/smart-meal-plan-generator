import uuid
from datetime import datetime
from enum import Enum

from extensions import db
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET, ARRAY
from sqlalchemy import (
    Column, String, Boolean, DateTime, Integer, Numeric, Date, Time,
    Text, ForeignKey, CheckConstraint, UniqueConstraint,
    func, Index
)


# ---------- Enums ----------
class UserRole(Enum):
    USER = 'user'
    PROFESSIONAL = 'professional'
    CLIENT = 'client'
    ADMIN = 'admin'

class AccountStatus(Enum):
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    SUSPENDED = 'suspended'
    PENDING_VERIFICATION = 'pending_verification'

class Gender(Enum):
    MALE = 'male'
    FEMALE = 'female'
    OTHER = 'other'
    PREFER_NOT_TO_SAY = 'prefer_not_to_say'

class Lifestyle(Enum):
    SEDENTARY = 'sedentary'
    LIGHTLY_ACTIVE = 'lightly_active'
    MODERATELY_ACTIVE = 'moderately_active'
    VERY_ACTIVE = 'very_active'
    EXTRA_ACTIVE = 'extra_active'

class DietPreference(Enum):
    OMNIVORE = 'omnivore'
    VEGETARIAN = 'vegetarian'
    VEGAN = 'vegan'
    PESCATARIAN = 'pescatarian'
    KETO = 'keto'
    PALEO = 'paleo'
    GLUTEN_FREE = 'gluten_free'
    DAIRY_FREE = 'dairy_free'
    LOW_CARB = 'low_carb'
    OTHER = 'other'

class ProfessionalApprovalStatus(Enum):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'

class SubscriptionStatus(Enum):
    ACTIVE = 'active'
    EXPIRED = 'expired'
    CANCELED = 'canceled'
    PENDING = 'pending'

class PaymentStatus(Enum):
    PENDING = 'pending'
    COMPLETED = 'completed'
    FAILED = 'failed'
    REFUNDED = 'refunded'

class BillingCycle(Enum):
    MONTHLY = 'monthly'
    QUARTERLY = 'quarterly'
    YEARLY = 'yearly'

class MealType(Enum):
    BREAKFAST = 'breakfast'
    LUNCH = 'lunch'
    DINNER = 'dinner'
    SNACK = 'snack'

class DifficultyLevel(Enum):
    EASY = 'easy'
    MEDIUM = 'medium'
    HARD = 'hard'


# ---------- Association Tables ----------
professional_category_assignment = db.Table(
    'professional_category_assignments',
    Column('professional_id', UUID(as_uuid=True), ForeignKey('professionals.id'), primary_key=True),
    Column('category_id', UUID(as_uuid=True), ForeignKey('professional_categories.id'), primary_key=True)
)

user_health_condition = db.Table(
    'user_health_conditions',
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True),
    Column('condition_id', UUID(as_uuid=True), ForeignKey('health_conditions.id'), primary_key=True),
    Column('diagnosed_date', Date),
    Column('notes', Text)
)

user_food_restriction = db.Table(
    'user_food_restrictions',
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True),
    Column('restriction_id', UUID(as_uuid=True), ForeignKey('food_restrictions.id'), primary_key=True),
    Column('notes', Text)
)


# ---------- Models ----------
class User(db.Model):
    __tablename__ = 'users'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(Text, nullable=False)

    role = Column(String(50), nullable=False, default='user')
    status = Column(String(50), nullable=False, default='pending_verification')

    is_verified = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    last_login_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())

    # Relationships
    profile = db.relationship('UserProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    professional = db.relationship('Professional', backref='user', uselist=False, cascade='all, delete-orphan')
    client = db.relationship('Client', backref='user', uselist=False, cascade='all, delete-orphan')
    admin = db.relationship('Admin', backref='user', uselist=False, cascade='all, delete-orphan')
    password_reset_tokens = db.relationship('PasswordResetToken', backref='user', lazy=True)
    email_verification_tokens = db.relationship('EmailVerificationToken', backref='user', lazy=True)
    refresh_tokens = db.relationship('RefreshToken', backref='user', lazy=True)
    sessions = db.relationship('Session', backref='user', lazy=True)
    login_history = db.relationship('LoginHistory', backref='user', lazy=True)
    user_subscriptions = db.relationship('UserSubscription', backref='user', lazy=True)
    payments = db.relationship('Payment', backref='user', lazy=True)
    invoices = db.relationship('Invoice', backref='user', lazy=True)
    recipes_created = db.relationship('Recipe', foreign_keys='Recipe.created_by_user_id', backref='creator')
    meal_plans_created = db.relationship('MealPlan', foreign_keys='MealPlan.created_by_user_id', backref='creator')
    water_logs = db.relationship('WaterLog', backref='user', lazy=True)
    goals = db.relationship('GoalTracker', backref='user', lazy=True)
    health_conditions = db.relationship('HealthCondition', secondary=user_health_condition, lazy='subquery', backref=db.backref('users', lazy=True))
    food_restrictions = db.relationship('FoodRestriction', secondary=user_food_restriction, lazy='subquery', backref=db.backref('users', lazy=True))
    nutriscan_entries = db.relationship('Nutriscan', backref='user', lazy=True)
    ai_conversations = db.relationship('AIConversation', backref='user', lazy=True)
    ai_recommendations = db.relationship('AIRecommendation', backref='user', lazy=True)
    reports = db.relationship('Report', backref='user', lazy=True)   # creates Report.user
    notifications = db.relationship('Notification', backref='user', lazy=True)
    notification_preference = db.relationship('NotificationPreference', backref='user', uselist=False, cascade='all, delete-orphan')
    contact_messages = db.relationship('ContactMessage', backref='user', lazy=True)
    app_settings = db.relationship('ApplicationSetting', backref='user', uselist=False, cascade='all, delete-orphan')
    files = db.relationship('File', backref='user', lazy=True)
    audit_logs = db.relationship('AuditLog', backref='user', lazy=True)
    activity_logs = db.relationship('ActivityLog', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.email}>'


class UserProfile(db.Model):
    __tablename__ = 'user_profiles'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, unique=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    phone = Column(String(20))
    date_of_birth = Column(Date)
    gender = Column(String(20))
    height_cm = Column(Numeric(5, 2))
    weight_kg = Column(Numeric(5, 2))
    bmi = Column(Numeric(4, 2))
    lifestyle = Column(String(50))
    diet_preference = Column(String(50))
    activity_level = Column(Numeric(3, 1))
    water_goal_ml = Column(Integer)
    calorie_goal = Column(Integer)
    allergies = Column(ARRAY(Text))
    medical_conditions = Column(ARRAY(Text))
    favorite_foods = Column(ARRAY(Text))
    disliked_foods = Column(ARRAY(Text))
    profile_picture_url = Column(Text)
    bio = Column(Text)
    settings = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    __table_args__ = (CheckConstraint('bmi >= 0 AND bmi <= 100', name='bmi_range'),)


class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    token = Column(String(255), nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    __table_args__ = (CheckConstraint('expires_at > created_at', name='expires_after_creation'),)


class EmailVerificationToken(db.Model):
    __tablename__ = 'email_verification_tokens'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    token = Column(String(255), nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())


class RefreshToken(db.Model):
    __tablename__ = 'refresh_tokens'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    token = Column(String(255), nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())


class Session(db.Model):
    __tablename__ = 'sessions'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    session_token = Column(String(255), nullable=False, unique=True)
    user_agent = Column(Text)
    ip_address = Column(INET)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())


class LoginHistory(db.Model):
    __tablename__ = 'login_history'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    login_time = Column(DateTime(timezone=True), nullable=False, default=func.now())
    ip_address = Column(INET)
    user_agent = Column(Text)
    success = Column(Boolean, nullable=False, default=True)


class ProfessionalCategory(db.Model):
    __tablename__ = 'professional_categories'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    professionals = db.relationship('Professional', secondary=professional_category_assignment, backref=db.backref('categories', lazy=True))


class Professional(db.Model):
    __tablename__ = 'professionals'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, unique=True)
    license_number = Column(String(100), unique=True)
    qualification = Column(Text)
    years_experience = Column(Integer)
    biography = Column(Text)
    consultation_fee = Column(Numeric(10, 2))
    availability = Column(JSONB)
    approval_status = Column(String(50), nullable=False, default='pending')
    rating = Column(Numeric(3, 2))
    total_ratings = Column(Integer, default=0)
    is_subscription_active = Column(Boolean, default=False)
    subscription_plan_id = Column(UUID(as_uuid=True), ForeignKey('subscription_plans.id'))
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())

    # Relationships – backrefs create Professional.appointments, Professional.reports
    appointments = db.relationship('Appointment', backref='professional', lazy=True)
    reports = db.relationship('Report', backref='professional', lazy=True)
    clients = db.relationship('Client', backref='professional', lazy=True)
    meal_plans = db.relationship('MealPlan', backref='professional', lazy=True)

    __table_args__ = (
        CheckConstraint('years_experience >= 0', name='non_negative_experience'),
        CheckConstraint('consultation_fee >= 0', name='non_negative_fee'),
        CheckConstraint('rating >= 0 AND rating <= 5', name='rating_range'),
    )


class Client(db.Model):
    __tablename__ = 'clients'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, unique=True)
    assigned_professional_id = Column(UUID(as_uuid=True), ForeignKey('professionals.id'))
    invitation_token = Column(UUID(as_uuid=True), unique=True)
    invitation_expires_at = Column(DateTime(timezone=True))
    password_created = Column(Boolean, default=False)
    medical_history = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())

    # Relationships – backrefs create Client.appointments, Client.reports
    appointments = db.relationship('Appointment', backref='client', lazy=True)
    reports = db.relationship('Report', backref='client', lazy=True)
    meal_plans = db.relationship('MealPlan', backref='client', lazy=True)
    shopping_lists = db.relationship('ShoppingList', backref='client', lazy=True)


class Admin(db.Model):
    __tablename__ = 'admins'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, unique=True)
    permissions = Column(JSONB, default=[])
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())


class SubscriptionPlan(db.Model):
    __tablename__ = 'subscription_plans'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), nullable=False, unique=True)
    description = Column(Text)
    price = Column(Numeric(10, 2), nullable=False, default=0)
    currency = Column(String(3), nullable=False, default='USD')
    billing_cycle = Column(String(20), nullable=False, default='monthly')
    features = Column(JSONB)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    professional_subscriptions = db.relationship('Professional', backref='subscription_plan', lazy=True)
    user_subscriptions = db.relationship('UserSubscription', backref='plan', lazy=True)


class UserSubscription(db.Model):
    __tablename__ = 'user_subscriptions'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    plan_id = Column(UUID(as_uuid=True), ForeignKey('subscription_plans.id'), nullable=False)
    status = Column(String(20), nullable=False, default='pending')
    starts_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True))
    auto_renew = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    payments = db.relationship('Payment', backref='subscription', lazy=True)
    __table_args__ = (CheckConstraint('expires_at > starts_at', name='expires_after_starts'),)


class Payment(db.Model):
    __tablename__ = 'payments'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey('user_subscriptions.id'))
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default='USD')
    method = Column(String(50))
    status = Column(String(20), nullable=False, default='pending')
    transaction_reference = Column(String(255), unique=True)
    invoice_number = Column(String(100), unique=True)
    payment_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    invoice = db.relationship('Invoice', backref='payment', uselist=False, cascade='all, delete-orphan')


class Invoice(db.Model):
    __tablename__ = 'invoices'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id = Column(UUID(as_uuid=True), ForeignKey('payments.id'))
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    invoice_number = Column(String(100), nullable=False, unique=True)
    issued_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    due_at = Column(DateTime(timezone=True))
    total = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default='USD')
    pdf_url = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())


class FoodCategory(db.Model):
    __tablename__ = 'food_categories'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    foods = db.relationship('Food', backref='category', lazy=True)


class Food(db.Model):
    __tablename__ = 'foods'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey('food_categories.id'))
    serving_size = Column(String(100))
    calories = Column(Numeric(8, 2))
    protein = Column(Numeric(8, 2))
    fat = Column(Numeric(8, 2))
    carbohydrates = Column(Numeric(8, 2))
    fiber = Column(Numeric(8, 2))
    sugar = Column(Numeric(8, 2))
    sodium = Column(Numeric(8, 2))
    calcium = Column(Numeric(8, 2))
    iron = Column(Numeric(8, 2))
    potassium = Column(Numeric(8, 2))
    vitamin_a = Column(Numeric(8, 2))
    vitamin_c = Column(Numeric(8, 2))
    source = Column(Text)
    source_id = Column(String(100))
    country = Column(String(100))
    image_url = Column(Text)
    search_keywords = Column(ARRAY(Text))
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())

    recipe_ingredients = db.relationship('RecipeIngredient', backref='food', lazy=True)
    shopping_items = db.relationship('ShoppingItem', backref='food', lazy=True)

    __table_args__ = (
        Index('idx_foods_source_source_id', source, source_id),
    )


class Recipe(db.Model):
    __tablename__ = 'recipes'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    cuisine = Column(String(100))
    meal_type = Column(String(20))
    difficulty = Column(String(20))
    prep_time_minutes = Column(Integer)
    cook_time_minutes = Column(Integer)
    total_time_minutes = Column(Integer)
    servings = Column(Integer)
    image_url = Column(Text)
    nutrition_summary = Column(JSONB)
    is_public = Column(Boolean, default=True)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    ingredients = db.relationship('RecipeIngredient', backref='recipe', lazy=True, cascade='all, delete-orphan')
    steps = db.relationship('RecipeStep', backref='recipe', lazy=True, cascade='all, delete-orphan')
    meals = db.relationship('Meal', backref='recipe', lazy=True)


class RecipeIngredient(db.Model):
    __tablename__ = 'recipe_ingredients'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey('recipes.id'), nullable=False)
    food_id = Column(UUID(as_uuid=True), ForeignKey('foods.id'))
    ingredient_name = Column(String(255), nullable=False)
    quantity = Column(Numeric(8, 2))
    unit = Column(String(50))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())


class RecipeStep(db.Model):
    __tablename__ = 'recipe_steps'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey('recipes.id'), nullable=False)
    step_number = Column(Integer, nullable=False)
    instruction = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    __table_args__ = (UniqueConstraint('recipe_id', 'step_number', name='idx_recipe_steps_unique_step'),)


class MealPlan(db.Model):
    __tablename__ = 'meal_plans'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id'))
    professional_id = Column(UUID(as_uuid=True), ForeignKey('professionals.id'))
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    is_ai_generated = Column(Boolean, default=False)
    start_date = Column(Date)
    end_date = Column(Date)
    daily_calories = Column(Integer)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    meals = db.relationship('Meal', backref='meal_plan', lazy=True, cascade='all, delete-orphan')
    shopping_lists = db.relationship('ShoppingList', backref='meal_plan', lazy=True)


class Meal(db.Model):
    __tablename__ = 'meals'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meal_plan_id = Column(UUID(as_uuid=True), ForeignKey('meal_plans.id'), nullable=False)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey('recipes.id'))
    meal_type = Column(String(20), nullable=False)
    scheduled_date = Column(Date, nullable=False)
    scheduled_time = Column(Time)
    custom_name = Column(String(255))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())


class ShoppingList(db.Model):
    __tablename__ = 'shopping_lists'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id'))
    meal_plan_id = Column(UUID(as_uuid=True), ForeignKey('meal_plans.id'))
    title = Column(String(255), nullable=False)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    items = db.relationship('ShoppingItem', backref='shopping_list', lazy=True, cascade='all, delete-orphan')


class ShoppingItem(db.Model):
    __tablename__ = 'shopping_items'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shopping_list_id = Column(UUID(as_uuid=True), ForeignKey('shopping_lists.id'), nullable=False)
    food_id = Column(UUID(as_uuid=True), ForeignKey('foods.id'))
    item_name = Column(String(255), nullable=False)
    quantity = Column(Numeric(8, 2))
    unit = Column(String(50))
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())


class WaterLog(db.Model):
    __tablename__ = 'water_logs'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    log_date = Column(Date, nullable=False, default=func.current_date())
    amount_ml = Column(Integer, nullable=False)
    logged_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    __table_args__ = (CheckConstraint('amount_ml > 0', name='positive_amount'),)


class GoalTracker(db.Model):
    __tablename__ = 'goal_tracker'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    goal_type = Column(String(50), nullable=False)
    target_value = Column(Numeric(10, 2), nullable=False)
    current_value = Column(Numeric(10, 2))
    unit = Column(String(20))
    start_date = Column(Date, nullable=False)
    target_date = Column(Date)
    status = Column(String(20), default='active')
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    progress_entries = db.relationship('GoalProgress', backref='goal', lazy=True, cascade='all, delete-orphan')


class GoalProgress(db.Model):
    __tablename__ = 'goal_progress'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    goal_id = Column(UUID(as_uuid=True), ForeignKey('goal_tracker.id'), nullable=False)
    progress_date = Column(Date, nullable=False, default=func.current_date())
    value = Column(Numeric(10, 2), nullable=False)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())


class HealthCondition(db.Model):
    __tablename__ = 'health_conditions'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text)
    icd_code = Column(String(20))
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    recommendations = db.relationship('ConditionRecommendation', backref='condition', lazy=True, cascade='all, delete-orphan')


class ConditionRecommendation(db.Model):
    __tablename__ = 'condition_recommendations'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    condition_id = Column(UUID(as_uuid=True), ForeignKey('health_conditions.id'), nullable=False)
    recommendation = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())


class FoodRestriction(db.Model):
    __tablename__ = 'food_restrictions'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())


class Nutriscan(db.Model):
    __tablename__ = 'nutriscan'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    barcode = Column(String(100), unique=True)
    food_name = Column(String(255), nullable=False)
    brand = Column(String(255))
    nutrition_facts = Column(JSONB)
    ingredients = Column(Text)
    image_url = Column(Text)
    ai_analysis = Column(Text)
    scan_date = Column(DateTime(timezone=True), nullable=False, default=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())


class AIConversation(db.Model):
    __tablename__ = 'ai_conversations'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    title = Column(String(255))
    context = Column(JSONB)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    messages = db.relationship('AIMessage', backref='conversation', lazy=True, cascade='all, delete-orphan')


class AIMessage(db.Model):
    __tablename__ = 'ai_messages'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey('ai_conversations.id'), nullable=False)
    sender = Column(String(10), nullable=False)
    content = Column(Text, nullable=False)
    prompt = Column(Text)
    response = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    __table_args__ = (CheckConstraint("sender IN ('user', 'ai')", name='valid_sender'),)


class AIRecommendation(db.Model):
    __tablename__ = 'ai_recommendations'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    recommendation_type = Column(String(50), nullable=False)
    content = Column(JSONB, nullable=False)
    generated_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    is_accepted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())


class Report(db.Model):
    __tablename__ = 'reports'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)          # who generated it
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id'), nullable=False)
    professional_id = Column(UUID(as_uuid=True), ForeignKey('professionals.id'), nullable=False)
    title = Column(String(255), nullable=False)
    report_type = Column(String(50), nullable=False)   # Nutrition, Compliance, Progress, Monthly
    content = Column(JSONB, default={})
    file_url = Column(Text)
    generated_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())

    # No relationships – backrefs from User, Client, Professional provide .user, .client, .professional

    def __repr__(self):
        return f'<Report {self.title}>'


class Notification(db.Model):
    __tablename__ = 'notifications'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    action_url = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())


class NotificationTemplate(db.Model):
    __tablename__ = 'notification_templates'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), nullable=False, unique=True)
    subject = Column(String(255))
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())


class NotificationPreference(db.Model):
    __tablename__ = 'notification_preferences'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, unique=True)
    email_notifications = Column(Boolean, default=True)
    push_notifications = Column(Boolean, default=True)
    sms_notifications = Column(Boolean, default=False)
    preferences = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())


class ContactMessage(db.Model):
    __tablename__ = 'contact_messages'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(20), default='pending')
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())


class SystemSetting(db.Model):
    __tablename__ = 'system_settings'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(100), nullable=False, unique=True)
    value = Column(JSONB, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())


class ApplicationSetting(db.Model):
    __tablename__ = 'application_settings'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, unique=True)
    language = Column(String(10), default='en')
    theme = Column(String(20), default='light')
    timezone = Column(String(50), default='UTC')
    currency = Column(String(3), default='USD')
    country = Column(String(100))
    preferences = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())


class Language(db.Model):
    __tablename__ = 'languages'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(10), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())


class Theme(db.Model):
    __tablename__ = 'themes'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), nullable=False, unique=True)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())


class File(db.Model):
    __tablename__ = 'files'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    file_name = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    file_size = Column(db.BigInteger)
    mime_type = Column(String(100))
    file_type = Column(String(50))
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    action = Column(String(100), nullable=False)
    entity_type = Column(String(100))
    entity_id = Column(UUID(as_uuid=True))
    changes = Column(JSONB)
    ip_address = Column(INET)
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())


class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    activity_type = Column(String(100), nullable=False)
    details = Column(JSONB)
    ip_address = Column(INET)
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())


# ---------- User Weekly Meal Plan ----------
class UserWeeklyPlan(db.Model):
    __tablename__ = 'user_weekly_plans'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, unique=True)
    week_data = Column(JSONB, nullable=False, default={})
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f'<UserWeeklyPlan user_id={self.user_id}>'


# ---------- Appointment ----------
class Appointment(db.Model):
    __tablename__ = 'appointments'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id'), nullable=False)
    professional_id = Column(UUID(as_uuid=True), ForeignKey('professionals.id'), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    appointment_date = Column(Date, nullable=False)
    appointment_time = Column(Time, nullable=False)
    duration_minutes = Column(Integer, default=30)
    type = Column(String(50), default='Virtual')
    status = Column(String(20), default='Scheduled')
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())

    # No explicit relationships – backrefs from Client and Professional provide .client and .professional

    def __repr__(self):
        return f'<Appointment {self.title}>'