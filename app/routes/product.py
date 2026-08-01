"""Página de detalhe do produto — stub temporário (a versão de verdade,
com tabela comparativa de preços e gráfico de histórico, é o Passo 6).
Existe agora só pra um clique no autocomplete/card da home não cair num
404 durante a revisão deste passo.
"""
from flask import Blueprint, abort, render_template

from app.models import Product

product_bp = Blueprint("product", __name__)


@product_bp.route("/produto/<slug>")
def detalhe(slug):
    produto = Product.query.filter_by(slug=slug).first()
    if produto is None:
        abort(404)
    return render_template(
        "_stub_em_construcao.html",
        titulo=produto.name,
        passo="Passo 6",
        termo=None,
    )
