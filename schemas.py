from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token: str
    user: dict

class PersoanaCreate(BaseModel):
    nume_complet: str
    grupa_securitate: Optional[str] = None
    functia: Optional[str] = None
    activ: Optional[int] = 1

class TipLucrareCreate(BaseModel):
    denumire: str
    activ: Optional[int] = 1

class FisaCreate(BaseModel):
    data_emitere: str
    sef_lucrari_id: int
    admitent_id: int
    adresa_postala: Optional[str] = None
    adresa_electrica: Optional[str] = None
    tip_lucrare_id: int
    membri_ids: List[int] = []

class FisaOut(BaseModel):
    id: int
    nr_ordine: int
    stare: str

class SemnareInceput(BaseModel):
    confirmat: bool

class SemnareFinal(BaseModel):
    confirmat: bool

class UtilizatorCreate(BaseModel):
    username: str
    nume_complet: str
    parola: str
    rol: str

class SchimbaParola(BaseModel):
    parola_noua: str
