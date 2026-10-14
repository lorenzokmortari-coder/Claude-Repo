"""Teste de ponta a ponta do pipeline com arquivos SINTÉTICOS no layout da Receita.

Nenhum dado aqui é real: as empresas, nomes e códigos de país são inventados só
para exercitar os filtros, a nota e o diff. Rodar: python -m pytest -q test_pipeline.py
"""
import csv
import datetime as dt
import io
import zipfile
from pathlib import Path

import pipeline as pl

HOJE = dt.date(2026, 10, 14)
FILLERS = [f"9{i:07d}" for i in range(25)]  # 25 empresas fora do universo com o mesmo domínio de contador


def _zip(pasta: Path, nome_zip: str, linhas: list[list[str]]) -> None:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator="\n")
    w.writerows(linhas)
    with zipfile.ZipFile(pasta / nome_zip, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"K3241.K03200Y0.D61011.{nome_zip[:-4].upper()}CSV", buf.getvalue().encode("latin-1"))


def _estab(basico, ordem, dv, matriz, fantasia, sit, inicio, cnae, sec, email):
    return [basico, ordem, dv, matriz, fantasia, sit, "20200101", "00", "", "", inicio, cnae, sec,
            "RUA", "EXEMPLO", "1", "", "CENTRO", "01000000", "SP", "7107", "11", "00000000", "", "", "", "",
            email, "", ""]


def montar_mes(pasta: Path, mes2: bool) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    _zip(pasta, "Qualificacoes.zip", [["05", "Administrador"], ["22", "Sócio"],
                                      ["37", "Sócio Pessoa Jurídica Domiciliado no Exterior"],
                                      ["38", "Sócio Pessoa Física Residente no Exterior"],
                                      ["49", "Sócio-Administrador"]])
    _zip(pasta, "Naturezas.zip", [["2062", "Sociedade Empresária Limitada"],
                                  ["2151", "Estabelecimento, no Brasil, de Sociedade Estrangeira"],
                                  ["1031", "Órgão Público do Poder Executivo Municipal"]])
    _zip(pasta, "Paises.zip", [["105", "BRASIL"], ["901", "PAIS FICTICIO A"], ["902", "PAIS FICTICIO B"]])
    _zip(pasta, "Cnaes.zip", [["6201501", "Desenvolvimento de programas de computador sob encomenda"],
                              ["5250803", "Agenciamento de cargas, exceto para o transporte marítimo"],
                              ["7020400", "Consultoria em gestão empresarial (fixture)"],
                              ["6204000", "Consultoria em tecnologia da informação"]])
    _zip(pasta, "Municipios.zip", [["7107", "SAO PAULO"]])
    _zip(pasta, "Motivos.zip", [["00", "SEM MOTIVO"]])

    emp = [
        ["11111111", "ALFA SOFTWARE TESTE LTDA", "2062", "49", "5000000,00", "05", ""],
        ["22222222", "BETA LOGISTICA TESTE LTDA", "2062", "49", "800000,00", "03", ""],
        ["33333333", "GAMA COMERCIO TESTE LTDA", "2062", "49", "50000,00", "05", ""],
        ["44444444", "DELTA PAGAMENTOS TESTE LTDA", "2062", "49", "9000000,00", "05", ""],
        ["55555555", "EPSILON CONSULTORIA TESTE LTDA", "2062", "49", "200000,00", "01", ""],
        ["66666666", "ZETA PUBLICIDADE TESTE LTDA", "2062", "49", "300000,00", "05", ""],
        ["77777777", "ETA TI TESTE LTDA", "2062", "49", "1000000,00", "05", ""],
        ["88888888", "ETA PARTICIPACOES TESTE LTDA", "2062", "49", "1000000,00", "05", ""],
        ["99999999", "TETA ORGAO TESTE", "1031", "49", "1000000,00", "05", ""],
        ["12121212", "IOTA BRASIL FILIAL TESTE", "2151", "49", "2000000,00", "05", ""],
        ["13131313", "KAPPA SOFTWARE TESTE LTDA", "2062", "49", "2000000,00", "05", ""],
    ] + [[f, f"FILLER {f} TESTE LTDA", "2062", "49", "10000,00", "01", ""] for f in FILLERS]
    _zip(pasta, "Empresas0.zip", emp[:6])
    _zip(pasta, "Empresas1.zip", emp[6:])

    soc = [
        ["11111111", "1", "ALFA HOLDINGS INC", "00000000000000", "37", "20230115", "901", "", "", "00", "0"],
        ["22222222", "3", "JOHN EXEMPLO FICTICIO", "***999999**", "38", "20210301", "902", "", "", "00", "4"],
        ["33333333", "1", "GAMA PARENT LLC", "00000000000000", "37", "20200101", "901", "", "", "00", "0"],
        ["44444444", "1", "DELTA GLOBAL LTD", "00000000000000", "37", "20200101", "901", "", "", "00", "0"],
        ["55555555", "1", "EPSILON WORLD INC", "00000000000000", "37", "20200101", "901", "", "", "00", "0"],
        ["66666666", "1", "ZETA ADS INC", "00000000000000", "37", "20200101", "901", "", "", "00", "0"],
        ["77777777", "1", "ETA PARTICIPACOES TESTE LTDA", "88888888000199", "22", "20200101", "", "", "", "00", "0"],
        ["88888888", "1", "ETA GLOBAL GMBH", "00000000000000", "37", "20190101", "902", "", "", "00", "0"],
        ["99999999", "1", "TETA FOREIGN CORP", "00000000000000", "37", "20200101", "901", "", "", "00", "0"],
        ["13131313", "1", "KAPPA INTERNATIONAL INC", "00000000000000", "37", "20200101", "901", "", "", "00", "0"],
        ["11111111", "2", "MARIA BRASILEIRA FICTICIA", "***111111**", "05", "20230115", "", "", "", "00", "5"],
    ]
    if mes2:
        soc.append(["22222222", "1", "BETA WORLDWIDE LLC", "00000000000000", "37", "20260920", "901", "", "", "00", "0"])
    _zip(pasta, "Socios0.zip", soc)

    _zip(pasta, "Simples.zip", [["55555555", "S", "20200101", "", "N", "", ""],
                                ["11111111", "N", "", "", "N", "", ""]])

    est = [
        _estab("11111111", "0001", "91", "1", "ALFA", "02", "20230115", "6201501", "", "contato@alfasoft-teste.com.br"),
        _estab("22222222", "0001", "01", "1", "", "02", "20210301", "5250803", "", "fulano@gmail.com"),
        _estab("33333333", "0001", "01", "1", "", "02", "20200101", "6201501", "", ""),
        _estab("44444444", "0001", "01", "1", "", "02", "20200101", "6201501", "", ""),
        _estab("55555555", "0001", "01", "1", "", "02", "20200101", "7020400", "", ""),
        _estab("66666666", "0001", "01", "1", "", "08", "20200101", "7311400", "", ""),
        _estab("77777777", "0001", "01", "1", "ETA", "02", "20180601", "6204000", "", "fiscal@contabil-exemplo.com.br"),
        _estab("88888888", "0001", "01", "1", "", "02", "20180601", "6462000", "", ""),
        _estab("99999999", "0001", "01", "1", "", "02", "20200101", "6201501", "", ""),
        _estab("12121212", "0001", "01", "1", "IOTA", "02", "20150101", "6204000" if mes2 else "7020400", "", ""),
        _estab("13131313", "0001", "01", "1", "", "02", "20200101", "6201501", "6619399,6202300", ""),
    ] + [_estab(f, "0001", "01", "1", "", "02", "20100101", "4711302", "", f"x{f}@contabil-exemplo.com.br")
         for f in FILLERS]
    if mes2:
        est.append(_estab("11111111", "0002", "80", "2", "ALFA RJ", "02", "20260901", "6201501", "", ""))
    _zip(pasta, "Estabelecimentos0.zip", est[:7])
    _zip(pasta, "Estabelecimentos1.zip", est[7:])
    return pasta


