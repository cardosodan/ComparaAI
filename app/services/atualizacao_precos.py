"""Atualização automática de preços (Fase 2, pedido explícito do usuário):
busca a página real de cada oferta (Price.url) e extrai preço/estoque/
imagem de lá — o painel admin (Passo 8) vira só um recurso de EMERGÊNCIA,
não a fonte principal.

Três estratégias de extração, nessa ordem de preferência:

1. **Dados estruturados (JSON-LD/schema.org)**: muita loja (confirmado
   testando contra uma página REAL da Bemol) já publica um bloco
   `<script type="application/ld+json">` com `@type: Product` — preço,
   disponibilidade e imagem exatos, sem ambiguidade nenhuma. Quando isso
   existe, é sempre preferível: instantâneo, de graça, sem depender de
   IA nenhuma pra "adivinhar" o preço num texto solto.
2. **Playwright (navegador headless de verdade)**, quando o site não
   publica JSON-LD. Confirmado pra Samsung/LG: o HTML bruto que
   `requests` recebe não tem preço NENHUM (nem em JSON-LD nem em texto
   solto) porque o preço só é preenchido por uma chamada de API que o
   JAVASCRIPT do navegador faz depois do carregamento inicial — isso não
   é proteção nenhuma, é só o jeito que o site foi construído, então
   resolver com um navegador de verdade (que executa o JS igual um
   usuário normal) é legítimo, não é burlar nada. Extrai preço/estoque
   do texto visível da página já renderizada (regex procurando "R$" +
   sinais de indisponibilidade tipo "avise-me quando chegar").
3. **Groq (LLM) como último fallback**, quando nem JSON-LD nem
   Playwright acham nada (site bloqueou os dois, ou o texto não tem
   preço reconhecível). Importante ser honesto sobre o que isso é: a
   Groq sozinha NÃO navega na internet — ela é uma API de inferência
   sobre um modelo já treinado, sem acesso à web ao vivo por conta
   própria. O fluxo real é: este módulo busca a página de verdade via
   HTTP (`requests`), respeitando o `robots.txt` do site antes de
   tentar, e só DEPOIS manda o texto já extraído da página pra Groq —
   que funciona aqui como um "parser inteligente" (mais resistente a
   mudança de layout que um scraper de seletor CSS fixo), não como
   substituto da busca em si.

Limitação conhecida, e onde a linha é traçada: muitos e-commerces
proíbem scraping automatizado nos próprios Termos de Uso, e alguns
bloqueiam ativamente esse tipo de acesso — testado contra os 6 sites do
seed (mais o site oficial de cada marca): Magazine Luiza e Casas Bahia
retornam 403 (bloqueio de bot) até pra buscar o próprio robots.txt; o
site da LG deixa `requests`/curl passar mas bloqueia um Chromium
headless de verdade com 403 via Akamai (confirmado testando — mesmo
navegador sem NENHUM disfarce, só rodando headless); Amazon, Bemol,
Brastemp, Consul, Electrolux e Samsung permitem os dois. **Este módulo
não tenta burlar bloqueio nenhum** — nem com Playwright, nem com nada
mais (sem stealth plugins, sem rotação de proxy, sem spoofing de
fingerprint): quando um site bloqueia de propósito, a função de extração
correspondente simplesmente devolve `None` e o fluxo desiste daquela
oferta. Ele respeita robots.txt e se identifica honestamente
(User-Agent próprio, não finge ser navegador) — mas isso não é garantia
legal de que TODO site aqui permite a prática; a fonte mais segura de
verdade continua sendo um programa de afiliados oficial (Amazon
Associates, Awin, Lomadee), como já documentado no brief original. Ver
seção "Atualização automática de preços" do README antes de apontar
isso pra um site novo.
"""
from __future__ import annotations

import json
import re
import time
import urllib.robotparser
from datetime import datetime
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from app import db
from app.models import Price, PriceHistory
from config import Config

USER_AGENT = "ComparaAI-PriceBot/1.0 (bot de comparação de preços; contato: configure em atualizacao_precos.py)"
TIMEOUT_SEGUNDOS = 12
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
PAUSA_ENTRE_REQUISICOES_SEGUNDOS = 3  # educado com o servidor do site — cortesia nossa, não é limite deles

_cache_robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}


