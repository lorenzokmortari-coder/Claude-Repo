#!/usr/bin/env python3
"""
Ozav · lista quente CNPJ · v2 (fonte WebDAV da Receita)
Pipeline Python + DuckDB sobre os Dados Abertos do CNPJ (Receita Federal).

Ideia: achar empresas brasileiras com sócio estrangeiro (de preferência pessoa
jurídica estrangeira = subsidiária), fora do Simples/MEI, matriz ativa, capital
>= R$ 100 mil e CNAE numa lista-alvo (cnae_alvo.csv), e dar uma nota de 0 a 100.

Fonte padrão (v2): o compartilhamento público da Receita (Nextcloud), lido por
WebDAV. PROPFIND Depth 1 lista os meses e os arquivos com tamanho; GET com
autenticação (token do link, senha vazia) baixa cada .zip. O servidor não aceita
retomar download parcial: em qualquer falha o parcial é apagado e o arquivo é
baixado de novo do zero, e no fim o tamanho tem de bater com o da listagem.

Processa um arquivo por vez: baixa o .zip, extrai, filtra com DuckDB para um
.parquet pequeno, apaga o .zip e o .csv. Pico de disco: ~1 zip + 1 csv (< 8 GB).

Uso:
  python pipeline.py listar                     # meses publicados e arquivos do mês mais recente, com tamanho
  python pipeline.py listar --mes 2026-10
  python pipeline.py rodar                      # acha o mês mais recente completo e roda tudo
  python pipeline.py rodar --mes 2026-10        # mês específico
  python pipeline.py rodar --fonte-local PASTA  # usa .zip já baixados (não apaga os originais)
  python pipeline.py rodar --manter-zips        # guarda os .zip em saida/<mes>/zips (rodada seguinte reaproveita)
  python pipeline.py rodar --regime             # tenta usar a base de regime tributário (lucro real)
  python pipeline.py rodar --refazer            # processa de novo um mês que já tem top1000.csv
  python pipeline.py pontuar --mes 2026-10      # só refaz a nota a partir dos .parquet
  python pipeline.py diff --anterior saida/2026-09 --atual saida/2026-10

Saída em saida/<mes>/: top1000.csv, contagens.csv, base_pontuada.parquet, os
.parquet intermediários usados no diff e, se o mês anterior já foi processado na
mesma pasta, novidades.csv (diff automático).

Privacidade: nome de sócio pessoa física nunca é gravado. Do e-mail cadastral só
se guarda o domínio. Nome de sócio só é guardado quando é pessoa jurídica.
"""
from __future__ import annotations

import argparse
import codecs
import datetime as dt
import re
import shutil
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

import duckdb
import requests

# Compartilhamento público da Receita (Nextcloud). O "usuário" do WebDAV é o token do link
# público e a senha é vazia: não é credencial pessoal. Endereço usado com sucesso pela
# conversa 00 no PC em 14/10/2026 (PROPFIND e download do mês 2026-10).
WEBDAV_CNPJ = "https://arquivos.receitafederal.gov.br/public.php/webdav/Dados/Cadastros/CNPJ/"
WEBDAV_TOKEN = "gn672Ad4CF8N6TK"
# Endereço antigo da base de regime tributário (página HTML). NÃO VERIFICADO; só é tentado
# com --regime e quando a pasta de regime não aparece no WebDAV.
FONTE_REGIME_HTML = "https://arquivos.receitafederal.gov.br/dados/cnpj/regime_tributario/"
UA = "Mozilla/5.0 (pipeline-dados-abertos-cnpj; uso analitico)"

AQUI = Path(__file__).resolve().parent
CNAE_ALVO_PADRAO = AQUI / "cnae_alvo.csv"

CAPITAL_MINIMO = 100_000
LIMIAR_DOMINIO_REPETIDO = 20  # domínio de e-mail presente em >= N empresas ativas => provável contador
TOP_N = 1000
DISCO_MINIMO_GB = 8

TENTATIVAS_DOWNLOAD = 6   # cada tentativa recomeça do zero (sem Range)
ESPERA_BASE_S = 2.0       # espera exponencial entre tentativas: 2, 4, 8, 16, 32 s
TENTATIVAS_LISTAGEM = 3

RX_MES = re.compile(r"\d{4}-\d{2}")
# Um mês só conta como publicado quando tem estes quatro tipos de arquivo.
ESSENCIAIS = ("Empresas", "Estabelecimentos", "Socios", "Simples")

# Layout oficial (cnpj-metadados.pdf da Receita). Arquivos sem cabeçalho, separador ';'.
COLS = {
    "empresas": ["cnpj_basico", "razao_social", "natureza_juridica", "qualificacao_responsavel",
                 "capital_social", "porte", "ente_federativo"],
    "estabelecimentos": ["cnpj_basico", "cnpj_ordem", "cnpj_dv", "identificador_matriz_filial",
                         "nome_fantasia", "situacao_cadastral", "data_situacao_cadastral",
                         "motivo_situacao_cadastral", "nome_cidade_exterior", "pais",
                         "data_inicio_atividade", "cnae_fiscal_principal", "cnae_fiscal_secundaria",
                         "tipo_logradouro", "logradouro", "numero", "complemento", "bairro", "cep",
                         "uf", "municipio", "ddd_1", "telefone_1", "ddd_2", "telefone_2", "ddd_fax",
                         "fax", "correio_eletronico", "situacao_especial", "data_situacao_especial"],
    "socios": ["cnpj_basico", "identificador_socio", "nome_socio", "cnpj_cpf_socio",
               "qualificacao_socio", "data_entrada_sociedade", "pais", "representante_legal",
               "nome_representante", "qualificacao_representante", "faixa_etaria"],
    "simples": ["cnpj_basico", "opcao_simples", "data_opcao_simples", "data_exclusao_simples",
                "opcao_mei", "data_opcao_mei", "data_exclusao_mei"],
    "tabela": ["codigo", "descricao"],
}
TABELAS = ["Cnaes", "Motivos", "Municipios", "Naturezas", "Paises", "Qualificacoes"]

DOMINIOS_GENERICOS = {
    "gmail.com", "gmail.com.br", "hotmail.com", "hotmail.com.br", "outlook.com", "outlook.com.br",
    "live.com", "live.com.br", "msn.com", "yahoo.com", "yahoo.com.br", "ymail.com", "rocketmail.com",
    "icloud.com", "me.com", "mac.com", "aol.com", "bol.com.br", "uol.com.br", "terra.com.br",
    "ig.com.br", "superig.com.br", "globo.com", "globomail.com", "r7.com", "zipmail.com.br",
    "oi.com.br", "pop.com.br", "brturbo.com.br", "protonmail.com", "proton.me", "gmx.com",
    "gmx.net", "mail.com", "yandex.com", "zoho.com", "qq.com", "163.com", "126.com",
}

