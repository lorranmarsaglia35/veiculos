import os
import sys
from datetime import datetime
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, render_template, session
# Import db and models
from src.models import db, Settings, Promotion, Vehicle # Import Vehicle to pass current_year
# Import blueprints
from src.routes.admin import admin_bp
from src.routes.public import public_bp

app = Flask(__name__, 
            static_folder=os.path.join(os.path.dirname(__file__), 'static'),
            template_folder=os.path.join(os.path.dirname(__file__), 'templates')) # Main template folder

# Configuration
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'a_very_secret_key_for_dev_#$@!fl') # Stronger default secret key
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{os.getenv('DB_USERNAME', 'root')}:{os.getenv('DB_PASSWORD', 'password')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '3306')}/{os.getenv('DB_NAME', 'mydb')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16MB upload limit

# Initialize extensions
db.init_app(app)

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Register Blueprints
app.register_blueprint(public_bp, url_prefix='/')
app.register_blueprint(admin_bp, url_prefix='/admin')

# Context processors to make variables available in all templates
@app.context_processor
def inject_global_vars():
    # Check if admin blueprint exists to conditionally show admin link
    admin_login_route_exists = 'admin_bp.login' in app.url_map._rules_by_endpoint
    # Provide current year for validation or footer
    current_year = datetime.utcnow().year
    # Provide settings to base template if needed (e.g., for logo in header)
    settings = None
    try:
        # This might fail if DB is not ready yet during initial setup
        settings = Settings.query.first()
    except Exception:
        pass # Ignore error during setup
    return dict(
        admin_login_route_exists=admin_login_route_exists, 
        current_year=current_year,
        settings=settings # Make settings available globally
    )

# Serve uploaded files (ensure this route doesn't conflict with blueprints)
@app.route('/uploads/<path:filename>')
def uploaded_files(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Create database tables and initial data if they don't exist
with app.app_context():
    try:
        db.create_all()
        # Initialize settings if not present
        if not Settings.query.first():
            initial_settings = Settings()
            db.session.add(initial_settings)
            db.session.commit()
        # Initialize promotion if not present
        if not Promotion.query.first():
            initial_promotion = Promotion()
            db.session.add(initial_promotion)
            db.session.commit()
    except Exception as e:
        print(f"Error during initial DB setup: {e}")
        # Handle DB connection errors gracefully during startup if possible

if __name__ == '__main__':
    # Use debug=False for testing deployment readiness, True for development
    app.run(host='0.0.0.0', port=5000, debug=False) 

