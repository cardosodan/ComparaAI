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
# isso é o `Price.url`, só existe de verdade pra Bemol hoje).
#
# HISTÓRICO IMPORTANTE (não repetir o erro): a 1ª versão desta tabela
# tinha uma entrada por loja, "confirmada" só por status HTTP 200 via
# curl. Isso se provou insuficiente de DUAS formas diferentes, uma
# reportada pelo usuário e outra achada ao investigar a primeira:
# 1. Casas Bahia (`/s?q=`, chute por ela usar a mesma plataforma VTEX de
#    Bemol/Brastemp/Consul): usuário mandou print — página 404 REAL da
#    Casas Bahia. O chute estava errado, 200 nunca veio, era bloqueio de
#    bot disfarçado de sucesso.
# 2. Brastemp (`/search?q=`): sim, retornou 200 — mas o CONTEÚDO da
#    página (conferido via WebFetch depois do susto da Casas Bahia) é
#    "não encontramos nenhum resultado para 'search'" — ou seja, o nome
#    do parâmetro (`q`) está errado, a página carrega mas a busca em si
#    nunca roda. Status 200 não é prova de busca funcionando, só de que
#    o servidor respondeu alguma coisa.
# Diante disso, só entra aqui o que tem confiança REAL (não só status
# code): o formato de busca do Amazon (`/s?k=`) é um padrão global,
# extremamente estável, usado há mais de uma década em todos os países —
# não é um chute novo pra esse projeto. Todo o resto (Carrefour, Brastemp,
# Consul, Samsung, LG, Electrolux) fica de fora de propósito e cai no
# fallback de HOMEPAGE em `url_busca_de_apoio` — menos preciso, mas nunca
# mais um link inventado que erra o parâmetro ou bate num 404 real.
_PADROES_BUSCA_POR_SITE = {
    "https://www.amazon.com.br": "https://www.amazon.com.br/s?k={q}",
}


def url_busca_de_apoio(loja, produto) -> str | None:
    """Quando a oferta não tem `Price.url` confirmado pra esse produto
    específico (ver seed_data.py — cada loja tem dado real só nos
    produtos onde já foi verificado), manda pra busca de verdade DENTRO
    do site da própria loja (não uma busca no Google) — pedido explícito
    do usuário, que quer "entrar no site" e não ficar só numa pesquisa
    externa. Desde que cada marca (Electrolux/Brastemp/Consul/Samsung/LG)
    virou um `Store` próprio com o `website_url` já correto (em vez de um
    "Loja Oficial da Marca" genérico com lookup por marca), essa função
    não precisa mais adivinhar qual site usar — é sempre `loja.website_url`.

    Site sem padrão de busca confirmado (qualquer domínio fora de
    `_PADROES_BUSCA_POR_SITE`) cai na HOMEPAGE do site — ainda assim entra
    no site de verdade, só sem a query pronta; melhor que arriscar
    inventar uma URL de busca que talvez nem exista (foi exatamente esse
    erro que gerou o bug anterior: um link sintético que nunca existiu).

    `None` só quando a própria loja não tem site nenhum (Eletro Norte,
    loja física fictícia sem `website_url`)."""
    if not loja.website_url:
        return None

    padrao = _PADROES_BUSCA_POR_SITE.get(loja.website_url)
    if padrao:
        return padrao.format(q=quote_plus(produto.name))
    return loja.website_url


# Mapeamento de specs por CHAVE (não por categoria) — cada categoria nova
# (Fogões, Lava-louças...) só precisa acrescentar as chaves que usa de
# verdade aqui; chaves que uma categoria não tem simplesmente não aparecem
# (`if "chave" in specs`), então Geladeiras/Micro-ondas convivem na mesma
# função sem conflito.
def formatar_especificacoes(specs: dict) -> list[tuple[str, str]]:
    linhas = []
    if "capacidade_litros" in specs:
        linhas.append(("Capacidade", f"{specs['capacidade_litros']} litros"))
    if "tipo" in specs:
        linhas.append(("Tipo", specs["tipo"]))
    if "frost_free" in specs:
        linhas.append(("Frost Free", "Sim" if specs["frost_free"] else "Não"))
    if "grill" in specs:
        linhas.append(("Grill", "Sim" if specs["grill"] else "Não"))
    if "potencia_watts" in specs:
        linhas.append(("Potência", f"{specs['potencia_watts']} W"))
    if "cor" in specs:
        linhas.append(("Cor", specs["cor"]))
    if "voltagem" in specs:
        linhas.append(("Voltagem", specs["voltagem"]))
    if "dimensoes_cm" in specs:
        linhas.append(("Dimensões (A x L x P)", f"{specs['dimensoes_cm']} cm"))
    if "consumo_kwh_mes" in specs:
        linhas.append(("Consumo médio", f"{specs['consumo_kwh_mes']} kWh/mês"))
    return linhas
