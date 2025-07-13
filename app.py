"""Employee Leave Management System (ELMS) – Flask Application"""
"""Key Features to Implement:
User Roles: Admin, Manager, Employee

Authentication & Authorization: Login system using Flask-Login

Functionalities:

Employees: Apply for leave, view status, edit or cancel requests

Managers: Approve/reject leave, filter by date/employee/status

Admin: View full dashboard with metrics and user management

Data Storage: Use SQLite or PostgreSQL (via SQLAlchemy ORM)

Audit Logs: Track actions and maintain user activity logs

UI: Build responsive frontend using Jinja2 templates + Bootstrap

Reports: Generate PDF/CSV reports for leaves by team or month

Deployment: Deploy locally and prepare for cloud deployment (Heroku or Render)"""




#importing of required files to our elms project
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
import os
#configarations of app.py
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///elms.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
#login database
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# user details like id,username,email etc
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    department = db.Column(db.String(50), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_manager = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # requesting a leave
    leave_requests = db.relationship(
        'LeaveRequest',
        foreign_keys='LeaveRequest.employee_id',
        backref=db.backref('employee', lazy=True),
        primaryjoin='User.id == LeaveRequest.employee_id'
    )
    
    # approving a leave request
    approved_requests = db.relationship(
        'LeaveRequest',
        foreign_keys='LeaveRequest.approved_by',
        backref=db.backref('approver', lazy=True),
        primaryjoin='User.id == LeaveRequest.approved_by'
    )
#type of leave which we are going to request
class LeaveType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    days_allowed = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text)
    
    # storing the leave requests data in a relationship database 
    leave_requests = db.relationship('LeaveRequest', backref='leave_type', lazy=True)
#details of leave request of an employee like id,employee_id,leave_type_id etc
class LeaveRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    leave_type_id = db.Column(db.Integer, db.ForeignKey('leave_type.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    days_requested = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    approval_date = db.Column(db.DateTime)
    comments = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
#employee leave balance details like total_days,used_days,remaining_days etc
class LeaveBalance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    leave_type_id = db.Column(db.Integer, db.ForeignKey('leave_type.id'), nullable=False)
    total_days = db.Column(db.Integer, nullable=False)
    used_days = db.Column(db.Integer, default=0)
    remaining_days = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    
    # storing details of a employee leave request in a Relationships database
    employee = db.relationship('User', backref='leave_balances')
    leave_type = db.relationship('LeaveType', backref='balances')
#manager's login phase
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#admin section , finding whether the user is present or not using decorated functions
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Access denied. Admin privileges required.', 'error')
            return redirect('admin_panel')
        return f(*args, **kwargs)
    return decorated_function
#manager section,test whether the user is manager or not using decorated functions
def manager_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not (current_user.is_admin or current_user.is_manager):
            flash('Access denied. Manager privileges required.', 'error')
            return redirect('dashboard')
        return f(*args, **kwargs)
    return decorated_function

#route to templates
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect('dashboard')
    return render_template('login.html')
#login section to login with a specific username and password
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        #loging with correct password 
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect('dashboard')
        else:
            flash('Invalid username or password')
        return redirect('login')  # Redirecting to login section back if fails
    
    return render_template('login.html')
#logout section or page of user
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))
#dashbord section to select required task 
@app.route('/dashboard')
@login_required
def dashboard():
    #containing users recent request leave
    recent_requests = LeaveRequest.query.filter_by(employee_id=current_user.id)\
        .order_by(LeaveRequest.created_at.desc()).limit(5).all()
    
    #pending approvals of an employee by the manager or an admin
    pending_approvals = []
    if current_user.is_manager or current_user.is_admin:
        pending_approvals = LeaveRequest.query.filter_by(status='pending')\
            .order_by(LeaveRequest.created_at.desc()).limit(5).all()
    
    #leave balance of current user is mentioned
    leave_balances = LeaveBalance.query.filter_by(
        employee_id=current_user.id, 
        year=datetime.now().year
    ).all()
    #returning the  above templates 
    return render_template('dashboard.html',
                         recent_requests=recent_requests,
                         pending_approvals=pending_approvals,
                         leave_balances=leave_balances)