# Sufixos societários fortes para reconhecer pessoa jurídica pelo nome quando a
# qualificação não diz. "SA" solto fica de fora de propósito (Sá é sobrenome).
RX_NOME_PJ = (r"(\bLTD\b|\bLTDA\b|\bLIMITED\b|\bLLC\b|\bL\.L\.C\b|\bINC\b|\bINCORPORATED\b|\bCORP\b|"
              r"\bCORPORATION\b|\bCOMPANY\b|\bGMBH\b|\bS\.A\.?$|\bS/A\b|\bSARL\b|\bS\.R\.L\b|\bSRL\b|"
              r"\bB\.V\b|\bBV$|\bN\.V\b|\bPLC\b|\bPTY\b|\bPTE\b|\bS\.P\.A\b|\bHOLDINGS?\b|\bGROUP\b|"
              r"\bGRUPO\b|\bINTERNATIONAL\b|\bTRUST\b|\bFUND\b|\bPARTNERS\b|\bL\.P\b|\bLIMITADA\b|"
              r"\bSOCIEDAD\b|\bSOCIETE\b|\bGESELLSCHAFT\b|\bAKTIENGESELLSCHAFT\b|\bA/S\b|\bAG$|"
              r"\bKABUSHIKI\b|\bCO\., LTD\b)")

# Concorrentes e setor financeiro: exclui pelo nome (razão social ou fantasia).
RX_EXCLUI_NOME = (r"\b(BANCO|BANK|BANKING|CAMBIO|CAMBIOS|EXCHANGE|FOREX|PAGAMENTO|PAGAMENTOS|"
                  r"PAYMENT|PAYMENTS|PAY|REMESSA|REMESSAS|REMITTANCE|CORRETORA|DTVM|CTVM|FINTECH|"
                  r"CRIPTO|CRYPTO|BITCOIN|BLOCKCHAIN|STABLECOIN|SECURITIZADORA|"
                  r"INSTITUICAO DE PAGAMENTO)\b")

# Natureza jurídica: excluídas pela descrição oficial (tabela Naturezas).
RX_NATUREZA_EXCLUI = (r"EMPRESA PUBLICA|ECONOMIA MISTA|DOMICILIAD[OA] NO EXTERIOR|FUNDO DE INVESTIMENTO|"
                      r"CLUBE|COOPERATIVA|CONSORCIO|GRUPO DE SOCIEDADES|EMPRESARIO|CANDIDATO|"
                      r"CONTA DE PARTICIPACAO")
RX_NATUREZA_FILIAL_ESTRANGEIRA = r"SOCIEDADE ESTRANGEIRA|EMPRESA BINACIONAL"

PORTE = {0: "Não informado", 1: "Micro empresa", 3: "Empresa de pequeno porte", 5: "Demais"}


# --------------------------------------------------------------------------- util

def log(msg: str) -> None:
    print(f"[{dt.datetime.now():%H:%M:%S}] {msg}", flush=True)


def q(path: Path | str) -> str:
    """Literal SQL seguro para caminho."""
    return "'" + str(path).replace("'", "''") + "'"


