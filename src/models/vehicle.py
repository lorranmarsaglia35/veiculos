from .admin_user import db
import json

class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    mileage = db.Column(db.Integer, nullable=False)
    color = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True) # Includes payment methods info
    is_sold = db.Column(db.Boolean, default=False, nullable=False)
    photos = db.relationship('VehiclePhoto', backref='vehicle', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Vehicle {self.brand} {self.model} ({self.year})>'

class VehiclePhoto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False) # Store filename, actual file stored on disk

    def __repr__(self):
        return f'<VehiclePhoto {self.filename} for Vehicle {self.vehicle_id}>'
