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

# Magazine Luiza e Casas Bahia foram REMOVIDAS de propósito (rodada de
# revisão): as duas bloqueiam toda requisição automatizada, mesmo pra uma
# URL de produto real (confirmado com curl, WebFetch e até Playwright sem
# nenhum disfarce — ver histórico completo em atualizacao_precos.py e no
# README). Usuário pediu pra tirar as duas e substituir por lojas que não
# bloqueiam — Carrefour entrou no lugar (mesma plataforma VTEX de Bemol/
# Brastemp/Consul/Electrolux, robots.txt permite, JSON-LD funciona).
#
# "Loja Oficial da Marca" (um Store genérico só, reaproveitado por todo
# produto) também foi REMOVIDA — usuário pediu pra mostrar o nome real da
# marca em vez desse rótulo genérico. Virou 5 Stores distintos, um por
# marca (Electrolux/Brastemp/Consul/Samsung/LG), cada um só relevante pro
# produto da própria marca (ver popular_produtos_e_precos abaixo — a
# seleção de lojas por produto usa `Store.name == produto["brand"]`).
LOJAS = [
    {
        "name": "Amazon",
        "type": Store.TIPO_ONLINE,
        "website_url": "https://www.amazon.com.br",
        "logo_url": "/static/img/lojas/amazon.svg",
        "trust_score": 4.6,
    },
    {
        "name": "Carrefour",
        "type": Store.TIPO_ONLINE,
        "website_url": "https://www.carrefour.com.br",
        "logo_url": "/static/img/lojas/carrefour.svg",
        "trust_score": 4.3,
    },
    {
        "name": "Americanas",
        "type": Store.TIPO_ONLINE,
        "website_url": "https://www.americanas.com.br",
        "logo_url": "/static/img/lojas/americanas.svg",
        "trust_score": 4.2,
    },
    {
        "name": "Electrolux",
        "type": Store.TIPO_ONLINE,
        "website_url": "https://loja.electrolux.com.br",
        "logo_url": "/static/img/lojas/electrolux.svg",
        "trust_score": 4.7,
    },
    {
        "name": "Brastemp",
        "type": Store.TIPO_ONLINE,
        "website_url": "https://www.brastemp.com.br",
        "logo_url": "/static/img/lojas/brastemp.svg",
        "trust_score": 4.7,
    },
    {
        "name": "Consul",
        "type": Store.TIPO_ONLINE,
        "website_url": "https://www.consul.com.br",
        "logo_url": "/static/img/lojas/consul.svg",
        "trust_score": 4.6,
    },
    {
        # shop.samsung.com (não www.samsung.com — esse é o site
        # institucional/marketing, carregado por JS, o mesmo tipo de
        # limitação que a Electrolux tinha com www. vs loja.). A LOJA de
        # verdade é shop.samsung.com, também VTEX, com JSON-LD estático —
        # achada via WebSearch depois de ver esse domínio aparecer
        # repetidamente em buscas por produtos Samsung noutras lojas.
        "name": "Samsung",
        "type": Store.TIPO_ONLINE,
        "website_url": "https://shop.samsung.com/br",
        "logo_url": "/static/img/lojas/samsung.svg",
        "trust_score": 4.7,
    },
    {
        "name": "LG",
        "type": Store.TIPO_ONLINE,
        "website_url": "https://www.lg.com/br",
        "logo_url": "/static/img/lojas/lg.svg",
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
# `lojas_reais` (quando presente): dict {nome_da_loja: {...}} com dado REAL
# achado no catálogo de verdade daquela loja (sitemap público + extração
# via JSON-LD, mesma técnica de sempre, ver app/services/atualizacao_precos.py)
# — pedido do usuário ("quero ser redirecionado pro site" + "todos com
# foto" + depois "entre no produto específico, não só no site"). Nunca é o
# MESMO produto exato do nosso catálogo mockado, sempre o mais parecido em
# capacidade/linha que a loja de verdade vende — aproximação deliberada,
# documentada, não correspondência 1:1 garantida.
#
# As chaves possíveis são: "Bemol", o NOME DA PRÓPRIA MARCA (Electrolux/
# Brastemp/Consul/Samsung/LG — cada produto só usa a chave da sua própria
# marca, nunca a de outra) e "Carrefour". Magazine Luiza e Casas Bahia
# foram removidas do catálogo inteiro (bloqueiam toda requisição
# automatizada, mesmo com Playwright sem disfarce nenhum — ver
# atualizacao_precos.py e README) e substituídas pelo Carrefour, que não
# bloqueia.
#
# Cada entrada tem `url` (obrigatório) e, quando disponível, `imagem`/
# `preco`/`em_estoque`. Bemol/Brastemp/Consul/Electrolux (mesma plataforma
# VTEX) e Carrefour (idem, quando o catálogo dele não está com preço
# zerado — ver comentários pontuais abaixo) expõem os campos via JSON-LD.
# Samsung e LG **não publicam preço/estoque em lugar nenhum estático** — a
# busca por produto nessas duas confirmou que são sites carregados por
# JavaScript (o preço só aparece depois de uma chamada de API feita pelo
# navegador, invisível pra qualquer requisição HTTP simples) — resolvido
# com Playwright pra Samsung (não bloqueia automação), mas não pra LG
# (bloqueia com 403 via Akamai, mesma categoria de proteção anti-bot que
# já bloqueava Magazine Luiza/Casas Bahia). O que não tem preço/estoque
# real continua SIMULADO (`popular_produtos_e_precos` decide isso campo a
# campo, não é tudo ou nada). Ainda assim resolve o pedido central do
# usuário — entrar na página REAL e específica daquele produto — mesmo sem
# conseguir sincronizar preço ao vivo com essas marcas.
PRODUTOS = [
    {
        "brand": "Electrolux", "model": "DF44", "nome_curto": "Frost Free 382L",
        "preco_base": 2799.00,
        "specs": {"capacidade_litros": 382, "frost_free": True, "cor": "Branca",
                   "voltagem": "220V", "dimensoes_cm": "179 x 68 x 68", "consumo_kwh_mes": 38.6},
        "lojas_reais": {
            "Bemol": {
                "url": "https://www.bemol.com.br/geladeira-electrolux-frost-free-371l-funcao-drink-express-duplex-127v-branca-dfn41/p",
                "preco": 3179.00, "em_estoque": False,
                "imagem": "https://bemol.vtexassets.com/arquivos/ids/483967/192150-9.jpg?v=639093423065830000",
            },
            # Mesmo modelo DFN41 no site oficial da Electrolux (não
            # www.electrolux.com.br — esse é o site institucional/marketing,
            # sempre 503 pra qualquer busca; a loja de verdade é
            # loja.electrolux.com.br, achada via WebSearch, mesma
            # plataforma VTEX de Bemol/Brastemp/Consul).
            "Electrolux": {
                "url": "https://loja.electrolux.com.br/geladeira-refrigerador-frost-free-371-litros-dfn41/p",
                "preco": 3469.00, "em_estoque": True,
                "imagem": "https://electrolux.vtexassets.com/arquivos/ids/214052/Refrigerador_DFN41_Frontal_1000x1000_principal.jpg?v=638804364273430000",
            },
            # Mesmo modelo DFN41 no Carrefour — 1ª rodada de busca só achou
            # URLs "bonitas" (com o nome do produto no path) que 404avam;
            # usuário reportou clicar e cair na HOMEPAGE do Carrefour em vez
            # do produto (bug real — sem essa entrada, `url_busca_de_apoio`
            # caía no fallback de homepage). Achado com uma 2ª busca focada
            # no formato canônico `/produto/{slug}-{id}` — página real,
            # confirmada (200 + JSON-LD de Product), mas com "price": 0
            # (mesmo problema de catálogo visto em outros produtos no
            # Carrefour). Só `url`.
            "Carrefour": {
                "url": "https://www.carrefour.com.br/produto/geladeirarefrigerador-frost-free-electrolux-dfn-litros-branco-244624",
            },
            # Mesmo modelo DFN41 na Americanas — JSON-LD real (marketplace,
            # vários vendedores por produto; usei o preço do 1º vendedor
            # listado).
            "Americanas": {
                "url": "https://www.americanas.com.br/geladeira-electrolux-371-litros-frost-free-branco-dfn41-127v--h17i38691a352141/p",
                "preco": 3399.99, "em_estoque": False,
            },
        },
    },
    {
        "brand": "Electrolux", "model": "IF55", "nome_curto": "Inverter Duplex 490L",
        "preco_base": 4599.00,
        "specs": {"capacidade_litros": 490, "frost_free": True, "cor": "Inox",
                   "voltagem": "Bivolt", "dimensoes_cm": "186 x 70 x 73", "consumo_kwh_mes": 42.1},
        "lojas_reais": {
            "Bemol": {
                "url": "https://www.bemol.com.br/geladeira-electrolux-frost-free-490-litros-efficient-com-autosense-inverse-inox-look-ib7s/p",
                "preco": 5768.00, "em_estoque": True,
                "imagem": "https://bemol.vtexassets.com/arquivos/ids/613701/238944.jpg?v=639167831135570000",
            },
            # Mesmo modelo IB7S no site oficial da Electrolux (loja.electrolux.com.br).
            "Electrolux": {
                "url": "https://loja.electrolux.com.br/geladeira-electrolux-frost-free-490l-efficient-com-autosense-inverse-inox-look--ib7s-/p",
                "preco": 4399.00, "em_estoque": True,
                "imagem": "https://electrolux.vtexassets.com/arquivos/ids/288571/Refrigerator_IB7S_Front_Electrolux_Portuguese-1000x1000.raw.jpg?v=639046841437700000",
            },
            # Mesmo modelo IB7S no Carrefour (também VTEX) — JSON-LD achado,
            # mas com "price": 0 (dado de catálogo claramente quebrado nessa
            # listagem específica — visto o mesmo problema em vários outros
            # produtos no Carrefour). Só `url`, nunca um preço que a própria
            # página mostra como inválido.
            "Carrefour": {
                "url": "https://www.carrefour.com.br/geladeira-electrolux-frost-free-inverter-490l-inverse-inox-look-ib7s-mp955042852/p",
            },
            # Mesmo modelo IB7S na Americanas — JSON-LD achado, mas também
            # com "price": 0 (mesmo problema de catálogo). Só `url`.
            "Americanas": {
                "url": "https://www.americanas.com.br/geladeira-electrolux-frost-free-inverter-490l-inverse-inox-look-ib7s-7489466541/p",
            },
        },
    },
    {
        "brand": "Brastemp", "model": "BRM44", "nome_curto": "Frost Free 375L",
        "preco_base": 2649.00,
        "specs": {"capacidade_litros": 375, "frost_free": True, "cor": "Branca",
                   "voltagem": "127V", "dimensoes_cm": "177 x 67 x 67", "consumo_kwh_mes": 37.9},
        "lojas_reais": {
            "Bemol": {
                "url": "https://www.bemol.com.br/geladeira-brastemp-frost-free-duplex-375-litros-compartimento-extrafrio-inox-brm44hk/p",
                "preco": 3449.00, "em_estoque": False,
                "imagem": "https://bemol.vtexassets.com/arquivos/ids/398580/194468.jpg?v=639090093114030000",
            },
            # Mesmo modelo BRM44 de verdade, achado no sitemap oficial da Brastemp.
            "Brastemp": {
                "url": "https://www.brastemp.com.br/geladeira-brastemp-frost-free-375-litros-brm44hb/p",
                "preco": 3089.00, "em_estoque": False,
                "imagem": "https://brastemp.vtexassets.com/arquivos/ids/285442/01_Brastemp_Geladeira_BRM44HB_Imagem_Frontal_Fechada.jpg?v=639120439093400000",
            },
            # Mesmo modelo BRM44HB no Carrefour — JSON-LD real, em estoque.
            "Carrefour": {
                "url": "https://carrefour.com.br/geladeira-brastemp-frost-free-duplex-375-litros-com-compartimento-extrafrio-brm44hb-110v-5299802/p",
                "preco": 2848.39, "em_estoque": True,
                "imagem": "https://carrefourbr.vtexassets.com/arquivos/ids/181487971/image-0.jpg?v=638935408554630000",
            },
            # Mesmo modelo BRM44HB na Americanas — JSON-LD real (marketplace,
            # preço do vendedor mais barato entre os listados).
            "Americanas": {
                "url": "https://www.americanas.com.br/geladeira-brastemp-375-litros-frost-free-duplex-branco-brm44hb-220v-173b869f134f5194/p",
                "preco": 2749.00, "em_estoque": True,
            },
        },
    },
    {
        "brand": "Brastemp", "model": "BRE80", "nome_curto": "Inverse Frost Free 573L",
        "preco_base": 5899.00,
        "specs": {"capacidade_litros": 573, "frost_free": True, "cor": "Inox",
                   "voltagem": "220V", "dimensoes_cm": "191 x 91 x 71", "consumo_kwh_mes": 48.3},
        "lojas_reais": {
            "Bemol": {
                "url": "https://www.bemol.com.br/geladeira-brastemp-frost-free-inverse-side-554-litros-inox-bro85ak/p",
                "preco": 7859.00, "em_estoque": False,
                "imagem": "https://bemol.vtexassets.com/arquivos/ids/519181/223947_a.jpg?v=639096960327000000",
            },
            # BRE85AK (588L) é a Inverse mais próxima da nossa BRE80 (573L)
            # no catálogo oficial da Brastemp.
            "Brastemp": {
                "url": "https://www.brastemp.com.br/geladeira-brastemp-frost-free-inverse-588-litros-cor-inox-com-smart-bar-bre85ak/p",
                "preco": 6539.00, "em_estoque": False,
                "imagem": "https://brastemp.vtexassets.com/arquivos/ids/270753/Brastemp_Geladeira_BRE85AK_Imagem_Frontal_fechada_jpg_1.jpg?v=638996724145800000",
            },
            # Mesmo modelo BRE85AK no Carrefour — JSON-LD achado, mas com
            # "price": 0 (mesmo problema de catálogo do IB7S acima). Só `url`.
            "Carrefour": {
                "url": "https://www.carrefour.com.br/geladeira-brastemp-frost-free-inverse-588-litros-cor-inox-com-smart-bar-bre85ak-220v-mp929716281/p",
            },
            # Mesmo modelo BRE85AK na Americanas — JSON-LD achado, mas
            # também com "price": 0 (mesmo problema de catálogo). Só `url`.
            "Americanas": {
                "url": "https://www.americanas.com.br/geladeira-frost-free-inverse-2-portas-588-litros-bre85ak-brastemp-7462033239/p",
            },
        },
    },
    {
        "brand": "Consul", "model": "CRB39", "nome_curto": "Frost Free 340L",
        "preco_base": 2299.00,
        "specs": {"capacidade_litros": 340, "frost_free": True, "cor": "Branca",
                   "voltagem": "127V", "dimensoes_cm": "170 x 66 x 66", "consumo_kwh_mes": 35.2},
        "lojas_reais": {
            "Bemol": {
                "url": "https://www.bemol.com.br/geladeira-consul-frost-free-342-litros-gavetao-hortifruti-branca-crb39ab/p",
                "preco": 3119.00, "em_estoque": False,
                "imagem": "https://bemol.vtexassets.com/arquivos/ids/409316/120334-7.jpg?v=639096891458630000",
            },
            # Mesmo modelo CRB39 de verdade, achado no sitemap oficial da Consul.
            "Consul": {
                "url": "https://www.consul.com.br/geladeira-consul-frost-free-342-litros-evox-crb39ak/p",
                "preco": 2609.00, "em_estoque": False,
                "imagem": "https://consul.vtexassets.com/arquivos/ids/273738/01_Consul_Geladeira_CRB39AK_Imagem_Frontal_Frontal_png_3.jpg?v=639014052388430000",
            },
            # Mesmo modelo CRB39AB no Carrefour — JSON-LD real, em estoque.
            "Carrefour": {
                "url": "https://www.carrefour.com.br/geladeira-consul-frost-free-342-litros-branca-com-gavetao-hortifruti-crb39ab-110v-8950121/p",
                "preco": 3187.00, "em_estoque": True,
                "imagem": "https://carrefourbr.vtexassets.com/arquivos/ids/181487971/image-0.jpg?v=638935408554630000",
            },
            # Mesmo modelo CRB39AB na Americanas — JSON-LD real (marketplace,
            # preço do vendedor mais barato listado).
            "Americanas": {
                "url": "https://www.americanas.com.br/geladeira-consul-342-litros-frost-free-branco-crb39ab-127v-173g9z552j157793/p",
                "preco": 2499.00, "em_estoque": True,
            },
        },
    },
    {
        "brand": "Consul", "model": "CRM50", "nome_curto": "Duplex Frost Free 450L",
        "preco_base": 3399.00,
        "specs": {"capacidade_litros": 450, "frost_free": True, "cor": "Branca",
                   "voltagem": "220V", "dimensoes_cm": "183 x 70 x 69", "consumo_kwh_mes": 40.0},
        "lojas_reais": {
            "Bemol": {
                "url": "https://www.bemol.com.br/geladeira-consul-frost-free-300-litros-freezer-supercapacidade-branca-crb36ab/p",
                "preco": 2449.00, "em_estoque": False,
                "imagem": "https://bemol.vtexassets.com/arquivos/ids/409307/120332.jpg?v=639096889477570000",
            },
            # Mesmo modelo CRM50 de verdade, achado no sitemap oficial da Consul.
            "Consul": {
                "url": "https://www.consul.com.br/geladeira-consul-frost-free-duplex-com-espaco-flex-e-controle-interno-de-temperatura-410-litros-cor-branca-crm50fb/p",
                "preco": 3499.00, "em_estoque": False,
                "imagem": "https://consul.vtexassets.com/arquivos/ids/273875/01_Consul_Geladeira_CRM50FB_Imagem_Frontal_3--2-.jpg?v=639014100338000000",
            },
            # Mesmo modelo CRM50FB no Carrefour — JSON-LD achado, mas com
            # "price": 0 (mesmo problema de catálogo visto em outros
            # produtos no Carrefour). Só `url`.
            "Carrefour": {
                "url": "https://www.carrefour.com.br/geladeira-consul-crm50fb-frost-free-duplex-410l-mp934406719/p",
            },
            # Mesmo modelo CRM50FB na Americanas — JSON-LD achado, mas
            # também com "price": 0 (mesmo problema de catálogo). Só `url`.
            "Americanas": {
                "url": "https://www.americanas.com.br/geladeira-consul-frost-free-duplex-com-espaco-flex-410l-branca-crm50fb-7512217016/p",
            },
        },
    },
    {
        "brand": "Samsung", "model": "RT46", "nome_curto": "Frost Free Inverter 460L",
        "preco_base": 4299.00,
        "specs": {"capacidade_litros": 460, "frost_free": True, "cor": "Inox",
                   "voltagem": "220V", "dimensoes_cm": "182 x 70 x 74", "consumo_kwh_mes": 39.5},
        "lojas_reais": {
            "Bemol": {
                "url": "https://www.bemol.com.br/geladeira-samsung-duplex-rt42-evolution-com-smartthings-ai-inox-bivolt-415l/p",
                "preco": 3959.00, "em_estoque": True,
                "imagem": "https://bemol.vtexassets.com/arquivos/ids/398739/240859.jpg?v=639105809594570000",
            },
            # ACHADO IMPORTANTE: www.samsung.com (usado numa rodada anterior,
            # via Playwright) é só o site institucional/marketing, carregado
            # por JS — a LOJA de verdade é shop.samsung.com (também VTEX,
            # achada via WebSearch depois de aparecer repetida em buscas de
            # produto Samsung noutras lojas), com JSON-LD ESTÁTICO — nem
            # precisa de Playwright pra essa. "Evolution RT46 POWERvolt"
            # bate exato com o nosso model "RT46".
            "Samsung": {
                "url": "https://shop.samsung.com/br/geladeira-samsung-evolution-rt46-com-powervolt-inverter-duplex-460l/p",
                "preco": 4786.17, "em_estoque": False,
                "imagem": "https://samsungbrshop.vtexassets.com/arquivos/ids/225589/1.jpg?v=638369774580530000",
            },
            # Achada no Carrefour — JSON-LD achado, mas com "price": 0
            # (mesmo problema de catálogo). Só `url`.
            "Carrefour": {
                "url": "https://www.carrefour.com.br/geladeira-samsung-evolution-rt46-com-powervolt-inverter-duplex-460l-inox-look-bivolt-mp929908731/p",
            },
        },
    },
    {
        "brand": "Samsung", "model": "RF50", "nome_curto": "French Door 501L",
        "preco_base": 7499.00,
        "specs": {"capacidade_litros": 501, "frost_free": True, "cor": "Inox",
                   "voltagem": "Bivolt", "dimensoes_cm": "179 x 91 x 74", "consumo_kwh_mes": 45.7},
        "lojas_reais": {
            "Bemol": {
                "url": "https://www.bemol.com.br/geladeira-samsung-smart-french-door-dispenser-de-aguia-e-gelo-550-litros-inox-rf26/p",
                "preco": 11169.00, "em_estoque": False,
                "imagem": "https://bemol.vtexassets.com/arquivos/ids/409223/241162.jpg?v=639093422531800000",
            },
            # RF22R7351SR (501L French Door) bate exato com a capacidade da
            # nossa RF50 — em shop.samsung.com (a LOJA de verdade, JSON-LD
            # estático, ver comentário na RT46 acima), não www.samsung.com.
            "Samsung": {
                "url": "https://shop.samsung.com/br/geladeira-french-door-rf22r-inox-com-food-showcase-e-gaveta-flexzone-501-l/p",
                "preco": 22999.00, "em_estoque": False,
                "imagem": "https://samsungbrshop.vtexassets.com/arquivos/ids/174245/RF22R7351SRAZ_1.jpg?v=637360483544270000",
            },
            # Mesmo modelo RF22R7351SR no Carrefour — JSON-LD achado, mas
            # com "price": 0 (mesmo problema de catálogo). Só `url`.
            "Carrefour": {
                "url": "https://www.carrefour.com.br/produto/refrigeradorgeladeira-samsung-frost-free-0l-rfrsr-320224374",
            },
        },
    },
    {
        "brand": "LG", "model": "GC-B", "nome_curto": "Frost Free Inverter 395L",
        "preco_base": 3199.00,
        "specs": {"capacidade_litros": 395, "frost_free": True, "cor": "Branca",
                   "voltagem": "220V", "dimensoes_cm": "180 x 68 x 70", "consumo_kwh_mes": 36.8},
        # Sem entrada "Bemol" de propósito — LG não aparece no catálogo dela
        # (~80 sitemaps verificados, ver histórico acima). GN-B392PQWB
        # (395L Duplex) achado direto no site oficial da LG via busca —
        # preço/estoque também via JS lá (mesmo caso de Samsung). DIFERENTE
        # da Samsung, porém: tentei resolver com Playwright (mesma técnica
        # que funcionou pra Samsung) e o site da LG bloqueou com 403 via
        # Akamai (proteção anti-bot de verdade) — só não bloqueou minhas
        # requisições `requests`/curl simples usadas na busca inicial. Não
        # insisti (mesma decisão de não tentar burlar proteção nenhuma) —
        # só URL + imagem (og:image) reais, preço/estoque continuam
        # simulados.
        "lojas_reais": {
            "LG": {
                "url": "https://www.lg.com/br/geladeiras/geladeiras-duplex/gn-b392pqwb/",
                "imagem": "https://www.lg.com/content/dam/channel/wcms/br/images/geladeiras/gn-b392pqwb/gallery/Basic-450.jpg",
            },
            # Modelo próximo (GN-B392PLMB, mesma família 392/395L) no
            # Carrefour — JSON-LD real, em estoque.
            "Carrefour": {
                "url": "https://www.carrefour.com.br/geladeira-lg-2-portas-frost-free-inverter-395l-duplex-inox-look-110v-gnb392plmb-3376389/p",
                "preco": 3156.84, "em_estoque": True,
            },
            # Modelo próximo (GN-B392PLM) na Americanas — JSON-LD achado,
            # mas com "price": 0 (mesmo problema de catálogo). Só `url`.
            "Americanas": {
                "url": "https://www.americanas.com.br/geladeira-lg-frost-free-inverter-395l-duplex-inox-look-gn-b392plm-220v-17592d4yo3629823/p",
            },
        },
    },
    {
        "brand": "LG", "model": "GC-L", "nome_curto": "Side by Side 601L",
        "preco_base": 8299.00,
        "specs": {"capacidade_litros": 601, "frost_free": True, "cor": "Inox",
                   "voltagem": "Bivolt", "dimensoes_cm": "179 x 91 x 73", "consumo_kwh_mes": 51.4},
        # GC-L247SLUV (601L Side by Side) — mesmo prefixo "GC-L" do nosso
        # model e capacidade EXATAMENTE igual (601L). Mesma limitação de
        # preço/estoque via JS que a Samsung/GC-B.
        "lojas_reais": {
            "LG": {
                "url": "https://www.lg.com/br/geladeiras/lg-GC-L247SLUV-geladeira-side-by-side-601-litros",
                "imagem": "https://www.lg.com/content/dam/channel/wcms/br/images/geladeiras/gc-l247sluv_apzfsbs_essp_br_c/450_basic.jpg",
            },
            # GS65SDN1 (mesma capacidade 601L, Side by Side com ThinQ) no
            # Carrefour — JSON-LD real, em estoque.
            "Carrefour": {
                "url": "https://www.carrefour.com.br/geladeira-smart-lg-side-by-side-inverter-601-litros-inox-220v-com-door-in-door-e-lg-thinq-gs65sdn1-5122953/p",
                "preco": 12799.00, "em_estoque": True,
            },
        },
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
        lojas_reais = dados.get("lojas_reais", {})
        # Foto REAL (de qualquer loja que tenha uma) quando existe; cai no
        # ícone placeholder do template (produto.image_url vazio) só quando
        # NENHUMA loja com dado real tem foto pra esse produto — nunca um
        # caminho de arquivo local fingindo ser foto de produto.
        imagem_real = next((v["imagem"] for v in lojas_reais.values() if v.get("imagem")), None)
        produto = Product(
            name=nome,
            brand=dados["brand"],
            model=dados["model"],
            category=categoria_geladeiras,
            specs=dados["specs"],
            image_url=imagem_real,
            slug=slugify(f"{nome}-{dados['model']}"),
        )
        db.session.add(produto)
        produtos.append(produto)

        # Lojas online "universais" (Amazon, Carrefour, Americanas) —
        # comparar o máximo de ofertas possível é o pedido do usuário
        # ("quero que todos os produtos estejam com todos os links de
        # todas as marcas funcionando" + depois "eu queria ter mais opções
        # de lugares para comprar"), MAS Carrefour/Americanas só têm dado
        # real pra ALGUNS produtos (WebSearch não achou tudo) — incluir
        # elas em produto SEM entrada real repetiria o mesmo bug corrigido
        # 2x nesta sessão (Carrefour no Electrolux DF44, Bemol no LG): sem
        # `Price.url`, a oferta cai no fallback de HOMEPAGE, que parece um
        # link quebrado/sem sentido pro usuário. Por isso, diferente da
        # Amazon (busca sempre funciona, entra sempre), Carrefour/
        # Americanas só entram no produto onde JÁ existe uma URL real
        # confirmada em `lojas_reais` — garante estruturalmente que
        # NENHUMA oferta dessas duas caia em homepage, mesmo pra produto
        # futuro que eu esqueça de pesquisar.
        lojas_online = [l for l in lojas if l.type == Store.TIPO_ONLINE]
        lojas_fisicas = [l for l in lojas if l.type == Store.TIPO_FISICA]

        selecionadas = []
        for nome in ("Amazon", "Carrefour", "Americanas"):
            loja_universal = next((l for l in lojas_online if l.name == nome), None)
            if loja_universal and (nome == "Amazon" or nome in lojas_reais):
                selecionadas.append(loja_universal)

        loja_da_marca = next((l for l in lojas_online if l.name == dados["brand"]), None)
        if loja_da_marca:
            selecionadas.append(loja_da_marca)

        # LG nunca é sorteada pra Bemol (~80 sitemaps verificados, ela
        # confirmadamente não vende essa marca — mostrar o link da Bemol
        # ali caía na homepage dela por padrão, dando a entender que "pode
        # estar lá" quando sabemos que não está). Eletro Norte (loja
        # física fictícia, sempre "Sem site") é a única opção física pra
        # produto LG sem dado real da Bemol.
        candidatas_fisicas = lojas_fisicas if dados["brand"] != "LG" else [l for l in lojas_fisicas if l.name != "Bemol"]
        loja_fisica_escolhida = loja_bemol if ("Bemol" in lojas_reais and loja_bemol) else random.choice(candidatas_fisicas)
        selecionadas.append(loja_fisica_escolhida)

        for loja in selecionadas:
            dado_real = lojas_reais.get(loja.name)
            url = dado_real["url"] if dado_real else None

            # Preço e estoque são decididos CAMPO A CAMPO, não tudo-ou-nada
            # por loja: algumas lojas reais têm os dois confirmados
            # (Bemol/Brastemp/Consul/Electrolux, via JSON-LD), outras só
            # `url` sem nenhum dos dois (Samsung/LG — preço/estoque
            # carregados por JavaScript, invisíveis pra scraping estático;
            # Carrefour em alguns produtos — JSON-LD existe, mas com
            # "price": 0, dado de catálogo claramente inválido). O que não
            # tem dado real cai no mesmo simulado de qualquer loja sem
            # informação nenhuma.
            usou_dado_real = False
            if dado_real and "preco" in dado_real:
                preco = Decimal(str(dado_real["preco"]))
                usou_dado_real = True
            else:
                variacao = random.uniform(-0.08, 0.12)  # loja mais barata até mais cara que a base
                preco = _preco_com_variacao(dados["preco_base"], variacao)

            if dado_real and "em_estoque" in dado_real:
                em_estoque = dado_real["em_estoque"]
                usou_dado_real = True
            else:
                em_estoque = random.random() > 0.08  # ~92% em estoque, resto "esgotado" (realismo)

            atualizado_ha_horas = random.randint(1, 6) if usou_dado_real else random.randint(1, 30)

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
