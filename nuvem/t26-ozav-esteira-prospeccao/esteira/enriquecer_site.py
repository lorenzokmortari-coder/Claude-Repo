#!/usr/bin/env python3
"""
Ozav · enriquecer site da lista

Lê o top1000.csv da lista quente CNPJ (tarefas 1 e 5) e, para cada empresa com domínio de
e-mail próprio (marca_email = "próprio"), visita o site: a home e até 3 páginas internas
óbvias (contato, sobre, carreiras, equipe). Extrai SEM IA, só com regras fixas:
  - e-mails de função publicados no site (contato@, comercial@, financeiro@...);
  - telefones (validados pela biblioteca phonenumbers), separando Brasil e exterior;
  - link da página da EMPRESA no LinkedIn (/company/, /showcase/, /school/);
  - sinais no texto: importa, exporta, comércio exterior, matriz no exterior, escritório em X,
    "global", clientes/fornecedores no exterior, menção a câmbio/moeda e vagas de
    comex/finanças/tesouraria (só na página de carreiras);
  - idioma do site.

Motores (o texto sai sempre do HTML, pelo selectolax):
  - crawl4ai: Crawl4AI como biblioteca; renderiza a página num Chromium (pega site feito em
    JavaScript). Medido em 14/10/2026: pico de ~1,2 GB de RAM somando Python e Chrome, então
    cabe em 4 GB. É o padrão quando o pacote está instalado.
  - leve: requests, sem navegador. É o padrão quando o Crawl4AI não está instalado.

Regras de coleta, iguais nos dois motores: lê e respeita o robots.txt de cada host (RFC 9309:
4xx = pode tudo; 5xx ou sem resposta = não pode nada; vale também o Crawl-delay, até 30 s),
no máximo 1 requisição por segundo por domínio (o robots.txt e cada redirecionamento contam),
teto de 4 páginas por site e de 2 MB por página, só HTML.

Privacidade: nada de nome de pessoa física na saída. E-mail só entra se o nome antes do @ for
de função (contato@, financeiro@...); e-mail que pode ser de pessoa (joao.silva@) é descartado
e só contado. Link de perfil pessoal do LinkedIn (/in/) é ignorado. Não guarda HTML nem trecho
do texto: só os termos fixos que dispararam cada sinal e nomes de lugar de uma lista fechada.

Uso:
  pip install requests selectolax phonenumbers            # motor leve
  pip install crawl4ai && crawl4ai-setup                  # opcional: motor crawl4ai
  python enriquecer_site.py saida/2026-10/top1000.csv              # grava ao lado: enriquecido.csv, relatorio.md
  python enriquecer_site.py top1000.csv --saida enriq --limite 20  # teste com 20 empresas
  python enriquecer_site.py top1000.csv --motor leve --workers 8   # 8 domínios em paralelo (cada um a 1 req/s)
  python enriquecer_site.py top1000.csv --motor crawl4ai --cdp-url http://127.0.0.1:9222   # Chrome já aberto
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import datetime as dt
import json
import re
import sys
import threading
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import phonenumbers
import requests
from selectolax.lexbor import LexborHTMLParser as HTMLParser

UA_TOKEN = "OzavSiteEnricher"
UA = f"Mozilla/5.0 (compatible; {UA_TOKEN}/1.0; leitura de site institucional publico)"
INTERVALO_MIN_S = 1.0          # por domínio
CRAWL_DELAY_MAX_S = 30.0       # Crawl-delay acima disso é limitado a 30 s
MAX_PAGINAS_SITE = 4           # home + 3 internas
MAX_BYTES_PAGINA = 2_000_000
MAX_REDIRECIONAMENTOS = 5
TIMEOUT = (6, 20)
MAX_ITENS = 6                  # por coluna de lista (e-mails, telefones...)
REDIRECIONA = {301, 302, 303, 307, 308}

COLUNAS_NOVAS = [
    "status_site", "site", "redireciona_para", "paginas_lidas", "paginas", "motor", "texto_chars",
    "idioma", "lang_html", "hreflangs",
    "emails_funcao", "emails_funcao_outros_dominios", "n_emails_pessoais_descartados",
    "telefones_br", "telefones_exterior", "linkedin_empresa", "plataforma_vagas",
    "sinal_importa", "sinal_exporta", "sinal_comex", "sinal_matriz_exterior", "matriz_em",
    "escritorios", "escritorio_exterior", "sinal_global", "sinal_clientes_exterior", "menciona_cambio",
    "vagas_alvo", "n_sinais", "evidencias", "coletado_em",
]
SINAIS_BINARIOS = ["sinal_importa", "sinal_exporta", "sinal_comex", "sinal_matriz_exterior",
                   "escritorio_exterior", "sinal_global", "sinal_clientes_exterior", "menciona_cambio"]


# --------------------------------------------------------------------------- texto

def sem_acento(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", sem_acento(s).lower()).strip()


def decodificar(corpo: bytes, tipo: str) -> str:
    m = re.search(r"charset=([\w-]+)", tipo or "", re.I) or re.search(rb"""charset=["']?([\w-]+)""", corpo[:4096], re.I)
    cands = []
    if m:
        cands.append(m.group(1).decode() if isinstance(m.group(1), bytes) else m.group(1))
    cands += ["utf-8", "cp1252"]
    for enc in cands:
        try:
            return corpo.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return corpo.decode("utf-8", errors="replace")


def e_html(tipo: str) -> bool:
    t = (tipo or "").lower()
    return not t or "text/html" in t or "application/xhtml" in t


# --------------------------------------------------------------------------- extração de uma página

@dataclass
class Pagina:
    url: str
    categoria: str
    texto: str
    links: list[tuple[str, str]]
    mailtos: list[str]
    tels: list[str]
    lang: str | None
    hreflangs: set[str]


def extrair_html(html: str, url: str, categoria: str = "home") -> Pagina:
    arv = HTMLParser(html)
    raiz = arv.css_first("html")
    lang = (raiz.attributes.get("lang") or "").strip() or None if raiz is not None else None
    hreflangs = {(n.attributes.get("hreflang") or "").strip().lower() for n in arv.css("link[hreflang], a[hreflang]")}
    hreflangs.discard("")
    base = arv.css_first("base[href]")
    url_base = urljoin(url, base.attributes.get("href") or "") if base is not None else url
    links, mailtos, tels = [], [], []
    for a in arv.css("a[href]"):
        href = (a.attributes.get("href") or "").strip()
        baixo = href.lower()
        if baixo.startswith("mailto:"):
            mailtos.append(unquote(href[7:].split("?")[0]))
        elif baixo.startswith("tel:"):
            tels.append(unquote(href[4:]))
        elif baixo.startswith(("http://", "https://", "/")) or not re.match(r"^[a-z][a-z0-9+.-]*:", baixo):
            if baixo.startswith("#") or not baixo:
                continue
            absoluto = urlunsplit(urlsplit(urljoin(url_base, href))._replace(fragment=""))
            links.append((absoluto, re.sub(r"\s+", " ", a.text(separator=" ") or "").strip()))
    # de dentro para fora: um nó aninhado (style dentro de svg) sai antes do nó que o contém
    for no in reversed(arv.css("script, style, noscript, template, svg, iframe")):
        no.decompose()
    corpo = arv.body or arv.css_first("html")
    texto = re.sub(r"\s+", " ", corpo.text(separator=" ") if corpo is not None else "").strip()
    return Pagina(url, categoria, texto, links, mailtos, tels, lang, hreflangs)


