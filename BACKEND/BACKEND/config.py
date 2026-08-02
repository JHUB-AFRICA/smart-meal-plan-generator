import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ===== Core =====
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql://user:pass@localhost/smartlishe_db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-change')
    JWT_ACCESS_TOKEN_EXPIRES = 86400  # 24 hours
    BCRYPT_LOG_ROUNDS = 12

    # ===== Uploads =====
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

    # ===== AI & Payment (mock) =====
    AI_PROVIDER = os.getenv('AI_PROVIDER', 'mock')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    PAYMENT_GATEWAY = os.getenv('PAYMENT_GATEWAY', 'mock')

    # ===== CORS =====
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')

    # ===== Email (Flask-Mail) =====
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')           # Your email address
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')           # App password (not your regular password)
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', ('Smart Lishe', MAIL_USERNAME))

    # ===== Frontend URL (for invitation links) =====
    FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5500')

# Ensure upload folder exists
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)