"""Página de detalhe do produto (Passo 6): especificações, tabela
comparativa de preços por loja, gráfico de histórico e produtos similares.
"""
from datetime import datetime

from flask import Blueprint, abort, render_template

from app.models import Product, Store
from app.services.pricing import (
    formatar_especificacoes,
    montar_historico_para_grafico,
    tempo_relativo,
    url_busca_de_apoio,
)
from app.services.search import produtos_similares

product_bp = Blueprint("product", __name__)


@product_bp.route("/produto/<slug>")
def detalhe(slug):
    produto = Product.query.filter_by(slug=slug).first()
    if produto is None:
        abort(404)

    agora = datetime.utcnow()
    menor_preco_em_estoque = produto.melhor_oferta.price if produto.melhor_oferta else None

    # Mais barata primeiro; esgotadas por último (não fazem sentido no topo
    # de uma tabela comparativa de "onde comprar agora").
    ofertas = []
    for preco in sorted(produto.prices, key=lambda p: (not p.in_stock, p.price)):
        ofertas.append({
            "loja": preco.store,
            "preco": preco.price,
            "url": preco.url,
            # Fallback só quando não há link direto confirmado (ver
            # url_busca_de_apoio) — mantém a tabela sem nenhum botão morto.
            "url_busca": None if preco.url else url_busca_de_apoio(preco.store, produto),
            "em_estoque": preco.in_stock,
            "atualizado_ha": tempo_relativo(preco.last_updated, agora),
            "frete": "Retirada na loja" if preco.store.type == Store.TIPO_FISICA else "Consulte o site",
            "eh_melhor_oferta": preco.in_stock and menor_preco_em_estoque is not None and preco.price == menor_preco_em_estoque,
        })

    return render_template(
        "produto.html",
        produto=produto,
        ofertas=ofertas,
        especificacoes=formatar_especificacoes(produto.specs),
        historico=montar_historico_para_grafico(produto),
        similares=produtos_similares(produto, limite=4),
    )