# --------------------------------------------------------------------------- e-mails

RX_EMAIL = re.compile(r"(?<![\w.%+-])[a-z0-9][a-z0-9._%+-]{0,63}@(?:[a-z0-9-]+\.)+[a-z]{2,24}(?![\w-])", re.I)
EXT_ARQUIVO = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".avif", ".css", ".js")
FUNCOES = set("""
contato contatos contact contacto contactus faleconosco fale conosco comercial vendas venda sales negocios business
bd parcerias parceria partners partner partnership financeiro financas finance faturamento billing cobranca contas
pagar receber contasapagar contasareceber pagamentos tesouraria treasury fiscal tributario contabilidade contabil
accounting compras purchasing procurement suprimentos rh recursos humanos hr people pessoas recrutamento recruitment
recruiting talentos talent vagas jobs careers carreiras curriculo curriculos cv trabalheconosco sac atendimento cliente
clientes customer customers service servicos suporte support help ajuda helpdesk info informacoes informacao
information hello ola oi hi marketing mkt comunicacao imprensa press media midia juridico legal compliance privacidade
privacy dpo lgpd gdpr encarregado ouvidoria ombudsman comex export exports exportacao import imports importacao
logistica logistics operacoes operations ops ti it tech admin administrativo administracao adm diretoria board
investidores investors ri ir eventos events orcamento orcamentos quote quotes pedidos orders nfe notas notafiscal
fornecedores suppliers qualidade quality engenharia engineering projetos projects recepcao reception secretaria
webmaster newsletter cadastro cadastros expedicao frete fretes cotacao cotacoes international internacional
""".split())
NEUTROS = set("""
br sp rj mg pr sc rs ba pe df go es ce am pa brasil brazil latam la geral central online digital web site no reply
noreply nao responder responda nacional matriz filial sede escritorio office global team time equipe de do da e and
""".split())
PLATAFORMAS_EMAIL_IGNORAR = ("example.com", "exemplo.com", "dominio.com", "seudominio", "email.com", "sentry",
                             "wixpress.com", "onetrust", "cookiebot", "googleusercontent", "w3.org", "schema.org")


def classificar_email(email: str) -> str:
    """'funcao' quando todo pedaço do nome antes do @ é palavra de função ou neutra (e há pelo
    menos uma de função); senão 'pessoal' (pode ter nome de pessoa: é descartado)."""
    local = norm(email.split("@", 1)[0])
    tokens = [re.sub(r"\d+", "", t) for t in re.split(r"[._+\-]+", local)]
    tokens = [t for t in tokens if t]
    if tokens and all(t in FUNCOES or t in NEUTROS for t in tokens) and any(t in FUNCOES for t in tokens):
        return "funcao"
    return "pessoal"


def mesmo_site(host: str, dominio: str) -> bool:
    h = host.lower().split(":")[0].removeprefix("www.")
    d = dominio.lower().split(":")[0].removeprefix("www.")
    return h == d or h.endswith("." + d)


def achar_emails(paginas: list[Pagina], dominios_site: list[str]) -> tuple[list[str], list[str], int]:
    proprios, outros, pessoais = [], [], set()
    for p in paginas:
        for e in p.mailtos + RX_EMAIL.findall(p.texto):
            e = e.strip().strip(".").lower()
            if not RX_EMAIL.fullmatch(e) or e.endswith(EXT_ARQUIVO) or re.search(r"@\dx\b", e):
                continue
            dom = e.split("@", 1)[1]
            if any(x in dom for x in PLATAFORMAS_EMAIL_IGNORAR):
                continue
            if classificar_email(e) != "funcao":
                pessoais.add(e)
                continue
            alvo = proprios if any(mesmo_site(dom, d) for d in dominios_site) else outros
            if e not in alvo:
                alvo.append(e)
    return proprios[:MAX_ITENS], outros[:MAX_ITENS], len(pessoais)


# --------------------------------------------------------------------------- telefones

RX_CNPJ = re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")
RX_CEP = re.compile(r"\b\d{5}-\d{3}\b")


def achar_telefones(paginas: list[Pagina]) -> tuple[list[str], list[str]]:
    numeros = []
    for p in paginas:
        limpo = RX_CEP.sub(" ", RX_CNPJ.sub(" ", p.texto))
        for m in phonenumbers.PhoneNumberMatcher(limpo, "BR", leniency=phonenumbers.Leniency.VALID):
            numeros.append(m.number)
        for t in p.tels:
            try:
                n = phonenumbers.parse(t, "BR")
            except phonenumbers.NumberParseException:
                continue
            if phonenumbers.is_valid_number(n):
                numeros.append(n)
    br, ext = [], []
    for n in numeros:
        txt = phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        alvo = br if n.country_code == 55 else ext
        if txt not in alvo:
            alvo.append(txt)
    return br[:MAX_ITENS], ext[:MAX_ITENS]


# --------------------------------------------------------------------------- LinkedIn e vagas

RX_LINKEDIN = re.compile(r"^https?://(?:[a-z]{2,3}\.)?(?:www\.)?linkedin\.com/(company|showcase|school)/([^/?#\s]+)", re.I)
PLATAFORMAS_VAGAS = {
    "gupy.io": "Gupy", "vagas.com.br": "Vagas.com", "kenoby.com": "Kenoby", "solides.com.br": "Sólides",
    "solides.jobs": "Sólides", "infojobs.com.br": "InfoJobs", "workable.com": "Workable", "lever.co": "Lever",
    "greenhouse.io": "Greenhouse", "recrutei.com.br": "Recrutei", "pandape.com.br": "Pandapé",
    "abler.com.br": "Abler", "breezy.hr": "Breezy", "bamboohr.com": "BambooHR",
    "smartrecruiters.com": "SmartRecruiters", "myworkdayjobs.com": "Workday", "trampos.co": "Trampos",
    "99jobs.com": "99jobs", "catho.com.br": "Catho", "indeed.com": "Indeed", "glassdoor.com": "Glassdoor",
}


def achar_linkedin(paginas: list[Pagina]) -> list[str]:
    achados = []
    for p in paginas:
        for url, _ in p.links:
            m = RX_LINKEDIN.match(url)
            if m:
                norm_url = f"https://www.linkedin.com/{m.group(1).lower()}/{m.group(2).strip('/')}/"
                if norm_url not in achados:
                    achados.append(norm_url)
    return achados[:3]


