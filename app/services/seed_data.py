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
# `lojas_reais` (quando presente): dict {nome_da_loja: {...}} com dado REAL
# achado no catálogo de verdade daquela loja (sitemap público + extração
# via JSON-LD, mesma técnica de sempre, ver app/services/atualizacao_precos.py)
# — pedido do usuário ("quero ser redirecionado pro site" + "todos com
# foto" + depois "entre no produto específico, não só no site"). Nunca é o
# MESMO produto exato do nosso catálogo mockado, sempre o mais parecido em
# capacidade/linha que a loja de verdade vende — aproximação deliberada,
# documentada, não correspondência 1:1 garantida.
#
# Cada entrada tem `url` (obrigatório) e, quando disponível, `imagem`/
# `preco`/`em_estoque`. Brastemp e Consul (mesma plataforma VTEX da Bemol)
# expõem os 4 campos via JSON-LD. Samsung e LG **não publicam preço/estoque
# em lugar nenhum estático** — a busca por produto nessas duas confirmou
# que são sites carregados por JavaScript (o preço só aparece depois de uma
# chamada de API feita pelo navegador, invisível pra qualquer requisição
# HTTP simples) — por isso essas duas entradas só têm `url` (+ `imagem` via
# tag `og:image`, quando existe) e o preço/estoque continuam sendo
# SIMULADOS pra elas (`popular_produtos_e_precos` decide isso campo a
# campo, não é tudo ou nada). Ainda assim resolve o pedido central do
# usuário — entrar na página REAL e específica daquele produto — mesmo sem
# conseguir sincronizar preço ao vivo com essas duas marcas.
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
            "Loja Oficial da Marca": {
                "url": "https://loja.electrolux.com.br/geladeira-refrigerador-frost-free-371-litros-dfn41/p",
                "preco": 3469.00, "em_estoque": True,
                "imagem": "https://electrolux.vtexassets.com/arquivos/ids/214052/Refrigerador_DFN41_Frontal_1000x1000_principal.jpg?v=638804364273430000",
            },
            # URL achada via WebSearch (Casas Bahia bloqueia toda requisição
            # automatizada, mesmo pra essa página específica — não deu pra
            # confirmar sozinho). Usuário abriu no próprio navegador e
            # confirmou: carrega de verdade, "não tem em estoque" e SEM
            # nenhum preço visível na página (por isso sem campo `preco`
            # aqui — nunca inventar um valor que a própria página não
            # mostra).
            "Casas Bahia": {
                "url": "https://www.casasbahia.com.br/geladeira-electrolux-dfn41-frost-free-com-painel-de-controle-externo-371l-branca/p/11688808",
                "em_estoque": False,
            },
            # Mesmo motivo/mesma verificação da Casas Bahia acima (Magazine
            # Luiza também bloqueia toda requisição automatizada) — usuário
            # abriu no navegador e confirmou: carrega certo, sem estoque.
            "Magazine Luiza": {
                "url": "https://www.magazineluiza.com.br/refrigerador-geladeira-electrolux-371-litros-2-portas-frost-free-dfn41/p/6498619/ed/ref2/",
                "em_estoque": False,
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
            "Loja Oficial da Marca": {
                "url": "https://loja.electrolux.com.br/geladeira-electrolux-frost-free-490l-efficient-com-autosense-inverse-inox-look--ib7s-/p",
                "preco": 4399.00, "em_estoque": True,
                "imagem": "https://electrolux.vtexassets.com/arquivos/ids/288571/Refrigerator_IB7S_Front_Electrolux_Portuguese-1000x1000.raw.jpg?v=639046841437700000",
            },
            # Achadas via WebSearch (Magazine Luiza/Casas Bahia bloqueiam toda
            # requisição automatizada, mesmo pra uma URL de produto real —
            # diferente da Bemol/Brastemp/Consul/Electrolux acima, não deu
            # pra confirmar preço/estoque via JSON-LD). Só `url`, mesmo
            # padrão de honestidade do Samsung/LG (ver comentário acima).
            "Magazine Luiza": {
                "url": "https://www.magazineluiza.com.br/refrigerador-de-02-portas-electrolux-frost-free-com-490-litros-efficient-com-autosense-inverse-inox-look-ib7s/p/jh536e5b79/ed/refr/",
            },
            "Casas Bahia": {
                "url": "https://www.casasbahia.com.br/geladeira-electrolux-ib7s-frost-free-inverse-efficient-com-autosense-inox-look-490l/p/55065689",
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
            "Loja Oficial da Marca": {
                "url": "https://www.brastemp.com.br/geladeira-brastemp-frost-free-375-litros-brm44hb/p",
                "preco": 3089.00, "em_estoque": False,
                "imagem": "https://brastemp.vtexassets.com/arquivos/ids/285442/01_Brastemp_Geladeira_BRM44HB_Imagem_Frontal_Fechada.jpg?v=639120439093400000",
            },
            # Achadas via WebSearch, mesmo motivo/mesma limitação do
            # Electrolux IF55 acima (só `url`, sem preço/estoque confirmados).
            "Magazine Luiza": {
                "url": "https://www.magazineluiza.com.br/geladeira-brastemp-frost-free-duplex-375l-inox-com-compartimento-extrafrio-fresh-zone-brm44hk/p/013085700/ed/refr/",
            },
            "Casas Bahia": {
                "url": "https://www.casasbahia.com.br/geladeira-brastemp-brm44hk-frost-free-duplex-com-compartimento-extrafrio-e-fresh-zone-inox-375l/p/12731690",
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
            "Loja Oficial da Marca": {
                "url": "https://www.brastemp.com.br/geladeira-brastemp-frost-free-inverse-588-litros-cor-inox-com-smart-bar-bre85ak/p",
                "preco": 6539.00, "em_estoque": False,
                "imagem": "https://brastemp.vtexassets.com/arquivos/ids/270753/Brastemp_Geladeira_BRE85AK_Imagem_Frontal_fechada_jpg_1.jpg?v=638996724145800000",
            },
            # Achadas via WebSearch (só `url`, mesma limitação de sempre).
            "Magazine Luiza": {
                "url": "https://www.magazineluiza.com.br/geladeira-brastemp-frost-free-inverse-588-litros-cor-inox-com-smart-bar-bre85ak/p/hjc6fd5g2a/ed/rinv/",
            },
            "Casas Bahia": {
                "url": "https://www.casasbahia.com.br/geladeira-brastemp-frost-free-inverse-588-litros-cor-inox-com-smart-bar-bre85ak/p/1546151993",
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
            "Loja Oficial da Marca": {
                "url": "https://www.consul.com.br/geladeira-consul-frost-free-342-litros-evox-crb39ak/p",
                "preco": 2609.00, "em_estoque": False,
                "imagem": "https://consul.vtexassets.com/arquivos/ids/273738/01_Consul_Geladeira_CRB39AK_Imagem_Frontal_Frontal_png_3.jpg?v=639014052388430000",
            },
            # Achadas via WebSearch (só `url`, mesma limitação de sempre).
            "Magazine Luiza": {
                "url": "https://www.magazineluiza.com.br/geladeira-consul-frost-free-342-litros-cor-inox-com-gavetao-hortifruti-crb39ak/p/837872400/ed/ref1/",
            },
            "Casas Bahia": {
                "url": "https://www.casasbahia.com.br/eletrodomesticos/geladeiraerefrigerador/1porta/refrigerador-consul-frost-free-facilite-crb39ak-1-porta-evox-342-litros-10153510.html",
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
            "Loja Oficial da Marca": {
                "url": "https://www.consul.com.br/geladeira-consul-frost-free-duplex-com-espaco-flex-e-controle-interno-de-temperatura-410-litros-cor-branca-crm50fb/p",
                "preco": 3499.00, "em_estoque": False,
                "imagem": "https://consul.vtexassets.com/arquivos/ids/273875/01_Consul_Geladeira_CRM50FB_Imagem_Frontal_3--2-.jpg?v=639014100338000000",
            },
            # Achadas via WebSearch (só `url`, mesma limitação de sempre).
            "Magazine Luiza": {
                "url": "https://www.magazineluiza.com.br/geladeira-consul-crm50fb-frost-free-duplex-410l/p/fafhck6b5e/ed/ref2/",
            },
            "Casas Bahia": {
                "url": "https://www.casasbahia.com.br/p/55065204",
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
            # Site da Samsung carrega preço/estoque via JavaScript (nenhum
            # dado estático via requests/curl) — resolvido com Playwright
            # (navegador headless de verdade, executa o JS) em vez de
            # tentar burlar proteção nenhuma: a Samsung não bloqueia
            # automação, só carrega o preço depois do carregamento inicial.
            # Preço + "Avise-me quando chegar" (= esgotado) extraídos de
            # verdade da página renderizada. Sem og:image específico aqui
            # (só o logo genérico da Samsung), então sem `imagem`.
            "Loja Oficial da Marca": {
                "url": "https://www.samsung.com/br/refrigerators/bottom-mount-freezer/rb6000d-462l-refined-inox-rb50dg6020s9az/",
                "preco": 6735.79, "em_estoque": False,
            },
            # RT46K6A4KS9 (linha "RT6000K") — bate ainda melhor com o nosso
            # model "RT46" (prefixo idêntico) que o RB50DG6020S9AZ usado no
            # site da Samsung acima. Achadas via WebSearch, só `url`.
            "Magazine Luiza": {
                "url": "https://www.magazineluiza.com.br/geladeira-samsung-inverter-rt6000k-460-litros-inox-look-bivolt-rt46k6a4ks9-fz/p/ac9cc6797h/ed/refr/",
            },
            "Casas Bahia": {
                "url": "https://m.casasbahia.com.br/geladeira-samsung-inverter-rt6000k-460-litros-inox-look-bivolt-rt46k6a4ks9-fz-1509474809.html?IdSku=1509474809",
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
            # nossa RF50. Preço + estoque extraídos via Playwright (ver
            # comentário na RT46 acima) — real, não simulado.
            "Loja Oficial da Marca": {
                "url": "https://www.samsung.com/br/refrigerators/french-door/501l-real-sts-rf22r7351sr-az/",
                "preco": 26137.00, "em_estoque": False,
                "imagem": "https://stg-images.samsung.com/is/image/samsung/br-ref-fdsr-rf22r7351sraz-rf22r7351sr-az-frontsilver-thumb-185294248",
            },
            # Achadas via WebSearch, mesmo modelo RF22R7351SR (só `url`).
            "Magazine Luiza": {
                "url": "https://www.magazineluiza.com.br/geladeira-inverter-frost-free-samsung-french-door-smartthings-wi-fi-twin-cooling-plus-com-food-showcase-e-gaveta-flexzone-rf22r7351sr-501l-inox/p/dkdjgegbh4/ed/grfd/",
            },
            "Casas Bahia": {
                "url": "https://www.casasbahia.com.br/p/55007344",
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
        # Akamai (proteção anti-bot de verdade, mesma categoria de Magazine
        # Luiza/Casas Bahia) — só não bloqueou minhas requisições `requests`/
        # curl simples usadas na busca inicial. Não insisti (mesma decisão
        # de não tentar burlar proteção nenhuma) — só URL + imagem
        # (og:image) reais, preço/estoque continuam simulados.
        "lojas_reais": {
            "Loja Oficial da Marca": {
                "url": "https://www.lg.com/br/geladeiras/geladeiras-duplex/gn-b392pqwb/",
                "imagem": "https://www.lg.com/content/dam/channel/wcms/br/images/geladeiras/gn-b392pqwb/gallery/Basic-450.jpg",
            },
            # Achada via WebSearch, modelo próximo (GN-B392PLM, mesma família
            # 392/395L) — Casas Bahia não retornou nenhum resultado pra LG
            # duplex 395L (provavelmente não carrega esse modelo específico,
            # mesmo tipo de lacuna já documentado pra Bemol/LG acima).
            "Magazine Luiza": {
                "url": "https://www.magazineluiza.com.br/geladeira-lg-frost-free-inverter-395l-duplex-cor-inox-look-gn-b392plm-220v/p/egb27f8ek4/ed/ref2/",
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
        # preço/estoque via JS que a Samsung.
        "lojas_reais": {
            "Loja Oficial da Marca": {
                "url": "https://www.lg.com/br/geladeiras/lg-GC-L247SLUV-geladeira-side-by-side-601-litros",
                "imagem": "https://www.lg.com/content/dam/channel/wcms/br/images/geladeiras/gc-l247sluv_apzfsbs_essp_br_c/450_basic.jpg",
            },
            # Mesmo modelo GC-L247SLUV, achadas via WebSearch (só `url`).
            "Magazine Luiza": {
                "url": "https://www.magazineluiza.com.br/geladeira-refrigerador-smart-lg-side-by-side-inverter-601l-com-lg-thinq-gc-l247sluv-inox/p/224801700/ed/grsb/",
            },
            "Casas Bahia": {
                "url": "https://www.casasbahia.com.br/refrigerador-smart-lg-side-by-side-601-litros-inox-220v-gc-l247sluv/p/1518119779",
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

        # TODAS as lojas online (Amazon, Magazine Luiza, Casas Bahia, Loja
        # Oficial da Marca) + 1 loja física, pra todo produto comparar o
        # máximo de ofertas possível. Antes só sorteava 2-4 das 4 online —
        # fazia sentido quando só a Bemol tinha dado real (o resto era tudo
        # simulado, nível de detalhe igual entre elas), mas agora que a
        # maioria das lojas tem alguma URL real por produto, sortear menos
        # que todas escondia dado bom atrás de sorte (pedido do usuário:
        # "quero que todos os produtos estejam com todos os links de todas
        # as marcas funcionando").
        lojas_online = [l for l in lojas if l.type == Store.TIPO_ONLINE]
        lojas_fisicas = [l for l in lojas if l.type == Store.TIPO_FISICA]

        selecionadas = list(lojas_online)

        loja_fisica_escolhida = loja_bemol if ("Bemol" in lojas_reais and loja_bemol) else random.choice(lojas_fisicas)
        selecionadas.append(loja_fisica_escolhida)

        for loja in selecionadas:
            dado_real = lojas_reais.get(loja.name)
            url = dado_real["url"] if dado_real else None

            # Preço e estoque são decididos CAMPO A CAMPO, não tudo-ou-nada
            # por loja: algumas lojas reais têm os dois confirmados
            # (Bemol/Brastemp/Consul/Electrolux, via JSON-LD), outras só
            # estoque sem preço (Casas Bahia — página confirmada pelo
            # usuário no navegador, "não tem em estoque" mas sem nenhum
            # preço visível pra copiar), outras nenhum dos dois (Samsung/LG
            # — preço/estoque carregados por JavaScript, invisíveis pra
            # scraping estático). O que não tem dado real cai no mesmo
            # simulado de qualquer loja sem informação nenhuma.
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
