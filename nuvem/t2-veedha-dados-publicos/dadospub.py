"""dadospub: dados públicos para comparar produtos de investimento com o CDI.

Fontes (todas abertas, sem login):
  - Banco Central, SGS: CDI (12), Selic diária (11), meta Selic (432), IPCA mensal (433)
  - Banco Central, Olinda: Focus (ExpectativasMercadoAnuais)
  - CVM, Dados Abertos: Informe Diário de fundos (cota, PL, cotistas)
  - Tesouro Transparente: preços e taxas históricos do Tesouro Direto
Nada da ANBIMA (os termos de uso proíbem acesso automatizado).

Convenções:
  - Taxas do SGS em % (CDI e Selic diária em % ao dia; IPCA em % no mês).
  - Retornos devolvidos em fração (0.1050 = 10,50%).
  - CDI acumulado entre `inicio` e `fim` usa as taxas dos dias úteis em [inicio, fim):
    quem aplica em `inicio` e resgata em `fim` ganha o DI de `inicio` até a véspera de `fim`.
    É a mesma janela de cota(fim) / cota(inicio) - 1.

Uso rápido:
    import dadospub as dp
    dp.cdi_acumulado("2025-10-01", "2026-10-01")
    dp.rentabilidade_vs_cdi("00.000.000/0001-00", "2025-10-01", "2026-10-01")
    dp.tesouro("Tesouro IPCA+", "2035-05-15")
    python dadospub.py exemplo     # maior fundo do Informe Diário, últimos 12 meses x CDI
"""
from __future__ import annotations

import datetime as dt
import io
import re
import sys
import time
import urllib.parse
import zipfile
from functools import lru_cache
from pathlib import Path

import pandas as pd
import requests

SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados"
FOCUS_URL = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais"
CVM_INF_DIARIO = "https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/inf_diario_fi_{aaaamm}.zip"
CVM_INF_DIARIO_HIST = "https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/HIST/inf_diario_fi_{aaaa}.zip"
CVM_CADASTRO = "https://dados.cvm.gov.br/dados/FI/CAD/DADOS/cad_fi.csv"
TESOURO_URL = ("https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/"
               "resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/PrecoTaxaTesouroDireto.csv")
SERIES = {"cdi": 12, "selic": 11, "selic_meta": 432, "ipca": 433}
CACHE = Path.home() / ".cache" / "dadospub"
UA = {"User-Agent": "dadospub/1.0 (uso analitico)", "Accept": "application/json, text/csv, */*"}

def _data(x) -> dt.date:
    return pd.Timestamp(x).date()


def _qs(params: dict | None) -> str | None:
    """Query string com `$` literal (padrão OData) e espaço como %20."""
    if not params:
        return None
    return urllib.parse.urlencode(params, safe="$',()", quote_via=urllib.parse.quote)


def _get(url: str, params: dict | None = None, tentativas: int = 4, timeout: int = 60) -> requests.Response:
    for i in range(tentativas):
        try:
            r = requests.get(url, params=_qs(params), headers=UA, timeout=timeout)
            if r.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"HTTP {r.status_code}", response=r)
            r.raise_for_status()
            return r
        except requests.RequestException:
            if i == tentativas - 1:
                raise
            time.sleep(2 ** (i + 1))
    raise RuntimeError("inalcançável")


# --------------------------------------------------------------------------- calendário

def pascoa(ano: int) -> dt.date:
    """Domingo de Páscoa (algoritmo de Meeus/Jones/Butcher, calendário gregoriano)."""
    a, b, c = ano % 19, ano // 100, ano % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l_ = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_) // 451
    mes = (h + l_ - 7 * m + 114) // 31
    dia = (h + l_ - 7 * m + 114) % 31 + 1
    return dt.date(ano, mes, dia)


@lru_cache(maxsize=None)
def feriados_nacionais(ano: int) -> frozenset[dt.date]:
    """Feriados bancários nacionais: fixos, Carnaval (seg e ter), Sexta-feira Santa e Corpus Christi.
    20/11 (Consciência Negra) entra a partir de 2024 (Lei 14.759/2023). Feriado municipal não entra."""
    p = pascoa(ano)
    fixos = [(1, 1), (4, 21), (5, 1), (9, 7), (10, 12), (11, 2), (11, 15), (12, 25)]
    if ano >= 2024:
        fixos.append((11, 20))
    moveis = [p - dt.timedelta(days=48), p - dt.timedelta(days=47), p - dt.timedelta(days=2),
              p + dt.timedelta(days=60)]
    return frozenset([dt.date(ano, m, d) for m, d in fixos] + moveis)


