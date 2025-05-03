from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import os
import json

# Assuming models are correctly set up in src.models
from src.models import db, AdminUser, Vehicle, VehiclePhoto, Settings, Promotion

admin_bp = Blueprint(
    'admin_bp', 
    __name__,
    template_folder='templates', # Specify template folder relative to blueprint
    static_folder='static', 
    static_url_path='/admin/static' # Optional: if you have admin-specific static files
)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Authentication --- 

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_user_id' not in session:
            flash('Por favor, faça login para acessar esta página.', 'warning')
            return redirect(url_for('admin_bp.login'))
        # Check if admin user still exists (optional but good practice)
        user = AdminUser.query.get(session['admin_user_id'])
        if not user:
            session.clear()
            flash('Sua sessão expirou ou o usuário foi removido.', 'warning')
            return redirect(url_for('admin_bp.login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Create default admin if none exists
        if not AdminUser.query.first():
            hashed_password = generate_password_hash('admin', method='pbkdf2:sha256')
            default_admin = AdminUser(username='admin', password_hash=hashed_password)
            db.session.add(default_admin)
            db.session.commit()
            flash('Usuário admin padrão criado com senha \'admin\'. Por favor, altere a senha imediatamente.', 'info')
        
        user = AdminUser.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            session.permanent = True # Make session last longer (configure lifetime in app config if needed)
            session['admin_user_id'] = user.id
            session['admin_username'] = user.username
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('admin_bp.dashboard'))
        else:
            flash('Nome de usuário ou senha inválidos.', 'danger')
            
    return render_template('admin/login.html')

@admin_bp.route('/logout')
@login_required
def logout():
    session.pop('admin_user_id', None)
    session.pop('admin_username', None)
    flash('Logout realizado com sucesso.', 'info')
    return redirect(url_for('admin_bp.login'))

# --- Dashboard --- 

@admin_bp.route('/')
@login_required
def dashboard():
    vehicle_count = Vehicle.query.count()
    sold_count = Vehicle.query.filter_by(is_sold=True).count()
    return render_template('admin/dashboard.html', vehicle_count=vehicle_count, sold_count=sold_count)

# --- Password Change --- 

@admin_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        user_id = session['admin_user_id']
        user = AdminUser.query.get(user_id)
        
        if not user or not check_password_hash(user.password_hash, current_password):
            flash('Senha atual incorreta.', 'danger')
        elif not new_password or len(new_password) < 6:
             flash('Nova senha deve ter pelo menos 6 caracteres.', 'warning')
        elif new_password != confirm_password:
            flash('Nova senha e confirmação não coincidem.', 'danger')
        else:
            user.password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
            db.session.commit()
            flash('Senha alterada com sucesso!', 'success')
            return redirect(url_for('admin_bp.dashboard'))
            
    return render_template('admin/change_password.html')

# --- Vehicle Management --- 

@admin_bp.route('/vehicles')
@login_required
def manage_vehicles():
    vehicles = Vehicle.query.order_by(Vehicle.id.desc()).all()
    return render_template('admin/manage_vehicles.html', vehicles=vehicles)

@admin_bp.route('/vehicles/add', methods=['GET', 'POST'])
@login_required
def add_vehicle():
    if request.method == 'POST':
        # Extract form data
        brand = request.form.get('brand')
        model = request.form.get('model')
        year = request.form.get('year', type=int)
        mileage = request.form.get('mileage', type=int)
        color = request.form.get('color')
        price = request.form.get('price', type=float)
        description = request.form.get('description')
        
        # Basic validation
        if not all([brand, model, year, mileage, color, price]):
            flash('Por favor, preencha todos os campos obrigatórios.', 'warning')
            return render_template('admin/vehicle_form.html', form_action=url_for('admin_bp.add_vehicle'))

        new_vehicle = Vehicle(
            brand=brand, model=model, year=year, mileage=mileage, 
            color=color, price=price, description=description
        )
        db.session.add(new_vehicle)
        # Commit here to get the new_vehicle.id for photos
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao adicionar veículo: {e}', 'danger')
            return render_template('admin/vehicle_form.html', form_action=url_for('admin_bp.add_vehicle'), vehicle=request.form)

        # Handle photo uploads
        photos = request.files.getlist('photos')
        for photo in photos:
            if photo and allowed_file(photo.filename):
                filename = secure_filename(f"vehicle_{new_vehicle.id}_{photo.filename}")
                save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                try:
                    photo.save(save_path)
                    vehicle_photo = VehiclePhoto(vehicle_id=new_vehicle.id, filename=filename)
                    db.session.add(vehicle_photo)
                except Exception as e:
                     flash(f'Erro ao salvar foto {photo.filename}: {e}', 'danger')
                     # Continue trying to save other photos
            elif photo.filename != '':
                flash(f'Tipo de arquivo inválido para foto: {photo.filename}', 'warning')

        try:
            db.session.commit() # Commit photo additions
            flash('Veículo adicionado com sucesso!', 'success')
            return redirect(url_for('admin_bp.manage_vehicles'))
        except Exception as e:
            db.session.rollback()
            # Attempt to clean up saved files if commit fails?
            flash(f'Erro ao salvar fotos do veículo: {e}', 'danger')
            # Redirecting to edit might be better here, but let's keep it simple
            return redirect(url_for('admin_bp.manage_vehicles'))

    # GET request
    return render_template('admin/vehicle_form.html', form_action=url_for('admin_bp.add_vehicle'), form_title='Adicionar Novo Veículo')

@admin_bp.route('/vehicles/edit/<int:vehicle_id>', methods=['GET', 'POST'])
@login_required
def edit_vehicle(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)

    if request.method == 'POST':
        # Update fields
        vehicle.brand = request.form.get('brand')
        vehicle.model = request.form.get('model')
        vehicle.year = request.form.get('year', type=int)
        vehicle.mileage = request.form.get('mileage', type=int)
        vehicle.color = request.form.get('color')
        vehicle.price = request.form.get('price', type=float)
        vehicle.description = request.form.get('description')
        # is_sold is handled separately

        # Basic validation
        if not all([vehicle.brand, vehicle.model, vehicle.year, vehicle.mileage, vehicle.color, vehicle.price]):
            flash('Por favor, preencha todos os campos obrigatórios.', 'warning')
            return render_template('admin/vehicle_form.html', vehicle=vehicle, form_action=url_for('admin_bp.edit_vehicle', vehicle_id=vehicle_id), form_title='Editar Veículo')

        # Handle new photo uploads
        photos = request.files.getlist('photos')
        for photo in photos:
            if photo and allowed_file(photo.filename):
                filename = secure_filename(f"vehicle_{vehicle.id}_{photo.filename}")
                save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                try:
                    photo.save(save_path)
                    # Avoid duplicates if filename already exists for this vehicle?
                    if not VehiclePhoto.query.filter_by(vehicle_id=vehicle.id, filename=filename).first():
                        vehicle_photo = VehiclePhoto(vehicle_id=vehicle.id, filename=filename)
                        db.session.add(vehicle_photo)
                except Exception as e:
                     flash(f'Erro ao salvar nova foto {photo.filename}: {e}', 'danger')
            elif photo.filename != '':
                flash(f'Tipo de arquivo inválido para nova foto: {photo.filename}', 'warning')

        try:
            db.session.commit()
            flash('Veículo atualizado com sucesso!', 'success')
            return redirect(url_for('admin_bp.manage_vehicles'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar veículo: {e}', 'danger')
            return render_template('admin/vehicle_form.html', vehicle=vehicle, form_action=url_for('admin_bp.edit_vehicle', vehicle_id=vehicle_id), form_title='Editar Veículo')

    # GET request
    return render_template('admin/vehicle_form.html', vehicle=vehicle, form_action=url_for('admin_bp.edit_vehicle', vehicle_id=vehicle_id), form_title='Editar Veículo')

@admin_bp.route('/vehicles/delete/<int:vehicle_id>', methods=['POST'])
@login_required
def delete_vehicle(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    try:
        # Delete associated photos from disk first
        for photo in vehicle.photos:
            try:
                os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], photo.filename))
            except OSError as e:
                flash(f'Erro ao remover arquivo de foto {photo.filename}: {e}', 'warning') # Log this instead?
        
        # Database cascade should handle deleting VehiclePhoto entries
        db.session.delete(vehicle)
        db.session.commit()
        flash('Veículo excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir veículo: {e}', 'danger')
    return redirect(url_for('admin_bp.manage_vehicles'))

@admin_bp.route('/vehicles/photo/delete/<int:photo_id>', methods=['POST'])
@login_required
def delete_vehicle_photo(photo_id):
    photo = VehiclePhoto.query.get_or_404(photo_id)
    vehicle_id = photo.vehicle_id # Keep track for redirect
    filename = photo.filename
    try:
        db.session.delete(photo)
        db.session.commit()
        # Delete file from disk after DB commit
        try:
            os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
        except OSError as e:
            flash(f'Erro ao remover arquivo de foto {filename} do disco: {e}', 'warning') # Log this
        flash('Foto excluída com sucesso.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir foto: {e}', 'danger')
    # Redirect back to the edit page of the vehicle
    return redirect(url_for('admin_bp.edit_vehicle', vehicle_id=vehicle_id))


@admin_bp.route('/vehicles/toggle_sold/<int:vehicle_id>', methods=['POST'])
@login_required
def toggle_sold_vehicle(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    try:
        vehicle.is_sold = not vehicle.is_sold
        db.session.commit()
        status = "vendido" if vehicle.is_sold else "disponível"
        flash(f'Status do veículo alterado para {status}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao alterar status do veículo: {e}', 'danger')
    return redirect(url_for('admin_bp.manage_vehicles'))


# --- Settings Management --- 

@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def manage_settings():
    settings = Settings.query.first()
    if not settings: # Should have been created on app start, but just in case
        settings = Settings()
        db.session.add(settings)
        db.session.commit()

    if request.method == 'POST':
        # Handle logo upload
        logo_file = request.files.get('logo')
        if logo_file and allowed_file(logo_file.filename):
            # Delete old logo if exists
            if settings.logo_filename:
                try:
                    os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], settings.logo_filename))
                except OSError:
                    pass # Ignore if file doesn't exist
            # Save new logo
            filename = secure_filename(f"logo_{logo_file.filename}")
            save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            try:
                logo_file.save(save_path)
                settings.logo_filename = filename
            except Exception as e:
                flash(f'Erro ao salvar logo: {e}', 'danger')
        elif logo_file and logo_file.filename != '':
             flash(f'Tipo de arquivo inválido para logo: {logo_file.filename}', 'warning')

        # Handle social media links (simple example, assumes keys like 'facebook', 'instagram')
        social_links = {}
        if request.form.get('social_facebook'):
            social_links['facebook'] = request.form.get('social_facebook')
        if request.form.get('social_instagram'):
            social_links['instagram'] = request.form.get('social_instagram')
        # Add more social links as needed
        settings.set_social_media_links(social_links)

        # Handle WhatsApp contacts
        whatsapp_contacts = []
        contact_names = request.form.getlist('whatsapp_name[]')
        contact_numbers = request.form.getlist('whatsapp_number[]')
        for name, number in zip(contact_names, contact_numbers):
            if name and number:
                # Basic phone number cleanup (remove non-digits)
                cleaned_number = ''.join(filter(str.isdigit, number))
                # Add country code if missing (assuming Brazil)
                if len(cleaned_number) <= 11 and not cleaned_number.startswith('55'):
                     cleaned_number = '55' + cleaned_number 
                whatsapp_contacts.append({'name': name, 'number': cleaned_number})
        settings.set_whatsapp_contacts(whatsapp_contacts)

        try:
            db.session.commit()
            flash('Configurações atualizadas com sucesso!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar configurações: {e}', 'danger')
        
        return redirect(url_for('admin_bp.manage_settings')) # Redirect to refresh

    # GET request
    return render_template('admin/manage_settings.html', settings=settings)

