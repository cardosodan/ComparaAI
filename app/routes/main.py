"""Rotas principais (home, busca, resultados) — Passos 4/5 da implementação.

Por enquanto só a rota de verificação do Passo 1 (`/`), confirmando que o
Flask sobe e o Tailwind compilado está sendo servido corretamente. Vai ser
substituída pela home de verdade no Passo 4.
"""
from flask import Blueprint, render_template

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("_setup_check.html")
