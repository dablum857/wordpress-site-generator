from flask import render_template, send_file, redirect, url_for, flash, session, current_app
from functools import wraps
from models import User, WordPressSite
from utils import parse_bibtex, format_publication_html
from io import BytesIO
from datetime import datetime
import xml.etree.ElementTree as ET


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
    
        # Parse BibTeX publications
        bibtex_publications = []
        if step3_data and step3_data.bibtex_content:
            try:
                bibtex_publications = parse_bibtex(step3_data.bibtex_content)
            except Exception as e:
                print(f"Error parsing BibTeX: {e}")
                bibtex_publications = []
    
        # Get manual publications
        manual_publications = []
        if step3_data:
            manual_publications = list(step3_data.manual_publications)
    
        # Combine all publications
        all_publications = bibtex_publications + manual_publications
    
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
                             publications=bibtex_publications,
                             manual_publications=manual_publications,
                             all_publications=all_publications,
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
            wxr_content = _generate_wxr_content(
                user, site, step1_data, step2_data, step3_data, step4_data,
                current_app.config['UPLOAD_FOLDER']
            )
    
            # Create filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"wordpress_export_{site.id}_{timestamp}.wxr"
    
            # Store in session for download
            session['wxr_data'] = wxr_content
            session['wxr_filename'] = filename
    
            # Parse BibTeX publications
            bibtex_publications = []
            if step3_data and step3_data.bibtex_content:
                try:
                    bibtex_publications = parse_bibtex(step3_data.bibtex_content)
                except Exception as e:
                    print(f"Error parsing BibTeX: {e}")
                    bibtex_publications = []
    
            # Get manual publications
            manual_publications = []
            if step3_data:
                manual_publications = list(step3_data.manual_publications)
    
            # Combine all publications
            all_publications = bibtex_publications + manual_publications
    
            gallery_images = []
            if step4_data:
                gallery_images = step4_data.get_gallery_images()
    
            return render_template('wizard/download.html',
                                 site=site,
                                 filename=filename,
                                 has_publications=bool(all_publications),
                                 publication_count=len(all_publications),
                                 has_gallery=bool(gallery_images),
                                 gallery_count=len(gallery_images))
    
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
        
        # Create file-like object
        output = BytesIO()
        output.write(wxr_data.encode('utf-8'))
        output.seek(0)
        
        # Send file
        return send_file(
            output,
            mimetype='application/xml',
            as_attachment=True,
            download_name=filename
        )


def _generate_wxr_content(user, site, step1_data, step2_data, step3_data, step4_data, upload_folder):
    """
    Generate WXR content as properly formatted XML string.
    
    Returns:
        String containing valid WXR XML
    """
    import os
    from utils import get_uploaded_file_path
    
    # Start XML document
    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0"',
        '    xmlns:excerpt="http://wordpress.org/export/1.2/excerpt/"',
        '    xmlns:content="http://purl.org/rss/1.0/modules/content/"',
        '    xmlns:wfw="http://wellformedweb.org/CommentAPI/"',
        '    xmlns:dc="http://purl.org/dc/elements/1.1/"',
        '    xmlns:wp="http://wordpress.org/export/1.2/">',
        '  <channel>',
        f'    <title>{_escape_xml(site.site_name)}</title>',
        '    <link>https://example.com</link>',
        f'    <description>WordPress site for {_escape_xml(user.full_name)}</description>',
        '    <language>en-us</language>',
        f'    <pubDate>{datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")}</pubDate>',
        f'    <lastBuildDate>{datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")}</lastBuildDate>',
        '    <generator>https://github.com/mit-libraries/wordpress-site-generator</generator>',
        '    <wp:wxr_version>1.2</wp:wxr_version>',
        '    <wp:base>https://example.com/index.php/</wp:base>',
        f'    <wp:blog_name>{_escape_xml(site.site_name)}</wp:blog_name>',
        '    <wp:author>',
        f'      <wp:author_login>{_escape_xml(user.username)}</wp:author_login>',
        f'      <wp:author_email>{_escape_xml(user.email or user.username)}</wp:author_email>',
        f'      <wp:author_first_name>{_escape_xml(user.first_name or "")}</wp:author_first_name>',
        f'      <wp:author_last_name>{_escape_xml(user.last_name or "")}</wp:author_last_name>',
        '    </wp:author>',
    ]
    
    post_id_counter = 1
    gallery_post_ids = []
    profile_picture_post_id = None
    
    # Add gallery images as attachments
    if step4_data and step4_data.get_gallery_images():
        for img_filename in step4_data.get_gallery_images():
            image_path = get_uploaded_file_path(site.id, img_filename, upload_folder)
            if os.path.exists(image_path):
                post_id_counter += 1
                xml_lines.extend(_create_attachment_xml(user, img_filename, post_id_counter))
                gallery_post_ids.append(post_id_counter)
    
    # Add profile picture as attachment
    if step4_data and step4_data.profile_picture:
        image_path = get_uploaded_file_path(site.id, step4_data.profile_picture, upload_folder)
        if os.path.exists(image_path):
            post_id_counter += 1
            xml_lines.extend(_create_attachment_xml(user, step4_data.profile_picture, post_id_counter))
            profile_picture_post_id = post_id_counter
    
    # Create Home page
    post_id_counter += 1
    homepage_content = _build_homepage_content(step1_data, step2_data, profile_picture_post_id)
    xml_lines.extend(_create_page_xml(user, 'Home', homepage_content, post_id_counter))
    
    # Create Publications page - parse BOTH BibTeX and manual publications
    bibtex_publications = []
    manual_publications_list = []
    
    if step3_data:
        # Parse BibTeX content if present
        if step3_data.bibtex_content:
            try:
                bibtex_publications = parse_bibtex(step3_data.bibtex_content)
            except Exception as e:
                print(f"Error parsing BibTeX: {e}")
                bibtex_publications = []
        
        # Get manually added publications
        if step3_data.manual_publications:
            manual_publications_list = list(step3_data.manual_publications)
    
    # Create Publications page if we have any publications
    if bibtex_publications or manual_publications_list:
        post_id_counter += 1
        pub_html = _build_publications_html(bibtex_publications, manual_publications_list)
        xml_lines.extend(_create_page_xml(user, 'Publications', pub_html, post_id_counter))
    
    # Create Gallery page
    if gallery_post_ids:
        post_id_counter += 1
        gallery_html = _build_gallery_html(gallery_post_ids)
        xml_lines.extend(_create_page_xml(user, 'Gallery', gallery_html, post_id_counter))
    
    # Close XML document
    xml_lines.extend([
        '  </channel>',
        '</rss>',
    ])
    
    return '\n'.join(xml_lines)


