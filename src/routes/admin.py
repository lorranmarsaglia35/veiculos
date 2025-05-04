from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import os
from src.models import db, AdminUser, Vehicle, Settings, Promotion

# Remove template_folder argument, Flask will use the default 'templates' folder
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def allowed_file(filename):
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "admin_id" not in session:
            return redirect(url_for("admin.login"))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = AdminUser.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session["admin_id"] = user.id
            session["admin_username"] = user.username
            flash("Login bem-sucedido!", "success")
            return redirect(url_for("admin.dashboard"))
        else:
            flash("Usuário ou senha inválidos.", "danger")
    # Use path relative to the default 'templates' folder
    return render_template("admin/login.html")

@admin_bp.route("/logout")
@login_required
def logout():
    session.pop("admin_id", None)
    session.pop("admin_username", None)
    flash("Logout realizado com sucesso.", "info")
    return redirect(url_for("admin.login"))

@admin_bp.route("/dashboard")
@login_required
def dashboard():
    # Use path relative to the default 'templates' folder
    return render_template("admin/dashboard.html")

@admin_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current_password = request.form["current_password"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        user = AdminUser.query.get(session["admin_id"])

        if not check_password_hash(user.password_hash, current_password):
            flash("Senha atual incorreta.", "danger")
        elif new_password != confirm_password:
            flash("As novas senhas não coincidem.", "danger")
        else:
            user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            flash("Senha alterada com sucesso!", "success")
            return redirect(url_for("admin.dashboard"))
    # Use path relative to the default 'templates' folder
    return render_template("admin/change_password.html")

# --- Vehicle Management ---
@admin_bp.route("/vehicles")
@login_required
def manage_vehicles():
    vehicles = Vehicle.query.order_by(Vehicle.created_at.desc()).all()
    # Use path relative to the default 'templates' folder
    return render_template("admin/manage_vehicles.html", vehicles=vehicles)

@admin_bp.route("/vehicles/add", methods=["GET", "POST"])
@login_required
def add_vehicle():
    if request.method == "POST":
        # ... (form processing logic - unchanged) ...
        make = request.form["make"]
        model = request.form["model"]
        year = request.form["year"]
        mileage = request.form["mileage"]
        color = request.form["color"]
        price = request.form["price"]
        description = request.form.get("description", "")
        payment_methods = request.form.get("payment_methods", "")
        photos = request.files.getlist("photos")
        photo_filenames = []

        for photo in photos:
            if photo and allowed_file(photo.filename):
                filename = secure_filename(photo.filename)
                # Ensure unique filenames if needed, e.g., using uuid
                save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
                photo.save(save_path)
                photo_filenames.append(filename)
            elif photo:
                 flash(f"Tipo de arquivo inválido para {photo.filename}", "warning")

        new_vehicle = Vehicle(
            make=make, model=model, year=int(year), mileage=int(mileage),
            color=color, price=float(price), description=description,
            payment_methods=payment_methods, photos=",".join(photo_filenames)
        )
        db.session.add(new_vehicle)
        db.session.commit()
        flash("Veículo adicionado com sucesso!", "success")
        return redirect(url_for("admin.manage_vehicles"))
    # Use path relative to the default 'templates' folder
    return render_template("admin/vehicle_form.html", form_action=url_for("admin.add_vehicle"))

@admin_bp.route("/vehicles/edit/<int:vehicle_id>", methods=["GET", "POST"])
@login_required
def edit_vehicle(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    if request.method == "POST":
        # ... (form processing logic - largely unchanged, handle photo updates/removals) ...
        vehicle.make = request.form["make"]
        vehicle.model = request.form["model"]
        vehicle.year = int(request.form["year"])
        vehicle.mileage = int(request.form["mileage"])
        vehicle.color = request.form["color"]
        vehicle.price = float(request.form["price"])
        vehicle.description = request.form.get("description", "")
        vehicle.payment_methods = request.form.get("payment_methods", "")
        vehicle.sold = "sold" in request.form # Checkbox for sold status

        # Handle photo uploads (add new, keep existing, potentially remove old)
        new_photos = request.files.getlist("photos")
        existing_photos = vehicle.photos.split(",") if vehicle.photos else []
        updated_photo_filenames = list(existing_photos) # Start with existing

        for photo in new_photos:
            if photo and allowed_file(photo.filename):
                filename = secure_filename(photo.filename)
                save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
                photo.save(save_path)
                if filename not in updated_photo_filenames:
                    updated_photo_filenames.append(filename)
            elif photo:
                 flash(f"Tipo de arquivo inválido para {photo.filename}", "warning")

        # Add logic here if you want to allow removing specific photos via the form
        # e.g., checkboxes next to existing photos to mark for deletion

        vehicle.photos = ",".join(filter(None, updated_photo_filenames)) # Filter out empty strings

        db.session.commit()
        flash("Veículo atualizado com sucesso!", "success")
        return redirect(url_for("admin.manage_vehicles"))
    # Use path relative to the default 'templates' folder
    return render_template("admin/vehicle_form.html", vehicle=vehicle, form_action=url_for("admin.edit_vehicle", vehicle_id=vehicle.id))

@admin_bp.route("/vehicles/delete/<int:vehicle_id>", methods=["POST"])
@login_required
def delete_vehicle(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    # Optionally delete photo files from server
    if vehicle.photos:
        for filename in vehicle.photos.split(","):
            try:
                os.remove(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))
            except OSError as e:
                flash(f"Erro ao remover arquivo {filename}: {e}", "warning")
    db.session.delete(vehicle)
    db.session.commit()
    flash("Veículo excluído com sucesso!", "success")
    return redirect(url_for("admin.manage_vehicles"))

@admin_bp.route("/vehicles/toggle_sold/<int:vehicle_id>", methods=["POST"])
@login_required
def toggle_sold_vehicle(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    vehicle.sold = not vehicle.sold
    db.session.commit()
    status = "vendido" if vehicle.sold else "disponível"
    flash(f"Status do veículo {vehicle.make} {vehicle.model} alterado para {status}.", "success")
    return redirect(url_for("admin.manage_vehicles"))

# --- Settings Management ---
@admin_bp.route("/settings", methods=["GET", "POST"])
@login_required
def manage_settings():
    settings = Settings.query.first()
    if not settings:
        # Initialize settings if they don't exist
        settings = Settings()
        db.session.add(settings)
        db.session.commit()

    if request.method == "POST":
        settings.whatsapp_number = request.form["whatsapp_number"]
        settings.whatsapp_message = request.form.get("whatsapp_message", "")
        settings.facebook_url = request.form.get("facebook_url", "")
        settings.instagram_url = request.form.get("instagram_url", "")
        settings.other_social_url = request.form.get("other_social_url", "")

        logo = request.files.get("logo")
        if logo and allowed_file(logo.filename):
            # Delete old logo if exists
            if settings.logo_filename:
                 try:
                    os.remove(os.path.join(current_app.config["UPLOAD_FOLDER"], settings.logo_filename))
                 except OSError:
                    pass # Ignore if file doesn't exist
            filename = secure_filename(f"logo_{logo.filename}") # Add prefix to avoid conflicts
            save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            logo.save(save_path)
            settings.logo_filename = filename
        elif logo:
            flash(f"Tipo de arquivo inválido para o logo: {logo.filename}", "warning")

        db.session.commit()
        flash("Configurações atualizadas com sucesso!", "success")
        return redirect(url_for("admin.manage_settings"))
    # Use path relative to the default 'templates' folder
    return render_template("admin/manage_settings.html", settings=settings)

# --- Promotion Management ---
@admin_bp.route("/promotions")
@login_required
def manage_promotions():
    promotions = Promotion.query.order_by(Promotion.id.desc()).all()
    # Use path relative to the default 'templates' folder
    return render_template("admin/manage_promotions.html", promotions=promotions)

@admin_bp.route("/promotions/add", methods=["GET", "POST"])
@login_required
def add_promotion():
    if request.method == "POST":
        title = request.form["title"]
        text_content = request.form.get("text_content", "")
        is_active = "is_active" in request.form
        image = request.files.get("image")
        image_filename = None

        if image and allowed_file(image.filename):
            filename = secure_filename(f"promo_{image.filename}")
            save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            image.save(save_path)
            image_filename = filename
        elif image:
            flash(f"Tipo de arquivo inválido para imagem da promoção: {image.filename}", "warning")

        new_promo = Promotion(
            title=title, text_content=text_content,
            image_filename=image_filename, is_active=is_active
        )
        db.session.add(new_promo)
        db.session.commit()
        flash("Promoção adicionada com sucesso!", "success")
        return redirect(url_for("admin.manage_promotions"))
    # Use path relative to the default 'templates' folder
    return render_template("admin/promotion_form.html", form_action=url_for("admin.add_promotion"))

@admin_bp.route("/promotions/edit/<int:promo_id>", methods=["GET", "POST"])
@login_required
def edit_promotion(promo_id):
    promo = Promotion.query.get_or_404(promo_id)
    if request.method == "POST":
        promo.title = request.form["title"]
        promo.text_content = request.form.get("text_content", "")
        promo.is_active = "is_active" in request.form
        image = request.files.get("image")

        if image and allowed_file(image.filename):
            # Delete old image if exists
            if promo.image_filename:
                 try:
                    os.remove(os.path.join(current_app.config["UPLOAD_FOLDER"], promo.image_filename))
                 except OSError:
                    pass # Ignore if file doesn't exist
            filename = secure_filename(f"promo_{image.filename}")
            save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            image.save(save_path)
            promo.image_filename = filename
        elif image:
            flash(f"Tipo de arquivo inválido para imagem da promoção: {image.filename}", "warning")

        db.session.commit()
        flash("Promoção atualizada com sucesso!", "success")
        return redirect(url_for("admin.manage_promotions"))
    # Use path relative to the default 'templates' folder
    return render_template("admin/promotion_form.html", promo=promo, form_action=url_for("admin.edit_promotion", promo_id=promo.id))

@admin_bp.route("/promotions/delete/<int:promo_id>", methods=["POST"])
@login_required
def delete_promotion(promo_id):
    promo = Promotion.query.get_or_404(promo_id)
    # Delete image file if exists
    if promo.image_filename:
        try:
            os.remove(os.path.join(current_app.config["UPLOAD_FOLDER"], promo.image_filename))
        except OSError as e:
            flash(f"Erro ao remover arquivo de imagem {promo.image_filename}: {e}", "warning")
    db.session.delete(promo)
    db.session.commit()
    flash("Promoção excluída com sucesso!", "success")
    return redirect(url_for("admin.manage_promotions"))

@admin_bp.route("/promotions/toggle_active/<int:promo_id>", methods=["POST"])
@login_required
def toggle_active_promotion(promo_id):
    promo = Promotion.query.get_or_404(promo_id)
    promo.is_active = not promo.is_active
    db.session.commit()
    status = "ativa" if promo.is_active else "inativa"
    flash(f"Promoção ", {promo.title}, " marcada como {status}.", "success")
    return redirect(url_for("admin.manage_promotions"))

# Add a template for promotion_form.html if it doesn't exist
@admin_bp.route("/promotions/add_form_placeholder") # Placeholder route if needed
@login_required
def promotion_form_placeholder():
    # This is just a placeholder if you need to render the form directly
    # without add/edit logic, maybe for testing.
    # Use path relative to the default 'templates' folder
    return render_template("admin/promotion_form.html")

