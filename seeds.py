from app import app, db, Employee, Project, TimeEntry, compute_hours, User
from datetime import date, timedelta
with app.app_context():
    db.drop_all(); db.create_all()
    e1=Employee(id='E001', name='Alice', department='IT', email='alice@example.com', phone='1001')
    e2=Employee(id='E002', name='Bob', department='Operations', email='bob@example.com', phone='1002')
    e3=Employee(id='E003', name='Carol', department='Finance', email='carol@example.com', phone='1003')
    e4=Employee(id='E004', name='Ismail', department='IT', email='ismail@example.com', phone='1004')
    db.session.add_all([e1,e2,e3,e4])
    u_admin=User(username='admin', is_admin=True); u_admin.set_password('admin123')
    u_ismail=User(username='Ismail', is_admin=False, employee_id='E004'); u_ismail.set_password('Ismail123')
    db.session.add_all([u_admin,u_ismail])
    today=date.today(); start1=date(today.year,today.month,1); target1=start1+timedelta(days=62)
    start2=start1-timedelta(days=15); target2=start1+timedelta(days=45)
    p1=Project(project_code='PRJ001', project_name='Client Portal', start_date=start1, target_date=target1, manager_id='E001', status='Active')
    p2=Project(project_code='PRJ002', project_name='Mobile App', start_date=start2, target_date=target2, manager_id='E002', status='Inactive')
    db.session.add_all([p1,p2]); db.session.commit()
    for offs in [0,1,2]:
        d=start1+timedelta(days=20+offs); work,ot=compute_hours(d,'08:30','17:30')
        db.session.add(TimeEntry(employee_id='E001', project_id=p1.id, entry_date=d, start_time='08:30', end_time='17:30', working_hours=work, overtime_hours=ot, notes='Feature work'))
    for offs in [0,1]:
        d=start1+timedelta(days=18+offs); work,ot=compute_hours(d,'09:00','18:00')
        db.session.add(TimeEntry(employee_id='E002', project_id=p2.id, entry_date=d, start_time='09:00', end_time='18:00', working_hours=work, overtime_hours=ot, notes='Testing'))
    db.session.commit(); print('Database initialized with sample data.')
