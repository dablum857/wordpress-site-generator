from flask import render_template, request, redirect, url_for, flash, session
from functools import wraps
from models import db, User, WordPressSite, Step1PersonalInfo, Step2Biography, Step3Publications, Step4Gallery
from forms import Step1Form, Step2Form, Step3Form, Step4Form
from utils import get_environment_user_data, save_uploaded_file, get_uploaded_file_path, parse_bibtex
from wxr_generator import generate_wxr_file
import os


def require_login(f):
    """Decorator to require user login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


def wizard_routes(bp):
    """Register wizard routes"""
    
    @bp.route('/<int:site_id>/step/<int:step>', methods=['GET', 'POST'])
    @require_login
    def step(site_id, step):
        """Multi-step wizard for site generation"""
        user = User.query.get(session['user_id'])
        site = WordPressSite.query.get_or_404(site_id)
        
        # Verify user owns this site
        if site.user_id != user.id:
            flash('You do not have permission to access this site.', 'error')
            return redirect(url_for('index'))
        
        if step == 1:
            return _handle_step1(site, user)
        elif step == 2:
            return _handle_step2(site, user)
        elif step == 3:
            return _handle_step3(site, user)
        elif step == 4:
            return _handle_step4(site, user)
        elif step == 5:
            return _handle_preview(site, user)
        else:
            flash('Invalid step', 'error')
            return redirect(url_for('index'))


def _handle_step1(site, user):
    """Handle Step 1: Personal Information"""
    env_data = get_environment_user_data()
    step1_data = site.step1_data
    
    form = Step1Form()
    
    # Pre-populate from environment
    if request.method == 'GET' and step1_data is None:
        form.first_name.data = env_data.get('first_name') or user.first_name
        form.last_name.data = env_data.get('last_name') or user.last_name
        form.email.data = env_data.get('email') or user.email
        form.department.data = env_data.get('department')
    elif step1_data and request.method == 'GET':
        form.first_name.data = step1_data.first_name
        form.last_name.data = step1_data.last_name
        form.title_role.data = step1_data.title_role
        form.department.data = step1_data.department
        form.field_of_study.data = step1_data.field_of_study
        form.email.data = step1_data.email
        form.office_address.data = step1_data.office_address
        form.phone_number.data = step1_data.phone_number
    
    if form.validate_on_submit():
        # Save or update step1 data
        if step1_data is None:
            step1_data = Step1PersonalInfo(site_id=site.id)
        
        step1_data.first_name = form.first_name.data
        step1_data.last_name = form.last_name.data
        step1_data.title_role = form.title_role.data
        step1_data.department = form.department.data
        step1_data.field_of_study = form.field_of_study.data
        step1_data.email = form.email.data
        step1_data.office_address = form.office_address.data
        step1_data.phone_number = form.phone_number.data
        
        db.session.add(step1_data)
        db.session.commit()
        
        if form.submit.data:
            return redirect(url_for('wizard.step', site_id=site.id, step=2))
        else:
            flash('Step 1 saved as draft', 'success')
            return redirect(url_for('index'))
    
    return render_template('wizard/step1.html', form=form, site=site, step=1)


def _handle_step2(site, user):
    """Handle Step 2: Biography"""
    step2_data = site.step2_data
    
    form = Step2Form()
    
    if step2_data and request.method == 'GET':
        form.biography.data = step2_data.biography
    
    if form.validate_on_submit():
        if step2_data is None:
            step2_data = Step2Biography(site_id=site.id)
        
        step2_data.biography = form.biography.data
        
        db.session.add(step2_data)
        db.session.commit()
        
        if form.submit.data:
            return redirect(url_for('wizard.step', site_id=site.id, step=3))
        else:
            flash('Step 2 saved as draft', 'success')
            return redirect(url_for('index'))
    
    return render_template('wizard/step2.html', form=form, site=site, step=2)


def _handle_step3(site, user):
    """Handle Step 3: Publications"""
    step3_data = site.step3_data
    
    form = Step3Form()
    
    if step3_data and request.method == 'GET':
        form.bibtex_content.data = step3_data.bibtex_content
    
    if form.validate_on_submit():
        if step3_data is None:
            step3_data = Step3Publications(site_id=site.id)
        
        step3_data.bibtex_content = form.bibtex_content.data or ''
        
        db.session.add(step3_data)
        db.session.commit()
        
        if form.submit.data:
            return redirect(url_for('wizard.step', site_id=site.id, step=4))
        else:
            flash('Step 3 saved as draft', 'success')
            return redirect(url_for('index'))
    
    return render_template('wizard/step3.html', form=form, site=site, step=3)


def _handle_step4(site, user):
    """Handle Step 4: Gallery and Images"""
    from flask import current_app
    
    step4_data = site.step4_data
    if step4_data is None:
        step4_data = Step4Gallery(site_id=site.id)
        db.session.add(step4_data)
        db.session.commit()
    
    form = Step4Form()
    
    # Get current images
    current_profile = step4_data.profile_picture
    current_gallery = step4_data.get_gallery_images()
    
    if form.validate_on_submit():
        # Handle profile picture
        if form.profile_picture.data:
            # Delete old profile picture if exists
            if current_profile:
                from utils import delete_uploaded_file
                delete_uploaded_file(site.id, current_profile, current_app.config['UPLOAD_FOLDER'])
            
            filename = save_uploaded_file(
                form.profile_picture.data,
                site.id,
                current_app.config['UPLOAD_FOLDER']
            )
            if filename:
                step4_data.profile_picture = filename
        
        # Handle gallery images
        gallery_images = request.files.getlist('gallery_images')
        if gallery_images:
            new_gallery = []
            for gfile in gallery_images:
                if gfile and gfile.filename:
                    filename = save_uploaded_file(
                        gfile,
                        site.id,
                        current_app.config['UPLOAD_FOLDER']
                    )
                    if filename:
                        new_gallery.append(filename)
            
            # Append to existing gallery
            existing = step4_data.get_gallery_images()
            combined = existing + new_gallery
            step4_data.set_gallery_images(combined)
        
        db.session.commit()
        
        if form.submit.data:
            return redirect(url_for('export.preview', site_id=site.id))
        else:
            flash('Step 4 saved as draft', 'success')
            return redirect(url_for('index'))
    
    return render_template(
        'wizard/step4.html',
        form=form,
        site=site,
        step=4,
        current_profile=current_profile,
        current_gallery=current_gallery
    )
