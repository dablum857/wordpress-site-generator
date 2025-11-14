from flask import render_template, send_file, redirect, url_for, flash, session, current_app
from functools import wraps
from models import User, WordPressSite
from wxr_generator import generate_wxr_file
from utils import parse_bibtex
from io import BytesIO
from xml.etree.ElementTree import tostring
import xml.dom.minidom as minidom
from datetime import datetime


def require_login(f):
    """Decorator to require user login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


def export_routes(bp):
    """Register export/download routes"""
    
    @bp.route('/preview/<int:site_id>')
    @require_login
    def preview(site_id):
        """Preview the generated content before download"""
        user = User.query.get(session['user_id'])
        site = WordPressSite.query.get_or_404(site_id)
        
        # Verify user owns this site
        if site.user_id != user.id:
            flash('You do not have permission to access this site.', 'error')
            return redirect(url_for('index'))
        
        # Collect all data
        step1_data = site.step1_data
        step2_data = site.step2_data
        step3_data = site.step3_data
        step4_data = site.step4_data
        
        # Check if all required steps are complete
        if not step1_data or not step2_data:
            flash('Please complete at least Steps 1 and 2 before previewing.', 'warning')
            return redirect(url_for('wizard.step', site_id=site.id, step=1))
        
        # Parse publications
        publications = []
        if step3_data and step3_data.bibtex_content:
            publications = parse_bibtex(step3_data.bibtex_content)
        
        # Get gallery images
        gallery_images = []
        if step4_data:
            gallery_images = step4_data.get_gallery_images()
        
        return render_template('wizard/preview.html',
                             site=site,
                             step1_data=step1_data,
                             step2_data=step2_data,
                             step3_data=step3_data,
                             step4_data=step4_data,
                             publications=publications,
                             gallery_images=gallery_images)
    
    
    @bp.route('/generate/<int:site_id>')
    @require_login
    def generate(site_id):
        """Generate the WXR file and show download page"""
        user = User.query.get(session['user_id'])
        site = WordPressSite.query.get_or_404(site_id)
        
        # Verify user owns this site
        if site.user_id != user.id:
            flash('You do not have permission to access this site.', 'error')
            return redirect(url_for('index'))
        
        # Collect all data
        step1_data = site.step1_data
        step2_data = site.step2_data
        step3_data = site.step3_data
        step4_data = site.step4_data
        
        # Check if all required steps are complete
        if not step1_data or not step2_data:
            flash('Please complete at least Steps 1 and 2 before generating.', 'warning')
            return redirect(url_for('wizard.step', site_id=site.id, step=1))
        
        # Generate WXR file
        try:
            wxr_tree = generate_wxr_file(
                user, site, step1_data, step2_data, step3_data, step4_data,
                current_app.config['UPLOAD_FOLDER']
            )
            
            # Create filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"wordpress_export_{site.id}_{timestamp}.wxr"
            
            # Store in session for download
            session['wxr_data'] = tostring(wxr_tree.getroot(), encoding='unicode')
            session['wxr_filename'] = filename
            
            # Parse publications and gallery for display
            publications = []
            if step3_data and step3_data.bibtex_content:
                publications = parse_bibtex(step3_data.bibtex_content)
            
            gallery_images = []
            if step4_data:
                gallery_images = step4_data.get_gallery_images()
            
            return render_template('wizard/download.html',
                                 site=site,
                                 filename=filename,
                                 has_publications=bool(publications),
                                 has_gallery=bool(gallery_images))
        
        except Exception as e:
            flash(f'Error generating WXR file: {str(e)}', 'error')
            return redirect(url_for('export.preview', site_id=site.id))
    
    
    @bp.route('/download/<int:site_id>')
    @require_login
    def download(site_id):
        """Download the generated WXR file"""
        user = User.query.get(session['user_id'])
        site = WordPressSite.query.get_or_404(site_id)
        
        # Verify user owns this site
        if site.user_id != user.id:
            flash('You do not have permission to download this file.', 'error')
            return redirect(url_for('index'))
        
        # Get WXR data from session
        wxr_data = session.get('wxr_data')
        filename = session.get('wxr_filename', 'wordpress_export.wxr')
        
        if not wxr_data:
            flash('WXR file not found. Please generate the file again.', 'error')
            return redirect(url_for('export.preview', site_id=site.id))
        
        # Create file-like object with proper XML formatting
        output = BytesIO()
        
        # Write XML declaration
        output.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        
        # Write the WXR content
        output.write(wxr_data.encode('utf-8'))
        
        output.seek(0)
        
        # Send file
        return send_file(
            output,
            mimetype='application/xml',
            as_attachment=True,
            download_name=filename
        )
