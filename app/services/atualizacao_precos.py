"""Atualização automática de preços (Fase 2, pedido explícito do usuário):
busca a página real de cada oferta (Price.url) e extrai preço/estoque/
imagem de lá — o painel admin (Passo 8) vira só um recurso de EMERGÊNCIA,
não a fonte principal.

Duas estratégias de extração, nessa ordem de preferência:

1. **Dados estruturados (JSON-LD/schema.org)**: muita loja (confirmado
   testando contra uma página REAL da Bemol) já publica um bloco
   `<script type="application/ld+json">` com `@type: Product` — preço,
   disponibilidade e imagem exatos, sem ambiguidade nenhuma. Quando isso
   existe, é sempre preferível: instantâneo, de graça, sem depender de
   IA nenhuma pra "adivinhar" o preço num texto solto.
2. **Groq (LLM) como fallback**, só quando o site não publica esse
   schema. Importante ser honesto sobre o que isso é: a Groq sozinha NÃO
   navega na internet — ela é uma API de inferência sobre um modelo já
   treinado, sem acesso à web ao vivo por conta própria. O fluxo real é:
   este módulo busca a página de verdade via HTTP (`requests`),
   respeitando o `robots.txt` do site antes de tentar, e só DEPOIS manda
   o texto já extraído da página pra Groq — que funciona aqui como um
   "parser inteligente" (mais resistente a mudança de layout que um
   scraper de seletor CSS fixo), não como substituto da busca em si.

Limitação conhecida: muitos e-commerces proíbem scraping automatizado nos
próprios Termos de Uso, e alguns bloqueiam ativamente esse tipo de acesso
— testado contra os 6 sites do seed: Magazine Luiza e Casas Bahia
retornam 403 (bloqueio de bot) até pra buscar o próprio robots.txt;
Amazon e Bemol permitem. Este módulo respeita robots.txt e se identifica
honestamente (User-Agent próprio, não finge ser navegador) — mas isso
não é garantia legal de que TODO site aqui permite a prática; a fonte
mais segura de verdade continua sendo um programa de afiliados oficial
(Amazon Associates, Awin, Lomadee), como já documentado no brief
original. Ver seção "Atualização automática de preços" do README antes
de apontar isso pra um site novo.
"""
from __future__ import annotations

import json
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
    """Busca a página UMA VEZ + extrai (JSON-LD primeiro, Groq como
    fallback) + grava no banco (Price atual + novo ponto de
    PriceHistory). Devolve True/False (sucesso/falha) pro script de lote
    poder contar/logar."""
    if not preco.url or preco.url == "#":
        return False

    sopa = buscar_pagina(preco.url)
    if sopa is None:
        return False

    dados = extrair_de_jsonld(sopa)
    origem = "JSON-LD"
    if dados is None:
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
