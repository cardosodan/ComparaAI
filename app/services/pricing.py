"""Agregação de preço/histórico pra exibição — página de produto (Passo 6).
Separado de search.py de propósito: search.py é sobre ACHAR produtos,
este módulo é sobre como EXIBIR preço/histórico de UM produto já achado.
"""
from collections import defaultdict
from datetime import datetime
from urllib.parse import quote_plus


def montar_historico_para_grafico(produto) -> dict:
    """Devolve {"labels": [...], "serie_media": [...], "series_por_loja":
    {nome_loja: [...]}} pronto pro Chart.js (brief seção 6.3: "por loja ou
    média"). Um ponto por dia (é como o seed gera, ver seed_data.
    gerar_historico_de_precos) — dia sem ponto pra uma loja específica
    vira `None` na série dela, o Chart.js pula o ponto sem quebrar a linha
    inteira."""
    pontos = sorted(produto.price_history, key=lambda h: h.recorded_at)
    if not pontos:
        return {"labels": [], "serie_media": [], "series_por_loja": {}}

    datas_ordenadas = sorted({p.recorded_at.date() for p in pontos})
    labels = [d.strftime("%d/%m") for d in datas_ordenadas]

    por_loja_e_data = defaultdict(dict)
    for ponto in pontos:
        por_loja_e_data[ponto.store.name][ponto.recorded_at.date()] = float(ponto.price)

    series_por_loja = {
        loja: [valores.get(d) for d in datas_ordenadas] for loja, valores in por_loja_e_data.items()
    }

    serie_media = []
    for d in datas_ordenadas:
        valores_do_dia = [valores[d] for valores in por_loja_e_data.values() if d in valores]
        serie_media.append(round(sum(valores_do_dia) / len(valores_do_dia), 2) if valores_do_dia else None)

    return {"labels": labels, "serie_media": serie_media, "series_por_loja": series_por_loja}


def tempo_relativo(momento: datetime, agora: datetime) -> str:
    """"atualizado há X horas" (brief seção 6.3) — texto pronto, não deixa
    conta de data solta no template Jinja."""
    horas = (agora - momento).total_seconds() / 3600
    if horas < 1:
        return "agora mesmo"
    if horas < 24:
        h = int(horas)
        return f"há {h} hora{'s' if h != 1 else ''}"
    dias = int(horas / 24)
    return f"há {dias} dia{'s' if dias != 1 else ''}"


# Padrão de busca REAL de cada loja (não uma URL de produto específico —
# isso é o `Price.url`, só existe de verdade pra Bemol hoje). Testado um
# por um via curl (com User-Agent de navegador) antes de usar qualquer um
# destes: Amazon (/s?k=), Brastemp/Consul (/s?q=, mesma plataforma VTEX)
# e Samsung/LG (/search) responderam 200 de verdade. Usuário pediu
# explicitamente pra entrar no site de verdade em vez de cair numa busca
# do Google — por isso essa tabela existe em vez do fallback anterior.
_PADROES_BUSCA_POR_SITE = {
    "https://www.amazon.com.br": "https://www.amazon.com.br/s?k={q}",
    "https://www.magazineluiza.com.br": "https://www.magazineluiza.com.br/busca/{q}/",
    # Casas Bahia bloqueou toda tentativa de verificação automatizada (403,
    # mesmo bloqueio de bot documentado em atualizacao_precos.py) — mas é
    # VTEX como Bemol/Brastemp/Consul, então usa o mesmo padrão /s?q= dessa
    # plataforma (alta confiança mesmo sem conseguir confirmar por curl).
    "https://www.casasbahia.com.br": "https://www.casasbahia.com.br/s?q={q}",
    "https://www.brastemp.com.br": "https://www.brastemp.com.br/search?q={q}",
    "https://www.consul.com.br": "https://www.consul.com.br/s?q={q}",
    "https://www.samsung.com/br": "https://www.samsung.com/br/search/?searchvalue={q}",
    "https://www.lg.com/br": "https://www.lg.com/br/search?search={q}",
    # Electrolux: toda URL com query bateu 503 nos meus testes (só a home
    # responde 200) — sem padrão confirmado, fica de fora do dict de
    # propósito e cai no fallback de homepage abaixo em vez de arriscar
    # outra URL inventada.
}

# "Loja Oficial da Marca" no seed sempre apontava pro site da Electrolux
# (bug pré-existente) mesmo pra produto Brastemp/Consul/Samsung/LG — cada
# marca tem seu próprio site oficial de verdade no Brasil.
_SITE_OFICIAL_POR_MARCA = {
    "Electrolux": "https://www.electrolux.com.br",
    "Brastemp": "https://www.brastemp.com.br",
    "Consul": "https://www.consul.com.br",
    "Samsung": "https://www.samsung.com/br",
    "LG": "https://www.lg.com/br",
}


def url_busca_de_apoio(loja, produto) -> str | None:
    """Quando a oferta não tem `Price.url` confirmado (loja sem dado real
    extraído ainda — hoje só a Bemol tem, ver seed_data.py), manda pra
    busca de verdade DENTRO do site da própria loja (não uma busca no
    Google) — pedido explícito do usuário, que quer "entrar no site" e
    não ficar só numa pesquisa externa.

    Site sem padrão de busca confirmado (Electrolux, ou qualquer domínio
    fora de `_PADROES_BUSCA_POR_SITE`) cai na HOMEPAGE do site — ainda
    assim entra no site de verdade, só sem a query pronta; melhor que
    arriscar inventar uma URL de busca que talvez nem exista (foi
    exatamente esse erro que gerou o bug anterior: um link sintético que
    nunca existiu).

    `None` só quando a própria loja não tem site nenhum (Eletro Norte,
    loja física fictícia sem `website_url`)."""
    base = loja.website_url
    if loja.name == "Loja Oficial da Marca":
        base = _SITE_OFICIAL_POR_MARCA.get(produto.brand, base)
    if not base:
        return None

    padrao = _PADROES_BUSCA_POR_SITE.get(base)
    if padrao:
        return padrao.format(q=quote_plus(produto.name))
    return base


# Fase 1 é só geladeiras — mapeamento de specs fixo pra essa categoria.
# Categoria nova (fogão, lava-louças...) vai precisar do próprio mapeamento
# quando ganhar produtos de verdade (specs de fogão não tem "capacidade em
# litros", por exemplo).
def formatar_especificacoes(specs: dict) -> list[tuple[str, str]]:
    linhas = []
    if "capacidade_litros" in specs:
        linhas.append(("Capacidade", f"{specs['capacidade_litros']} litros"))
    if "frost_free" in specs:
        linhas.append(("Frost Free", "Sim" if specs["frost_free"] else "Não"))
    if "cor" in specs:
        linhas.append(("Cor", specs["cor"]))
    if "voltagem" in specs:
        linhas.append(("Voltagem", specs["voltagem"]))
    if "dimensoes_cm" in specs:
        linhas.append(("Dimensões (A x L x P)", f"{specs['dimensoes_cm']} cm"))
    if "consumo_kwh_mes" in specs:
        linhas.append(("Consumo médio", f"{specs['consumo_kwh_mes']} kWh/mês"))
    return linhas