def achar_plataformas(paginas: list[Pagina]) -> list[str]:
    achadas = []
    for p in paginas:
        for url, _ in p.links:
            host = urlsplit(url).netloc.lower()
            caminho = urlsplit(url).path.lower()
            if host.endswith("linkedin.com") and caminho.startswith("/jobs"):
                nome = "LinkedIn Vagas"
            else:
                nome = next((v for k, v in PLATAFORMAS_VAGAS.items() if host == k or host.endswith("." + k)), None)
            if nome and nome not in achadas:
                achadas.append(nome)
    return achadas


CARGO = (r"(?:analista|assistente|auxiliar|coordenador|coordenadora|gerente|especialista|supervisor|supervisora|"
         r"estagiario|estagiaria|estagio|trainee|diretor|diretora|head|lider|consultor|consultora|comprador|compradora|"
         r"analyst|manager|specialist|coordinator|director|intern|associate|lead)")
AREA = (r"(?:comercio exterior|comex|importacao|exportacao|importacoes|exportacoes|cambio|tesouraria|treasury|"
        r"financeiro|financeira|financas|finance|financial|fp&a|contas a pagar|contas a receber|accounts payable|"
        r"controladoria|controller|fiscal|tributario|trade compliance|logistica internacional|international logistics|"
        r"supply chain|compras internacionais|international purchasing|procurement)")
RX_VAGA = re.compile(rf"\b{CARGO}(?:\(a\)|/a|\(o\)|/o)?(?!\w)(?:\s+(?:de|do|da|of|em|in|pleno|plena|senior|junior|sr|jr|pl|i{{1,3}}|[123]|-))*\s+{AREA}\b"
                     rf"|\b(?:finance|financial|treasury|trade compliance|import|export|fp&a|accounts payable|tax)\s+"
                     rf"(?:analyst|manager|specialist|coordinator|director|intern|associate|lead)\b")


# --------------------------------------------------------------------------- sinais no texto

NAO_COMERCIO = r"(?! (?:de |dos |das |do |da )?(?:dados|relatorios?|arquivos?|planilhas?|xml|pdf|csv|excel|notas|contatos|nfe|extratos?))"
SINAIS = {
    "sinal_importa": rf"\bimportac(?:ao|oes){NAO_COMERCIO}\b|\bimportador(?:a|es|as)?\b|\bimportamos\b|\b(?:produtos|itens|materiais|equipamentos) importad(?:o|a)s\b|\bimporters?\b|\bimporting goods\b|\bimportacion(?:es)?\b|\bimportador(?:a|es)?\b",
    "sinal_exporta": rf"\bexportac(?:ao|oes){NAO_COMERCIO}\b|\bexportador(?:a|es|as)?\b|\bexportamos\b|\bexporters?\b|\bwe export\b|\bexporting to\b|\bexportacion(?:es)?\b",
    "sinal_comex": r"\bcomercio exterior\b|\bcomex\b|\bforeign trade\b|\bcomercio internacional\b|\binternational trade\b|\bdespacho aduaneiro\b|\bdesembaraco aduaneiro\b|\bdrawback\b|\bincoterms?\b|\bsiscomex\b|\bfreight forward(?:er|ing)\b|\bagente de cargas?\b|\btrading company\b",
    "sinal_global": r"\bglobal\b|\bmultinaciona(?:l|is)\b|\bmultinational\b|\bworldwide\b|\bem (?:mais de )?\d+ paises\b|\bin (?:over |more than )?\d+ countries\b|\ben (?:mas de )?\d+ paises\b|\bpresenca (?:global|internacional)\b|\bao redor do mundo\b|\bem todo o mundo\b|\baround the world\b|\binternacionalmente\b",
    "sinal_clientes_exterior": r"\b(?:clientes|fornecedores|parceiros) (?:no exterior|internacionais|em \d+ paises|em todo o mundo|ao redor do mundo|fora do brasil|em mais de \d+ paises)\b|\b(?:customers|clients|suppliers|partners) (?:in \d+ countries|worldwide|around the world|across the globe|in over \d+ countries)\b",
    "menciona_cambio": r"\bcambio\b|\bdolar(?:es)?\b|\bus\$|\busd\b|\beuros?\b|\bremessas? (?:internaciona(?:l|is)|ao exterior|para o exterior)\b|\bpagamentos? (?:internaciona(?:l|is)|ao exterior|no exterior)\b|\binternational payments?\b",
}
RX_SINAIS = {k: re.compile(v) for k, v in SINAIS.items()}

