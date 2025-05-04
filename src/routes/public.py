from flask import Blueprint, render_template, abort
from src.models import Vehicle, Settings, Promotion, db

# Remove template_folder argument, Flask will use the default 'templates' folder
public_bp = Blueprint('public', __name__)

@public_bp.route('/')
def home():
    settings = Settings.query.first()
    # Fetch only active promotions
    promotions = Promotion.query.filter_by(is_active=True).all()
    # Fetch only vehicles not marked as sold
    vehicles = Vehicle.query.filter_by(sold=False).order_by(Vehicle.created_at.desc()).all()
    return render_template('index.html', vehicles=vehicles, settings=settings, promotions=promotions)

@public_bp.route('/vehicle/<int:vehicle_id>')
def vehicle_detail(vehicle_id):
    settings = Settings.query.first()
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    # Optionally, prevent viewing sold cars directly via URL, or show a 'Sold' banner
    # if vehicle.sold:
    #     abort(404) # Or render a specific template
    return render_template('vehicle_detail.html', vehicle=vehicle, settings=settings)

