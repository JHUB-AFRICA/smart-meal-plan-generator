import os
from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from config import Config
from extensions import db, bcrypt, mail   # Added bcrypt and mail


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)    # <-- Added
    mail.init_app(app)      # <-- Added
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

    # Fixed: added @app.errorhandler decorator
    @app.errorhandler(Exception)
    def handle_generic_exception(e):
        app.logger.error(f'Unhandled exception: {e}', exc_info=True)
        return jsonify({
            'success': False,
            'error': 'An internal server error occurred.',
            'code': 500
        }), 500

    return app


if __name__ == '__main__':
    app = create_app()
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)