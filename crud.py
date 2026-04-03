import hashlib
from datetime import datetime, date
from database import hash_password
import schemas

def authenticate_user(db, username, password):
    row = db.execute(
        "SELECT * FROM utilizatori WHERE username=? AND parola_hash=? AND activ=1",
        (username, hash_password(password))
    ).fetchone()
    if not row:
        return None
    return dict(row)

def save_session(db, token, user_id):
    db.execute("INSERT INTO sesiuni (token, utilizator_id) VALUES (?,?)", (token, user_id))
    db.commit()

def delete_session(db, token):
    db.execute("DELETE FROM sesiuni WHERE token=?", (token,))
    db.commit()

def get_session_user(db, token):
    row = db.execute(
        "SELECT u.* FROM utilizatori u JOIN sesiuni s ON u.id=s.utilizator_id WHERE s.token=?",
        (token,)
    ).fetchone()
    return dict(row) if row else None

# ─── PERSOANE ────────────────────────────────────────────────────────────────

def get_persoane(db):
    rows = db.execute("SELECT * FROM persoane ORDER BY nume_complet").fetchall()
    return [dict(r) for r in rows]

def add_persoana(db, data: schemas.PersoanaCreate):
    cur = db.execute(
        "INSERT INTO persoane (nume_complet, grupa_securitate, functia, activ) VALUES (?,?,?,?)",
        (data.nume_complet, data.grupa_securitate, data.functia, data.activ)
    )
    db.commit()
    return {"id": cur.lastrowid, **data.dict()}

def update_persoana(db, id, data: schemas.PersoanaCreate):
    db.execute(
        "UPDATE persoane SET nume_complet=?, grupa_securitate=?, functia=?, activ=? WHERE id=?",
        (data.nume_complet, data.grupa_securitate, data.functia, data.activ, id)
    )
    db.commit()
    return {"id": id, **data.dict()}

def delete_persoana(db, id):
    db.execute("UPDATE persoane SET activ=0 WHERE id=?", (id,))
    db.commit()

# ─── TIPURI LUCRĂRI ───────────────────────────────────────────────────────────

def get_tipuri_lucrari(db):
    rows = db.execute("SELECT * FROM tipuri_lucrari ORDER BY denumire").fetchall()
    return [dict(r) for r in rows]

def add_tip_lucrare(db, data: schemas.TipLucrareCreate):
    cur = db.execute("INSERT INTO tipuri_lucrari (denumire, activ) VALUES (?,?)", (data.denumire, data.activ))
    db.commit()
    return {"id": cur.lastrowid, **data.dict()}

def update_tip_lucrare(db, id, data: schemas.TipLucrareCreate):
    db.execute("UPDATE tipuri_lucrari SET denumire=?, activ=? WHERE id=?", (data.denumire, data.activ, id))
    db.commit()
    return {"id": id, **data.dict()}

def delete_tip_lucrare(db, id):
    db.execute("UPDATE tipuri_lucrari SET activ=0 WHERE id=?", (id,))
    db.commit()

# ─── FIȘE ────────────────────────────────────────────────────────────────────

def _next_nr_ordine(db, luna, an):
    row = db.execute(
        "SELECT COALESCE(MAX(nr_ordine),0)+1 as nr FROM fise WHERE luna=? AND an=?",
        (luna, an)
    ).fetchone()
    return row["nr"]

def _fisa_full(db, fisa_id):
    fisa = db.execute("SELECT * FROM fise WHERE id=?", (fisa_id,)).fetchone()
    if not fisa:
        return None
    result = dict(fisa)
    # Enrich with related data
    sef = db.execute("SELECT * FROM persoane WHERE id=?", (fisa["sef_lucrari_id"],)).fetchone()
    admitent = db.execute("SELECT * FROM persoane WHERE id=?", (fisa["admitent_id"],)).fetchone()
    tip = db.execute("SELECT * FROM tipuri_lucrari WHERE id=?", (fisa["tip_lucrare_id"],)).fetchone()
    membri_rows = db.execute(
        "SELECT p.* FROM persoane p JOIN fisa_membri fm ON p.id=fm.persoana_id WHERE fm.fisa_id=?",
        (fisa_id,)
    ).fetchall()
    emis_de = db.execute("SELECT * FROM utilizatori WHERE id=?", (fisa["emis_de"],)).fetchone()

    result["sef_lucrari"] = dict(sef) if sef else None
    result["admitent"] = dict(admitent) if admitent else None
    result["tip_lucrare"] = dict(tip) if tip else None
    result["membri"] = [dict(m) for m in membri_rows]
    result["emis_de_user"] = dict(emis_de) if emis_de else None

    if fisa["semnat_inceput_de"]:
        u = db.execute("SELECT * FROM utilizatori WHERE id=?", (fisa["semnat_inceput_de"],)).fetchone()
        result["semnat_inceput_de_user"] = dict(u) if u else None
    if fisa["semnat_sfarsit_de"]:
        u = db.execute("SELECT * FROM utilizatori WHERE id=?", (fisa["semnat_sfarsit_de"],)).fetchone()
        result["semnat_sfarsit_de_user"] = dict(u) if u else None

    return result

