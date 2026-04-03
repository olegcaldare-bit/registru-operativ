from datetime import datetime
from database import hash_password
import schemas

def _row(cur):
    r = cur.fetchone()
    return dict(r) if r else None

def _rows(cur):
    return [dict(r) for r in cur.fetchall()]

def authenticate_user(db, username, password):
    cur = db.cursor()
    cur.execute("SELECT * FROM utilizatori WHERE username=%s AND parola_hash=%s AND activ=1",
                (username, hash_password(password)))
    r = cur.fetchone()
    return dict(r) if r else None

def save_session(db, token, user_id):
    cur = db.cursor()
    cur.execute("INSERT INTO sesiuni (token, utilizator_id) VALUES (%s,%s)", (token, user_id))
    db.commit()

def delete_session(db, token):
    cur = db.cursor()
    cur.execute("DELETE FROM sesiuni WHERE token=%s", (token,))
    db.commit()

def get_session_user(db, token):
    cur = db.cursor()
    cur.execute("SELECT u.* FROM utilizatori u JOIN sesiuni s ON u.id=s.utilizator_id WHERE s.token=%s", (token,))
    r = cur.fetchone()
    return dict(r) if r else None

def get_persoane(db):
    cur = db.cursor()
    cur.execute("SELECT * FROM persoane ORDER BY nume_complet")
    return _rows(cur)

def add_persoana(db, data):
    cur = db.cursor()
    cur.execute("INSERT INTO persoane (nume_complet, grupa_securitate, functia, activ) VALUES (%s,%s,%s,%s) RETURNING id",
                (data.nume_complet, data.grupa_securitate, data.functia, data.activ))
    id = cur.fetchone()["id"]
    db.commit()
    return {"id": id, **data.dict()}

def update_persoana(db, id, data):
    cur = db.cursor()
    cur.execute("UPDATE persoane SET nume_complet=%s, grupa_securitate=%s, functia=%s, activ=%s WHERE id=%s",
                (data.nume_complet, data.grupa_securitate, data.functia, data.activ, id))
    db.commit()
    return {"id": id, **data.dict()}

def delete_persoana(db, id):
    cur = db.cursor()
    cur.execute("UPDATE persoane SET activ=0 WHERE id=%s", (id,))
    db.commit()

def get_tipuri_lucrari(db):
    cur = db.cursor()
    cur.execute("SELECT * FROM tipuri_lucrari ORDER BY denumire")
    return _rows(cur)

def add_tip_lucrare(db, data):
    cur = db.cursor()
    cur.execute("INSERT INTO tipuri_lucrari (denumire, activ) VALUES (%s,%s) RETURNING id", (data.denumire, data.activ))
    id = cur.fetchone()["id"]
    db.commit()
    return {"id": id, **data.dict()}

def update_tip_lucrare(db, id, data):
    cur = db.cursor()
    cur.execute("UPDATE tipuri_lucrari SET denumire=%s, activ=%s WHERE id=%s", (data.denumire, data.activ, id))
    db.commit()
    return {"id": id, **data.dict()}

def delete_tip_lucrare(db, id):
    cur = db.cursor()
    cur.execute("UPDATE tipuri_lucrari SET activ=0 WHERE id=%s", (id,))
    db.commit()

def _fisa_full(db, fisa_id):
    cur = db.cursor()
    cur.execute("SELECT * FROM fise WHERE id=%s", (fisa_id,))
    fisa = cur.fetchone()
    if not fisa:
        return None
    result = dict(fisa)

    cur.execute("SELECT * FROM persoane WHERE id=%s", (fisa["sef_lucrari_id"],))
    result["sef_lucrari"] = _row(cur)
    cur.execute("SELECT * FROM persoane WHERE id=%s", (fisa["admitent_id"],))
    result["admitent"] = _row(cur)
    cur.execute("SELECT * FROM tipuri_lucrari WHERE id=%s", (fisa["tip_lucrare_id"],))
    result["tip_lucrare"] = _row(cur)
    cur.execute("SELECT p.* FROM persoane p JOIN fisa_membri fm ON p.id=fm.persoana_id WHERE fm.fisa_id=%s", (fisa_id,))
    result["membri"] = _rows(cur)
    cur.execute("SELECT * FROM utilizatori WHERE id=%s", (fisa["emis_de"],))
    result["emis_de_user"] = _row(cur)

    if fisa.get("semnat_inceput_de"):
        cur.execute("SELECT * FROM utilizatori WHERE id=%s", (fisa["semnat_inceput_de"],))
        result["semnat_inceput_de_user"] = _row(cur)
    if fisa.get("semnat_sfarsit_de"):
        cur.execute("SELECT * FROM utilizatori WHERE id=%s", (fisa["semnat_sfarsit_de"],))
        result["semnat_sfarsit_de_user"] = _row(cur)

    # Convert date/datetime to string for JSON
    for k, v in result.items():
        if hasattr(v, 'isoformat'):
            result[k] = v.isoformat()

    return result

