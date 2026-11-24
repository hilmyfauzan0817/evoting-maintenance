# E-VOTE MAHASISWA

Website pemilihan Ketua Himpunan Mahasiswa menggunakan Python Flask dan SQLite. Dibuat mengikuti instruksi pada dokumen tugas final project Dasar Pemrograman.

## 1. Persiapan
- Install Python 3.10 atau lebih baru.
- Install Visual Studio Code.
- Buka folder `evote_mahasiswa` di VS Code.
- Buka terminal VS Code.

## 2. Instalasi
Jalankan perintah berikut di terminal:

```bash
python -m venv venv
```

Aktifkan virtual environment:

**Windows CMD**
```bash
venv\\Scripts\\activate
```

**Windows PowerShell**
```powershell
.\\venv\\Scripts\\Activate.ps1
```

Install Flask:
```bash
pip install -r requirements.txt
```

## 3. Menjalankan website
```bash
python main.py
```

Buka browser dan kunjungi:
http://127.0.0.1:5000

Database `evote_mahasiswa.db` akan dibuat otomatis saat program pertama kali dijalankan.

## 4. Akun demo
**Admin**
- Username: `admin`
- Password: `admin123`

**Mahasiswa**
- NIM pertama: `2310631170001`
- NIM terakhir: `2310631170500`

Data mahasiswa tersebut adalah data contoh untuk demonstrasi. Ganti dengan data pemilih resmi sebelum digunakan sungguhan.

## 5. Struktur folder
```text
evote_mahasiswa/
├── main.py
├── requirements.txt
├── README.md
├── evote_mahasiswa.db   # dibuat otomatis ketika dijalankan
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── mahasiswa.html
│   ├── admin.html
│   └── hasil.html
└── static/
    └── style.css
```

## 6. Fitur sesuai tugas
- Login mahasiswa dengan NIM.
- Login admin.
- CRUD kandidat (tambah, ubah, hapus).
- Profil kandidat berisi visi dan misi.
- Voting satu kali per NIM.
- Konfirmasi sebelum mengirim suara.
- Penyimpanan suara dan waktu voting di SQLite.
- Dashboard hasil voting dan persentase.
- Statistik total pemilih, sudah memilih, belum memilih, dan partisipasi.
- Penutupan pemilu dan pengumuman pemenang.
- Grafik batang hasil voting.

## 7. Catatan penting
Ini merupakan proyek pembelajaran/demonstrasi, bukan sistem pemilu siap produksi. Sebelum digunakan sungguhan, perlu penguatan keamanan seperti CSRF protection, pengelolaan secret key melalui environment variable, penggantian kredensial admin, verifikasi identitas mahasiswa, backup database, dan pengujian keamanan.
