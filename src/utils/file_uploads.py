import os
from flask import current_app, url_for
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf'}


# --- Utility Functions ---

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_extension(filename: str) -> str:
    return filename.rsplit('.', 1)[1].lower()


def sanitize_path_component(component: str) -> str:
    return secure_filename(component.lower())


def build_file_path(*path_parts: str) -> str:
    """Create and return the full path inside the UPLOAD_FOLDER"""
    base_path = current_app.config['UPLOAD_FOLDER']
    full_path = os.path.join(base_path, *path_parts)
    os.makedirs(full_path, exist_ok=True)
    return full_path


def save_file(file, directory: str, filename: str) -> str:
    """Save file and return public URL path"""
    filepath = os.path.join(directory, filename)
    file.save(filepath)
    relative_path = os.path.relpath(filepath, start=current_app.static_folder)
    return url_for('static', filename=relative_path.replace(os.sep, '/'), _external=True)


# --- Core Service Class ---

class CompanyDocumentsService:
    def __init__(self):
        pass

    def save_logo(self, file, company_id: str) -> str:
        """Save company logo and return its public URL"""
        if not allowed_file(file.filename):
            raise ValueError("Invalid file type")

        ext = get_file_extension(file.filename)
        filename = f"company_{company_id}.{ext}"
        target_dir = build_file_path("logos")

        return save_file(file, target_dir, filename)

    def save_verification_document(
            self,
            file,
            company_name: str,
            company_id: str,
            document_id: str,
            doc_type: str
    ) -> str:
        """Save a verification document and return its public URL"""
        if not allowed_file(file.filename):
            raise ValueError("Invalid file type")

        ext = get_file_extension(file.filename)
        filename = f"verification_{company_id}_{document_id}.{ext}"
        safe_company = sanitize_path_component(company_name)
        safe_doc_type = sanitize_path_component(doc_type)
        target_dir = build_file_path(safe_company, safe_doc_type)

        return save_file(file, target_dir, filename)

    def company_document_reader(self, document_id: str, company_id: str):
        # TODO: implement reader logic
        pass

    def company_document_saver(self, file_contents, document_id: str, company_id: str):
        # TODO: implement writer logic
        pass


# --- Public API: Legacy-style function interface ---

_service = CompanyDocumentsService()


def save_company_logo(file, company_id):
    return _service.save_logo(file, company_id)


def save_verification_file(file, company_name, company_id, document_id, doc_type):
    return _service.save_verification_document(file, company_name, company_id, document_id, doc_type)
