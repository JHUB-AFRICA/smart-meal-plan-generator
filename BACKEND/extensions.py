from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from flask_migrate import Migrate   # <-- ADD THIS

db = SQLAlchemy()
bcrypt = Bcrypt()
mail = Mail()
migrate = Migrate()                 # <-- ADD THIS