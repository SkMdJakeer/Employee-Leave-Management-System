# Employee Leave Management System (ELMS)

A Flask-based web application for managing employee leave requests with admin, manager, and employee roles.

## Features
- Secure login system
- Role-based access (Admin/Manager/Employee)
- Leave request submission and approval
- Leave balance tracking
- Real-time dashboards
- Responsive design

## Installation
1. Clone the repo:
   git clone https://github.com/yourusername/elms.git
   cd elms

2. Create virtual environment:
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate

3. Install dependencies:
   pip install flask flask-sqlalchemy flask-login

4. Run the app:
   python app.py

## Usage
Access at: http://localhost:5000

Demo logins:
- Admin: admin/admin123
- Employee: employee/emp123

## File Structure
templates/
  add_user.html
  admin_panel.html
  admin_users.html  
  approve_requests.html
  base.html
  dashboard.html
  employee_dashboard.html
  login.html
  manager_dashboard.html
  my_requests.html
  reports.html
  request_leave.html
app.py

## Technologies
- Python/Flask backend
- SQLite database
- Bootstrap frontend
- Chart.js for visuals

## License
MIT
