#!/usr/bin/env python3
"""Gera um mês SINTÉTICO dos Dados Abertos do CNPJ, no layout que o pipeline.py lê (zips sem cabeçalho,
separador ';', latin-1), para testar a esteira sem a Receita. Nenhum dado é real: empresas, domínios e
sócios são inventados. Os sócios pessoa física têm nome de propósito, para o teste conferir que nenhum
nome de pessoa chega às saídas.

Uso:
  python gerar_receita.py --saida zips/2026-09
  python gerar_receita.py --saida zips/2026-10 --mes2      # o mês seguinte, com as mudanças plantadas

Casos plantados (o teste da esteira usa cada um):
  ALFA      PJ estrangeira, software, site rico (matriz no exterior, comex, vaga-alvo, e-mail de função)
  BETA      logística, robots.txt proíbe tudo
  DEEL      concorrente pelo NOME (está no concorrentes.csv); passa no filtro de nome do pipeline
  ZULU      concorrente pelo DOMÍNIO do e-mail (ebury.com)
  GAMA      agência; o site tem e-mail pessoal, perfil /in/ e página da empresa no LinkedIn
  DELTA     consultoria no AM (para o teste de UF no icp.ini)
  EPSILON   trading; no mês 2 ganha sócio PJ estrangeiro e entra
  ETA       software; no mês 2 fica inapta e sai
  IOTA      agente de carga; no mês 2 o capital sobe de 200 mil para 50 mi (a nota muda)
  KAPPA     e-mail no Gmail (o site não é visitado)
  OMEGAnn   empresas comuns para encher a lista (sites simples)
"""
from __future__ import annotations

import argparse
import csv
import io
import zipfile
from pathlib import Path

CONTADOR = [f"9{i:07d}" for i in range(25)]   # 25 empresas fora do universo com o mesmo domínio de contador


def _zip(pasta: Path, nome_zip: str, linhas: list[list[str]]) -> None:
    buf = io.StringIO()
    csv.writer(buf, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator="\n").writerows(linhas)
    with zipfile.ZipFile(pasta / nome_zip, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"K3241.K03200Y0.D61011.{nome_zip[:-4].upper()}CSV", buf.getvalue().encode("latin-1"))


def _estab(basico, ordem, dv, matriz, fantasia, sit, inicio, cnae, sec, email, uf="SP", mun="7107"):
    return [basico, ordem, dv, matriz, fantasia, sit, "20200101", "00", "", "", inicio, cnae, sec,
            "RUA", "EXEMPLO", "1", "", "CENTRO", "01000000", uf, mun, "11", "00000000", "", "", "", "",
            email, "", ""]


# basico, razão social, capital, porte, fantasia, cnae, e-mail, início, sócio estrangeiro (nome, qualif., país), uf
EMPRESAS = [
    ("11111111", "ALFA SOFTWARE TESTE LTDA", "5000000,00", "05", "ALFA", "6201501", "contato@alfa-teste.com.br", "20230115", ("ALFA HOLDINGS INC", "37", "901"), "SP"),
    ("22222222", "BETA LOGISTICA TESTE LTDA", "800000,00", "05", "BETA", "5250803", "comercial@beta-teste.com.br", "20210301", ("BETA FREIGHT LLC", "37", "902"), "SP"),
    ("33333333", "DEEL BRASIL TESTE LTDA", "3000000,00", "05", "DEEL", "6201501", "contato@deel-teste.com.br", "20220101", ("DEEL WORLD INC", "37", "901"), "SP"),
    ("34343434", "ZULU SERVICOS DIGITAIS TESTE LTDA", "3000000,00", "05", "ZULU", "6204000", "br@ebury.com", "20220101", ("ZULU GROUP LTD", "37", "902"), "SP"),
    ("44444444", "GAMA AGENCIA TESTE LTDA", "600000,00", "05", "GAMA", "7311400", "contato@gama-teste.com.br", "20190101", ("GAMA ADS INC", "37", "901"), "RJ"),
    ("55555555", "DELTA CONSULTORIA TESTE LTDA", "900000,00", "05", "DELTA", "7020400", "contato@delta-teste.com.br", "20180101", ("DELTA PARTNERS LLC", "37", "901"), "AM"),
    ("66666666", "EPSILON TRADING TESTE LTDA", "1500000,00", "05", "EPSILON", "4693100", "contato@epsilon-teste.com.br", "20170101", None, "SC"),
    ("77777777", "ETA SOFTWARE TESTE LTDA", "1200000,00", "05", "ETA", "6201501", "contato@eta-teste.com.br", "20200101", ("ETA GLOBAL GMBH", "37", "902"), "SP"),
    ("88888888", "IOTA CARGAS TESTE LTDA", "200000,00", "05", "IOTA", "5250803", "contato@iota-teste.com.br", "20160101", ("IOTA LOGISTICS BV", "37", "902"), "SP"),
    ("99999999", "KAPPA TI TESTE LTDA", "2000000,00", "05", "KAPPA", "6204000", "fiscal.kappa@gmail.com", "20200101", ("KAPPA INTERNATIONAL INC", "37", "901"), "SP"),
] + [
    (f"5{i:07d}", f"OMEGA{i:02d} SISTEMAS TESTE LTDA", f"{150000 + 50000 * i},00", "03", f"OMEGA{i:02d}", "6201501",
     f"contato@omega{i:02d}-teste.com.br", "20150101", (f"OMEGA{i:02d} PARENT INC", "37", "901"), "PR")
    for i in range(1, 9)
]
SOCIOS_PF = [  # nomes de pessoa inventados: o teste confere que não aparecem em nenhuma saída
    ("11111111", "PESSOA FICTICIA EXEMPLO", "05"),
    ("44444444", "OUTRA PESSOA INVENTADA", "38"),
]