# Lugares: lista fechada (normalizado -> (nome, é exterior?)). Só nomes desta lista vão para a saída.
_EXTERIOR = """
estados unidos|EUA;eua|EUA;usa|EUA;united states|EUA;canada|Canadá;mexico|México;argentina|Argentina;chile|Chile;
colombia|Colômbia;peru|Peru;uruguai|Uruguai;uruguay|Uruguai;paraguai|Paraguai;paraguay|Paraguai;bolivia|Bolívia;
equador|Equador;ecuador|Equador;venezuela|Venezuela;panama|Panamá;costa rica|Costa Rica;portugal|Portugal;
espanha|Espanha;spain|Espanha;espana|Espanha;franca|França;france|França;francia|França;alemanha|Alemanha;
germany|Alemanha;alemania|Alemanha;italia|Itália;italy|Itália;reino unido|Reino Unido;united kingdom|Reino Unido;
inglaterra|Reino Unido;england|Reino Unido;irlanda|Irlanda;ireland|Irlanda;holanda|Holanda;paises baixos|Holanda;
netherlands|Holanda;belgica|Bélgica;belgium|Bélgica;suica|Suíça;switzerland|Suíça;suiza|Suíça;austria|Áustria;
suecia|Suécia;sweden|Suécia;noruega|Noruega;norway|Noruega;dinamarca|Dinamarca;denmark|Dinamarca;finlandia|Finlândia;
finland|Finlândia;polonia|Polônia;poland|Polônia;israel|Israel;emirados arabes|Emirados Árabes;
united arab emirates|Emirados Árabes;india|Índia;china|China;japao|Japão;japan|Japão;japon|Japão;
coreia do sul|Coreia do Sul;south korea|Coreia do Sul;singapura|Singapura;singapore|Singapura;hong kong|Hong Kong;
australia|Austrália;nova zelandia|Nova Zelândia;new zealand|Nova Zelândia;africa do sul|África do Sul;
south africa|África do Sul;angola|Angola;mocambique|Moçambique;mozambique|Moçambique;luxemburgo|Luxemburgo;
luxembourg|Luxemburgo;taiwan|Taiwan;turquia|Turquia;turkey|Turquia;europa|Europa;europe|Europa;asia|Ásia;
america latina|América Latina;latin america|América Latina;america do norte|América do Norte;north america|América do Norte;
miami|Miami (EUA);nova york|Nova York (EUA);nova iorque|Nova York (EUA);new york|Nova York (EUA);nueva york|Nova York (EUA);
boston|Boston (EUA);chicago|Chicago (EUA);houston|Houston (EUA);austin|Austin (EUA);dallas|Dallas (EUA);
atlanta|Atlanta (EUA);orlando|Orlando (EUA);san francisco|San Francisco (EUA);sao francisco|San Francisco (EUA);
silicon valley|Vale do Silício (EUA);vale do silicio|Vale do Silício (EUA);los angeles|Los Angeles (EUA);
seattle|Seattle (EUA);delaware|Delaware (EUA);toronto|Toronto (Canadá);montreal|Montreal (Canadá);
vancouver|Vancouver (Canadá);cidade do mexico|Cidade do México;mexico city|Cidade do México;ciudad de mexico|Cidade do México;
buenos aires|Buenos Aires;santiago do chile|Santiago (Chile);santiago de chile|Santiago (Chile);bogota|Bogotá;
medellin|Medellín;montevideu|Montevidéu;montevideo|Montevidéu;assuncao|Assunção;asuncion|Assunção;
londres|Londres;london|Londres;lisboa|Lisboa;lisbon|Lisboa;madri|Madri;madrid|Madri;barcelona|Barcelona;
paris|Paris;berlim|Berlim;berlin|Berlim;munique|Munique;munich|Munique;frankfurt|Frankfurt;hamburgo|Hamburgo;
hamburg|Hamburgo;amsterda|Amsterdã;amsterdam|Amsterdã;roterda|Roterdã;rotterdam|Roterdã;bruxelas|Bruxelas;
brussels|Bruxelas;zurique|Zurique;zurich|Zurique;genebra|Genebra;geneva|Genebra;milao|Milão;milan|Milão;
roma|Roma;rome|Roma;dublin|Dublin;estocolmo|Estocolmo;stockholm|Estocolmo;copenhague|Copenhague;copenhagen|Copenhague;
oslo|Oslo;helsinque|Helsinque;helsinki|Helsinque;varsovia|Varsóvia;warsaw|Varsóvia;viena|Viena;vienna|Viena;
praga|Praga;prague|Praga;tel aviv|Tel Aviv;dubai|Dubai;abu dhabi|Abu Dhabi;mumbai|Mumbai;bangalore|Bangalore;
bengaluru|Bangalore;nova delhi|Nova Délhi;new delhi|Nova Délhi;xangai|Xangai;shanghai|Xangai;pequim|Pequim;
beijing|Pequim;shenzhen|Shenzhen;guangzhou|Cantão;cantao|Cantão;taipei|Taipei;toquio|Tóquio;tokyo|Tóquio;
osaka|Osaka;seul|Seul;seoul|Seul;sydney|Sydney;melbourne|Melbourne;joanesburgo|Joanesburgo;johannesburg|Joanesburgo;
luanda|Luanda;maputo|Maputo;istambul|Istambul;istanbul|Istambul
"""
_BRASIL = """
brasil|Brasil;brazil|Brasil;sao paulo|São Paulo;rio de janeiro|Rio de Janeiro;belo horizonte|Belo Horizonte;
curitiba|Curitiba;porto alegre|Porto Alegre;brasilia|Brasília;recife|Recife;salvador|Salvador;fortaleza|Fortaleza;
campinas|Campinas;florianopolis|Florianópolis;manaus|Manaus;goiania|Goiânia;vitoria|Vitória;joinville|Joinville;
barueri|Barueri;alphaville|Alphaville;santos|Santos;itajai|Itajaí;paranagua|Paranaguá;ribeirao preto|Ribeirão Preto;
sorocaba|Sorocaba;sao jose dos campos|São José dos Campos;jundiai|Jundiaí;blumenau|Blumenau;londrina|Londrina;
maringa|Maringá;uberlandia|Uberlândia;natal|Natal;joao pessoa|João Pessoa;maceio|Maceió;aracaju|Aracaju;belem|Belém;
sao luis|São Luís;teresina|Teresina;cuiaba|Cuiabá;campo grande|Campo Grande;macae|Macaé;guarulhos|Guarulhos;
osasco|Osasco;niteroi|Niterói;caxias do sul|Caxias do Sul;chapeco|Chapecó;foz do iguacu|Foz do Iguaçu
"""


def _carregar_lugares() -> dict[str, tuple[str, bool]]:
    lugares = {}
    for bloco, exterior in ((_EXTERIOR, True), (_BRASIL, False)):
        for par in bloco.replace("\n", "").split(";"):
            if par.strip():
                chave, nome = par.split("|")
                lugares[chave.strip()] = (nome.strip(), exterior)
    return lugares


LUGARES = _carregar_lugares()
RX_LUGAR = re.compile(r"\b(" + "|".join(sorted(map(re.escape, LUGARES), key=len, reverse=True)) + r")\b")
RX_JANELA_ESCRITORIO = re.compile(r"\b(?:escritorios?|filia(?:l|is)|unidades?|offices?|oficinas?|sucursa(?:l|les)|presenca|bases?)\b[^.;:!?]{0,25}?\b(?:em|no|na|nos|nas|in|en)\b([^.;!?]{0,90})")
RX_JANELA_MATRIZ = re.compile(r"\b(?:matriz|sede(?: global| mundial| internacional| corporativa)?|headquarter(?:s|ed)|hq|casa matriz|controladora)\b[^.;:!?]{0,25}?\b(?:em|no|na|nos|nas|in|en)\b([^.;!?]{0,70})")
RX_SUBSIDIARIA = re.compile(r"\b(?:subsidiaria|filial|braco|unidade|operacao) (?:brasileira|no brasil|do brasil)\b|\bsubsidiary of\b|\bbrazilian (?:subsidiary|branch|arm|office|unit)\b|\bpertence ao grupo\b|\bdo grupo (?:alemao|americano|norte-americano|frances|ingles|britanico|japones|chines|italiano|espanhol|suico|holandes|sueco|canadense|portugues|argentino|chileno|mexicano|europeu|asiatico)\b")


RX_FIM_JANELA = re.compile(r"\b(?:por|com|sob|liderad\w*|dirigid\w*|comandad\w*|onde|que|desde|with|led|since|where|which|who|by)\b")


def lugares_em(janela: str) -> list[tuple[str, bool]]:
    """Lugares da lista fechada que aparecem na janela, cortada antes de palavras que costumam
    introduzir outra coisa ("escritório em Miami, liderado por Orlando...")."""
    janela = RX_FIM_JANELA.split(janela, maxsplit=1)[0]
    vistos = []
    for m in RX_LUGAR.finditer(janela):
        lugar = LUGARES[m.group(1)]
        if lugar not in vistos:
            vistos.append(lugar)
    return vistos