def eh_dia_util(d) -> bool:
    d = _data(d)
    return d.weekday() < 5 and d not in feriados_nacionais(d.year)


def dias_uteis(inicio, fim) -> list[dt.date]:
    """Dias úteis em [inicio, fim)."""
    a, b = _data(inicio), _data(fim)
    return [x.date() for x in pd.date_range(a, b - dt.timedelta(days=1)) if eh_dia_util(x)]


def n_dias_uteis(inicio, fim) -> int:
    """Número de dias úteis entre duas datas, contando o início e excluindo o fim (padrão de mercado)."""
    return len(dias_uteis(inicio, fim))


def somar_dias_uteis(d, n: int) -> dt.date:
    d, passo = _data(d), (1 if n >= 0 else -1)
    while n:
        d += dt.timedelta(days=passo)
        if eh_dia_util(d):
            n -= passo
    return d


# --------------------------------------------------------------------------- taxas e contas

def taxa_aa_para_ad(taxa_aa_pct: float, base: int = 252) -> float:
    return ((1 + taxa_aa_pct / 100) ** (1 / base) - 1) * 100


def taxa_ad_para_aa(taxa_ad_pct: float, base: int = 252) -> float:
    return ((1 + taxa_ad_pct / 100) ** base - 1) * 100


def fator_acumulado(taxas_pct: pd.Series, inicio=None, fim=None) -> float:
    """Produto de (1 + taxa/100) para as datas em [inicio, fim). Devolve o fator (1.105 = +10,5%)."""
    s = taxas_pct.dropna()
    idx = pd.to_datetime(s.index)
    m = pd.Series(True, index=s.index)
    if inicio is not None:
        m &= idx >= pd.Timestamp(inicio)
    if fim is not None:
        m &= idx < pd.Timestamp(fim)
    return float((1 + s[m.values] / 100).prod())


def percentual_do_cdi(retorno: float, retorno_cdi: float) -> float:
    return retorno / retorno_cdi * 100 if retorno_cdi else float("nan")


# --------------------------------------------------------------------------- BCB / SGS

def _janelas(inicio: dt.date, fim: dt.date, anos: int = 10) -> list[tuple[dt.date, dt.date]]:
    """O SGS limita séries diárias a 10 anos por consulta."""
    out, a = [], inicio
    while a <= fim:
        b = min(fim, dt.date(a.year + anos, a.month, min(a.day, 28)) - dt.timedelta(days=1))
        out.append((a, b))
        a = b + dt.timedelta(days=1)
    return out


def parse_sgs(payload: list[dict]) -> pd.Series:
    if not payload:
        return pd.Series(dtype=float)
    df = pd.DataFrame(payload)
    idx = pd.to_datetime(df["data"], format="%d/%m/%Y")
    return pd.Series(pd.to_numeric(df["valor"], errors="coerce").values, index=idx).sort_index()


def sgs(serie: int | str, inicio, fim) -> pd.Series:
    """Série do SGS entre duas datas (inclusive). `serie` pode ser o código ou 'cdi', 'selic', 'ipca'..."""
    codigo = SERIES.get(serie, serie) if isinstance(serie, str) else serie
    partes = []
    for a, b in _janelas(_data(inicio), _data(fim)):
        r = _get(SGS_URL.format(serie=codigo),
                 {"formato": "json", "dataInicial": f"{a:%d/%m/%Y}", "dataFinal": f"{b:%d/%m/%Y}"})
        partes.append(parse_sgs(r.json()))
    s = pd.concat(partes) if partes else pd.Series(dtype=float)
    s = s[~s.index.duplicated()]
    s.name = str(serie)
    return s


def cdi_diario(inicio, fim) -> pd.Series:
    """CDI em % ao dia, um valor por dia útil."""
    return sgs("cdi", inicio, fim)


def cdi_acumulado(inicio, fim) -> float:
    """Retorno do CDI (fração) de quem aplica em `inicio` e resgata em `fim`."""
    s = cdi_diario(inicio, _data(fim) - dt.timedelta(days=1))
    return fator_acumulado(s, inicio, fim) - 1


