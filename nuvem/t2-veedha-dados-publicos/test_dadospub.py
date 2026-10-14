"""Testes do dadospub.

Dois grupos:
  - offline: contas, calendário e leitura dos formatos oficiais (amostras pequenas escritas à mão
    no layout de cada fonte; os valores das amostras são de teste, não são cotações reais).
  - rede (marcados `rede`): batem nas fontes de verdade. Se o host não responde, o teste é pulado
    com o nome do host no motivo.

    python -m pytest -q test_dadospub.py            # tudo
    python -m pytest -q -m "not rede" test_dadospub.py
"""
import datetime as dt
import zipfile

import pandas as pd
import pytest
import requests

import dadospub as dp

D = dt.date


# --------------------------------------------------------------------------- offline

def test_pascoa():
    assert dp.pascoa(2024) == D(2024, 3, 31)
    assert dp.pascoa(2025) == D(2025, 4, 20)
    assert dp.pascoa(2026) == D(2026, 4, 5)
    assert dp.pascoa(2027) == D(2027, 3, 28)


def test_feriados_2026():
    f = dp.feriados_nacionais(2026)
    for d in (D(2026, 2, 16), D(2026, 2, 17), D(2026, 4, 3), D(2026, 6, 4), D(2026, 11, 20), D(2026, 12, 25)):
        assert d in f
    assert D(2026, 2, 18) not in f  # quarta de cinzas é dia útil
    assert len(f) == 13
    assert len(dp.feriados_nacionais(2023)) == 12  # antes da Lei 14.759/2023


def test_dias_uteis():
    assert dp.dias_uteis("2026-02-13", "2026-02-20") == [D(2026, 2, 13), D(2026, 2, 18), D(2026, 2, 19)]
    # 2026: 261 dias de semana, 12 feriados nacionais caem em dia de semana (15/11 é domingo)
    assert dp.n_dias_uteis("2026-01-01", "2027-01-01") == 249
    assert dp.somar_dias_uteis("2026-04-02", 1) == D(2026, 4, 6)  # pula Sexta-feira Santa e fim de semana
    assert dp.somar_dias_uteis("2026-04-06", -1) == D(2026, 4, 2)
    assert not dp.eh_dia_util("2026-11-20") and dp.eh_dia_util("2026-11-19")


def test_conversao_de_taxas():
    ad = dp.taxa_aa_para_ad(10.0)
    assert abs(ad - 0.0378287) < 1e-6
    assert abs(dp.taxa_ad_para_aa(ad) - 10.0) < 1e-9


def test_fator_acumulado_janela_fechada_aberta():
    idx = pd.to_datetime(["2026-10-01", "2026-10-02", "2026-10-05", "2026-10-06"])
    s = pd.Series([0.05, 0.05, 0.05, 0.05], index=idx)
    # [01, 06): três taxas
    assert abs(dp.fator_acumulado(s, "2026-10-01", "2026-10-06") - 1.0005 ** 3) < 1e-12
    assert dp.fator_acumulado(s, "2026-10-06", "2026-10-06") == 1.0


def test_janelas_sgs_10_anos():
    js = dp._janelas(D(2001, 1, 1), D(2026, 10, 14))
    assert js[0][0] == D(2001, 1, 1) and js[-1][1] == D(2026, 10, 14)
    for (a, b), (c, _) in zip(js, js[1:]):
        assert c == b + dt.timedelta(days=1)
    assert all((b - a).days < 3653 for a, b in js)


def test_parse_sgs():
    s = dp.parse_sgs([{"data": "02/10/2026", "valor": "0.055"}, {"data": "01/10/2026", "valor": "0.054"}])
    assert list(s.index) == [pd.Timestamp("2026-10-01"), pd.Timestamp("2026-10-02")]
    assert s.iloc[0] == 0.054


def test_parse_focus():
    df = dp.parse_focus([{"Indicador": "IPCA", "Data": "2026-10-09", "DataReferencia": "2026",
                          "Media": 4.1, "Mediana": 4.0, "Minimo": 3.0, "Maximo": 5.0, "numeroRespondentes": 90}])
    assert df.loc[0, "mediana"] == 4.0 and df.loc[0, "data"] == D(2026, 10, 9)


INF_NOVO = (
    "TP_FUNDO_CLASSE;CNPJ_FUNDO_CLASSE;ID_SUBCLASSE;DT_COMPTC;VL_TOTAL;VL_QUOTA;VL_PATRIM_LIQ;CAPTC_DIA;RESG_DIA;NR_COTST\n"
    "CLASSES - FIF;11.111.111/0001-11;;2026-09-30;100;1.500000000000;1000000.00;0;0;10\n"
    "CLASSES - FIF;11.111.111/0001-11;;2026-10-01;100;1.501000000000;1000000.00;0;0;10\n"
    "CLASSES - FIF;22.222.222/0001-22;;2026-10-01;100;2.0;5000000.00;0;0;3\n"
)
INF_ANTIGO = (
    "TP_FUNDO;CNPJ_FUNDO;DT_COMPTC;VL_TOTAL;VL_QUOTA;VL_PATRIM_LIQ;CAPTC_DIA;RESG_DIA;NR_COTST\n"
    "FI;11.111.111/0001-11;2022-01-03;100;1.1;1000;0;0;5\n"
)


def test_ler_informe_diario_dois_layouts():
    novo = dp.ler_informe_diario(INF_NOVO.encode("latin-1"))
    assert set(novo["cnpj"]) == {"11111111000111", "22222222000122"}
    assert novo["cota"].iloc[1] == 1.501
    antigo = dp.ler_informe_diario(INF_ANTIGO.encode("utf-8"))
    assert antigo.loc[0, "cnpj"] == "11111111000111" and antigo["subclasse"].isna().all()


