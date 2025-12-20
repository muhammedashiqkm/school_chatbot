import os
import uuid
from flask import redirect, url_for, flash
from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.sqla.filters import FilterLike, FilterEqual
from flask_login import current_user
from markupsafe import Markup
from wtforms import SelectField, FileField
from app.db.session import SessionLocal
from app.models.document import Document
from app.models.school import School, Syllabus, Class, Subject
from app.models.user import User
from app.config import settings


if not os.path.exists(settings.UPLOAD_FOLDER):
    os.makedirs(settings.UPLOAD_FOLDER)


class SecureModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_superuser

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('admin_login'))


class DocumentView(SecureModelView):
    
    form_excluded_columns = ['chunks', 'file_path'] 
    column_exclude_list = ['chunks']

    form_extra_fields = {
        'file': FileField('Upload PDF')
    }

    column_filters = [
        FilterEqual(Document.school_name, 'College Name'),
        'syllabus', 'class_name', 'subject', 'status'
    ]
    column_labels = {
        'school_name': 'College Name',
        'class_name': 'Class'
    }

    column_formatters = {
        'source_url': lambda v, c, m, p: Markup(f'<a href="{m.source_url}" target="_blank">Link</a>') if m.source_url else "",
        'status': lambda v, c, m, p: Markup(f'<b>{m.status}</b>')
    }

    form_overrides = {
        'school_name': SelectField,
        'syllabus': SelectField,
        'class_name': SelectField,
        'subject': SelectField,
        'status': SelectField
    }
    
    form_args = {
        'school_name': {'label': 'College Name'},
        'syllabus': {'label': 'Syllabus'},
        'class_name': {'label': 'Class'},
        'subject': {'label': 'Subject'},
        'status': {'choices': [('PENDING', 'PENDING'), ('PROCESSING', 'PROCESSING'), ('COMPLETED', 'COMPLETED'), ('FAILED', 'FAILED')]}
    }

    def _populate_choices(self, form):
        db = SessionLocal()
        try:
            schools = db.query(School.name).distinct().all()
            syllabi = db.query(Syllabus.name).distinct().all()
            classes = db.query(Class.name).distinct().all()
            subjects = db.query(Subject.name).distinct().all()

            form.school_name.choices = [(s[0], s[0]) for s in schools]
            form.syllabus.choices = [(s[0], s[0]) for s in syllabi]
            form.class_name.choices = [(c[0], c[0]) for c in classes]
            form.subject.choices = [(sub[0], sub[0]) for sub in subjects]
        finally:
            db.close()

    def create_form(self, obj=None):
        form = super(DocumentView, self).create_form(obj)
        self._populate_choices(form)
        return form

    def edit_form(self, obj=None):
        form = super(DocumentView, self).edit_form(obj)
        self._populate_choices(form)
        return form

    def on_model_change(self, form, model, is_created):
        file_data = form.file.data
        
        if file_data:
            if not model.id:
                model.id = uuid.uuid4()
            
            ext = file_data.filename.split('.')[-1] if '.' in file_data.filename else 'pdf'
            new_filename = f"{model.id}.{ext}"
            new_file_path = os.path.join(settings.UPLOAD_FOLDER, new_filename)

            if not is_created and model.file_path:
                if os.path.exists(model.file_path):
                    try:
                        os.remove(model.file_path)
                        print(f"Deleted old file: {model.file_path}")
                    except OSError:
                        pass 

            try:
                file_data.save(new_file_path)
                model.file_path = new_file_path
                model.source_url = None 
            except Exception as e:
                raise Exception(f"Failed to save file: {str(e)}")

        model.status = 'PENDING'

    def after_model_change(self, form, model, is_created):
        from app.worker.tasks import ingest_pdf_task
        ingest_pdf_task.delay(str(model.id))

class SchoolView(SecureModelView):
    form_columns = ['name']
    column_list = ['name', 'syllabi', 'classes', 'subjects']
    column_labels = {'name': 'College Name'}

class SchoolRelatedView(SecureModelView):
    column_filters = [FilterLike(School.name, 'College Name')]
    column_labels = {'school': 'College Name', 'name': 'Name'}
    form_columns = ['name', 'school']

class UserView(SecureModelView):
    column_exclude_list = ['password_hash']
    can_create = False