# Backend: Help Desk Ticketing System API with Flask

from flask import Flask, request, jsonify, render_template, redirect, session, url_for
import sqlite3
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace with a strong secret key

# === DATABASE SETUP ===
def init_db():
    conn = sqlite3.connect("helpdesk.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            role TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            subject TEXT,
            description TEXT,
            priority TEXT,
            status TEXT DEFAULT 'Open',
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# === EMAIL FUNCTION ===
def send_email(to_email, subject, body):
    try:
        from_email = "jainish8624@gmail.com"  # Replace
        password = "ovczxpmflnxykzfu"  # Replace
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = to_email

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(from_email, password)
            server.sendmail(from_email, to_email, msg.as_string())
    except Exception as e:
        print("Email error:", e)

# === ROUTES ===
@app.route('/')
def index():
    return render_template("index.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'admin123':
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        else:
            return "Invalid credentials", 403
    return render_template("login.html")

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))

@app.route('/admin')
def admin():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    conn = sqlite3.connect("helpdesk.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT tickets.ticket_id, users.name, users.email, tickets.subject,
               tickets.priority, tickets.status, tickets.created_at, tickets.description
        FROM tickets
        JOIN users ON tickets.user_id = users.user_id
    """)
    tickets = cursor.fetchall()
    conn.close()
    return render_template("admin.html", tickets=tickets)

@app.route('/submit', methods=['POST'])
def submit_ticket():
    name = request.form['name']
    email = request.form['email']
    subject = request.form['subject']
    description = request.form['description']
    priority = request.form['priority']

    conn = sqlite3.connect("helpdesk.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (name, email, role) VALUES (?, ?, ?)", (name, email, 'user'))
    user_id = cursor.lastrowid
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO tickets (user_id, subject, description, priority, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                   (user_id, subject, description, priority, now, now))
    conn.commit()
    conn.close()

    send_email(email, "Ticket Submitted", f"Your ticket '{subject}' has been submitted successfully.")
    return jsonify({"message": "Ticket submitted successfully."})

@app.route('/update_status', methods=['POST'])
def update_status():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    ticket_id = request.form.get('ticket_id')
    new_status = request.form.get('status')

    if not ticket_id or not new_status:
        return "Invalid input", 400

    conn = sqlite3.connect("helpdesk.db")
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE tickets SET status = ?, updated_at = ? WHERE ticket_id = ?", (new_status, now, ticket_id))
    conn.commit()

    # Send email if ticket is closed
    if new_status == "Closed":
        cursor.execute("SELECT users.email, tickets.subject FROM tickets JOIN users ON tickets.user_id = users.user_id WHERE tickets.ticket_id = ?", (ticket_id,))
        user_info = cursor.fetchone()
        if user_info:
            user_email, subject = user_info
            send_email(user_email, "Ticket Closed", f"Your ticket '{subject}' has been resolved and marked as closed. Thank you!")

    conn.close()
    return redirect("/admin")

@app.route('/delete_ticket', methods=['POST'])
def delete_ticket():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    ticket_id = request.form.get('ticket_id')
    if not ticket_id:
        return "Ticket ID required", 400

    conn = sqlite3.connect("helpdesk.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tickets WHERE ticket_id = ?", (ticket_id,))
    conn.commit()
    conn.close()
    return redirect("/admin")

if __name__ == '__main__':
    app.run(debug=True)
