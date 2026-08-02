"""Modelos de dados do ComparaAI — Passo 2.

Categoria > Produto > Preço (por loja) + Histórico de Preço (série
temporal, alimenta o gráfico da página de produto). Um `Product` nunca
guarda "o preço" diretamente — preço é sempre uma relação produto+loja
(`Price`), porque o objetivo central do produto é justamente comparar o
MESMO produto entre lojas diferentes.
"""
from datetime import datetime
from decimal import Decimal

from app import db


def slugify(texto: str) -> str:
    """Slug bem simples (nomes de produto/categoria aqui são só
    alfanuméricos + espaço, não precisa de biblioteca externa pra lidar
    com acentos/unicode)."""
    permitido = "abcdefghijklmnopqrstuvwxyz0123456789"
    texto = texto.lower().strip()
    saida = []
    ultimo_foi_hifen = False
    for ch in texto:
        if ch in permitido:
            saida.append(ch)
            ultimo_foi_hifen = False
        elif not ultimo_foi_hifen:
            saida.append("-")
            ultimo_foi_hifen = True
    return "".join(saida).strip("-")


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    icon = db.Column(db.String(50))  # nome do ícone Lucide (ver templates, Passo 3+)
    # Categorias "em breve" (fogões, lava-louças, micro-ondas) existem como
    # linha no banco mas sem nenhum Product de verdade — active=False é só
    # pra distinguir isso na home sem precisar de uma tabela/flag separada.
    active = db.Column(db.Boolean, default=True, nullable=False)

    products = db.relationship("Product", back_populates="category")

    def __repr__(self):
        return f"<Category {self.slug}>"


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    brand = db.Column(db.String(80), nullable=False)
    model = db.Column(db.String(80), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    # specs livre em JSON de propósito — cada categoria futura (fogão,
    # lava-louças...) tem um conjunto de especificações bem diferente de
    # geladeira, então uma coluna por spec exigiria alterar o schema a
    # cada categoria nova. Chaves usadas por geladeira, ver seed_data.py:
    # capacidade_litros, frost_free, cor, voltagem, dimensoes_cm, consumo_kwh_mes.
    specs = db.Column(db.JSON, default=dict, nullable=False)
    image_url = db.Column(db.String(300))
    slug = db.Column(db.String(220), unique=True, nullable=False)

    category = db.relationship("Category", back_populates="products")
    prices = db.relationship(
        "Price", back_populates="product", cascade="all, delete-orphan", order_by="Price.price"
    )
    price_history = db.relationship(
        "PriceHistory", back_populates="product", cascade="all, delete-orphan"
    )

    @property
    def precos_em_estoque(self):
        return [p for p in self.prices if p.in_stock]

    @property
    def price_min(self):
        precos = self.precos_em_estoque or self.prices
        return min((p.preco_atual for p in precos), default=None)

    @property
    def price_max(self):
        precos = self.precos_em_estoque or self.prices
        return max((p.preco_atual for p in precos), default=None)

    @property
    def melhor_oferta(self):
        """A oferta mais barata em estoque — usada pro badge "Melhor preço".
        Compara por `preco_atual` (não `price` puro), então uma promoção
        vencida não engana a comparação achando que ainda é a mais barata."""
        precos = self.precos_em_estoque
        if not precos:
            return None
        return min(precos, key=lambda p: p.preco_atual)

    def __repr__(self):
        return f"<Product {self.brand} {self.model}>"


class Store(db.Model):
    __tablename__ = "stores"

    TIPO_ONLINE = "online"
    TIPO_FISICA = "fisica"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    logo_url = db.Column(db.String(300))
    website_url = db.Column(db.String(300))
    type = db.Column(db.String(10), nullable=False)  # Store.TIPO_ONLINE | Store.TIPO_FISICA
    city = db.Column(db.String(80))  # só preenchido quando type == TIPO_FISICA
    trust_score = db.Column(db.Float)  # 0-5, opcional (futuro)

    prices = db.relationship("Price", back_populates="store")

    def __repr__(self):
        return f"<Store {self.name}>"


class Price(db.Model):
    """Preço ATUAL de um produto numa loja — uma linha por par
    produto+loja. Histórico de verdade fica em `PriceHistory`."""

    __tablename__ = "prices"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    # Promoção temporária (pedido do usuário: "risquinho no preço original +
    # preço com desconto bem chamativo, e quando acabar a promoção volta ao
    # normal"). Os dois só têm sentido juntos: `original_price` é o preço
    # "de", `price` continua sendo o preço "por" (atual/com desconto)
    # enquanto a promoção estiver ativa. `promo_valid_until` nulo = sem
    # prazo conhecido (promoção considerada ativa indefinidamente, até
    # alguém atualizar os campos na mão ou um scrape real sobrescrever).
    original_price = db.Column(db.Numeric(10, 2))
    promo_valid_until = db.Column(db.DateTime)
    # Desconto condicional à forma de pagamento (achado real: Carrefour
    # mostra um preço "de cartão" e um preço menor "à vista no PIX" — não é
    # a mesma coisa que uma promoção de tabela, já que quem paga no cartão/
    # boleto continua pagando o preço original). Só muda o TEXTO do selo no
    # template ("-X% no PIX" em vez de só "-X%") — a lógica de
    # `promocao_ativa`/`preco_atual` é idêntica pros dois casos.
    promo_pix = db.Column(db.Boolean, default=False, nullable=False)
    url = db.Column(db.String(400))
    in_stock = db.Column(db.Boolean, default=True, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    product = db.relationship("Product", back_populates="prices")
    store = db.relationship("Store", back_populates="prices")

    __table_args__ = (db.UniqueConstraint("product_id", "store_id", name="uq_price_produto_loja"),)

    @property
    def promocao_ativa(self) -> bool:
        """Só é promoção de verdade se o preço original for maior que o
        atual (não um dado inconsistente) E o prazo (quando existe) ainda
        não passou."""
        if not self.original_price or self.original_price <= self.price:
            return False
        if self.promo_valid_until is not None and self.promo_valid_until <= datetime.utcnow():
            return False
        return True

    @property
    def preco_atual(self) -> Decimal:
        """Preço efetivo pra exibir/comparar. Quando a promoção tem prazo
        gravado e ele já passou, volta pro preço original SOZINHO — não
        depende de nenhum job/cron reescrever `price`, só de alguém abrir
        a página depois do prazo (a checagem acontece na hora, a cada
        acesso)."""
        if self.original_price is not None and self.promo_valid_until is not None \
                and self.promo_valid_until <= datetime.utcnow():
            return self.original_price
        return self.price

    @property
    def percentual_desconto(self) -> int | None:
        if not self.promocao_ativa:
            return None
        return round((1 - float(self.price) / float(self.original_price)) * 100)

    def __repr__(self):
        return f"<Price {self.product_id}@{self.store_id} R${self.price}>"


class PriceHistory(db.Model):
    """Série temporal de preço — um ponto por dia (aprox.), usada só pelo
    gráfico da página de produto. Independente de `Price` de propósito:
    mesmo que uma loja pare de vender o produto (removida de `Price`), o
    histórico continua existindo."""

    __tablename__ = "price_history"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    recorded_at = db.Column(db.DateTime, nullable=False)

    product = db.relationship("Product", back_populates="price_history")
    store = db.relationship("Store")

    def __repr__(self):
        return f"<PriceHistory {self.product_id}@{self.store_id} {self.recorded_at:%Y-%m-%d} R${self.price}>"
