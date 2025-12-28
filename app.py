from flask import Flask, jsonify, request, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, time as dtime
from functools import wraps
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret')

db = SQLAlchemy(app)

BUSINESS_START = '08:00'
BUSINESS_END = '17:00'

class Employee(db.Model):
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)
    department = db.Column(db.String)
    email = db.Column(db.String)
    phone = db.Column(db.String)
    hire_date = db.Column(db.Date)
    def as_dict(self):
        return {'id': self.id, 'name': self.name, 'department': self.department, 'email': self.email, 'phone': self.phone, 'hire_date': self.hire_date.isoformat() if self.hire_date else None}

class User(db.Model):
    username = db.Column(db.String, primary_key=True)
    password_hash = db.Column(db.String, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    employee_id = db.Column(db.String, db.ForeignKey('employee.id'))
    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_code = db.Column(db.String, unique=True, nullable=False)
    project_name = db.Column(db.String, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    target_date = db.Column(db.Date, nullable=False)
    extend_date = db.Column(db.Date)
    extend_reason = db.Column(db.String)
    manager_id = db.Column(db.String, db.ForeignKey('employee.id'))
    status = db.Column(db.String, default='Active')
    manager = db.relationship('Employee', backref='managed_projects', lazy=True)
    def as_dict(self):
        return {'id': self.id, 'project_code': self.project_code, 'project_name': self.project_name, 'start_date': self.start_date.isoformat() if self.start_date else None, 'target_date': self.target_date.isoformat() if self.target_date else None, 'extend_date': self.extend_date.isoformat() if self.extend_date else None, 'extend_reason': self.extend_reason, 'manager_id': self.manager_id, 'status': self.status}

class TimeEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String, db.ForeignKey('employee.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    entry_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.String, nullable=False)
    end_time = db.Column(db.String, nullable=False)
    working_hours = db.Column(db.Float, default=0.0)
    overtime_hours = db.Column(db.Float, default=0.0)
    notes = db.Column(db.String)
    employee = db.relationship('Employee', backref='time_entries', lazy=True)
    project = db.relationship('Project', backref='time_entries', lazy=True)
    def as_dict(self):
        return {'id': self.id, 'employee_id': self.employee_id, 'project_id': self.project_id, 'entry_date': self.entry_date.isoformat(), 'start_time': self.start_time, 'end_time': self.end_time, 'working_hours': round(self.working_hours, 2), 'overtime_hours': round(self.overtime_hours, 2), 'notes': self.notes}

# helpers

def parse_time(tstr: str) -> dtime: return datetime.strptime(tstr, '%H:%M').time()

def hours(delta): return delta.total_seconds() / 3600.0

def compute_hours(entry_date: date, start_str: str, end_str: str):
    start_t = parse_time(start_str); end_t = parse_time(end_str)
    start_dt = datetime.combine(entry_date, start_t); end_dt = datetime.combine(entry_date, end_t)
    if end_dt <= start_dt: return 0.0, 0.0
    b_start = datetime.combine(entry_date, parse_time(BUSINESS_START))
    b_end = datetime.combine(entry_date, parse_time(BUSINESS_END))
    overtime_before = 0.0
    if start_dt < b_start:
        early_end = min(end_dt, b_start)
        if early_end > start_dt: overtime_before = hours(early_end - start_dt)
    office_hours = 0.0
    office_start = max(start_dt, b_start); office_end = min(end_dt, b_end)
    if office_end > office_start: office_hours = hours(office_end - office_start)
    overtime_after = 0.0
    if end_dt > b_end:
        late_start = max(start_dt, b_end)
        if end_dt > late_start: overtime_after = hours(end_dt - late_start)
    overtime_total = max(0.0, overtime_before) + max(0.0, overtime_after)
    total_working = max(0.0, office_hours) + overtime_total
    return round(total_working, 2), round(overtime_total, 2)

# payload

def payload():
    data = request.get_json(silent=True)
    if not data: data = request.form.to_dict() if request.form else request.args.to_dict()
    return data or {}

# decorators

def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            if request.path.startswith('/api/'): return jsonify({'error': 'Unauthorized'}), 401
            return redirect(url_for('login', next=request.path))
        return view_func(*args, **kwargs)
    return wrapper

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get('is_admin'):
            if request.path.startswith('/api/'): return jsonify({'error': 'Forbidden'}), 403
            return redirect(url_for('time_entries_page'))
        return view_func(*args, **kwargs)
    return wrapper

# pages
@app.route('/')
@login_required
def home(): return render_template('index.html')

@app.route('/employees')
@login_required
@admin_required
def employees_page(): return render_template('employees.html')

@app.route('/projects')
@login_required
@admin_required
def projects_page(): return render_template('projects.html')

@app.route('/time-entries')
@login_required
def time_entries_page(): return render_template('time_entries.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username','').strip(); password = request.form.get('password','')
        user = User.query.get(username)
        if user and user.check_password(password):
            session['user'] = username; session['is_admin'] = bool(user.is_admin); session['employee_id'] = user.employee_id
            return redirect(request.args.get('next') or url_for('home'))
        return render_template('login.html', error='Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

# public API
@app.route('/api/public/me')
@login_required
def public_me(): return jsonify({'username': session.get('user'), 'employee_id': session.get('employee_id')})

@app.route('/api/public/projects')
@login_required
def public_projects():
    projects = Project.query.filter(Project.status=='Active').order_by(Project.project_code).all()
    return jsonify([{'id': p.id, 'project_code': p.project_code, 'project_name': p.project_name} for p in projects])

@app.route('/api/public/employees')
@login_required
def public_employees():
    emps = Employee.query.order_by(Employee.id).all()
    return jsonify([{'id': e.id, 'name': e.name} for e in emps])

# employees API
@app.route('/api/employees', methods=['GET'])
@login_required
@admin_required
def list_employees(): return jsonify([e.as_dict() for e in Employee.query.order_by(Employee.id).all()])

@app.route('/api/employees', methods=['POST'])
@login_required
@admin_required
def create_employee():
    data = payload()
    if not data or 'id' not in data or 'name' not in data: return jsonify({'error': 'id and name are required'}), 400
    hire_date = None
    if data.get('hire_date'):
        try: hire_date = datetime.strptime(data['hire_date'],'%Y-%m-%d').date()
        except Exception: hire_date = None
    e = Employee(id=data['id'], name=data['name'], department=data.get('department'), email=data.get('email'), phone=data.get('phone'), hire_date=hire_date)
    db.session.add(e)
    try: db.session.commit()
    except Exception as ex:
        db.session.rollback(); return jsonify({'error': str(ex)}), 400
    return jsonify(e.as_dict()), 201

@app.route('/api/employees/<emp_id>')
@login_required
@admin_required
def get_employee(emp_id): e = Employee.query.get_or_404(emp_id); return jsonify(e.as_dict())

@app.route('/api/employees/<emp_id>', methods=['PUT'])
@login_required
@admin_required
def update_employee(emp_id):
    e = Employee.query.get_or_404(emp_id); data = payload()
    for f in ['name','department','email','phone']:
        if f in data: setattr(e, f, data[f])
    if 'hire_date' in data:
        e.hire_date = datetime.strptime(data['hire_date'],'%Y-%m-%d').date() if data['hire_date'] else None
    db.session.commit(); return jsonify(e.as_dict())

@app.route('/api/employees/<emp_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_employee(emp_id):
    from sqlalchemy import func
    cnt = db.session.query(func.count(TimeEntry.id)).filter(TimeEntry.employee_id==emp_id).scalar()
    if cnt and cnt>0: return jsonify({'error': 'Cannot delete employee with existing time entries'}), 400
    e = Employee.query.get_or_404(emp_id); db.session.delete(e); db.session.commit(); return jsonify({'status': 'deleted'})

# projects API
@app.route('/api/projects', methods=['GET'])
@login_required
@admin_required
def list_projects(): return jsonify([p.as_dict() for p in Project.query.order_by(Project.project_code).all()])

@app.route('/api/projects', methods=['POST'])
@login_required
@admin_required
def create_project():
    data = payload(); req = ['project_code','project_name','start_date','target_date']
    if not data or not all(k in data and data[k] for k in req): return jsonify({'error': f'Required fields: {req}'}), 400
    def parse_date(s):
        try: return datetime.strptime(s,'%Y-%m-%d').date()
        except Exception: return None
    p = Project(project_code=data['project_code'], project_name=data['project_name'], start_date=parse_date(data['start_date']), target_date=parse_date(data['target_date']), extend_date=parse_date(data.get('extend_date')) if data.get('extend_date') else None, extend_reason=data.get('extend_reason'), manager_id=data.get('manager_id'), status=data.get('status','Active'))
    db.session.add(p)
    try: db.session.commit()
    except Exception as ex:
        db.session.rollback(); return jsonify({'error': str(ex)}), 400
    return jsonify(p.as_dict()), 201

@app.route('/api/projects/<int:pid>')
@login_required
@admin_required
def get_project(pid): p = Project.query.get_or_404(pid); return jsonify(p.as_dict())

@app.route('/api/projects/<int:pid>', methods=['PUT'])
@login_required
@admin_required
def update_project(pid):
    p = Project.query.get_or_404(pid); data = payload()
    for f in ['project_code','project_name','extend_reason','manager_id','status']:
        if f in data: setattr(p, f, data[f])
    for df in ['start_date','target_date','extend_date']:
        if df in data: setattr(p, df, datetime.strptime(data[df],'%Y-%m-%d').date() if data[df] else None)
    db.session.commit(); return jsonify(p.as_dict())

@app.route('/api/projects/<int:pid>', methods=['DELETE'])
@login_required
@admin_required
def delete_project(pid):
    from sqlalchemy import func
    cnt = db.session.query(func.count(TimeEntry.id)).filter(TimeEntry.project_id==pid).scalar()
    if cnt and cnt>0: return jsonify({'error': 'Cannot delete project with existing time entries'}), 400
    p = Project.query.get_or_404(pid); db.session.delete(p); db.session.commit(); return jsonify({'status': 'deleted'})

# time entries API
@app.route('/api/time-entries')
@login_required
def list_time_entries(): entries = TimeEntry.query.order_by(TimeEntry.entry_date.desc(), TimeEntry.id.desc()).all(); return jsonify([t.as_dict() for t in entries])

@app.route('/api/time-entries', methods=['POST'])
@login_required
def create_time_entry():
    data = payload(); req = ['entry_date','start_time','end_time']
    is_admin = bool(session.get('is_admin'))
    if is_admin:
        req_admin = ['employee_id','project_id']
        if not data or not all(k in data and data[k] for k in req+req_admin): return jsonify({'error': f'Required fields: {req+req_admin}'}), 400
        emp_id = data['employee_id']; proj_id_raw = data['project_id']
    else:
        if not data or 'project_id' not in data or 'employee_id' not in data: return jsonify({'error': 'employee_id and project_id are required'}), 400
        emp_id = data['employee_id']; proj_id_raw = data['project_id']
    emp = Employee.query.get(emp_id)
    if not emp: return jsonify({'error': 'Invalid employee_id'}), 400
    try: pid = int(proj_id_raw)
    except Exception: return jsonify({'error': 'project_id must be an integer'}), 400
    proj = Project.query.get(pid)
    if not proj: return jsonify({'error': 'Invalid project_id'}), 400
    try: entry_date = datetime.strptime(data['entry_date'],'%Y-%m-%d').date()
    except Exception: return jsonify({'error': 'Invalid entry_date'}), 400
    working, overtime = compute_hours(entry_date, data['start_time'], data['end_time'])
    t = TimeEntry(employee_id=emp.id, project_id=proj.id, entry_date=entry_date, start_time=data['start_time'], end_time=data['end_time'], working_hours=working, overtime_hours=overtime, notes=data.get('notes'))
    db.session.add(t)
    try: db.session.commit()
    except Exception as ex:
        db.session.rollback(); return jsonify({'error': str(ex)}), 400
    return jsonify(t.as_dict()), 201

@app.route('/api/time-entries/<int:tid>')
@login_required
def get_time_entry(tid): t = TimeEntry.query.get_or_404(tid); return jsonify(t.as_dict())

@app.route('/api/time-entries/<int:tid>', methods=['PUT'])
@login_required
def update_time_entry(tid):
    t = TimeEntry.query.get_or_404(tid); data = payload(); is_admin = bool(session.get('is_admin'))
    updatable = ['start_time','end_time','notes','entry_date'] + (['employee_id','project_id'] if is_admin else [])
    for f in updatable:
        if f in data:
            if f=='entry_date': t.entry_date = datetime.strptime(data['entry_date'],'%Y-%m-%d').date() if data['entry_date'] else t.entry_date
            else: setattr(t, f, data[f])
    emp = Employee.query.get(t.employee_id)
    if not emp: return jsonify({'error':'Invalid employee_id'}), 400
    try: pid = int(t.project_id)
    except Exception: return jsonify({'error':'project_id must be an integer'}), 400
    proj = Project.query.get(pid)
    if not proj: return jsonify({'error':'Invalid project_id'}), 400
    t.working_hours, t.overtime_hours = compute_hours(t.entry_date, t.start_time, t.end_time)
    db.session.commit(); return jsonify(t.as_dict())

@app.route('/api/time-entries/<int:tid>', methods=['DELETE'])
@login_required
@admin_required
def delete_time_entry(tid): t = TimeEntry.query.get_or_404(tid); db.session.delete(t); db.session.commit(); return jsonify({'status':'deleted'})

# dashboard
@app.route('/api/dashboard')
@login_required
def dashboard():
    today = date.today(); month_start = date(today.year, today.month, 1)
    totals = {'employees': Employee.query.count(), 'projects': Project.query.count()}
    proj_summaries = []; overdue_projects = 0; active_projects = 0
    for p in Project.query.all():
        effective_target = p.extend_date or p.target_date
        days_gone = (today - p.start_date).days if today >= p.start_date else 0
        days_remaining = (effective_target - today).days if effective_target and effective_target >= today else 0
        overdue_days = (today - effective_target).days if effective_target and today > effective_target else 0
        is_overdue = bool(effective_target and today > effective_target)
        overdue_projects += 1 if is_overdue else 0
        active_projects += 1 if not is_overdue else 0
        entries = TimeEntry.query.filter(TimeEntry.project_id==p.id, TimeEntry.entry_date>=month_start, TimeEntry.entry_date<=today).all()
        total_working = sum(e.working_hours for e in entries)
        total_overtime = sum(e.overtime_hours for e in entries)
        proj_summaries.append({'project_id': p.id, 'project_code': p.project_code, 'project_name': p.project_name, 'days_gone': days_gone, 'days_remaining_to_target': days_remaining, 'overdue_days': overdue_days, 'total_working_hours_this_month': round(total_working, 2), 'total_overtime_hours_this_month': round(total_overtime, 2), 'status': p.status})
    entries_month = TimeEntry.query.filter(TimeEntry.entry_date>=month_start, TimeEntry.entry_date<=today).all()
    totals['active_projects'] = active_projects; totals['overdue_projects'] = overdue_projects
    totals['working_hours_this_month'] = round(sum(e.working_hours for e in entries_month), 2)
    totals['overtime_hours_this_month'] = round(sum(e.overtime_hours for e in entries_month), 2)
    overtime_by_emp = {}
    for e in entries_month:
        overtime_by_emp[e.employee_id] = overtime_by_emp.get(e.employee_id, 0.0) + e.overtime_hours
    top_employees = sorted([{'employee_id': k, 'overtime_hours': round(v, 2)} for k, v in overtime_by_emp.items()], key=lambda x: x['overtime_hours'], reverse=True)[:5]
    return jsonify({'totals': totals, 'projects': proj_summaries, 'top_employees_by_overtime': top_employees, 'business_hours': {'start': BUSINESS_START, 'end': BUSINESS_END}})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.get('admin'):
            u = User(username='admin', is_admin=True); u.set_password('admin123'); db.session.add(u)
        if not Employee.query.get('E004'):
            e4 = Employee(id='E004', name='Ismail', department='IT', email='ismail@example.com', phone='1004'); db.session.add(e4)
        if not User.query.get('Ismail'):
            u2 = User(username='Ismail', is_admin=False, employee_id='E004'); u2.set_password('Ismail123'); db.session.add(u2)
        db.session.commit()
    app.run(debug=True)
