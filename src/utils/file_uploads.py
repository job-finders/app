import os
from werkzeug.utils import secure_filename
from flask import current_app, url_for

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf'}


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_company_logo(file, company_id):
    """Save company logo in the 'logos' subfolder and return its URL"""
    if not allowed_file(file.filename):
        raise ValueError("Invalid file type")

    # Extract extension and generate filename
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"company_{company_id}.{ext}"

    # Define the target subfolder: uploads/logos/
    upload_base = current_app.config['UPLOAD_FOLDER']  # Should point to /static/uploads
    logo_folder = os.path.join(upload_base, 'logos')
    os.makedirs(logo_folder, exist_ok=True)

    # Final file path
    filepath = os.path.join(logo_folder, filename)

    # Save the file
    file.save(filepath)

    # Create the URL (static/uploads/logos/company_123.png)
    relative_path = os.path.relpath(filepath, start=current_app.static_folder)
    return url_for('static', filename=relative_path.replace(os.sep, '/'), _external=True)


def save_verification_file(file, company_name: str, company_id: str, document_id: str, doc_type: str):
    """
    Uploaded files must be cached on cloudflare and served from CDN.
    Save verification document under company and doc_type directories and return its URL
    """
    if not allowed_file(file.filename):
        raise ValueError("Invalid file type")

    # Sanitize inputs to avoid path injection
    safe_company = secure_filename(company_name.lower())
    safe_doc_type = secure_filename(doc_type.lower())

    # Generate filename
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"verification_{company_id}_{document_id}.{ext}"

    # Build full directory path
    upload_base = current_app.config['UPLOAD_FOLDER']
    target_dir = os.path.join(upload_base, safe_company, safe_doc_type)
    os.makedirs(target_dir, exist_ok=True)

    # Save file
    filepath = os.path.join(target_dir, filename)
    file.save(filepath)

    # Build URL path relative to /static
    relative_path = os.path.relpath(filepath, start=current_app.static_folder)
    return url_for('static', filename=relative_path.replace(os.sep, '/'), _external=True)


class CompanyDocumentsService():
    def __init__(self):
        pass

    def company_document_reader(document_id: str, company_id: str):
        """

        :param file:
        :param company_id:
        :return:
        """
        pass

    def company_document_saver(file_contents, document_id: str, company_id: str):
        """

        :param file_contents:
        :param document_id:
        :param company_id:
        :return:
        """
        pass


