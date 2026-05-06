from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here' # In a real app, use a secure random key

DATABASE = 'smarthire.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if not os.path.exists(DATABASE):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            cover_letter TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES jobs (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        ''')
        
        conn.commit()
        conn.close()

# Initialize DB on startup
init_db()

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
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        
        hashed_password = generate_password_hash(password)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)", 
                           (username, email, hashed_password, role))
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already exists!', 'danger')
        finally:
            conn.close()
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
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
        title = request.form['title']
        company = request.form['company']
        location = request.form['location']
        description = request.form['description']
        
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
        cover_letter = request.form['cover_letter']
        
        # Check if already applied
        cursor.execute("SELECT id FROM applications WHERE job_id = ? AND user_id = ?", (id, session['user_id']))
        if cursor.fetchone():
            flash('You have already applied for this job.', 'warning')
        else:
            cursor.execute("INSERT INTO applications (job_id, user_id, cover_letter) VALUES (?, ?, ?)",
                           (id, session['user_id'], cover_letter))
            conn.commit()
            flash('Application submitted successfully!', 'success')
            
        conn.close()
        return redirect(url_for('dashboard'))
        
    conn.close()
    return render_template('apply.html', job=job)

@app.route('/delete-job/<int:id>', methods=['POST'])
def delete_job(id):
    if 'user_id' not in session or session['role'] != 'employer':
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
