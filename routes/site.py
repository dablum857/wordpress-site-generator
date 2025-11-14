from flask import render_template, request, redirect, url_for, flash, session
from functools import wraps
from models import db, User, WordPressSite
from forms import CreateSiteForm


def require_login(f):
    """Decorator to require user login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


def site_routes(bp):
    """Register site management routes"""
    
    @bp.route('/new', methods=['GET', 'POST'])
    @require_login
    def create():
        """Create new WordPress site"""
        form = CreateSiteForm()
        user = User.query.get(session['user_id'])
        
        if form.validate_on_submit():
            site = WordPressSite(user_id=user.id, site_name=form.site_name.data)
            db.session.add(site)
            db.session.commit()
            
            flash(f'Site "{site.site_name}" created successfully!', 'success')
            return redirect(url_for('wizard.step', site_id=site.id, step=1))
        
        return render_template('create_site.html', form=form)
    
    
    @bp.route('/select')
    @require_login
    def select():
        """Select which site to edit/regenerate"""
        user = User.query.get(session['user_id'])
        sites = user.wordpress_sites
        
        if not sites:
            flash('No WordPress sites found. Create one to get started.', 'info')
            return redirect(url_for('site.create'))
        
        return render_template('select_site.html', sites=sites)
    
    
    @bp.route('/<int:site_id>/delete', methods=['POST'])
    @require_login
    def delete(site_id):
        """Delete a WordPress site"""
        user = User.query.get(session['user_id'])
        site = WordPressSite.query.get_or_404(site_id)
        
        # Verify user owns this site
        if site.user_id != user.id:
            flash('You do not have permission to delete this site.', 'error')
            return redirect(url_for('index'))
        
        db.session.delete(site)
        db.session.commit()
        
        flash(f'Site "{site.site_name}" deleted successfully.', 'success')
        return redirect(url_for('index'))
