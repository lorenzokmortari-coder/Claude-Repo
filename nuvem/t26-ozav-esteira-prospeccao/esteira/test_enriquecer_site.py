"""Testes do enriquecer_site.py com sites SINTÉTICOS (nenhuma empresa, pessoa ou número real).

1. Funções de extração sobre HTML sintético (e-mail, telefone, LinkedIn, sinais, lugares, idioma).
2. Coletor com um transporte falso e um relógio falso: robots.txt, redirecionamento, ritmo de
   1 req/s por domínio (e Crawl-delay), teto de páginas e os status de falha.
3. Rodada completa (top1000.csv sintético -> enriquecido.csv + relatorio.md) com checagem de
   privacidade byte a byte: nenhum nome de pessoa nem e-mail pessoal na saída.
4. Integração com HTTP de verdade (requests) contra um servidor local.
5. Opcional: o mesmo site local pelo motor crawl4ai (renderiza JavaScript). Roda só se o
   pacote crawl4ai estiver instalado e ENRIQUECER_CDP_URL apontar para um Chrome aberto.

Rodar: python -m pytest -q
"""
from __future__ import annotations

import csv
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import requests

import enriquecer_site as es

# --------------------------------------------------------------------------- sites sintéticos

ROBOTS_ALFA = "User-agent: *\nDisallow: /equipe\nCrawl-delay: 2\n"
TEXTO_LONGO = " Atendemos indústrias de todos os portes com tecnologia própria e suporte local." * 6

