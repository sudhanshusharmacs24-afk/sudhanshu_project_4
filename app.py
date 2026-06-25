from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, g
import sqlite3, os, json, random
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'academia-crm-secret-2024'

@app.template_filter('fmtdate')
def fmtdate(s, fmt='%d %b %Y'):
    if not s: return '—'
    try: return datetime.strptime(str(s)[:19], '%Y-%m-%d %H:%M:%S').strftime(fmt)
    except: return str(s)[:10]

@app.template_filter('fmtdatetime')
def fmtdatetime(s): return fmtdate(s, '%d %b %Y, %I:%M %p')

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'crm.db')
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# ─── DB Helpers ───────────────────────────────────────────────────────────────

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
    return db

@app.teardown_appcontext
def close_db(e=None):
    db = getattr(g, '_database', None)
    if db: db.close()

def query(sql, args=(), one=False):
    cur = get_db().execute(sql, args)
    rv = cur.fetchall()
    return (rv[0] if rv else None) if one else rv

def execute(sql, args=()):
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    return cur.lastrowid

def row_to_dict(row):
    if row is None: return None
    return dict(row)

def rows_to_dicts(rows):
    return [dict(r) for r in rows]

# ─── DB Init ──────────────────────────────────────────────────────────────────

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript("""
    CREATE TABLE IF NOT EXISTS institution (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        location TEXT, institution_type TEXT, student_strength INTEGER DEFAULT 0,
        website TEXT, contact_person TEXT, email TEXT, phone TEXT, designation TEXT,
        program_interest TEXT, lead_source TEXT, lead_status TEXT DEFAULT 'New Lead',
        priority_score INTEGER DEFAULT 0, priority_label TEXT DEFAULT 'Medium',
        assigned_to TEXT, notes TEXT, next_action TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS follow_up (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        institution_id INTEGER NOT NULL,
        due_date TEXT NOT NULL, task_type TEXT, description TEXT,
        status TEXT DEFAULT 'Pending',
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(institution_id) REFERENCES institution(id)
    );
    CREATE TABLE IF NOT EXISTS activity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        institution_id INTEGER NOT NULL,
        action TEXT, actor TEXT DEFAULT 'System',
        timestamp TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(institution_id) REFERENCES institution(id)
    );
    """)
    db.commit()
    db.close()

# ─── AI Engine ────────────────────────────────────────────────────────────────

def calculate_priority(inst):
    score = 0
    strength = inst['student_strength'] or 0
    if strength >= 10000: score += 35
    elif strength >= 5000: score += 25
    elif strength >= 2000: score += 15
    else: score += 5

    t = (inst['institution_type'] or '').lower()
    if any(x in t for x in ['iit','nit','iim']): score += 30
    elif 'university' in t: score += 20
    elif 'college' in t: score += 12
    elif 'polytechnic' in t: score += 8

    if inst['program_interest']:
        score += min(len(inst['program_interest'].split(',')) * 5, 20)

    src_scores = {'Referral':15,'Conference':12,'LinkedIn':10,'Website':8,'Cold Outreach':5,'Other':3}
    score += src_scores.get(inst['lead_source'] or '', 3)

    st_scores = {'Negotiation':10,'Proposal Sent':8,'Meeting Scheduled':6,'Contacted':3,'New Lead':0}
    score += st_scores.get(inst['lead_status'] or '', 0)

    score = min(score, 100)
    label = 'High' if score >= 70 else ('Medium' if score >= 40 else 'Low')
    return score, label


def generate_next_action(inst):
    actions = {
        'New Lead': f"Send introductory email to {inst['contact_person'] or 'contact'} about our training programs",
        'Contacted': f"Follow up with {inst['contact_person'] or 'contact'} — schedule a discovery call this week",
        'Meeting Scheduled': f"Prepare customized presentation for {inst['name']} focusing on {inst['program_interest'] or 'their interests'}",
        'Proposal Sent': f"Follow up on the proposal — address queries from {inst['contact_person'] or 'decision maker'}",
        'Negotiation': f"Finalize contract terms with {inst['name']} — check budget and timeline",
        'Closed': f"Onboard {inst['name']} — share welcome kit and assign a delivery manager",
    }
    return actions.get(inst['lead_status'], "Review lead details and plan next steps")


