import os
from werkzeug.utils import secure_filename
from flask import current_app, url_for

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_company_logo(file, company_id):
    """Save company logo and return its URL"""
    if not allowed_file(file.filename):
        raise ValueError("Invalid file type")

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


