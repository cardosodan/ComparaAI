"""Configuração central do ComparaAI — lê variáveis de ambiente (.env) e
define os defaults de desenvolvimento local (SQLite), pra trocar por
Postgres em produção sem tocar em nenhum outro lugar do código (a
abstração do SQLAlchemy cuida disso, ver README).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# python-dotenv já era dependência (requirements.txt) mas nunca era
# carregado de verdade — sem essa chamada, .env nunca chegava a virar
# variável de ambiente de verdade, então GROQ_API_KEY (e qualquer outra
# var só definida no .env) nunca era lida.
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-troque-em-producao"
    # "or" (não .get(key, default)) de propósito: .env costuma deixar
    # DATABASE_URL="" em branco (documentando a variável sem preenchê-la) —
    # depois que load_dotenv() passou a rodar de verdade, isso virava uma
    # string vazia em os.environ (chave EXISTE, só que vazia), e
    # os.environ.get(key, default) só cai no default quando a chave está
    # AUSENTE, não quando está vazia — sem o "or", o app tentava conectar
    # num banco "" e quebrava (achado rodando de verdade, não hipotético).
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or f"sqlite:///{BASE_DIR / 'comparaai.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    GROQ_API_KEY = os.environ.get("GROQ_API_KEY") or ""
