from .admin_user import db

class Promotion(db.Model):
    id = db.Column(db.Integer, primary_key=True) # Singleton pattern, only one promotion active at a time?
    is_active = db.Column(db.Boolean, default=False, nullable=False)
    text = db.Column(db.Text, nullable=True)
    image_filename = db.Column(db.String(255), nullable=True) # Store filename, actual file stored on disk

    def __repr__(self):
        return f'<Promotion {self.id} (Active: {self.is_active})>'
