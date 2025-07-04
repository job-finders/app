import os
from werkzeug.utils import secure_filename
from flask import current_app, url_for

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf'}


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_company_logo(file, company_id):
    """Save company logo and return its URL"""
    if not allowed_file(file.filename):
        raise ValueError("Invalid file event_type")

    # Generate unique filename
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"company_{company_id}.{ext}"

    # Determine save path
    upload_dir = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, filename)

    # Save file
    file.save(filepath)

    # Return URL path
    return url_for('static', filename=f"uploads/{filename}", _external=True)


def save_verification_file(file, company_name: str, company_id: str, document_id: str, doc_type: str):
    """Save verification document under company and doc_type directories and return its URL"""
    if not allowed_file(file.filename):
        raise ValueError("Invalid file type")

    # Sanitize inputs to avoid path injection
    safe_company = secure_filename(company_name)
    safe_doc_type = secure_filename(doc_type)

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