#requesting a leave to the manager with specified details 
@app.route('/request_leave', methods=['GET', 'POST'])
@login_required
def request_leave():
    if request.method == 'POST':
        leave_type_id = request.form['leave_type_id']
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
        reason = request.form['reason']
        
        #no.of days requesting is calculated
        days_requested = (end_date - start_date).days + 1
        
        #leave balance of an employee leave 
        leave_balance = LeaveBalance.query.filter_by(
            employee_id=current_user.id,
            leave_type_id=leave_type_id,
            year=datetime.now().year
        ).first()
        #check for leave balance to reaquest a leave 
        if leave_balance and leave_balance.remaining_days >= days_requested:
            leave_request = LeaveRequest(
                employee_id=current_user.id,
                leave_type_id=leave_type_id,
                start_date=start_date,
                end_date=end_date,
                days_requested=days_requested,
                reason=reason
            )
            #leave request database session 
            db.session.add(leave_request)
            db.session.commit()
            flash('Leave request submitted successfully!', 'success')
            return redirect('request_leave')
        else:
            flash('Insufficient leave balance!', 'error')
    #selecting leave request type of an employee
    leave_types = LeaveType.query.all()
    return render_template('request_leave.html', leave_types=leave_types)
#route for my_request page by current user
@app.route('/my_requests')
@login_required
def my_requests():
    requests = LeaveRequest.query.filter_by(employee_id=current_user.id)\
        .order_by(LeaveRequest.created_at.desc()).all()
    return render_template('my_requests.html', requests=requests)
#leave request approving of an employee by the manager
@app.route('/approve_requests')
@login_required
@manager_required
def approve_requests():
    pending_requests = LeaveRequest.query.filter_by(status='pending')\
        .order_by(LeaveRequest.created_at.desc()).all()
    return render_template('approve_requests.html', requests=pending_requests)
#leave request details & status of an employee
@app.route('/approve_leave/<int:request_id>')
@login_required
@manager_required
def approve_leave(request_id):
    leave_request = LeaveRequest.query.get_or_404(request_id)
    leave_request.status = 'approved'
    leave_request.approved_by = current_user.id
    leave_request.approval_date = datetime.utcnow()
    
    #leave balance is updated
    leave_balance = LeaveBalance.query.filter_by(
        employee_id=leave_request.employee_id,
        leave_type_id=leave_request.leave_type_id,
        year=datetime.now().year
    ).first()
    #leave balance days checking 
    if leave_balance:
        leave_balance.used_days += leave_request.days_requested
        leave_balance.remaining_days -= leave_request.days_requested
    #getting approval for leave request
    db.session.commit()
    flash('Leave request approved successfully!', 'success')
    return redirect('approve_requests')
#rejecting a leave request by the manager  
@app.route('/reject_leave/<int:request_id>')
@login_required
@manager_required
def reject_leave(request_id):
    leave_request = LeaveRequest.query.get_or_404(request_id)
    leave_request.status = 'rejected'
    leave_request.approved_by = current_user.id
    leave_request.approval_date = datetime.utcnow()
    #outputting the rejection of current leave request
    db.session.commit()
    flash('Leave request rejected successfully!', 'success')
    return redirect('approve_requests.html')
#checking whether the leave request is approved or not in the admin_panel
@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    total_employees = User.query.count()
    total_requests = LeaveRequest.query.count()
    pending_requests = LeaveRequest.query.filter_by(status='pending').count()
    approved_requests = LeaveRequest.query.filter_by(status='approved').count()
    #returning render_template according to request  
    return render_template('admin_panel.html',
                         total_employees=total_employees,
                         total_requests=total_requests,
                         pending_requests=pending_requests,
                         approved_requests=approved_requests)

@app.route('/admin/employees')
@login_required
@admin_required
def manage_employees():
    employees = User.query.all()
    return render_template('add_user.html', employees=employees)

