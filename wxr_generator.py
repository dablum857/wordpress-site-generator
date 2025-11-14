import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element, SubElement, ElementTree
from datetime import datetime
import os
from utils import get_uploaded_file_path, parse_bibtex, format_publication_html


# Define namespaces
NAMESPACES = {
    'excerpt': 'http://wordpress.org/export/1.2/excerpt/',
    'content': 'http://purl.org/rss/1.0/modules/content/',
    'wfw': 'http://wellformedweb.org/CommentAPI/',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'wp': 'http://wordpress.org/export/1.2/',
}

# Register namespaces to prevent ns0, ns1, etc.
for prefix, uri in NAMESPACES.items():
    ET.register_namespace(prefix, uri)


def generate_wxr_file(user, site, step1_data, step2_data, step3_data, step4_data, upload_folder):
    """
    Generate WordPress XML (WXR) export file.
    
    Args:
        user: User model instance
        site: WordPressSite model instance
        step1_data: Step1PersonalInfo model instance
        step2_data: Step2Biography model instance
        step3_data: Step3Publications model instance
        step4_data: Step4Gallery model instance
        upload_folder: Path to upload folder
        
    Returns:
        ElementTree object
    """
    
    # Create root RSS element
    rss = Element('rss')
    rss.set('version', '2.0')
    # Set namespace declarations correctly
    rss.set('xmlns:excerpt', NAMESPACES['excerpt'])
    rss.set('xmlns:content', NAMESPACES['content'])
    rss.set('xmlns:wfw', NAMESPACES['wfw'])
    rss.set('xmlns:dc', NAMESPACES['dc'])
    rss.set('xmlns:wp', NAMESPACES['wp'])
    
    channel = SubElement(rss, 'channel')
    
    # Channel metadata
    _add_channel_metadata(channel, site, user)
    
    # Track post IDs for relationships
    post_id_counter = [1]
    image_info = {}
    
    # Add gallery images as attachments
    gallery_post_ids = []
    if step4_data and step4_data.get_gallery_images():
        for img_filename in step4_data.get_gallery_images():
            image_path = get_uploaded_file_path(site.id, img_filename, upload_folder)
            if os.path.exists(image_path):
                post_id_counter[0] += 1
                _create_attachment_item(
                    channel, user, img_filename, image_path, post_id_counter[0]
                )
                gallery_post_ids.append(post_id_counter[0])
                image_info[img_filename] = post_id_counter[0]
    
    # Add profile picture as attachment
    profile_picture_post_id = None
    if step4_data and step4_data.profile_picture:
        image_path = get_uploaded_file_path(site.id, step4_data.profile_picture, upload_folder)
        if os.path.exists(image_path):
            post_id_counter[0] += 1
            _create_attachment_item(
                channel, user, step4_data.profile_picture, 
                image_path, post_id_counter[0]
            )
            profile_picture_post_id = post_id_counter[0]
            image_info[step4_data.profile_picture] = post_id_counter[0]
    
    # Create Home page (from step 1 and 2)
    post_id_counter[0] += 1
    homepage_content = _build_homepage_content(step1_data, step2_data, profile_picture_post_id)
    _create_page_item(channel, user, 'Home', homepage_content, post_id_counter[0])
    
    # Create Publications page (from step 3)
    if step3_data and step3_data.bibtex_content:
        publications = parse_bibtex(step3_data.bibtex_content)
        if publications:
            post_id_counter[0] += 1
            pub_html = _build_publications_html(publications)
            _create_page_item(channel, user, 'Publications', pub_html, post_id_counter[0])
    
    # Create Gallery page (from step 4 gallery images)
    if gallery_post_ids:
        post_id_counter[0] += 1
        gallery_html = _build_gallery_html(gallery_post_ids)
        _create_page_item(channel, user, 'Gallery', gallery_html, post_id_counter[0])
    
    return ElementTree(rss)


