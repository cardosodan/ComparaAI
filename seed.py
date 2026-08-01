"""Popula o banco com dados mockados (Fase 1: geladeiras).

Uso:
    venv\\Scripts\\python.exe seed.py

Zera e recria as tabelas antes de popular (ver seed_data.executar_seed) —
rodar de novo não duplica nada, sempre converge pro mesmo estado.
"""
from app import create_app
from app.services.seed_data import executar_seed

app = create_app()

with app.app_context():
    executar_seed()
