import os
import uuid
import logging
from flask import redirect, url_for, flash, request, abort
from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.sqla.filters import FilterEqual
from flask_login import current_user
from markupsafe import Markup
from wtforms import SelectField, FileField

from app.config import settings
from app.models.document import Document, DocStatus
from app.models.school import School, Syllabus, Class, Subject
from app.models.user import User

logger = logging.getLogger(__name__)

if not os.path.exists(settings.UPLOAD_FOLDER):
    os.makedirs(settings.UPLOAD_FOLDER)


class SecureModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and getattr(current_user, 'is_superuser', False)

    def inaccessible_callback(self, name, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('admin_login', next=request.url))
        abort(403)


class DocumentView(SecureModelView):
    create_template = 'create_document.html'
    edit_template = 'edit_document.html'

    form_excluded_columns = ['chunks', 'file_path', 'error', 'created_at']
    column_exclude_list = ['chunks', 'file_path', 'error']

    form_extra_fields = {
        'file': FileField('Upload PDF (Overrides URL)')
    }

    column_list = ['display_name', 'school_name', 'class_name', 'subject', 'status']
    column_labels = {
        'school_name': 'College Name',
        'class_name': 'Class',
        'display_name': 'Title'
    }
    column_searchable_list = ['display_name', 'school_name']
    
    column_filters = [
        FilterEqual(Document.school_name, 'College Name'),
        'syllabus', 'class_name', 'subject', 'status'
    ]

    column_formatters = {
        'source_url': lambda v, c, m, p: Markup(f'<a href="{m.source_url}" target="_blank">Link</a>') if m.source_url else "",
        'status': lambda v, c, m, p: Markup(
            f'<span class="label label-{"success" if m.status == "COMPLETED" else "danger" if m.status == "FAILED" else "warning"}">{m.status}</span>'
        )
    }

    form_overrides = {
        'school_name': SelectField,
        'syllabus': SelectField,
        'class_name': SelectField,
        'subject': SelectField,
        'status': SelectField
    }
    
    form_args = {
        'school_name': {'label': 'College Name', 'choices': []},
        'syllabus': {'label': 'Syllabus', 'choices': []},
        'class_name': {'label': 'Class', 'choices': []},
        'subject': {'label': 'Subject', 'choices': []},
        'status': {'choices': [(s.value, s.name) for s in DocStatus]}
    }

    def _populate_choices(self, form):
        try:
            schools = self.session.query(School.name).distinct().order_by(School.name).all()
            syllabi = self.session.query(Syllabus.name).distinct().order_by(Syllabus.name).all()
            classes = self.session.query(Class.name).distinct().order_by(Class.name).all()
            subjects = self.session.query(Subject.name).distinct().order_by(Subject.name).all()

            form.school_name.choices = [(s[0], s[0]) for s in schools]
            form.syllabus.choices = [(s[0], s[0]) for s in syllabi]
            form.class_name.choices = [(c[0], c[0]) for c in classes]
            form.subject.choices = [(s[0], s[0]) for s in subjects]
        except Exception:
            pass

    def create_form(self, obj=None):
        form = super(DocumentView, self).create_form(obj)
        self._populate_choices(form)
        return form

    def edit_form(self, obj=None):
        form = super(DocumentView, self).edit_form(obj)
        self._populate_choices(form)
        return form

    def on_model_delete(self, model):
        """
        Triggered when a document is deleted via the Admin Panel.
        Deletes the associated PDF file from the disk.
        """
        if model.file_path and os.path.exists(model.file_path):
            try:
                os.remove(model.file_path)
                logger.info(f"Deleted file: {model.file_path}")
            except OSError as e:
                logger.error(f"Error deleting file {model.file_path}: {e}")
                
    def on_model_change(self, form, model, is_created):
        file_data = form.file.data
        model._should_ingest = False
        
        if not model.id:
            model.id = uuid.uuid4()

        def normalize(val):
            return str(val).strip() if val else ""

        if file_data and hasattr(file_data, 'filename') and file_data.filename:
            try:
                ext = file_data.filename.split('.')[-1] if '.' in file_data.filename else 'pdf'
                new_filename = f"{model.id}.{ext}"
                new_file_path = os.path.join(settings.UPLOAD_FOLDER, new_filename)

                if not is_created and model.file_path and model.file_path != new_file_path:
                    if os.path.exists(model.file_path):
                        try: os.remove(model.file_path)
                        except OSError: pass

                file_data.save(new_file_path)
                model.file_path = new_file_path
                model.source_url = None
                model._should_ingest = True
            except Exception as e:
                raise ValueError(f"Failed to save file: {str(e)}")

        elif not is_created:
            old_url = normalize(form.source_url.object_data)
            new_url = normalize(form.source_url.data)

            if old_url != new_url:
                if model.file_path and os.path.exists(model.file_path):
                    try: os.remove(model.file_path)
                    except OSError: pass
                
                model.file_path = None
                model._should_ingest = True

        elif is_created:
            model._should_ingest = True

        if model._should_ingest:
            model.status = DocStatus.PENDING
            model.error = None
        else:
            if form.status.object_data:
                model.status = form.status.object_data

    def after_model_change(self, form, model, is_created):
        if getattr(model, '_should_ingest', False):
            try:
                from app.worker.tasks import ingest_pdf_task
                ingest_pdf_task.delay(str(model.id))
                flash("Document saved. Ingestion started.", "info")
            except Exception:
                flash("Saved, but background worker failed to start.", "warning")


class SchoolView(SecureModelView):
    column_labels = {'name': 'College Name'}
    form_columns = ['name']
    column_list = ['name', 'syllabi', 'classes', 'subjects']
    column_searchable_list = ['name']

class SchoolRelatedView(SecureModelView):
    column_labels = {'school': 'College', 'name': 'Name'}
    form_columns = ['name', 'school']
    column_list = ['name', 'school']
    column_filters = ['school.name']
    column_searchable_list = ['name']
    form_args = {'school': {'label': 'College'}}

class UserView(SecureModelView):
    column_exclude_list = ['password_hash']
    can_create = False