HOME_ALFA = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>Alfa Teste</title>
<link rel="alternate" hreflang="en" href="https://www.alfa-teste.com.br/en/"><link rel="alternate" hreflang="pt-br" href="/">
<style>.x{{color:red}}</style></head><body>
<nav><a href="/quem-somos">Quem somos</a> <a href="/contato">Fale conosco</a> <a href="/trabalhe-conosco">Carreiras</a>
<a href="/equipe">Nossa equipe</a> <a href="/blog">Blog</a> <a href="/politica.pdf">Política</a> <a href="#topo">topo</a>
<a href="javascript:void(0)">menu</a></nav>
<h1>Alfa Software Teste</h1>
<p>Somos uma empresa global com escritórios em São Paulo, Miami e Lisboa. Exportamos software para clientes em 12 países.{TEXTO_LONGO}</p>
<footer><a href="https://www.linkedin.com/company/alfa-teste/">LinkedIn</a>
<a href="https://www.linkedin.com/in/maria-ficticia-souza">Maria no LinkedIn</a>
<a href="https://alfateste.gupy.io/">Vagas</a> <a href="mailto:contato@alfa-teste.com.br">contato</a>
<a href="mailto:maria.souza@alfa-teste.com.br">fale com a Maria</a> <a href="tel:+551134567890">ligue</a></footer>
<script>var segredo = "joao.silva@alfa-teste.com.br";</script></body></html>"""

SOBRE_ALFA = """<html lang="pt-BR"><body><h1>Quem somos</h1>
<p>A Alfa é subsidiária brasileira da Alfa Holdings Inc., com sede em Nova York. Trabalhamos com importação de
equipamentos de rede e oferecemos exportação de relatórios em PDF.</p></body></html>"""

CONTATO_ALFA = """<html lang="pt-BR"><body><h1>Contato</h1>
<p>Comercial: comercial@alfa-teste.com.br · Financeiro: financeiro2@alfa-teste.com.br · RH do grupo: rh@grupo-alfa.com</p>
<p>Diretor: joao.silva@alfa-teste.com.br · Cookies: privacidade@onetrust.com · logo@2x.png</p>
<p>Telefone (11) 3456-7890 · Miami +1 305 577 1234 · CNPJ 11.111.111/0001-91 · CEP 01310-100</p>
<p>Pagamentos internacionais em dólar.</p></body></html>"""

CARREIRAS_ALFA = """<html lang="pt-BR"><body><h1>Trabalhe conosco</h1><ul>
<li>Analista de Comércio Exterior Pleno</li><li>Coordenador(a) de Tesouraria</li><li>Desenvolvedor Python</li></ul></body></html>"""

EQUIPE = """<html><body><h1>Equipe</h1><p>Maria Fictícia Souza, Diretora Financeira. João Silva, Gerente de Importação.</p></body></html>"""

HOME_ZETA = f"""<html lang="en"><body><h1>Zeta Logistics</h1>
<p>We are a freight forwarding company headquartered in Rotterdam with offices in London and Miami.
Our customers in 40 countries trust our international trade experts.{" We move cargo every day for our partners." * 8}</p>
<a href="/about-us">About us</a></body></html>"""

HOME_DELTA = f"""<html lang="pt-BR"><body><p>Delta Teste.{TEXTO_LONGO}</p>
<a href="/equipe">Equipe</a> <a href="/contato">Contato</a></body></html>"""

HOME_ETA = f"""<html lang="pt-BR"><body><p>Eta Brasil, parte de um grupo global.{TEXTO_LONGO}</p></body></html>"""


class Relogio:
    def __init__(self):
        self.t = 1000.0

    def agora(self) -> float:
        return self.t

    def dormir(self, s: float) -> None:
        self.t += s


class TransporteFalso:
    """Mapa url -> (status, content-type, corpo, Location). Host em `sem_conexao` levanta erro."""

    def __init__(self, relogio: Relogio):
        self.relogio = relogio
        self.pedidos: list[tuple[float, str]] = []
        self.sem_conexao = {"epsilon-teste.com.br", "www.epsilon-teste.com.br"}
        html = "text/html; charset=utf-8"
        txt = "text/plain"
        self.mapa = {
            "https://alfa-teste.com.br/robots.txt": (200, txt, ROBOTS_ALFA, None),
            "https://alfa-teste.com.br/": (301, html, "", "https://www.alfa-teste.com.br/"),
            "https://www.alfa-teste.com.br/robots.txt": (200, txt, ROBOTS_ALFA, None),
            "https://www.alfa-teste.com.br/": (200, html, HOME_ALFA, None),
            "https://www.alfa-teste.com.br/quem-somos": (200, html, SOBRE_ALFA, None),
            "https://www.alfa-teste.com.br/contato": (200, html, CONTATO_ALFA, None),
            "https://www.alfa-teste.com.br/trabalhe-conosco": (200, html, CARREIRAS_ALFA, None),
            "https://www.alfa-teste.com.br/equipe": (200, html, EQUIPE, None),
            "https://beta-teste.com.br/robots.txt": (200, txt, "User-agent: *\nDisallow: /\n", None),
            "https://gama-teste.com/robots.txt": (503, txt, "", None),
            "https://www.gama-teste.com/robots.txt": (503, txt, "", None),
            "http://gama-teste.com/robots.txt": (503, txt, "", None),
            "http://www.gama-teste.com/robots.txt": (503, txt, "", None),
            "https://zeta-teste.com/": (200, html, HOME_ZETA, None),
            "https://zeta-teste.com/about-us": (200, html, "<html><body><p>About Zeta.</p></body></html>", None),
            "https://delta-teste.com.br/robots.txt": (200, txt, "User-agent: OzavSiteEnricher\nDisallow: /equipe\n", None),
            "https://delta-teste.com.br/": (200, html, HOME_DELTA, None),
            "https://delta-teste.com.br/equipe": (200, html, EQUIPE, None),
            "https://delta-teste.com.br/contato": (200, html, CONTATO_ALFA.replace("alfa-teste", "delta-teste"), None),
            "https://eta-teste.com.br/": (302, html, "", "https://www.eta-global.com/br/"),
            "https://www.eta-global.com/br/": (200, html, HOME_ETA, None),
        }

    def __call__(self, url: str) -> es.RespostaBruta:
        self.pedidos.append((self.relogio.agora(), url))
        host = url.split("/")[2]
        if host in self.sem_conexao:
            raise requests.ConnectionError("sem conexão (fixture)")
        status, tipo, corpo, local = self.mapa.get(url, (404, "text/html", "", None))
        return es.RespostaBruta(status, url, tipo, corpo.encode("utf-8"), local)


@pytest.fixture
def coletor():
    rel = Relogio()
    tr = TransporteFalso(rel)
    c = es.Coletor(tr, relogio=rel.agora, dormir=rel.dormir, nome_motor="falso")
    return c, tr


# --------------------------------------------------------------------------- 1. extração

def test_email_de_funcao_entra_e_pessoal_sai():
    assert es.classificar_email("contato@x.com.br") == "funcao"
    assert es.classificar_email("financeiro2@x.com.br") == "funcao"
    assert es.classificar_email("rh.sp@x.com.br") == "funcao"
    assert es.classificar_email("recursos.humanos@x.com.br") == "funcao"
    assert es.classificar_email("maria.souza@x.com.br") == "pessoal"
    assert es.classificar_email("joao@x.com.br") == "pessoal"
    assert es.classificar_email("maria.financeiro@x.com.br") == "pessoal"  # nome + função também sai
    assert es.classificar_email("noreply@x.com.br") == "pessoal"


def test_sinais_nao_confundem_software_nem_verbo():
    p = es.extrair_html("<p>Exportação de relatórios em PDF e importação de planilhas. O que importa é o cliente.</p>",
                        "https://x.com.br/")
    s = es.achar_sinais([p])
    assert s["sinal_importa"] == 0 and s["sinal_exporta"] == 0 and s["n_sinais"] == 0


def test_lugares_lista_fechada_e_janela_curta():
    p = es.extrair_html("<p>Temos escritórios em São Paulo e Miami, liderados por Orlando Lima.</p>", "https://x.com.br/")
    s = es.achar_sinais([p])
    assert s["escritorios"] == "São Paulo; Miami (EUA)"   # Orlando ficou fora: a janela para em "liderados"
    assert s["escritorio_exterior"] == 1


def test_idioma_e_internas():
    assert es.idioma("Somos uma empresa com soluções para nossos clientes e também serviços para você") == "pt"
    assert es.idioma("We are a company with services and solutions for our customers and you") == "en"
    assert es.idioma("abc") == "indefinido"
    links = [("https://www.x.com.br/sobre-nos/", "Sobre"), ("https://www.x.com.br/contato", "Fale"),
             ("https://www.x.com.br/blog/contato-com-o-cliente-um-guia-longo", "Post"),
             ("https://outro.com/contato", "externo"), ("https://www.x.com.br/vagas.pdf", "pdf"),
             ("https://www.x.com.br/carreiras", "Carreiras"), ("https://www.x.com.br/time", "Time")]
    escolhidas = es.escolher_internas(links, "https://www.x.com.br/", 3)
    assert escolhidas == [("https://www.x.com.br/contato", "contato"), ("https://www.x.com.br/sobre-nos/", "sobre"),
                          ("https://www.x.com.br/carreiras", "carreiras")]


# --------------------------------------------------------------------------- 2. coletor

def test_site_completo_com_redirecionamento(coletor):
    c, tr = coletor
    r = c.processar("alfa-teste.com.br")
    assert r["status_site"] == "ok" and r["site"] == "https://www.alfa-teste.com.br/"
    assert r["paginas"] == "home;contato;sobre;carreiras" and r["paginas_lidas"] == 4
    assert r["emails_funcao"] == "contato@alfa-teste.com.br;comercial@alfa-teste.com.br;financeiro2@alfa-teste.com.br"
    assert r["emails_funcao_outros_dominios"] == "rh@grupo-alfa.com"
    assert r["n_emails_pessoais_descartados"] == 2          # maria.souza@ e joao.silva@ (o do <script> nem é lido)
    assert r["telefones_br"] == "+55 11 3456-7890" and r["telefones_exterior"] == "+1 305-577-1234"
    assert r["linkedin_empresa"] == "https://www.linkedin.com/company/alfa-teste/"
    assert r["plataforma_vagas"] == "Gupy"
    assert (r["sinal_exporta"], r["sinal_importa"], r["sinal_global"], r["sinal_clientes_exterior"]) == (1, 1, 1, 1)
    assert r["sinal_matriz_exterior"] == 1 and r["matriz_em"] == "Nova York (EUA)"
    assert r["escritorios"] == "São Paulo; Miami (EUA); Lisboa" and r["escritorio_exterior"] == 1
    assert r["menciona_cambio"] == 1
    assert r["vagas_alvo"] == "analista de comercio exterior; coordenador(a) de tesouraria"
    assert r["idioma"] == "pt" and r["lang_html"] == "pt-BR" and r["hreflangs"] == "en;pt-br"
    assert r["n_sinais"] == 9

    urls = [u for _, u in tr.pedidos]
    assert not any(u.endswith("/equipe") for u in urls), "robots.txt proíbe /equipe"
    assert not any(u.endswith((".pdf", "/blog")) for u in urls)
    paginas = [u for u in urls if not u.endswith("robots.txt")]
    assert len(paginas) == 5  # a home sem www (301) + 4 páginas
    # ritmo: >= 1 s entre quaisquer duas requisições do domínio e >= 2 s (Crawl-delay) depois do robots.txt
    tempos = [t for t, _ in tr.pedidos]
    gaps = [b - a for a, b in zip(tempos, tempos[1:])]
    assert min(gaps) >= 1.0
    assert all(g >= 2.0 for g in gaps[1:])


def test_falhas_e_robots(coletor):
    c, tr = coletor
    assert c.processar("beta-teste.com.br")["status_site"] == "robots.txt bloqueia"
    assert c.processar("gama-teste.com")["status_site"] == "robots.txt inacessível"
    assert c.processar("epsilon-teste.com.br")["status_site"] == "sem resposta"
    urls = [u for _, u in tr.pedidos]
    assert [u for u in urls if "beta-teste" in u] == ["https://beta-teste.com.br/robots.txt"]
    assert all(u.endswith("/robots.txt") for u in urls if "gama-teste" in u)

    delta = c.processar("delta-teste.com.br")
    assert delta["paginas"] == "home;contato"       # /equipe proibida para o nosso user-agent
    assert not any(u.endswith("delta-teste.com.br/equipe") for _, u in tr.pedidos)

    zeta = c.processar("zeta-teste.com")              # robots.txt 404 = pode tudo
    assert zeta["status_site"] == "ok" and zeta["idioma"] == "en"
    assert zeta["sinal_comex"] == 1 and zeta["sinal_matriz_exterior"] == 1 and zeta["matriz_em"] == "Roterdã"
    assert zeta["escritorios"] == "Londres; Miami (EUA)" and zeta["sinal_clientes_exterior"] == 1

    eta = c.processar("eta-teste.com.br")
    assert eta["redireciona_para"] == "www.eta-global.com" and eta["site"] == "https://www.eta-global.com/br/"


def test_teto_de_paginas(coletor):
    c, tr = coletor
    c.max_paginas = 2
    r = c.processar("alfa-teste.com.br")
    assert r["paginas"] == "home;contato"


# --------------------------------------------------------------------------- 3. rodada completa + privacidade

def _top1000(caminho: Path) -> None:
    cols = ["cnpj", "razao_social", "nome_fantasia", "uf", "dominio_email", "marca_email", "nota"]
    linhas = [
        ["11111111000191", "ALFA SOFTWARE TESTE LTDA", "ALFA", "SP", "alfa-teste.com.br", "próprio", "84.3"],
        ["11111111000272", "ALFA SOFTWARE TESTE LTDA", "ALFA RJ", "RJ", "alfa-teste.com.br", "próprio", "80.0"],
        ["22222222000101", "BETA TESTE LTDA", "", "SP", "beta-teste.com.br", "próprio", "70.0"],
        ["33333333000101", "ZETA LOGISTICA TESTE LTDA", "", "SC", "zeta-teste.com", "próprio", "66.0"],
        ["44444444000101", "CONTADOR TESTE LTDA", "", "SP", "contabil-exemplo.com.br", "provável contador (domínio em 26 empresas)", "60.0"],
        ["55555555000101", "SEM EMAIL TESTE LTDA", "", "SP", "", "", "50.0"],
        ["66666666000101", "GMAIL TESTE LTDA", "", "SP", "gmail.com", "provável contador (domínio genérico)", "40.0"],
    ]
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(linhas)


def test_rodada_completa_sem_dado_pessoal(coletor, tmp_path: Path):
    c, tr = coletor
    entrada = tmp_path / "top1000.csv"
    _top1000(entrada)
    destino = es.rodar(entrada, tmp_path / "saida", workers=1, coletor=c)
    with open(destino, encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    assert len(linhas) == 7
    st = {l["cnpj"]: l["status_site"] for l in linhas}
    assert st["11111111000191"] == st["11111111000272"] == "ok"      # mesmo domínio, visitado uma vez
    assert st["22222222000101"] == "robots.txt bloqueia"
    assert st["44444444000101"] == "não visitado: domínio genérico ou de contador"
    assert st["55555555000101"] == "sem e-mail cadastral"
    assert sum(1 for _, u in tr.pedidos if u == "https://www.alfa-teste.com.br/") == 1
    rel = (tmp_path / "saida" / "relatorio.md").read_text(encoding="utf-8")
    assert "| Sites lidos | 2 |" in rel and "ALFA" in rel

    for arq in (tmp_path / "saida").iterdir():
        dados = arq.read_bytes().lower()
        for proibido in (b"maria", b"souza", b"joao", "joão".encode(), b"silva", b"linkedin.com/in/", b"onetrust"):
            assert proibido not in dados, (arq.name, proibido)

    # rodar de novo reaproveita o cache e não pede nada
    n = len(tr.pedidos)
    es.rodar(entrada, tmp_path / "saida", workers=1, coletor=c)
    assert len(tr.pedidos) == n


# --------------------------------------------------------------------------- 4. HTTP de verdade

HOME_LOCAL = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"></head><body>
<p>Importadora Local Teste. Somos importadores de máquinas.{TEXTO_LONGO}</p>
<a href="/contato">Contato</a> <a href="/privado/equipe">Equipe</a> <a href="/arquivo.txt">Sobre (texto)</a>
<script>document.body.insertAdjacentHTML("beforeend", "<p>Exportamos para 30 países.</p>")</script>
</body></html>"""