def pode_buscar(url: str) -> bool:
    """Consulta (e cacheia por domínio) o robots.txt do site antes de
    buscar qualquer página — não tenta burlar/ignorar isso em nenhuma
    circunstância. Sem resposta válida (bloqueio, erro, timeout) = trata
    como NÃO permitido, o oposto do que muitos scrapers fazem de
    propósito: na dúvida, não busca."""
    dominio = urlparse(url).netloc
    if dominio not in _cache_robots:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(f"https://{dominio}/robots.txt")
        try:
            rp.read()
            _cache_robots[dominio] = rp
        except Exception:
            _cache_robots[dominio] = None

    rp = _cache_robots[dominio]
    return rp.can_fetch(USER_AGENT, url) if rp else False


def buscar_pagina(url: str) -> BeautifulSoup | None:
    if not pode_buscar(url):
        print(f"[atualizacao_precos] robots.txt não permite buscar: {url}")
        return None
    try:
        resposta = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_SEGUNDOS)
        resposta.raise_for_status()
    except requests.RequestException as erro:
        print(f"[atualizacao_precos] falha ao buscar {url}: {erro}")
        return None
    return BeautifulSoup(resposta.text, "html.parser")


def _eh_tipo_produto(tipo) -> bool:
    if isinstance(tipo, list):
        return any(_eh_tipo_produto(t) for t in tipo)
    return isinstance(tipo, str) and tipo.lower() == "product"


def extrair_de_jsonld(sopa: BeautifulSoup) -> dict | None:
    """Procura um bloco <script type="application/ld+json"> com
    @type: Product (schema.org) — quando existe, é a fonte mais confiável
    possível: preço exato, sem ambiguidade de texto solto."""
    for script in sopa.find_all("script", type="application/ld+json"):
        try:
            dados = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        candidatos = dados if isinstance(dados, list) else [dados]
        for item in candidatos:
            if not isinstance(item, dict) or not _eh_tipo_produto(item.get("@type")):
                continue

            bloco_ofertas = item.get("offers")
            if not isinstance(bloco_ofertas, dict):
                continue

            # AggregateOffer (comum quando tem 1+ vendedor) guarda lowPrice/
            # highPrice no nível de FORA, mas "availability" só existe na
            # oferta INDIVIDUAL aninhada em offers.offers[] — testando
            # contra uma página real (Bemol), pegar availability do nível
            # de fora sempre dava "" (chave não existe ali), o que fazia
            # todo produto parecer em estoque mesmo quando a página dizia
            # OutOfStock. Cai pro bloco de fora só se não for AggregateOffer
            # (Offer "solta", sem aninhamento).
            oferta_individual = bloco_ofertas.get("offers")
            if isinstance(oferta_individual, list):
                oferta_individual = oferta_individual[0] if oferta_individual else None
            if not isinstance(oferta_individual, dict):
                oferta_individual = bloco_ofertas

            preco = oferta_individual.get("price") or bloco_ofertas.get("lowPrice") or bloco_ofertas.get("price")
            if preco is None:
                continue

            disponibilidade = str(oferta_individual.get("availability", "")).lower()
            # schema.org: .../InStock, .../OutOfStock, .../LimitedAvailability.
            # Sem NENHUMA info de disponibilidade, assume em estoque (produto
            # listado com preço geralmente está disponível, na ausência de
            # sinal em contrário).
            em_estoque = "outofstock" not in disponibilidade if disponibilidade else True

            imagem = item.get("image")
            if isinstance(imagem, list):
                imagem = imagem[0] if imagem else None

            return {"preco": float(preco), "em_estoque": em_estoque, "imagem_url": imagem}
    return None


_SINAIS_DE_ESGOTADO = ("avise-me", "indispon", "esgotado", "fora de estoque", "sem estoque")


