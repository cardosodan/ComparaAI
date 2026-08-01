"""Painel admin simples de edição manual de preços (Passo 8) — SEM
autenticação ainda (brief seção 6.4 é explícito sobre isso: "não precisa
de auth ainda"). Simula o fluxo que uma loja física parceira vai usar no
futuro pra atualizar o próprio preço.

Limitação conhecida, documentada de propósito: como não tem login, esta
rota fica acessível a qualquer um que souber a URL — aceitável só porque
é Fase 1/dado mockado; autenticação de verdade é pré-requisito antes de
qualquer dado real entrar aqui.
"""
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app import db
from app.models import Price, Product

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _parsear_preco(texto: str) -> float | None:
    """Aceita tanto "2799.90" quanto "2799,90"/"2.799,90" (formato BR) —
    usuário de loja física digitando preço não deveria precisar pensar em
    qual separador decimal usar."""
    texto = (texto or "").strip().replace("R$", "").replace(" ", "")
    if not texto:
        return None
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        valor = float(texto)
    except ValueError:
        return None
    return valor if valor > 0 else None


@admin_bp.route("/precos")
def listar_precos():
    produtos = Product.query.order_by(Product.brand, Product.name).all()
    return render_template("admin_precos.html", produtos=produtos)


@admin_bp.route("/precos/<int:price_id>/editar", methods=["POST"])
def editar_preco(price_id):
    preco = db.get_or_404(Price, price_id)

    novo_preco = _parsear_preco(request.form.get("price", ""))
    if novo_preco is None:
        flash(f"Preço inválido pra {preco.product.name} — {preco.store.name}. Nada foi salvo.", "erro")
        return redirect(url_for("admin.listar_precos"))

    preco.price = novo_preco
    preco.in_stock = "in_stock" in request.form
    preco.last_updated = datetime.utcnow()
    db.session.commit()

    flash(f"Preço de {preco.product.name} na {preco.store.name} atualizado.", "sucesso")
    return redirect(url_for("admin.listar_precos"))