class _Servidor:
    def __init__(self):
        self.pedidos: list[tuple[float, str]] = []
        paginas = {
            "/robots.txt": ("text/plain", "User-agent: *\nDisallow: /privado\n"),
            "/": ("text/html; charset=utf-8", HOME_LOCAL),
            "/contato": ("text/html; charset=utf-8", "<html><body><p>comercial@127.0.0.1 · (21) 2222-3333</p></body></html>"),
            "/arquivo.txt": ("text/plain", "não é HTML"),
            "/grande": ("text/html", "<p>" + "x" * 3_000_000 + "</p>"),
        }
        srv = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):  # noqa: N802
                import time as _t
                srv.pedidos.append((_t.monotonic(), self.path))
                tipo, corpo = paginas.get(self.path, ("text/html", None))
                if corpo is None:
                    self.send_response(404)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                dados = corpo.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", tipo)
                self.send_header("Content-Length", str(len(dados)))
                self.end_headers()
                self.wfile.write(dados)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.dominio = f"127.0.0.1:{self.httpd.server_port}"


@pytest.fixture
def servidor():
    s = _Servidor()
    yield s
    s.httpd.shutdown()
    s.httpd.server_close()


def test_http_de_verdade_com_requests(servidor):
    tr = es.TransporteLeve()
    c = es.Coletor(tr, intervalo=0.2, nome_motor="leve")
    r = c.processar(servidor.dominio)       # https falha (servidor só fala http) e cai para http://
    assert r["status_site"] == "ok" and r["site"] == f"http://{servidor.dominio}/"
    assert r["paginas"] == "home;contato"   # /privado proibido e /arquivo.txt não é HTML
    assert r["telefones_br"] == "+55 21 2222-3333" and r["sinal_importa"] == 1
    assert r["sinal_exporta"] == 0          # o texto que só o JavaScript escreve não aparece no motor leve
    caminhos = [p for _, p in servidor.pedidos]
    assert not any(p.startswith("/privado") for p in caminhos)
    tempos = [t for t, _ in servidor.pedidos]
    assert min(b - a for a, b in zip(tempos, tempos[1:])) >= 0.19
    grande = tr(f"http://{servidor.dominio}/grande")
    assert grande.truncado and len(grande.corpo) == es.MAX_BYTES_PAGINA


@pytest.mark.skipif(not os.environ.get("ENRIQUECER_CDP_URL"), reason="defina ENRIQUECER_CDP_URL para testar o motor crawl4ai")
def test_motor_crawl4ai_renderiza_javascript(servidor):
    pytest.importorskip("crawl4ai")
    tr = es.TransporteCrawl4AI(os.environ["ENRIQUECER_CDP_URL"])
    try:
        c = es.Coletor(tr, es.TransporteLeve(), intervalo=0.2, nome_motor="crawl4ai")
        r = c.processar(servidor.dominio)
    finally:
        tr.fechar()
    assert r["status_site"] == "ok" and r["motor"] == "crawl4ai"
    assert r["sinal_exporta"] == 1          # "Exportamos para 30 países" só existe depois do JavaScript
    assert r["paginas"] == "home;contato"
    assert not any(p.startswith("/privado") for _, p in servidor.pedidos)