def generate_outreach_message(inst):
    programs = inst['program_interest'] or "technical training programs"
    strength = f"{inst['student_strength']:,}" if inst['student_strength'] else "your"
    contact = inst['contact_person'] or 'Sir/Madam'
    name = inst['name']
    rep = inst['assigned_to'] or 'Sales Team'
    return f"""Dear {contact},

I hope this message finds you well. I'm reaching out regarding an exciting opportunity to enhance technical education at {name}.

With {strength} students, {name} has tremendous potential to lead industry-ready skill development. We specialize in delivering hands-on training in {programs} — programs designed in collaboration with top industry partners.

We've successfully partnered with 50+ institutions across India, and I'd love to explore how we can create similar impact at {name}.

Could we schedule a 30-minute discovery call this week?

Warm regards,
{rep}"""


def generate_suggestions(inst):
    suggestions = []
    created = datetime.strptime(inst['created_at'][:19], '%Y-%m-%d %H:%M:%S')
    days_since = (datetime.utcnow() - created).days
    status = inst['lead_status']

    if status == 'New Lead':
        suggestions += [
            {'icon':'📧','text':f"Send personalized intro email to {inst['contact_person'] or 'contact'} within 24 hours",'urgency':'High'},
            {'icon':'🔗','text':'Connect on LinkedIn and engage with recent institutional posts','urgency':'Medium'},
        ]
    elif status == 'Contacted':
        suggestions += [
            {'icon':'📞','text':'Make a follow-up call if email unanswered for 3+ days','urgency':'High'},
            {'icon':'📅','text':'Propose 3 specific meeting slots for a discovery call','urgency':'High'},
        ]
    elif status == 'Meeting Scheduled':
        suggestions += [
            {'icon':'📊','text':"Research institution's current programs and gaps before meeting",'urgency':'High'},
            {'icon':'🎯','text':'Prepare case studies from similar institutions','urgency':'Medium'},
            {'icon':'📁','text':'Send pre-meeting agenda and company deck','urgency':'Medium'},
        ]
    elif status == 'Proposal Sent':
        suggestions += [
            {'icon':'📞','text':'Schedule proposal review call within 5 business days','urgency':'High'},
            {'icon':'💰','text':'Discuss pricing flexibility or pilot program options','urgency':'Medium'},
        ]
    elif status == 'Negotiation':
        suggestions += [
            {'icon':'⚖️','text':'Loop in management for final pricing decisions','urgency':'High'},
            {'icon':'📝','text':'Share MOU draft with legal-friendly terms','urgency':'High'},
        ]

    if days_since > 14 and status not in ['Closed', 'Lost']:
        suggestions.append({'icon':'⚠️','text':f'Lead inactive for {days_since} days — re-engage with fresh value proposition','urgency':'High'})
    return suggestions

