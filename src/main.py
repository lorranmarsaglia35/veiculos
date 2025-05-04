import os
import sys
from datetime import datetime
from urllib.parse import urlparse
from flask import Flask, send_from_directory, render_template, session
from src.models import db, Settings, Promotion, Vehicle
from src.routes.admin import admin_bp
from src.routes.public import public_bp

# Configuração inicial do app
app = Flask(__name__,
            static_folder=os.path.join(os.path.dirname(__file__), 'static'),
            template_folder=os.path.join(os.path.dirname(__file__), 'templates'))

# Configuração robusta do banco de dados
def get_database_uri():
    # 1. Prioridade para DATABASE_URL do Render (PostgreSQL)
    if 'DATABASE_URL' in os.environ:
        db_url = os.environ['DATABASE_URL']
        if db_url.startswith('postgres://'):
            return db_url.replace('postgres://', 'postgresql+psycopg2://', 1)
        return db_url
    
    # 2. Fallback para MySQL (se variáveis individuais existirem)
    if all(k in os.environ for k in ['DB_HOST', 'DB_USERNAME', 'DB_PASSWORD', 'DB_NAME']):
        return f"mysql+pymysql://{os.getenv('DB_USERNAME')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT', '3306')}/{os.getenv('DB_NAME')}"
    
    # 3. Fallback para SQLite local (apenas desenvolvimento)
    return 'sqlite:///' + os.path.join(os.path.dirname(__file__), 'local.db')

# Configurações principais
app.config.update(
    SECRET_KEY=os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-me'),
    SQLALCHEMY_DATABASE_URI=get_database_uri(),
    SQLALCHEMY_ENGINE_OPTIONS={
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_timeout': 30,
        'max_overflow': 20,
    },
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    UPLOAD_FOLDER=os.path.join(os.path.dirname(__file__), 'static', 'uploads'),
    MAX_CONTENT_LENGTH=16 * 1024 * 1024
)

# Inicializações
db.init_app(app)

# Criar pasta de uploads
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Registrar blueprints
app.register_blueprint(public_bp, url_prefix='/')
app.register_blueprint(admin_bp, url_prefix='/admin')

# Context processors
@app.context_processor
def inject_global_vars():
    try:
        settings = Settings.query.first() if db.session.is_active else None
    except:
        settings = None
    
    return dict(
        admin_login_route_exists='admin_bp.login' in app.url_map._rules_by_endpoint,
        current_year=datetime.now().year,
        settings=settings
    )

# Rota para arquivos uploadados
@app.route('/uploads/<path:filename>')
def uploaded_files(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Inicialização do banco de dados
with app.app_context():
    try:
        db.create_all()
        if not Settings.query.first():
            db.session.add(Settings())
        if not Promotion.query.first():
            db.session.add(Promotion())
        db.session.commit()
    except Exception as e:
        app.logger.error(f"Database initialization error: {str(e)}")
        # Tentar novamente após 5 segundos se em produção
        if not app.debug:
            import time
            time.sleep(5)
            db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=False)

