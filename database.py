import sqlite3
import os
import hashlib
from datetime import datetime

DB_PATH = os.environ.get("DB_PATH", "registru.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS utilizatori (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            nume_complet TEXT NOT NULL,
            parola_hash TEXT NOT NULL,
            rol TEXT NOT NULL CHECK(rol IN ('admin','emitent','admitent')),
            activ INTEGER DEFAULT 1,
            creat_la TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS sesiuni (
            token TEXT PRIMARY KEY,
            utilizator_id INTEGER NOT NULL,
            creat_la TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(utilizator_id) REFERENCES utilizatori(id)
        );

        CREATE TABLE IF NOT EXISTS persoane (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nume_complet TEXT NOT NULL,
            grupa_securitate TEXT,
            functia TEXT,
            activ INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS tipuri_lucrari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            denumire TEXT NOT NULL,
            activ INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS fise (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            creat_la TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(sef_lucrari_id) REFERENCES persoane(id),
            FOREIGN KEY(admitent_id) REFERENCES persoane(id),
            FOREIGN KEY(tip_lucrare_id) REFERENCES tipuri_lucrari(id),
            FOREIGN KEY(emis_de) REFERENCES utilizatori(id)
        );

        CREATE TABLE IF NOT EXISTS fisa_membri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fisa_id INTEGER NOT NULL,
            persoana_id INTEGER NOT NULL,
            FOREIGN KEY(fisa_id) REFERENCES fise(id),
            FOREIGN KEY(persoana_id) REFERENCES persoane(id)
        );
    """)

    # Insert default admin if not exists
    existing = db.execute("SELECT id FROM utilizatori WHERE username='admin'").fetchone()
    if not existing:
        db.execute(
            "INSERT INTO utilizatori (username, nume_complet, parola_hash, rol) VALUES (?,?,?,?)",
            ("admin", "Administrator", hash_password("admin123"), "admin")
        )
        # Sample data
        db.executescript("""
            INSERT OR IGNORE INTO persoane (nume_complet, grupa_securitate, functia) VALUES
                ('Ion Popescu', 'IV', 'Inginer sector'),
                ('Maria Ionescu', 'III', 'Electrician'),
                ('Vasile Rusu', 'IV', 'Șef echipă'),
                ('Alexandru Popa', 'III', 'Electrician'),
                ('Nicolae Botnaru', 'V', 'Admitent');

            INSERT OR IGNORE INTO tipuri_lucrari (denumire) VALUES
                ('Înlocuire contor electric'),
                ('Verificare instalație electrică'),
                ('Reparație linie aeriană'),
                ('Montare branșament'),
                ('Revizie echipament de măsură'),
                ('Deconectare/Reconectare consumator');
        """)
    db.commit()
    db.close()