# ─── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def dashboard():
    institutions = rows_to_dicts(query("SELECT * FROM institution"))
    total = len(institutions)
    active = sum(1 for i in institutions if i['lead_status'] not in ['Closed','Lost'])
    meetings = sum(1 for i in institutions if i['lead_status']=='Meeting Scheduled')
    closed = sum(1 for i in institutions if i['lead_status']=='Closed')
    proposals = sum(1 for i in institutions if i['lead_status']=='Proposal Sent')
    negotiations = sum(1 for i in institutions if i['lead_status']=='Negotiation')
    high_priority = sum(1 for i in institutions if i['priority_label']=='High')

    pending_followups = len(query(
        "SELECT id FROM follow_up WHERE status='Pending' AND due_date <= ?",
        [(datetime.utcnow()+timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S')]
    ))

    recent = rows_to_dicts(query("SELECT * FROM institution ORDER BY created_at DESC LIMIT 5"))

    acts = query("""SELECT a.*, i.name as inst_name FROM activity a
                    LEFT JOIN institution i ON a.institution_id=i.id
                    ORDER BY a.timestamp DESC LIMIT 8""")
    recent_activities = rows_to_dicts(acts)

    statuses = ['New Lead','Contacted','Meeting Scheduled','Proposal Sent','Negotiation','Closed']
    pipeline = {s: sum(1 for i in institutions if i['lead_status']==s) for s in statuses}

    source_data = {}
    for i in institutions:
        src = i['lead_source'] or 'Unknown'
        source_data[src] = source_data.get(src, 0) + 1

    return render_template('dashboard.html',
        total=total, active=active, meetings=meetings, closed=closed,
        proposals=proposals, negotiations=negotiations,
        high_priority=high_priority, pending_followups=pending_followups,
        recent=recent, recent_activities=recent_activities,
        pipeline=pipeline, source_data=source_data
    )


@app.route('/leads')
def leads():
    status_filter = request.args.get('status','')
    priority_filter = request.args.get('priority','')
    search = request.args.get('search','')

    sql = "SELECT * FROM institution WHERE 1=1"
    args = []
    if status_filter:
        sql += " AND lead_status=?"; args.append(status_filter)
    if priority_filter:
        sql += " AND priority_label=?"; args.append(priority_filter)
    if search:
        sql += " AND (name LIKE ? OR contact_person LIKE ? OR location LIKE ?)"
        args += [f'%{search}%',f'%{search}%',f'%{search}%']
    sql += " ORDER BY created_at DESC"
    institutions = rows_to_dicts(query(sql, args))
    statuses = ['New Lead','Contacted','Meeting Scheduled','Proposal Sent','Negotiation','Closed']
    return render_template('leads.html', institutions=institutions, statuses=statuses,
                           current_status=status_filter, current_priority=priority_filter, search=search)


@app.route('/leads/add', methods=['GET','POST'])
def add_lead():
    if request.method == 'POST':
        prog_keys = [k for k in request.form if k.startswith('prog_')]
        programs = ', '.join(request.form[k] for k in prog_keys)
        if not programs:
            programs = request.form.get('program_interest','')

        inst = {
            'name': request.form['name'],
            'location': request.form.get('location'),
            'institution_type': request.form.get('institution_type'),
            'student_strength': int(request.form.get('student_strength') or 0),
            'website': request.form.get('website'),
            'contact_person': request.form.get('contact_person'),
            'email': request.form.get('email'),
            'phone': request.form.get('phone'),
            'designation': request.form.get('designation'),
            'program_interest': programs,
            'lead_source': request.form.get('lead_source'),
            'lead_status': request.form.get('lead_status','New Lead'),
            'assigned_to': request.form.get('assigned_to'),
            'notes': request.form.get('notes'),
        }
        score, label = calculate_priority(inst)
        next_action = generate_next_action(inst)

        iid = execute("""INSERT INTO institution
            (name,location,institution_type,student_strength,website,contact_person,
             email,phone,designation,program_interest,lead_source,lead_status,
             priority_score,priority_label,assigned_to,notes,next_action)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (inst['name'],inst['location'],inst['institution_type'],inst['student_strength'],
             inst['website'],inst['contact_person'],inst['email'],inst['phone'],
             inst['designation'],inst['program_interest'],inst['lead_source'],inst['lead_status'],
             score,label,inst['assigned_to'],inst['notes'],next_action))

        execute("INSERT INTO follow_up (institution_id,due_date,task_type,description) VALUES (?,?,?,?)",
                (iid, (datetime.utcnow()+timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'),
                 'Email', f"Send intro email to {inst['contact_person'] or inst['name']}"))
        execute("INSERT INTO activity (institution_id,action,actor) VALUES (?,?,?)",
                (iid, f"Lead created — Status: {inst['lead_status']}, Priority: {label} ({score})", 'System'))

        flash(f"Lead \"{inst['name']}\" added successfully!", 'success')
        return redirect(url_for('lead_detail', id=iid))

    programs = ['Data Science & AI','Web Development','Cloud Computing','Cybersecurity',
                'IoT & Embedded Systems','Machine Learning','DevOps','Python Programming',
                'Java Full Stack','Digital Marketing']
    return render_template('add_lead.html', programs=programs)


@app.route('/leads/<int:id>')
def lead_detail(id):
    inst = row_to_dict(query("SELECT * FROM institution WHERE id=?", [id], one=True))
    if not inst: return "Not found", 404
    suggestions = generate_suggestions(inst)
    outreach = generate_outreach_message(inst)
    follow_ups = rows_to_dicts(query("SELECT * FROM follow_up WHERE institution_id=? ORDER BY due_date", [id]))
    activities = rows_to_dicts(query("SELECT * FROM activity WHERE institution_id=? ORDER BY timestamp DESC", [id]))
    statuses = ['New Lead','Contacted','Meeting Scheduled','Proposal Sent','Negotiation','Closed']
    now = datetime.utcnow()
    return render_template('lead_detail.html', inst=inst, suggestions=suggestions,
                           outreach=outreach, follow_ups=follow_ups,
                           activities=activities, statuses=statuses, now=now.strftime('%Y-%m-%d %H:%M:%S'))


@app.route('/leads/<int:id>/edit', methods=['GET','POST'])
def edit_lead(id):
    inst = row_to_dict(query("SELECT * FROM institution WHERE id=?", [id], one=True))
    if not inst: return "Not found", 404
    if request.method == 'POST':
        old_status = inst['lead_status']
        updated = {
            'name': request.form['name'],
            'location': request.form.get('location'),
            'institution_type': request.form.get('institution_type'),
            'student_strength': int(request.form.get('student_strength') or 0),
            'website': request.form.get('website'),
            'contact_person': request.form.get('contact_person'),
            'email': request.form.get('email'),
            'phone': request.form.get('phone'),
            'designation': request.form.get('designation'),
            'program_interest': request.form.get('program_interest'),
            'lead_source': request.form.get('lead_source'),
            'lead_status': request.form.get('lead_status', inst['lead_status']),
            'assigned_to': request.form.get('assigned_to'),
            'notes': request.form.get('notes'),
        }
        score, label = calculate_priority(updated)
        next_action = generate_next_action(updated)

        execute("""UPDATE institution SET name=?,location=?,institution_type=?,student_strength=?,
            website=?,contact_person=?,email=?,phone=?,designation=?,program_interest=?,
            lead_source=?,lead_status=?,priority_score=?,priority_label=?,assigned_to=?,
            notes=?,next_action=?,updated_at=? WHERE id=?""",
            (updated['name'],updated['location'],updated['institution_type'],updated['student_strength'],
             updated['website'],updated['contact_person'],updated['email'],updated['phone'],
             updated['designation'],updated['program_interest'],updated['lead_source'],updated['lead_status'],
             score,label,updated['assigned_to'],updated['notes'],next_action,
             datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'), id))

        if old_status != updated['lead_status']:
            execute("INSERT INTO activity (institution_id,action,actor) VALUES (?,?,?)",
                    (id, f"Status updated: {old_status} → {updated['lead_status']}", 'Sales Rep'))

        flash('Lead updated successfully!', 'success')
        return redirect(url_for('lead_detail', id=id))

    programs = ['Data Science & AI','Web Development','Cloud Computing','Cybersecurity',
                'IoT & Embedded Systems','Machine Learning','DevOps','Python Programming',
                'Java Full Stack','Digital Marketing']
    statuses = ['New Lead','Contacted','Meeting Scheduled','Proposal Sent','Negotiation','Closed']
    return render_template('edit_lead.html', inst=inst, programs=programs, statuses=statuses)


@app.route('/leads/<int:id>/delete', methods=['POST'])
def delete_lead(id):
    execute("DELETE FROM follow_up WHERE institution_id=?", [id])
    execute("DELETE FROM activity WHERE institution_id=?", [id])
    execute("DELETE FROM institution WHERE id=?", [id])
    flash('Lead deleted.', 'info')
    return redirect(url_for('leads'))


@app.route('/leads/<int:id>/add_followup', methods=['POST'])
def add_followup(id):
    due_str = request.form.get('due_date')
    due_date = due_str.replace('T',' ') + ':00' if due_str else (datetime.utcnow()+timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
    task_type = request.form.get('task_type','Call')
    desc = request.form.get('description','')
    execute("INSERT INTO follow_up (institution_id,due_date,task_type,description) VALUES (?,?,?,?)",
            (id, due_date, task_type, desc))
    execute("INSERT INTO activity (institution_id,action,actor) VALUES (?,?,?)",
            (id, f"Follow-up task created: {task_type} — {desc[:60]}", 'Sales Rep'))
    flash('Follow-up task added!', 'success')
    return redirect(url_for('lead_detail', id=id))


@app.route('/followup/<int:fu_id>/complete', methods=['POST'])
def complete_followup(fu_id):
    fu = row_to_dict(query("SELECT * FROM follow_up WHERE id=?", [fu_id], one=True))
    if fu:
        execute("UPDATE follow_up SET status='Completed' WHERE id=?", [fu_id])
        execute("INSERT INTO activity (institution_id,action,actor) VALUES (?,?,?)",
                (fu['institution_id'], f"Follow-up completed: {fu['task_type']} — {(fu['description'] or '')[:60]}", 'Sales Rep'))
    return jsonify({'success': True})


@app.route('/followups')
def followups():
    now_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    all_pending = rows_to_dicts(query("""
        SELECT f.*, i.name as inst_name, i.location as inst_location,
               i.assigned_to as inst_assigned, i.priority_label as inst_priority
        FROM follow_up f LEFT JOIN institution i ON f.institution_id=i.id
        WHERE f.status='Pending' ORDER BY f.due_date"""))
    overdue = [f for f in all_pending if f['due_date'] < now_str]
    upcoming = [f for f in all_pending if f['due_date'] >= now_str]
    return render_template('followups.html', overdue=overdue, upcoming=upcoming)


# ─── API ──────────────────────────────────────────────────────────────────────

@app.route('/api/ai/analyze/<int:id>')
def ai_analyze(id):
    inst = row_to_dict(query("SELECT * FROM institution WHERE id=?", [id], one=True))
    if not inst: return jsonify({'error':'Not found'}), 404
    score, label = calculate_priority(inst)
    next_action = generate_next_action(inst)
    execute("UPDATE institution SET priority_score=?,priority_label=?,next_action=? WHERE id=?",
            (score, label, next_action, id))
    return jsonify({
        'score': score, 'label': label, 'next_action': next_action,
        'suggestions': generate_suggestions(inst),
        'outreach': generate_outreach_message(inst)
    })


@app.route('/api/leads/status_update', methods=['POST'])
def api_status_update():
    data = request.json
    inst = row_to_dict(query("SELECT * FROM institution WHERE id=?", [data['id']], one=True))
    if not inst: return jsonify({'error':'Not found'}), 404
    old = inst['lead_status']
    inst['lead_status'] = data['status']
    next_action = generate_next_action(inst)
    execute("UPDATE institution SET lead_status=?,next_action=?,updated_at=? WHERE id=?",
            (data['status'], next_action, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'), data['id']))
    execute("INSERT INTO activity (institution_id,action,actor) VALUES (?,?,?)",
            (data['id'], f"Status changed: {old} → {data['status']}", 'Sales Rep'))
    return jsonify({'success': True, 'next_action': next_action})


@app.route('/api/dashboard/stats')
def api_stats():
    institutions = rows_to_dicts(query("SELECT lead_status FROM institution"))
    pipeline = {}
    for s in ['New Lead','Contacted','Meeting Scheduled','Proposal Sent','Negotiation','Closed']:
        pipeline[s] = sum(1 for i in institutions if i['lead_status']==s)
    return jsonify(pipeline)


@app.route('/api/leads')
def api_leads():
    institutions = rows_to_dicts(query("SELECT * FROM institution ORDER BY priority_score DESC"))
    return jsonify(institutions)


# ─── Seed ─────────────────────────────────────────────────────────────────────

def seed_sample_data():
    db = sqlite3.connect(DB_PATH)
    count = db.execute("SELECT COUNT(*) FROM institution").fetchone()[0]
    if count > 0:
        db.close(); return

    samples = [
        ('GLA University','Mathura, UP','University',12000,'Dr. Rajesh Kumar','rajesh@gla.ac.in','9876543210','Dean, Academics','Data Science & AI, Machine Learning','Referral','Meeting Scheduled','Priya Sharma'),
        ('Amity University','Noida, UP','University',25000,'Prof. Anita Singh','anita@amity.edu','9123456789','Director, Training','Cloud Computing, DevOps, Cybersecurity','Conference','Proposal Sent','Rahul Verma'),
        ('AKTU Lucknow','Lucknow, UP','University',8000,'Mr. Suresh Yadav','suresh@aktu.ac.in','9988776655','Training Coordinator','IoT & Embedded Systems, Python Programming','LinkedIn','Contacted','Priya Sharma'),
        ('Delhi Technological University','Delhi','University',5500,'Dr. Meera Patel','meera@dtu.ac.in','9871234560','HOD, CSE','Web Development, Java Full Stack','Website','Negotiation','Amit Gupta'),
        ('IIT Kanpur Extension','Kanpur, UP','IIT',3000,'Prof. Vikram Nair','vikram@iitk.ac.in','9900112233','Outreach Director','Machine Learning, Data Science & AI','Referral','New Lead','Rahul Verma'),
        ('Sharda University','Greater Noida, UP','University',15000,'Ms. Pooja Mishra','pooja@sharda.ac.in','9456789012','Industry Relations','Digital Marketing, Web Development','Cold Outreach','Closed','Priya Sharma'),
    ]
    for s in samples:
        inst = {
            'name':s[0],'location':s[1],'institution_type':s[2],'student_strength':s[3],
            'contact_person':s[4],'email':s[5],'phone':s[6],'designation':s[7],
            'program_interest':s[8],'lead_source':s[9],'lead_status':s[10],'assigned_to':s[11]
        }
        score = 0
        strength = inst['student_strength']
        if strength>=10000: score+=35
        elif strength>=5000: score+=25
        elif strength>=2000: score+=15
        else: score+=5
        t = inst['institution_type'].lower()
        if 'iit' in t: score+=30
        elif 'university' in t: score+=20
        score += min(len(inst['program_interest'].split(','))*5,20)
        src_s={'Referral':15,'Conference':12,'LinkedIn':10,'Website':8,'Cold Outreach':5}
        score += src_s.get(inst['lead_source'],3)
        score = min(score,100)
        label = 'High' if score>=70 else ('Medium' if score>=40 else 'Low')

        cur = db.execute("""INSERT INTO institution
            (name,location,institution_type,student_strength,contact_person,email,phone,
             designation,program_interest,lead_source,lead_status,priority_score,priority_label,
             assigned_to,next_action)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (inst['name'],inst['location'],inst['institution_type'],inst['student_strength'],
             inst['contact_person'],inst['email'],inst['phone'],inst['designation'],
             inst['program_interest'],inst['lead_source'],inst['lead_status'],score,label,
             inst['assigned_to'], f"Next step for {inst['name']}"))
        iid = cur.lastrowid
        db.execute("INSERT INTO activity (institution_id,action,actor) VALUES (?,?,?)",
                   (iid,'Lead created (sample data)','System'))
        import random
        db.execute("INSERT INTO follow_up (institution_id,due_date,task_type,description) VALUES (?,?,?,?)",
                   (iid, (datetime.utcnow()+timedelta(days=random.randint(1,7))).strftime('%Y-%m-%d %H:%M:%S'),
                    random.choice(['Call','Email','Meeting']), 'Scheduled follow-up'))
    db.commit()
    db.close()


if __name__ == '__main__':
    init_db()
    seed_sample_data()
    app.run(debug=True, port=5000)
