"""Dados mockados do ComparaAI (Fase 1: só geladeiras) — usado por `seed.py`.

Preços e histórico são gerados por código (não digitados um a um) a partir
de um preço-base por produto + uma variação por loja, com seed fixa
(reprodutível — mesmo resultado toda vez que `seed.py` roda, útil pra
comparar antes/depois de uma mudança).
"""
import random
from datetime import datetime, timedelta
from decimal import Decimal

from app import db
from app.models import Category, PriceHistory, Price, Product, Store, slugify

random.seed(42)

CATEGORIAS = [
    {"name": "Geladeiras", "slug": "geladeiras", "icon": "refrigerator", "active": True},
    {"name": "Fogões", "slug": "fogoes", "icon": "flame", "active": False},
    {"name": "Lava-louças", "slug": "lava-loucas", "icon": "utensils", "active": False},
    {"name": "Micro-ondas", "slug": "micro-ondas", "icon": "microwave", "active": False},
]

LOJAS = [
    {
        "name": "Amazon",
        "type": Store.TIPO_ONLINE,
        "website_url": "https://www.amazon.com.br",
        "logo_url": "/static/img/lojas/amazon.svg",
        "trust_score": 4.6,
    },
    {
        "name": "Magazine Luiza",
        "type": Store.TIPO_ONLINE,
        "website_url": "https://www.magazineluiza.com.br",
        "logo_url": "/static/img/lojas/magalu.svg",
        "trust_score": 4.4,
    },
    {
        "name": "Casas Bahia",
        "type": Store.TIPO_ONLINE,
        "website_url": "https://www.casasbahia.com.br",
        "logo_url": "/static/img/lojas/casasbahia.svg",
        "trust_score": 4.1,
    },
    {
        "name": "Loja Oficial da Marca",
        "type": Store.TIPO_ONLINE,
        "website_url": "https://www.electrolux.com.br",
        "logo_url": "/static/img/lojas/marca-oficial.svg",
        "trust_score": 4.7,
    },
    {
        "name": "Bemol",
        "type": Store.TIPO_FISICA,
        "city": "Manaus",
        "website_url": "https://www.bemol.com.br",
        "logo_url": "/static/img/lojas/bemol.svg",
        "trust_score": 4.5,
    },
    {
        "name": "Eletro Norte",
        "type": Store.TIPO_FISICA,
        "city": "Manaus",
        "website_url": None,
        "logo_url": "/static/img/lojas/eletro-norte.svg",
        "trust_score": 3.9,
    },
]

