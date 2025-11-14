from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()


class User(db.Model):
    """User model - represents an MIT user"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), nullable=True)
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    wordpress_sites = db.relationship('WordPressSite', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username


class WordPressSite(db.Model):
    """WordPress Site model - represents a WordPress site configuration"""
    __tablename__ = 'wordpress_sites'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    site_name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    step1_data = db.relationship('Step1PersonalInfo', backref='site', uselist=False, cascade='all, delete-orphan')
    step2_data = db.relationship('Step2Biography', backref='site', uselist=False, cascade='all, delete-orphan')
    step3_data = db.relationship('Step3Publications', backref='site', uselist=False, cascade='all, delete-orphan')
    step4_data = db.relationship('Step4Gallery', backref='site', uselist=False, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<WordPressSite {self.site_name}>'
    
    def is_complete(self):
        """Check if all required steps are complete"""
        return bool(self.step1_data and self.step2_data)


class Step1PersonalInfo(db.Model):
    """Step 1: Personal Information"""
    __tablename__ = 'step1_personal_info'
    
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('wordpress_sites.id'), nullable=False)
    
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    title_role = db.Column(db.String(255), nullable=True)
    department = db.Column(db.String(255), nullable=True)
    field_of_study = db.Column(db.String(255), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    office_address = db.Column(db.Text, nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Step1PersonalInfo {self.site_id}>'


class Step2Biography(db.Model):
    """Step 2: Biography"""
    __tablename__ = 'step2_biography'
    
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('wordpress_sites.id'), nullable=False)
    
    biography = db.Column(db.Text, nullable=True)
    
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Step2Biography {self.site_id}>'


class Step3Publications(db.Model):
    """Step 3: Publications (BibTeX format)"""
    __tablename__ = 'step3_publications'
    
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('wordpress_sites.id'), nullable=False)
    
    bibtex_content = db.Column(db.Text, nullable=True)
    
    # Relationship to manual publications
    manual_publications = db.relationship('ManualPublication', backref='step3', lazy=True, cascade='all, delete-orphan')
    
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Step3Publications {self.site_id}>'


class ManualPublication(db.Model):
    """Manually entered publication"""
    __tablename__ = 'manual_publications'
    
    id = db.Column(db.Integer, primary_key=True)
    step3_id = db.Column(db.Integer, db.ForeignKey('step3_publications.id'), nullable=False)
    
    author = db.Column(db.String(500), nullable=False)
    title = db.Column(db.String(500), nullable=False)
    publication_year = db.Column(db.String(4), nullable=True)
    journal_or_booktitle = db.Column(db.String(500), nullable=True)
    publisher = db.Column(db.String(500), nullable=True)
    doi = db.Column(db.String(100), nullable=True)
    url = db.Column(db.String(500), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary for display"""
        return {
            'id': self.id,
            'author': self.author,
            'title': self.title,
            'year': self.publication_year,
            'journal': self.journal_or_booktitle,
            'publisher': self.publisher,
            'doi': self.doi,
            'url': self.url
        }
    
    def __repr__(self):
        return f'<ManualPublication {self.title}>'


class Step4Gallery(db.Model):
    """Step 4: Gallery Images"""
    __tablename__ = 'step4_gallery'
    
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('wordpress_sites.id'), nullable=False)
    
    profile_picture = db.Column(db.String(500), nullable=True)
    gallery_images = db.Column(db.Text, nullable=True)  # JSON list of filenames
    
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_gallery_images(self):
        """Parse gallery images from JSON"""
        if self.gallery_images:
            return json.loads(self.gallery_images)
        return []
    
    def set_gallery_images(self, images_list):
        """Store gallery images as JSON"""
        self.gallery_images = json.dumps(images_list)
    
    def __repr__(self):
        return f'<Step4Gallery {self.site_id}>'
