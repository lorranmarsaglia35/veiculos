from flask import Blueprint, render_template, abort
from src.models import db, Vehicle, Settings, Promotion

public_bp = Blueprint(
    \'public_bp\
    ', __name__,
    template_folder='../templates', # Point to the main templates folder
    static_folder='../static', 
    static_url_path='/static' # Use the main static folder
)

@public_bp.route('/')
def home():
    # Fetch data needed for the home page
    try:
        vehicles = Vehicle.query.filter_by(is_sold=False).order_by(Vehicle.id.desc()).all()
        promotion = Promotion.query.filter_by(is_active=True).first()
        settings = Settings.query.first()
    except Exception as e:
        # Log the error e
        print(f"Error fetching data for home page: {e}")
        vehicles = []
        promotion = None
        settings = None
        # Optionally, flash a message or render an error page

    # Pass admin_login_route_exists=True if the admin blueprint is registered
    # This check will be done implicitly by url_for in the template
    return render_template('index.html', vehicles=vehicles, promotion=promotion, settings=settings, admin_login_route_exists=True)

@public_bp.route('/vehicle/<int:vehicle_id>')
def vehicle_detail(vehicle_id):
    # Fetch specific vehicle data
    try:
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        # Don't show sold vehicles directly via URL? Or show with a clear "SOLD" banner?
        # Let's allow viewing for now, but admin controls visibility on the list.
        settings = Settings.query.first()
    except Exception as e:
        print(f"Error fetching data for vehicle detail page: {e}")
        abort(500) # Internal Server Error

    return render_template('vehicle_detail.html', vehicle=vehicle, settings=settings, admin_login_route_exists=True)