# Preço-base (R$) + specs de cada geladeira. Marcas do brief: Electrolux,
# Brastemp, Consul, Samsung, LG — variando capacidade/frost-free/cor pra
# dar variedade real de filtro (não só o mesmo produto 10 vezes).
#
# `bemol_real` (quando presente): foto + preço + estoque + URL REAIS,
# achados buscando o catálogo de verdade da Bemol (sitemap público +
# extração via JSON-LD, ver app/services/atualizacao_precos.py) — pedido
# do usuário ("quero ser redirecionado pro site" + "todos com foto").
# Não é o MESMO modelo exato do nosso catálogo mockado (ex: nosso "DF44"
# vira o "DFN41" real mais parecido em capacidade/linha) — aproximação
# deliberada, documentada, não uma correspondência 1:1 garantida.
# LG não apareceu em ~80 sitemaps de produto verificados (Bemol
# provavelmente não vende essa marca) — os 2 produtos LG ficam sem
# `bemol_real` de propósito (foto cai no ícone placeholder, não uma foto
# fingindo ser de um produto que não existe).
PRODUTOS = [
    {
        "brand": "Electrolux", "model": "DF44", "nome_curto": "Frost Free 382L",
        "preco_base": 2799.00,
        "specs": {"capacidade_litros": 382, "frost_free": True, "cor": "Branca",
                   "voltagem": "220V", "dimensoes_cm": "179 x 68 x 68", "consumo_kwh_mes": 38.6},
        "bemol_real": {
            "url": "https://www.bemol.com.br/geladeira-electrolux-frost-free-371l-funcao-drink-express-duplex-127v-branca-dfn41/p",
            "preco": 3179.00, "em_estoque": False,
            "imagem": "https://bemol.vtexassets.com/arquivos/ids/483967/192150-9.jpg?v=639093423065830000",
        },
    },
    {
        "brand": "Electrolux", "model": "IF55", "nome_curto": "Inverter Duplex 490L",
        "preco_base": 4599.00,
        "specs": {"capacidade_litros": 490, "frost_free": True, "cor": "Inox",
                   "voltagem": "Bivolt", "dimensoes_cm": "186 x 70 x 73", "consumo_kwh_mes": 42.1},
        "bemol_real": {
            "url": "https://www.bemol.com.br/geladeira-electrolux-frost-free-490-litros-efficient-com-autosense-inverse-inox-look-ib7s/p",
            "preco": 5768.00, "em_estoque": True,
            "imagem": "https://bemol.vtexassets.com/arquivos/ids/613701/238944.jpg?v=639167831135570000",
        },
    },
    {
        "brand": "Brastemp", "model": "BRM44", "nome_curto": "Frost Free 375L",
        "preco_base": 2649.00,
        "specs": {"capacidade_litros": 375, "frost_free": True, "cor": "Branca",
                   "voltagem": "127V", "dimensoes_cm": "177 x 67 x 67", "consumo_kwh_mes": 37.9},
        "bemol_real": {
            "url": "https://www.bemol.com.br/geladeira-brastemp-frost-free-duplex-375-litros-compartimento-extrafrio-inox-brm44hk/p",
            "preco": 3449.00, "em_estoque": False,
            "imagem": "https://bemol.vtexassets.com/arquivos/ids/398580/194468.jpg?v=639090093114030000",
        },
    },
    {
        "brand": "Brastemp", "model": "BRE80", "nome_curto": "Inverse Frost Free 573L",
        "preco_base": 5899.00,
        "specs": {"capacidade_litros": 573, "frost_free": True, "cor": "Inox",
                   "voltagem": "220V", "dimensoes_cm": "191 x 91 x 71", "consumo_kwh_mes": 48.3},
        "bemol_real": {
            "url": "https://www.bemol.com.br/geladeira-brastemp-frost-free-inverse-side-554-litros-inox-bro85ak/p",
            "preco": 7859.00, "em_estoque": False,
            "imagem": "https://bemol.vtexassets.com/arquivos/ids/519181/223947_a.jpg?v=639096960327000000",
        },
    },
    {
        "brand": "Consul", "model": "CRB39", "nome_curto": "Frost Free 340L",
        "preco_base": 2299.00,
        "specs": {"capacidade_litros": 340, "frost_free": True, "cor": "Branca",
                   "voltagem": "127V", "dimensoes_cm": "170 x 66 x 66", "consumo_kwh_mes": 35.2},
        "bemol_real": {
            "url": "https://www.bemol.com.br/geladeira-consul-frost-free-342-litros-gavetao-hortifruti-branca-crb39ab/p",
            "preco": 3119.00, "em_estoque": False,
            "imagem": "https://bemol.vtexassets.com/arquivos/ids/409316/120334-7.jpg?v=639096891458630000",
        },
    },
    {
        "brand": "Consul", "model": "CRM50", "nome_curto": "Duplex Frost Free 450L",
        "preco_base": 3399.00,
        "specs": {"capacidade_litros": 450, "frost_free": True, "cor": "Branca",
                   "voltagem": "220V", "dimensoes_cm": "183 x 70 x 69", "consumo_kwh_mes": 40.0},
        "bemol_real": {
            "url": "https://www.bemol.com.br/geladeira-consul-frost-free-300-litros-freezer-supercapacidade-branca-crb36ab/p",
            "preco": 2449.00, "em_estoque": False,
            "imagem": "https://bemol.vtexassets.com/arquivos/ids/409307/120332.jpg?v=639096889477570000",
        },
    },
    {
        "brand": "Samsung", "model": "RT46", "nome_curto": "Frost Free Inverter 460L",
        "preco_base": 4299.00,
        "specs": {"capacidade_litros": 460, "frost_free": True, "cor": "Inox",
                   "voltagem": "220V", "dimensoes_cm": "182 x 70 x 74", "consumo_kwh_mes": 39.5},
        "bemol_real": {
            "url": "https://www.bemol.com.br/geladeira-samsung-duplex-rt42-evolution-com-smartthings-ai-inox-bivolt-415l/p",
            "preco": 3959.00, "em_estoque": True,
            "imagem": "https://bemol.vtexassets.com/arquivos/ids/398739/240859.jpg?v=639105809594570000",
        },
    },
    {
        "brand": "Samsung", "model": "RF50", "nome_curto": "French Door 501L",
        "preco_base": 7499.00,
        "specs": {"capacidade_litros": 501, "frost_free": True, "cor": "Inox",
                   "voltagem": "Bivolt", "dimensoes_cm": "179 x 91 x 74", "consumo_kwh_mes": 45.7},
        "bemol_real": {
            "url": "https://www.bemol.com.br/geladeira-samsung-smart-french-door-dispenser-de-aguia-e-gelo-550-litros-inox-rf26/p",
            "preco": 11169.00, "em_estoque": False,
            "imagem": "https://bemol.vtexassets.com/arquivos/ids/409223/241162.jpg?v=639093422531800000",
        },
    },
    {
        "brand": "LG", "model": "GC-B", "nome_curto": "Frost Free Inverter 395L",
        "preco_base": 3199.00,
        "specs": {"capacidade_litros": 395, "frost_free": True, "cor": "Branca",
                   "voltagem": "220V", "dimensoes_cm": "180 x 68 x 70", "consumo_kwh_mes": 36.8},
    },
    {
        "brand": "LG", "model": "GC-L", "nome_curto": "Side by Side 601L",
        "preco_base": 8299.00,
        "specs": {"capacidade_litros": 601, "frost_free": True, "cor": "Inox",
                   "voltagem": "Bivolt", "dimensoes_cm": "179 x 91 x 73", "consumo_kwh_mes": 51.4},
    },
]

