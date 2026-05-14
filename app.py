"""
Chizhya's Career Hub — Flask app backed by SQLite 3 (stdlib sqlite3 only; no MySQL).
"""
from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

from db_path import DATABASE

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY') or 'dev-only-change-with-FLASK_SECRET_KEY'

VALID_ROLES = frozenset({'job_seeker', 'employer'})


def _parse_sqlite_datetime(val):
    """SQLite often returns TIMESTAMP columns as str; normalize for display."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        s = val.strip()
        for fmt, n in (('%Y-%m-%d %H:%M:%S', 19), ('%Y-%m-%d', 10)):
            try:
                return datetime.strptime(s[:n], fmt)
            except ValueError:
                continue
    return None


@app.template_filter('sh_dt')
def sh_dt_filter(value, fmt='%Y-%m-%d'):
    dt = _parse_sqlite_datetime(value)
    return dt.strftime(fmt) if dt else ''

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Create the SQLite file and tables from database.sql if the DB file does not exist yet."""
    if os.path.exists(DATABASE):
        return
    schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.sql")
    conn = get_db_connection()
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.commit()
    finally:
        conn.close()


def ensure_indexes():
    """Migrations for existing DB files (idempotent)."""
    if not os.path.exists(DATABASE):
        return
    conn = get_db_connection()
    try:
        conn.execute(
            'CREATE UNIQUE INDEX IF NOT EXISTS idx_applications_job_user '
            'ON applications(job_id, user_id)'
        )
        conn.commit()
    except sqlite3.OperationalError as e:
        print('ensure_indexes:', e, flush=True)
    finally:
        conn.close()


# Initialize DB on startup
init_db()
ensure_indexes()

@app.route('/')
def index():
    search_query = request.args.get('q', '')
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if search_query:
        query = "SELECT * FROM jobs WHERE title LIKE ? OR location LIKE ? ORDER BY created_at DESC"
        cursor.execute(query, (f"%{search_query}%", f"%{search_query}%"))
    else:
        cursor.execute("SELECT * FROM jobs ORDER BY created_at DESC")
        
    jobs = cursor.fetchall()
    conn.close()
    return render_template('index.html', jobs=jobs, search_query=search_query)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        email = (request.form.get('email') or '').strip()
        password = request.form.get('password') or ''
        role = request.form.get('role') or ''

        if not username or not email or not password:
            flash('Please fill in all fields.', 'danger')
            return render_template('register.html')
        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
            return render_template('register.html')
        if role not in VALID_ROLES:
            flash('Please choose a valid account type.', 'danger')
            return render_template('register.html')

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
                (username, email, hashed_password, role),
            )
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError as err:
            msg = str(err).lower()
            if 'email' in msg or 'users.email' in msg:
                flash('Email already exists!', 'danger')
            else:
                flash('Could not complete registration. Please check your details.', 'danger')
        finally:
            conn.close()

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip()
        password = request.form.get('password') or ''

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please login to access the dashboard.', 'warning')
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if session['role'] == 'employer':
        cursor.execute("SELECT * FROM jobs WHERE user_id = ? ORDER BY created_at DESC", (session['user_id'],))
        jobs = [dict(row) for row in cursor.fetchall()]
        
        # Get application counts for each job
        for job in jobs:
            cursor.execute("SELECT COUNT(*) as count FROM applications WHERE job_id = ?", (job['id'],))
            job['app_count'] = cursor.fetchone()['count']
            
        context = {'jobs': jobs}
    else: # job_seeker
        cursor.execute("""
            SELECT a.*, j.title, j.company 
            FROM applications a 
            JOIN jobs j ON a.job_id = j.id 
            WHERE a.user_id = ? 
            ORDER BY a.created_at DESC
        """, (session['user_id'],))
        applications = cursor.fetchall()
        context = {'applications': applications}
        
    conn.close()
    return render_template('dashboard.html', **context)

@app.route('/post-job', methods=['GET', 'POST'])
def post_job():
    if 'user_id' not in session or session['role'] != 'employer':
        flash('Only employers can post jobs.', 'danger')
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        title = (request.form.get('title') or '').strip()
        company = (request.form.get('company') or '').strip()
        location = (request.form.get('location') or '').strip()
        description = (request.form.get('description') or '').strip()

        if not title or not company or not location or not description:
            flash('Please complete all fields.', 'danger')
            return render_template('post_job.html')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO jobs (title, company, location, description, user_id) VALUES (?, ?, ?, ?, ?)",
                       (title, company, location, description, session['user_id']))
        conn.commit()
        conn.close()
        
        flash('Job posted successfully!', 'success')
        return redirect(url_for('dashboard'))
        
    return render_template('post_job.html')

@app.route('/job/<int:id>')
def job_details(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT j.*, u.username as posted_by FROM jobs j JOIN users u ON j.user_id = u.id WHERE j.id = ?", (id,))
    job = cursor.fetchone()
    conn.close()
    
    if not job:
        flash('Job not found.', 'danger')
        return redirect(url_for('index'))
        
    return render_template('job_details.html', job=job)

@app.route('/apply/<int:id>', methods=['GET', 'POST'])
def apply(id):
    if 'user_id' not in session or session['role'] != 'job_seeker':
        flash('Please login as a job seeker to apply.', 'warning')
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE id = ?", (id,))
    job = cursor.fetchone()
    
    if not job:
        conn.close()
        flash('Job not found.', 'danger')
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        cover_letter = (request.form.get('cover_letter') or '').strip()
        if len(cover_letter) < 20:
            flash('Please write a cover letter of at least 20 characters.', 'warning')
            conn.close()
            return redirect(url_for('apply', id=id))

        cursor.execute("SELECT id FROM applications WHERE job_id = ? AND user_id = ?", (id, session['user_id']))
        if cursor.fetchone():
            flash('You have already applied for this job.', 'warning')
        else:
            try:
                cursor.execute(
                    "INSERT INTO applications (job_id, user_id, cover_letter) VALUES (?, ?, ?)",
                    (id, session['user_id'], cover_letter),
                )
                conn.commit()
                flash('Application submitted successfully!', 'success')
            except sqlite3.IntegrityError:
                conn.rollback()
                flash('You have already applied for this job.', 'warning')

        conn.close()
        return redirect(url_for('dashboard'))
        
    conn.close()
    return render_template('apply.html', job=job)

@app.route('/delete-job/<int:id>', methods=['POST'])
def delete_job(id):
    if 'user_id' not in session or session['role'] != 'employer':
        flash('You must be logged in as an employer to delete a job.', 'warning')
        return redirect(url_for('index'))
        
    conn = get_db_connection()
    cursor = conn.cursor()
    # Check ownership
    cursor.execute("SELECT user_id FROM jobs WHERE id = ?", (id,))
    job = cursor.fetchone()
    
    if job and job['user_id'] == session['user_id']:
        cursor.execute("DELETE FROM jobs WHERE id = ?", (id,))
        conn.commit()
        flash('Job deleted successfully.', 'success')
    else:
        flash('Unauthorized action.', 'danger')
        
    conn.close()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
