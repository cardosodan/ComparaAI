"""Dados mockados do ComparAI (Fase 1: só geladeiras) — usado por `seed.py`.

Todo `Price` gravado vem de `lojas_reais` (dado REAL, achado via JSON-LD/
Playwright, ver comentários pontuais em cada produto) — pedido explícito
do usuário: "eu só quero LOJAS REAIS SEM INVENTAR NADA E COM PREÇOS
REAIS". Uma loja só aparece pra um produto quando JÁ existe um preço real
confirmado pra aquele par produto+loja (`popular_produtos_e_precos`
decide isso). Não existe mais nenhum preço/estoque simulado por
aleatoriedade — só o HISTÓRICO de 30 dias (`gerar_historico_de_precos`)
continua sendo uma tendência sintética (documentado ali, com seed fixa
pra reprodutibilidade), já que não temos preço histórico real capturado
dia a dia.
"""
import random
from datetime import datetime, timedelta
from decimal import Decimal

from app import db
from app.models import Category, PriceHistory, Price, Product, Store, slugify

random.seed(42)

# Usuário pediu pra listar mais categorias (mesmo sem produto nenhum
# ainda) + um "ver mais" na home pra não poluir a tela com todas de
# cara — ver home.html. Só "Geladeiras" é `active` (única com produtos
# de verdade, Fase 1); o resto existe como "em breve" pra já dar uma
# ideia do catálogo completo planejado.
CATEGORIAS = [
    {"name": "Geladeiras", "slug": "geladeiras", "icon": "refrigerator", "active": True},
    {"name": "Fogões", "slug": "fogoes", "icon": "flame", "active": False},
    {"name": "Lava-louças", "slug": "lava-loucas", "icon": "utensils", "active": False},
    {"name": "Micro-ondas", "slug": "micro-ondas", "icon": "microwave", "active": True},
    {"name": "Máquina de Lavar", "slug": "maquina-de-lavar", "icon": "washing-machine", "active": False},
    {"name": "Ar-condicionado", "slug": "ar-condicionado", "icon": "wind", "active": False},
    {"name": "Aspirador de Pó", "slug": "aspirador-de-po", "icon": "fan", "active": False},
    {"name": "Cafeteira", "slug": "cafeteira", "icon": "coffee", "active": False},
    {"name": "Adega Climatizada", "slug": "adega-climatizada", "icon": "wine", "active": False},
    {"name": "TV e Som", "slug": "tv-e-som", "icon": "tv", "active": False},
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
        # Havan — rede nacional de departamentos (não é um comércio local
        # de Manaus, por isso "online" e não "física", mesmo critério já
        # usado pro Carrefour/Angeloni). Magento (não VTEX) — robots.txt
        # permite, preço/estoque/promoção vêm de microdata schema.org
        # embutida no HTML (`itemprop="price"/"availability"`, dentro do
        # bloco `product-info-main` — cuidado: a página também tem blocos
        # de preço de produtos RELACIONADOS num carrossel `swiper-slide`,
        # com a mesma estrutura de classe; só o bloco dentro de
        # `product-info-main` é o produto de verdade).
        "name": "Havan",
        "type": Store.TIPO_ONLINE,
        "website_url": "https://www.havan.com.br",
        "logo_url": "/static/img/lojas/havan.svg",
        "trust_score": 4.1,
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
        # Panasonic — marca própria, entrando com a categoria Micro-ondas
        # (Samsung não tem presença real de verdade nesse mercado no
        # Brasil, confirmado por WebSearch — Panasonic é historicamente
        # uma das marcas mais fortes de micro-ondas aqui, então entrou no
        # lugar dela pra essa categoria). "Loja de Parceiros Panasonic"
        # (parceiros.panasonic.com.br) é a loja oficial/autorizada da
        # marca no Brasil — mesma plataforma VTEX das outras marcas,
        # JSON-LD real.
        "name": "Panasonic",
        "type": Store.TIPO_ONLINE,
        "website_url": "https://parceiros.panasonic.com.br",
        "logo_url": "/static/img/lojas/panasonic.svg",
        "trust_score": 4.4,
    },
    {
        "name": "Bemol",
        "type": Store.TIPO_FISICA,
        "city": "Manaus",
        "website_url": "https://www.bemol.com.br",
        "logo_url": "/static/img/lojas/bemol.svg",
        "trust_score": 4.5,
    },
    # "Eletro Norte" foi REMOVIDA de vez (era uma loja física FICTÍCIA —
    # nunca existiu de verdade, sem site, sem CNPJ, preço/estoque sempre
    # simulado). Usuário pediu explicitamente "SÓ LOJAS REAIS, SEM
    # INVENTAR NADA, COM PREÇOS REAIS" e depois pediu pra pesquisar mais
    # lojas de Manaus — TVLar e APA Móveis entraram no lugar: são REDES
    # FÍSICAS DE VERDADE de Manaus (não inventadas), com preço/estoque
    # real via JSON-LD, finalmente dando pluralidade de loja física de
    # novo (antes só a Bemol).
    {
        # TVLar — 77 lojas (25 em Manaus + 43 interior do Amazonas + 9 em
        # Roraima), fundada em 1964. VTEX, robots.txt permite, JSON-LD real.
        "name": "TVLar",
        "type": Store.TIPO_FISICA,
        "city": "Manaus",
        "website_url": "https://www.tvlar.com.br",
        "logo_url": "/static/img/lojas/tvlar.svg",
        "trust_score": 4.3,
    },
    {
        # APA Móveis — rede de móveis/eletrodomésticos de Manaus (desde
        # 2005). robots.txt tem `Disallow: /produtos` só pra listagem SEM
        # barra, com `Allow: /produtos/` liberando páginas de produto
        # individual — igual ao padrão já visto em várias lojas VTEX.
        # JSON-LD real (formato solto: um `Offer` direto no `Product`, sem
        # aninhamento em AggregateOffer).
        "name": "APA Móveis",
        "type": Store.TIPO_FISICA,
        "city": "Manaus",
        "website_url": "https://www.apamoveis.com.br",
        "logo_url": "/static/img/lojas/apa-moveis.svg",
        "trust_score": 4.0,
    },
    # Ramsons e Bigazine (também de Manaus) foram PESQUISADAS mas
    # descartadas por enquanto — as duas têm catálogo real de geladeiras,
    # mas toda URL de produto testada (várias tentativas, WebSearch
    # focado) redirecionava pra uma página de busca genérica ou dava 404
    # — mesmo padrão de "link indexado que já saiu do ar" já visto com
    # outras lojas nesta sessão. Sem URL de produto confirmada, não
    # entram (nunca inventar uma URL só pra preencher).
]