@app.route('/admin/reports')
@login_required
@admin_required
def reports():
    # Generate various reports
    department_stats = db.session.query(
    User.department, 
    db.func.count(LeaveRequest.id).label('total_requests')
    ).join(LeaveRequest, User.id == LeaveRequest.employee_id).group_by(User.department).all()  
    
    monthly_stats = db.session.query(
        db.func.strftime('%Y-%m', LeaveRequest.created_at).label('month'),
        db.func.count(LeaveRequest.id).label('total_requests')
    ).group_by(db.func.strftime('%Y-%m', LeaveRequest.created_at)).all()
    
    return render_template('reports.html', 
                         department_stats=department_stats,
                         monthly_stats=monthly_stats)

@app.route('/api/leave_status/<int:request_id>')
@login_required
def get_leave_status(request_id):
    leave_request = LeaveRequest.query.get_or_404(request_id)
    
    # Check if user can access this request
    if (leave_request.employee_id != current_user.id and 
        not current_user.is_admin and 
        not current_user.is_manager):
        return jsonify({'error': 'Access denied'}), 403
    
    return jsonify({
        'id': leave_request.id,
        'status': leave_request.status,
        'updated_at': leave_request.updated_at.isoformat(),
        'approved_by': leave_request.approver.username if leave_request.approver else None,
        'approval_date': leave_request.approval_date.isoformat() if leave_request.approval_date else None
    })

@app.route('/api/dashboard_stats')
@login_required
def dashboard_stats():
    stats = {
        'total_requests': LeaveRequest.query.filter_by(employee_id=current_user.id).count(),
        'pending_requests': LeaveRequest.query.filter_by(employee_id=current_user.id, status='pending').count(),
        'approved_requests': LeaveRequest.query.filter_by(employee_id=current_user.id, status='approved').count(),
        'rejected_requests': LeaveRequest.query.filter_by(employee_id=current_user.id, status='rejected').count(),
    }
    
    if current_user.is_admin or current_user.is_manager:
        stats['pending_approvals'] = LeaveRequest.query.filter_by(status='pending').count()
    
    return jsonify(stats)

def create_sample_data():
    """Create sample data for testing"""
    # Create leave types
    leave_types = [
        LeaveType(name='Annual Leave', days_allowed=30, description='Yearly vacation days'),
        LeaveType(name='Sick Leave', days_allowed=15, description='Medical leave days'),
        LeaveType(name='Personal Leave', days_allowed=10, description='Personal time off'),
        LeaveType(name='Maternity Leave', days_allowed=90, description='Maternity leave days'),
    ]
    
    for lt in leave_types:
        if not LeaveType.query.filter_by(name=lt.name).first():
            db.session.add(lt)
    
    # Create admin user
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            email='admin@company.com',
            password_hash=generate_password_hash('admin123'),
            first_name='Admin',
            last_name='User',
            department='IT',
            is_admin=True,
            is_manager=True
        )
        db.session.add(admin)
    
    # Create sample employee
    if not User.query.filter_by(username='employee').first():
        employee = User(
            username='employee',
            email='employee@company.com',
            password_hash=generate_password_hash('emp123'),
            first_name='John',
            last_name='Doe',
            department='HR'
        )
        db.session.add(employee)
    
    db.session.commit()
    
    # Create leave balances for the current year
    users = User.query.all()
    leave_types = LeaveType.query.all()
    current_year = datetime.now().year
    
    for user in users:
        for leave_type in leave_types:
            if not LeaveBalance.query.filter_by(
                employee_id=user.id,
                leave_type_id=leave_type.id,
                year=current_year
            ).first():
                balance = LeaveBalance(
                    employee_id=user.id,
                    leave_type_id=leave_type.id,
                    total_days=leave_type.days_allowed,
                    used_days=0,
                    remaining_days=leave_type.days_allowed,
                    year=current_year
                )
                db.session.add(balance)
    
    db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_sample_data()
    
    app.run(debug=True)