def gerar(pasta: Path, mes2: bool = False) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    _zip(pasta, "Qualificacoes.zip", [["05", "Administrador"], ["22", "Sócio"],
                                      ["37", "Sócio Pessoa Jurídica Domiciliado no Exterior"],
                                      ["38", "Sócio Pessoa Física Residente no Exterior"],
                                      ["49", "Sócio-Administrador"]])
    _zip(pasta, "Naturezas.zip", [["2062", "Sociedade Empresária Limitada"],
                                  ["2151", "Estabelecimento, no Brasil, de Sociedade Estrangeira"]])
    _zip(pasta, "Paises.zip", [["105", "BRASIL"], ["901", "PAIS FICTICIO A"], ["902", "PAIS FICTICIO B"]])
    _zip(pasta, "Cnaes.zip", [["6201501", "Desenvolvimento de programas de computador sob encomenda"],
                              ["6204000", "Consultoria em tecnologia da informação"],
                              ["5250803", "Agenciamento de cargas, exceto para o transporte marítimo"],
                              ["7311400", "Agências de publicidade"],
                              ["7020400", "Atividades de consultoria em gestão empresarial"],
                              ["4693100", "Comércio atacadista de mercadorias em geral"],
                              ["4711302", "Comércio varejista de mercadorias em geral (fixture)"]])
    _zip(pasta, "Municipios.zip", [["7107", "SAO PAULO"], ["0255", "MANAUS"], ["6001", "RIO DE JANEIRO"],
                                   ["8105", "FLORIANOPOLIS"], ["7535", "CURITIBA"]])
    _zip(pasta, "Motivos.zip", [["00", "SEM MOTIVO"]])

    mun = {"SP": "7107", "AM": "0255", "RJ": "6001", "SC": "8105", "PR": "7535"}
    emp, soc, est = [], [], []
    for basico, razao, capital, porte, fantasia, cnae, email, inicio, estrangeiro, uf in EMPRESAS:
        if mes2 and basico == "88888888":
            capital = "50000000,00"
        emp.append([basico, razao, "2062", "49", capital, porte, ""])
        if estrangeiro:
            soc.append([basico, "1", estrangeiro[0], "00000000000000", estrangeiro[1], "20200101", estrangeiro[2], "", "", "00", "0"])
        sit = "08" if (mes2 and basico == "77777777") else "02"
        est.append(_estab(basico, "0001", "01", "1", fantasia, sit, inicio, cnae, "", email, uf, mun[uf]))
    if mes2:
        soc.append(["66666666", "1", "EPSILON TRADE CO LTD", "00000000000000", "37", "20260920", "902", "", "", "00", "0"])
    for basico, nome, qualif in SOCIOS_PF:
        soc.append([basico, "2", nome, "***123456**", qualif, "20200101", "902" if qualif == "38" else "", "", "", "00", "5"])
    for f in CONTADOR:
        emp.append([f, f"VAREJO {f} TESTE LTDA", "2062", "49", "10000,00", "01", ""])
        est.append(_estab(f, "0001", "01", "1", "", "02", "20100101", "4711302", "", f"x{f}@contabil-exemplo.com.br"))

    meio = len(emp) // 2
    _zip(pasta, "Empresas0.zip", emp[:meio])
    _zip(pasta, "Empresas1.zip", emp[meio:])
    _zip(pasta, "Socios0.zip", soc)
    _zip(pasta, "Simples.zip", [["11111111", "N", "", "", "N", "", ""]])
    meio = len(est) // 2
    _zip(pasta, "Estabelecimentos0.zip", est[:meio])
    _zip(pasta, "Estabelecimentos1.zip", est[meio:])
    return pasta


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--saida", type=Path, required=True, help="pasta dos zips (ex.: zips/2026-10)")
    ap.add_argument("--mes2", action="store_true", help="o mês seguinte, com as mudanças plantadas")
    a = ap.parse_args(argv)
    print(f"ok: {gerar(a.saida, a.mes2)}")


if __name__ == "__main__":
    main()
