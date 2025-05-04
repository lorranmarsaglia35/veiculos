from flask import Blueprint, render_template, abort, flash
from src.models import db, Vehicle, Settings, Promotion

# Configuração do Blueprint para rotas públicas
public_bp = Blueprint(
    'public_bp',  # Nome do blueprint
    __name__,
    template_folder='../templates',
    static_folder='../static',
    static_url_path='/static'
)

# ==================== ROTAS PÚBLICAS ====================

@public_bp.route('/')
def home():
    """
    Rota da página inicial.
    Exibe veículos disponíveis, promoções ativas e configurações do site.
    """
    try:
        settings = Settings.query.first()
        vehicles = Vehicle.query.filter_by(
            is_sold=False,
            is_featured=True if settings and settings.feature_vehicles else None
        ).order_by(Vehicle.created_at.desc()).limit(8).all()
        
        promotion = Promotion.query.filter_by(is_active=True).first()

    except Exception as e:
        flash('Erro ao carregar dados da página inicial', 'error')
        print(f"ERRO (home): {str(e)}")
        vehicles = []
        promotion = None
        settings = None

    return render_template(
        'public/index.html',
        vehicles=vehicles,
        promotion=promotion,
        settings=settings
    )

@public_bp.route('/veiculos')
def list_vehicles():
    """Lista completa de todos os veículos disponíveis"""
    try:
        vehicles = Vehicle.query.filter_by(is_sold=False)\
                      .order_by(Vehicle.price.desc()).all()
        settings = Settings.query.first()
        
    except Exception as e:
        flash('Erro ao carregar lista de veículos', 'error')
        print(f"ERRO (list_vehicles): {str(e)}")
        vehicles = []
        settings = None

    return render_template(
        'public/vehicles.html',
        vehicles=vehicles,
        settings=settings
    )

@public_bp.route('/veiculo/<int:vehicle_id>')
def vehicle_detail(vehicle_id):
    """Página de detalhes de um veículo específico"""
    try:
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        settings = Settings.query.first()
        
        if vehicle.is_sold:
            flash('Este veículo já foi vendido', 'warning')

    except Exception as e:
        print(f"ERRO (vehicle_detail): {str(e)}")
        abort(500, description="Erro ao carregar detalhes do veículo")

    return render_template(
        'public/vehicle_detail.html',
        vehicle=vehicle,
        settings=settings
    )

@public_bp.route('/promocoes')
def promotions():
    """Página com todas as promoções ativas"""
    try:
        promotions = Promotion.query.filter_by(is_active=True)\
                          .order_by(Promotion.end_date.asc()).all()
        settings = Settings.query.first()
        
    except Exception as e:
        flash('Erro ao carregar promoções', 'error')
        print(f"ERRO (promotions): {str(e)}")
        promotions = []
        settings = None

    return render_template(
        'public/promotions.html',
        promotions=promotions,
        settings=settings
    )

# ==================== TRATAMENTO DE ERROS ====================

@public_bp.app_errorhandler(404)
def page_not_found(e):
    return render_template('public/errors/404.html'), 404

@public_bp.app_errorhandler(500)
def internal_server_error(e):
    return render_template('public/errors/500.html'), 500