def achar_sinais(paginas: list[Pagina]) -> dict:
    out = {k: 0 for k in SINAIS} | {"sinal_matriz_exterior": 0, "escritorio_exterior": 0}
    evid: dict[str, list[str]] = {}
    matriz, escritorios, vagas = [], [], []

    def anota(sinal: str, termo: str) -> None:
        lista = evid.setdefault(sinal, [])
        if termo not in lista and len(lista) < 4:
            lista.append(termo)

    for p in paginas:
        t = norm(p.texto)
        for k, rx in RX_SINAIS.items():
            for m in rx.finditer(t):
                out[k] = 1
                anota(k, m.group(0))
        for m in RX_JANELA_MATRIZ.finditer(t):
            for nome, exterior in lugares_em(m.group(1)):
                if nome not in matriz:
                    matriz.append(nome)
                if exterior:
                    out["sinal_matriz_exterior"] = 1
                    anota("sinal_matriz_exterior", "matriz/sede: " + nome)
        for m in RX_SUBSIDIARIA.finditer(t):
            out["sinal_matriz_exterior"] = 1
            anota("sinal_matriz_exterior", m.group(0))
        for m in RX_JANELA_ESCRITORIO.finditer(t):
            for nome, exterior in lugares_em(m.group(1)):
                if nome not in escritorios:
                    escritorios.append(nome)
                if exterior:
                    out["escritorio_exterior"] = 1
        if p.categoria == "carreiras":
            for m in RX_VAGA.finditer(t):
                cargo = m.group(0).strip()
                if cargo not in vagas:
                    vagas.append(cargo)
    out["matriz_em"] = "; ".join(matriz[:MAX_ITENS])
    out["escritorios"] = "; ".join(escritorios[:MAX_ITENS])
    out["vagas_alvo"] = "; ".join(vagas[:8])
    out["evidencias"] = " | ".join(f"{k.removeprefix('sinal_')}: {', '.join(v)}" for k, v in evid.items())
    out["n_sinais"] = sum(out[k] for k in SINAIS_BINARIOS) + (1 if vagas else 0)
    return out


STOP = {
    "pt": set("nao voce sao tambem nossa nosso nossos nossas uma com dos das pelo pela seu sua mais servicos solucoes voces ate entao isso empresa clientes".split()),
    "en": set("the and of to is our we with you your are this that from for more about services solutions company customers".split()),
    "es": set("el los las del y nuestra nuestro nuestros nuestras servicios soluciones tambien usted ustedes sus con muy hacia empresa clientes".split()),
}


def idioma(texto: str) -> str:
    tokens = re.findall(r"[a-z]+", norm(texto))
    contas = {k: sum(1 for t in tokens if t in v) for k, v in STOP.items()}
    total = sum(contas.values())
    melhor = max(contas, key=contas.get)
    if total < 5 or contas[melhor] < 0.5 * total:
        return "indefinido"
    return melhor


# --------------------------------------------------------------------------- páginas internas

CATEGORIAS = [
    ("contato", r"contatos?|fale[-_ ]?conosco|contact(?:[-_ ]?us)?|contacto|atendimento|onde[-_ ]?estamos"),
    ("sobre", r"sobre(?:[-_ ]?nos)?|quem[-_ ]?somos|about(?:[-_ ]?us)?|a[-_ ]?empresa|nossa[-_ ]?empresa|institucional|nossa[-_ ]?historia|company|quienes[-_ ]?somos|nosotros"),
    ("carreiras", r"carreiras?|trabalhe[-_ ]?conosco|vagas|careers?|jobs|join[-_ ]?us|oportunidades|empregos|trabaja[-_ ]?con[-_ ]?nosotros"),
    ("equipe", r"equipe|nossa[-_ ]?equipe|nosso[-_ ]?time|time|team|our[-_ ]?team|lideranca|leadership"),
]
EXT_NAO_HTML = re.compile(r"\.(?:pdf|jpe?g|png|gif|webp|svg|zip|rar|docx?|xlsx?|pptx?|mp4|mp3|avi|mov|csv|xml|json|txt)$", re.I)


def escolher_internas(links: list[tuple[str, str]], url_home: str, n: int) -> list[tuple[str, str]]:
    """Até n links internos, um por categoria, na ordem contato > sobre > carreiras > equipe.
    Casa primeiro pelo caminho da URL e depois pelo texto do link; prefere o caminho mais curto."""
    host_home = urlsplit(url_home).netloc
    home_sem_barra = url_home.rstrip("/")
    candidatos = []
    for url, texto in links:
        partes = urlsplit(url)
        if partes.scheme not in ("http", "https") or not mesmo_site(partes.netloc, host_home):
            continue
        if url.rstrip("/") == home_sem_barra or EXT_NAO_HTML.search(partes.path):
            continue
        candidatos.append((url, norm(unquote(partes.path)), norm(texto)))
    escolhidos: list[tuple[str, str]] = []
    for cat, kw in CATEGORIAS:
        if len(escolhidos) >= n:
            break
        rx_caminho = re.compile(rf"(?:^|[/_.\- ])(?:{kw})(?:$|[/_.\- ])")
        rx_texto = re.compile(rf"\b(?:{kw})\b")
        ja = {u for u, _ in escolhidos}
        por_caminho = [c for c in candidatos if c[0] not in ja and rx_caminho.search(c[1])]
        por_texto = [c for c in candidatos if c[0] not in ja and rx_texto.search(c[2])]
        lista = sorted(por_caminho, key=lambda c: (len(c[1]), c[0])) or sorted(por_texto, key=lambda c: (len(c[1]), c[0]))
        if lista:
            escolhidos.append((lista[0][0], cat))
    return escolhidos


# --------------------------------------------------------------------------- transporte

@dataclass
class RespostaBruta:
    status: int
    url: str
    tipo: str
    corpo: bytes
    local: str | None = None        # cabeçalho Location (redirecionamento)
    truncado: bool = False


class TransporteLeve:
    """requests sem seguir redirecionamento (quem segue é o Coletor, conferindo o robots.txt)."""
    nome = "leve"

    def __init__(self, max_bytes: int = MAX_BYTES_PAGINA, timeout=TIMEOUT):
        self.max_bytes, self.timeout = max_bytes, timeout
        self._local = threading.local()

    def _sessao(self) -> requests.Session:
        s = getattr(self._local, "s", None)
        if s is None:
            s = requests.Session()
            s.headers.update({"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
                              "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.5"})
            self._local.s = s
        return s

    def __call__(self, url: str) -> RespostaBruta:
        with self._sessao().get(url, stream=True, timeout=self.timeout, allow_redirects=False) as r:
            tipo = r.headers.get("Content-Type", "")
            corpo, truncado = bytearray(), False
            if r.status_code < 300 and (e_html(tipo) or "text/plain" in tipo.lower()):
                for bloco in r.iter_content(65536):
                    corpo += bloco
                    if len(corpo) >= self.max_bytes:
                        truncado = True
                        del corpo[self.max_bytes:]
                        break
            return RespostaBruta(r.status_code, url, tipo, bytes(corpo), r.headers.get("Location"), truncado)

    def fechar(self) -> None:
        pass