DIAS_DE_HISTORICO = 30


def _preco_com_variacao(base: float, variacao_pct: float) -> Decimal:
    valor = base * (1 + variacao_pct)
    # preço "redondo" tipo e-commerce de verdade (termina em ,90 ou ,99)
    final = round(valor / 10) * 10 - 0.10
    return Decimal(str(round(final, 2)))


def popular_categorias() -> dict[str, Category]:
    mapa = {}
    for dados in CATEGORIAS:
        cat = Category(**dados)
        db.session.add(cat)
        mapa[cat.slug] = cat
    db.session.flush()
    return mapa


def popular_lojas() -> list[Store]:
    lojas = []
    for dados in LOJAS:
        loja = Store(**dados)
        db.session.add(loja)
        lojas.append(loja)
    db.session.flush()
    return lojas


def popular_produtos_e_precos(categoria_geladeiras: Category, lojas: list[Store]) -> list[Product]:
    loja_bemol = next((l for l in lojas if l.name == "Bemol"), None)

    produtos = []
    for dados in PRODUTOS:
        nome = f"{dados['brand']} {dados['nome_curto']}"
        real = dados.get("bemol_real")
        produto = Product(
            name=nome,
            brand=dados["brand"],
            model=dados["model"],
            category=categoria_geladeiras,
            specs=dados["specs"],
            # Foto REAL (achada no catálogo de verdade da Bemol) quando existe;
            # cai no ícone placeholder do template (produto.image_url vazio)
            # pros 2 produtos LG, que a Bemol não vende — nunca um caminho
            # de arquivo local fingindo ser foto de produto.
            image_url=(real["imagem"] if real else None),
            slug=slugify(f"{nome}-{dados['model']}"),
        )
        db.session.add(produto)
        produtos.append(produto)

        # 3 a 5 lojas por produto, sorteadas — sempre incluindo pelo menos
        # 1 loja física (Bemol/Eletro Norte), pra todo produto ter opção
        # online E física (o diferencial do produto, ver brief seção 1).
        # Quando temos dado REAL da Bemol pro produto, ela entra garantida
        # (não sorteada) — senão o dado real podia nem aparecer se o sorteio
        # escolhesse Eletro Norte em vez dela.
        lojas_online = [l for l in lojas if l.type == Store.TIPO_ONLINE]
        lojas_fisicas = [l for l in lojas if l.type == Store.TIPO_FISICA]
        n_online = random.randint(2, min(4, len(lojas_online)))
        selecionadas = random.sample(lojas_online, n_online)
        loja_fisica_escolhida = loja_bemol if (real and loja_bemol) else random.choice(lojas_fisicas)
        selecionadas.append(loja_fisica_escolhida)

        for loja in selecionadas:
            usar_dado_real = real is not None and loja is loja_bemol
            if usar_dado_real:
                preco = Decimal(str(real["preco"]))
                em_estoque = real["em_estoque"]
                url = real["url"]
                atualizado_ha_horas = random.randint(1, 6)  # dado "fresco", acabou de ser buscado de verdade
            else:
                variacao = random.uniform(-0.08, 0.12)  # loja mais barata até mais cara que a base
                preco = _preco_com_variacao(dados["preco_base"], variacao)
                em_estoque = random.random() > 0.08  # ~92% em estoque, resto "esgotado" (realismo)
                # SEM url sintética aqui de propósito — usuário reportou clicar
                # em "Ver oferta" e cair numa página 404 real da loja (ex:
                # amazon.com.br/produto/<slug-nosso>, que nunca existiu de
                # verdade). Só a Bemol (bloco `real` acima) tem URL confirmada
                # por scraping; as outras 5 lojas ficam sem link até termos
                # dado real de cada uma — produto.html mostra "Link em breve"
                # em vez de um botão que promete um destino que não existe.
                url = None
                atualizado_ha_horas = random.randint(1, 30)

            db.session.add(Price(
                product=produto,
                store=loja,
                price=preco,
                url=url,
                in_stock=em_estoque,
                last_updated=datetime.utcnow() - timedelta(hours=atualizado_ha_horas),
            ))
    db.session.flush()
    return produtos


