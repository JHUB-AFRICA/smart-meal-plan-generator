import os
from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from config import Config
from extensions import db, bcrypt, mail, migrate   # <-- ADDED migrate

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)           # <-- THIS ENABLES THE `db` COMMAND
    CORS(app, origins=app.config.get('CORS_ORIGINS', '*'))

    # Lazy import to avoid circular dependency
    from routes import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    @app.route('/')
    def index():
        return jsonify({
            'message': 'Smart Lishe API is running',
            'version': '1.0.0',
            'status': 'healthy'
        })

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        return jsonify({
            'success': False,
            'error': e.description,
            'code': e.code
        }), e.code

    @app.errorhandler(Exception)
    def handle_generic_exception(e):
        app.logger.error(f'Unhandled exception: {e}', exc_info=True)
        return jsonify({
            'success': False,
            'error': 'An internal server error occurred.',
            'code': 500
        }), 500

    return app

# =====================================================
# Create the Flask application for Gunicorn
# =====================================================
app = create_app()

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)