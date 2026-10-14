"""Teste offline do diff do vigia_bc com dois retratos SINTÉTICOS (nomes de campo e empresas inventados).
Rodar: python -m pytest -q test_vigia_bc.py"""
import pandas as pd
import pytest
import requests

import vigia_bc as vb

ANTES = pd.DataFrame({
    "cnpj8": ["11111111", "22222222", "33333333"],
    "nomeEntidade": ["ALFA CORRETORA DE CAMBIO S.A.", "BETA PAGAMENTOS IP S.A.", "GAMA COOPERATIVA DE CREDITO"],
    "tipoEntidade": ["Corretora de câmbio", "Instituição de pagamento", "Cooperativa de crédito"],
    "situacao": ["Normal", "Normal", "Normal"],
}).astype("string")
DEPOIS = pd.DataFrame({
    "cnpj8": ["11111111", "33333333", "44444444"],
    "nomeEntidade": ["ALFA CORRETORA DE CAMBIO S.A.", "GAMA COOPERATIVA DE CREDITO", "DELTA BANCO DE CAMBIO S.A."],
    "tipoEntidade": ["Corretora de câmbio", "Cooperativa de crédito", "Banco de câmbio"],
    "situacao": ["Em liquidação", "Normal", "Normal"],
}).astype("string")


def test_comparar():
    ev = vb.comparar(ANTES, DEPOIS)
    got = {(r.evento, r.chave, r.campo) for r in ev.itertuples()}
    assert got == {("entrou", "44444444", ""), ("saiu", "22222222", ""), ("mudou", "11111111", "situacao")}
    assert vb.coluna_chave(DEPOIS) == "cnpj8" and vb.coluna_nome(DEPOIS) == "nomeEntidade"


def test_filtro_cambio_pagamentos():
    f = vb.so_cambio_pagamentos(ANTES)
    assert set(f["cnpj8"]) == {"11111111", "22222222"}


@pytest.mark.rede
def test_rede_esquema_e_amostra():
    try:
        requests.get("https://olinda.bcb.gov.br/", timeout=20)
    except requests.RequestException as e:
        pytest.skip(f"rede bloqueada ou fora do ar: olinda.bcb.gov.br ({type(e).__name__})")
    assert vb.RECURSO in vb.esquema()
    r = vb._get(vb.BASE + vb.RECURSO, {"$format": "json", "$top": "5"})
    assert len(r.json()["value"]) == 5
