from flask import Flask, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import uuid
import cloudinary
import cloudinary.uploader

app = Flask(__name__)
app.secret_key = "super_secret_key_change_this"
# ------------------ CLOUDINARY CONFIG ------------------
cloudinary.config(
    cloud_name="dezeelkh8",
    api_key="765782388165964",
    api_secret="mluHEaLb8_2rk5YHeN-tbMMKweI"
)

# ------------------ DATABASE INIT ------------------
def init_db():
    with sqlite3.connect("notes.db") as conn:
        c = conn.cursor()

        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            email TEXT
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            content TEXT,
            filename TEXT,
            share_id TEXT,
            is_public INTEGER DEFAULT 1
        )
        """)

        try:
            c.execute("ALTER TABLE users ADD COLUMN email TEXT")
        except:
            pass

init_db()

# ------------------ HOME ------------------
@app.route("/")
def home():
    return redirect("/dashboard" if "user_id" in session else "/login")

# ------------------ SIGNUP ------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])

        try:
            with sqlite3.connect("notes.db") as conn:
                c = conn.cursor()
                c.execute(
                    "INSERT INTO users (username, password) VALUES (?, ?)",
                    (username, password)
                )

            flash("Account created! Please login.")
            return redirect("/login")

        except:
            flash("Username already exists!")
            return redirect("/signup")

    return render_template("signup.html")

# ------------------ LOGIN ------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        with sqlite3.connect("notes.db") as conn:
            c = conn.cursor()
            user = c.execute(
                "SELECT * FROM users WHERE username=?",
                (username,)
            ).fetchone()

        if user and check_password_hash(user[2], password):
            session["user_id"] = user[0]
            return redirect("/dashboard")

        flash("Invalid login credentials")

    return render_template("login.html")

# ------------------ DASHBOARD ------------------
# ------------------ DASHBOARD ------------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    with sqlite3.connect("notes.db") as conn:
        c = conn.cursor()

        # 👇 Get username
        user = c.execute(
            "SELECT username FROM users WHERE id=?",
            (session["user_id"],)
        ).fetchone()

        # 👇 Get notes
        notes = c.execute(
            "SELECT * FROM notes WHERE user_id=? ORDER BY id DESC",
            (session["user_id"],)
        ).fetchall()

    # 👇 Simple counting (easy to understand)
    total = len(notes)
    public = len([n for n in notes if n[5] == 1])
    private = total - public

    return render_template(
        "dashboard.html",
        username=user[0],
        notes=notes,
        total=total,
        public=public,
        private=private
    )

# ------------------ ADD NOTE ------------------
@app.route("/add", methods=["POST"])
def add_note():
    if "user_id" not in session:
        return redirect("/login")

    content = request.form["content"]
    file = request.files["file"]

    file_url = None

    if file and file.filename != "":
        upload_result = cloudinary.uploader.upload(file)
        file_url = upload_result["secure_url"]

    share_id = str(uuid.uuid4())

    with sqlite3.connect("notes.db") as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO notes (user_id, content, filename, share_id, is_public) VALUES (?, ?, ?, ?, 1)",
            (session["user_id"], content, file_url, share_id)
        )

    return redirect("/dashboard")

# ------------------ EDIT NOTE ------------------
@app.route("/edit/<int:note_id>", methods=["POST"])
def edit_note(note_id):
    if "user_id" not in session:
        return redirect("/login")

    new_content = request.form["content"]

    with sqlite3.connect("notes.db") as conn:
        c = conn.cursor()
        c.execute(
            "UPDATE notes SET content=? WHERE id=? AND user_id=?",
            (new_content, note_id, session["user_id"])
        )

    return redirect("/dashboard")

# ------------------ DELETE NOTE ------------------
@app.route("/delete/<int:note_id>")
def delete_note(note_id):
    if "user_id" not in session:
        return redirect("/login")

    with sqlite3.connect("notes.db") as conn:
        c = conn.cursor()
        c.execute(
            "DELETE FROM notes WHERE id=? AND user_id=?",
            (note_id, session["user_id"])
        )

    return redirect("/dashboard")

# ------------------ TOGGLE PUBLIC ------------------
@app.route("/toggle/<int:note_id>")
def toggle(note_id):
    if "user_id" not in session:
        return redirect("/login")

    with sqlite3.connect("notes.db") as conn:
        c = conn.cursor()

        note = c.execute(
            "SELECT is_public FROM notes WHERE id=? AND user_id=?",
            (note_id, session["user_id"])
        ).fetchone()

        if note:
            new_value = 0 if note[0] == 1 else 1
            c.execute(
                "UPDATE notes SET is_public=? WHERE id=? AND user_id=?",
                (new_value, note_id, session["user_id"])
            )

    return redirect("/dashboard")

# ------------------ PROFILE ------------------
@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect("/login")

    with sqlite3.connect("notes.db") as conn:
        c = conn.cursor()
        user = c.execute(
            "SELECT username, email FROM users WHERE id=?",
            (session["user_id"],)
        ).fetchone()

    return render_template("profile.html", user=user)

# ------------------ UPDATE PROFILE ------------------
@app.route("/update_profile", methods=["POST"])
def update_profile():
    if "user_id" not in session:
        return redirect("/login")

    username = request.form["username"]
    email = request.form["email"]

    try:
        with sqlite3.connect("notes.db") as conn:
            c = conn.cursor()
            c.execute("""
                UPDATE users
                SET username=?, email=?
                WHERE id=?
            """, (username, email, session["user_id"]))

        flash("Profile updated!")
    except:
        flash("Username already taken!")

    return redirect("/profile")

# ------------------ SHARE ------------------
@app.route("/share/<share_id>")
def share(share_id):
    with sqlite3.connect("notes.db") as conn:
        c = conn.cursor()
        note = c.execute(
            "SELECT * FROM notes WHERE share_id=?",
            (share_id,)
        ).fetchone()

    if not note or note[5] == 0:
        return "This note is private"

    file_link = ""
    if note[3]:
        file_link = f"<a href='{note[3]}' target='_blank'>View File</a>"

    return f"""
    <h2>{note[2]}</h2>
    {file_link}
    """

# ------------------ LOGOUT ------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ------------------ RUN ------------------
if __name__ == "__main__":
    app.run(debug=True)