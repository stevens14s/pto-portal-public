from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

DB = "database.db"
MAX_OFFICERS_OFF = 2

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS pto_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        start_date TEXT,
        end_date TEXT,
        status TEXT DEFAULT 'Pending',
        admin_note TEXT,
        created_at TEXT
    )''')

    conn.commit()
    conn.close()

init_db()

# ---------------- USER CLASS ----------------
class User(UserMixin):
    def __init__(self, id_, username, password, role):
        self.id = id_
        self.username = username
        self.password = password
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = c.fetchone()
    conn.close()
    if user:
        return User(*user)
    return None

# ---------------- ROUTES ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=?", (username,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            login_user(User(*user))
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid login")

    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT * FROM pto_requests WHERE user_id=?", (current_user.id,))
    requests_data = c.fetchall()

    conn.close()
    return render_template("dashboard.html", requests=requests_data)

@app.route("/request", methods=["GET", "POST"])
@login_required
def request_pto():
    if request.method == "POST":
        start = request.form["start_date"]
        end = request.form["end_date"]

        from datetime import datetime, timedelta

        start_date = datetime.strptime(start, "%Y-%m-%d")
        end_date = datetime.strptime(end, "%Y-%m-%d")

        # 🚨 Basic validation
        if end_date < start_date:
            flash("End date cannot be before start date.")
            return redirect(url_for("request_pto"))

        conn = sqlite3.connect(DB)
        c = conn.cursor()

        current = start_date
        while current <= end_date:
            day_str = current.strftime("%Y-%m-%d")

            # Get approved PTO
            c.execute("""
                SELECT start_date, end_date
                FROM pto_requests
                WHERE status='Approved'
            """)
            approved_requests = c.fetchall()

            count = 0
            for s, e in approved_requests:
                s_date = datetime.strptime(s, "%Y-%m-%d")
                e_date = datetime.strptime(e, "%Y-%m-%d")

                if s_date <= current <= e_date:
                    count += 1

            # 🚨 Conflict check
            if count >= MAX_OFFICERS_OFF:
                conn.close()
                flash(f"Too many officers already off on {day_str}.")
                return redirect(url_for("request_pto"))

            current += timedelta(days=1)

        # ✅ No conflicts → insert
        c.execute("""
            INSERT INTO pto_requests (user_id, start_date, end_date, created_at)
            VALUES (?, ?, ?, ?)
        """, (current_user.id, start, end, datetime.now()))

        conn.commit()
        conn.close()

        flash("PTO request submitted successfully.")
        return redirect(url_for("dashboard"))

    return render_template("request_pto.html")

@app.route("/admin", methods=["GET", "POST"])
@login_required
def admin():
    print("NEW ADMIN ROUTE IS RUNNING", flush=True)
    print("CURRENT USER =", current_user.username, "ROLE =", current_user.role, flush=True)
    print("REQUEST METHOD =", request.method, flush=True)

    if current_user.role != "admin":
        return "Access Denied"

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    if request.method == "POST":
        req_id = request.form["req_id"]
        action = request.form["action"]

        print("REQ ID =", req_id, flush=True)
        print("ACTION =", repr(action), flush=True)

        if action.strip().lower() == "approved":
            c.execute("""
                SELECT start_date, end_date
                FROM pto_requests
                WHERE id = ?
            """, (req_id,))
            request_data = c.fetchone()

            print("REQUEST DATA =", request_data, flush=True)

            if not request_data:
                conn.close()
                flash("Request not found.")
                return redirect(url_for("admin"))

            start, end = request_data
            start_date = datetime.strptime(start, "%Y-%m-%d")
            end_date = datetime.strptime(end, "%Y-%m-%d")

            from datetime import timedelta
            current = start_date

            while current <= end_date:
                day_str = current.strftime("%Y-%m-%d")

                c.execute("""
                    SELECT COUNT(*)
                    FROM pto_requests
                    WHERE status = 'Approved'
                    AND id != ?
                    AND start_date <= ?
                    AND end_date >= ?
                """, (req_id, day_str, day_str))

                count = c.fetchone()[0]
                print("APPROVAL CHECK:", day_str, "count =", count, flush=True)

                if count >= MAX_OFFICERS_OFF:
                    conn.close()
                    flash(f"Cannot approve request. Too many officers already off on {day_str}.")
                    return redirect(url_for("admin"))

                current += timedelta(days=1)

            c.execute("""
                UPDATE pto_requests
                SET status = 'Approved'
                WHERE id = ?
            """, (req_id,))
            conn.commit()
            conn.close()
            flash("Request approved.")
            return redirect(url_for("admin"))

        elif action.strip().lower() == "denied":
            c.execute("""
                UPDATE pto_requests
                SET status = 'Denied'
                WHERE id = ?
            """, (req_id,))
            conn.commit()
            conn.close()
            flash("Request denied.")
            return redirect(url_for("admin"))

        else:
            conn.close()
            flash(f"Unexpected action value: {action!r}")
            return redirect(url_for("admin"))

    c.execute("""
        SELECT pto_requests.*, users.username
        FROM pto_requests
        JOIN users ON pto_requests.user_id = users.id
        ORDER BY pto_requests.start_date
    """)
    data = c.fetchall()

    conn.close()
    return render_template("admin.html", requests=data)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# ---------------- CREATE ADMIN ----------------
def create_admin():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    try:
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (
            "admin",
            generate_password_hash("admin123"),
            "admin"
        ))
        conn.commit()
    except:
        pass

    conn.close()

create_admin()

@app.route("/calendar")
@login_required
def calendar():
    raw_month = request.args.get("month")
    raw_year = request.args.get("year")

    return f"""
    <h1>CALENDAR TEST</h1>
    <p>raw_month={raw_month}</p>
    <p>raw_year={raw_year}</p>
    """

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)