def _add_channel_metadata(channel, site, user):
    """Add channel metadata to WXR"""
    title = SubElement(channel, 'title')
    title.text = site.site_name
    
    link = SubElement(channel, 'link')
    link.text = 'https://example.com'
    
    description = SubElement(channel, 'description')
    description.text = f"WordPress site for {user.full_name}"
    
    language = SubElement(channel, 'language')
    language.text = 'en-us'
    
    pubDate = SubElement(channel, 'pubDate')
    pubDate.text = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')
    
    lastBuildDate = SubElement(channel, 'lastBuildDate')
    lastBuildDate.text = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')
    
    generator = SubElement(channel, 'generator')
    generator.text = 'https://github.com/mit-libraries/wordpress-site-generator'
    
    # IMPORTANT: WordPress requires the WXR version
    wp_wxr_version = SubElement(channel, f'{{{NAMESPACES["wp"]}}}wxr_version')
    wp_wxr_version.text = '1.2'
    
    # WordPress namespaced elements
    wp_base = SubElement(channel, f'{{{NAMESPACES["wp"]}}}base')
    wp_base.text = 'https://example.com/index.php/'
    
    wp_blog_name = SubElement(channel, f'{{{NAMESPACES["wp"]}}}blog_name')
    wp_blog_name.text = site.site_name
    
    # Add author
    wp_author = SubElement(channel, f'{{{NAMESPACES["wp"]}}}author')
    author_login = SubElement(wp_author, f'{{{NAMESPACES["wp"]}}}author_login')
    author_login.text = user.username
    author_email = SubElement(wp_author, f'{{{NAMESPACES["wp"]}}}author_email')
    author_email.text = user.email or user.username
    author_first_name = SubElement(wp_author, f'{{{NAMESPACES["wp"]}}}author_first_name')
    author_first_name.text = user.first_name or ''
    author_last_name = SubElement(wp_author, f'{{{NAMESPACES["wp"]}}}author_last_name')
    author_last_name.text = user.last_name or ''


def _create_page_item(channel, user, title, content, post_id):
    """Create a WordPress page item"""
    item = SubElement(channel, 'item')
    
    item_title = SubElement(item, 'title')
    item_title.text = title
    
    wp_post_id = SubElement(item, f'{{{NAMESPACES["wp"]}}}post_id')
    wp_post_id.text = str(post_id)
    
    wp_status = SubElement(item, f'{{{NAMESPACES["wp"]}}}status')
    wp_status.text = 'publish'
    
    wp_post_type = SubElement(item, f'{{{NAMESPACES["wp"]}}}post_type')
    wp_post_type.text = 'page'
    
    wp_post_parent = SubElement(item, f'{{{NAMESPACES["wp"]}}}post_parent')
    wp_post_parent.text = '0'
    
    wp_menu_order = SubElement(item, f'{{{NAMESPACES["wp"]}}}menu_order')
    wp_menu_order.text = '0'
    
    wp_is_sticky = SubElement(item, f'{{{NAMESPACES["wp"]}}}is_sticky')
    wp_is_sticky.text = '0'
    
    # Content - CDATA for safety
    item_content = SubElement(item, f'{{{NAMESPACES["content"]}}}encoded')
    item_content.text = content
    
    # Author
    item_creator = SubElement(item, f'{{{NAMESPACES["dc"]}}}creator')
    item_creator.text = user.username
    
    # Pubdate
    item_pubdate = SubElement(item, 'pubDate')
    item_pubdate.text = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')
    
    # Post date
    wp_post_date = SubElement(item, f'{{{NAMESPACES["wp"]}}}post_date')
    wp_post_date.text = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    
    wp_post_date_gmt = SubElement(item, f'{{{NAMESPACES["wp"]}}}post_date_gmt')
    wp_post_date_gmt.text = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    
    return item


def _create_attachment_item(channel, user, filename, filepath, post_id):
    """Create a WordPress attachment item"""
    item = SubElement(channel, 'item')
    
    item_title = SubElement(item, 'title')
    item_title.text = filename
    
    item_description = SubElement(item, 'description')
    item_description.text = ''
    
    wp_post_id = SubElement(item, f'{{{NAMESPACES["wp"]}}}post_id')
    wp_post_id.text = str(post_id)
    
    wp_status = SubElement(item, f'{{{NAMESPACES["wp"]}}}status')
    wp_status.text = 'inherit'
    
    wp_post_type = SubElement(item, f'{{{NAMESPACES["wp"]}}}post_type')
    wp_post_type.text = 'attachment'
    
    wp_post_parent = SubElement(item, f'{{{NAMESPACES["wp"]}}}post_parent')
    wp_post_parent.text = '0'
    
    wp_attachment_url = SubElement(item, f'{{{NAMESPACES["wp"]}}}attachment_url')
    wp_attachment_url.text = f'https://example.com/uploads/{filename}'
    
    # Author
    item_creator = SubElement(item, f'{{{NAMESPACES["dc"]}}}creator')
    item_creator.text = user.username
    
    # Pubdate
    item_pubdate = SubElement(item, 'pubDate')
    item_pubdate.text = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')
    
    # Post date
    wp_post_date = SubElement(item, f'{{{NAMESPACES["wp"]}}}post_date')
    wp_post_date.text = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    
    wp_post_date_gmt = SubElement(item, f'{{{NAMESPACES["wp"]}}}post_date_gmt')
    wp_post_date_gmt.text = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    
    return item