class TransporteCrawl4AI:
    """Crawl4AI como biblioteca: renderiza a página num Chromium (pega site feito em JavaScript).
    Um navegador só, num laço asyncio próprio, compartilhado pelos workers. O navegador segue
    redirecionamentos sozinho; o Coletor confere o robots.txt do destino e descarta o conteúdo
    se o destino for proibido. A checagem "anti-bot" do Crawl4AI é ignorada quando a página veio
    com HTTP 200 e HTML (ela marca como bloqueada página legítima curta, como um 'contato')."""
    nome = "crawl4ai"

    def __init__(self, cdp_url: str | None = None, max_bytes: int = MAX_BYTES_PAGINA, timeout_ms: int = 30000):
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
        self.max_bytes = max_bytes
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()
        bc = BrowserConfig(headless=True, cdp_url=cdp_url, user_agent=UA, verbose=False)
        self.crawler = AsyncWebCrawler(config=bc)
        self._rodar(self.crawler.start(), 120)
        self.cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, page_timeout=timeout_ms, verbose=False,
                                    check_robots_txt=False)

    def _rodar(self, coro, timeout: float):
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result(timeout)

    def __call__(self, url: str) -> RespostaBruta:
        r = self._rodar(self.crawler.arun(url, config=self.cfg), 120)
        html = r.html or ""
        if not html:
            raise OSError(r.error_message or "Crawl4AI não devolveu HTML")
        cab = {k.lower(): v for k, v in (r.response_headers or {}).items()}
        tipo = cab.get("content-type", "text/html")
        tipo = "text/html; charset=utf-8" if e_html(tipo) else tipo   # o HTML renderizado é recodificado em UTF-8
        corpo = html.encode("utf-8")
        truncado = len(corpo) > self.max_bytes
        return RespostaBruta(r.status_code or 200, r.redirected_url or r.url or url, tipo,
                             corpo[: self.max_bytes], None, truncado)

    def fechar(self) -> None:
        async def cancelar_pendentes() -> None:
            tarefas = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
            for t in tarefas:
                t.cancel()
            await asyncio.gather(*tarefas, return_exceptions=True)

        try:
            self._rodar(self.crawler.close(), 60)
            self._rodar(cancelar_pendentes(), 10)
        finally:
            self.loop.call_soon_threadsafe(self.loop.stop)


def criar_transporte(motor: str, cdp_url: str | None = None):
    if motor in ("auto", "crawl4ai"):
        try:
            return TransporteCrawl4AI(cdp_url)
        except ImportError:
            if motor == "crawl4ai":
                raise SystemExit("Motor crawl4ai pedido, mas o pacote não está instalado: pip install crawl4ai && crawl4ai-setup")
        except Exception as e:  # noqa: BLE001
            if motor == "crawl4ai":
                raise SystemExit(f"Crawl4AI não abriu o navegador: {e}")
            print(f"Crawl4AI instalado mas não abriu o navegador ({e}); sigo com o motor leve.", file=sys.stderr)
    return TransporteLeve()


# --------------------------------------------------------------------------- ritmo e robots.txt

class Limitador:
    """No máximo uma requisição a cada `intervalo` segundos por domínio, entre todas as threads."""

    def __init__(self, relogio: Callable[[], float] = time.monotonic, dormir: Callable[[float], None] = time.sleep):
        self.relogio, self.dormir = relogio, dormir
        self.proxima: dict[str, float] = {}
        self.lock = threading.Lock()

    def esperar(self, chave: str, intervalo: float) -> None:
        with self.lock:
            agora = self.relogio()
            vez = max(agora, self.proxima.get(chave, agora))
            self.proxima[chave] = vez + intervalo
        if vez > agora:
            self.dormir(vez - agora)


@dataclass
class Robots:
    estado: str                       # ok | ausente | inacessivel | sem_conexao
    parser: RobotFileParser | None = None
    atraso: float = 0.0

    def pode(self, url: str) -> bool:
        if self.estado == "ausente":
            return True
        if self.estado in ("inacessivel", "sem_conexao") or self.parser is None:
            return False
        return self.parser.can_fetch(UA_TOKEN, url)


def chave_dominio(url: str) -> str:
    return urlsplit(url).netloc.lower().split(":")[0].removeprefix("www.")


# --------------------------------------------------------------------------- coletor

