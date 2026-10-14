#!/usr/bin/env python3
"""radar_temas: acha o tema corporativo do momento antes dos outros (perfil Fred).

Lê o RSS de tendências do Google Trends Brasil e o RSS do Google News com buscas sobre
trabalho e mundo corporativo, filtra o que é tema de escritório, agrupa notícias do mesmo
assunto e dá uma nota de "potencial de sátira" (0 a 100) com a justificativa.
Saída: digest-AAAA-MM-DD.md com os N melhores temas (tema, fato, fonte, data e ângulo).

Não escreve roteiro nem piada. Entrega só tema, fato e ângulo.

Uso:
  python radar_temas.py                      # Trends + Google News, últimas 48 h, top 15
  python radar_temas.py --top 20 --horas 72
  python radar_temas.py --entrada coleta.json --agora 2026-10-14T12:00-03:00
  python radar_temas.py --salvar-bruto bruto.json

Formato de --entrada: lista de objetos com titulo, link, fonte, data (ISO 8601 ou vazio),
origem e, opcionalmente, resumo, trafego (Trends), tema (força o agrupamento) e angulo
(ângulo editorial que substitui o modelo automático).
"""
from __future__ import annotations

import argparse
import datetime as dt
import email.utils
import json
import math
import re
import sys
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

import requests

TRENDS_RSS = "https://trends.google.com/trending/rss?geo=BR"
NEWS_RSS = "https://news.google.com/rss/search?q={q}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
UA = {"User-Agent": "Mozilla/5.0 (radar-temas; leitura de RSS publico)"}

# Buscas no Google News. O sufixo "when:Nd" é aplicado pelo script.
BUSCAS = [
    '"home office" OR "trabalho presencial" OR "volta ao escritório"',
    'layoff OR "demissão em massa" OR "corte de vagas" OR "demite funcionários"',
    '"escala 6x1" OR "jornada de trabalho" OR "semana de quatro dias"',
    '"Faria Lima"',
    'bancários OR "fechamento de agências" OR fintech funcionários',
    '"inteligência artificial" emprego OR escritório OR demissões',
    'PLR OR bônus OR "reajuste salarial" OR "participação nos lucros"',
    '"saúde mental" trabalho OR burnout OR "NR-1"',
    'chefe OR liderança OR "recursos humanos" pesquisa trabalhadores',
    'reunião OR produtividade OR monitoramento funcionários empresa',
    'Nubank OR Itaú OR Bradesco OR Santander OR "Banco do Brasil" funcionários',
    'CLT OR pejotização OR "contratação PJ"',
    'LinkedIn OR "geração Z" trabalho OR carreira',
]