# Specs de cada geladeira. Marcas do brief: Electrolux, Brastemp, Consul,
# Samsung, LG — variando capacidade/frost-free/cor pra dar variedade real
# de filtro (não só o mesmo produto 10 vezes).
#
# `lojas_reais` (quando presente): dict {nome_da_loja: {...}} com dado REAL
# achado no catálogo de verdade daquela loja (sitemap público + extração
# via JSON-LD, mesma técnica de sempre, ver app/services/atualizacao_precos.py)
# — pedido do usuário ("quero ser redirecionado pro site" + "todos com
# foto" + depois "entre no produto específico, não só no site" + depois
# "eu só quero LOJAS REAIS SEM INVENTAR NADA E COM PREÇOS REAIS"). Nunca é
# o MESMO produto exato do nosso catálogo mockado, sempre o mais parecido
# em capacidade/linha que a loja de verdade vende — aproximação
# deliberada, documentada, não correspondência 1:1 garantida.
#
# As chaves possíveis são: "Bemol", o NOME DA PRÓPRIA MARCA (Electrolux/
# Brastemp/Consul/Samsung/LG — cada produto só usa a chave da sua própria
# marca, nunca a de outra), "Carrefour", "Americanas", "Fast Shop", "Kabum",
# "Angeloni" e "Amazon". Magazine Luiza e Casas Bahia foram removidas do
# catálogo inteiro (bloqueiam toda requisição automatizada, mesmo com
# Playwright sem disfarce nenhum — ver atualizacao_precos.py e README).
#
# **`preco` e `em_estoque` são OBRIGATÓRIOS pra uma loja aparecer** nesse
# produto — `popular_produtos_e_precos` só cria uma oferta quando os dois
# estão presentes (nunca simulado por aleatoriedade, nem pra Amazon, que
# antes era exceção). `imagem` é sempre opcional. `url` sozinho, sem
# `preco`, não gera oferta nenhuma — é só um resquício documentado do
# processo de pesquisa (ver comentários pontuais: várias lojas têm
# catálogo com "price": 0/OutOfStock — confirmado ao vivo que é falta de
# estoque real, não bug — então a chave existe só pra registrar a
# investigação, mas não produz `Price` nenhum).
#
# Bemol/Brastemp/Consul/Electrolux/Carrefour/Americanas/Fast Shop/Kabum/
# Angeloni (todos VTEX) expõem preço/estoque via JSON-LD estático. Samsung
# usa `shop.samsung.com` (JSON-LD estático também, achado via WebSearch —
# não confundir com `www.samsung.com`, o site institucional/marketing
# carregado por JS). **LG nunca tem `preco` real** — o site é carregado
# por JavaScript e bloqueia Playwright com 403 via Akamai (mesma categoria
# de proteção anti-bot que já bloqueava Magazine Luiza/Casas Bahia) — por
# isso a loja "LG" NUNCA aparece como oferta em nenhum produto LG (só
# `url`/`imagem`, sem preço pra mostrar). Amazon não publica JSON-LD
# nenhum — cada página real foi verificada AO VIVO com Playwright (não só
# o status HTTP, que sempre retorna 200 mesmo com o item indisponível);
# a maioria mostrou "Não disponível. Não temos previsão de quando este
# produto estará disponível novamente" — sem preço nenhum pra registrar,
# então a Amazon só aparece nos poucos produtos onde teve preço real
# confirmado em estoque no momento da verificação.
PRODUTOS_GELADEIRAS = [
    {
        "brand": "Electrolux", "model": "DF44", "nome_curto": "Frost Free 382L",
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
            # Mesmo modelo BRM44HB na TVLar (rede física de Manaus) —
            # JSON-LD real, em estoque.
            "TVLar": {
                "url": "https://www.tvlar.com.br/geladeira-brastemp-frost-free-duplex-375l-branca-110v-brm44hb/p",
                "preco": 3675.55, "em_estoque": True,
                "imagem": "https://tvlar.vtexassets.com/arquivos/ids/19935460/1ptUFjkxBC6keDdyR2eF87aTViTdoVHc.jpg?v=639090016567570000",
            },
        },
    },
    {
        "brand": "Brastemp", "model": "BRE80", "nome_curto": "Inverse Frost Free 573L",
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
            # BRE66AK (500L Inverse, mesma linha/classe da nossa BRE80) na
            # Havan — microdata schema.org real (não JSON-LD script, mas
            # `itemprop`/`meta` embutidos no HTML do produto principal,
            # confirmado dentro do bloco `product-info-main`, não um item
            # de carrossel de "produtos relacionados"): de R$5.499,90 por
            # R$4.899,90 (~11%, selo "-11%" na própria página), mas
            # `OutOfStock` — preço real registrado, sem promoção (deixar
            # de mostrar desconto num item esgotado evita confusão visual,
            # mesmo critério já usado noutras lojas esgotadas).
            "Havan": {
                "url": "https://www.havan.com.br/geladeira-inteligente-smart-brastemp-frost-free-inverse-500l-bre66ak-diversos/p",
                "preco": 4899.90, "em_estoque": False,
            },
        },
    },
    {
        "brand": "Consul", "model": "CRB39", "nome_curto": "Frost Free 340L",
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
            # CRM50MB (412L Duplex, praticamente idêntica à nossa CRM50FB
            # 410L) na Havan — microdata schema.org real, dentro do bloco
            # `product-info-main` do produto principal (não confundir com
            # um preço de carrossel de produto relacionado, que a mesma
            # página também tem, com a mesma estrutura de classe CSS).
            # `InStock`, sem promoção ativa no momento.
            "Havan": {
                "url": "https://www.havan.com.br/geladeira-frost-free-duplex-consul-412l-crm50mb/p",
                "preco": 3799.90, "em_estoque": True,
            },
            # CRM56FBANA (451L Duplex, mesma classe) na APA Móveis (rede
            # física de Manaus) — JSON-LD real (`Offer` solto, não
            # aninhado), em estoque.
            "APA Móveis": {
                "url": "https://www.apamoveis.com.br/geladeira-duplex-frost-free-painel-eletronico-451l-crm56fbana-127v-branco-consul-p16284",
                "preco": 4479.00, "em_estoque": True,
                "imagem": "https://d1likr6vgtxkkw.cloudfront.net/Custom/Content/Products/16/28/16284_geladeira-duplex-frost-free-painel-eletronico-451l-crm56fbana-127v-branco-consul_l1_638731437616435328.webp",
            },
        },
    },
    {
        "brand": "Samsung", "model": "RT46", "nome_curto": "Frost Free Inverter 460L",
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

# Micro-ondas (2ª categoria com produto de verdade, depois de Geladeiras)
# — mesmas 5 marcas quando fizeram sentido, EXCETO Samsung: WebSearch
# confirmou que a Samsung não tem presença de catálogo real de
# micro-ondas no Brasil (os resultados de busca só retornavam produtos
# de Portugal/África) — forçar ela aqui seria inventar uma marca que não
# vende essa categoria de verdade aqui, o mesmo erro já corrigido antes
# pra Bemol+LG em geladeiras. Panasonic entrou no lugar (marca
# historicamente forte em micro-ondas no Brasil, catálogo real
# confirmado, loja oficial "Parceiros Panasonic" também VTEX).
#
# Specs: `capacidade_litros`, `potencia_watts` (só quando confirmado —
# várias fontes só davam "alta potência" sem número exato, e não vale
# inventar um watts específico), `grill` (bool), `tipo` (Solo/Grill/
# Embutir), `cor`, `voltagem`, `dimensoes_cm`.
PRODUTOS_MICROONDAS = [
    {
        "brand": "Electrolux", "model": "MTO30", "nome_curto": "Solo 20L",
        "specs": {"capacidade_litros": 20, "grill": False, "tipo": "Solo", "cor": "Branco"},
        # Loja oficial da Electrolux — JSON-LD real, em estoque.
        "lojas_reais": {
            "Electrolux": {
                "url": "https://loja.electrolux.com.br/micro-ondas-com-funcao-tira-odor-electrolux-mto30/p",
                "preco": 529.00, "em_estoque": True,
                "imagem": "https://electrolux.vtexassets.com/arquivos/ids/213875/Micro_ondas_MTO30_frontal_1000x1000.jpg?v=638796669337900000",
            },
            # Achada no Carrefour — JSON-LD real, mas com "price": 0 (mesmo
            # problema de catálogo já visto em Geladeiras). Amazon (2
            # ASINs testados) confirmado indisponível ao vivo, sem preço
            # nenhum pra registrar — nenhuma das duas entra.
            "Carrefour": {
                "url": "https://www.carrefour.com.br/microondas-com-funcao-tira-odor-20l-electrolux-220v-mto30-branco-mp929917524/p",
            },
        },
    },
    {
        "brand": "Electrolux", "model": "MI41S", "nome_curto": "Painel Integrado 31L",
        "specs": {"capacidade_litros": 31, "grill": False, "tipo": "Solo", "cor": "Inox Espelhado"},
        # Loja oficial da Electrolux — JSON-LD real, em estoque.
        "lojas_reais": {
            "Electrolux": {
                "url": "https://loja.electrolux.com.br/micro-ondas-painel-integrado-electrolux-mi41s/p",
                "preco": 749.00, "em_estoque": True,
                "imagem": "https://electrolux.vtexassets.com/arquivos/ids/213863/Micro-ondas_MI41S_frontal_1000x1000.jpg?v=638796662872700000",
            },
            # Carrefour — JSON-LD real E reconferido ao vivo com
            # Playwright: sem aviso de indisponibilidade, com desconto
            # real à vista no PIX (R$906,19 no cartão, R$879,00 no PIX,
            # ~3%).
            "Carrefour": {
                "url": "https://www.carrefour.com.br/produto/micro-ondas-electrolux-litros-inox-espelhado-com-painel-integrado-funcao-tira-odor-e-receitas-mis-v-25254",
                "preco": 879.00, "em_estoque": True,
                "preco_original": 906.19, "promo_dias": 10, "promo_pix": True,
                "imagem": "https://carrefourbr.vtexassets.com/arquivos/ids/215575781/9966730_1.jpg?v=639180956466830000",
            },
            # Amazon — sem JSON-LD, confirmado AO VIVO com Playwright: em
            # estoque, preço real na página.
            "Amazon": {
                "url": "https://www.amazon.com.br/Micro-Ondas-Electrolux-Prata-Painel-Integrado/dp/B076XCSJ4Q",
                "preco": 749.00, "em_estoque": True,
                "imagem": "https://m.media-amazon.com/images/I/51jWG1vyGyL._AC_SX679_.jpg",
            },
            # Bemol — JSON-LD real, mas indisponível.
            "Bemol": {
                "url": "https://www.bemol.com.br/micro-ondas-electrolux-31l-painel-integrado-espelhado-127v-inox-mi41s/p",
                "preco": 1049.00, "em_estoque": False,
                "imagem": "https://bemol.vtexassets.com/arquivos/ids/166933/182284.jpg?v=639034236273270000",
            },
        },
    },
    {
        "brand": "Brastemp", "model": "BMJ38AR", "nome_curto": "Ative Grill 38L",
        "specs": {"capacidade_litros": 38, "grill": True, "tipo": "Grill", "cor": "Inox Espelhado"},
        # Loja oficial da Brastemp — achado direto no JSON-LD embutido no
        # HTML (não veio via BeautifulSoup script[type=application/ld+json],
        # mas é o mesmo formato Product/Offer real). PROMOÇÃO REAL: de
        # R$1.639 por R$1.027,80 (~37%, o maior desconto achado nesta
        # categoria) — `listPrice` via estado embutido Apollo/GraphQL,
        # mesma técnica já usada em Geladeiras.
        "lojas_reais": {
            "Brastemp": {
                "url": "https://www.brastemp.com.br/micro-ondas-brastemp-ative-38l-bmj38ar/p",
                "preco": 1027.80, "em_estoque": True,
                "preco_original": 1639.00, "promo_dias": 7,
                "imagem": "https://brastemp.vtexassets.com/arquivos/ids/255318/01_Brastemp_Micro_ondas_BMJ38AR_Imagem_Fechado--1-.png?v=638858514969700000",
            },
            # Fast Shop e Kabum — JSON-LD real nas duas, mas AMBAS
            # indisponíveis no momento (preço real registrado, sem
            # destacar a promoção que a Fast Shop mostra, já que não dá
            # pra comprar ali — mesmo critério de sempre).
            "Fast Shop": {
                "url": "https://site.fastshop.com.br/micro-ondas-brastemp-ative-38-litros-espelhado-com-grill-inox---bmj38ar-brbmj38ar_prd/p",
                "preco": 1419.00, "em_estoque": False,
                "imagem": "https://fastshopbr.vtexassets.com/arquivos/ids/5295867/0_0_675b42eb447c42f8bd09ef3c.jpg?v=639202588417930000",
            },
            "Kabum": {
                "url": "https://www.kabum.com.br/produto/183255/micro-ondas-brastemp-ative-38-litros-com-grill-127v-inox-bmj38ar",
                "preco": 1284.60, "em_estoque": False,
                "imagem": "https://images5.kabum.com.br/produtos/fotos/sync_mirakl/183255/Micro-Ondas-Brastemp-Ative-38-Litros-Com-Grill-127V-Inox-Bmj38ar_1685627296_g.jpg",
            },
        },
    },
    {
        "brand": "Brastemp", "model": "BMO45AR", "nome_curto": "Embutir Gourmand 40L",
        "specs": {"capacidade_litros": 40, "grill": True, "tipo": "Embutir", "cor": "Inox"},
        # Loja oficial da Brastemp — modelo de embutir premium (Sistema 3D
        # + Sensor Cooking), a opção "mais exclusiva" desta categoria.
        # PROMOÇÃO REAL: de R$16.499 por R$13.199,99 (~20%).
        "lojas_reais": {
            "Brastemp": {
                "url": "https://www.brastemp.com.br/micro-ondas-de-embutir-brastemp-gourmand-40-litros-inox-com-sistema-3d-e-sensor-cooking--bmo45ar/p",
                "preco": 13199.99, "em_estoque": True,
                "preco_original": 16499.00, "promo_dias": 5,
                "imagem": "https://brastemp.vtexassets.com/arquivos/ids/267249/01_Brastemp_Micro_ondas_BMO45AR_Imagem_Frontal.jpg?v=638974470401830000",
            },
            # Carrefour — JSON-LD real + Playwright confirmou "Comprar"
            # ativo (sem aviso de indisponibilidade). Preço de cartão
            # R$14.619, com desconto de 5% no PIX (R$13.888,05).
            "Carrefour": {
                "url": "https://www.carrefour.com.br/microondas-de-embutir-brastemp-gourmand-40-litros-inox-com-sistema-3d-e-sensor-cooking-bmo45ar-220v-mp920201703/p",
                "preco": 13888.05, "em_estoque": True,
                "preco_original": 14619.00, "promo_dias": 10, "promo_pix": True,
            },
            # Amazon — Playwright confirmou "Somente 3 em estoque" (real,
            # sem fallback/estimativa).
            "Amazon": {
                "url": "https://www.amazon.com.br/Micro-ondas-embutir-Brastemp-Gourmand-BMO45ARBNA/dp/B0831NX2D5",
                "preco": 13315.00, "em_estoque": True,
            },
            # Kabum — JSON-LD real, sem estoque no momento da checagem.
            "Kabum": {
                "url": "https://www.kabum.com.br/produto/266058/microondas-de-embutir-brastemp-gourmand-40-litros-inox-220v-bmo45arbna",
                "preco": 15401.69, "em_estoque": False,
            },
        },
    },
    {
        "brand": "Consul", "model": "CMS23AE", "nome_curto": "Marmita 23L",
        "specs": {"capacidade_litros": 23, "grill": False, "tipo": "Solo", "cor": "Preto"},
        # Loja oficial da Consul — JSON-LD real. PROMOÇÃO REAL: de R$599
        # por R$504,90 (~16%). Modelo irmão CMS23AR (mesma capacidade,
        # cor inox) achado real na Fast Shop — aproximação de cor,
        # mesmo padrão já usado em Geladeiras (BRE85AK/BRO85ME etc.).
        # CONFIRMADO (pesquisa dedicada): esse é o micro-ondas "entrada"
        # da linha Marmita — não achado em Carrefour/Amazon/Kabum/
        # Americanas/Bemol/Angeloni (só em varejistas menores fora do
        # nosso catálogo de lojas, tipo Taqi/CompraCerta/WebcoPeças).
        # Escassez real do próprio mercado, não falha de pesquisa.
        "lojas_reais": {
            "Consul": {
                "url": "https://www.consul.com.br/micro-ondas-consul-23l-preto-com-funcao-marmita-cms23ae/p",
                "preco": 504.90, "em_estoque": True,
                "preco_original": 599.00, "promo_dias": 6,
                "imagem": "https://consul.vtexassets.com/arquivos/ids/283815/01_Consul_Micro_ondas_CMS23AE.jpg?v=639107534154700000",
            },
            "Fast Shop": {
                "url": "https://site.fastshop.com.br/micro-ondas-23-litros-com-funcao-marmita-inox-consul---cms23ar-170159/p",
                "preco": 619.00, "em_estoque": True,
                "preco_original": 849.00, "promo_dias": 6,
            },
        },
    },
    {
        "brand": "Consul", "model": "CMS46AB", "nome_curto": "Menu Fácil 32L",
        "specs": {"capacidade_litros": 32, "grill": False, "tipo": "Solo", "cor": "Branco"},
        # Loja oficial da Consul — JSON-LD real. PROMOÇÃO REAL: de R$969
        # por R$604,80 (~38%).
        "lojas_reais": {
            "Consul": {
                "url": "https://www.consul.com.br/micro-ondas-consul-32-litros-branco-com-menu-facil-cms46ab/p",
                "preco": 604.80, "em_estoque": True,
                "preco_original": 969.00, "promo_dias": 4,
                "imagem": "https://consul.vtexassets.com/arquivos/ids/267975/01_Consul_Micro_ondas_CMS46AB_Imagem_Frontal.jpg?v=638975360656400000",
            },
            # Carrefour — JSON-LD real E reconferido ao vivo com
            # Playwright: sem aviso de indisponibilidade, com desconto
            # real à vista no PIX (R$705,43 no cartão, R$649,00 no PIX,
            # ~8%).
            "Carrefour": {
                "url": "https://www.carrefour.com.br/microondas-consul-32-litros-branco-com-menu-facil-cms46ab-110v-6558828/p",
                "preco": 649.00, "em_estoque": True,
                "preco_original": 705.43, "promo_dias": 10, "promo_pix": True,
                "imagem": "https://carrefourbr.vtexassets.com/arquivos/ids/26440123/6558828_1.jpg?v=637729232468330000",
            },
            # Amazon — sem JSON-LD, confirmado AO VIVO com Playwright: em
            # estoque, preço real na página.
            "Amazon": {
                "url": "https://www.amazon.com.br/Micro-Ondas-32-Cms46Abana-Branco-Consul/dp/B0BL88R1Q8",
                "preco": 659.00, "em_estoque": True,
                "imagem": "https://m.media-amazon.com/images/I/51I38-LDDxL._AC_SX679_.jpg",
            },
            # Modelo próximo CMS46AR (mesma capacidade/linha, cor cinza
            # espelhado em vez de branco) na Bemol — JSON-LD real, em
            # estoque.
            "Bemol": {
                "url": "https://www.bemol.com.br/micro-ondas-consul-32-litros-espelhado-menu-facil-cinza-cms46ar/p",
                "preco": 659.00, "em_estoque": True,
                "imagem": "https://bemol.vtexassets.com/arquivos/ids/566950/223771.jpg?v=639080550814130000",
            },
        },
    },
    {
        "brand": "LG", "model": "MS3043BR", "nome_curto": "Solo Limpa Fácil 30L",
        "specs": {"capacidade_litros": 30, "grill": False, "tipo": "Solo", "cor": "Prata"},
        # Site da LG — mesma limitação de sempre (JS-rendered, Akamai
        # bloqueia Playwright): só URL + imagem reais, sem preço/estoque.
        # Achado no Carrefour com preço real — reconferido AO VIVO com
        # Playwright (não só JSON-LD estático, mesmo cuidado de sempre):
        # sem aviso de indisponibilidade, mostra até um desconto real à
        # vista no PIX (R$772,16 no cartão, R$749,00 no PIX, ~3%).
        "lojas_reais": {
            "LG": {
                "url": "https://www.lg.com/br/micro-ondas/micro-ondas-solo/ms3043br/",
                "imagem": "https://www.lg.com/content/dam/channel/wcms/br/images/fornos-microondas/ms3043br_fslflgz_essp_br_c/gallery/450.jpg",
            },
            "Carrefour": {
                "url": "https://www.carrefour.com.br/microondas-lg-mesa-30-litros-prata-limpa-facil-ms3043br-110v-3503577/p",
                "preco": 749.00, "em_estoque": True,
                "preco_original": 772.16, "promo_dias": 10, "promo_pix": True,
                "imagem": "https://carrefourbr.vtexassets.com/arquivos/ids/168195324/microondas-lg-ms3043br-20l-esp-110v-1.jpg?v=638588279386400000",
            },
        },
    },
    {
        "brand": "LG", "model": "MH7093BRA", "nome_curto": "Grill Quartzo 30L",
        "specs": {"capacidade_litros": 30, "grill": True, "tipo": "Grill", "cor": "Prata"},
        # Site da LG — mesma limitação (sem preço/estoque real). Achado no
        # Carrefour, mas CONFIRMADO ao vivo com Playwright: mesmo o
        # JSON-LD estático dizendo "InStock" (desatualizado), a página
        # renderizada mostra "não possui disponibilidade para entrega na
        # sua região" — mesmo padrão de sempre, preço real registrado com
        # `em_estoque: False`.
        "lojas_reais": {
            "LG": {
                "url": "https://www.lg.com/br/micro-ondas/micro-ondas-grill/mh7093bra/",
                "imagem": "https://www.lg.com/content/dam/channel/wcms/br/images/fornos-microondas/mh7093bra_fslglgz_essp_br_c/Thumb_450.jpg",
            },
            "Carrefour": {
                "url": "https://www.carrefour.com.br/micro-ondas-lg-grill-mh7093bra-30-litros-prata-220v-5908442/p",
                "preco": 879.00, "em_estoque": False,
                "imagem": "https://carrefourbr.vtexassets.com/arquivos/ids/23639731/5908442_1.jpg?v=637660151320400000",
            },
        },
    },
    {
        "brand": "Panasonic", "model": "NN-ST25", "nome_curto": "Antibacteria Ag 21L",
        "specs": {"capacidade_litros": 21, "potencia_watts": 700, "grill": False, "tipo": "Solo",
                   "cor": "Branco", "dimensoes_cm": "26 x 44.2 x 36.6"},
        # Loja oficial "Parceiros Panasonic" — JSON-LD real (2 SKUs/cores
        # com o mesmo preço; um deles OutOfStock, o outro InStock —
        # usado o InStock).
        "lojas_reais": {
            "Panasonic": {
                "url": "https://parceiros.panasonic.com.br/micro-ondas-panasonic-st25-branco-nn-st25lwru/p",
                "preco": 569.05, "em_estoque": True,
                "imagem": "https://panasonic.vtexassets.com/arquivos/ids/163258/Micro_Frontal_Branco.jpg?v=638786914020070000",
            },
            # Kabum — JSON-LD real, mas indisponível.
            "Kabum": {
                "url": "https://www.kabum.com.br/produto/162080/micro-ondas-panasonic-nn-st25lwrun-21-litros-branco-cinza-110v",
                "preco": 617.22, "em_estoque": False,
                "imagem": "https://images0.kabum.com.br/produtos/fotos/sync_mirakl/162080/Micro-ondas-Panasonic-Nn-st25lwrun-21-Litros-Branco-cinza-110v_1693859294_g.jpg",
            },
            # Amazon — sem JSON-LD, confirmado AO VIVO com Playwright: em
            # estoque, preço real na página.
            "Amazon": {
                "url": "https://www.amazon.com.br/Micro-ondas-Panasonic-NN-ST25LWRUN-Branco-110V/dp/B08JN318M2",
                "preco": 499.00, "em_estoque": True,
                "imagem": "https://m.media-amazon.com/images/I/515SGypJAmL._AC_SX679_.jpg",
            },
        },
    },
    {
        "brand": "Panasonic", "model": "NN-GT68", "nome_curto": "SmartSense Grill 30L",
        "specs": {"capacidade_litros": 30, "potencia_watts": 900, "grill": True, "tipo": "Grill", "cor": "Preto"},
        # Achado na Fast Shop — JSON-LD real. PROMOÇÃO REAL: de
        # R$1.239,37 por R$1.099, mas `OutOfStock` (quantity: 0) —
        # preço real registrado sem desconto em destaque (mesmo critério
        # já usado em Geladeiras pra item esgotado: não faz sentido
        # destacar promoção de algo que não dá pra comprar ali). Kabum
        # também achado, real, mas igualmente indisponível. Amazon
        # testado (Playwright) — página real mas sem oferta em destaque
        # nem preço claro (mesmo padrão "nenhuma oferta em destaque" já
        # visto antes com outras lojas); não entra, sem inventar preço.
        "lojas_reais": {
            "Fast Shop": {
                "url": "https://site.fastshop.com.br/micro-ondas-de-mesa-panasonic-com-30-litros-de-capacidade-e-grill-preto---nn-gt68lbru-panngt68l_prd/p",
                "preco": 1099.00, "em_estoque": False,
                "imagem": "https://fastshopbr.vtexassets.com/arquivos/ids/5293945/0_0_675b43a6447c42f8bd09ff9b.jpg?v=639202480184070000",
            },
            "Kabum": {
                "url": "https://www.kabum.com.br/produto/182809/micro-ondas-panasonic-tecnologia-dupla-refeicao-preto-30-litros-110v-nn-gt68lbrun",
                "preco": 1067.00, "em_estoque": False,
                "imagem": "https://images9.kabum.com.br/produtos/fotos/sync_mirakl/182809/Microondas-Panasonic-Tecnologia-Dupla-Refei-o-Preto-30-Litros-110v-Nn-gt68lbrun_1689988689_g.jpg",
            },
        },
    },
]

DIAS_DE_HISTORICO = 30


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


def popular_produtos_e_precos(categoria: Category, lojas: list[Store], produtos_lista: list[dict]) -> list[Product]:
    """Genérico por categoria desde que Fogões/Lava-louças/Micro-ondas
    ganharam produtos de verdade — cada categoria tem sua própria lista
    de dados (`PRODUTOS_GELADEIRAS`, `PRODUTOS_MICROONDAS`, ...), mas a
    lógica de "só entra loja com preço real confirmado" é a mesma pra
    todas (ver comentário mais abaixo)."""
    lojas_fisicas = [l for l in lojas if l.type == Store.TIPO_FISICA]

    produtos = []
    for dados in produtos_lista:
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
            category=categoria,
            specs=dados["specs"],
            image_url=imagem_real,
            slug=slugify(f"{nome}-{dados['model']}"),
        )
        db.session.add(produto)
        produtos.append(produto)

        # SÓ entram lojas com PREÇO REAL confirmado pra esse produto
        # específico (pedido explícito do usuário: "eu só quero LOJAS
        # REAIS SEM INVENTAR NADA E COM PREÇOS REAIS") — nada de preço/
        # estoque simulado por aleatoriedade, nem pra Amazon (que antes
        # era a única exceção sempre incluída, mesmo sem dado real — essa
        # exceção foi removida). Uma loja (universal, da marca, ou física)
        # só vira uma oferta visível quando `lojas_reais[nome]` tem a
        # chave `"preco"` — sem isso, ela simplesmente não aparece nesse
        # produto, em vez de aparecer com um número inventado.
        lojas_online = [l for l in lojas if l.type == Store.TIPO_ONLINE]

        selecionadas = []
        for nome in ("Amazon", "Carrefour", "Americanas", "Fast Shop", "Kabum", "Angeloni", "Havan"):
            loja_universal = next((l for l in lojas_online if l.name == nome), None)
            if loja_universal and "preco" in lojas_reais.get(nome, {}):
                selecionadas.append(loja_universal)

        loja_da_marca = next((l for l in lojas_online if l.name == dados["brand"]), None)
        if loja_da_marca and "preco" in lojas_reais.get(dados["brand"], {}):
            selecionadas.append(loja_da_marca)

        # TODAS as lojas físicas com preço real confirmado entram (Bemol,
        # TVLar, APA Móveis — não é mais só uma escolhida por sorteio/
        # preenchimento). Um produto pode ter 0, 1 ou várias lojas
        # físicas, dependendo só de quantas realmente vendem aquele
        # modelo (ex: nenhuma delas vende LG).
        for loja_fisica in lojas_fisicas:
            if "preco" in lojas_reais.get(loja_fisica.name, {}):
                selecionadas.append(loja_fisica)

        for loja in selecionadas:
            dado_real = lojas_reais[loja.name]
            preco = Decimal(str(dado_real["preco"]))
            em_estoque = dado_real["em_estoque"]

            # Promoção temporária REAL (ver comentários pontuais em
            # `lojas_reais` — achadas comparando o estado embutido
            # `priceRange.listPrice` vs. `priceRange.sellingPrice`/
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
            if "preco_original" in dado_real:
                preco_original = Decimal(str(dado_real["preco_original"]))
                promo_valid_until = datetime.utcnow() + timedelta(days=dado_real.get("promo_dias", 5))
                promo_pix = dado_real.get("promo_pix", False)

            db.session.add(Price(
                product=produto,
                store=loja,
                price=preco,
                original_price=preco_original,
                promo_pix=promo_pix,
                promo_valid_until=promo_valid_until,
                url=dado_real["url"],
                in_stock=em_estoque,
                last_updated=datetime.utcnow() - timedelta(hours=random.randint(1, 6)),
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
    produtos = popular_produtos_e_precos(categorias["geladeiras"], lojas, PRODUTOS_GELADEIRAS)
    produtos += popular_produtos_e_precos(categorias["micro-ondas"], lojas, PRODUTOS_MICROONDAS)
    gerar_historico_de_precos(produtos)

    db.session.commit()

    total_precos = sum(len(p.prices) for p in produtos)
    # sem acento de propósito aqui — o console do Windows (cp1252/850) as
    # vezes exibe texto UTF-8 acentuado errado; os dados no banco continuam
    # UTF-8 corretos, isso e so pra nao confundir quem rodar `python seed.py`
    print(f"OK: {len(categorias)} categorias, {len(lojas)} lojas, {len(produtos)} produtos.")
    print(f"    {total_precos} precos (ofertas produto+loja).")
    print(f"    Historico: {DIAS_DE_HISTORICO + 1} pontos por oferta.")
