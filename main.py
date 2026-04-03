from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
import hashlib, secrets, os
from database import get_db, init_db
import crud, schemas
from pdf_generator import generate_monthly_pdf, generate_fisa_pdf
from fastapi.responses import StreamingResponse
import io

app = FastAPI(title="Registru Operativ API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

@app.on_event("startup")
async def startup():
    init_db()

# ─── AUTH ────────────────────────────────────────────────────────────────────

@app.post("/auth/login", response_model=schemas.LoginResponse)
def login(data: schemas.LoginRequest):
    db = get_db()
    user = crud.authenticate_user(db, data.username, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Credențiale incorecte")
    token = secrets.token_hex(32)
    crud.save_session(db, token, user["id"])
    return {"token": token, "user": user}

@app.post("/auth/logout")
def logout(creds: HTTPAuthorizationCredentials = Depends(security)):
    db = get_db()
    crud.delete_session(db, creds.credentials)
    return {"ok": True}

def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)):
    db = get_db()
    user = crud.get_session_user(db, creds.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Sesiune expirată")
    return user

# ─── NOMENCLATOARE ───────────────────────────────────────────────────────────

@app.get("/nomenclator/persoane")
def get_persoane(current_user=Depends(get_current_user)):
    db = get_db()
    return crud.get_persoane(db)

@app.post("/nomenclator/persoane")
def add_persoana(data: schemas.PersoanaCreate, current_user=Depends(get_current_user)):
    if current_user["rol"] != "admin":
        raise HTTPException(status_code=403, detail="Acces interzis")
    db = get_db()
    return crud.add_persoana(db, data)

@app.put("/nomenclator/persoane/{id}")
def update_persoana(id: int, data: schemas.PersoanaCreate, current_user=Depends(get_current_user)):
    if current_user["rol"] != "admin":
        raise HTTPException(status_code=403, detail="Acces interzis")
    db = get_db()
    return crud.update_persoana(db, id, data)

@app.delete("/nomenclator/persoane/{id}")
def delete_persoana(id: int, current_user=Depends(get_current_user)):
    if current_user["rol"] != "admin":
        raise HTTPException(status_code=403, detail="Acces interzis")
    db = get_db()
    crud.delete_persoana(db, id)
    return {"ok": True}

@app.get("/nomenclator/lucrari")
def get_tipuri_lucrari(current_user=Depends(get_current_user)):
    db = get_db()
    return crud.get_tipuri_lucrari(db)

@app.post("/nomenclator/lucrari")
def add_tip_lucrare(data: schemas.TipLucrareCreate, current_user=Depends(get_current_user)):
    if current_user["rol"] != "admin":
        raise HTTPException(status_code=403, detail="Acces interzis")
    db = get_db()
    return crud.add_tip_lucrare(db, data)

@app.put("/nomenclator/lucrari/{id}")
def update_tip_lucrare(id: int, data: schemas.TipLucrareCreate, current_user=Depends(get_current_user)):
    if current_user["rol"] != "admin":
        raise HTTPException(status_code=403, detail="Acces interzis")
    db = get_db()
    return crud.update_tip_lucrare(db, id, data)

@app.delete("/nomenclator/lucrari/{id}")
def delete_tip_lucrare(id: int, current_user=Depends(get_current_user)):
    if current_user["rol"] != "admin":
        raise HTTPException(status_code=403, detail="Acces interzis")
    db = get_db()
    crud.delete_tip_lucrare(db, id)
    return {"ok": True}

# ─── FIȘE ────────────────────────────────────────────────────────────────────

@app.get("/fise")
def get_fise(luna: Optional[int] = None, an: Optional[int] = None, current_user=Depends(get_current_user)):
    db = get_db()
    return crud.get_fise(db, luna, an)

@app.get("/fise/{id}")
def get_fisa(id: int, current_user=Depends(get_current_user)):
    db = get_db()
    fisa = crud.get_fisa(db, id)
    if not fisa:
        raise HTTPException(status_code=404, detail="Fișa nu există")
    return fisa

@app.post("/fise", response_model=schemas.FisaOut)
def create_fisa(data: schemas.FisaCreate, current_user=Depends(get_current_user)):
    if current_user["rol"] not in ("emitent", "admin"):
        raise HTTPException(status_code=403, detail="Acces interzis")
    db = get_db()
    return crud.create_fisa(db, data, current_user["id"])

@app.put("/fise/{id}")
def update_fisa(id: int, data: schemas.FisaCreate, current_user=Depends(get_current_user)):
    if current_user["rol"] not in ("emitent", "admin"):
        raise HTTPException(status_code=403, detail="Acces interzis")
    db = get_db()
    fisa = crud.get_fisa(db, id)
    if not fisa:
        raise HTTPException(status_code=404, detail="Fișa nu există")
    if fisa["stare"] == "semnat":
        raise HTTPException(status_code=400, detail="Fișa semnată nu poate fi modificată")
    return crud.update_fisa(db, id, data)

@app.patch("/fise/{id}/anuleaza")
def anuleaza_fisa(id: int, current_user=Depends(get_current_user)):
    if current_user["rol"] not in ("emitent", "admin"):
        raise HTTPException(status_code=403, detail="Acces interzis")
    db = get_db()
    fisa = crud.get_fisa(db, id)
    if not fisa:
        raise HTTPException(status_code=404, detail="Fișa nu există")
    if fisa["stare"] == "semnat":
        raise HTTPException(status_code=400, detail="Fișa semnată nu poate fi anulată")
    return crud.set_stare_fisa(db, id, "anulat")

@app.patch("/fise/{id}/incepe")
def incepe_lucrarea(id: int, data: schemas.SemnareInceput, current_user=Depends(get_current_user)):
    if current_user["rol"] not in ("admitent", "admin"):
        raise HTTPException(status_code=403, detail="Acces interzis")
    db = get_db()
    fisa = crud.get_fisa(db, id)
    if not fisa:
        raise HTTPException(status_code=404, detail="Fișa nu există")
    if fisa["stare"] != "emis":
        raise HTTPException(status_code=400, detail="Fișa nu este în starea corectă")
    return crud.incepe_lucrarea(db, id, current_user["id"], data.confirmat)

@app.patch("/fise/{id}/finalizeaza")
def finalizeaza_lucrarea(id: int, data: schemas.SemnareFinal, current_user=Depends(get_current_user)):
    if current_user["rol"] not in ("admitent", "admin"):
        raise HTTPException(status_code=403, detail="Acces interzis")
    db = get_db()
    fisa = crud.get_fisa(db, id)
    if not fisa:
        raise HTTPException(status_code=404, detail="Fișa nu există")
    if fisa["stare"] != "in_lucru":
        raise HTTPException(status_code=400, detail="Lucrarea nu a fost începută")
    return crud.finalizeaza_lucrarea(db, id, current_user["id"], data.confirmat)

# ─── PDF ─────────────────────────────────────────────────────────────────────

@app.get("/pdf/lunar")
def pdf_lunar(luna: int, an: int, current_user=Depends(get_current_user)):
    db = get_db()
    fise = crud.get_fise(db, luna, an)
    pdf_bytes = generate_monthly_pdf(fise, luna, an)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=registru_{an}_{luna:02d}.pdf"}
    )