# Léxico por categoria (texto sem acento, minúsculo). Peso = quanto o tema é "de escritório"
# e quanto o público se reconhece nele.
CATEGORIAS: dict[str, tuple[float, list[str]]] = {
    "home office e presencial": (1.0, [r"home office", r"trabalho remoto", r"\bremot[oa]s?\b", r"presencia",
                                       r"hibrid", r"volta ao escritorio", r"retorno ao escritorio"]),
    "chefe e liderança": (1.0, [r"\bchefes?\b", r"lideranc", r"\bgestor", r"\bceos?\b", r"\bdiretor",
                                r"superintendente", r"\blider"]),
    "reunião e rotina de escritório": (1.0, [r"reunia", r"reunio", r"\bcall\b", r"\bteams\b", r"\bslack\b", r"planilha",
                                             r"escritorio", r"coworking", r"cracha", r"catraca", r"open space"]),
    "RH, benefícios e salário": (0.9, [r"\brh\b", r"recursos humanos", r"beneficio", r"vale.refeicao",
                                       r"vale.alimentacao", r"\bplr\b", r"participacao nos lucros", r"\bbonus",
                                       r"salari", r"reajuste", r"decimo terceiro", r"\bferias\b"]),
    "produtividade e vigilância": (0.9, [r"produtividade", r"monitora", r"vigilanc", r"webcam", r"\bcameras?\b",
                                         r"rastrea", r"bater ponto", r"ponto eletronico", r"sobrecarga"]),
    "layoff e demissões": (0.9, [r"layoff", r"demiss", r"demit", r"corte de (vagas|funcionarios|empregos|postos)",
                                 r"cortam? .{0,20}(vagas|postos)", r"reestrutura", r"enxugamento", r"desligament",
                                 r"\bpdv\b"]),
    "jornada e CLT": (0.8, [r"6x1", r"jornada", r"\bclt\b", r"carteira assinada", r"hora extra", r"banco de horas",
                            r"semana de (4|quatro) dias", r"pejotiza", r"\bmeis?\b", r"contratacao (pj|por hora)"]),
    "IA no trabalho": (0.8, [r"inteligencia artificial", r"\bias?\b", r"chatgpt", r"gemini", r"copilot",
                             r"agentes? de ia", r"automaca", r"\brobo"]),
    "Faria Lima e mercado": (0.8, [r"faria lima", r"ibovespa", r"\bbolsa\b", r"\bdolar", r"\bjuros\b", r"\bselic\b",
                                   r"mercado financeiro", r"investidor", r"gestora", r"\bbanker"]),
    "saúde mental": (0.7, [r"saude mental", r"burnout", r"psicossocia", r"\bnr-?1\b", r"ansiedade",
                           r"transtornos? mentais?", r"afastament"]),
    "bancos e fintechs": (0.7, [r"\bbancos?\b", r"bancari", r"fintech", r"nubank", r"\bitau\b", r"bradesco",
                                r"santander", r"banco do brasil", r"caixa economica", r"\bbtg\b", r"picpay",
                                r"\bpix\b", r"agencias", r"fenaban"]),
    "carreira e LinkedIn": (0.7, [r"linkedin", r"carreira", r"curriculo", r"entrevista de emprego", r"estagi",
                                  r"trainee", r"geracao z", r"promocao"]),
    "mercado de trabalho": (0.4, [r"caged", r"desemprego", r"emprego formal", r"\bvagas\b", r"mercado de trabalho"]),
}

# Sinais de contradição ou absurdo, que é onde mora o ângulo de sátira.
CONTRADICOES: list[tuple[str, str]] = [
    (r"lucr\w*.{0,80}(demit|demiss|corte de|cortam|fecham? \d)|(demit|demiss|corte de|cortam|fecham? \d)\w*.{0,80}lucr",
     "lucro e corte na mesma notícia"),
    (r"assedio|ameaca|retaliac|coag", "chefe usando o cargo contra o time"),
    (r"obrigat|\bexige|proib|endurece|passa a exigir", "regra imposta de cima"),
    (r"webcam|\bcameras?\b|monitora|vigilanc|rastrea|\bfotos\b", "vigilância vendida como produtividade"),
    (r"prometia|mas entreg|na pratica|apesar d", "promessa contra realidade"),
    (r"\bplr\b|\bbonus|participacao nos lucros", "dinheiro na conta contra discurso de crise"),
    (r"fora do ar|instabilidade|\bcaiu\b|pane", "ferramenta caiu e o trabalho parou"),
    (r"cultura|proposito|engajamento|bem.estar|felicidade|familia", "jargão de RH"),
    (r"\bpec\b|senado|camara|votaca|projeto de lei|\blei\b|portaria|norma", "lei ou governo mexendo na rotina do escritório"),
    (r"(recua|dispara|despenca|sobe|cai|recorde).{0,40}(pesquisa|eleic|turno)|(pesquisa|eleic|turno).{0,40}(recua|dispara|despenca|sobe|cai|recorde)",
     "mercado que muda de humor a cada pesquisa"),
    (r"\d+ ?%|\bpesquisa\b|levantamento", "número de pesquisa que todo mundo reconhece"),
]

RUIDO = r"futebol|campeonato|brasileirao|\bgol\b|novela|\bbbb\b|reality|cantor|atriz|\bator\b|assassin|homicid|" \
        r"previsao do tempo|loteria|mega.sena|horoscopo|\bufc\b|formula 1"