def gerar_historico_de_precos(produtos: list[Product]) -> None:
    """Um ponto de histórico por dia, últimos 30 dias, por produto+loja —
    caminho aleatório suave começando ~10% ACIMA do preço atual (narrativa
    de "preço caiu" ao longo do mês, bom pro gráfico de demonstração) com
    ruído dia a dia, não uma reta perfeita."""
    hoje = datetime.utcnow()
    for produto in produtos:
        for preco_atual in produto.prices:
            preco_final = float(preco_atual.price)
            preco_inicial = preco_final * random.uniform(1.05, 1.15)
            for i in range(DIAS_DE_HISTORICO, -1, -1):
                progresso = 1 - (i / DIAS_DE_HISTORICO)  # 0 (30 dias atrás) -> 1 (hoje)
                tendencia = preco_inicial + (preco_final - preco_inicial) * progresso
                ruido = tendencia * random.uniform(-0.015, 0.015)
                valor = round(tendencia + ruido, 2)
                db.session.add(PriceHistory(
                    product_id=produto.id,
                    store_id=preco_atual.store_id,
                    price=Decimal(str(valor)),
                    recorded_at=hoje - timedelta(days=i),
                ))


def executar_seed() -> None:
    """Zera e repopula o banco inteiro — comportamento intencional (não
    incremental): um seed de dados mockados deve sempre convergir pro
    mesmo estado previsível, não acumular duplicatas a cada execução."""
    db.drop_all()
    db.create_all()

    categorias = popular_categorias()
    lojas = popular_lojas()
    produtos = popular_produtos_e_precos(categorias["geladeiras"], lojas)
    gerar_historico_de_precos(produtos)

    db.session.commit()

    total_precos = sum(len(p.prices) for p in produtos)
    # sem acento de propósito aqui — o console do Windows (cp1252/850) as
    # vezes exibe texto UTF-8 acentuado errado; os dados no banco continuam
    # UTF-8 corretos, isso e so pra nao confundir quem rodar `python seed.py`
    print(f"OK: {len(categorias)} categorias, {len(lojas)} lojas, {len(produtos)} produtos.")
    print(f"    {total_precos} precos (ofertas produto+loja).")
    print(f"    Historico: {DIAS_DE_HISTORICO + 1} pontos por oferta.")