def extrair_via_playwright(url: str) -> dict | None:
    """Fallback pra sites sem JSON-LD onde o HTML bruto (`requests`) não
    tem preço nenhum — o preço só existe depois de uma chamada de API que
    o JAVASCRIPT do navegador faz, invisível pra qualquer requisição HTTP
    simples. Abre um Chromium headless de verdade, SEM nenhum disfarce
    (não esconde `navigator.webdriver`, não spoofa fingerprint, não usa
    proxy) — resolve o problema pra sites que só têm essa limitação
    técnica (confirmado: Samsung), mas devolve `None` de propósito quando
    o site bloqueia a automação de verdade (confirmado: LG bloqueia isso
    com 403 via Akamai, mesma categoria de proteção que já bloqueia
    Magazine Luiza/Casas Bahia mesmo com `requests` simples) — nesse caso
    o chamador cai pro próximo fallback (Groq) em vez de insistir."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[atualizacao_precos] Playwright não instalado — pulando esse fallback.")
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            resposta = page.goto(url, timeout=30000, wait_until="domcontentloaded")
            if resposta is None or resposta.status >= 400:
                browser.close()
                return None
            page.wait_for_timeout(5000)  # tempo pro JS da página buscar/renderizar o preço
            texto = page.inner_text("body")
            browser.close()
    except Exception as erro:
        print(f"[atualizacao_precos] Playwright falhou em {url}: {erro}")
        return None

    match_preco = re.search(r"R\$\s?([\d.]+,\d{2})", texto)
    if not match_preco:
        return None

    preco_valor = float(match_preco.group(1).replace(".", "").replace(",", "."))
    janela = texto[match_preco.end():match_preco.end() + 150].lower()
    em_estoque = not any(sinal in janela for sinal in _SINAIS_DE_ESGOTADO)

    return {"preco": preco_valor, "em_estoque": em_estoque, "imagem_url": None}


def extrair_com_groq(sopa: BeautifulSoup, produto_nome: str) -> dict | None:
    """Fallback pra quando o site não publica JSON-LD de Product —
    manda o TEXTO visível (remove <script>/<style>, sem isso o HTML bruto
    seria caro em tokens e cheio de ruído) pra Groq extrair em JSON."""
    if not Config.GROQ_API_KEY:
        print("[atualizacao_precos] GROQ_API_KEY não configurada — pulando extração via IA.")
        return None

    copia = BeautifulSoup(str(sopa), "html.parser")
    for tag in copia(["script", "style", "noscript"]):
        tag.decompose()
    texto_pagina = copia.get_text(separator=" ", strip=True)[:12000]

    prompt_sistema = (
        "Você recebe o texto extraído da página de um produto num site de e-commerce. "
        "Extraia o PREÇO ATUAL do produto (em reais), se está EM ESTOQUE, e a URL da "
        "imagem principal se conseguir identificar com confiança. "
        'Responda APENAS em JSON: {"preco": 1234.56, "em_estoque": true, "imagem_url": "https://..." ou null}. '
        "Se não conseguir achar o preço com confiança (página de erro, produto não "
        'encontrado, bloqueio/CAPTCHA, texto insuficiente), responda '
        '{"preco": null, "em_estoque": null, "imagem_url": null}. Nunca invente um preço.'
    )

    try:
        resposta = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {Config.GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": prompt_sistema},
                    {"role": "user", "content": f"Produto esperado: {produto_nome}\n\nTEXTO DA PÁGINA:\n{texto_pagina}"},
                ],
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "max_tokens": 300,
            },
            timeout=30,
        )
        resposta.raise_for_status()
        dados = json.loads(resposta.json()["choices"][0]["message"]["content"])
    except Exception as erro:
        print(f"[atualizacao_precos] falha ao consultar Groq: {erro}")
        return None

    return dados if dados.get("preco") else None


def atualizar_oferta(preco: Price) -> bool:
    """Busca a página (JSON-LD primeiro, Playwright depois, Groq como
    último fallback — ver docstring do módulo) + grava no banco (Price
    atual + novo ponto de PriceHistory). Devolve True/False (sucesso/
    falha) pro script de lote poder contar/logar."""
    if not preco.url or preco.url == "#":
        return False

    sopa = buscar_pagina(preco.url)

    dados = extrair_de_jsonld(sopa) if sopa is not None else None
    origem = "JSON-LD"

    if dados is None:
        # Playwright faz sua PRÓPRIA navegação (não reaproveita `sopa`,
        # que veio de `requests` sem executar JS nenhum) — só tenta se o
        # robots.txt permitir, mesma regra de `buscar_pagina` acima.
        if pode_buscar(preco.url):
            dados = extrair_via_playwright(preco.url)
            origem = "Playwright"

    if dados is None and sopa is not None:
        dados = extrair_com_groq(sopa, preco.product.name)
        origem = "Groq"

    if dados is None:
        return False

    print(f"[atualizacao_precos] extraído via {origem}: R$ {dados['preco']}")

    agora = datetime.utcnow()
    preco.price = dados["preco"]
    preco.in_stock = bool(dados.get("em_estoque", True))
    preco.last_updated = agora
    if dados.get("imagem_url") and not preco.product.image_url:
        preco.product.image_url = dados["imagem_url"]

    db.session.add(PriceHistory(
        product_id=preco.product_id,
        store_id=preco.store_id,
        price=dados["preco"],
        recorded_at=agora,
    ))
    db.session.commit()
    return True