ANGULOS = {
    "home office e presencial": "O contraste entre o comunicado sobre flexibilidade e a regra de crachá na catraca.",
    "chefe e liderança": "O chefe que some quando aparece o problema e volta quando chega o resultado.",
    "reunião e rotina de escritório": "A reunião que poderia ser um e-mail e o e-mail que vira três reuniões.",
    "RH, benefícios e salário": "A distância entre a campanha de valorização do RH e o que chega no contracheque.",
    "produtividade e vigilância": "Medir produtividade com ferramenta que só mede quem parece ocupado.",
    "layoff e demissões": "A linguagem corporativa que transforma corte de gente em jornada de eficiência.",
    "jornada e CLT": "Brasília discute a jornada enquanto o escritório já trabalha no WhatsApp depois do expediente.",
    "IA no trabalho": "A IA que ia liberar tempo e virou mais uma coisa para revisar.",
    "Faria Lima e mercado": "A Faria Lima que muda de convicção a cada pesquisa, sempre com a mesma certeza.",
    "saúde mental": "A empresa que trata saúde mental com palestra e prazo para ontem.",
    "bancos e fintechs": "O banco que fecha agência e diz que está mais perto de você.",
    "carreira e LinkedIn": "O post de LinkedIn que transforma qualquer derrota em lição de liderança.",
    "mercado de trabalho": "O número oficial que ninguém no escritório reconhece na própria vida.",
}

STOP = set("""a o os as um uma de do da dos das em no na nos nas por para com sem sobre que se e ou mais menos
como ate apos entre ao aos pelo pela pelos pelas seu sua seus suas ja nao sim tem ter ser foi sao esta este essa
isso hoje diz dizem veja entenda apos anos ano novo nova novos novas brasil brasileiros brasileiro""".split())


def sem_acento(s: str) -> str:
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()


# --------------------------------------------------------------------------- coleta

@dataclass
class Item:
    titulo: str
    link: str
    fonte: str
    data: dt.datetime | None
    origem: str
    resumo: str = ""
    trafego: int = 0
    tema: str | None = None
    angulo: str | None = None
    precisao: str = "dia"          # "dia" ou "mes" (quando só o mês é conhecido)
    tipo_data: str = "publicação"  # ou "fato" (data do acontecimento, não da matéria)
    evento: dt.datetime | None = None  # próximo acontecimento marcado (votação, prazo)

    @property
    def texto(self) -> str:
        return sem_acento(f"{self.titulo} {self.resumo}")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _filhos(el: ET.Element, nome: str) -> list[ET.Element]:
    return [c for c in el if _local(c.tag) == nome]


def _texto(el: ET.Element, nome: str) -> str:
    f = _filhos(el, nome)
    return (f[0].text or "").strip() if f else ""


def _data_rfc822(s: str) -> dt.datetime | None:
    try:
        return email.utils.parsedate_to_datetime(s) if s else None
    except (TypeError, ValueError):
        return None


def _trafego(s: str) -> int:
    m = re.search(r"([\d.,]+)\s*([kKmM]?)", s or "")
    if not m:
        return 0
    n = float(m.group(1).replace(".", "").replace(",", "."))
    return int(n * {"k": 1e3, "m": 1e6}.get(m.group(2).lower(), 1))


def parse_trends(xml: bytes | str) -> list[Item]:
    """RSS do Google Trends: cada termo vira um item; as notícias ligadas vão no resumo."""
    raiz = ET.fromstring(xml)
    out = []
    for it in raiz.iter():
        if _local(it.tag) != "item":
            continue
        noticias = _filhos(it, "news_item")
        titulos = [_texto(n, "news_item_title") for n in noticias]
        primeira = noticias[0] if noticias else None
        out.append(Item(
            titulo=_texto(it, "title"),
            link=_texto(primeira, "news_item_url") if primeira is not None else _texto(it, "link"),
            fonte=("Google Trends · " + _texto(primeira, "news_item_source")) if primeira is not None else "Google Trends",
            data=_data_rfc822(_texto(it, "pubDate")),
            origem="trends",
            resumo=" | ".join(t for t in titulos if t),
            trafego=_trafego(_texto(it, "approx_traffic")),
        ))
    return out