@dataclass
class Coletor:
    transporte: Callable[[str], RespostaBruta]
    transporte_robots: Callable[[str], RespostaBruta] | None = None
    intervalo: float = INTERVALO_MIN_S
    max_paginas: int = MAX_PAGINAS_SITE
    relogio: Callable[[], float] = time.monotonic
    dormir: Callable[[float], None] = time.sleep
    nome_motor: str = "leve"
    _robots: dict = field(default_factory=dict)
    _atraso: dict = field(default_factory=dict)

    def __post_init__(self):
        self.transporte_robots = self.transporte_robots or self.transporte
        self.limitador = Limitador(self.relogio, self.dormir)
        self._lock = threading.Lock()

    def _pedir(self, url: str, robots: bool = False) -> RespostaBruta | None:
        chave = chave_dominio(url)
        self.limitador.esperar(chave, max(self.intervalo, self._atraso.get(chave, 0.0)))
        try:
            return (self.transporte_robots if robots else self.transporte)(url)
        except (requests.RequestException, OSError, TimeoutError, asyncio.TimeoutError) as e:  # noqa: F841
            return None

    def robots(self, url: str) -> Robots:
        p = urlsplit(url)
        chave = (p.scheme, p.netloc.lower())
        with self._lock:
            if chave in self._robots:
                return self._robots[chave]
        alvo = f"{p.scheme}://{p.netloc}/robots.txt"
        r = None
        for _ in range(MAX_REDIRECIONAMENTOS + 1):
            r = self._pedir(alvo, robots=True)
            if r is None or r.status not in REDIRECIONA or not r.local:
                break
            alvo = urljoin(alvo, r.local)
        if r is None:
            rb = Robots("sem_conexao")
        elif r.status >= 500 or r.status in REDIRECIONA:
            rb = Robots("inacessivel")
        elif r.status >= 400:
            rb = Robots("ausente")
        else:
            parser = RobotFileParser()
            parser.parse(decodificar(r.corpo, r.tipo).splitlines())
            atraso = parser.crawl_delay(UA_TOKEN) or 0
            rb = Robots("ok", parser, min(float(atraso), CRAWL_DELAY_MAX_S))
            with self._lock:
                self._atraso[chave_dominio(url)] = max(self._atraso.get(chave_dominio(url), 0.0), rb.atraso)
        with self._lock:
            self._robots[chave] = rb
        return rb

    def baixar_pagina(self, url: str) -> tuple[str, RespostaBruta | None]:
        """Pede a URL seguindo até 5 redirecionamentos e conferindo o robots.txt de cada passo.
        Devolve (motivo, resposta): motivo 'ok' quando veio HTML com status 2xx."""
        for _ in range(MAX_REDIRECIONAMENTOS + 1):
            rb = self.robots(url)
            if rb.estado == "sem_conexao":
                return "sem resposta", None
            if rb.estado == "inacessivel":
                return "robots.txt inacessível", None
            if not rb.pode(url):
                return "robots.txt bloqueia", None
            r = self._pedir(url)
            if r is None:
                return "sem resposta", None
            if r.status in REDIRECIONA and r.local:
                url = urljoin(url, r.local)
                continue
            if r.url != url and not self.robots(r.url).pode(r.url):   # o navegador redirecionou sozinho
                return "robots.txt bloqueia", None
            if r.status >= 400:
                return f"HTTP {r.status}", None
            if not e_html(r.tipo):
                return "não é HTML", None
            return "ok", r
        return "redirecionamentos demais", None

    def processar(self, dominio: str) -> dict:
        res = {c: "" for c in COLUNAS_NOVAS}
        res.update(motor=self.nome_motor, coletado_em=dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
                   paginas_lidas=0, n_emails_pessoais_descartados=0, n_sinais=0, texto_chars=0)
        for k in SINAIS_BINARIOS:
            res[k] = 0
        home, motivos = None, []
        for base in (f"https://{dominio}/", f"https://www.{dominio}/", f"http://{dominio}/", f"http://www.{dominio}/"):
            motivo, r = self.baixar_pagina(base)
            if motivo == "ok":
                home = r
                break
            motivos.append(motivo)
            if motivo == "robots.txt bloqueia":
                break
        if home is None:
            prioridade = ["robots.txt bloqueia", "não é HTML", "robots.txt inacessível"]
            res["status_site"] = next((m for m in prioridade if m in motivos), None) or \
                next((m for m in motivos if m.startswith("HTTP")), motivos[-1] if motivos else "sem resposta")
            return res

        paginas = [extrair_html(decodificar(home.corpo, home.tipo), home.url, "home")]
        res["site"] = home.url
        if not mesmo_site(urlsplit(home.url).netloc, dominio):
            res["redireciona_para"] = urlsplit(home.url).netloc.lower()
        for url, cat in escolher_internas(paginas[0].links, home.url, self.max_paginas - 1):
            motivo, r = self.baixar_pagina(url)
            if motivo == "ok":
                paginas.append(extrair_html(decodificar(r.corpo, r.tipo), r.url, cat))

        dominios_site = [dominio, urlsplit(home.url).netloc]
        emails, emails_outros, descartados = achar_emails(paginas, dominios_site)
        tel_br, tel_ext = achar_telefones(paginas)
        res.update(
            status_site="ok", paginas_lidas=len(paginas), paginas=";".join(p.categoria for p in paginas),
            texto_chars=sum(len(p.texto) for p in paginas),
            idioma=idioma(" ".join(p.texto for p in paginas)), lang_html=paginas[0].lang or "",
            hreflangs=";".join(sorted(set().union(*(p.hreflangs for p in paginas))))[:80],
            emails_funcao=";".join(emails), emails_funcao_outros_dominios=";".join(emails_outros),
            n_emails_pessoais_descartados=descartados,
            telefones_br=";".join(tel_br), telefones_exterior=";".join(tel_ext),
            linkedin_empresa=";".join(achar_linkedin(paginas)), plataforma_vagas=";".join(achar_plataformas(paginas)),
        )
        res.update(achar_sinais(paginas))
        if res["texto_chars"] < 400:
            res["status_site"] = "ok, pouco texto (site em JavaScript?)"
        return res


# --------------------------------------------------------------------------- rodada

def ler_entrada(caminho: Path) -> list[dict]:
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def dominio_valido(d: str) -> bool:
    return bool(re.fullmatch(r"(?:[a-z0-9-]+\.)+[a-z]{2,24}(?::\d{2,5})?|127\.0\.0\.1:\d{2,5}", d or ""))


def rodar(entrada: Path, saida: Path | None = None, limite: int | None = None, workers: int = 6,
          motor: str = "auto", cdp_url: str | None = None, refazer: bool = False,
          coletor: Coletor | None = None, intervalo: float = INTERVALO_MIN_S) -> Path:
    saida = saida or entrada.parent
    saida.mkdir(parents=True, exist_ok=True)
    linhas = ler_entrada(entrada)
    if linhas and "marca_email" not in linhas[0]:
        raise SystemExit(f"{entrada} não tem a coluna marca_email (é o top1000.csv da lista quente?)")
    alvo = [l for l in linhas if l.get("marca_email") == "próprio" and dominio_valido((l.get("dominio_email") or "").lower())]
    dominios = list(dict.fromkeys(l["dominio_email"].lower() for l in alvo))
    if limite:
        dominios = dominios[:limite]

    cache_path = saida / "cache_sites.jsonl"
    cache: dict[str, dict] = {}
    if cache_path.exists() and not refazer:
        for linha in cache_path.read_text(encoding="utf-8").splitlines():
            try:
                item = json.loads(linha)
                cache[item["dominio"]] = item["resultado"]
            except (ValueError, KeyError):
                continue
    pendentes = [d for d in dominios if d not in cache]

    transporte = None
    if coletor is None:
        transporte = criar_transporte(motor, cdp_url)
        robots_t = TransporteLeve() if transporte.nome == "crawl4ai" else transporte
        coletor = Coletor(transporte, robots_t, intervalo=intervalo, nome_motor=transporte.nome)
    t0 = time.time()
    print(f"{len(linhas)} linhas · {len(alvo)} com domínio próprio · {len(dominios)} domínios · "
          f"{len(dominios) - len(pendentes)} já no cache · motor {coletor.nome_motor}", flush=True)
    lock = threading.Lock()
    try:
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool, open(cache_path, "a", encoding="utf-8") as fc:
            futuros = {pool.submit(coletor.processar, d): d for d in pendentes}
            for i, fut in enumerate(as_completed(futuros), 1):
                d = futuros[fut]
                try:
                    res = fut.result()
                except Exception as e:  # noqa: BLE001
                    res = {c: "" for c in COLUNAS_NOVAS} | {"status_site": f"erro: {type(e).__name__}"}
                with lock:
                    cache[d] = res
                    fc.write(json.dumps({"dominio": d, "resultado": res}, ensure_ascii=False) + "\n")
                    fc.flush()
                print(f"[{i}/{len(pendentes)}] {d}: {res['status_site']} · {res.get('paginas_lidas', 0)} pág. · "
                      f"{res.get('n_sinais', 0)} sinais", flush=True)
    finally:
        if transporte is not None:
            transporte.fechar()

    colunas = [c for c in (linhas[0].keys() if linhas else []) if c not in COLUNAS_NOVAS] + COLUNAS_NOVAS
    destino = saida / "enriquecido.csv"
    with open(destino, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=colunas, extrasaction="ignore")
        w.writeheader()
        for l in linhas:
            d = (l.get("dominio_email") or "").lower()
            if d in cache:
                extra = cache[d]
            elif l.get("marca_email") != "próprio" or not dominio_valido(d):
                motivo = "sem e-mail cadastral" if not d else "não visitado: domínio genérico ou de contador"
                extra = {"status_site": motivo}
            else:
                extra = {"status_site": "não visitado: fora do --limite"}
            w.writerow(l | {c: extra.get(c, "") for c in COLUNAS_NOVAS})
    escrever_relatorio(saida / "relatorio.md", entrada, linhas, cache, dominios, coletor, time.time() - t0)
    print(f"ok: {destino} e {saida / 'relatorio.md'}", flush=True)
    return destino


