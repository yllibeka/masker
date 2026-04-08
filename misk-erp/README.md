# MISK ERP — Udhëzuesi i Deploy-it në Hostinger

## Struktura e Skedarëve

```
misk-erp/
├── app.py                  ← Aplikacioni kryesor Flask
├── passenger_wsgi.py       ← Entry point për Hostinger
├── requirements.txt        ← Bibliotekat Python
├── templates/              ← Faqet HTML
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── klientet.html
│   ├── profil_klient.html
│   ├── form_klient.html
│   ├── porosi.html
│   ├── detajet_porosi.html
│   ├── form_porosi.html
│   ├── fabrika.html
│   ├── stoku.html
│   ├── shpenzimet.html
│   └── financat.html
├── static/                 ← Skedarë statikë (CSS, JS)
└── instance/               ← SQLite DB (krijohet automatikisht)
    └── misk.db
```

---

## Hapat për Deploy në Hostinger (Shared Hosting)

### 1. Aktivizo Python në Hostinger
1. Hyr tek **hPanel → Advanced → Python**
2. Krijo një Python App të re:
   - **Python Version**: 3.11
   - **Application Root**: `public_html/misk-erp` (ose emri që dëshiron)
   - **Application URL**: `/` ose subdomain
   - **Application Startup File**: `passenger_wsgi.py`

### 2. Ngarko Skedarët
Përdor **File Manager** ose **FTP (FileZilla)**:
1. Ngarko të gjithë skedarët e projektit tek `public_html/misk-erp/`
2. Sigurohu që struktura të jetë saktë si më sipër

### 3. Instalo Bibliotekat
Hyr tek **SSH Terminal** (ose hPanel → Terminal):
```bash
cd ~/public_html/misk-erp
pip install -r requirements.txt --user
```

Nëse Hostinger ka Virtual Environment:
```bash
source ~/virtualenv/public_html/misk-erp/3.11/bin/activate
pip install -r requirements.txt
```

### 4. Inicializo Databazën
Në SSH Terminal:
```bash
cd ~/public_html/misk-erp
python -c "from app import app, db; app.app_context().push(); db.create_all(); print('DB created!')"
```

### 5. Rinisja e Aplikacionit
Tek **hPanel → Python → Restart App**

---

## Testimi Lokal (para deploy)

```bash
# Instalo bibliotekat
pip install -r requirements.txt

# Nisni aplikacionin
python app.py

# Hape shfletuesin tek:
# http://localhost:5000
```

**Login:**
- Përdoruesi: `Admin`
- Fjalëkalimi: `admin`

---

## Ndryshimi i Çmimit Default

Tek profili i klientit, çdo tepih ka fushën **"Çmimi/m²"** — default është **€5.00/m²**.
Mund ta ndryshosh sipas nevojës.

---

## Siguria (Rekomandim)

Për prodhim, ndrysho `secret_key` tek `app.py`:
```python
app.secret_key = 'vendos-ketu-nje-fjalekalim-te-forte-dhe-unik-2024'
```

Dhe ndrysho kredencialet e login-it (gjithashtu tek `app.py`):
```python
if request.form['username'] == 'Admin' and request.form['password'] == 'admin':
```

---

## Backup i Databazës

Databaza SQLite ndodhet tek: `instance/misk.db`

Për backup, kopjo këtë skedar periodikisht!

---

*MISK ERP v1.0 — Internal System*
