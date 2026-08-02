"""Rotas principais: home (Passo 4) + autocomplete de busca (Passo 4) +
resultados de busca com filtros (Passo 5).
"""
from flask import Blueprint, render_template, request

from app.models import Category, Product
from app.services.search import buscar_produtos, filtrar_produtos, listar_marcas_disponiveis

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    # "Mais buscados": sem métrica de popularidade real ainda (Fase 1 é
    # dado mockado) — mostra uma seleção fixa dos produtos cadastrados,
    # documentado aqui pra não parecer que é ranking de verdade. Pega
    # alguns de CADA categoria ativa (não só os 6 primeiros por ID) —
    # sem isso, assim que uma 2ª categoria ganhasse produtos de verdade,
    # ela nunca apareceria aqui (os IDs das Geladeiras, cadastradas
    # primeiro, sempre vêm antes).
    mais_buscados = []
    for categoria in Category.query.filter_by(active=True).order_by(Category.name).all():
        mais_buscados.extend(
            Product.query.filter_by(category_id=categoria.id).order_by(Product.id).limit(2).all()
        )
    return render_template("home.html", mais_buscados=mais_buscados)


@main_bp.route("/busca/sugestoes")
def busca_sugestoes():
    """Endpoint consumido pelo HTMX no campo de busca da home — devolve só
    o FRAGMENTO da lista de sugestões (não uma página inteira), pra
    injetar direto no dropdown abaixo do campo."""
    termo = request.args.get("q", "")
    sugestoes = buscar_produtos(termo, limite=6) if len(termo.strip()) >= 2 else []
    return render_template("components/_autocomplete_sugestoes.html", sugestoes=sugestoes, termo=termo)


def _float_ou_none(valor: str | None) -> float | None:
    if not valor:
        return None
    try:
        return float(valor)
    except ValueError:
        return None


@main_bp.route("/busca")
def busca():
    termo = request.args.get("q", "").strip()
    marcas_selecionadas = request.args.getlist("marca")
    tipos_loja_selecionados = request.args.getlist("tipo_loja")
    frost_free_param = request.args.get("frost_free") or ""
    ordenar = request.args.get("ordenar", "relevante")

    preco_min = _float_ou_none(request.args.get("preco_min"))
    preco_max = _float_ou_none(request.args.get("preco_max"))
    capacidade_min = _float_ou_none(request.args.get("capacidade_min"))
    capacidade_max = _float_ou_none(request.args.get("capacidade_max"))

    frost_free = {"sim": True, "nao": False}.get(frost_free_param)

    produtos = filtrar_produtos(
        termo=termo or None,
        marcas=marcas_selecionadas or None,
        tipos_loja=tipos_loja_selecionados or None,
        frost_free=frost_free,
        preco_min=preco_min,
        preco_max=preco_max,
        capacidade_min=capacidade_min,
        capacidade_max=capacidade_max,
        ordenar=ordenar,
    )

    contexto = dict(
        produtos=produtos,
        termo=termo,
        ordenar=ordenar,
        marcas_disponiveis=listar_marcas_disponiveis(),
        marcas_selecionadas=marcas_selecionadas,
        tipos_loja_selecionados=tipos_loja_selecionados,
        frost_free_param=frost_free_param,
        preco_min=request.args.get("preco_min", ""),
        preco_max=request.args.get("preco_max", ""),
        capacidade_min=request.args.get("capacidade_min", ""),
        capacidade_max=request.args.get("capacidade_max", ""),
    )

    # Requisição vinda do HTMX (mudança de filtro/ordenação): devolve só o
    # miolo (contador + grid), sem repetir navbar/footer/head inteiros.
    if request.headers.get("HX-Request"):
        return render_template("components/_resultados_conteudo.html", **contexto)
    return render_template("resultados.html", **contexto)