def parse_news(xml: bytes | str, busca: str = "") -> list[Item]:
    """RSS do Google News: título vem como 'Manchete - Veículo'."""
    raiz = ET.fromstring(xml)
    out = []
    for it in raiz.iter():
        if _local(it.tag) != "item":
            continue
        titulo = _texto(it, "title")
        fonte = _texto(it, "source")
        if fonte and titulo.endswith(f" - {fonte}"):
            titulo = titulo[: -len(fonte) - 3]
        out.append(Item(titulo=titulo, link=_texto(it, "link"), fonte=fonte or "Google News",
                        data=_data_rfc822(_texto(it, "pubDate")), origem=f"news:{busca}"))
    return out


def _erro(e: Exception) -> str:
    t = str(e)
    return "bloqueado pelo proxy de rede (HTTP 403)" if "403" in t else f"{type(e).__name__}: {t[:120]}"


def coletar(horas: int = 48, usar_trends: bool = True, buscas: list[str] = BUSCAS) -> tuple[list[Item], list[str]]:
    itens, erros = [], []
    s = requests.Session()
    s.headers.update(UA)
    if usar_trends:
        try:
            r = s.get(TRENDS_RSS, timeout=30)
            r.raise_for_status()
            itens += parse_trends(r.content)
        except Exception as e:  # noqa: BLE001
            erros.append(f"Google Trends ({TRENDS_RSS}): {_erro(e)}")
    dias = max(1, math.ceil(horas / 24))
    for b in buscas:
        url = NEWS_RSS.format(q=urllib.parse.quote(f"{b} when:{dias}d"))
        try:
            r = s.get(url, timeout=30)
            r.raise_for_status()
            itens += parse_news(r.content, b)
        except Exception as e:  # noqa: BLE001
            erros.append(f"Google News [{b}]: {_erro(e)}")
    return itens, erros


def _data_json(s: str | None) -> tuple[dt.datetime | None, str]:
    """Aceita ISO 8601 completo ou só 'AAAA-MM' (sem inventar o dia)."""
    if not s:
        return None, "dia"
    if re.fullmatch(r"\d{4}-\d{2}", s):
        return dt.datetime.fromisoformat(f"{s}-01T00:00:00-03:00"), "mes"
    d = dt.datetime.fromisoformat(s)
    return (d if d.tzinfo else d.replace(tzinfo=dt.timezone(dt.timedelta(hours=-3)))), "dia"


def carregar_json(caminho: Path) -> list[Item]:
    out = []
    for d in json.loads(caminho.read_text(encoding="utf-8")):
        data, precisao = _data_json(d.get("data"))
        evento, _ = _data_json(d.get("evento"))
        out.append(Item(titulo=d["titulo"], link=d.get("link", ""), fonte=d.get("fonte", ""), data=data,
                        origem=d.get("origem", "manual"), resumo=d.get("resumo", ""),
                        trafego=int(d.get("trafego") or 0), tema=d.get("tema"), angulo=d.get("angulo"),
                        precisao=precisao, tipo_data=d.get("tipo_data", "publicação"), evento=evento))
    return out


# --------------------------------------------------------------------------- filtro, grupos, nota

def categorias(texto: str) -> dict[str, int]:
    achou = {}
    for nome, (_, padroes) in CATEGORIAS.items():
        n = sum(1 for p in padroes if re.search(p, texto))
        if n:
            achou[nome] = n
    return achou


def eh_tema_de_escritorio(item: Item) -> bool:
    cats = categorias(item.texto)
    nucleo = {k for k in cats if CATEGORIAS[k][0] >= 0.7}
    if not nucleo:
        return False
    if re.search(RUIDO, item.texto) and sum(cats.values()) < 2:
        return False
    return True


def _tokens(texto: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]{4,}", texto) if w not in STOP}


@dataclass
class Tema:
    itens: list[Item] = field(default_factory=list)
    chave: str | None = None

    @property
    def tokens(self) -> set[str]:
        return set().union(*(_tokens(i.texto) for i in self.itens)) if self.itens else set()

    @property
    def texto(self) -> str:
        return " ".join(i.texto for i in self.itens)

    @property
    def principal(self) -> Item:
        return sorted(self.itens, key=lambda i: (i.data is not None, i.data or dt.datetime.min.replace(tzinfo=dt.timezone.utc)),
                      reverse=True)[0]

    @property
    def nome(self) -> str:
        return self.chave or self.principal.titulo


