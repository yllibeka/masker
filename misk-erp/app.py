from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
from functools import wraps
import os

app = Flask(__name__)
app.secret_key = 'misk-erp-secret-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///misk.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ─────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    emri = db.Column(db.String(100), nullable=False)
    mbiemri = db.Column(db.String(100), nullable=False)
    adresa = db.Column(db.String(200))
    telefoni = db.Column(db.String(30))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    tepihat = db.relationship('Tepih', backref='klienti', lazy=True, cascade='all, delete-orphan')
    porositë = db.relationship('Porosi', backref='klienti', lazy=True)

class Tepih(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    pershkrimi = db.Column(db.String(200), nullable=False)
    gjatesia = db.Column(db.Float, nullable=False)   # meters
    gjeresia = db.Column(db.Float, nullable=False)   # meters
    cmimi_per_m2 = db.Column(db.Float, default=5.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def m2(self):
        return round(self.gjatesia * self.gjeresia, 2)

    @property
    def cmimi_total(self):
        return round(self.m2 * self.cmimi_per_m2, 2)

class Porosi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    data_marrjes = db.Column(db.Date, default=date.today)
    data_dorezimit = db.Column(db.Date, nullable=True)
    statusi = db.Column(db.String(50), default='U mor')
    cmimi_total = db.Column(db.Float, default=0.0)
    shenimet = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    artikujt = db.relationship('PorosiArtikull', backref='porosi', lazy=True, cascade='all, delete-orphan')

    STATUSET = ['U mor', 'Në Matje', 'Larje', 'Tharje', 'Paketim', 'Gati']

class PorosiArtikull(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    porosi_id = db.Column(db.Integer, db.ForeignKey('porosi.id'), nullable=False)
    tepih_id = db.Column(db.Integer, db.ForeignKey('tepih.id'), nullable=False)
    cmimi_snapshot = db.Column(db.Float)
    tepih = db.relationship('Tepih')

class Material(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    emri = db.Column(db.String(100), nullable=False)
    njesia = db.Column(db.String(30))      # kg, cope, litra
    sasia_stock = db.Column(db.Float, default=0.0)
    cmimi_per_njesi = db.Column(db.Float, default=0.0)
    konsumi_per_m2 = db.Column(db.Float, default=0.0)  # consumption per m2
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

class LevizjeMateriali(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('material.id'), nullable=False)
    lloji = db.Column(db.String(20))  # 'hyrje' or 'dalje'
    sasia = db.Column(db.Float)
    cmimi_total = db.Column(db.Float)
    shenim = db.Column(db.String(200))
    data = db.Column(db.DateTime, default=datetime.utcnow)
    material = db.relationship('Material')

class Shpenzim(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kategoria = db.Column(db.String(100))  # Nafta, Rryme, Rrogat, Furnizime
    pershkrimi = db.Column(db.String(200))
    shuma = db.Column(db.Float, nullable=False)
    data = db.Column(db.Date, default=date.today)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    KATEGORITE = ['Nafta', 'Rrymë', 'Rrogat', 'Furnizime', 'Mirëmbajtje', 'Tjetër']

# ─────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == 'Admin' and request.form['password'] == 'admin':
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        flash('Kredencialet janë të gabuara!', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ─────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────

@app.route('/')
@login_required
def dashboard():
    today = date.today()
    month_start = today.replace(day=1)

    total_klientet = Client.query.count()
    porosi_aktive = Porosi.query.filter(Porosi.statusi != 'Gati').count()
    porosi_gati = Porosi.query.filter_by(statusi='Gati').count()

    shitjet_muaji = db.session.query(db.func.sum(Porosi.cmimi_total))\
        .filter(Porosi.data_marrjes >= month_start).scalar() or 0
    shpenzimet_muaji = db.session.query(db.func.sum(Shpenzim.shuma))\
        .filter(Shpenzim.data >= month_start).scalar() or 0
    profit_muaji = shitjet_muaji - shpenzimet_muaji

    porosi_te_fundit = Porosi.query.order_by(Porosi.created_at.desc()).limit(5).all()

    return render_template('dashboard.html',
        total_klientet=total_klientet,
        porosi_aktive=porosi_aktive,
        porosi_gati=porosi_gati,
        shitjet_muaji=shitjet_muaji,
        shpenzimet_muaji=shpenzimet_muaji,
        profit_muaji=profit_muaji,
        porosi_te_fundit=porosi_te_fundit
    )

# ─────────────────────────────────────────
# KLIENTET
# ─────────────────────────────────────────

@app.route('/klientet')
@login_required
def klientet():
    q = request.args.get('q', '')
    if q:
        klientet = Client.query.filter(
            (Client.emri.ilike(f'%{q}%')) | (Client.mbiemri.ilike(f'%{q}%')) | (Client.telefoni.ilike(f'%{q}%'))
        ).all()
    else:
        klientet = Client.query.order_by(Client.created_at.desc()).all()
    return render_template('klientet.html', klientet=klientet, q=q)

@app.route('/klientet/shto', methods=['GET', 'POST'])
@login_required
def shto_klient():
    if request.method == 'POST':
        k = Client(
            emri=request.form['emri'],
            mbiemri=request.form['mbiemri'],
            adresa=request.form.get('adresa', ''),
            telefoni=request.form.get('telefoni', '')
        )
        db.session.add(k)
        db.session.commit()
        flash('Klienti u shtua me sukses!', 'success')
        return redirect(url_for('profili_klientit', id=k.id))
    return render_template('form_klient.html', klient=None)

@app.route('/klientet/<int:id>')
@login_required
def profili_klientit(id):
    k = Client.query.get_or_404(id)
    porositë = Porosi.query.filter_by(client_id=id).order_by(Porosi.created_at.desc()).all()
    return render_template('profil_klient.html', klient=k, porositë=porositë)

@app.route('/klientet/<int:id>/edito', methods=['GET', 'POST'])
@login_required
def edito_klient(id):
    k = Client.query.get_or_404(id)
    if request.method == 'POST':
        k.emri = request.form['emri']
        k.mbiemri = request.form['mbiemri']
        k.adresa = request.form.get('adresa', '')
        k.telefoni = request.form.get('telefoni', '')
        db.session.commit()
        flash('Klienti u përditësua!', 'success')
        return redirect(url_for('profili_klientit', id=k.id))
    return render_template('form_klient.html', klient=k)

@app.route('/klientet/<int:id>/fshi', methods=['POST'])
@login_required
def fshi_klient(id):
    k = Client.query.get_or_404(id)
    db.session.delete(k)
    db.session.commit()
    flash('Klienti u fshi!', 'success')
    return redirect(url_for('klientet'))

# ─────────────────────────────────────────
# TEPIHAT
# ─────────────────────────────────────────

@app.route('/klientet/<int:client_id>/tepihat/shto', methods=['POST'])
@login_required
def shto_tepih(client_id):
    t = Tepih(
        client_id=client_id,
        pershkrimi=request.form['pershkrimi'],
        gjatesia=float(request.form['gjatesia']),
        gjeresia=float(request.form['gjeresia']),
        cmimi_per_m2=float(request.form.get('cmimi_per_m2', 5.0))
    )
    db.session.add(t)
    db.session.commit()
    flash('Tepih u regjistrua!', 'success')
    return redirect(url_for('profili_klientit', id=client_id))

@app.route('/tepihat/<int:id>/fshi', methods=['POST'])
@login_required
def fshi_tepih(id):
    t = Tepih.query.get_or_404(id)
    client_id = t.client_id
    db.session.delete(t)
    db.session.commit()
    flash('Tepih u fshi!', 'success')
    return redirect(url_for('profili_klientit', id=client_id))

# ─────────────────────────────────────────
# POROSITË
# ─────────────────────────────────────────

@app.route('/porosi')
@login_required
def porositë():
    statusi = request.args.get('statusi', '')
    if statusi:
        lista = Porosi.query.filter_by(statusi=statusi).order_by(Porosi.created_at.desc()).all()
    else:
        lista = Porosi.query.order_by(Porosi.created_at.desc()).all()
    return render_template('porosi.html', porositë=lista, statusi_filter=statusi, statuset=Porosi.STATUSET)

@app.route('/porosi/shto', methods=['GET', 'POST'])
@login_required
def shto_porosi():
    if request.method == 'POST':
        client_id = int(request.form['client_id'])
        tepih_ids = request.form.getlist('tepih_ids')
        if not tepih_ids:
            flash('Zgjidhni të paktën një tepih!', 'error')
            return redirect(request.url)

        p = Porosi(
            client_id=client_id,
            data_marrjes=datetime.strptime(request.form['data_marrjes'], '%Y-%m-%d').date(),
            shenimet=request.form.get('shenimet', '')
        )
        db.session.add(p)
        db.session.flush()

        total = 0
        for tid in tepih_ids:
            t = Tepih.query.get(int(tid))
            if t and t.client_id == client_id:
                pa = PorosiArtikull(porosi_id=p.id, tepih_id=t.id, cmimi_snapshot=t.cmimi_total)
                db.session.add(pa)
                total += t.cmimi_total

        p.cmimi_total = round(total, 2)
        db.session.commit()
        flash('Porosia u krijua me sukses!', 'success')
        return redirect(url_for('detajet_porosise', id=p.id))

    klientet = Client.query.order_by(Client.emri).all()
    return render_template('form_porosi.html', klientet=klientet, today=date.today().isoformat())

@app.route('/porosi/<int:id>')
@login_required
def detajet_porosise(id):
    p = Porosi.query.get_or_404(id)
    return render_template('detajet_porosi.html', porosi=p, statuset=Porosi.STATUSET)

@app.route('/porosi/<int:id>/statusi', methods=['POST'])
@login_required
def ndrysho_statusin(id):
    p = Porosi.query.get_or_404(id)
    p.statusi = request.form['statusi']
    if p.statusi == 'Gati' and not p.data_dorezimit:
        p.data_dorezimit = date.today()
    db.session.commit()
    return redirect(url_for('detajet_porosise', id=id))

@app.route('/porosi/<int:id>/fshi', methods=['POST'])
@login_required
def fshi_porosi(id):
    p = Porosi.query.get_or_404(id)
    db.session.delete(p)
    db.session.commit()
    flash('Porosia u fshi!', 'success')
    return redirect(url_for('porositë'))

# ─────────────────────────────────────────
# FABRIKA (Dashboard 1)
# ─────────────────────────────────────────

@app.route('/fabrika')
@login_required
def fabrika():
    porosi_per_status = {}
    for s in Porosi.STATUSET:
        porosi_per_status[s] = Porosi.query.filter_by(statusi=s).order_by(Porosi.created_at.desc()).all()
    return render_template('fabrika.html', porosi_per_status=porosi_per_status, statuset=Porosi.STATUSET)

# ─────────────────────────────────────────
# STOKU (Dashboard 2)
# ─────────────────────────────────────────

@app.route('/stoku')
@login_required
def stoku():
    materialet = Material.query.all()
    levizjet = LevizjeMateriali.query.order_by(LevizjeMateriali.data.desc()).limit(20).all()
    return render_template('stoku.html', materialet=materialet, levizjet=levizjet)

@app.route('/stoku/material/shto', methods=['POST'])
@login_required
def shto_material():
    m = Material(
        emri=request.form['emri'],
        njesia=request.form.get('njesia', 'copë'),
        sasia_stock=float(request.form.get('sasia_stock', 0)),
        cmimi_per_njesi=float(request.form.get('cmimi_per_njesi', 0)),
        konsumi_per_m2=float(request.form.get('konsumi_per_m2', 0))
    )
    db.session.add(m)
    db.session.commit()
    flash('Materiali u shtua!', 'success')
    return redirect(url_for('stoku'))

@app.route('/stoku/levizje', methods=['POST'])
@login_required
def shto_levizje():
    mat_id = int(request.form['material_id'])
    lloji = request.form['lloji']
    sasia = float(request.form['sasia'])
    m = Material.query.get_or_404(mat_id)

    if lloji == 'hyrje':
        m.sasia_stock += sasia
    else:
        m.sasia_stock = max(0, m.sasia_stock - sasia)

    m.updated_at = datetime.utcnow()
    lev = LevizjeMateriali(
        material_id=mat_id,
        lloji=lloji,
        sasia=sasia,
        cmimi_total=sasia * m.cmimi_per_njesi,
        shenim=request.form.get('shenim', '')
    )
    db.session.add(lev)
    db.session.commit()
    flash('Lëvizja u regjistrua!', 'success')
    return redirect(url_for('stoku'))

# ─────────────────────────────────────────
# SHPENZIMET (Dashboard 3)
# ─────────────────────────────────────────

@app.route('/shpenzimet')
@login_required
def shpenzimet():
    muaji = request.args.get('muaji', date.today().strftime('%Y-%m'))
    try:
        year, month = map(int, muaji.split('-'))
        start = date(year, month, 1)
        if month == 12:
            end = date(year+1, 1, 1)
        else:
            end = date(year, month+1, 1)
    except:
        start = date.today().replace(day=1)
        end = date.today()

    lista = Shpenzim.query.filter(Shpenzim.data >= start, Shpenzim.data < end)\
        .order_by(Shpenzim.data.desc()).all()
    total = sum(s.shuma for s in lista)

    per_kategori = {}
    for s in lista:
        per_kategori[s.kategoria] = per_kategori.get(s.kategoria, 0) + s.shuma

    return render_template('shpenzimet.html',
        lista=lista, total=total, per_kategori=per_kategori,
        kategorite=Shpenzim.KATEGORITE, muaji=muaji)

@app.route('/shpenzimet/shto', methods=['POST'])
@login_required
def shto_shpenzim():
    sh = Shpenzim(
        kategoria=request.form['kategoria'],
        pershkrimi=request.form.get('pershkrimi', ''),
        shuma=float(request.form['shuma']),
        data=datetime.strptime(request.form['data'], '%Y-%m-%d').date()
    )
    db.session.add(sh)
    db.session.commit()
    flash('Shpenzimi u regjistrua!', 'success')
    return redirect(url_for('shpenzimet'))

@app.route('/shpenzimet/<int:id>/fshi', methods=['POST'])
@login_required
def fshi_shpenzim(id):
    sh = Shpenzim.query.get_or_404(id)
    db.session.delete(sh)
    db.session.commit()
    flash('Shpenzimi u fshi!', 'success')
    return redirect(url_for('shpenzimet'))

# ─────────────────────────────────────────
# FINANCAT (Dashboard 4)
# ─────────────────────────────────────────

@app.route('/financat')
@login_required
def financat():
    today = date.today()
    year = today.year

    monthly_data = []
    for m in range(1, 13):
        start = date(year, m, 1)
        end = date(year, m+1, 1) if m < 12 else date(year+1, 1, 1)
        shitjet = db.session.query(db.func.sum(Porosi.cmimi_total))\
            .filter(Porosi.data_marrjes >= start, Porosi.data_marrjes < end).scalar() or 0
        shpenzimet = db.session.query(db.func.sum(Shpenzim.shuma))\
            .filter(Shpenzim.data >= start, Shpenzim.data < end).scalar() or 0
        monthly_data.append({
            'muaji': start.strftime('%b'),
            'shitjet': round(shitjet, 2),
            'shpenzimet': round(shpenzimet, 2),
            'profit': round(shitjet - shpenzimet, 2)
        })

    total_shitjet = sum(d['shitjet'] for d in monthly_data)
    total_shpenzimet = sum(d['shpenzimet'] for d in monthly_data)
    total_profit = total_shitjet - total_shpenzimet

    # Shpenzimet per kategori (viti)
    year_start = date(year, 1, 1)
    shpenzimet_kategorite = db.session.query(
        Shpenzim.kategoria, db.func.sum(Shpenzim.shuma)
    ).filter(Shpenzim.data >= year_start).group_by(Shpenzim.kategoria).all()

    return render_template('financat.html',
        monthly_data=monthly_data,
        total_shitjet=total_shitjet,
        total_shpenzimet=total_shpenzimet,
        total_profit=total_profit,
        shpenzimet_kategorite=shpenzimet_kategorite,
        year=year
    )

# ─────────────────────────────────────────
# API (AJAX)
# ─────────────────────────────────────────

@app.route('/api/klient/<int:id>/tepihat')
@login_required
def api_tepihat(id):
    tepihat = Tepih.query.filter_by(client_id=id).all()
    return jsonify([{
        'id': t.id,
        'pershkrimi': t.pershkrimi,
        'gjatesia': t.gjatesia,
        'gjeresia': t.gjeresia,
        'm2': t.m2,
        'cmimi_total': t.cmimi_total
    } for t in tepihat])

# ─────────────────────────────────────────
# INIT
# ─────────────────────────────────────────

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