def selic_diaria(inicio, fim) -> pd.Series:
    return sgs("selic", inicio, fim)


def selic_meta(inicio, fim) -> pd.Series:
    return sgs("selic_meta", inicio, fim)


def ipca_mensal(inicio, fim) -> pd.Series:
    return sgs("ipca", inicio, fim)


def ipca_acumulado(inicio, fim) -> float:
    """IPCA acumulado (fração) dos meses de referência entre `inicio` e `fim`, inclusive."""
    s = ipca_mensal(inicio, fim)
    return float((1 + s / 100).prod() - 1)


def focus_mais_recente(indicadores=("IPCA", "Selic", "PIB Total", "Câmbio"), base_calculo: int = 0) -> pd.DataFrame:
    """Medianas do boletim Focus mais recente (expectativas anuais), um ano de referência por linha."""
    ult = _get(FOCUS_URL, {"$top": "1", "$orderby": "Data desc", "$format": "json", "$select": "Data"}).json()["value"]
    data = ult[0]["Data"]
    filtro = " or ".join(f"Indicador eq '{i}'" for i in indicadores)
    r = _get(FOCUS_URL, {"$filter": f"Data eq '{data}' and baseCalculo eq {base_calculo} and ({filtro})",
                         "$format": "json", "$top": "1000",
                         "$select": "Indicador,Data,DataReferencia,Media,Mediana,Minimo,Maximo,numeroRespondentes"})
    return parse_focus(r.json()["value"])


