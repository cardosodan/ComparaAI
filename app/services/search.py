"""Lógica de busca/filtragem de produtos — usada pelo autocomplete da home
(Passo 4) e pela página de resultados (Passo 5), pra nunca ter duas
implementações de "o que combina com esse termo" divergindo uma da outra.
"""
from sqlalchemy import or_

from app.models import Category, Price, Product, Store


def _filtrar_por_texto(query, termo: str):
    """"geladeira" não aparece em NENHUM Product.name/brand/model (os
    nomes são só "{marca} {modelo curto}") — é o nome da CATEGORIA. Sem o
    join com Category, a busca genérica que o brief pede como exemplo
    principal simplesmente não achava nada (bug real, achado testando no
    Passo 4)."""
    padrao = f"%{termo}%"
    return query.join(Category).filter(
        or_(
            Product.name.ilike(padrao),
            Product.brand.ilike(padrao),
            Product.model.ilike(padrao),
            Category.name.ilike(padrao),
        )
    )


def buscar_produtos(termo: str, limite: int | None = None):
    """Busca simples (só texto) — usada pelo autocomplete, que não precisa
    de nenhum dos filtros da página de resultados."""
    termo = (termo or "").strip()
    if not termo:
        return []
    query = _filtrar_por_texto(Product.query, termo).order_by(Product.name)
    if limite:
        query = query.limit(limite)
    return query.all()


def filtrar_produtos(
    termo: str | None = None,
    marcas: list[str] | None = None,
    tipos_loja: list[str] | None = None,
    frost_free: bool | None = None,
    preco_min: float | None = None,
    preco_max: float | None = None,
    capacidade_min: float | None = None,
    capacidade_max: float | None = None,
    ordenar: str = "relevante",
):
    """Página de resultados (Passo 5) — todos os filtros do brief (seção
    6.2) numa função só. Marca e tipo de loja filtram no BANCO (colunas
    reais); capacidade e frost_free filtram em PYTHON depois de buscar
    (specs é JSON — extrair isso via SQL é sintaxe diferente entre
    SQLite/Postgres, e o projeto quer trocar de banco sem dor de cabeça,
    ver config.py). Preço também é calculado em Python porque price_min
    é uma property (menor oferta EM ESTOQUE), não uma coluna."""
    query = Product.query
    if termo:
        query = _filtrar_por_texto(query, termo)
    if marcas:
        query = query.filter(Product.brand.in_(marcas))
    if tipos_loja:
        query = query.join(Price).join(Store).filter(Store.type.in_(tipos_loja)).distinct()

    produtos = query.all()

    resultado = []
    for produto in produtos:
        if frost_free is not None and produto.specs.get("frost_free") != frost_free:
            continue

        capacidade = produto.specs.get("capacidade_litros")
        if capacidade_min is not None and (capacidade is None or capacidade < capacidade_min):
            continue
        if capacidade_max is not None and (capacidade is None or capacidade > capacidade_max):
            continue

        preco = produto.price_min
        if preco is None:
            continue  # sem nenhuma oferta em estoque — não faz sentido aparecer numa busca
        if preco_min is not None and float(preco) < preco_min:
            continue
        if preco_max is not None and float(preco) > preco_max:
            continue

        resultado.append(produto)

    if ordenar == "menor_preco":
        resultado.sort(key=lambda p: p.price_min)
    elif ordenar == "maior_preco":
        resultado.sort(key=lambda p: p.price_min, reverse=True)
    # "relevante" (default): mantém a ordem de Product.name — sem métrica
    # de relevância de verdade ainda (viria de popularidade/cliques reais).

    return resultado


def listar_marcas_disponiveis() -> list[str]:
    """Marcas distintas cadastradas — popula os checkboxes do filtro sem
    hardcoded (marca nova cadastrada aparece sozinha, mesmo princípio já
    usado pra categorias no navbar)."""
    linhas = Product.query.with_entities(Product.brand).distinct().order_by(Product.brand).all()
    return [linha[0] for linha in linhas]


def produtos_similares(produto: Product, limite: int = 4):
    """"Produtos similares" no rodapé da página de produto (brief seção
    6.3) — mesma categoria, ordenado pelo preço mais PRÓXIMO do produto
    atual primeiro. É uma aproximação por faixa de preço, não uma
    similaridade de especificação/comportamento de usuário de verdade
    (não existe dado nenhum disso ainda)."""
    candidatos = Product.query.filter(
        Product.category_id == produto.category_id,
        Product.id != produto.id,
    ).all()
    preco_referencia = float(produto.price_min or 0)
    candidatos.sort(key=lambda p: abs(float(p.price_min or 0) - preco_referencia))
    return candidatos[:limite]
