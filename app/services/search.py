"""Lógica de busca de produtos — usada pelo autocomplete da home (Passo 4)
e pela página de resultados de busca (Passo 5), pra nunca ter duas
implementações de "o que combina com esse termo" divergindo uma da outra.
"""
from sqlalchemy import or_

from app.models import Category, Product


def buscar_produtos(termo: str, limite: int | None = None):
    """Busca por nome genérico ("geladeira") OU marca/modelo específico
    ("Electrolux", "RT46") — case-insensitive, combinando as duas formas
    de busca que o brief pede (seção 6.2) numa query só.

    "geladeira" não aparece em NENHUM Product.name/brand/model (os nomes
    são só "{marca} {modelo curto}", ex. "Electrolux Frost Free 382L") —
    é o nome da CATEGORIA. Sem o join com Category, a busca genérica que
    o brief pede como exemplo principal simplesmente não achava nada."""
    termo = (termo or "").strip()
    if not termo:
        return []

    padrao = f"%{termo}%"
    query = (
        Product.query.join(Category)
        .filter(
            or_(
                Product.name.ilike(padrao),
                Product.brand.ilike(padrao),
                Product.model.ilike(padrao),
                Category.name.ilike(padrao),
            )
        )
        .order_by(Product.name)
    )

    if limite:
        query = query.limit(limite)
    return query.all()