def parse_focus(valores: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(valores)
    if df.empty:
        return df
    df = df.rename(columns={"Indicador": "indicador", "Data": "data", "DataReferencia": "ano_referencia",
                            "Media": "media", "Mediana": "mediana", "Minimo": "minimo", "Maximo": "maximo",
                            "numeroRespondentes": "respondentes"})
    df["data"] = pd.to_datetime(df["data"]).dt.date
    return df.sort_values(["indicador", "ano_referencia"]).reset_index(drop=True)


# --------------------------------------------------------------------------- CVM / fundos

def normaliza_cnpj(cnpj: str) -> str:
    """Só dígitos e letras, em maiúsculas (aceita o CNPJ alfanumérico de 2026)."""
    return re.sub(r"[^0-9A-Za-z]", "", str(cnpj)).upper()


def _baixar_cache(url: str, nome: str, cache: Path = CACHE, validade_h: float | None = None) -> Path:
    cache.mkdir(parents=True, exist_ok=True)
    p = cache / nome
    if p.exists() and (validade_h is None or time.time() - p.stat().st_mtime < validade_h * 3600):
        return p
    r = _get(url, timeout=300)
    p.write_bytes(r.content)
    return p


def ler_informe_diario(conteudo: bytes) -> pd.DataFrame:
    """Lê o CSV do Informe Diário (layout antigo CNPJ_FUNDO ou pós-CVM 175 CNPJ_FUNDO_CLASSE)."""
    for enc in ("utf-8", "latin-1"):
        try:
            texto = conteudo.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    df = pd.read_csv(io.StringIO(texto), sep=";", dtype=str)
    df = df.rename(columns={"CNPJ_FUNDO_CLASSE": "cnpj", "CNPJ_FUNDO": "cnpj", "ID_SUBCLASSE": "subclasse",
                            "DT_COMPTC": "data", "VL_QUOTA": "cota", "VL_PATRIM_LIQ": "pl",
                            "NR_COTST": "cotistas", "TP_FUNDO_CLASSE": "tipo", "TP_FUNDO": "tipo"})
    for c in ("subclasse", "tipo"):
        if c not in df:
            df[c] = pd.NA
    df["cnpj"] = df["cnpj"].map(normaliza_cnpj)
    df["data"] = pd.to_datetime(df["data"])
    for c in ("cota", "pl", "cotistas"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df[["cnpj", "subclasse", "tipo", "data", "cota", "pl", "cotistas"]]


def _informe_mes(ano: int, mes: int) -> pd.DataFrame:
    aaaamm = f"{ano}{mes:02d}"
    atual = pd.Period(f"{ano}-{mes:02d}", "M") >= pd.Period(dt.date.today(), "M") - 1
    try:
        p = _baixar_cache(CVM_INF_DIARIO.format(aaaamm=aaaamm), f"inf_diario_fi_{aaaamm}.zip",
                          validade_h=12 if atual else None)
        nome_csv = None
    except requests.HTTPError:  # meses antigos ficam no HIST, num zip por ano
        p = _baixar_cache(CVM_INF_DIARIO_HIST.format(aaaa=ano), f"inf_diario_fi_{ano}.zip")
        nome_csv = f"inf_diario_fi_{aaaamm}.csv"
    with zipfile.ZipFile(p) as z:
        nomes = [n for n in z.namelist() if n.endswith(".csv") and (nome_csv is None or n.endswith(nome_csv))]
        return pd.concat([ler_informe_diario(z.read(n)) for n in nomes], ignore_index=True)


def _meses(inicio: dt.date, fim: dt.date) -> list[tuple[int, int]]:
    return [(p.year, p.month) for p in pd.period_range(inicio, fim, freq="M")]


def cotas_fundo(cnpj: str, inicio, fim, subclasse: str | None = None) -> pd.DataFrame:
    """Cota diária, PL e cotistas de um fundo (ou classe) pelo CNPJ, entre duas datas."""
    alvo = normaliza_cnpj(cnpj)
    partes = []
    for ano, mes in _meses(_data(inicio), _data(fim)):
        try:
            df = _informe_mes(ano, mes)
        except requests.HTTPError:
            continue  # mês ainda não publicado
        partes.append(df[df["cnpj"] == alvo])
    if not partes:
        raise LookupError("nenhum Informe Diário disponível no período")
    df = pd.concat(partes, ignore_index=True)
    if subclasse is not None:
        df = df[df["subclasse"] == subclasse]
    elif df["subclasse"].nunique(dropna=True) > 0:
        df = df[df["subclasse"].isna()] if df["subclasse"].isna().any() else df
        if df.groupby("data").size().max() > 1:
            raise ValueError(f"{cnpj} tem subclasses {sorted(df['subclasse'].dropna().unique())}; escolha uma")
    df = df[(df["data"] >= pd.Timestamp(inicio)) & (df["data"] <= pd.Timestamp(fim))]
    if df.empty:
        raise LookupError(f"CNPJ {cnpj} sem cotas entre {inicio} e {fim}")
    return df.sort_values("data").drop_duplicates("data", keep="last").set_index("data")[["cota", "pl", "cotistas"]]


def retorno_entre_cotas(cotas: pd.Series, inicio, fim) -> tuple[float, pd.Timestamp, pd.Timestamp]:
    """Retorno pela última cota disponível em ou antes de cada data. Devolve (retorno, data_ini, data_fim)."""
    c = cotas.dropna().sort_index()
    a = c[c.index <= pd.Timestamp(inicio)]
    b = c[c.index <= pd.Timestamp(fim)]
    if a.empty or b.empty:
        raise LookupError("sem cota em ou antes da data pedida")
    return float(b.iloc[-1] / a.iloc[-1] - 1), a.index[-1], b.index[-1]


def rentabilidade_vs_cdi(cnpj: str, inicio, fim, subclasse: str | None = None) -> dict:
    """Retorno do fundo e do CDI na mesma janela efetiva de cotas."""
    ini = _data(inicio)
    c = cotas_fundo(cnpj, ini - dt.timedelta(days=10), fim, subclasse)
    ret, d0, d1 = retorno_entre_cotas(c["cota"], ini, fim)
    ret_cdi = cdi_acumulado(d0, d1)
    return {"cnpj": cnpj, "data_inicial": d0.date(), "data_final": d1.date(),
            "cota_inicial": float(c["cota"].loc[d0]), "cota_final": float(c["cota"].loc[d1]),
            "pl_final": float(c["pl"].loc[d1]), "retorno_fundo": ret, "retorno_cdi": ret_cdi,
            "pct_cdi": percentual_do_cdi(ret, ret_cdi), "dias_uteis": n_dias_uteis(d0, d1)}


def nome_fundo(cnpj: str) -> str | None:
    """Denominação no cadastro da CVM (cad_fi.csv). Pode faltar para classes criadas pela CVM 175."""
    try:
        p = _baixar_cache(CVM_CADASTRO, "cad_fi.csv", validade_h=24 * 7)
        df = pd.read_csv(p, sep=";", dtype=str, encoding="latin-1", usecols=["CNPJ_FUNDO", "DENOM_SOCIAL"])
        m = df[df["CNPJ_FUNDO"].map(normaliza_cnpj) == normaliza_cnpj(cnpj)]
        return None if m.empty else m["DENOM_SOCIAL"].iloc[-1]
    except Exception:  # noqa: BLE001
        return None


# --------------------------------------------------------------------------- Tesouro Direto

def ler_tesouro(conteudo: bytes | str) -> pd.DataFrame:
    """Lê PrecoTaxaTesouroDireto.csv (separador ';', decimal ',', datas dd/mm/aaaa)."""
    texto = conteudo.decode("latin-1") if isinstance(conteudo, bytes) else conteudo
    df = pd.read_csv(io.StringIO(texto), sep=";", decimal=",", dtype={"Tipo Titulo": str})
    df = df.rename(columns={"Tipo Titulo": "titulo", "Data Vencimento": "vencimento", "Data Base": "data",
                            "Taxa Compra Manha": "taxa_compra", "Taxa Venda Manha": "taxa_venda",
                            "PU Compra Manha": "pu_compra", "PU Venda Manha": "pu_venda", "PU Base Manha": "pu_base"})
    for c in ("vencimento", "data"):
        df[c] = pd.to_datetime(df[c], format="%d/%m/%Y")
    return df


@lru_cache(maxsize=1)
def _tesouro_completo() -> pd.DataFrame:
    return ler_tesouro(_baixar_cache(TESOURO_URL, "PrecoTaxaTesouroDireto.csv", validade_h=12).read_bytes())


def tesouro(titulo: str, vencimento=None, inicio=None, fim=None) -> pd.DataFrame:
    """Taxa e PU históricos de um título. Ex.: tesouro('Tesouro IPCA+', '2035-05-15')."""
    df = _tesouro_completo()
    df = df[df["titulo"].str.casefold() == titulo.casefold()]
    if vencimento is not None:
        df = df[df["vencimento"] == pd.Timestamp(vencimento)]
    if inicio is not None:
        df = df[df["data"] >= pd.Timestamp(inicio)]
    if fim is not None:
        df = df[df["data"] <= pd.Timestamp(fim)]
    return df.sort_values("data").set_index("data")


def titulos_disponiveis() -> pd.DataFrame:
    df = _tesouro_completo()
    return (df.groupby(["titulo", "vencimento"])["data"].agg(["min", "max"])
              .rename(columns={"min": "primeira_data", "max": "ultima_data"}).reset_index())


# --------------------------------------------------------------------------- exemplo

def maior_fundo_recente() -> tuple[str, pd.Timestamp, float]:
    """CNPJ com maior PL na data mais recente do Informe Diário (sem subclasse)."""
    hoje = dt.date.today()
    for k in range(3):
        per = pd.Period(hoje, "M") - k
        try:
            df = _informe_mes(per.year, per.month)
            break
        except requests.HTTPError:
            continue
    else:
        raise LookupError("Informe Diário recente indisponível")
    df = df[df["subclasse"].isna() & df["pl"].notna()]
    ult = df["data"].max()
    linha = df[df["data"] == ult].sort_values("pl", ascending=False).iloc[0]
    return linha["cnpj"], ult, float(linha["pl"])


def exemplo(meses: int = 12) -> dict:
    cnpj, ult, pl = maior_fundo_recente()
    inicio = (ult - pd.DateOffset(months=meses)).date()
    res = rentabilidade_vs_cdi(cnpj, inicio, ult.date())
    res["nome"] = nome_fundo(cnpj)
    return res


if __name__ == "__main__":
    if sys.argv[1:] == ["exemplo"]:
        r = exemplo()
        print(f"Fundo: {r['nome'] or '(nome não encontrado no cad_fi)'}  CNPJ {r['cnpj']}")
        print(f"Período: {r['data_inicial']} a {r['data_final']} ({r['dias_uteis']} dias úteis)")
        print(f"PL final: R$ {r['pl_final']:,.0f}")
        print(f"Fundo: {r['retorno_fundo']:.2%} | CDI: {r['retorno_cdi']:.2%} | {r['pct_cdi']:.1f}% do CDI")
    else:
        print(__doc__)