def test_retorno_entre_cotas_usa_ultima_cota_disponivel():
    c = pd.Series([1.0, 1.1, 1.21], index=pd.to_datetime(["2026-01-02", "2026-06-01", "2026-12-01"]))
    r, d0, d1 = dp.retorno_entre_cotas(c, "2026-01-05", "2026-11-30")
    assert abs(r - 0.1) < 1e-12 and d0 == pd.Timestamp("2026-01-02") and d1 == pd.Timestamp("2026-06-01")


def test_rentabilidade_vs_cdi_sem_rede(monkeypatch):
    cotas = pd.DataFrame({"cota": [1.0, 1.0005 ** 3], "pl": [1e6, 1e6], "cotistas": [1, 1]},
                         index=pd.to_datetime(["2026-10-01", "2026-10-06"]))
    monkeypatch.setattr(dp, "cotas_fundo", lambda *a, **k: cotas)
    taxas = pd.Series([0.05, 0.05, 0.05], index=pd.to_datetime(["2026-10-01", "2026-10-02", "2026-10-05"]))
    monkeypatch.setattr(dp, "cdi_diario", lambda a, b: taxas)
    r = dp.rentabilidade_vs_cdi("11.111.111/0001-11", "2026-10-01", "2026-10-06")
    assert abs(r["pct_cdi"] - 100.0) < 1e-9 and r["dias_uteis"] == 3


TESOURO = (
    "Tipo Titulo;Data Vencimento;Data Base;Taxa Compra Manha;Taxa Venda Manha;PU Compra Manha;PU Venda Manha;PU Base Manha\n"
    "Tesouro IPCA+;15/05/2035;01/10/2026;7,50;7,62;2000,10;1990,20;1990,00\n"
    "Tesouro Selic;01/03/2029;01/10/2026;0,05;0,06;17000,00;16990,00;16990,00\n"
)


def test_ler_tesouro(monkeypatch):
    df = dp.ler_tesouro(TESOURO.encode("latin-1"))
    assert df.loc[0, "taxa_compra"] == 7.50 and df.loc[0, "vencimento"] == pd.Timestamp("2035-05-15")
    monkeypatch.setattr(dp, "_tesouro_completo", lambda: df)
    t = dp.tesouro("tesouro ipca+", "2035-05-15")
    assert len(t) == 1 and t["pu_venda"].iloc[0] == 1990.20


def test_cotas_fundo_com_zip_local(monkeypatch, tmp_path):
    z = tmp_path / "inf.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("inf_diario_fi_202610.csv", INF_NOVO.encode("latin-1"))
    monkeypatch.setattr(dp, "_informe_mes", lambda a, m: dp.ler_informe_diario(zipfile.ZipFile(z).read("inf_diario_fi_202610.csv")))
    c = dp.cotas_fundo("11111111000111", "2026-09-30", "2026-10-01")
    assert list(c["cota"]) == [1.5, 1.501]


# --------------------------------------------------------------------------- rede

def _alcanca(url: str) -> None:
    try:
        requests.get(url, timeout=20, headers=dp.UA)
    except requests.RequestException as e:
        host = url.split("/")[2]
        pytest.skip(f"rede bloqueada ou fora do ar: {host} ({type(e).__name__})")


@pytest.mark.rede
def test_rede_cdi_e_calendario():
    _alcanca("https://api.bcb.gov.br/")
    fim = dt.date.today()
    ini = fim - dt.timedelta(days=730)
    s = dp.cdi_diario(ini, fim)
    assert 0.01 < s.iloc[-1] < 0.1  # % ao dia
    # o calendário local tem que bater com os dias em que o BC publicou CDI
    ultimo = s.index[-1].date()
    assert [d.date() for d in s.index] == dp.dias_uteis(s.index[0].date(), ultimo + dt.timedelta(days=1))
    r12 = dp.cdi_acumulado(fim - dt.timedelta(days=365), fim)
    assert 0.03 < r12 < 0.25


@pytest.mark.rede
def test_rede_selic_ipca():
    _alcanca("https://api.bcb.gov.br/")
    fim = dt.date.today()
    assert not dp.selic_meta(fim - dt.timedelta(days=60), fim).empty
    assert -0.05 < dp.ipca_acumulado(fim - dt.timedelta(days=400), fim) < 0.2


@pytest.mark.rede
def test_rede_focus():
    _alcanca("https://olinda.bcb.gov.br/")
    df = dp.focus_mais_recente()
    assert {"IPCA", "Selic"} <= set(df["indicador"])
    assert (dt.date.today() - df["data"].max()).days < 15


@pytest.mark.rede
def test_rede_cvm_maior_fundo_12m():
    _alcanca("https://dados.cvm.gov.br/")
    r = dp.exemplo(12)
    assert r["pl_final"] > 1e9 and r["dias_uteis"] > 200
    assert -0.5 < r["retorno_fundo"] < 1.0


@pytest.mark.rede
def test_rede_tesouro():
    _alcanca("https://www.tesourotransparente.gov.br/")
    tit = dp.titulos_disponiveis()
    assert "Tesouro Selic" in set(tit["titulo"])
    venc = tit[tit["titulo"] == "Tesouro IPCA+"].sort_values("ultima_data")["vencimento"].iloc[-1]
    assert not dp.tesouro("Tesouro IPCA+", venc).empty
