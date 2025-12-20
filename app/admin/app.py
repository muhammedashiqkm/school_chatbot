from flask import Flask, redirect, url_for, request
from flask_admin import Admin, AdminIndexView, expose
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from app.db.session import SessionLocal
from app.models.user import User
from app.models.school import School, Syllabus, Class, Subject
from app.models.document import Document
# Import our custom views
from app.admin.views import (
    UserView, 
    SchoolView, 
    SchoolRelatedView, 
    DocumentView
)
from app.config import settings

# ---------------------------------------------------------
# 1. Setup Flask App & Login Manager
# ---------------------------------------------------------
flask_app = Flask(__name__)
flask_app.secret_key = settings.SECRET_KEY

login_manager = LoginManager()
login_manager.init_app(flask_app)
login_manager.login_view = 'admin_login'

# ---------------------------------------------------------
# 2. User Loader Logic
# ---------------------------------------------------------
class AdminUser(UserMixin):
    def __init__(self, id, username, is_superuser):
        self.id = id
        self.username = username
        self.is_superuser = is_superuser

@login_manager.user_loader
def load_user(user_id):
    db = SessionLocal()
    try:
        u = db.query(User).get(int(user_id))
        if u:
            return AdminUser(u.id, u.username, u.is_superuser)
    finally:
        db.close()
    return None

# ---------------------------------------------------------
# 3. Custom Dashboard Index
# ---------------------------------------------------------
class MyAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        if not current_user.is_authenticated:
            return redirect(url_for('admin_login'))
        return super(MyAdminIndexView, self).index()

# ---------------------------------------------------------
# 4. Auth Routes & Root Redirect
# ---------------------------------------------------------
@flask_app.route('/')
def root():
    return redirect(url_for('admin.index'))

@flask_app.route('/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == username).first()
            
            # Use AuthService to verify hash
            from app.services.auth_service import AuthService
            
            if user and user.is_superuser and AuthService.verify_password(password, user.password_hash):
                login_user(AdminUser(user.id, user.username, user.is_superuser))
                return redirect(url_for('admin.index'))
            else:
                return "Invalid credentials or not a superuser", 401
        finally:
            db.close()
             
    # Simple HTML Login Form
    return """
    <div style="display:flex; justify-content:center; align-items:center; height:100vh; background:#f4f4f4;">
        <form method="POST" style="display:flex; flex-direction:column; gap:15px; padding:30px; background:white; border-radius:8px; box-shadow:0 2px 10px rgba(0,0,0,0.1);">
            <h3 style="margin:0 0 10px 0; text-align:center;">SyllabusQA Admin</h3>
            <input name="username" placeholder="Username" required style="padding:10px; border:1px solid #ddd; border-radius:4px;">
            <input name="password" type="password" placeholder="Password" required style="padding:10px; border:1px solid #ddd; border-radius:4px;">
            <button type="submit" style="padding:10px; background:#007bff; color:white; border:none; border-radius:4px; cursor:pointer; font-weight:bold;">Login</button>
        </form>
    </div>
    """

@flask_app.route('/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('admin_login'))

# ---------------------------------------------------------
# 5. Initialize Admin
# ---------------------------------------------------------
admin = Admin(
    flask_app, 
    name='SyllabusQA', 
    index_view=MyAdminIndexView(),
    url='/dashboard' 
)

# ---------------------------------------------------------
# 6. Register Views
# ---------------------------------------------------------
db_session = SessionLocal()

# User Management
admin.add_view(UserView(User, db_session))

# School Management 
# [FIXED] This must be SchoolView, NOT SchoolRelatedView
admin.add_view(SchoolView(School, db_session))

# Metadata Management
# These use SchoolRelatedView because they have a 'school' relationship
admin.add_view(SchoolRelatedView(Syllabus, db_session))
admin.add_view(SchoolRelatedView(Class, db_session))
admin.add_view(SchoolRelatedView(Subject, db_session))

# Document Management
admin.add_view(DocumentView(Document, db_session))

# ---------------------------------------------------------
# 7. Cleanup
# ---------------------------------------------------------
@flask_app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.close()