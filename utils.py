import os
import uuid
from werkzeug.utils import secure_filename
import bibtexparser


def get_environment_user_data():
    """
    Extract user data from environment variables set by web server.
    
    Supported environment variables:
    - REMOTE_USER (required): username
    - HTTP_X_REMOTE_USER: username alternative
    - HTTP_X_MAIL: email address
    - HTTP_X_FIRSTNAME: first name
    - HTTP_X_LASTNAME: last name
    - HTTP_X_DEPARTMENT: department
    """
    user_data = {}
    
    user_data['username'] = os.environ.get('REMOTE_USER') or os.environ.get('HTTP_X_REMOTE_USER')
    user_data['email'] = os.environ.get('HTTP_X_MAIL')
    user_data['first_name'] = os.environ.get('HTTP_X_FIRSTNAME')
    user_data['last_name'] = os.environ.get('HTTP_X_LASTNAME')
    user_data['department'] = os.environ.get('HTTP_X_DEPARTMENT')
    
    return user_data


def allowed_file(filename):
    """Check if file extension is allowed"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(file, site_id, upload_folder):
    """
    Save uploaded file and return the filename.
    
    Args:
        file: FileStorage object from Flask
        site_id: WordPress site ID
        upload_folder: Path to upload folder
        
    Returns:
        Secure filename string or None
    """
    if not file or file.filename == '':
        return None
    
    if not allowed_file(file.filename):
        return None
    
    site_upload_dir = os.path.join(upload_folder, str(site_id))
    os.makedirs(site_upload_dir, exist_ok=True)
    
    ext = secure_filename(file.filename).rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4()}.{ext}"
    
    filepath = os.path.join(site_upload_dir, unique_filename)
    file.save(filepath)
    
    return unique_filename


def get_uploaded_file_path(site_id, filename, upload_folder):
    """Get full path to uploaded file"""
    return os.path.join(upload_folder, str(site_id), filename)


def delete_uploaded_file(site_id, filename, upload_folder):
    """Delete an uploaded file"""
    filepath = get_uploaded_file_path(site_id, filename, upload_folder)
    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False

def parse_bibtex(bibtex_content):
    """
    Parse BibTeX content and return a list of publication dictionaries.
    Uses bibtexparser library for more robust parsing.
    
    Args:
        bibtex_content: String containing BibTeX entries
        
    Returns:
        List of dictionaries, each representing a publication
    """
    publications = []
    
    try:
        import bibtexparser
        from bibtexparser.bparser import BibTexParser
        
        # Parse the BibTeX content
        parser = BibTexParser(common_strings=True)
        parser.ignore_nonstandard_types = False
        bibtex_database = bibtexparser.loads(bibtex_content, parser=parser)
        
        # Convert entries to our format
        for entry in bibtex_database.entries:
            pub_dict = {
                'key': entry.get('ID', ''),
                'type': entry.get('ENTRYTYPE', '').lower(),
                'title': entry.get('title', ''),
                'author': entry.get('author', ''),
                'year': entry.get('year', ''),
                'journal': entry.get('journal', ''),
                'booktitle': entry.get('booktitle', ''),
                'publisher': entry.get('publisher', ''),
                'volume': entry.get('volume', ''),
                'pages': entry.get('pages', ''),
                'doi': entry.get('doi', ''),
                'url': entry.get('url', '')
            }
            
            # Only add if we have at least a title
            if pub_dict['title']:
                publications.append(pub_dict)
        
        return publications
    
    except ImportError:
        # Fallback to regex parsing if bibtexparser is not available
        return _parse_bibtex_regex(bibtex_content)


def _parse_bibtex_regex(bibtex_content):
    """
    Fallback regex-based BibTeX parser.
    
    Args:
        bibtex_content: String containing BibTeX entries
        
    Returns:
        List of dictionaries, each representing a publication
    """
    import re
    
    publications = []
    
    # Split entries by @ symbol - more robust approach
    # Find all @type{...} blocks
    pattern = r'@(\w+)\s*\{\s*([^,\n]+),\s*([\s\S]*?)\n\s*\}'
    
    matches = re.finditer(pattern, bibtex_content, re.IGNORECASE)
    
    for match in matches:
        entry_type = match.group(1).lower()
        entry_key = match.group(2).strip()
        entry_content = match.group(3)
        
        pub_dict = {
            'key': entry_key,
            'type': entry_type,
            'title': '',
            'author': '',
            'year': '',
            'journal': '',
            'booktitle': '',
            'publisher': '',
            'volume': '',
            'pages': '',
            'doi': '',
            'url': ''
        }
        
        # Parse individual fields more carefully
        # Match: field = {value} or field = "value" or field = value
        field_pattern = r'(\w+)\s*=\s*(?:\{([^}]*)\}|"([^"]*)"|([^,\n}]*))'
        
        field_matches = re.finditer(field_pattern, entry_content, re.IGNORECASE)
        
        for field_match in field_matches:
            field_name = field_match.group(1).lower()
            # Get value from one of the three groups (braces, quotes, or plain)
            field_value = field_match.group(2) or field_match.group(3) or field_match.group(4)
            field_value = field_value.strip() if field_value else ''
            
            if field_name in pub_dict:
                pub_dict[field_name] = field_value
        
        # Only add if we have at least a title
        if pub_dict['title']:
            publications.append(pub_dict)
    
    return publications


def format_publication_html(publication):
    """
    Format a publication dictionary as HTML.
    
    Args:
        publication: Dictionary with publication data
        
    Returns:
        HTML string
    """
    html_parts = []
    
    if publication.get('author'):
        html_parts.append(publication['author'] + '.')
    
    if publication.get('title'):
        html_parts.append(f" \"{publication['title']}.\"")
    
    if publication.get('journal'):
        html_parts.append(f" <em>{publication['journal']}</em>")
    elif publication.get('booktitle'):
        html_parts.append(f" In <em>{publication['booktitle']}</em>")
    
    if publication.get('publisher'):
        html_parts.append(f" {publication['publisher']}")
    
    if publication.get('year'):
        html_parts.append(f" ({publication['year']})")
    
    if publication.get('doi'):
        html_parts.append(f" <a href='https://doi.org/{publication['doi']}' target='_blank'>DOI</a>")
    elif publication.get('url'):
        html_parts.append(f" <a href='{publication['url']}' target='_blank'>Link</a>")
    
    return ''.join(html_parts)
