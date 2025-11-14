from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, TelField, SubmitField
from wtforms.validators import DataRequired, Email, Optional, Length


class Step1Form(FlaskForm):
    """Step 1: Personal Information"""
    first_name = StringField('First Name', validators=[
        DataRequired(message='First name is required'),
        Length(max=100)
    ])
    last_name = StringField('Last Name', validators=[
        DataRequired(message='Last name is required'),
        Length(max=100)
    ])
    title_role = StringField('Title/Role', validators=[
        DataRequired(message='Title/Role is required'),
        Length(max=255)
    ])
    department = StringField('Department', validators=[
        DataRequired(message='Department is required'),
        Length(max=255)
    ])
    field_of_study = StringField('Field of Study', validators=[
        Optional(),
        Length(max=255)
    ])
    email = StringField('Email Address', validators=[
        DataRequired(message='Email is required'),
        Email(message='Invalid email address')
    ])
    office_address = TextAreaField('Campus Office Address', validators=[
        DataRequired(message='Office address is required')
    ])
    phone_number = TelField('Phone Number (Optional)', validators=[
        Optional(),
        Length(max=20)
    ])
    submit = SubmitField('Next Step')
    save_draft = SubmitField('Save Draft')


class Step2Form(FlaskForm):
    """Step 2: Biography"""
    biography = TextAreaField('Biography', validators=[
        DataRequired(message='Biography is required'),
        Length(min=50, message='Biography should be at least 50 characters')
    ], render_kw={
        'rows': 10,
        'placeholder': 'Enter a paragraph or two about yourself...'
    })
    submit = SubmitField('Next Step')
    save_draft = SubmitField('Save Draft')


class Step3FormUpdated(FlaskForm):
    """Step 3: Publications - Updated with file upload"""
    bibtex_file = FileField('Upload BibTeX File', validators=[
        FileAllowed(['bib', 'txt'], 'BibTeX files only!')
    ])
    
    bibtex_content = TextAreaField('Publications (BibTeX Format)', validators=[
        Optional()
    ], render_kw={
        'rows': 15,
        'placeholder': '@article{key2023,\n  author={Author, Name},\n  title={Article Title},\n  journal={Journal Name},\n  year={2023}\n}'
    })
    submit = SubmitField('Next Step')
    save_draft = SubmitField('Save Draft')


class ManualPublicationForm(FlaskForm):
    """Form for manually entering a single publication"""
    author = StringField('Author(s)', validators=[
        DataRequired(message='Author is required'),
        Length(max=500)
    ])
    title = StringField('Title', validators=[
        DataRequired(message='Title is required'),
        Length(max=500)
    ])
    publication_year = StringField('Year', validators=[
        Optional(),
        Length(max=4)
    ])
    journal_or_booktitle = StringField('Journal/Booktitle', validators=[
        Optional(),
        Length(max=500)
    ])
    publisher = StringField('Publisher', validators=[
        Optional(),
        Length(max=500)
    ])
    doi = StringField('DOI (Optional)', validators=[
        Optional(),
        Length(max=100)
    ])
    url = StringField('URL (Optional)', validators=[
        Optional(),
        Length(max=500)
    ])
    submit = SubmitField('Add Publication')


class Step4Form(FlaskForm):
    """Step 4: Gallery and Images"""
    profile_picture = FileField('Profile Picture (Optional)', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 'Images only!')
    ])
    gallery_images = FileField('Gallery Images (Optional)', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 'Images only!')
    ], render_kw={'multiple': True})
    submit = SubmitField('Review & Preview')
    save_draft = SubmitField('Save Draft')


class CreateSiteForm(FlaskForm):
    """Create new WordPress site"""
    site_name = StringField('Site Name', validators=[
        DataRequired(message='Site name is required'),
        Length(max=255)
    ])
    submit = SubmitField('Create New Site')

class EditManualPublicationForm(FlaskForm):
    """Form for editing a manual publication"""
    author = StringField('Author(s)', validators=[
        DataRequired(message='Author is required'),
        Length(max=500)
    ])
    title = StringField('Title', validators=[
        DataRequired(message='Title is required'),
        Length(max=500)
    ])
    publication_year = StringField('Year', validators=[
        Optional(),
        Length(max=4)
    ])
    journal_or_booktitle = StringField('Journal/Booktitle', validators=[
        Optional(),
        Length(max=500)
    ])
    publisher = StringField('Publisher', validators=[
        Optional(),
        Length(max=500)
    ])
    doi = StringField('DOI (Optional)', validators=[
        Optional(),
        Length(max=100)
    ])
    url = StringField('URL (Optional)', validators=[
        Optional(),
        Length(max=500)
    ])
    submit = SubmitField('Update Publication')