def agrupar(itens: list[Item], limiar: float = 0.3) -> list[Tema]:
    temas: list[Tema] = []
    por_chave: dict[str, Tema] = {}
    vistos: set[str] = set()
    for it in itens:
        k = sem_acento(it.titulo)
        if k in vistos:
            continue
        vistos.add(k)
        if it.tema:
            t = por_chave.setdefault(it.tema, Tema(chave=it.tema))
            if t not in temas:
                temas.append(t)
            t.itens.append(it)
            continue
        tk = _tokens(it.texto)
        melhor, sim = None, 0.0
        for t in temas:
            if t.chave:
                continue
            tt = t.tokens
            j = len(tk & tt) / max(1, len(tk | tt))
            if j > sim:
                melhor, sim = t, j
        if melhor is not None and sim >= limiar:
            melhor.itens.append(it)
        else:
            temas.append(Tema(itens=[it]))
    return temas


def pontuar(tema: Tema, agora: dt.datetime) -> tuple[float, list[str], str]:
    """Nota de potencial de sátira (0 a 100), motivos e categoria principal."""
    texto = tema.texto
    cats = categorias(texto)
    if not cats:
        return 0.0, ["sem categoria de escritório"], ""
    principal = max(cats, key=lambda c: (CATEGORIAS[c][0], cats[c]))
    wmax = CATEGORIAS[principal][0]
    relevancia = 30 * min(1.0, (wmax + 0.2 * (len(cats) - 1)) / 1.2)
    identificacao = 20 * wmax
    sinais = [rot for rx, rot in CONTRADICOES if re.search(rx, texto)]
    contradicao = min(20, 7 * len(sinais))
    fontes = {i.fonte.split(" · ")[-1] for i in tema.itens if i.fonte}
    forca = {0: 0, 1: 4, 2: 8, 3: 11}.get(len(fontes), 14)
    trends = [i for i in tema.itens if i.origem == "trends"]
    if trends:
        forca += 3 + min(3, math.log10(max(1, max(i.trafego for i in trends))) / 2)
    forca = min(20, forca)
    datas = [i.data for i in tema.itens if i.data]
    if datas:
        horas = (agora - max(datas)).total_seconds() / 3600
        frescor = 10 if horas <= 24 else 8 if horas <= 48 else 6 if horas <= 72 else 4 if horas <= 168 else 2 if horas <= 720 else 1
        idade = f"mais recente há {horas:.0f} h" if horas < 72 else f"mais recente há {horas / 24:.0f} dias"
    else:
        frescor, idade = 1, "data não informada"
    eventos = [i.evento for i in tema.itens if i.evento and agora <= i.evento <= agora + dt.timedelta(days=7)]
    if eventos:
        frescor, idade = 10, f"{idade}; acontecimento marcado para {min(eventos):%d/%m}"
    nota = round(relevancia + identificacao + contradicao + forca + frescor, 1)
    motivos = [f"categorias: {', '.join(sorted(cats, key=lambda c: -CATEGORIAS[c][0]))}"]
    if sinais:
        motivos.append("contradição: " + "; ".join(sinais))
    motivos.append(f"{len(fontes)} fonte(s)" + (f", no Google Trends ({max(i.trafego for i in trends)}+ buscas)" if trends else ""))
    motivos.append(idade)
    return nota, motivos, principal


# --------------------------------------------------------------------------- digest

def _fmt_data(d: dt.datetime | None, item: "Item | None" = None) -> str:
    if not d:
        return "data não verificada"
    txt = d.strftime("%m/%Y") + ", dia não verificado" if item is not None and item.precisao == "mes" else d.strftime("%d/%m/%Y")
    if item is not None and item.tipo_data == "fato":
        txt += ", data do fato"
    return txt


