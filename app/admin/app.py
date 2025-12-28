import os
import logging
from flask import Flask, redirect, url_for, request, render_template, flash
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.menu import MenuLink
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from sqlalchemy.orm import scoped_session

from app.config import settings
from app.db.session import SessionLocal
from app.models.user import User
from app.models.school import School, Syllabus, Class, Subject
from app.models.document import Document
from app.admin.views import UserView, SchoolView, SchoolRelatedView, DocumentView
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

def create_admin_app():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(base_dir, 'templates')

    flask_app = Flask(
        __name__, 
        template_folder=template_dir
    )
    flask_app.secret_key = settings.SECRET_KEY

    db_session = scoped_session(SessionLocal)

    @flask_app.teardown_appcontext
    def shutdown_session(exception=None):
        db_session.remove()

    login_manager = LoginManager()
    login_manager.init_app(flask_app)
    login_manager.login_view = 'admin_login'

    class AdminUser(UserMixin):
        def __init__(self, user):
            self.id = user.id
            self.username = user.username
            self.is_superuser = user.is_superuser

    @login_manager.user_loader
    def load_user(user_id):
        try:
            u = db_session.query(User).get(int(user_id))
            return AdminUser(u) if u else None
        except:
            return None

    class MyAdminIndexView(AdminIndexView):
        @expose('/')
        def index(self):
            if not current_user.is_authenticated:
                return redirect(url_for('admin_login'))
            return super(MyAdminIndexView, self).index()

    @flask_app.route('/')
    def index():
        return redirect(url_for('admin.index'))

    @flask_app.route('/login', methods=['GET', 'POST'])
    def admin_login():
        if current_user.is_authenticated:
            return redirect(url_for('admin.index'))

        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            try:
                user = db_session.query(User).filter(User.username == username).first()
                if user and user.is_superuser and AuthService.verify_password(password, user.password_hash):
                    login_user(AdminUser(user))
                    next_page = request.args.get('next')
                    if not next_page or not next_page.startswith('/'):
                        next_page = url_for('admin.index')
                    return redirect(next_page)
                else:
                    flash("Invalid credentials or access denied.", "danger")
            except Exception as e:
                logger.error(f"Login Error: {e}")
                flash("An unexpected error occurred.", "danger")
        
        return render_template('login.html')

    @flask_app.route('/logout')
    @login_required
    def admin_logout():
        logout_user()
        flash("You have been logged out.", "info")
        return redirect(url_for('admin_login'))

    @flask_app.errorhandler(403)
    def forbidden(e):
        return render_template('403.html'), 403

    admin = Admin(
        flask_app, 
        name='SyllabusQA', 
        index_view=MyAdminIndexView(),
        url='/dashboard'
    )

    admin.add_view(UserView(User, db_session))
    admin.add_view(SchoolView(School, db_session))
    admin.add_view(SchoolRelatedView(Syllabus, db_session, category="School Data", name="Syllabi"))
    admin.add_view(SchoolRelatedView(Class, db_session, category="School Data", name="Classes"))
    admin.add_view(SchoolRelatedView(Subject, db_session, category="School Data", name="Subjects"))
    admin.add_view(DocumentView(Document, db_session))

    admin.add_link(MenuLink(name='Logout', category='', url='/admin/logout'))

    return flask_app