# --- Promotion Management --- 

@admin_bp.route('/promotions', methods=['GET', 'POST'])
@login_required
def manage_promotions():
    promotion = Promotion.query.first()
    if not promotion: # Should have been created on app start
        promotion = Promotion()
        db.session.add(promotion)
        db.session.commit()

    if request.method == 'POST':
        promotion.text = request.form.get('text')
        promotion.is_active = 'is_active' in request.form

        # Handle image upload
        promo_image = request.files.get('image')
        delete_image = 'delete_image' in request.form

        if delete_image and promotion.image_filename:
             try:
                 os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], promotion.image_filename))
                 promotion.image_filename = None
                 flash('Imagem da promoção removida.', 'info')
             except OSError as e:
                 flash(f'Erro ao remover imagem da promoção: {e}', 'warning')
        elif promo_image and allowed_file(promo_image.filename):
            # Delete old image if exists
            if promotion.image_filename:
                try:
                    os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], promotion.image_filename))
                except OSError:
                    pass # Ignore if file doesn't exist
            # Save new image
            filename = secure_filename(f"promotion_{promo_image.filename}")
            save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            try:
                promo_image.save(save_path)
                promotion.image_filename = filename
            except Exception as e:
                flash(f'Erro ao salvar imagem da promoção: {e}', 'danger')
        elif promo_image and promo_image.filename != '':
             flash(f'Tipo de arquivo inválido para imagem da promoção: {promo_image.filename}', 'warning')

        try:
            db.session.commit()
            flash('Promoção atualizada com sucesso!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar promoção: {e}', 'danger')
        
        return redirect(url_for('admin_bp.manage_promotions')) # Redirect to refresh

    # GET request
    return render_template('admin/manage_promotions.html', promotion=promotion)

