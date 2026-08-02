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
        # site.fastshop.com.br (não www.fastshop.com.br, que redireciona
        # pra ela) — VTEX, robots.txt limpo (sem bloqueio geral nem de
        # bot de IA).
        "name": "Fast Shop",
        "type": Store.TIPO_ONLINE,
        "website_url": "https://site.fastshop.com.br",
        "logo_url": "/static/img/lojas/fastshop.svg",
        "trust_score": 4.4,
    },
    {
        # Kabum — testada inicialmente achando só produtos de marca
        # diferente (sitemap "eletrodomesticos.xml" limitado), mas o
        # catálogo de verdade (via WebSearch) tem cobertura boa: 4 dos
        # 10 produtos confirmados com JSON-LD real.
        "name": "Kabum",
        "type": Store.TIPO_ONLINE,
        "website_url": "https://www.kabum.com.br",
        "logo_url": "/static/img/lojas/kabum.svg",
        "trust_score": 4.5,
    },
    {
        # Angeloni — rede de supermercados/eletro de Santa Catarina, sem
        # robots.txt (ausência = sem restrição) e sem bloqueio nenhum
        # testado.
        "name": "Angeloni",
        "type": Store.TIPO_ONLINE,
        "website_url": "https://www.angeloni.com.br/eletro",
        "logo_url": "/static/img/lojas/angeloni.svg",
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
# marca, nunca a de outra), "Carrefour", "Americanas", "Fast Shop", "Kabum",
# "Angeloni" e "Amazon". Magazine Luiza e Casas Bahia foram removidas do
# catálogo inteiro (bloqueiam toda requisição automatizada, mesmo com
# Playwright sem disfarce nenhum — ver atualizacao_precos.py e README).
#
# Cada entrada tem `url` (obrigatório) e, quando disponível, `imagem`/
# `preco`/`em_estoque`. Bemol/Brastemp/Consul/Electrolux (mesma plataforma
# VTEX) e Carrefour/Americanas/Fast Shop/Kabum/Angeloni (idem, quando o
# catálogo da loja não está com preço zerado — ver comentários pontuais
# abaixo) expõem os campos via JSON-LD estático. Samsung e LG **não
# publicam preço/estoque em lugar nenhum estático** — a busca por produto
# nessas duas confirmou que são sites carregados por JavaScript (o preço só
# aparece depois de uma chamada de API feita pelo navegador, invisível pra
# qualquer requisição HTTP simples) — resolvido com Playwright pra Samsung
# (não bloqueia automação), mas não pra LG (bloqueia com 403 via Akamai,
# mesma categoria de proteção anti-bot que já bloqueava Magazine Luiza/
# Casas Bahia). AMAZON também não publica JSON-LD nenhum (nem preço nem
# estoque em atributo estático) — mas ao contrário de Samsung/LG, Amazon
# não bloqueia Playwright, então cada uma das 10 páginas de produto real
# foi verificada AO VIVO (não só o status HTTP, que sempre retorna 200
# mesmo com o item indisponível): a maioria mostrou "Não disponível. Não
# temos previsão de quando este produto estará disponível novamente." —
# nesses casos `em_estoque: False` é gravado EXPLICITAMENTE (não fica de
# fora nem cai no sorteio aleatório, que erraria mostrando "em estoque" a
# maior parte das vezes) — só 2 produtos (Electrolux IF55, LG GC-B) têm
# preço real confirmado em estoque na Amazon no momento desta verificação.
# O que não tem preço/estoque real continua SIMULADO
# (`popular_produtos_e_precos` decide isso campo a campo, não é tudo ou
# nada). Ainda assim resolve o pedido central do usuário — entrar na
# página REAL e específica daquele produto — mesmo sem conseguir
# sincronizar preço ao vivo com essas marcas/lojas.
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
            # PROMOÇÃO REAL confirmada: o estado embutido da página (VTEX
            # Apollo/GraphQL cache, chave `priceRange.listPrice` vs.
            # `priceRange.sellingPrice` — não é um "% OFF" genérico de
            # banner de pagamento, é o preço "de/por" específico deste
            # produto) mostra `listPrice=3789` vs. `sellingPrice=3469`
            # (nosso `preco` já registrado) — ~8% de desconto ativo agora.
            "Electrolux": {
                "url": "https://loja.electrolux.com.br/geladeira-refrigerador-frost-free-371-litros-dfn41/p",
                "preco": 3469.00, "em_estoque": True,
                "preco_original": 3789.00, "promo_dias": 6,
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
            # Carrefour). CONFIRMADO ao vivo (Playwright, usuário reportou
            # com print de tela): a página renderizada mostra "Este produto
            # não possui disponibilidade para entrega na sua região ou na
            # loja escolhida" — não é preço zerado por bug de catálogo, é
            # falta de estoque de verdade. `em_estoque: False` explícito
            # (não deixar cair no sorteio aleatório, que erraria mostrando
            # "em estoque" a maioria das vezes).
            "Carrefour": {
                "url": "https://www.carrefour.com.br/produto/geladeirarefrigerador-frost-free-electrolux-dfn-litros-branco-244624",
                "em_estoque": False,
            },
            # Mesmo modelo DFN41 na Americanas — JSON-LD real (marketplace,
            # vários vendedores por produto; usei o preço do 1º vendedor
            # listado).
            "Americanas": {
                "url": "https://www.americanas.com.br/geladeira-electrolux-371-litros-frost-free-branco-dfn41-127v--h17i38691a352141/p",
                "preco": 3399.99, "em_estoque": False,
            },
            # Mesmo modelo DFN41 na Kabum — JSON-LD real.
            "Kabum": {
                "url": "https://www.kabum.com.br/produto/122048/geladeira-refrigerador-electrolux-dfn41-371l-frost-free-duplex-127v-branco",
                "preco": 3015.52, "em_estoque": False,
                "imagem": "https://images8.kabum.com.br/produtos/fotos/sync_mirakl/122048/Geladeira-Refrigerador-Electrolux-DFN41-371L-Frost-Free-Duplex-127V-Branco_1709151493_g.jpg",
            },
            # Mesmo modelo DFN41 na Amazon — página real confirmada (título
            # bate exato: "Geladeira Electrolux Frost Free 371L Função Drink
            # Express Duplex Branca (DFN41)"), mas SEM JSON-LD (Amazon não
            # publica) — verificado AO VIVO com Playwright (não só o status
            # HTTP): "Não disponível. Não temos previsão de quando este
            # produto estará disponível novamente." `em_estoque: False`
            # explícito de propósito, pra não cair no sorteio aleatório
            # (que erraria mostrando "em estoque" ~92% das vezes).
            "Amazon": {
                "url": "https://www.amazon.com.br/Refrigerador-Frost-Electrolux-litros-DFN41/dp/B07BBVX8XR",
                "em_estoque": False,
                "imagem": "https://m.media-amazon.com/images/I/31ndOiwQRQL._AC_SX679_.jpg",
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
            # PROMOÇÃO REAL confirmada (mesma técnica da DF44 acima):
            # `listPrice=5649` vs. `sellingPrice=4399` — ~22% de desconto
            # ativo agora, o maior dos 3 achados nesta rodada.
            "Electrolux": {
                "url": "https://loja.electrolux.com.br/geladeira-electrolux-frost-free-490l-efficient-com-autosense-inverse-inox-look--ib7s-/p",
                "preco": 4399.00, "em_estoque": True,
                "preco_original": 5649.00, "promo_dias": 4,
                "imagem": "https://electrolux.vtexassets.com/arquivos/ids/288571/Refrigerator_IB7S_Front_Electrolux_Portuguese-1000x1000.raw.jpg?v=639046841437700000",
            },
            # Mesmo modelo IB7S no Carrefour (também VTEX) — JSON-LD achado,
            # mas com "price": 0. CONFIRMADO ao vivo (Playwright): página
            # mostra "não possui disponibilidade para entrega na sua
            # região" — sem estoque de verdade, não é bug de catálogo.
            "Carrefour": {
                "url": "https://www.carrefour.com.br/geladeira-electrolux-frost-free-inverter-490l-inverse-inox-look-ib7s-mp955042852/p",
                "em_estoque": False,
            },
            # Mesmo modelo IB7S na Americanas — JSON-LD confirma
            # `price: "0"`, `availability: OutOfStock`, `seller: "1"` (o
            # mesmo vendedor-placeholder usado quando não há nenhuma oferta
            # de marketplace válida — não é bug de catálogo, é falta de
            # estoque real). `em_estoque: False` explícito.
            "Americanas": {
                "url": "https://www.americanas.com.br/geladeira-electrolux-frost-free-inverter-490l-inverse-inox-look-ib7s-7489466541/p",
                "em_estoque": False,
            },
            # Mesmo modelo IB7S na Amazon — sem JSON-LD, mas confirmado AO
            # VIVO com Playwright (título bate exato): em estoque, com
            # preço real visível na página. Uma das 2 únicas entradas de
            # Amazon com preço/estoque de verdade (junto do LG GC-B abaixo)
            # — a maioria dos outros produtos está indisponível na Amazon
            # no momento desta verificação.
            "Amazon": {
                "url": "https://www.amazon.com.br/Geladeira-Electrolux-Efficient-AutoSense-Inverse/dp/B0CL7XV8NN",
                "preco": 4221.55, "em_estoque": True,
                "imagem": "https://m.media-amazon.com/images/I/413y5xpxNxL._AC_SX679_.jpg",
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
            # PROMOÇÃO REAL confirmada (mesma técnica das Electrolux acima):
            # `listPrice=3329` vs. `sellingPrice=3089` — ~7% de desconto
            # ativo agora. `em_estoque` reconferido numa auditoria posterior
            # (usuário pediu pra checar de novo) — o JSON-LD atual mostra
            # `InStock` (voltou a vender, não é mais o `False` de quando
            # verifiquei da primeira vez).
            "Brastemp": {
                "url": "https://www.brastemp.com.br/geladeira-brastemp-frost-free-375-litros-brm44hb/p",
                "preco": 3089.00, "em_estoque": True,
                "preco_original": 3329.00, "promo_dias": 8,
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
            # Mesmo modelo BRM44HB na Fast Shop — JSON-LD real, em estoque.
            # PROMOÇÃO REAL confirmada (usuário reportou "tem umas promoção
            # no fast shop que você não colocou" — auditoria confirmou):
            # o próprio JSON-LD de Offer traz `listPriceWithTaxes=3399` ao
            # lado de `price=3001.05` — ~12% de desconto ativo agora.
            "Fast Shop": {
                "url": "https://site.fastshop.com.br/geladeira-brastemp-frost-free-duplex-375-litros-cor-branca---brm44hb-47612/p",
                "preco": 3001.05, "em_estoque": True,
                "preco_original": 3399.00, "promo_dias": 7,
                "imagem": "https://fastshopbr.vtexassets.com/arquivos/ids/3224680/17644568029130.jpg?v=639018782689000000",
            },
            # Mesmo modelo BRM44HB na Amazon — página real confirmada,
            # indisponível (Playwright, sem previsão de retorno).
            "Amazon": {
                "url": "https://www.amazon.com.br/Geladeira-Brastemp-Duplex-litros-Branca/dp/B084KLPY1J",
                "em_estoque": False,
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
            # "price": 0. CONFIRMADO ao vivo (Playwright): sem
            # disponibilidade de entrega/retirada de verdade.
            "Carrefour": {
                "url": "https://www.carrefour.com.br/geladeira-brastemp-frost-free-inverse-588-litros-cor-inox-com-smart-bar-bre85ak-220v-mp929716281/p",
                "em_estoque": False,
            },
            # Mesmo modelo BRE85AK na Americanas — mesmo padrão de "sem
            # oferta válida" (JSON-LD: `price: "0"`, `OutOfStock`, seller
            # placeholder "1"). `em_estoque: False` explícito.
            "Americanas": {
                "url": "https://www.americanas.com.br/geladeira-frost-free-inverse-2-portas-588-litros-bre85ak-brastemp-7462033239/p",
                "em_estoque": False,
            },
            # BRO85ME (French Door, 559L) — outra Brastemp Inverse/French
            # Door na mesma classe de capacidade, achada real na Kabum
            # (JSON-LD, em estoque). Modelo de linha diferente (BRO vs
            # BRE), mesma aproximação já usada nas outras lojas pra essa
            # capacidade.
            "Kabum": {
                "url": "https://www.kabum.com.br/produto/993303/refrigerador-french-door-brastemp-de-03-portas-frost-free-com-559-litros-eclipse-collection-bro85me-220v",
                "preco": 6162.61, "em_estoque": True,
                "imagem": "https://images3.kabum.com.br/produtos/fotos/sync_mirakl/993303/large/Refrigerador-French-Door-Brastemp-De-03-Portas-Frost-Free-Com-559-Litros-Black-Inox-Bro85me-220v_1770929040.jpg",
            },
            # Mesmo modelo BRE85AK na Amazon — página real confirmada,
            # indisponível (Playwright, sem previsão de retorno).
            "Amazon": {
                "url": "https://www.amazon.com.br/Geladeira-Brastemp-Inverse-litros-BRE85AK/dp/B0BVSRSRCW",
                "em_estoque": False,
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
            # PROMOÇÃO REAL confirmada (mesma técnica das Electrolux/Brastemp
            # acima): `listPrice=3049` vs. `sellingPrice=2609` — ~14% de
            # desconto ativo agora.
            "Consul": {
                "url": "https://www.consul.com.br/geladeira-consul-frost-free-342-litros-evox-crb39ak/p",
                "preco": 2609.00, "em_estoque": False,
                "preco_original": 3049.00, "promo_dias": 5,
                "imagem": "https://consul.vtexassets.com/arquivos/ids/273738/01_Consul_Geladeira_CRB39AK_Imagem_Frontal_Frontal_png_3.jpg?v=639014052388430000",
            },
            # Mesmo modelo CRB39AB no Carrefour — JSON-LD real, em estoque.
            # DESCONTO REAL À VISTA NO PIX confirmado (visível renderizando
            # a página real com Playwright, não no JSON-LD — o Carrefour
            # não publica isso em dado estruturado): R$3.187,00 no
            # cartão/preço de tabela, R$2.868,30 à vista no PIX (-10%,
            # exatamente 10% de desconto). Usuário pediu explicitamente pra
            # mostrar como promoção, com selo "no PIX" (`promo_pix`) pra
            # deixar claro que não é desconto pra qualquer forma de
            # pagamento — o preço "atual"/em destaque vira o do PIX,
            # `preco_original` continua sendo o de tabela/cartão.
            "Carrefour": {
                "url": "https://www.carrefour.com.br/geladeira-consul-frost-free-342-litros-branca-com-gavetao-hortifruti-crb39ab-110v-8950121/p",
                "preco": 2868.30, "em_estoque": True,
                "preco_original": 3187.00, "promo_dias": 10, "promo_pix": True,
                "imagem": "https://carrefourbr.vtexassets.com/arquivos/ids/181487971/image-0.jpg?v=638935408554630000",
            },
            # Mesmo modelo CRB39AB na Americanas — JSON-LD real (marketplace,
            # preço do vendedor mais barato listado).
            "Americanas": {
                "url": "https://www.americanas.com.br/geladeira-consul-342-litros-frost-free-branco-crb39ab-127v-173g9z552j157793/p",
                "preco": 2499.00, "em_estoque": True,
            },
            # Mesmo modelo CRB39AB na Fast Shop — JSON-LD real, em estoque.
            # PROMOÇÃO REAL confirmada: `listPriceWithTaxes=3908` vs.
            # `price=2902.50` — ~26% de desconto, a maior das achadas nesta
            # rodada.
            "Fast Shop": {
                "url": "https://site.fastshop.com.br/refrigerador-consul-frost-free-342-litros-crb39ab---127-volts-95798/p",
                "preco": 2902.50, "em_estoque": True,
                "preco_original": 3908.00, "promo_dias": 6,
            },
            # Mesmo modelo CRB39AB na Kabum — JSON-LD real.
            "Kabum": {
                "url": "https://www.kabum.com.br/produto/122096/geladeira-frost-free-1-porta-342-litros-consul-crb39ab",
                "preco": 4897.04, "em_estoque": False,
                "imagem": "https://images6.kabum.com.br/produtos/fotos/sync_mirakl/122096/Geladeira-Consul-Domest-342l-Frost-Free-1-Porta-220V-Branco-CRB39AB_1711981697_g.jpg",
            },
            # Modelo próximo CRB39A na Angeloni — JSON-LD real.
            "Angeloni": {
                "url": "https://www.angeloni.com.br/eletro/geladeira-frost-free-consul-facilite-1-porta-342l-branca-crb39a-2480183/p",
                "preco": 2499.00, "em_estoque": False,
                "imagem": "https://eletroangeloni.vtexassets.com/arquivos/ids/175612/2480183_1_zoom.jpg?v=637931633608330000",
            },
            # Mesmo modelo CRB39AB na Amazon — página real confirmada
            # (título bate exato), mas sem oferta em destaque no momento
            # ("Nenhuma opção de compra em destaque" / só "ver todas as
            # opções de compra", sem preço nem vendedor claro na página) —
            # só `url`, sem inventar preço nem status de estoque quando a
            # própria página não afirma nenhum dos dois com clareza.
            "Amazon": {
                "url": "https://www.amazon.com.br/Geladeira-Consul-litros-Gavet%C3%A3o-Hortifruti/dp/B076BDN8TJ",
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
            # "price": 0. CONFIRMADO ao vivo (Playwright, o próprio usuário
            # mandou print desta exata página): "Este produto não possui
            # disponibilidade para entrega na sua região ou na loja
            # escolhida para retirada" — não é bug de catálogo, é falta de
            # estoque real. `em_estoque: False` explícito.
            "Carrefour": {
                "url": "https://www.carrefour.com.br/geladeira-consul-crm50fb-frost-free-duplex-410l-mp934406719/p",
                "em_estoque": False,
            },
            # Mesmo modelo CRM50FB na Americanas — mesmo padrão de "sem
            # oferta válida" (JSON-LD: `price: "0"`, `OutOfStock`, seller
            # placeholder "1"). `em_estoque: False` explícito.
            "Americanas": {
                "url": "https://www.americanas.com.br/geladeira-consul-frost-free-duplex-com-espaco-flex-410l-branca-crm50fb-7512217016/p",
                "em_estoque": False,
            },
            # Mesmo modelo CRM50FB na Amazon — página real confirmada
            # (título bate exato, inclusive o código do modelo), indisponível
            # (Playwright, sem previsão de retorno).
            "Amazon": {
                "url": "https://www.amazon.com.br/Refrigerador-Consul-Litros-CRM50FB-Branca/dp/B0CDXQWPZ7",
                "em_estoque": False,
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
            # Achada no Carrefour — JSON-LD achado, mas com "price": 0.
            # CONFIRMADO ao vivo (Playwright): sem disponibilidade de
            # entrega/retirada de verdade.
            "Carrefour": {
                "url": "https://www.carrefour.com.br/geladeira-samsung-evolution-rt46-com-powervolt-inverter-duplex-460l-inox-look-bivolt-mp929908731/p",
                "em_estoque": False,
            },
            # Mesmo modelo RT46 na Kabum — JSON-LD real.
            "Kabum": {
                "url": "https://www.kabum.com.br/produto/148048/geladeira-samsung-evolution-com-powervolt-inverter-duplex-460l-black-inox-look-rt46",
                "preco": 4084.05, "em_estoque": False,
                "imagem": "https://images8.kabum.com.br/produtos/fotos/sync_mirakl/148048/Geladeira-Samsung-Evolution-Com-PowerVolt-Inverter-Duplex-460L-Black-Inox-Look-RT46_1698245300_g.jpg",
            },
            # Mesmo modelo RT46 na Amazon — página real confirmada (título
            # bate exato), indisponível (Playwright, sem previsão de
            # retorno).
            "Amazon": {
                "url": "https://www.amazon.com.br/Geladeira-Samsung-Evolution-POWERvolt-Inverter/dp/B09QW39MY7",
                "em_estoque": False,
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
            # com "price": 0. CONFIRMADO ao vivo (Playwright): sem
            # disponibilidade de entrega/retirada de verdade.
            "Carrefour": {
                "url": "https://www.carrefour.com.br/produto/refrigeradorgeladeira-samsung-frost-free-0l-rfrsr-320224374",
                "em_estoque": False,
            },
            # Mesmo modelo RF22R7351SR na Amazon — página real confirmada
            # (título bate exato, inclusive o sufixo /AZ), indisponível
            # (Playwright, sem previsão de retorno).
            "Amazon": {
                "url": "https://www.amazon.com.br/Refrigerador-French-Samsung-Portas-Cooling/dp/B08NFK4F5R",
                "em_estoque": False,
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
            # Carrefour — JSON-LD real, em estoque. DESCONTO REAL À VISTA
            # NO PIX confirmado (mesma técnica da CRB39 acima — visível
            # renderizando a página, não no JSON-LD): R$3.156,84 no cartão,
            # R$2.999,00 no PIX (-5%). `promo_pix=True`.
            "Carrefour": {
                "url": "https://www.carrefour.com.br/geladeira-lg-2-portas-frost-free-inverter-395l-duplex-inox-look-110v-gnb392plmb-3376389/p",
                "preco": 2999.00, "em_estoque": True,
                "preco_original": 3156.84, "promo_dias": 10, "promo_pix": True,
            },
            # Modelo próximo (GN-B392PLM) na Americanas — mesmo padrão de
            # "sem oferta válida" (JSON-LD: `price: "0"`, `OutOfStock`,
            # seller placeholder "1"). `em_estoque: False` explícito.
            "Americanas": {
                "url": "https://www.americanas.com.br/geladeira-lg-frost-free-inverter-395l-duplex-inox-look-gn-b392plm-220v-17592d4yo3629823/p",
                "em_estoque": False,
            },
            # Modelo próximo (mesma família GN-B392) na Fast Shop —
            # JSON-LD real, em estoque. PROMOÇÃO REAL confirmada:
            # `listPriceWithTaxes=3699` vs. `price=3477.06` — ~6% de
            # desconto ativo agora.
            "Fast Shop": {
                "url": "https://site.fastshop.com.br/geladeira-lg-frost-free-inverter-395l-duplex-branca-110v-129095/p",
                "preco": 3477.06, "em_estoque": True,
                "preco_original": 3699.00, "promo_dias": 9,
                "imagem": "https://fastshopbr.vtexassets.com/arquivos/ids/2484520/17582049198853.jpg?v=638973653955830000",
            },
            # Família GN-B392 (GN-B392PLMB, mesma capacidade 395L) na
            # Amazon — sem JSON-LD, mas confirmado AO VIVO com Playwright:
            # em estoque, com preço real visível na página. Uma das 2
            # únicas entradas de Amazon com preço/estoque de verdade (junto
            # da Electrolux IF55 acima).
            "Amazon": {
                "url": "https://www.amazon.com.br/Geladeira-LG-Freezer-Inverter-GN-B392PLMB/dp/B0CJMWC77S",
                "preco": 3161.07, "em_estoque": True,
                "imagem": "https://m.media-amazon.com/images/I/41fuFa+6--L._AC_SX679_.jpg",
            },
        },
    },
    {
        "brand": "LG", "model": "GC-X267", "nome_curto": "Side by Side InstaView 628L",
        "preco_base": 19999.00,
        "specs": {"capacidade_litros": 628, "frost_free": True, "cor": "Inox",
                   "voltagem": "Bivolt", "dimensoes_cm": "179 x 91.3 x 73.5", "consumo_kwh_mes": 54.0},
        # SUBSTITUIU o antigo "GC-L" (GC-L247SLUV/GS65SDN1, 601L) —
        # usuário confirmou que aquele modelo foi DESCONTINUADO de vez
        # ("está completamente indisponível" em todos os sites, inclusive
        # no da LG) e pediu geladeiras ATUAIS, populares-a-exclusivas, à
        # venda em todos os sites. GC-X267GL5P (628L, linha InstaView —
        # painel de vidro que acende com 2 toques, sem precisar abrir a
        # porta) é o Side by Side atual da LG, confirmado em
        # lg.com.br/br + Carrefour + Fast Shop + Angeloni, todos com
        # preço real e InStock confirmado (Carrefour reconferido AO VIVO
        # com Playwright, não só JSON-LD estático — sem repetir o mesmo
        # erro do GC-L antigo). Amazon não tem esse SKU exato; usei o
        # GC-X257CSH1 (598L, mesma linha InstaView/Craft Ice) como
        # aproximação — página real confirmada, mas indisponível lá
        # (mesmo padrão da maioria dos produtos Amazon nesta sessão).
        # Kabum e Americanas não têm nenhum dos dois SKUs indexado.
        "lojas_reais": {
            "LG": {
                "url": "https://www.lg.com/br/geladeiras/geladeiras-side-by-side/gc-x267gl5p/",
                "imagem": "https://www.lg.com/content/dam/channel/wcms/br/images/geladeiras/gc-x267gl5p/gallery/450.jpg",
            },
            # GC-X267GL5P no Carrefour — JSON-LD real (R$18.230,00,
            # InStock) E reconferido ao vivo com Playwright: sem aviso de
            # indisponibilidade, mostra inclusive um desconto real à
            # vista no PIX (R$16.407,00, exatamente -10% — mesmo padrão
            # já visto na Consul CRB39/LG GC-B).
            "Carrefour": {
                "url": "https://www.carrefour.com.br/geladeira-smart-lg-side-by-side-inverter-frost-free-628-litros-inox-gc-x267gl5p-mp957895903/p",
                "preco": 16407.00, "em_estoque": True,
                "preco_original": 18230.00, "promo_dias": 8, "promo_pix": True,
                "imagem": "https://carrefourbr.vtexassets.com/arquivos/ids/215032081/image-0.jpg?v=639155922294530000",
            },
            # GC-X267GL5P na Fast Shop — JSON-LD real, em estoque.
            # PROMOÇÃO REAL confirmada (mesmo padrão de sempre,
            # `listPriceWithTaxes`): de R$23.789,00 por R$21.410,10, ~10%.
            "Fast Shop": {
                "url": "https://site.fastshop.com.br/geladeira-lg-side-by-side-frost-free-inverter-628l-gc-x267gl5p-inox-bivolt-170375/p",
                "preco": 21410.10, "em_estoque": True,
                "preco_original": 23789.00, "promo_dias": 6,
                "imagem": "https://fastshopbr.vtexassets.com/arquivos/ids/4958385/17803228281732.jpg?v=639160284511300000",
            },
            # GC-X267GL5P na Angeloni — JSON-LD real (AggregateOffer,
            # marketplace "Webcontinental"), em estoque.
            "Angeloni": {
                "url": "https://www.angeloni.com.br/eletro/geladeira-lg-side-by-side-frost-free-inverter-628l-gc-x267gl5p-inox-bivolt-689647/p",
                "preco": 23789.00, "em_estoque": True,
                "imagem": "https://eletroangeloni.vtexassets.com/arquivos/ids/4657707/17817313429693.jpg?v=639197403570400000",
            },
            # GC-X257CSH1 (598L, mesma linha InstaView/Craft Ice) na
            # Amazon — página real confirmada, indisponível (Playwright,
            # sem previsão de retorno — mesmo padrão da maioria dos
            # produtos Amazon nesta sessão).
            "Amazon": {
                "url": "https://www.amazon.com.br/Geladeira-LG-InstaView-UVnano-litros/dp/B0B5B29TG4",
                "em_estoque": False,
                "imagem": "https://m.media-amazon.com/images/I/41vKKsTW5FL._AC_SX679_.jpg",
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

        # Lojas online "universais" (Amazon, Carrefour, Americanas, Fast
        # Shop, Kabum, Angeloni) — comparar o máximo de ofertas possível é
        # o pedido do usuário ("quero que todos os produtos estejam com
        # todos os links de todas as marcas funcionando" + depois "eu
        # queria ter mais opções de lugares para comprar" + "eu pedi
        # OPÇÕES, não uma opção a mais" + "na amazon ele só vai pra página
        # geral, não pra página específica do produto"), MAS nenhuma delas
        # tem dado real pra TODOS os produtos (WebSearch não acha tudo, e
        # vários links indexados já saíram do ar) — incluir uma delas em
        # produto SEM entrada real repetiria o mesmo bug corrigido 2x nesta
        # sessão (Carrefour no Electrolux DF44, Bemol no LG): sem
        # `Price.url`, a oferta cairia no fallback de HOMEPAGE (ou, no caso
        # da Amazon antes desta rodada, na busca genérica `/s?k=`), que
        # parece um link quebrado/sem sentido pro usuário. Por isso Amazon
        # é a ÚNICA exceção que ainda entra sempre (`nome == "Amazon"`
        # abaixo) — mesmo pros produtos sem `lojas_reais["Amazon"]` (não há
        # nenhum caso hoje, os 10 produtos já têm entrada real de Amazon,
        # mas a exceção continua como rede de segurança pra um produto
        # futuro sem cobertura) — porque a busca `/s?k=` da Amazon sempre
        # funciona como fallback aceitável, diferente de uma homepage
        # genérica de qualquer outra loja. Carrefour/Americanas/Fast Shop/
        # Kabum/Angeloni só entram no produto onde JÁ existe uma URL real
        # confirmada em `lojas_reais` — garante estruturalmente que NENHUMA
        # oferta delas caia em homepage, mesmo pra loja nova/produto futuro
        # que eu esqueça de pesquisar por completo.
        lojas_online = [l for l in lojas if l.type == Store.TIPO_ONLINE]
        lojas_fisicas = [l for l in lojas if l.type == Store.TIPO_FISICA]

        selecionadas = []
        for nome in ("Amazon", "Carrefour", "Americanas", "Fast Shop", "Kabum", "Angeloni"):
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

            # Promoção temporária REAL (ver comentários pontuais em
            # `lojas_reais` — achadas de duas formas: comparando o estado
            # embutido `priceRange.listPrice` vs. `priceRange.sellingPrice`/
            # `listPrice`/`listPriceWithTaxes` do JSON-LD de cada página
            # VTEX — nunca um "% OFF" genérico de banner de pagamento — ou,
            # no caso do Carrefour, um desconto de verdade só que
            # condicional à forma de pagamento, "à vista no PIX"; marcado
            # via `promo_pix` pra mudar só o TEXTO do selo, não a lógica).
            # `promo_dias` é relativo ao momento do seed (não uma data fixa
            # gravada no dicionário) — do mesmo jeito que `atualizado_ha_horas`
            # já é relativo a "agora" logo abaixo.
            preco_original = None
            promo_valid_until = None
            promo_pix = False
            if dado_real and "preco_original" in dado_real:
                preco_original = Decimal(str(dado_real["preco_original"]))
                promo_valid_until = datetime.utcnow() + timedelta(days=dado_real.get("promo_dias", 5))
                promo_pix = dado_real.get("promo_pix", False)

            atualizado_ha_horas = random.randint(1, 6) if usou_dado_real else random.randint(1, 30)

            db.session.add(Price(
                product=produto,
                store=loja,
                price=preco,
                original_price=preco_original,
                promo_pix=promo_pix,
                promo_valid_until=promo_valid_until,
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
