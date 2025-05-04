from .admin_user import db
import json

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True) # Singleton pattern, only one row expected
    logo_filename = db.Column(db.String(255), nullable=True)
    # Store social media links as JSON: {"facebook": "url", "instagram": "url", ...}
    social_media_links = db.Column(db.Text, nullable=True, default='{}')
    # Store WhatsApp contacts as JSON: [{"name": "Vendedor 1", "number": "5527..."}, ...]
    whatsapp_contacts = db.Column(db.Text, nullable=True, default='[]')

    def get_social_media_links(self):
        try:
            return json.loads(self.social_media_links or '{}')
        except json.JSONDecodeError:
            return {}

    def set_social_media_links(self, links_dict):
        self.social_media_links = json.dumps(links_dict)

    def get_whatsapp_contacts(self):
        try:
            return json.loads(self.whatsapp_contacts or '[]')
        except json.JSONDecodeError:
            return []

    def set_whatsapp_contacts(self, contacts_list):
        self.whatsapp_contacts = json.dumps(contacts_list)

    def __repr__(self):
        return f'<Settings {self.id}>'
