"""Painel admin simples de edição manual de preços (Passo 8) — atualização
manual pra emergências, não a fonte principal de preço (isso vem do
scraping automático, ver atualizacao_precos.py).

Login por sessão (pedido explícito do usuário: usuário "admin", senha
"admin12345", configuráveis via ADMIN_USERNAME/ADMIN_PASSWORD — ver
config.py). Comparação com `hmac.compare_digest` (não `==`) pra não
vazar quanto da string bateu certo através do tempo de resposta — barato
de fazer, sem custo de legibilidade, então sem motivo pra pular mesmo
sendo um único usuário fixo. Sessão guarda só um booleano
(`admin_logado`), nunca a senha em si.
"""
import hmac
from datetime import datetime
from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app import db
from app.models import Price, Product
from config import Config

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def login_necessario(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logado"):
            return redirect(url_for("admin.login"))
        return view(*args, **kwargs)
    return wrapper


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


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "")
        senha = request.form.get("senha", "")
        usuario_ok = hmac.compare_digest(usuario, Config.ADMIN_USERNAME)
        senha_ok = hmac.compare_digest(senha, Config.ADMIN_PASSWORD)
        if usuario_ok and senha_ok:
            session["admin_logado"] = True
            return redirect(url_for("admin.listar_precos"))
        flash("Usuário ou senha incorretos.", "erro")
    return render_template("admin_login.html")


@admin_bp.route("/logout")
def logout():
    session.pop("admin_logado", None)
    return redirect(url_for("admin.login"))


@admin_bp.route("", strict_slashes=False)
@login_necessario
def listar_precos():
    produtos = Product.query.order_by(Product.brand, Product.name).all()
    return render_template("admin_precos.html", produtos=produtos)


@admin_bp.route("/<int:price_id>/editar", methods=["POST"])
@login_necessario
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
