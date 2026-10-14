"""Testes da esteira mensal, de ponta a ponta e sem rede: a Receita vem do gerar_receita.py (dois meses
sintéticos com mudanças plantadas) e os sites vêm de um servidor HTTP local de verdade, que atende cada
domínio falso pelo cabeçalho Host (o transporte usa o servidor como proxy). Nada aqui é dado real.

Rodar: python -m pytest -q test_esteira.py      (leva ~1 min: o ritmo de 1 pedido por segundo por domínio é real)
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import shutil
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import pytest
import requests

import enriquecer_site as es
import esteira as st
import gerar_receita as gr
import pipeline as pl

HOJE = dt.date(2026, 10, 14)
AQUI = Path(__file__).resolve().parent
TEXTO = " Atendemos empresas de todos os portes com tecnologia própria e suporte local." * 6
HTML = "text/html; charset=utf-8"


def pagina(corpo: str, lang: str = "pt-BR") -> tuple[int, str, str]:
    return 200, HTML, f"<!doctype html><html lang=\"{lang}\"><body>{corpo}</body></html>"


LIVRE = (200, "text/plain", "User-agent: *\nAllow: /\n")
SITES = {
    "alfa-teste.com.br": {
        "/robots.txt": LIVRE,
        "/": pagina(f"<h1>Alfa Teste</h1><p>A Alfa é subsidiária brasileira da Alfa Holdings Inc., com sede em Nova York. "
                    f"Trabalhamos com importação de equipamentos e comércio exterior.{TEXTO}</p>"
                    "<a href='/contato'>Contato</a> <a href='/trabalhe-conosco'>Carreiras</a>"),
        "/contato": pagina("<p>Comercial: comercial@alfa-teste.com.br · Diretor: joao.silva@alfa-teste.com.br</p>"),
        "/trabalhe-conosco": pagina("<ul><li>Analista de Comércio Exterior Pleno</li></ul>"),
    },
    "beta-teste.com.br": {"/robots.txt": (200, "text/plain", "User-agent: *\nDisallow: /\n"),
                          "/": pagina(f"<p>Beta.{TEXTO}</p>")},
    "deel-teste.com.br": {"/robots.txt": LIVRE, "/": pagina(f"<p>Deel.{TEXTO}</p>")},
    "gama-teste.com.br": {
        "/robots.txt": LIVRE,
        "/": pagina(f"<p>Gama Agência.{TEXTO}</p><a href='/contato'>Contato</a>"
                    "<a href='https://www.linkedin.com/company/gama-teste/'>LinkedIn</a>"
                    "<a href='https://www.linkedin.com/in/pessoa-ficticia-exemplo'>perfil</a>"),
        "/contato": pagina("<p>contato@gama-teste.com.br · maria.souza@gama-teste.com.br</p>"),
    },
    "delta-teste.com.br": {"/robots.txt": LIVRE, "/": pagina(f"<p>Delta Consultoria.{TEXTO}</p>")},
    "epsilon-teste.com.br": {"/robots.txt": LIVRE,
                             "/": pagina(f"<p>Epsilon Trading. Somos importadores de máquinas.{TEXTO}</p>")},
    "eta-teste.com.br": {"/robots.txt": LIVRE, "/": pagina(f"<p>Eta.{TEXTO}</p>")},
    "iota-teste.com.br": {"/robots.txt": LIVRE, "/": (301, HTML, "http://www.iota-global.com/br/")},
    "www.iota-global.com": {"/robots.txt": LIVRE,
                            "/br/": pagina(f"<p>We are a freight forwarding company headquartered in Rotterdam "
                                           f"with offices in London and Miami.{TEXTO}</p>", "en")},
    "omega08-teste.com.br": {"/robots.txt": LIVRE, "/": (301, HTML, "http://br.ebury.com/omega/")},
    "br.ebury.com": {"/robots.txt": LIVRE, "/omega/": pagina(f"<p>Pagamentos internacionais.{TEXTO}</p>")},
    **{f"omega0{i}-teste.com.br": {"/robots.txt": LIVRE, "/": pagina(f"<p>Omega {i} Sistemas.{TEXTO}</p>")}
       for i in range(1, 5)},
}


class ServidorSites:
    """Proxy HTTP local que serve os sites sintéticos pelo host pedido. HTTPS (CONNECT) é recusado, então o
    coletor cai para http:// como num site sem certificado. Registra (hora, método, host, caminho)."""

    def __init__(self):
        self.pedidos: list[tuple[float, str, str, str]] = []
        srv = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _registrar(self, metodo):
                import time
                u = urlsplit(self.path)
                host = (u.netloc or self.headers.get("Host", "")).split(":")[0].lower()
                srv.pedidos.append((time.monotonic(), metodo, host, u.path or "/"))
                return host, u.path or "/"

            def do_CONNECT(self):  # noqa: N802
                self._registrar("CONNECT")
                self.send_response(405)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def do_POST(self):  # noqa: N802
                self._registrar("POST")
                self.send_response(405)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def do_GET(self):  # noqa: N802
                host, caminho = self._registrar("GET")
                site = SITES.get(host)
                if site is None:
                    self.send_response(502)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                status, tipo, corpo = site.get(caminho, (404, HTML, ""))
                self.send_response(status)
                if status in (301, 302):
                    self.send_header("Location", corpo)
                    corpo = ""
                dados = corpo.encode("utf-8")
                self.send_header("Content-Type", tipo)
                self.send_header("Content-Length", str(len(dados)))
                self.end_headers()
                self.wfile.write(dados)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.httpd.server_port}"

    def hosts(self, metodo: str = "GET") -> set[str]:
        return {h for _, m, h, _ in self.pedidos if m == metodo}

    def fechar(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class TransporteProxy(es.TransporteLeve):
    """O transporte leve de verdade (requests), só que passando pelo servidor local."""

    def __init__(self, proxy: str, cair_depois: int | None = None):
        super().__init__(timeout=(3, 5))
        self.proxy, self.cair_depois, self.n = proxy, cair_depois, 0
        self.lock = threading.Lock()
        self.enviados: list[tuple[float, str]] = []      # (hora em que o pedido saiu, host), do lado do coletor

    def _sessao(self) -> requests.Session:
        s = super()._sessao()
        s.trust_env = False                      # não usar o proxy do ambiente
        s.proxies = {"http": self.proxy, "https": self.proxy}
        return s

    def __call__(self, url):
        import time
        with self.lock:
            self.enviados.append((time.monotonic(), urlsplit(url).netloc.lower()))
            self.n += 1
            if self.cair_depois is not None and self.n > self.cair_depois:
                raise Queda("a luz caiu no meio da rodada (teste)")
        return super().__call__(url)


class Queda(BaseException):
    """Simula o processo morrendo (não é uma exceção que o coletor trata como erro de site)."""


def config(tmp: Path, **troca) -> Path:
    texto = (AQUI / "icp.ini").read_text(encoding="utf-8")
    texto = texto.replace("candidatos = 1500", "candidatos = 20").replace("top = 1000", "top = 10")
    texto = texto.replace("arquivo = concorrentes.csv", f"arquivo = {AQUI / 'concorrentes.csv'}")
    texto = texto.replace("workers = 6", "workers = 16")
    for chave, valor in troca.items():
        linhas = [f"{chave} = {valor}" if l.split("=")[0].strip() == chave else l for l in texto.splitlines()]
        texto = "\n".join(linhas)
    destino = tmp / "icp.ini"
    destino.write_text(texto, encoding="utf-8")
    return destino


def ler(p: Path) -> list[dict]:
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def dois_meses(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("esteira")
    gr.gerar(tmp / "zips" / "2026-09")
    gr.gerar(tmp / "zips" / "2026-10", mes2=True)
    srv = ServidorSites()
    cfg = config(tmp)
    t = TransporteProxy(srv.url)
    s9 = st.rodar("2026-09", tmp / "zips" / "2026-09", tmp / "saida", cfg, transporte=t, hoje=HOJE)
    n9, e9 = len(srv.pedidos), len(t.enviados)
    s10 = st.rodar("2026-10", tmp / "zips" / "2026-10", tmp / "saida", cfg, transporte=t, hoje=HOJE)
    yield {"tmp": tmp, "srv": srv, "cfg": cfg, "s9": s9, "s10": s10, "n9": n9, "e9": e9, "t": t}
    srv.fechar()


# --------------------------------------------------------------------------- ponta a ponta

def test_saidas_do_mes(dois_meses):
    s10 = dois_meses["s10"]
    top = ler(s10 / "top1000.csv")
    assert len(top) == 10 and [int(r["posicao"]) for r in top] == list(range(1, 11))
    assert list(top[0].keys()) == st.COLUNAS_TOP
    por = {r["razao_social"]: r for r in top}
    alfa = por["ALFA SOFTWARE TESTE LTDA"]
    assert top[0]["razao_social"] == "IOTA CARGAS TESTE LTDA"          # capital subiu para 50 mi e o site tem 3 sinais
    assert alfa["posicao"] == "2" and float(alfa["nota_site"]) >= 50
    assert alfa["email_funcao"] == "comercial@alfa-teste.com.br"
    assert "matriz no exterior" in alfa["motivo"] and "PJ estrangeira (ALFA HOLDINGS INC" in alfa["motivo"]
    assert float(alfa["nota"]) == pytest.approx(0.7 * float(alfa["nota_cnpj"]) + 0.3 * float(alfa["nota_site"]), abs=0.06)
    kappa = por["KAPPA TI TESTE LTDA"]                      # Gmail: o site não é visitado
    assert kappa["site"] == "" and kappa["status_site"].startswith("não visitado")
    assert por["BETA LOGISTICA TESTE LTDA"]["status_site"] == "robots.txt bloqueia"
    assert "IOTA CARGAS TESTE LTDA" in por and "Roterdã" in por["IOTA CARGAS TESTE LTDA"]["motivo"]
    notas = [float(r["nota"]) for r in top]
    assert notas == sorted(notas, reverse=True)

    crm = [json.loads(l) for l in (s10 / "crm.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(crm) == 10 and crm[1]["cnpj"] == alfa["cnpj"] and crm[1]["id_externo"] == alfa["cnpj"]
    assert set(crm[0]) == {"id_externo", "mes", "posicao", "nome", "nome_fantasia", "cnpj", "site", "email_funcao",
                           "emails_funcao", "nota", "motivo", "origem"}
    assert all(r["mes"] == "2026-10" for r in crm)


def test_concorrentes_ficam_fora(dois_meses):
    s10 = dois_meses["s10"]
    nomes = {r["razao_social"] for r in ler(s10 / "top1000.csv")}
    exc = {r["razao_social"]: r for r in ler(s10 / "excluidos.csv")}
    assert "DEEL BRASIL TESTE LTDA" not in nomes and "Deel" in exc["DEEL BRASIL TESTE LTDA"]["motivo"]
    assert "ZULU SERVICOS DIGITAIS TESTE LTDA" not in nomes
    assert "domínio ebury.com" in exc["ZULU SERVICOS DIGITAIS TESTE LTDA"]["motivo"]
    assert "OMEGA08 SISTEMAS TESTE LTDA" not in nomes          # o site redireciona para o domínio de um concorrente
    assert "ebury.com" in exc["OMEGA08 SISTEMAS TESTE LTDA"]["motivo"]
    hosts = dois_meses["srv"].hosts()
    assert "deel-teste.com.br" not in hosts and "ebury.com" not in hosts   # concorrente nem é visitado


def test_robots_ritmo_e_nada_alem_de_get(dois_meses):
    srv = dois_meses["srv"]
    assert {(h, c) for _, m, h, c in srv.pedidos if h == "beta-teste.com.br" and m == "GET"} == {("beta-teste.com.br", "/robots.txt")}
    assert srv.hosts("POST") == set()
    assert {m for _, m, _, _ in srv.pedidos} <= {"GET", "CONNECT"}
    # o ritmo é medido na saída do pedido (o que o limitador controla); no servidor local a chegada tem atraso
    # variável de fila de conexão. Cada mês é uma rodada própria, com o seu limitador.
    t = dois_meses["t"]
    for rodada in (t.enviados[:dois_meses["e9"]], t.enviados[dois_meses["e9"]:]):
        por_dominio: dict[str, list[float]] = {}
        for hora, h in rodada:
            por_dominio.setdefault(h.removeprefix("www."), []).append(hora)
        assert len(por_dominio) >= 12
        for h, ts in por_dominio.items():
            ts.sort()
            if len(ts) > 1:
                assert min(b - a for a, b in zip(ts, ts[1:])) >= 0.99, h


def test_sem_dado_pessoal_nem_linkedin(dois_meses):
    for s in (dois_meses["s9"], dois_meses["s10"]):
        for nome in ("top1000.csv", "crm.jsonl", "novidades.md", "excluidos.csv", "mudancas.csv", "RODADA.md"):
            dados = (s / nome).read_bytes().lower()
            for proibido in (b"pessoa ficticia", b"outra pessoa", b"joao.silva", b"maria.souza", b"linkedin"):
                assert proibido not in dados, (nome, proibido)


def test_novidades_do_mes(dois_meses):
    nov = (dois_meses["s10"] / "novidades.md").read_text(encoding="utf-8")
    assert "Comparado com 2026-09" in nov
    entrou = nov.split("## Entraram")[1].split("## Saíram")[0]
    saiu = nov.split("## Saíram")[1].split("## Mudaram")[0]
    mudou = nov.split("## Mudaram")[1].split("## Eventos")[0]
    assert "EPSILON TRADING TESTE LTDA" in entrou
    assert "ETA SOFTWARE TESTE LTDA" in saiu and "saiu da base qualificada" in saiu
    assert "IOTA CARGAS TESTE LTDA" in mudou and "nota" in mudou
    assert "ganhou_socio_estrangeiro: EPSILON TRADING TESTE LTDA" in nov
    assert "## Vigia de concorrentes" in nov and "Sem retrato do vigia" in nov
    primeiro = (dois_meses["s9"] / "novidades.md").read_text(encoding="utf-8")
    assert "Primeiro mês da esteira" in primeiro
    eventos = {(r["evento"], r["razao_social"]) for r in ler(dois_meses["s10"] / "mudancas.csv")}
    assert ("entrou", "EPSILON TRADING TESTE LTDA") in eventos and ("saiu", "ETA SOFTWARE TESTE LTDA") in eventos


def test_rodar_de_novo_nao_refaz_nada(dois_meses, monkeypatch):
    s10, srv = dois_meses["s10"], dois_meses["srv"]
    antes = {n: (s10 / n).read_bytes() for n in ("top1000.csv", "crm.jsonl", "excluidos.csv")}
    n = len(srv.pedidos)
    monkeypatch.setattr(pl, "rodar", lambda *a, **k: pytest.fail("refez a etapa cnpj"))
    st.rodar("2026-10", dois_meses["tmp"] / "zips" / "2026-10", dois_meses["tmp"] / "saida", dois_meses["cfg"],
             transporte=dois_meses["t"], hoje=HOJE)
    assert len(srv.pedidos) == n                                  # nenhum site visitado de novo
    assert {n: (s10 / n).read_bytes() for n in antes} == antes
    estado = json.loads((s10 / "estado.json").read_text(encoding="utf-8"))
    assert set(estado["etapas"]) == {"cnpj", "icp", "site", "nota", "saidas"}


def test_icp_editado_muda_o_filtro_sem_refazer_o_cnpj(dois_meses, monkeypatch, tmp_path):
    saida = tmp_path / "saida"
    shutil.copytree(dois_meses["tmp"] / "saida" / "2026-10", saida / "2026-10")
    cfg = config(tmp_path, ufs_excluir="AM")
    monkeypatch.setattr(pl, "rodar", lambda *a, **k: pytest.fail("refez a etapa cnpj"))
    s = st.rodar("2026-10", tmp_path / "nao-existe", saida, cfg, transporte=dois_meses["t"], hoje=HOJE)
    exc = {r["razao_social"]: r for r in ler(s / "excluidos.csv")}
    assert exc["DELTA CONSULTORIA TESTE LTDA"]["tipo"] == "fora do ICP" and "AM" in exc["DELTA CONSULTORIA TESTE LTDA"]["motivo"]
    assert "DELTA CONSULTORIA TESTE LTDA" not in {r["razao_social"] for r in ler(s / "top1000.csv")}


# --------------------------------------------------------------------------- retomada

def test_retomada_depois_de_cair_no_meio(tmp_path, dois_meses):
    gr.gerar(tmp_path / "zips" / "2026-10", mes2=True)
    srv = ServidorSites()
    try:
        cfg = config(tmp_path, workers="2")
        with pytest.raises(Queda):
            st.rodar("2026-10", tmp_path / "zips" / "2026-10", tmp_path / "saida", cfg,
                     transporte=TransporteProxy(srv.url, cair_depois=25), hoje=HOJE)
        destino = tmp_path / "saida" / "2026-10" / "esteira"
        cache = [json.loads(l)["dominio"] for l in (destino / "site" / "cache_sites.jsonl").read_text(encoding="utf-8").splitlines()]
        assert 0 < len(cache) < 14 and not (destino / "top1000.csv").exists()
        homes_antes = {h for _, m, h, c in srv.pedidos if m == "GET" and c == "/" and h in cache}
        n = len(srv.pedidos)
        st.rodar("2026-10", tmp_path / "zips" / "2026-10", tmp_path / "saida", cfg,
                 transporte=TransporteProxy(srv.url), hoje=HOJE)
        depois = [h for _, m, h, c in srv.pedidos[n:] if m == "GET"]
        assert not (homes_antes & set(depois))                    # o que terminou não é visitado de novo
    finally:
        srv.fechar()
    ref = [(r["cnpj"], r["nota"]) for r in ler(dois_meses["s10"] / "top1000.csv")]
    assert [(r["cnpj"], r["nota"]) for r in ler(destino / "top1000.csv")] == ref   # mesmo resultado de uma rodada limpa


# --------------------------------------------------------------------------- vigia do BC

def test_bloco_do_vigia_e_exclusao_pelo_cadastro_do_bc(dois_meses, tmp_path):
    retratos = tmp_path / "retratos"
    retratos.mkdir()
    cab = "cnpj8,nome_entidade,segmento\n"
    (retratos / "2026-09-30.csv").write_text(cab + "12345678,CAMBIO ANTIGA TESTE,CORRETORA DE CAMBIO\n", encoding="utf-8")
    (retratos / "2026-10-13.csv").write_text(cab + "12345678,CAMBIO ANTIGA TESTE,CORRETORA DE CAMBIO\n"
                                             "50000001,OMEGA01 SISTEMAS TESTE LTDA,INSTITUICAO DE PAGAMENTO\n", encoding="utf-8")
    saida = tmp_path / "saida"
    shutil.copytree(dois_meses["tmp"] / "saida" / "2026-10", saida / "2026-10")
    cfg = config(tmp_path, pasta_vigia_bc=str(retratos))
    s = st.rodar("2026-10", tmp_path / "nao-existe", saida, cfg, transporte=dois_meses["t"], hoje=HOJE)
    nov = (s / "novidades.md").read_text(encoding="utf-8")
    assert "De 2026-09-30 a 2026-10-13" in nov and "- entrou: OMEGA01 SISTEMAS TESTE LTDA (50000001)" in nov
    exc = {r["razao_social"]: r["motivo"] for r in ler(s / "excluidos.csv")}
    assert "supervisionada pelo BC" in exc["OMEGA01 SISTEMAS TESTE LTDA"]


# --------------------------------------------------------------------------- unidades

def test_dominio_registravel():
    assert st.registravel("https://br.ebury.com/") == "ebury.com"
    assert st.registravel("https://www.c6bank.com.br/") == "c6bank.com.br"
    assert st.registravel("contato@alfa-teste.com.br") == "alfa-teste.com.br"
    assert st.registravel("www.iota-global.com:8080") == "iota-global.com"


def test_nome_de_concorrente_casa_palavra_inteira_e_evita_palavra_comum():
    conc = st.ler_concorrentes(AQUI / "concorrentes.csv", st.ler_config(AQUI / "icp.ini")["niveis"])
    extra = {"raizes": {}, "dominios": {}}

    def m(razao, dominio=""):
        return st.motivo_concorrente({"cnpj": "12345678000100", "razao_social": razao, "nome_fantasia": "",
                                      "dominio_email": dominio}, conc, extra, set())
    assert m("DEEL BRASIL SERVICOS LTDA") and m("DLOCAL BRASIL LTDA") and m("AIRWALLEX BRASIL LTDA")
    assert m("BEXS TECNOLOGIA LTDA")                              # nome antigo, "(ex-Bexs ...)"
    assert m("NEUTRA LTDA", "financeiro@wise.com")                # pelo domínio
    assert m("INTER TRANSPORTES LTDA") is None                    # "Inter" sozinho é palavra comum
    assert m("FRENTE FRIA LOGISTICA LTDA") is None
    assert m("WISEMAN CONSULTORIA LTDA") is None                  # palavra inteira, não pedaço
    assert m("DEELIGHT SOFTWARE LTDA") is None


def test_exclusao_extra_do_dono(tmp_path):
    p = tmp_path / "extra.csv"
    p.write_text("cnpj_raiz,dominio,motivo\n11.111.111,,cliente atual\n,parceiro-teste.com.br,parceiro\n", encoding="utf-8")
    extra = st.ler_exclusao_extra(p)
    vazio = {"dominios": {}, "nomes": []}
    assert "cliente atual" in st.motivo_concorrente({"cnpj": "11111111000100", "razao_social": "X"}, vazio, extra, set())
    assert "parceiro" in st.motivo_concorrente({"cnpj": "2" * 14, "razao_social": "Y", "dominio_email": "parceiro-teste.com.br"},
                                               vazio, extra, set())


def test_ritmo_minimo_nao_se_afrouxa(tmp_path):
    with pytest.raises(SystemExit):
        st.rodar("2026-10", tmp_path, tmp_path / "saida", intervalo=0.2)
    with pytest.raises(SystemExit):
        st.main(["--mes", "2026-10", "--fonte-local", str(tmp_path), "--intervalo", "0.2"])


def test_sem_codigo_de_crm_nem_mensagem():
    fonte = (AQUI / "esteira.py").read_text(encoding="utf-8").lower()
    for proibido in ("requests.post", ".post(", "smtplib", "whatsapp", "hubspot", "pipedrive", "linkedin.com"):
        assert proibido not in fonte, proibido