def sem_acento(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")


def checar_disco(pasta: Path, precisa: int | None = None) -> None:
    livre = shutil.disk_usage(pasta).free
    minimo = max(DISCO_MINIMO_GB * 1e9, (precisa or 0) * 5)  # o CSV extraído é bem maior que o zip
    if livre < minimo:
        log(f"AVISO: só {livre / 1e9:.1f} GB livres em {pasta}; recomendo {minimo / 1e9:.0f} GB.")


def sessao() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = UA
    return s


def nome_local(nome: str) -> str:
    """Nome de arquivo seguro para gravar no disco (sem caminho, sem caractere estranho)."""
    base = re.sub(r"[^\w.-]", "_", Path(nome.replace("\\", "/")).name)
    if base in ("", ".", "..") or not base.lower().endswith(".zip"):
        raise ValueError(f"nome de arquivo inesperado na fonte: {nome!r}")
    return base


def baixar(url: str, destino: Path, tamanho: int | None = None, auth: tuple[str, str] | None = None,
           http: requests.Session | None = None, tentativas: int | None = None) -> None:
    """GET em streaming SEM retomada (o servidor da Receita não aceita Range).

    Em qualquer falha (rede, HTTP, tamanho diferente do anunciado na listagem, zip inválido)
    apaga o parcial e baixa de novo do zero, com espera exponencial. Só renomeia para o nome
    final quando o arquivo está inteiro."""
    tentativas = tentativas or TENTATIVAS_DOWNLOAD
    http = http or sessao()
    parcial = destino.with_name(destino.name + ".part")
    erro: Exception | None = None
    for i in range(tentativas):
        parcial.unlink(missing_ok=True)
        try:
            checar_disco(destino.parent, tamanho)
            with http.get(url, auth=auth, stream=True, timeout=(30, 300)) as r:
                r.raise_for_status()
                with open(parcial, "wb") as f:
                    for bloco in r.iter_content(8 << 20):
                        f.write(bloco)
            obtido = parcial.stat().st_size
            if tamanho is not None and obtido != tamanho:
                raise OSError(f"chegaram {obtido} bytes, a listagem anuncia {tamanho}")
            if not zipfile.is_zipfile(parcial):
                raise OSError("o arquivo baixado não é um zip válido")
            parcial.replace(destino)
            log(f"  baixado {destino.name} ({obtido / 1e6:.0f} MB, tamanho conferido)")
            return
        except (requests.RequestException, OSError) as e:
            erro = e
            parcial.unlink(missing_ok=True)
            if i + 1 < tentativas:
                espera = ESPERA_BASE_S * 2 ** i
                log(f"  falha baixando {destino.name} ({e}); apago o parcial e baixo de novo em {espera:.0f}s")
                time.sleep(espera)
    raise RuntimeError(f"não consegui baixar {url} em {tentativas} tentativas: {erro}")


def listar_html(url: str, rx: str) -> list[str]:
    r = sessao().get(url, timeout=60)
    r.raise_for_status()
    return sorted(set(re.findall(rx, r.text)))


# --------------------------------------------------------------------------- WebDAV

DAV = "{DAV:}"
PROPFIND_CORPO = (b'<?xml version="1.0" encoding="utf-8"?>'
                  b'<d:propfind xmlns:d="DAV:"><d:prop><d:resourcetype/><d:getcontentlength/>'
                  b'<d:getlastmodified/></d:prop></d:propfind>')


@dataclass(frozen=True)
class ItemDAV:
    nome: str
    url: str
    pasta: bool
    tamanho: int | None
    modificado: str | None


def _status_ok(status: str | None) -> bool:
    partes = (status or "").split()
    return len(partes) < 2 or partes[1] == "200"


def ler_multistatus(xml: bytes, url_pedido: str) -> list[ItemDAV]:
    """Lê a resposta 207 Multi-Status do PROPFIND. Ignora a própria pasta pedida e as
    propriedades que vêm em propstat com status diferente de 200 (o Nextcloud manda
    getcontentlength com 404 para pastas)."""
    raiz = ET.fromstring(xml)
    pedido = unquote(urlsplit(url_pedido).path).rstrip("/")
    itens = []
    for resp in raiz.iter(f"{DAV}response"):
        href = (resp.findtext(f"{DAV}href") or "").strip()
        if not href:
            continue
        url = urljoin(url_pedido, href)
        caminho = unquote(urlsplit(url).path)
        if caminho.rstrip("/") == pedido:
            continue
        props: dict[str, ET.Element] = {}
        for ps in resp.iter(f"{DAV}propstat"):
            prop = ps.find(f"{DAV}prop")
            if prop is not None and _status_ok(ps.findtext(f"{DAV}status")):
                for el in prop:
                    props[el.tag] = el
        rt = props.get(f"{DAV}resourcetype")
        pasta = (rt is not None and rt.find(f"{DAV}collection") is not None) or href.endswith("/")
        el = props.get(f"{DAV}getcontentlength")
        txt = (el.text or "").strip() if el is not None else ""
        tamanho = int(txt) if txt.isdigit() else None
        mod = props.get(f"{DAV}getlastmodified")
        nome = caminho.rstrip("/").rsplit("/", 1)[-1]
        itens.append(ItemDAV(nome, url, pasta, None if pasta else tamanho,
                             mod.text.strip() if mod is not None and mod.text else None))
    return sorted(itens, key=lambda i: i.nome)


class WebDAV:
    """Cliente mínimo do WebDAV público da Receita: PROPFIND Depth 1 e GET com auth (token, "")."""

    def __init__(self, base: str = WEBDAV_CNPJ, token: str = WEBDAV_TOKEN, senha: str = ""):
        self.base = base if base.endswith("/") else base + "/"
        self.auth = (token, senha)
        self.http = sessao()

    def url(self, rel: str = "") -> str:
        return urljoin(self.base, rel)

    def listar(self, rel: str = "") -> list[ItemDAV]:
        url = self.url(rel)
        url = url if url.endswith("/") else url + "/"
        erro: Exception | None = None
        for i in range(TENTATIVAS_LISTAGEM):
            try:
                r = self.http.request("PROPFIND", url, data=PROPFIND_CORPO, auth=self.auth, timeout=(30, 120),
                                      headers={"Depth": "1", "Content-Type": "application/xml; charset=utf-8"})
            except requests.RequestException as e:
                erro = e
                time.sleep(ESPERA_BASE_S * 2 ** i)
                continue
            if r.status_code in (401, 403):
                raise PermissionError(f"PROPFIND {url}: HTTP {r.status_code} (token do compartilhamento errado ou link trocado)")
            if r.status_code == 404:
                raise FileNotFoundError(f"PROPFIND {url}: pasta não existe")
            if r.status_code not in (200, 207):
                erro = RuntimeError(f"PROPFIND {url}: HTTP {r.status_code}")
                time.sleep(ESPERA_BASE_S * 2 ** i)
                continue
            return ler_multistatus(r.content, url)
        raise RuntimeError(f"listagem falhou: {erro}")

    def baixar(self, item: ItemDAV, destino: Path) -> None:
        baixar(item.url, destino, tamanho=item.tamanho, auth=self.auth, http=self.http)


def _zips(itens: list[ItemDAV]) -> list[ItemDAV]:
    return [i for i in itens if not i.pasta and i.nome.lower().endswith(".zip")]


def _contagem(itens: list[ItemDAV]) -> dict[str, int]:
    return {p: sum(bool(re.fullmatch(rf"{p}\d*\.zip", i.nome, re.I)) for i in itens) for p in ESSENCIAIS}


def listar_meses(dav: WebDAV) -> list[str]:
    return sorted(i.nome for i in dav.listar() if i.pasta and RX_MES.fullmatch(i.nome))


def descobrir_mes(dav: WebDAV, mes: str | None = None) -> tuple[str, list[ItemDAV]]:
    """Devolve (mês, arquivos .zip do mês). Sem --mes, escolhe o mês mais recente COMPLETO:
    tem os quatro tipos essenciais, nenhum arquivo vazio e, se existe mês anterior, pelo
    menos tantas partes de cada tipo quanto ele (protege contra mês ainda subindo)."""
    meses = listar_meses(dav)
    if not meses:
        raise SystemExit(f"Nenhuma pasta AAAA-MM em {dav.base}")
    log(f"meses publicados: {', '.join(meses[-6:])}")
    if mes:
        if mes not in meses:
            raise SystemExit(f"Mês {mes} não publicado (últimos: {', '.join(meses[-3:])})")
        itens = _zips(dav.listar(f"{mes}/"))
        faltam = [p for p, n in _contagem(itens).items() if n == 0]
        if faltam:
            raise SystemExit(f"Mês {mes} sem {', '.join(faltam)}")
        return mes, itens
    cache: dict[str, list[ItemDAV]] = {}

    def zips_de(m: str) -> list[ItemDAV]:
        if m not in cache:
            cache[m] = _zips(dav.listar(f"{m}/"))
        return cache[m]

    for k in range(len(meses) - 1, -1, -1):
        m = meses[k]
        itens = zips_de(m)
        cont = _contagem(itens)
        motivo = None
        if any(n == 0 for n in cont.values()):
            motivo = "faltam " + ", ".join(p for p, n in cont.items() if n == 0)
        elif any(i.tamanho == 0 for i in itens):
            motivo = "há arquivo com 0 bytes"
        elif k > 0:
            ant = _contagem(zips_de(meses[k - 1]))
            menos = [p for p in ESSENCIAIS if cont[p] < ant[p]]
            if menos:
                motivo = "menos partes que o mês anterior em " + ", ".join(menos)
        if motivo is None:
            return m, itens
        log(f"  {m} parece incompleto ({motivo}); tento o mês anterior")
    raise SystemExit("Nenhum mês completo na fonte.")


def achar_regime_webdav(dav: WebDAV) -> ItemDAV:
    """NÃO VERIFICADO: supõe uma pasta com 'regime' no nome ao lado da pasta CNPJ e, dentro
    dela (até 2 níveis), zips com 'real' no nome. Escolhe o de maior ano no nome."""
    candidatos: list[ItemDAV] = []
    for pasta in (i for i in dav.listar("../") if i.pasta and "regime" in sem_acento(i.nome).lower()):
        fila, nivel = [pasta.url], 0
        while fila and nivel < 3:
            proxima = []
            for url in fila:
                for i in dav.listar(url):
                    if i.pasta:
                        proxima.append(i.url)
                    elif i.nome.lower().endswith(".zip") and "real" in sem_acento(i.nome).lower():
                        candidatos.append(i)
            fila, nivel = proxima, nivel + 1
    if not candidatos:
        raise RuntimeError("pasta de regime tributário não encontrada no WebDAV")

    def ano(i: ItemDAV) -> tuple[int, str]:
        anos = re.findall(r"(?:19|20)\d{2}", i.nome)
        return (max(map(int, anos)) if anos else 0, i.nome)
    return max(candidatos, key=ano)


# --------------------------------------------------------------------------- fontes

class Fonte:
    """Origem dos .zip, um por vez: obter() devolve o caminho local; descartar() apaga se pode."""

    arquivos: list[str]
    manter: bool = True

    def do_tipo(self, prefixo: str) -> list[str]:
        rx = re.compile(rf"^{prefixo}\d*\.zip$", re.I)
        return sorted((a for a in self.arquivos if rx.match(a)),
                      key=lambda a: int(re.sub(r"\D", "", a) or 0))

    def obter(self, nome: str) -> Path:
        raise NotImplementedError

    def descartar(self, zip_path: Path) -> None:
        if not self.manter:
            zip_path.unlink(missing_ok=True)

    def descricao(self) -> str:
        raise NotImplementedError


class FonteLocal(Fonte):
    """Pasta com os .zip já baixados (pelo navegador ou por outro script). Nunca apaga."""

    def __init__(self, pasta: Path):
        self.pasta = pasta
        self.manter = True
        self.arquivos = sorted(p.name for p in pasta.iterdir() if p.is_file() and p.suffix.lower() == ".zip")
        if not self.arquivos:
            raise SystemExit(f"Nenhum .zip em {pasta}")

    def obter(self, nome: str) -> Path:
        return self.pasta / nome

    def descricao(self) -> str:
        return f"pasta local {self.pasta}"


class FonteWebDAV(Fonte):
    """Baixa cada .zip do WebDAV na hora de usar. Reaproveita um .zip já presente na pasta
    de trabalho se o tamanho bate com a listagem (útil com --manter-zips)."""

    def __init__(self, trabalho: Path, dav: WebDAV, mes: str, itens: list[ItemDAV], manter_zips: bool = False):
        self.trabalho, self.dav, self.mes = trabalho, dav, mes
        self.manter = manter_zips
        self.itens = {i.nome: i for i in _zips(itens)}
        self.arquivos = sorted(self.itens)
        if not self.arquivos:
            raise SystemExit("Nenhum .zip encontrado na fonte.")

    def obter(self, nome: str) -> Path:
        item = self.itens[nome]
        destino = self.trabalho / nome_local(nome)
        if (destino.exists() and zipfile.is_zipfile(destino)
                and (item.tamanho is None or destino.stat().st_size == item.tamanho)):
            log(f"  {destino.name} já estava baixado (tamanho confere)")
            return destino
        destino.unlink(missing_ok=True)
        self.dav.baixar(item, destino)
        return destino

    def descricao(self) -> str:
        return f"WebDAV {self.dav.url(self.mes + '/')}"

    def total_bytes(self) -> int:
        return sum(i.tamanho or 0 for i in self.itens.values())


# --------------------------------------------------------------------------- leitura dos CSV

def extrair(zip_path: Path, pasta: Path) -> Path:
    """Extrai o maior membro do zip (o CSV) com nome seguro; converte UTF-16 para UTF-8."""
    with zipfile.ZipFile(zip_path) as zf:
        membro = max(zf.infolist(), key=lambda m: m.file_size)
        destino = pasta / (Path(membro.filename).name or "dados.csv")
        with zf.open(membro) as src, open(destino, "wb") as dst:
            shutil.copyfileobj(src, dst, 16 << 20)
    enc = detectar_encoding(destino)
    if enc == "utf-16":  # relatado após a migração de 2026; o DuckDB lê UTF-8/latin-1 com mais segurança
        conv = destino.with_name(destino.name + ".utf8")
        with codecs.open(destino, "r", "utf-16") as src, open(conv, "w", encoding="utf-8") as dst:
            shutil.copyfileobj(src, dst, 16 << 20)
        destino.unlink()
        conv.rename(destino)
    return destino


def detectar_encoding(path: Path) -> str:
    with open(path, "rb") as f:
        amostra = f.read(1 << 20)
    if amostra.startswith(b"\xef\xbb\xbf"):
        return "utf-8"
    if amostra[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return "utf-16"
    try:
        amostra.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError as e:
        return "utf-8" if e.start > len(amostra) - 4 else "latin-1"


def csv_sql(path: Path, tipo: str) -> str:
    cols = "{" + ", ".join(f"'{c}': 'VARCHAR'" for c in COLS[tipo]) + "}"
    enc = detectar_encoding(path)
    return (f"read_csv({q(path)}, delim=';', quote='\"', escape='\"', header=false, columns={cols}, "
            f"encoding='{enc}', ignore_errors=true, null_padding=true, strict_mode=false)")


# --------------------------------------------------------------------------- etapas

class Pipeline:
    def __init__(self, saida: Path, fonte: Fonte | None, cnae_alvo: Path = CNAE_ALVO_PADRAO,
                 hoje: dt.date | None = None):
        self.saida = saida
        self.partes = saida / "partes"
        self.tab = saida / "tabelas"
        self.tmp = saida / "_trabalho"
        for p in (self.partes, self.tab, self.tmp):
            p.mkdir(parents=True, exist_ok=True)
        self.fonte = fonte
        self.cnae_alvo = cnae_alvo
        self.hoje = hoje or dt.date.today()
        self.con = duckdb.connect()
        self.con.execute(f"SET temp_directory={q(self.tmp / 'duckdb')}")
        self.con.execute("SET preserve_insertion_order=false")

    # ---- leitura de um zip por vez
    def _processar(self, nome_zip: str, tipo: str, sqls: list[tuple[str, Path]]) -> None:
        z = self.fonte.obter(nome_zip)
        csv = extrair(z, self.tmp)
        self.fonte.descartar(z)
        try:
            fonte_sql = csv_sql(csv, tipo)
            for sql, destino in sqls:
                self.con.execute(f"COPY ({sql.replace('{csv}', fonte_sql)}) TO {q(destino)} (FORMAT parquet)")
        finally:
            csv.unlink(missing_ok=True)

    def tabelas(self) -> None:
        for nome in TABELAS:
            arq = self.fonte.do_tipo(nome)
            if not arq:
                log(f"  tabela {nome} ausente na fonte")
                continue
            self._processar(arq[0], "tabela", [(
                "SELECT trim(codigo) AS codigo, trim(descricao) AS descricao, "
                "strip_accents(upper(trim(descricao))) AS dn FROM {csv}",
                self.tab / f"{nome.lower()}.parquet")])
        log("tabelas auxiliares ok")

    def _tab(self, nome: str) -> str:
        p = self.tab / f"{nome}.parquet"
        if p.exists():
            return f"read_parquet({q(p)})"
        return "(SELECT NULL::VARCHAR codigo, NULL::VARCHAR descricao, NULL::VARCHAR dn WHERE false)"

    def socios(self) -> None:
        qual = self._tab("qualificacoes")
        for i, nome in enumerate(self.fonte.do_tipo("Socios")):
            log(f"sócios: {nome}")
            base = f"""
                SELECT trim(s.cnpj_basico) AS cnpj_basico,
                       TRY_CAST(s.identificador_socio AS INT) AS ident,
                       strip_accents(upper(trim(s.nome_socio))) AS nome,
                       upper(trim(s.cnpj_cpf_socio)) AS doc,
                       TRY_CAST(s.qualificacao_socio AS INT) AS qual,
                       coalesce(q.dn, '') AS qdn,
                       nullif(trim(s.pais), '') AS pais,
                       nullif(trim(s.data_entrada_sociedade), '') AS data_entrada
                FROM {{csv}} s LEFT JOIN {qual} q ON TRY_CAST(q.codigo AS INT) = TRY_CAST(s.qualificacao_socio AS INT)
            """
            estrangeiro = f"""
                WITH b AS ({base}), t AS (
                  SELECT *, CASE
                      WHEN qdn LIKE '%JURIDIC%' THEN 'PJ'
                      WHEN qdn LIKE '%FISIC%' THEN 'PF'
                      WHEN ident = 1 THEN 'PJ'
                      WHEN ident = 2 THEN 'PF'
                      WHEN regexp_matches(nome, '{RX_NOME_PJ}') THEN 'PJ'
                      ELSE 'ND' END AS tipo
                  FROM b
                  WHERE qdn LIKE '%EXTERIOR%' OR ident = 3
                     OR coalesce(TRY_CAST(pais AS INT), 0) NOT IN (0, 105))
                SELECT cnpj_basico, tipo,
                       CASE WHEN regexp_matches(qdn, 'SOCIO|TITULAR|ACIONISTA|COTAS') THEN 'socio'
                            WHEN regexp_matches(qdn, 'ADMINISTRADOR|DIRETOR|PRESIDENTE|CONSELHEIRO|PROCURADOR|REPRESENTANTE')
                                 THEN 'administrador'
                            ELSE 'socio' END AS papel,
                       pais AS pais_codigo,
                       CASE WHEN tipo = 'PJ' THEN nome END AS nome_pj,   -- PF nunca tem nome gravado
                       data_entrada
                FROM t
            """
            # Sócio PJ brasileiro (holding): guarda só a aresta empresa -> CNPJ básico da holding.
            holding = f"""
                WITH b AS ({base})
                SELECT DISTINCT cnpj_basico, left(regexp_replace(doc, '[^0-9A-Z]', '', 'g'), 8) AS socio_basico
                FROM b WHERE ident = 1 AND qdn NOT LIKE '%EXTERIOR%' AND length(regexp_replace(doc, '[^0-9A-Z]', '', 'g')) = 14
            """
            self._processar(nome, "socios", [
                (estrangeiro, self.partes / f"socios_estr_{i}.parquet"),
                (holding, self.partes / f"socios_holding_{i}.parquet"),
            ])
        diretos = f"read_parquet({q(self.partes / 'socios_estr_*.parquet')})"
        self.con.execute(f"COPY (SELECT * FROM {diretos}) TO {q(self.saida / 'socios_estrangeiros.parquet')} (FORMAT parquet)")
        # Controle estrangeiro indireto: empresa cuja holding brasileira tem sócio PJ estrangeiro.
        self.con.execute(f"""
            COPY (
              SELECT DISTINCT h.cnpj_basico, 'PJ_INDIRETO' AS tipo, 'socio' AS papel,
                     e.pais_codigo, e.nome_pj, NULL AS data_entrada, h.socio_basico AS via_holding
              FROM read_parquet({q(self.partes / 'socios_holding_*.parquet')}) h
              JOIN {diretos} e ON e.cnpj_basico = h.socio_basico AND e.tipo = 'PJ'
            ) TO {q(self.saida / 'socios_indiretos.parquet')} (FORMAT parquet)""")
        n = self.con.execute(f"SELECT count(DISTINCT cnpj_basico) FROM read_parquet({q(self.saida / 'socios_estrangeiros.parquet')})").fetchone()[0]
        m = self.con.execute(f"SELECT count(DISTINCT cnpj_basico) FROM read_parquet({q(self.saida / 'socios_indiretos.parquet')})").fetchone()[0]
        log(f"sócios ok: {n} empresas com sócio estrangeiro direto, {m} via holding")

    def _universo_socios(self) -> str:
        return (f"(SELECT cnpj_basico FROM read_parquet({q(self.saida / 'socios_estrangeiros.parquet')}) "
                f"UNION SELECT cnpj_basico FROM read_parquet({q(self.saida / 'socios_indiretos.parquet')}))")

    def empresas(self) -> None:
        nat = self._tab("naturezas")
        univ = self._universo_socios()
        for i, nome in enumerate(self.fonte.do_tipo("Empresas")):
            log(f"empresas: {nome}")
            sql = f"""
                SELECT trim(e.cnpj_basico) AS cnpj_basico, trim(e.razao_social) AS razao_social,
                       trim(e.natureza_juridica) AS natureza_juridica,
                       TRY_CAST(replace(replace(trim(e.capital_social), '.', ''), ',', '.') AS DOUBLE) AS capital_social,
                       TRY_CAST(e.porte AS INT) AS porte,
                       regexp_matches(coalesce(n.dn, ''), '{RX_NATUREZA_FILIAL_ESTRANGEIRA}') AS filial_estrangeira
                FROM {{csv}} e LEFT JOIN {nat} n ON n.codigo = trim(e.natureza_juridica)
                WHERE trim(e.cnpj_basico) IN {univ}
                   OR regexp_matches(coalesce(n.dn, ''), '{RX_NATUREZA_FILIAL_ESTRANGEIRA}')
            """
            self._processar(nome, "empresas", [(sql, self.partes / f"empresas_{i}.parquet")])
        self.con.execute(f"COPY (SELECT * FROM read_parquet({q(self.partes / 'empresas_*.parquet')})) "
                         f"TO {q(self.saida / 'empresas_universo.parquet')} (FORMAT parquet)")
        log("empresas ok")

    def simples(self) -> None:
        univ = f"(SELECT cnpj_basico FROM read_parquet({q(self.saida / 'empresas_universo.parquet')}))"
        arq = self.fonte.do_tipo("Simples")
        destino = self.saida / "simples_mei.parquet"
        if not arq:
            log("AVISO: Simples.zip ausente; filtro do Simples não aplicado")
            self.con.execute(f"COPY (SELECT NULL::VARCHAR cnpj_basico WHERE false) TO {q(destino)} (FORMAT parquet)")
            return
        sql = f"""SELECT DISTINCT trim(cnpj_basico) AS cnpj_basico FROM {{csv}}
                  WHERE (upper(trim(opcao_simples)) = 'S' OR upper(trim(opcao_mei)) = 'S')
                    AND trim(cnpj_basico) IN {univ}"""
        self._processar(arq[0], "simples", [(sql, destino)])
        log("simples ok")

    def estabelecimentos(self) -> None:
        univ = f"(SELECT cnpj_basico FROM read_parquet({q(self.saida / 'empresas_universo.parquet')}))"
        dominio = r"nullif(regexp_extract(lower(trim(correio_eletronico)), '@([a-z0-9.-]+\.[a-z]{2,})$', 1), '')"
        for i, nome in enumerate(self.fonte.do_tipo("Estabelecimentos")):
            log(f"estabelecimentos: {nome}")
            estab = f"""
                SELECT trim(cnpj_basico) || trim(cnpj_ordem) || trim(cnpj_dv) AS cnpj,
                       trim(cnpj_basico) AS cnpj_basico,
                       TRY_CAST(identificador_matriz_filial AS INT) AS matriz_filial,
                       nullif(trim(nome_fantasia), '') AS nome_fantasia,
                       TRY_CAST(situacao_cadastral AS INT) AS situacao,
                       TRY_STRPTIME(trim(data_inicio_atividade), '%Y%m%d')::DATE AS data_inicio,
                       trim(cnae_fiscal_principal) AS cnae_principal,
                       nullif(trim(cnae_fiscal_secundaria), '') AS cnae_secundaria,
                       trim(uf) AS uf, trim(municipio) AS municipio,
                       {dominio} AS dominio_email          -- só o domínio; o endereço completo é descartado
                FROM {{csv}} WHERE trim(cnpj_basico) IN {univ}
            """
            dominios = f"""
                SELECT {dominio} AS dominio, count(DISTINCT trim(cnpj_basico)) AS n_empresas
                FROM {{csv}} WHERE TRY_CAST(situacao_cadastral AS INT) = 2 AND {dominio} IS NOT NULL
                GROUP BY 1
            """
            self._processar(nome, "estabelecimentos", [
                (estab, self.partes / f"estab_{i}.parquet"),
                (dominios, self.partes / f"dominios_{i}.parquet"),
            ])
        self.con.execute(f"COPY (SELECT * FROM read_parquet({q(self.partes / 'estab_*.parquet')})) "
                         f"TO {q(self.saida / 'estab_universo.parquet')} (FORMAT parquet)")
        self.con.execute(f"""COPY (SELECT dominio, sum(n_empresas)::BIGINT AS n_empresas
                                   FROM read_parquet({q(self.partes / 'dominios_*.parquet')}) GROUP BY 1)
                             TO {q(self.saida / 'dominios.parquet')} (FORMAT parquet)""")
        log("estabelecimentos ok")

    def _zip_regime(self, dav: WebDAV | None) -> Path:
        if dav is not None:
            try:
                item = achar_regime_webdav(dav)
                destino = self.tmp / nome_local(item.nome)
                dav.baixar(item, destino)
                return destino
            except Exception as e:  # noqa: BLE001
                log(f"  regime não achado no WebDAV ({e}); tento o endereço antigo")
        arqs = [a for a in listar_html(FONTE_REGIME_HTML, r'href="([^"/]+\.zip)"') if "real" in a.lower()]
        if not arqs:
            raise RuntimeError("nenhum zip com 'real' no nome")
        destino = self.tmp / nome_local(unquote(arqs[-1]))
        baixar(FONTE_REGIME_HTML + arqs[-1], destino)
        return destino

    def regime(self, dav: WebDAV | None = None) -> None:
        """Opcional. Base 'regime tributário' da Receita (forma de tributação por ano, com
        defasagem de ~1 ano). Local e layout NÃO VERIFICADOS: o código procura a pasta pelo
        nome e as colunas pelo nome; se falhar, segue sem regime."""
        destino = self.saida / "regime.parquet"
        try:
            z = self._zip_regime(dav)
            csv = extrair(z, self.tmp)
            z.unlink(missing_ok=True)
            enc = detectar_encoding(csv)
            rel = self.con.sql(f"SELECT * FROM read_csv({q(csv)}, encoding='{enc}', ignore_errors=true, all_varchar=true)")
            cols = {c.lower(): c for c in rel.columns}
            c_ano = next(c for k, c in cols.items() if "ano" in k)
            c_cnpj = next(c for k, c in cols.items() if k.startswith("cnpj") and "scp" not in k)
            self.con.execute(f"""
                COPY (SELECT left(regexp_replace("{c_cnpj}", '[^0-9A-Za-z]', '', 'g'), 8) AS cnpj_basico,
                             max(TRY_CAST("{c_ano}" AS INT)) AS ano_lucro_real
                      FROM read_csv({q(csv)}, encoding='{enc}', ignore_errors=true, all_varchar=true)
                      GROUP BY 1) TO {q(destino)} (FORMAT parquet)""")
            csv.unlink(missing_ok=True)
            log("regime tributário (lucro real) ok")
        except Exception as e:  # noqa: BLE001
            log(f"AVISO: regime tributário não usado ({e})")

    # ---- nota
    def pontuar(self) -> dict:
        s = self.saida
        regime = s / "regime.parquet"
        self.con.execute(f"CREATE OR REPLACE TABLE cnae_alvo AS SELECT prefixo::VARCHAR prefixo, grupo, peso::DOUBLE peso "
                         f"FROM read_csv({q(self.cnae_alvo)}, header=true, all_varchar=true)")
        regime_sql = (f"read_parquet({q(regime)})" if regime.exists()
                      else "(SELECT NULL::VARCHAR cnpj_basico, NULL::INT ano_lucro_real WHERE false)")
        hoje = self.hoje.isoformat()
        self.con.execute(f"""
        CREATE OR REPLACE TABLE base AS
        WITH soc AS (
            SELECT cnpj_basico, tipo, papel, pais_codigo, nome_pj FROM read_parquet({q(s / 'socios_estrangeiros.parquet')})
            UNION ALL
            SELECT cnpj_basico, tipo, papel, pais_codigo, nome_pj FROM read_parquet({q(s / 'socios_indiretos.parquet')})
        ), soc_pts AS (
            SELECT *, CASE WHEN tipo = 'PJ' THEN 30 WHEN tipo = 'PJ_INDIRETO' THEN 24 WHEN tipo = 'ND' THEN 18
                           WHEN papel = 'socio' THEN 12 ELSE 8 END AS pts FROM soc
        ), soc_ag AS (
            SELECT cnpj_basico, max(pts) AS pts_socio, arg_max(tipo, pts) AS tipo_socio,
                   arg_max(pais_codigo, pts) AS pais_codigo,
                   left(string_agg(DISTINCT nome_pj, ' | ') FILTER (WHERE tipo IN ('PJ', 'PJ_INDIRETO')), 250) AS empresa_estrangeira_socia,
                   count(*) AS n_vinculos_estrangeiros
            FROM soc_pts GROUP BY 1
        ), emp AS (
            SELECT e.*, n.dn AS natureza_dn FROM read_parquet({q(s / 'empresas_universo.parquet')}) e
            LEFT JOIN {self._tab('naturezas')} n ON n.codigo = e.natureza_juridica
        ), est AS (
            SELECT * FROM read_parquet({q(s / 'estab_universo.parquet')})
        ), n_est AS (
            SELECT cnpj_basico, count(*) AS n_estab_ativos FROM est WHERE situacao = 2 GROUP BY 1
        ), matriz AS (
            SELECT * FROM est WHERE matriz_filial = 1 AND situacao = 2
        ), alvo AS (
            SELECT m.cnpj, arg_max(a.grupo, length(a.prefixo)) AS grupo, arg_max(a.peso, length(a.prefixo)) AS peso
            FROM matriz m JOIN cnae_alvo a ON starts_with(m.cnae_principal, a.prefixo) GROUP BY 1
        ), dom AS (SELECT * FROM read_parquet({q(s / 'dominios.parquet')}))
        SELECT m.cnpj, e.cnpj_basico, e.razao_social, m.nome_fantasia, m.cnae_principal,
               c.descricao AS cnae_descricao, alvo.grupo AS grupo_cnae, alvo.peso AS peso_cnae,
               m.uf, coalesce(mu.descricao, m.municipio) AS municipio, e.capital_social, e.porte,
               m.data_inicio, e.natureza_juridica,
               CASE WHEN e.filial_estrangeira AND sa.cnpj_basico IS NULL THEN 'FILIAL_SOC_ESTRANGEIRA'
                    ELSE sa.tipo_socio END AS tipo_socio,
               CASE WHEN e.filial_estrangeira AND sa.cnpj_basico IS NULL THEN 30 ELSE sa.pts_socio END AS pts_socio,
               p.descricao AS pais_socio, sa.empresa_estrangeira_socia, coalesce(sa.n_vinculos_estrangeiros, 0) AS n_vinculos_estrangeiros,
               m.dominio_email, coalesce(dom.n_empresas, 0) AS dominio_n_empresas,
               coalesce(ne.n_estab_ativos, 1) AS n_estab_ativos, r.ano_lucro_real
        FROM matriz m
        JOIN emp e ON e.cnpj_basico = m.cnpj_basico
        JOIN alvo ON alvo.cnpj = m.cnpj
        LEFT JOIN soc_ag sa ON sa.cnpj_basico = m.cnpj_basico
        LEFT JOIN n_est ne ON ne.cnpj_basico = m.cnpj_basico
        LEFT JOIN dom ON dom.dominio = m.dominio_email
        LEFT JOIN {self._tab('cnaes')} c ON c.codigo = m.cnae_principal
        LEFT JOIN {self._tab('municipios')} mu ON mu.codigo = m.municipio
        LEFT JOIN {self._tab('paises')} p ON TRY_CAST(p.codigo AS INT) = TRY_CAST(sa.pais_codigo AS INT)
        LEFT JOIN {regime_sql} r ON r.cnpj_basico = m.cnpj_basico
        WHERE (sa.cnpj_basico IS NOT NULL OR e.filial_estrangeira)
          AND e.cnpj_basico NOT IN (SELECT cnpj_basico FROM read_parquet({q(s / 'simples_mei.parquet')}))
          AND coalesce(e.capital_social, 0) >= {CAPITAL_MINIMO}
          AND left(e.natureza_juridica, 1) = '2'
          AND NOT regexp_matches(coalesce(e.natureza_dn, ''), '{RX_NATUREZA_EXCLUI}')
          AND NOT regexp_matches(m.cnae_principal, '^6[456]')
          AND NOT regexp_matches(coalesce(m.cnae_secundaria, ''), '(^|,)6[456]')
          AND NOT regexp_matches(strip_accents(upper(coalesce(e.razao_social, '') || ' ' || coalesce(m.nome_fantasia, ''))),
                                 '{RX_EXCLUI_NOME}')
        """)
        genericos = ", ".join(f"'{d}'" for d in sorted(DOMINIOS_GENERICOS))
        self.con.execute(f"""
        CREATE OR REPLACE TABLE pontuada AS
        SELECT *,
          round(pts_socio
              + 25 * peso_cnae
              + 20 * least(greatest((log10(greatest(capital_social, 1)) - 5) / 3.0, 0), 1)
              + CASE WHEN ano_lucro_real IS NOT NULL OR porte = 5 THEN 10 WHEN porte = 3 THEN 4
                     WHEN porte = 1 THEN 2 ELSE 3 END
              + CASE WHEN idade_anos < 1 THEN 6 WHEN idade_anos < 3 THEN 10 WHEN idade_anos < 10 THEN 8
                     WHEN idade_anos < 20 THEN 6 ELSE 4 END
              + CASE WHEN n_estab_ativos >= 5 THEN 5 WHEN n_estab_ativos >= 2 THEN 3 ELSE 0 END, 1) AS nota,
          CASE WHEN dominio_email IS NULL THEN NULL
               WHEN dominio_email IN ({genericos}) THEN 'provável contador (domínio genérico)'
               WHEN dominio_n_empresas >= {LIMIAR_DOMINIO_REPETIDO}
                    THEN 'provável contador (domínio em ' || dominio_n_empresas || ' empresas)'
               ELSE 'próprio' END AS marca_email
        FROM (SELECT *, coalesce(date_diff('day', data_inicio, DATE '{hoje}') / 365.25, 0) AS idade_anos FROM base)
        """)
        self.con.execute(f"COPY pontuada TO {q(s / 'base_pontuada.parquet')} (FORMAT parquet)")
        porte_case = "CASE porte " + " ".join(f"WHEN {k} THEN '{v}'" for k, v in PORTE.items()) + " ELSE 'Não informado' END"
        self.con.execute(f"""
        COPY (
          SELECT cnpj, razao_social, nome_fantasia, cnae_principal, cnae_descricao, grupo_cnae, uf, municipio,
                 capital_social, {porte_case} AS porte, strftime(data_inicio, '%Y-%m-%d') AS data_inicio,
                 CASE tipo_socio WHEN 'PJ' THEN 'PJ estrangeira' WHEN 'PJ_INDIRETO' THEN 'PJ estrangeira via holding BR'
                                 WHEN 'FILIAL_SOC_ESTRANGEIRA' THEN 'filial de sociedade estrangeira'
                                 WHEN 'ND' THEN 'estrangeiro (tipo não identificado)' ELSE 'PF estrangeira' END AS tipo_socio_estrangeiro,
                 pais_socio AS pais_socio_estrangeiro, empresa_estrangeira_socia,
                 dominio_email, marca_email, ano_lucro_real, n_estab_ativos, nota
          FROM pontuada ORDER BY nota DESC, capital_social DESC, cnpj LIMIT {TOP_N}
        ) TO {q(s / 'top1000.csv')} (HEADER, DELIMITER ',')""")
        self.con.execute(f"""
        COPY (
          SELECT 'cnae' AS dimensao, cnae_principal AS chave, any_value(cnae_descricao) AS descricao, any_value(grupo_cnae) AS grupo,
                 count(*) AS n_empresas,
                 count(*) FILTER (WHERE tipo_socio IN ('PJ', 'PJ_INDIRETO', 'FILIAL_SOC_ESTRANGEIRA')) AS n_controle_pj_estrangeiro,
                 count(*) FILTER (WHERE tipo_socio NOT IN ('PJ', 'PJ_INDIRETO', 'FILIAL_SOC_ESTRANGEIRA')) AS n_so_pf_ou_nd,
                 round(avg(nota), 1) AS nota_media, round(median(capital_social)) AS capital_mediano
          FROM pontuada GROUP BY cnae_principal
          UNION ALL
          SELECT 'uf', uf, NULL, NULL, count(*),
                 count(*) FILTER (WHERE tipo_socio IN ('PJ', 'PJ_INDIRETO', 'FILIAL_SOC_ESTRANGEIRA')),
                 count(*) FILTER (WHERE tipo_socio NOT IN ('PJ', 'PJ_INDIRETO', 'FILIAL_SOC_ESTRANGEIRA')),
                 round(avg(nota), 1), round(median(capital_social))
          FROM pontuada GROUP BY uf
          ORDER BY dimensao, n_empresas DESC
        ) TO {q(s / 'contagens.csv')} (HEADER, DELIMITER ',')""")
        n = self.con.execute("SELECT count(*) FROM pontuada").fetchone()[0]
        log(f"nota ok: {n} empresas qualificadas; top{TOP_N} em {s / 'top1000.csv'}")
        return {"qualificadas": n}

    def limpar(self) -> None:
        shutil.rmtree(self.partes, ignore_errors=True)
        shutil.rmtree(self.tmp, ignore_errors=True)


# --------------------------------------------------------------------------- diff

def diff(anterior: Path, atual: Path, destino: Path | None = None) -> Path:
    """Compara dois meses já processados e grava novidades.csv no mês atual."""
    destino = destino or atual / "novidades.csv"
    con = duckdb.connect()
    a, b = anterior, atual

    def rp(p: Path, nome: str) -> str:
        return f"read_parquet({q(p / nome)})"

    paises = (rp(b, "tabelas/paises.parquet") if (b / "tabelas/paises.parquet").exists()
              else "(SELECT NULL::VARCHAR codigo, NULL::VARCHAR descricao WHERE false)")

    con.execute(f"""
    COPY (
      WITH nota AS (SELECT cnpj_basico, cnpj, razao_social, nota FROM {rp(b, 'base_pontuada.parquet')}),
      soc_a AS (SELECT DISTINCT cnpj_basico, tipo, coalesce(pais_codigo, '') pais, coalesce(nome_pj, '') nome_pj
                FROM {rp(a, 'socios_estrangeiros.parquet')}),
      soc_b AS (SELECT DISTINCT cnpj_basico, tipo, coalesce(pais_codigo, '') pais, coalesce(nome_pj, '') nome_pj
                FROM {rp(b, 'socios_estrangeiros.parquet')}),
      ganhou AS (
        SELECT b.cnpj_basico, 'ganhou_socio_estrangeiro' AS evento,
               CASE b.tipo WHEN 'PJ' THEN 'PJ estrangeira: ' || b.nome_pj WHEN 'PF' THEN 'PF estrangeira'
                           ELSE 'estrangeiro (tipo não identificado)' END
               || CASE WHEN b.pais <> '' THEN ' (' || coalesce(p.descricao, 'país ' || b.pais) || ')' ELSE '' END
               || CASE WHEN b.cnpj_basico NOT IN (SELECT cnpj_basico FROM soc_a) THEN ' [primeiro sócio estrangeiro]' ELSE '' END AS detalhe
        FROM (SELECT * FROM soc_b ANTI JOIN soc_a USING (cnpj_basico, tipo, pais, nome_pj)) b
        LEFT JOIN {paises} p ON TRY_CAST(p.codigo AS INT) = TRY_CAST(b.pais AS INT)
      ),
      est_a AS (SELECT * FROM {rp(a, 'estab_universo.parquet')}),
      est_b AS (SELECT * FROM {rp(b, 'estab_universo.parquet')}),
      filial AS (
        SELECT b.cnpj_basico, 'abriu_filial' AS evento,
               'filial ' || b.cnpj || ' em ' || b.uf || coalesce(' desde ' || strftime(b.data_inicio, '%Y-%m-%d'), '') AS detalhe
        FROM est_b b
        WHERE b.matriz_filial = 2 AND b.situacao = 2
          AND b.cnpj NOT IN (SELECT cnpj FROM est_a WHERE situacao = 2)
          AND b.cnpj_basico IN (SELECT cnpj_basico FROM est_a)
      ),
      cnae AS (
        SELECT b.cnpj_basico, 'mudou_cnae_principal' AS evento,
               a.cnae_principal || ' -> ' || b.cnae_principal AS detalhe
        FROM est_b b JOIN est_a a USING (cnpj)
        WHERE b.matriz_filial = 1 AND b.cnae_principal IS DISTINCT FROM a.cnae_principal
      ),
      ev AS (SELECT * FROM ganhou UNION ALL SELECT * FROM filial UNION ALL SELECT * FROM cnae)
      SELECT n.cnpj, ev.cnpj_basico, n.razao_social, ev.evento, ev.detalhe, n.nota AS nota_atual,
             n.cnpj IS NOT NULL AS esta_na_base_pontuada
      FROM ev LEFT JOIN nota n USING (cnpj_basico)
      ORDER BY esta_na_base_pontuada DESC, n.nota DESC NULLS LAST, ev.evento
    ) TO {q(destino)} (HEADER, DELIMITER ',')""")
    log(f"diff ok: {destino}")
    return destino


def mes_anterior_processado(pasta: Path, mes: str) -> Path | None:
    """Pasta do mês processado mais recente antes de `mes` (com os .parquet que o diff usa)."""
    precisa = ("base_pontuada.parquet", "socios_estrangeiros.parquet", "estab_universo.parquet")
    anteriores = sorted(p for p in pasta.iterdir() if p.is_dir() and RX_MES.fullmatch(p.name) and p.name < mes
                        and all((p / f).exists() for f in precisa))
    return anteriores[-1] if anteriores else None


# --------------------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def fonte_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("--webdav", default=WEBDAV_CNPJ, help="pasta CNPJ no WebDAV (padrão: compartilhamento da Receita)")
        p.add_argument("--token", default=WEBDAV_TOKEN, help="token do link público (usuário do WebDAV; senha vazia)")

    li = sub.add_parser("listar", help="mostra os meses publicados e os arquivos de um mês, com tamanho")
    li.add_argument("--mes", help="AAAA-MM (padrão: mais recente completo)")
    fonte_args(li)
    r = sub.add_parser("rodar")
    r.add_argument("--mes", help="AAAA-MM (padrão: mais recente completo)")
    r.add_argument("--dir", default="saida", help="pasta de saída (padrão: saida)")
    r.add_argument("--fonte-local", type=Path, help="pasta com os .zip já baixados (não baixa nada)")
    r.add_argument("--manter-zips", action="store_true", help="guarda os .zip baixados em saida/<mes>/zips")
    r.add_argument("--regime", action="store_true", help="usa a base de regime tributário (lucro real)")
    r.add_argument("--cnae-alvo", type=Path, default=CNAE_ALVO_PADRAO)
    r.add_argument("--manter-partes", action="store_true")
    r.add_argument("--refazer", action="store_true", help="processa de novo um mês que já tem top1000.csv")
    fonte_args(r)
    p = sub.add_parser("pontuar")
    p.add_argument("--mes", required=True)
    p.add_argument("--dir", default="saida")
    p.add_argument("--cnae-alvo", type=Path, default=CNAE_ALVO_PADRAO)
    d = sub.add_parser("diff")
    d.add_argument("--anterior", type=Path, required=True)
    d.add_argument("--atual", type=Path, required=True)
    a = ap.parse_args(argv)

    if a.cmd == "listar":
        listar(a.mes, a.webdav, a.token)
        return
    if a.cmd == "diff":
        diff(a.anterior, a.atual)
        return
    if a.cmd == "pontuar":
        Pipeline(Path(a.dir) / a.mes, None, a.cnae_alvo).pontuar()
        return
    rodar(a.mes, Path(a.dir), a.fonte_local, a.manter_zips, a.regime, a.cnae_alvo, a.manter_partes,
          webdav=a.webdav, token=a.token, refazer=a.refazer)


def listar(mes: str | None = None, webdav: str = WEBDAV_CNPJ, token: str = WEBDAV_TOKEN) -> None:
    dav = WebDAV(webdav, token)
    m, itens = descobrir_mes(dav, mes)
    print(f"\n{dav.url(m + '/')}")
    for i in sorted(itens, key=lambda i: i.nome):
        print(f"  {i.nome:28} {(i.tamanho or 0) / 1e6:10.1f} MB   {i.modificado or ''}")
    print(f"  {len(itens)} arquivos, {sum(i.tamanho or 0 for i in itens) / 1e9:.2f} GB")


def rodar(mes: str | None = None, pasta: Path = Path("saida"), fonte_local: Path | None = None,
          manter_zips: bool = False, regime: bool = False, cnae_alvo: Path = CNAE_ALVO_PADRAO,
          manter_partes: bool = False, hoje: dt.date | None = None, webdav: str = WEBDAV_CNPJ,
          token: str = WEBDAV_TOKEN, refazer: bool = False) -> Path:
    dav: WebDAV | None = None
    itens: list[ItemDAV] = []
    if fonte_local:
        mes = mes or (fonte_local.name if RX_MES.fullmatch(fonte_local.name) else dt.date.today().strftime("%Y-%m"))
    else:
        dav = WebDAV(webdav, token)
        mes, itens = descobrir_mes(dav, mes)
    saida = pasta / mes
    if (saida / "top1000.csv").exists() and not refazer:
        log(f"{mes} já processado em {saida} (use --refazer para processar de novo)")
        return saida
    saida.mkdir(parents=True, exist_ok=True)
    if fonte_local:
        fonte: Fonte = FonteLocal(fonte_local)
    else:
        zips = saida / ("zips" if manter_zips else "_trabalho")
        zips.mkdir(parents=True, exist_ok=True)
        fonte = FonteWebDAV(zips, dav, mes, itens, manter_zips)
        log(f"fonte {fonte.descricao()} · {len(fonte.arquivos)} arquivos, {fonte.total_bytes() / 1e9:.2f} GB")
    pl = Pipeline(saida, fonte, cnae_alvo, hoje)
    pl.tabelas()
    pl.socios()
    pl.empresas()
    pl.simples()
    pl.estabelecimentos()
    if regime:
        pl.regime(dav)
    pl.pontuar()
    if not manter_partes:
        pl.limpar()
    (saida / "FONTE.txt").write_text(
        f"fonte={fonte.descricao()}\nmes={mes}\narquivos={len(fonte.arquivos)}\n"
        f"processado_em={dt.datetime.now():%Y-%m-%d %H:%M}\n", encoding="utf-8")
    anterior = mes_anterior_processado(pasta, mes)
    if anterior:
        diff(anterior, saida)
    return saida


if __name__ == "__main__":
    main(sys.argv[1:])