def _escape_xml(text):
    """Escape special XML characters"""
    if not text:
        return ''
    return (str(text)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&apos;'))


def _create_attachment_xml(user, filename, post_id):
    """Create XML lines for an attachment item"""
    return [
        '    <item>',
        f'      <title>{_escape_xml(filename)}</title>',
        '      <description></description>',
        f'      <wp:post_id>{post_id}</wp:post_id>',
        '      <wp:status>inherit</wp:status>',
        '      <wp:post_type>attachment</wp:post_type>',
        '      <wp:post_parent>0</wp:post_parent>',
        f'      <wp:attachment_url>https://example.com/uploads/{_escape_xml(filename)}</wp:attachment_url>',
        f'      <dc:creator>{_escape_xml(user.username)}</dc:creator>',
        f'      <pubDate>{datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")}</pubDate>',
        f'      <wp:post_date>{datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")}</wp:post_date>',
        f'      <wp:post_date_gmt>{datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")}</wp:post_date_gmt>',
        '    </item>',
    ]


def _create_page_xml(user, title, content, post_id):
    """Create XML lines for a page item"""
    return [
        '    <item>',
        f'      <title>{_escape_xml(title)}</title>',
        f'      <wp:post_id>{post_id}</wp:post_id>',
        '      <wp:status>publish</wp:status>',
        '      <wp:post_type>page</wp:post_type>',
        '      <wp:post_parent>0</wp:post_parent>',
        '      <wp:menu_order>0</wp:menu_order>',
        '      <wp:is_sticky>0</wp:is_sticky>',
        f'      <content:encoded><![CDATA[{content}]]></content:encoded>',
        f'      <dc:creator>{_escape_xml(user.username)}</dc:creator>',
        f'      <pubDate>{datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")}</pubDate>',
        f'      <wp:post_date>{datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")}</wp:post_date>',
        f'      <wp:post_date_gmt>{datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")}</wp:post_date_gmt>',
        '    </item>',
    ]


def _build_homepage_content(step1_data, step2_data, profile_picture_post_id=None):
    """Build HTML content for homepage using Gutenberg blocks"""
    content_parts = []
    
    # Profile picture if available
    if profile_picture_post_id:
        content_parts.append(f'<!-- wp:image {{"id":{profile_picture_post_id},"sizeSlug":"large","linkDestination":"none"}} -->')
        content_parts.append('<figure class="wp-block-image size-large"><img src="https://example.com/uploads/profile.jpg" alt="Profile Picture" class="wp-image-{}" /></figure>'.format(profile_picture_post_id))
        content_parts.append('<!-- /wp:image -->')
        content_parts.append('')
    
    # Title/Role
    if step1_data.title_role:
        content_parts.append('<!-- wp:heading {"level":2} -->')
        content_parts.append('<h2 class="wp-block-heading">{}</h2>'.format(_escape_xml(step1_data.title_role)))
        content_parts.append('<!-- /wp:heading -->')
        content_parts.append('')
    
    # Contact info section
    contact_parts = []
    if step1_data.department:
        contact_parts.append('<strong>Department:</strong> {}'.format(_escape_xml(step1_data.department)))
    if step1_data.field_of_study:
        contact_parts.append('<strong>Field of Study:</strong> {}'.format(_escape_xml(step1_data.field_of_study)))
    if step1_data.email:
        contact_parts.append('<strong>Email:</strong> <a href="mailto:{}">{}</a>'.format(_escape_xml(step1_data.email), _escape_xml(step1_data.email)))
    if step1_data.office_address:
        contact_parts.append('<strong>Office:</strong> {}'.format(_escape_xml(step1_data.office_address)))
    if step1_data.phone_number:
        contact_parts.append('<strong>Phone:</strong> {}'.format(_escape_xml(step1_data.phone_number)))
    
    if contact_parts:
        content_parts.append('<!-- wp:paragraph -->')
        content_parts.append('<p class="wp-block-paragraph">{}</p>'.format('<br />'.join(contact_parts)))
        content_parts.append('<!-- /wp:paragraph -->')
        content_parts.append('')
    
    # Biography
    if step2_data and step2_data.biography:
        content_parts.append('<!-- wp:heading {"level":3} -->')
        content_parts.append('<h3 class="wp-block-heading">About</h3>')
        content_parts.append('<!-- /wp:heading -->')
        content_parts.append('')
        content_parts.append('<!-- wp:paragraph -->')
        content_parts.append('<p class="wp-block-paragraph">{}</p>'.format(_escape_xml(step2_data.biography)))
        content_parts.append('<!-- /wp:paragraph -->')
    
    return '\n'.join(content_parts)


def _build_publications_html(publications, manual_publications=None):
    """Build HTML content for publications page using Gutenberg blocks"""
    content_parts = []
    
    # Heading
    content_parts.append('<!-- wp:heading {"level":2} -->')
    content_parts.append('<h2 class="wp-block-heading">Publications</h2>')
    content_parts.append('<!-- /wp:heading -->')
    content_parts.append('')
    
    all_pubs = list(publications) if publications else []
    
    # Add manual publications
    if manual_publications:
        for manual_pub in manual_publications:
            pub_dict = manual_pub.to_dict()
            all_pubs.append(pub_dict)
    
    if not all_pubs:
        content_parts.append('<!-- wp:paragraph -->')
        content_parts.append('<p class="wp-block-paragraph">No publications listed.</p>')
        content_parts.append('<!-- /wp:paragraph -->')
        return '\n'.join(content_parts)
    
    # Build list using paragraph blocks instead of list block for better compatibility
    for pub in all_pubs:
        formatted = format_publication_html(pub)
        content_parts.append('<!-- wp:paragraph -->')
        content_parts.append('<p class="wp-block-paragraph">{}</p>'.format(formatted))
        content_parts.append('<!-- /wp:paragraph -->')
    
    return '\n'.join(content_parts)


def _build_gallery_html(gallery_post_ids):
    """Build HTML content for gallery page using Gutenberg blocks"""
    content_parts = []
    
    # Heading
    content_parts.append('<!-- wp:heading {"level":2} -->')
    content_parts.append('<h2 class="wp-block-heading">Gallery</h2>')
    content_parts.append('<!-- /wp:heading -->')
    content_parts.append('')
    
    if not gallery_post_ids:
        content_parts.append('<!-- wp:paragraph -->')
        content_parts.append('<p class="wp-block-paragraph">No gallery images.</p>')
        content_parts.append('<!-- /wp:paragraph -->')
        return '\n'.join(content_parts)
    
    # Gallery block with proper JSON
    ids_string = ','.join(str(id) for id in gallery_post_ids)
    gallery_json = '{{"ids":[{}],"columns":3,"size":"large","linkTo":"none"}}'.format(ids_string)
    
    content_parts.append('<!-- wp:gallery {} -->'.format(gallery_json))
    content_parts.append('<figure class="wp-block-gallery has-nested-images columns-3 is-cropped">')
    content_parts.append('<ul class="blocks-gallery-grid">')
    
    for post_id in gallery_post_ids:
        content_parts.append('<li class="blocks-gallery-item"><figure><img src="https://example.com/uploads/image{}.jpg" alt="" class="wp-image-{}" /></figure></li>'.format(post_id, post_id))
    
    content_parts.append('</ul>')
    content_parts.append('</figure>')
    content_parts.append('<!-- /wp:gallery -->')
    
    return '\n'.join(content_parts)
