import os
import hashlib
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get("DATABASE_URL", "")

def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    conn.autocommit = False
    return conn

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS utilizatori (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            nume_complet TEXT NOT NULL,
            parola_hash TEXT NOT NULL,
            rol TEXT NOT NULL CHECK(rol IN ('admin','emitent','admitent')),
            activ INTEGER DEFAULT 1,
            creat_la TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sesiuni (
            token TEXT PRIMARY KEY,
            utilizator_id INTEGER NOT NULL,
            creat_la TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(utilizator_id) REFERENCES utilizatori(id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS persoane (
            id SERIAL PRIMARY KEY,
            nume_complet TEXT NOT NULL,
            grupa_securitate TEXT,
            functia TEXT,
            activ INTEGER DEFAULT 1
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tipuri_lucrari (
            id SERIAL PRIMARY KEY,
            denumire TEXT NOT NULL,
            activ INTEGER DEFAULT 1
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fise (
            id SERIAL PRIMARY KEY,
            nr_ordine INTEGER NOT NULL,
            luna INTEGER NOT NULL,
            an INTEGER NOT NULL,
            data_emitere DATE NOT NULL,
            sef_lucrari_id INTEGER NOT NULL,
            admitent_id INTEGER NOT NULL,
            adresa_postala TEXT,
            adresa_electrica TEXT,
            tip_lucrare_id INTEGER NOT NULL,
            stare TEXT DEFAULT 'emis' CHECK(stare IN ('emis','in_lucru','semnat','anulat')),
            emis_de INTEGER NOT NULL,
            ora_inceput TIMESTAMP,
            semnat_inceput_de INTEGER,
            semnat_inceput_la TIMESTAMP,
            ora_sfarsit TIMESTAMP,
            semnat_sfarsit_de INTEGER,
            semnat_sfarsit_la TIMESTAMP,
            creat_la TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fisa_membri (
            id SERIAL PRIMARY KEY,
            fisa_id INTEGER NOT NULL,
            persoana_id INTEGER NOT NULL
        )
    """)

    cur.execute("SELECT id FROM utilizatori WHERE username='admin'")
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO utilizatori (username, nume_complet, parola_hash, rol) VALUES (%s,%s,%s,%s)",
            ("admin", "Administrator", hash_password("admin123"), "admin")
        )
        for p in [
            ('Ion Popescu', 'IV', 'Inginer sector'),
            ('Maria Ionescu', 'III', 'Electrician'),
            ('Vasile Rusu', 'IV', 'Șef echipă'),
            ('Alexandru Popa', 'III', 'Electrician'),
            ('Nicolae Botnaru', 'V', 'Admitent'),
        ]:
            cur.execute("INSERT INTO persoane (nume_complet, grupa_securitate, functia) VALUES (%s,%s,%s)", p)
        for t in [
            ('Înlocuire contor electric',),
            ('Verificare instalație electrică',),
            ('Reparație linie aeriană',),
            ('Montare branșament',),
            ('Revizie echipament de măsură',),
            ('Deconectare/Reconectare consumator',),
        ]:
            cur.execute("INSERT INTO tipuri_lucrari (denumire) VALUES (%s)", t)

    db.commit()
    cur.close()
    db.close()