def escrever_relatorio(caminho: Path, entrada: Path, linhas: list[dict], cache: dict, dominios: list[str],
                       coletor: Coletor, segundos: float) -> None:
    res = [cache[d] for d in dominios if d in cache]
    ok = [r for r in res if str(r.get("status_site", "")).startswith("ok")]
    contagem: dict[str, int] = {}
    for r in res:
        contagem[r.get("status_site", "?")] = contagem.get(r.get("status_site", "?"), 0) + 1

    def pct(n: int) -> str:
        return f"{n} ({100 * n / len(ok):.0f}%)" if ok else "0"

    sinais = {k: sum(1 for r in ok if int(r.get(k) or 0)) for k in SINAIS_BINARIOS}
    com_vagas = sum(1 for r in ok if r.get("vagas_alvo"))
    por_dominio = {}
    for l in linhas:
        d = (l.get("dominio_email") or "").lower()
        por_dominio.setdefault(d, l)
    top = sorted((d for d in dominios if d in cache and str(cache[d].get("status_site", "")).startswith("ok")),
                 key=lambda d: (-int(cache[d].get("n_sinais") or 0), -float(por_dominio.get(d, {}).get("nota") or 0)))[:25]
    L = [f"# Enriquecimento de site · {dt.datetime.now():%d/%m/%Y %H:%M}", "",
         f"Entrada: `{entrada}` · motor `{coletor.nome_motor}` · {coletor.intervalo:.1f} s entre requisições por domínio "
         f"· até {coletor.max_paginas} páginas por site · {segundos / 60:.1f} min nesta rodada.", "",
         "## Cobertura", "",
         "| Item | Quantidade |", "|---|---|",
         f"| Linhas na entrada | {len(linhas)} |",
         f"| Com domínio próprio (marca_email = próprio) | {sum(1 for l in linhas if l.get('marca_email') == 'próprio')} |",
         f"| Domínios distintos visitados | {len(res)} |",
         f"| Sites lidos | {len(ok)} |",
         f"| Páginas lidas | {sum(int(r.get('paginas_lidas') or 0) for r in res)} |", "",
         "## Resultado por site", "", "| Status | Sites |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in sorted(contagem.items(), key=lambda kv: -kv[1])]
    L += ["", "## Sinais nos sites lidos", "", "| Sinal | Sites |", "|---|---|"]
    L += [f"| {k.removeprefix('sinal_')} | {pct(v)} |" for k, v in sinais.items()]
    L += [f"| vagas de comex/finanças/tesouraria | {pct(com_vagas)} |",
          f"| com e-mail de função publicado | {pct(sum(1 for r in ok if r.get('emails_funcao')))} |",
          f"| com telefone no Brasil | {pct(sum(1 for r in ok if r.get('telefones_br')))} |",
          f"| com telefone no exterior | {pct(sum(1 for r in ok if r.get('telefones_exterior')))} |",
          f"| com página da empresa no LinkedIn | {pct(sum(1 for r in ok if r.get('linkedin_empresa')))} |",
          f"| e-mails pessoais descartados (só contados) | {sum(int(r.get('n_emails_pessoais_descartados') or 0) for r in res)} |",
          "", "## Mais sinais (até 25)", "", "| CNPJ | Empresa | Nota | Sinais | Evidências |", "|---|---|---|---|---|"]
    for d in top:
        l, r = por_dominio.get(d, {}), cache[d]
        nome = (l.get("nome_fantasia") or l.get("razao_social") or d).replace("|", "/")
        L.append(f"| {l.get('cnpj', '')} | {nome} | {l.get('nota', '')} | {r.get('n_sinais')} | "
                 f"{str(r.get('evidencias', '')).replace('|', '·')[:160]} |")
    bloqueados = sorted(d for d in dominios if d in cache and cache[d].get("status_site") == "robots.txt bloqueia")
    if bloqueados:
        L += ["", f"## robots.txt bloqueou ({len(bloqueados)})", "", ", ".join(bloqueados)]
    L += ["", "## Como ler", "",
          "- `n_sinais` soma os sinais binários e conta 1 se houver vaga-alvo. É indício, não prova de remessa.",
          "- `evidencias` traz só os termos fixos que dispararam cada sinal, sem trecho do site.",
          "- `escritorios` e `matriz_em` só mostram lugares de uma lista fechada (países e cidades).",
          "- \"ok, pouco texto\" quase sempre é site feito em JavaScript; com o motor crawl4ai ele é renderizado."]
    caminho.write_text("\n".join(L) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("entrada", type=Path, help="top1000.csv da lista quente")
    ap.add_argument("--saida", type=Path, help="pasta de saída (padrão: a pasta da entrada)")
    ap.add_argument("--limite", type=int, help="visita só os N primeiros domínios (teste)")
    ap.add_argument("--workers", type=int, default=6, help="domínios em paralelo (cada um a 1 req/s); padrão 6")
    ap.add_argument("--motor", choices=["auto", "crawl4ai", "leve"], default="auto")
    ap.add_argument("--cdp-url", help="motor crawl4ai: usar um Chrome já aberto (ex.: http://127.0.0.1:9222)")
    ap.add_argument("--intervalo", type=float, default=INTERVALO_MIN_S, help="segundos entre requisições ao mesmo domínio (mínimo 1)")
    ap.add_argument("--refazer", action="store_true", help="ignora o cache_sites.jsonl e visita de novo")
    a = ap.parse_args(argv)
    rodar(a.entrada, a.saida, a.limite, a.workers, a.motor, a.cdp_url, a.refazer, intervalo=max(1.0, a.intervalo))


if __name__ == "__main__":
    main(sys.argv[1:])
