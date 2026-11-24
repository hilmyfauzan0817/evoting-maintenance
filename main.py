import sqlite3
from functools import wraps
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "ganti-dengan-secret-key-acak-anda"
DATABASE = "evote_mahasiswa.db"


# =========================
# DATABASE DAN INISIALISASI
# =========================
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DATABASE)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS pemilih (
            nim TEXT PRIMARY KEY,
            nama TEXT NOT NULL,
            program_studi TEXT NOT NULL,
            angkatan INTEGER NOT NULL,
            sudah_memilih INTEGER DEFAULT 0,
            tanggal_vote TEXT
        );

        CREATE TABLE IF NOT EXISTS kandidat (
            id_kandidat INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_calon TEXT NOT NULL,
            program_studi TEXT NOT NULL,
            angkatan INTEGER NOT NULL,
            visi TEXT NOT NULL,
            misi TEXT NOT NULL,
            total_suara INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS pengaturan_pemilu (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            status_pemilu TEXT NOT NULL DEFAULT 'AKTIF'
        );
    """)
    # Akun admin awal untuk demonstrasi tugas.
    admin_count = db.execute("SELECT COUNT(*) FROM admin").fetchone()[0]
    if admin_count == 0:
        db.execute(
            "INSERT INTO admin (username, password) VALUES (?, ?)",
            ("admin", generate_password_hash("admin123"))
        )

    # Data awal 500 pemilih tetap (data contoh untuk pengujian).
    voter_count = db.execute("SELECT COUNT(*) FROM pemilih").fetchone()[0]
    if voter_count == 0:
        for nomor in range(1, 501):
            nim = f"231063117{nomor:04d}"
            db.execute(
                """INSERT INTO pemilih
                   (nim, nama, program_studi, angkatan, sudah_memilih)
                   VALUES (?, ?, ?, ?, 0)""",
                (nim, f"Mahasiswa {nomor:03d}", "Informatika", 2023)
            )

    candidate_count = db.execute("SELECT COUNT(*) FROM kandidat").fetchone()[0]
    if candidate_count == 0:
        contoh_kandidat = [
            ("Ahmad Fauzi", "Informatika", 2023,
             "Membangun himpunan yang inovatif dan inklusif.",
             "1. Meningkatkan kompetensi anggota.\n2. Memperluas kolaborasi industri."),
            ("Siti Nurhaliza", "Informatika", 2022,
             "Mewujudkan himpunan yang aktif, solid, dan berprestasi.",
             "1. Mengadakan kegiatan pengembangan anggota.\n2. Memperkuat komunikasi antaranggota."),
            ("Budi Santoso", "Informatika", 2023,
             "Menjadikan himpunan sebagai wadah aspirasi mahasiswa.",
             "1. Menampung aspirasi mahasiswa.\n2. Mengembangkan program kerja yang bermanfaat.")
        ]
        db.executemany(
            """INSERT INTO kandidat
               (nama_calon, program_studi, angkatan, visi, misi)
               VALUES (?, ?, ?, ?, ?)""",
            contoh_kandidat
        )

    db.execute(
        "INSERT OR IGNORE INTO pengaturan_pemilu (id, status_pemilu) VALUES (1, 'AKTIF')"
    )
    db.commit()
    db.close()


# =========================
# FUNCTION AUTENTIKASI
# =========================
def login_mahasiswa(nim):
    return get_db().execute(
        "SELECT * FROM pemilih WHERE nim = ?", (nim,)
    ).fetchone()


def login_admin(username, password):
    admin = get_db().execute(
        "SELECT * FROM admin WHERE username = ?", (username,)
    ).fetchone()
    return admin if admin and check_password_hash(admin["password"], password) else None


def mahasiswa_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if session.get("role") != "mahasiswa":
            flash("Silakan login sebagai mahasiswa terlebih dahulu.", "warning")
            return redirect(url_for("index"))
        return func(*args, **kwargs)
    return wrapper


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Silakan login sebagai admin terlebih dahulu.", "warning")
            return redirect(url_for("index"))
        return func(*args, **kwargs)
    return wrapper


# =========================
# FUNCTION DATA KANDIDAT
# =========================
def ambil_semua_kandidat():
    return get_db().execute(
        "SELECT * FROM kandidat ORDER BY id_kandidat"
    ).fetchall()


def ambil_kandidat(id_kandidat):
    return get_db().execute(
        "SELECT * FROM kandidat WHERE id_kandidat = ?", (id_kandidat,)
    ).fetchone()


def tambah_kandidat(data):
    db = get_db()
    db.execute(
        """INSERT INTO kandidat
           (nama_calon, program_studi, angkatan, visi, misi)
           VALUES (?, ?, ?, ?, ?)""",
        (data["nama_calon"], data["program_studi"], data["angkatan"],
         data["visi"], data["misi"])
    )
    db.commit()


def ubah_kandidat(id_kandidat, data):
    db = get_db()
    db.execute(
        """UPDATE kandidat
           SET nama_calon=?, program_studi=?, angkatan=?, visi=?, misi=?
           WHERE id_kandidat=?""",
        (data["nama_calon"], data["program_studi"], data["angkatan"],
         data["visi"], data["misi"], id_kandidat)
    )
    db.commit()


def hapus_kandidat(id_kandidat):
    db = get_db()
    kandidat = ambil_kandidat(id_kandidat)
    if kandidat and kandidat["total_suara"] == 0:
        db.execute("DELETE FROM kandidat WHERE id_kandidat=?", (id_kandidat,))
        db.commit()
        return True
    return False


# =========================
# FUNCTION VOTING DAN STATISTIK
# =========================
def status_pemilu():
    row = get_db().execute(
        "SELECT status_pemilu FROM pengaturan_pemilu WHERE id=1"
    ).fetchone()
    return row["status_pemilu"] if row else "DITUTUP"


def proses_voting(nim, id_kandidat):
    db = get_db()
    try:
        db.execute("BEGIN IMMEDIATE")
        pengaturan = db.execute(
            "SELECT status_pemilu FROM pengaturan_pemilu WHERE id=1"
        ).fetchone()
        pemilih = db.execute(
            "SELECT * FROM pemilih WHERE nim=?", (nim,)
        ).fetchone()
        kandidat = db.execute(
            "SELECT * FROM kandidat WHERE id_kandidat=?", (id_kandidat,)
        ).fetchone()

        if not pengaturan or pengaturan["status_pemilu"] != "AKTIF":
            db.rollback()
            return False, "Pemungutan suara telah ditutup."
        if not pemilih:
            db.rollback()
            return False, "NIM tidak terdaftar."
        if pemilih["sudah_memilih"] == 1:
            db.rollback()
            return False, "Anda sudah menggunakan hak suara."
        if not kandidat:
            db.rollback()
            return False, "Kandidat tidak ditemukan."

        waktu = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            "UPDATE kandidat SET total_suara=total_suara+1 WHERE id_kandidat=?",
            (id_kandidat,)
        )
        db.execute(
            "UPDATE pemilih SET sudah_memilih=1, tanggal_vote=? WHERE nim=?",
            (waktu, nim)
        )
        db.commit()
        return True, "Terima kasih. Suara Anda berhasil direkam."
    except sqlite3.Error:
        db.rollback()
        return False, "Terjadi kesalahan database. Silakan coba kembali."


def hitung_statistik():
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM pemilih").fetchone()[0]
    sudah = db.execute(
        "SELECT COUNT(*) FROM pemilih WHERE sudah_memilih=1"
    ).fetchone()[0]
    belum = total - sudah
    partisipasi = (sudah / total * 100) if total else 0
    return total, sudah, belum, partisipasi


def hasil_voting():
    db = get_db()
    total_suara = db.execute(
        "SELECT COALESCE(SUM(total_suara), 0) FROM kandidat"
    ).fetchone()[0]
    rows = db.execute(
        "SELECT * FROM kandidat ORDER BY total_suara DESC, nama_calon"
    ).fetchall()
    hasil = []
    for row in rows:
        persen = (row["total_suara"] / total_suara * 100) if total_suara else 0
        hasil.append({
            "id_kandidat": row["id_kandidat"],
            "nama_calon": row["nama_calon"],
            "total_suara": row["total_suara"],
            "persentase": persen
        })
    return hasil, total_suara


def tutup_pemilu():
    db = get_db()
    db.execute(
        "UPDATE pengaturan_pemilu SET status_pemilu='DITUTUP' WHERE id=1"
    )
    db.commit()


def buka_pemilu():
    db = get_db()
    db.execute(
        "UPDATE pengaturan_pemilu SET status_pemilu='AKTIF' WHERE id=1"
    )
    db.commit()


# =========================
# ROUTE WEBSITE
# =========================
@app.route("/")
def index():
    return render_template("index.html", status=status_pemilu())


@app.route("/login-mahasiswa", methods=["POST"])
def masuk_mahasiswa():
    nim = request.form.get("nim", "").strip()
    pemilih = login_mahasiswa(nim)
    if not pemilih:
        flash("NIM tidak terdaftar.", "danger")
        return redirect(url_for("index"))
    session.clear()
    session["role"] = "mahasiswa"
    session["nim"] = pemilih["nim"]
    session["nama"] = pemilih["nama"]
    return redirect(url_for("dashboard_mahasiswa"))


@app.route("/login-admin", methods=["POST"])
def masuk_admin():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    admin = login_admin(username, password)
    if not admin:
        flash("Username atau password admin salah.", "danger")
        return redirect(url_for("index"))
    session.clear()
    session["role"] = "admin"
    session["username"] = admin["username"]
    return redirect(url_for("dashboard_admin"))


@app.route("/mahasiswa")
@mahasiswa_required
def dashboard_mahasiswa():
    pemilih = login_mahasiswa(session["nim"])
    return render_template(
        "mahasiswa.html", pemilih=pemilih,
        kandidat=ambil_semua_kandidat(), status=status_pemilu()
    )


@app.route("/vote/<int:id_kandidat>", methods=["POST"])
@mahasiswa_required
def vote(id_kandidat):
    sukses, pesan = proses_voting(session["nim"], id_kandidat)
    flash(pesan, "success" if sukses else "danger")
    return redirect(url_for("dashboard_mahasiswa"))


@app.route("/admin")
@admin_required
def dashboard_admin():
    total, sudah, belum, partisipasi = hitung_statistik()
    hasil, total_suara = hasil_voting()
    pemilih = get_db().execute(
        "SELECT * FROM pemilih ORDER BY nim"
    ).fetchall()
    return render_template(
        "admin.html", kandidat=ambil_semua_kandidat(), hasil=hasil,
        total_suara=total_suara, total=total, sudah=sudah, belum=belum,
        partisipasi=partisipasi, pemilih=pemilih,
        status=status_pemilu()
    )


@app.route("/admin/kandidat/tambah", methods=["POST"])
@admin_required
def route_tambah_kandidat():
    data = {
        "nama_calon": request.form.get("nama_calon", "").strip(),
        "program_studi": request.form.get("program_studi", "").strip(),
        "angkatan": request.form.get("angkatan", "").strip(),
        "visi": request.form.get("visi", "").strip(),
        "misi": request.form.get("misi", "").strip()
    }
    if not all(data.values()) or not data["angkatan"].isdigit():
        flash("Semua data kandidat wajib diisi dengan benar.", "danger")
    else:
        tambah_kandidat(data)
        flash("Kandidat berhasil ditambahkan.", "success")
    return redirect(url_for("dashboard_admin"))


@app.route("/admin/kandidat/<int:id_kandidat>/edit", methods=["POST"])
@admin_required
def route_ubah_kandidat(id_kandidat):
    data = {
        "nama_calon": request.form.get("nama_calon", "").strip(),
        "program_studi": request.form.get("program_studi", "").strip(),
        "angkatan": request.form.get("angkatan", "").strip(),
        "visi": request.form.get("visi", "").strip(),
        "misi": request.form.get("misi", "").strip()
    }
    if not all(data.values()) or not data["angkatan"].isdigit():
        flash("Data kandidat belum lengkap atau angkatan tidak valid.", "danger")
    elif not ambil_kandidat(id_kandidat):
        flash("Kandidat tidak ditemukan.", "danger")
    else:
        ubah_kandidat(id_kandidat, data)
        flash("Data kandidat berhasil diperbarui.", "success")
    return redirect(url_for("dashboard_admin"))


@app.route("/admin/kandidat/<int:id_kandidat>/hapus", methods=["POST"])
@admin_required
def route_hapus_kandidat(id_kandidat):
    if hapus_kandidat(id_kandidat):
        flash("Kandidat berhasil dihapus.", "success")
    else:
        flash("Kandidat tidak dapat dihapus jika sudah memiliki suara.", "danger")
    return redirect(url_for("dashboard_admin"))


@app.route("/admin/tutup", methods=["POST"])
@admin_required
def route_tutup_pemilu():
    tutup_pemilu()
    flash("Pemungutan suara telah ditutup.", "warning")
    return redirect(url_for("dashboard_admin"))


@app.route("/admin/buka", methods=["POST"])
@admin_required
def route_buka_pemilu():
    buka_pemilu()
    flash("Pemungutan suara kembali diaktifkan.", "success")
    return redirect(url_for("dashboard_admin"))


@app.route("/logout")
def logout():
    session.clear()
    flash("Anda berhasil logout.", "info")
    return redirect(url_for("index"))


@app.route("/hasil")
def hasil_publik():
    if status_pemilu() != "DITUTUP":
        flash("Hasil akhir akan ditampilkan setelah pemilu ditutup.", "warning")
        return redirect(url_for("index"))
    hasil, total_suara = hasil_voting()
    pemenang = hasil[0] if hasil and total_suara else None
    return render_template(
        "hasil.html", hasil=hasil, total_suara=total_suara,
        pemenang=pemenang
    )


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