def get_fise(db, luna=None, an=None):
    query = "SELECT * FROM fise WHERE 1=1"
    params = []
    if luna:
        query += " AND luna=?"
        params.append(luna)
    if an:
        query += " AND an=?"
        params.append(an)
    query += " ORDER BY an DESC, luna DESC, nr_ordine DESC"
    rows = db.execute(query, params).fetchall()
    results = []
    for row in rows:
        f = _fisa_full(db, row["id"])
        if f:
            results.append(f)
    return results

def get_fisa(db, id):
    return _fisa_full(db, id)

def create_fisa(db, data: schemas.FisaCreate, user_id: int):
    dt = datetime.strptime(data.data_emitere, "%Y-%m-%d")
    luna, an = dt.month, dt.year
    nr = _next_nr_ordine(db, luna, an)
    cur = db.execute(
        """INSERT INTO fise (nr_ordine, luna, an, data_emitere, sef_lucrari_id, admitent_id,
           adresa_postala, adresa_electrica, tip_lucrare_id, emis_de)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (nr, luna, an, data.data_emitere, data.sef_lucrari_id, data.admitent_id,
         data.adresa_postala, data.adresa_electrica, data.tip_lucrare_id, user_id)
    )
    fisa_id = cur.lastrowid
    for m_id in data.membri_ids:
        db.execute("INSERT INTO fisa_membri (fisa_id, persoana_id) VALUES (?,?)", (fisa_id, m_id))
    db.commit()
    return {"id": fisa_id, "nr_ordine": nr, "stare": "emis"}

def update_fisa(db, id, data: schemas.FisaCreate):
    dt = datetime.strptime(data.data_emitere, "%Y-%m-%d")
    luna, an = dt.month, dt.year
    db.execute(
        """UPDATE fise SET data_emitere=?, sef_lucrari_id=?, admitent_id=?,
           adresa_postala=?, adresa_electrica=?, tip_lucrare_id=?, luna=?, an=?
           WHERE id=?""",
        (data.data_emitere, data.sef_lucrari_id, data.admitent_id,
         data.adresa_postala, data.adresa_electrica, data.tip_lucrare_id, luna, an, id)
    )
    db.execute("DELETE FROM fisa_membri WHERE fisa_id=?", (id,))
    for m_id in data.membri_ids:
        db.execute("INSERT INTO fisa_membri (fisa_id, persoana_id) VALUES (?,?)", (id, m_id))
    db.commit()
    return _fisa_full(db, id)

def set_stare_fisa(db, id, stare):
    db.execute("UPDATE fise SET stare=? WHERE id=?", (stare, id))
    db.commit()
    return _fisa_full(db, id)

def incepe_lucrarea(db, id, user_id, confirmat):
    if not confirmat:
        return {"error": "Neconfirmat"}
    now = datetime.now().isoformat()
    db.execute(
        "UPDATE fise SET stare='in_lucru', ora_inceput=?, semnat_inceput_de=?, semnat_inceput_la=? WHERE id=?",
        (now, user_id, now, id)
    )
    db.commit()
    return _fisa_full(db, id)

def finalizeaza_lucrarea(db, id, user_id, confirmat):
    if not confirmat:
        return {"error": "Neconfirmat"}
    now = datetime.now().isoformat()
    db.execute(
        "UPDATE fise SET stare='semnat', ora_sfarsit=?, semnat_sfarsit_de=?, semnat_sfarsit_la=? WHERE id=?",
        (now, user_id, now, id)
    )
    db.commit()
    return _fisa_full(db, id)

# ─── UTILIZATORI ─────────────────────────────────────────────────────────────

def get_utilizatori(db):
    rows = db.execute("SELECT id, username, nume_complet, rol, activ FROM utilizatori").fetchall()
    return [dict(r) for r in rows]

def create_utilizator(db, data: schemas.UtilizatorCreate):
    cur = db.execute(
        "INSERT INTO utilizatori (username, nume_complet, parola_hash, rol) VALUES (?,?,?,?)",
        (data.username, data.nume_complet, hash_password(data.parola), data.rol)
    )
    db.commit()
    return {"id": cur.lastrowid, "username": data.username, "rol": data.rol}

def schimba_parola(db, id, parola_noua):
    db.execute("UPDATE utilizatori SET parola_hash=? WHERE id=?", (hash_password(parola_noua), id))
    db.commit()
