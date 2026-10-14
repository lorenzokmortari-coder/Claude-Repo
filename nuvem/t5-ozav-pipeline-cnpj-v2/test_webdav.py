"""Testes da fonte WebDAV (v2) contra um servidor WebDAV FALSO que roda no próprio pytest.

O servidor imita o compartilhamento público do Nextcloud da Receita: exige Basic auth com
(token, senha vazia), responde PROPFIND Depth 1 com 207 Multi-Status (inclusive o propstat
404 que o Nextcloud manda para pastas) e serve GET. Ele pode cortar a conexão no meio do
download ou mandar um arquivo menor que o anunciado, para testar o "apaga e baixa de novo".
Também recusa Range: o cliente não pode pedir retomada.

Os .zip são os mesmos arquivos SINTÉTICOS do test_pipeline.py (nenhum dado real).
Rodar: python -m pytest -q
"""
from __future__ import annotations

import base64
import datetime as dt
import shutil
import threading
import zipfile
from email.utils import formatdate
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

import pytest

import pipeline as pl
from test_pipeline import HOJE, _ler, montar_mes

PREFIXO = "/public.php/webdav/"
TOKEN = "TOKENFALSO123"


class ServidorDAV:
    def __init__(self, raiz: Path, token: str = TOKEN):
        self.raiz = raiz.resolve()
        self.token = token
        self.pedidos: list[tuple[str, str, str | None]] = []  # (método, caminho, cabeçalho Range)
        self.cortes: dict[str, int] = {}   # nome do arquivo -> quantos GETs cortam a conexão no meio
        self.curtos: dict[str, int] = {}   # nome do arquivo -> quantos GETs mandam um corpo menor
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    @property
    def url_cnpj(self) -> str:
        return f"http://127.0.0.1:{self.httpd.server_port}{PREFIXO}Dados/Cadastros/CNPJ/"

    def gets(self, nome: str) -> int:
        return sum(1 for m, c, _ in self.pedidos if m == "GET" and unquote(c).endswith("/" + nome))

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()

    def _handler(srv):  # noqa: N805 - o handler fecha sobre o servidor
        class H(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):
                pass

            def _corpo_vazio(self, status: int, extra: dict | None = None) -> None:
                self.send_response(status)
                for k, v in (extra or {}).items():
                    self.send_header(k, v)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def _alvo(self) -> Path | None:
                caminho = unquote(urlsplit(self.path).path)
                if not caminho.startswith(PREFIXO):
                    return None
                alvo = (srv.raiz / caminho[len(PREFIXO):]).resolve()
                if alvo != srv.raiz and srv.raiz not in alvo.parents:
                    return None
                return alvo

            def _autenticado(self) -> bool:
                esperado = "Basic " + base64.b64encode(f"{srv.token}:".encode()).decode()
                if self.headers.get("Authorization") == esperado:
                    return True
                self._corpo_vazio(401, {"WWW-Authenticate": 'Basic realm="Nextcloud"'})
                return False

            def do_PROPFIND(self):  # noqa: N802
                srv.pedidos.append(("PROPFIND", self.path, self.headers.get("Range")))
                self.rfile.read(int(self.headers.get("Content-Length") or 0))
                if not self._autenticado():
                    return
                alvo = self._alvo()
                if alvo is None or not alvo.exists():
                    return self._corpo_vazio(404)
                entradas = [alvo]
                if alvo.is_dir() and self.headers.get("Depth", "1") != "0":
                    entradas += sorted(alvo.iterdir())
                corpo = multistatus(srv.raiz, entradas).encode("utf-8")
                self.send_response(207)
                self.send_header("Content-Type", "application/xml; charset=utf-8")
                self.send_header("Content-Length", str(len(corpo)))
                self.end_headers()
                self.wfile.write(corpo)

            def do_GET(self):  # noqa: N802
                srv.pedidos.append(("GET", self.path, self.headers.get("Range")))
                if not self._autenticado():
                    return
                if self.headers.get("Range"):
                    return self._corpo_vazio(400)  # o servidor real não aceita retomar
                alvo = self._alvo()
                if alvo is None or not alvo.is_file():
                    return self._corpo_vazio(404)
                dados = alvo.read_bytes()
                if srv.cortes.get(alvo.name, 0) > 0:
                    srv.cortes[alvo.name] -= 1
                    self.send_response(200)
                    self.send_header("Content-Length", str(len(dados)))
                    self.end_headers()
                    self.wfile.write(dados[: len(dados) // 2])
                    self.wfile.flush()
                    self.close_connection = True
                    return
                if srv.curtos.get(alvo.name, 0) > 0:
                    srv.curtos[alvo.name] -= 1
                    dados = dados[: len(dados) // 3]
                self.send_response(200)
                self.send_header("Content-Type", "application/zip")
                self.send_header("Content-Length", str(len(dados)))
                self.end_headers()
                self.wfile.write(dados)

        return H


def multistatus(raiz: Path, entradas: list[Path]) -> str:
    """Resposta no formato do Nextcloud (namespaces d:, s:, oc:, nc:)."""
    partes = ['<?xml version="1.0"?>\n<d:multistatus xmlns:d="DAV:" xmlns:s="http://sabredav.org/ns" '
              'xmlns:oc="http://owncloud.org/ns" xmlns:nc="http://nextcloud.org/ns">']
    for p in entradas:
        rel = p.relative_to(raiz).as_posix()
        href = PREFIXO + quote(rel) + ("/" if p.is_dir() and rel != "." else "")
        if rel == ".":
            href = PREFIXO
        mod = formatdate(p.stat().st_mtime, usegmt=True)
        if p.is_dir():
            partes.append(
                f"<d:response><d:href>{href}</d:href>"
                f"<d:propstat><d:prop><d:getlastmodified>{mod}</d:getlastmodified>"
                f"<d:resourcetype><d:collection/></d:resourcetype></d:prop>"
                f"<d:status>HTTP/1.1 200 OK</d:status></d:propstat>"
                f"<d:propstat><d:prop><d:getcontentlength/></d:prop>"
                f"<d:status>HTTP/1.1 404 Not Found</d:status></d:propstat></d:response>")
        else:
            partes.append(
                f"<d:response><d:href>{href}</d:href>"
                f"<d:propstat><d:prop><d:getlastmodified>{mod}</d:getlastmodified>"
                f"<d:getcontentlength>{p.stat().st_size}</d:getcontentlength><d:resourcetype/></d:prop>"
                f"<d:status>HTTP/1.1 200 OK</d:status></d:propstat></d:response>")
    partes.append("</d:multistatus>")
    return "".join(partes)


@pytest.fixture(autouse=True)
def sem_espera(monkeypatch):
    monkeypatch.setattr(pl, "ESPERA_BASE_S", 0.0)


@pytest.fixture
def share(tmp_path: Path) -> Path:
    raiz = tmp_path / "share"
    cnpj = raiz / "Dados" / "Cadastros" / "CNPJ"
    montar_mes(cnpj / "2026-09", mes2=False)
    montar_mes(cnpj / "2026-10", mes2=True)
    (cnpj / "2026-11").mkdir()  # mês ainda subindo: só uma tabela
    shutil.copy(cnpj / "2026-10" / "Cnaes.zip", cnpj / "2026-11" / "Cnaes.zip")
    (cnpj / "LEIA-ME.txt").write_text("arquivo solto que não é mês", encoding="utf-8")
    regime = raiz / "Dados" / "Cadastros" / "Regime Tributário" / "2025"
    regime.mkdir(parents=True)
    for ano in (2023, 2024):
        with zipfile.ZipFile(regime / f"Lucro Real {ano}.zip", "w") as z:
            z.writestr(f"lucro_real_{ano}.csv",
                       f"ano,cnpj,cnpj_da_scp,forma_de_tributacao\n{ano},11.111.111/0001-91,,LUCRO REAL\n")
    return raiz


@pytest.fixture
def srv(share: Path):
    with ServidorDAV(share) as s:
        yield s


def test_le_multistatus_do_nextcloud():
    xml = (b'<?xml version="1.0"?><d:multistatus xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns">'
           b'<d:response><d:href>/public.php/webdav/Dados/Cadastros/CNPJ/2026-10/</d:href>'
           b'<d:propstat><d:prop><d:resourcetype><d:collection/></d:resourcetype></d:prop>'
           b'<d:status>HTTP/1.1 200 OK</d:status></d:propstat>'
           b'<d:propstat><d:prop><d:getcontentlength/></d:prop><d:status>HTTP/1.1 404 Not Found</d:status>'
           b'</d:propstat></d:response>'
           b'<d:response><d:href>/public.php/webdav/Dados/Cadastros/CNPJ/2026-10/Estabelecimentos%200.zip</d:href>'
           b'<d:propstat><d:prop><d:getcontentlength>12345</d:getcontentlength><d:resourcetype/>'
           b'<d:getlastmodified>Mon, 13 Oct 2026 10:00:00 GMT</d:getlastmodified></d:prop>'
           b'<d:status>HTTP/1.1 200 OK</d:status></d:propstat></d:response></d:multistatus>')
    itens = pl.ler_multistatus(xml, "https://x.gov.br/public.php/webdav/Dados/Cadastros/CNPJ/2026-10/")
    assert len(itens) == 1  # a própria pasta pedida fica de fora
    i = itens[0]
    assert (i.nome, i.pasta, i.tamanho) == ("Estabelecimentos 0.zip", False, 12345)
    assert i.url == "https://x.gov.br/public.php/webdav/Dados/Cadastros/CNPJ/2026-10/Estabelecimentos%200.zip"


def test_propfind_lista_meses_e_tamanhos_com_auth(srv: ServidorDAV, share: Path):
    dav = pl.WebDAV(srv.url_cnpj, TOKEN)
    raiz = {i.nome: i for i in dav.listar()}
    assert {n for n, i in raiz.items() if i.pasta} == {"2026-09", "2026-10", "2026-11"}
    assert raiz["LEIA-ME.txt"].pasta is False
    assert pl.listar_meses(dav) == ["2026-09", "2026-10", "2026-11"]

    itens = {i.nome: i for i in dav.listar("2026-10/")}
    pasta = share / "Dados" / "Cadastros" / "CNPJ" / "2026-10"
    assert set(itens) == {p.name for p in pasta.iterdir()}
    for nome, item in itens.items():
        assert item.tamanho == (pasta / nome).stat().st_size
    assert all(m != "PROPFIND" or r is None for m, _, r in srv.pedidos)

    with pytest.raises(PermissionError):
        pl.WebDAV(srv.url_cnpj, "token-errado").listar()


def test_acha_o_mes_mais_recente_completo(srv: ServidorDAV, share: Path):
    dav = pl.WebDAV(srv.url_cnpj, TOKEN)
    mes, itens = pl.descobrir_mes(dav)
    assert mes == "2026-10"  # 2026-11 só tem Cnaes.zip
    assert {i.nome for i in itens} >= {"Empresas0.zip", "Empresas1.zip", "Socios0.zip", "Simples.zip"}
    assert pl.descobrir_mes(dav, "2026-09")[0] == "2026-09"
    with pytest.raises(SystemExit):
        pl.descobrir_mes(dav, "2026-12")
    with pytest.raises(SystemExit):
        pl.descobrir_mes(dav, "2026-11")  # pedido explícito de mês incompleto

    # 2026-11 chega com menos partes de Empresas que o mês anterior: ainda incompleto
    cnpj = share / "Dados" / "Cadastros" / "CNPJ"
    for p in (cnpj / "2026-10").iterdir():
        if p.name != "Empresas1.zip":
            shutil.copy(p, cnpj / "2026-11" / p.name)
    assert pl.descobrir_mes(dav)[0] == "2026-10"
    # completou
    shutil.copy(cnpj / "2026-10" / "Empresas1.zip", cnpj / "2026-11" / "Empresas1.zip")
    assert pl.descobrir_mes(dav)[0] == "2026-11"


def test_download_sem_retomada_apaga_e_baixa_de_novo(srv: ServidorDAV, share: Path, tmp_path: Path):
    dav = pl.WebDAV(srv.url_cnpj, TOKEN)
    mes, itens = pl.descobrir_mes(dav)
    trabalho = tmp_path / "trab"
    trabalho.mkdir()
    fonte = pl.FonteWebDAV(trabalho, dav, mes, itens)
    srv.cortes["Socios0.zip"] = 1      # conexão cai no meio
    srv.curtos["Empresas0.zip"] = 2    # servidor manda um arquivo menor que o anunciado, duas vezes
    original = share / "Dados" / "Cadastros" / "CNPJ" / mes
    for nome in ("Socios0.zip", "Empresas0.zip"):
        z = fonte.obter(nome)
        assert z.read_bytes() == (original / nome).read_bytes()
    assert srv.gets("Socios0.zip") == 2
    assert srv.gets("Empresas0.zip") == 3
    assert all(r is None for _, _, r in srv.pedidos), "o cliente nunca pode pedir Range"
    assert not list(trabalho.glob("*.part"))

    # já baixado e com o tamanho certo: não baixa de novo
    fonte.obter("Socios0.zip")
    assert srv.gets("Socios0.zip") == 2


def test_desiste_sem_deixar_lixo(srv: ServidorDAV, tmp_path: Path, monkeypatch):
    monkeypatch.setattr(pl, "TENTATIVAS_DOWNLOAD", 3)
    dav = pl.WebDAV(srv.url_cnpj, TOKEN)
    mes, itens = pl.descobrir_mes(dav)
    trabalho = tmp_path / "trab"
    trabalho.mkdir()
    fonte = pl.FonteWebDAV(trabalho, dav, mes, itens)
    srv.curtos["Simples.zip"] = 99
    with pytest.raises(RuntimeError, match="3 tentativas"):
        fonte.obter("Simples.zip")
    assert srv.gets("Simples.zip") == 3
    assert list(trabalho.iterdir()) == []


def test_ponta_a_ponta_via_webdav(srv: ServidorDAV, tmp_path: Path):
    saida = tmp_path / "saida"
    s9 = pl.rodar("2026-09", saida, webdav=srv.url_cnpj, token=TOKEN, hoje=HOJE)
    srv.cortes["Estabelecimentos0.zip"] = 1
    s = pl.rodar(None, saida, webdav=srv.url_cnpj, token=TOKEN, hoje=HOJE)
    assert (s9.name, s.name) == ("2026-09", "2026-10")

    top = {r["cnpj"]: r for r in _ler(s / "top1000.csv")}
    assert set(top) == {"11111111000191", "22222222000101", "77777777000101", "12121212000101"}
    assert top["22222222000101"]["tipo_socio_estrangeiro"] == "PJ estrangeira"
    assert "WebDAV" in (s / "FONTE.txt").read_text(encoding="utf-8")
    assert "2026-10" in (s / "FONTE.txt").read_text(encoding="utf-8")

    # diff automático contra o mês anterior já processado na mesma pasta
    eventos = {(r["cnpj_basico"], r["evento"]) for r in _ler(s / "novidades.csv")}
    assert eventos == {("22222222", "ganhou_socio_estrangeiro"), ("11111111", "abriu_filial"),
                       ("12121212", "mudou_cnae_principal")}

    # cada zip foi baixado uma vez (o cortado, duas) e nenhum .zip ficou no disco
    assert srv.gets("Estabelecimentos0.zip") == 3  # 1 em 2026-09 + 2 em 2026-10
    assert srv.gets("Empresas0.zip") == 2
    assert not list(saida.rglob("*.zip")) and not list(saida.rglob("*.part"))

    # rodar de novo não refaz nada (mês já processado), a não ser com refazer=True
    n = len(srv.pedidos)
    pl.rodar(None, saida, webdav=srv.url_cnpj, token=TOKEN, hoje=HOJE)
    assert not [p for p in srv.pedidos[n:] if p[0] == "GET"]


def test_manter_zips_reaproveita_na_rodada_seguinte(srv: ServidorDAV, tmp_path: Path):
    saida = tmp_path / "saida"
    s = pl.rodar(None, saida, manter_zips=True, webdav=srv.url_cnpj, token=TOKEN, hoje=HOJE)
    assert (s / "zips" / "Empresas0.zip").exists()
    gets = sum(1 for p in srv.pedidos if p[0] == "GET")
    pl.rodar(None, saida, manter_zips=True, refazer=True, webdav=srv.url_cnpj, token=TOKEN, hoje=HOJE)
    assert sum(1 for p in srv.pedidos if p[0] == "GET") == gets  # nenhum download novo


def test_regime_tributario_pelo_webdav(srv: ServidorDAV, tmp_path: Path):
    s = pl.rodar(None, tmp_path / "saida", regime=True, webdav=srv.url_cnpj, token=TOKEN, hoje=HOJE)
    top = {r["cnpj"]: r for r in _ler(s / "top1000.csv")}
    assert top["11111111000191"]["ano_lucro_real"] == "2024"  # pegou o zip do ano mais recente
    assert srv.gets("Lucro Real 2024.zip") == 1 and srv.gets("Lucro Real 2023.zip") == 0


def test_fonte_local_continua_funcionando(tmp_path: Path):
    pasta = montar_mes(tmp_path / "2026-10", mes2=True)
    s = pl.rodar(None, tmp_path / "saida", pasta, hoje=HOJE)  # mês sai do nome da pasta
    assert s.name == "2026-10"
    assert (s / "top1000.csv").exists()
    assert sorted(p.name for p in pasta.iterdir())[0] == "Cnaes.zip"  # originais intactos
    assert "pasta local" in (s / "FONTE.txt").read_text(encoding="utf-8")


def test_nome_local_recusa_caminho_estranho():
    assert pl.nome_local("Empresas0.zip") == "Empresas0.zip"
    assert pl.nome_local("../../x/Lucro Real 2024.zip") == "Lucro_Real_2024.zip"
    with pytest.raises(ValueError):
        pl.nome_local("..")
    with pytest.raises(ValueError):
        pl.nome_local("Empresas0.exe")
    assert dt.date(2026, 10, 14) == HOJE