def get_fise(db, luna=None, an=None):
    cur = db.cursor()
    query = "SELECT id FROM fise WHERE 1=1"
    params = []
    if luna:
        query += " AND luna=%s"; params.append(luna)
    if an:
        query += " AND an=%s"; params.append(an)
    query += " ORDER BY an DESC, luna DESC, nr_ordine DESC"
    cur.execute(query, params)
    ids = [r["id"] for r in cur.fetchall()]
    return [_fisa_full(db, i) for i in ids]

def get_fisa(db, id):
    return _fisa_full(db, id)

def _next_nr_ordine(db, luna, an):
    cur = db.cursor()
    cur.execute("SELECT COALESCE(MAX(nr_ordine),0)+1 AS nr FROM fise WHERE luna=%s AND an=%s", (luna, an))
    return cur.fetchone()["nr"]

def create_fisa(db, data, user_id):
    dt = datetime.strptime(data.data_emitere, "%Y-%m-%d")
    luna, an = dt.month, dt.year
    nr = _next_nr_ordine(db, luna, an)
    cur = db.cursor()
    cur.execute("""INSERT INTO fise (nr_ordine,luna,an,data_emitere,sef_lucrari_id,admitent_id,
                   adresa_postala,adresa_electrica,tip_lucrare_id,emis_de)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                (nr,luna,an,data.data_emitere,data.sef_lucrari_id,data.admitent_id,
                 data.adresa_postala,data.adresa_electrica,data.tip_lucrare_id,user_id))
    fisa_id = cur.fetchone()["id"]
    for m_id in data.membri_ids:
        cur.execute("INSERT INTO fisa_membri (fisa_id, persoana_id) VALUES (%s,%s)", (fisa_id, m_id))
    db.commit()
    return {"id": fisa_id, "nr_ordine": nr, "stare": "emis"}

def update_fisa(db, id, data):
    dt = datetime.strptime(data.data_emitere, "%Y-%m-%d")
    luna, an = dt.month, dt.year
    cur = db.cursor()
    cur.execute("""UPDATE fise SET data_emitere=%s,sef_lucrari_id=%s,admitent_id=%s,
                   adresa_postala=%s,adresa_electrica=%s,tip_lucrare_id=%s,luna=%s,an=%s WHERE id=%s""",
                (data.data_emitere,data.sef_lucrari_id,data.admitent_id,
                 data.adresa_postala,data.adresa_electrica,data.tip_lucrare_id,luna,an,id))
    cur.execute("DELETE FROM fisa_membri WHERE fisa_id=%s", (id,))
    for m_id in data.membri_ids:
        cur.execute("INSERT INTO fisa_membri (fisa_id, persoana_id) VALUES (%s,%s)", (id, m_id))
    db.commit()
    return _fisa_full(db, id)

def set_stare_fisa(db, id, stare):
    cur = db.cursor()
    cur.execute("UPDATE fise SET stare=%s WHERE id=%s", (stare, id))
    db.commit()
    return _fisa_full(db, id)

def incepe_lucrarea(db, id, user_id, confirmat):
    if not confirmat:
        return {"error": "Neconfirmat"}
    now = datetime.now()
    cur = db.cursor()
    cur.execute("UPDATE fise SET stare='in_lucru',ora_inceput=%s,semnat_inceput_de=%s,semnat_inceput_la=%s WHERE id=%s",
                (now, user_id, now, id))
    db.commit()
    return _fisa_full(db, id)

def finalizeaza_lucrarea(db, id, user_id, confirmat):
    if not confirmat:
        return {"error": "Neconfirmat"}
    now = datetime.now()
    cur = db.cursor()
    cur.execute("UPDATE fise SET stare='semnat',ora_sfarsit=%s,semnat_sfarsit_de=%s,semnat_sfarsit_la=%s WHERE id=%s",
                (now, user_id, now, id))
    db.commit()
    return _fisa_full(db, id)

def get_utilizatori(db):
    cur = db.cursor()
    cur.execute("SELECT id, username, nume_complet, rol, activ FROM utilizatori")
    return _rows(cur)

def create_utilizator(db, data):
    cur = db.cursor()
    cur.execute("INSERT INTO utilizatori (username, nume_complet, parola_hash, rol) VALUES (%s,%s,%s,%s) RETURNING id",
                (data.username, data.nume_complet, hash_password(data.parola), data.rol))
    id = cur.fetchone()["id"]
    db.commit()
    return {"id": id, "username": data.username, "rol": data.rol}

def schimba_parola(db, id, parola_noua):
    cur = db.cursor()
    cur.execute("UPDATE utilizatori SET parola_hash=%s WHERE id=%s", (hash_password(parola_noua), id))
    db.commit()