def _build_homepage_content(step1_data, step2_data, profile_picture_post_id=None):
    """Build HTML content for homepage"""
    content_parts = []
    
    # Profile picture if available
    if profile_picture_post_id:
        content_parts.append(
            f'<!-- wp:image {{"id":{profile_picture_post_id},"align":"center","width":300,"height":300}} -->\n'
            f'<figure class="wp-block-image aligncenter" style="width:300px;height:300px;"><img src="https://example.com/uploads/profile.jpg" alt="Profile Picture" class="wp-image-{profile_picture_post_id}" width="300" height="300" /></figure>\n'
            f'<!-- /wp:image -->'
        )
    
    # Title/Role
    if step1_data.title_role:
        content_parts.append(f'<!-- wp:heading -->\n<h2>{step1_data.title_role}</h2>\n<!-- /wp:heading -->')
    
    # Contact info section
    contact_parts = []
    if step1_data.department:
        contact_parts.append(f'<strong>Department:</strong> {step1_data.department}')
    if step1_data.field_of_study:
        contact_parts.append(f'<strong>Field of Study:</strong> {step1_data.field_of_study}')
    if step1_data.email:
        contact_parts.append(f'<strong>Email:</strong> <a href="mailto:{step1_data.email}">{step1_data.email}</a>')
    if step1_data.office_address:
        contact_parts.append(f'<strong>Office:</strong> {step1_data.office_address}')
    if step1_data.phone_number:
        contact_parts.append(f'<strong>Phone:</strong> {step1_data.phone_number}')
    
    if contact_parts:
        content_parts.append('<!-- wp:paragraph -->')
        content_parts.append('<p>' + '<br>'.join(contact_parts) + '</p>')
        content_parts.append('<!-- /wp:paragraph -->')
    
    # Biography
    if step2_data and step2_data.biography:
        content_parts.append('<!-- wp:heading -->\n<h3>About</h3>\n<!-- /wp:heading -->')
        content_parts.append(f'<!-- wp:paragraph -->\n<p>{step2_data.biography}</p>\n<!-- /wp:paragraph -->')
    
    return '\n'.join(content_parts)


def _build_publications_html(publications):
    """Build HTML content for publications page"""
    content_parts = ['<!-- wp:heading -->\n<h2>Publications</h2>\n<!-- /wp:heading -->']
    
    if not publications:
        content_parts.append('<!-- wp:paragraph -->\n<p>No publications listed.</p>\n<!-- /wp:paragraph -->')
        return '\n'.join(content_parts)
    
    content_parts.append('<!-- wp:list -->\n<ol>')
    for pub in publications:
        formatted = format_publication_html(pub)
        content_parts.append(f'<li>{formatted}</li>')
    content_parts.append('</ol>\n<!-- /wp:list -->')
    
    return '\n'.join(content_parts)


def _build_gallery_html(gallery_post_ids):
    """Build HTML content for gallery page"""
    content_parts = ['<!-- wp:heading -->\n<h2>Gallery</h2>\n<!-- /wp:heading -->']
    
    content_parts.append('<!-- wp:gallery {"ids":[' + ','.join(str(id) for id in gallery_post_ids) + ']} -->')
    content_parts.append('<figure class="wp-block-gallery has-nested-images columns-default is-cropped">')
    content_parts.append('<ul class="blocks-gallery-grid">')
    
    for post_id in gallery_post_ids:
        content_parts.append(
            f'<li class="blocks-gallery-item"><figure><img src="https://example.com/uploads/image{post_id}.jpg" alt="" data-id="{post_id}" data-full-url="https://example.com/uploads/image{post_id}.jpg" data-link="https://example.com/?p={post_id}" class="wp-image-{post_id}" /></figure></li>'
        )
    
    content_parts.append('</ul></figure>')
    content_parts.append('<!-- /wp:gallery -->')
    
    return '\n'.join(content_parts)