def _ler(p: Path) -> list[dict]:
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_ponta_a_ponta(tmp_path: Path):
    fonte1 = montar_mes(tmp_path / "zips1", mes2=False)
    fonte2 = montar_mes(tmp_path / "zips2", mes2=True)
    s1 = pl.rodar("2026-09", tmp_path / "saida", fonte1, hoje=HOJE)
    s2 = pl.rodar("2026-10", tmp_path / "saida", fonte2, hoje=HOJE)

    top = {r["cnpj"]: r for r in _ler(s1 / "top1000.csv")}
    assert set(top) == {"11111111000191", "22222222000101", "77777777000101", "12121212000101"}

    alfa = top["11111111000191"]
    assert alfa["tipo_socio_estrangeiro"] == "PJ estrangeira"
    assert alfa["empresa_estrangeira_socia"] == "ALFA HOLDINGS INC"
    assert alfa["pais_socio_estrangeiro"] == "PAIS FICTICIO A"
    assert alfa["marca_email"] == "próprio" and alfa["dominio_email"] == "alfasoft-teste.com.br"
    # 30 (PJ) + 25*1.0 (software) + 20*(log10(5e6)-5)/3 + 10 (porte demais) + 8 (3,7 anos) + 0 (1 estab.)
    assert abs(float(alfa["nota"]) - 84.3) < 0.05

    beta = top["22222222000101"]
    assert beta["tipo_socio_estrangeiro"] == "PF estrangeira" and beta["empresa_estrangeira_socia"] == ""
    assert beta["marca_email"] == "provável contador (domínio genérico)"

    eta = top["77777777000101"]
    assert eta["tipo_socio_estrangeiro"] == "PJ estrangeira via holding BR"
    assert eta["empresa_estrangeira_socia"] == "ETA GLOBAL GMBH"
    assert eta["marca_email"].startswith("provável contador (domínio em 26")

    assert top["12121212000101"]["tipo_socio_estrangeiro"] == "filial de sociedade estrangeira"
    assert float(alfa["nota"]) > float(beta["nota"])

    cont = _ler(s1 / "contagens.csv")
    assert {r["dimensao"] for r in cont} == {"cnae", "uf"}
    assert [r for r in cont if r["dimensao"] == "uf"][0]["n_empresas"] == "4"

    # Privacidade: nenhum nome de PF nem endereço de e-mail completo em nenhuma saída
    for saida in (s1, s2):
        for arq in saida.rglob("*"):
            if arq.is_file():
                dados = arq.read_bytes()
                for proibido in (b"JOHN EXEMPLO", b"MARIA BRASILEIRA", b"fulano@", b"contato@"):
                    assert proibido not in dados, (arq, proibido)

    pl.diff(s1, s2)
    nov = _ler(s2 / "novidades.csv")
    eventos = {(r["cnpj_basico"], r["evento"]) for r in nov}
    assert ("22222222", "ganhou_socio_estrangeiro") in eventos
    assert ("11111111", "abriu_filial") in eventos
    assert ("12121212", "mudou_cnae_principal") in eventos
    assert len(nov) == 3

    # No mês 2 a BETA passa a ter PJ estrangeira e sobe de nota
    top2 = {r["cnpj"]: r for r in _ler(s2 / "top1000.csv")}
    assert top2["22222222000101"]["tipo_socio_estrangeiro"] == "PJ estrangeira"
    assert float(top2["22222222000101"]["nota"]) > float(beta["nota"])
