"""Configuração central do ComparaAI — lê variáveis de ambiente (.env) e
define os defaults de desenvolvimento local (SQLite), pra trocar por
Postgres em produção sem tocar em nenhum outro lugar do código (a
abstração do SQLAlchemy cuida disso, ver README).
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-troque-em-producao")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'comparaai.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
