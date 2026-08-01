"""Rotas principais: home (Passo 4) + autocomplete de busca (Passo 4) +
stub da página de resultados (substituído de verdade no Passo 5).
"""
from flask import Blueprint, render_template, request

from app.models import Product
from app.services.search import buscar_produtos

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    # "Mais buscados": sem métrica de popularidade real ainda (Fase 1 é
    # dado mockado) — mostra uma seleção fixa dos produtos cadastrados,
    # documentado aqui pra não parecer que é ranking de verdade.
    mais_buscados = Product.query.order_by(Product.id).limit(6).all()
    return render_template("home.html", mais_buscados=mais_buscados)


@main_bp.route("/busca/sugestoes")
def busca_sugestoes():
    """Endpoint consumido pelo HTMX no campo de busca da home — devolve só
    o FRAGMENTO da lista de sugestões (não uma página inteira), pra
    injetar direto no dropdown abaixo do campo."""
    termo = request.args.get("q", "")
    sugestoes = buscar_produtos(termo, limite=6) if len(termo.strip()) >= 2 else []
    return render_template("components/_autocomplete_sugestoes.html", sugestoes=sugestoes, termo=termo)


@main_bp.route("/busca")
def busca():
    """Stub temporário — página de resultados de verdade (grid, filtros,
    ordenação) é o Passo 5. Existe agora só pra buscar a partir da home
    não cair num 404 durante a revisão deste passo."""
    termo = request.args.get("q", "")
    return render_template("_stub_em_construcao.html", titulo="Resultados da busca", passo="Passo 5", termo=termo)