def digest(temas: list[Tema], agora: dt.datetime, top: int = 15, erros: list[str] | None = None,
           nota_coleta: str = "") -> str:
    linhas = []
    pont = []
    for t in temas:
        nota, motivos, cat = pontuar(t, agora)
        if nota > 0:
            pont.append((nota, t, motivos, cat))
    pont.sort(key=lambda x: -x[0])
    pont = pont[:top]
    linhas.append(f"# Radar de temas · {agora:%Y-%m-%d}\n")
    linhas.append(f"Gerado por `radar_temas.py` em {agora:%d/%m/%Y %H:%M}. Nota = potencial de sátira (0 a 100): "
                  "relevância corporativa (30), identificação do público (20), contradição ou absurdo (20), "
                  "força nas fontes (20) e frescor (10). Só tema, fato e ângulo: sem roteiro e sem piada.\n")
    if nota_coleta:
        linhas.append(nota_coleta.strip() + "\n")
    if erros:
        linhas.append("**Fontes que falharam nesta rodada:**\n")
        linhas += [f"- {e}" for e in erros]
        linhas.append("")
    linhas.append("| # | Tema | Nota | Data do fato |")
    linhas.append("|---|---|---|---|")
    for n, (nota, t, _, _) in enumerate(pont, 1):
        linhas.append(f"| {n} | {t.nome} | {nota:.0f} | {_fmt_data(t.principal.data, t.principal)} |")
    linhas.append("")
    for n, (nota, t, motivos, cat) in enumerate(pont, 1):
        p = t.principal
        angulo = next((i.angulo for i in t.itens if i.angulo), None) or ANGULOS.get(cat, "")
        linhas.append(f"## {n}. {t.nome} · nota {nota:.0f}\n")
        linhas.append(f"- **Fato:** {p.titulo} ({p.fonte}, {_fmt_data(p.data, p)}). {p.resumo}".rstrip())
        linhas.append(f"- **Fonte:** {p.link}")
        outras = [i for i in t.itens if i is not p]
        if outras:
            linhas.append("- **Outras fontes:** " + "; ".join(f"{i.fonte} ({_fmt_data(i.data, i)}) {i.link}" for i in outras))
        linhas.append(f"- **Ângulo:** {angulo}")
        linhas.append(f"- **Por que a nota:** {'; '.join(motivos)}.\n")
    return "\n".join(linhas)


def main(argv: list[str] | None = None) -> Path:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--horas", type=int, default=48, help="janela das buscas no Google News")
    ap.add_argument("--sem-trends", action="store_true")
    ap.add_argument("--entrada", type=Path, help="JSON com itens já coletados (pula o RSS)")
    ap.add_argument("--agora", help="data/hora de referência ISO 8601 (padrão: agora)")
    ap.add_argument("--saida", type=Path, default=Path("."))
    ap.add_argument("--salvar-bruto", type=Path)
    ap.add_argument("--nota-coleta", default="", help="texto livre sobre a coleta, vai no topo do digest")
    a = ap.parse_args(argv)

    agora = dt.datetime.fromisoformat(a.agora) if a.agora else dt.datetime.now().astimezone()
    if a.entrada:
        itens, erros = carregar_json(a.entrada), []
    else:
        itens, erros = coletar(a.horas, not a.sem_trends)
    if a.salvar_bruto:
        a.salvar_bruto.write_text(json.dumps([{**i.__dict__, "data": i.data.isoformat() if i.data else None}
                                              for i in itens], ensure_ascii=False, indent=1), encoding="utf-8")
    filtrados = [i for i in itens if eh_tema_de_escritorio(i)]
    temas = agrupar(filtrados)
    md = digest(temas, agora, a.top, erros, a.nota_coleta)
    a.saida.mkdir(parents=True, exist_ok=True)
    destino = a.saida / f"digest-{agora:%Y-%m-%d}.md"
    destino.write_text(md, encoding="utf-8")
    print(f"{len(itens)} itens, {len(filtrados)} de escritório, {len(temas)} temas -> {destino}")
    for e in erros:
        print("AVISO:", e, file=sys.stderr)
    return destino


if __name__ == "__main__":
    main()