@app.get("/pdf/fisa/{id}")
def pdf_fisa(id: int, current_user=Depends(get_current_user)):
    db = get_db()
    fisa = crud.get_fisa(db, id)
    if not fisa:
        raise HTTPException(status_code=404, detail="Fișa nu există")
    pdf_bytes = generate_fisa_pdf(fisa)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=fisa_{id}.pdf"}
    )

# ─── UTILIZATORI (admin) ──────────────────────────────────────────────────────

@app.get("/utilizatori")
def get_utilizatori(current_user=Depends(get_current_user)):
    if current_user["rol"] != "admin":
        raise HTTPException(status_code=403, detail="Acces interzis")
    db = get_db()
    return crud.get_utilizatori(db)

@app.post("/utilizatori")
def create_utilizator(data: schemas.UtilizatorCreate, current_user=Depends(get_current_user)):
    if current_user["rol"] != "admin":
        raise HTTPException(status_code=403, detail="Acces interzis")
    db = get_db()
    return crud.create_utilizator(db, data)

@app.put("/utilizatori/{id}/parola")
def schimba_parola(id: int, data: schemas.SchimbaParola, current_user=Depends(get_current_user)):
    if current_user["rol"] != "admin" and current_user["id"] != id:
        raise HTTPException(status_code=403, detail="Acces interzis")
    db = get_db()
    crud.schimba_parola(db, id, data.parola_noua)
    return {"ok": True}
