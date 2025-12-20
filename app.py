import os
import sqlite3

from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ==============================
# KONFIGURACJA
# ==============================
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

app = Flask(__name__)
app.secret_key = "super_secret_key"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# ==============================
# BAZA DANYCH
# ==============================
def get_db():
    return sqlite3.connect(os.path.join(BASE_DIR, "database.db"))

with get_db() as db:
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            number TEXT NOT NULL,
            photo TEXT NOT NULL
        )
    """)

# ==============================
# MODEL UŻYTKOWNIKA
# ==============================
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    cur = db.execute("SELECT id, username, password FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    return User(*row) if row else None

# ==============================
# ENDPOINTY LOGOWANIA/REJESTRACJI
# ==============================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        db = get_db()
        cur = db.execute("SELECT id, username, password FROM users WHERE username = ?", (username,))
        user = cur.fetchone()
        if user and check_password_hash(user[2], password):
            login_user(User(*user))
            next_page = request.args.get("next")
            return redirect(next_page or url_for("index"))
        else:
            flash("Błędny login lub hasło")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = generate_password_hash(request.form.get("password"))
        db = get_db()
        try:
            db.execute("INSERT INTO users(username, password) VALUES (?, ?)", (username, password))
            db.commit()
        except sqlite3.IntegrityError:
            flash("Użytkownik już istnieje")
            return redirect(url_for("register"))
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# ==============================
# STRONY APLIKACJI
# ==============================
@app.route("/")
@login_required
def index():
    return render_template("index.html")

@app.route("/add_player", methods=["GET", "POST"])
@login_required
def add_player():
    db = get_db()
    if request.method == "POST":
        name = request.form.get("name")
        number = request.form.get("number")
        photo = request.files.get("photo")
        if not name or not number or not photo or photo.filename == "":
            flash("Wszystkie pola są wymagane")
            return redirect(url_for("add_player"))
        filename = secure_filename(photo.filename)
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        photo.save(save_path)
        db.execute("INSERT INTO players(name, number, photo) VALUES (?, ?, ?)", (name, number, filename))
        db.commit()
        return redirect(url_for("add_player"))
    players = db.execute("SELECT * FROM players").fetchall()
    return render_template("add_player.html", players=players)

@app.route("/lineup")
@login_required
def lineup():
    db = get_db()
    players = db.execute("SELECT * FROM players").fetchall()
    return render_template("lineup.html", players=players)

# ==============================
# STATIC UPLOADS
# ==============================
@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ==============================
# START
# ==============================

@app.route("/delete_player/<int:player_id>", methods=["POST"])
@login_required
def delete_player(player_id):
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    # pobierz nazwę pliku zdjęcia
    cur.execute("SELECT photo FROM players WHERE id = ?", (player_id,))
    row = cur.fetchone()

    if row:
        photo_filename = row[0]
        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], photo_filename)

        # usuń plik zdjęcia
        if os.path.exists(photo_path):
            os.remove(photo_path)

        # usuń zawodnika z bazy
        cur.execute("DELETE FROM players WHERE id = ?", (player_id,))
        conn.commit()

    conn.close()
    return redirect(url_for("add_player"))

if __name__ == "__main__":
    app.run(debug=True)


