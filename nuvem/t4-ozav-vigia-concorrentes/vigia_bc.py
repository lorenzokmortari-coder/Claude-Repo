#!/usr/bin/env python3
"""vigia_bc: quem entrou e quem saiu do cadastro de entidades supervisionadas do Banco Central.

Fonte: Portal de Dados Abertos do BC, conjunto "Dados cadastrais de entidades supervisionadas"
(serviço Olinda BcBase v2, recurso EntidadesSupervisionadas, atualização diária a partir do Unicad).

O script não depende de nomes de campo decorados: ele lê o $metadata, guarda o retrato do dia
inteiro em CSV e compara com o retrato anterior pela coluna de CNPJ.

Uso:
  python vigia_bc.py esquema                    # lista recursos e campos do serviço
  python vigia_bc.py baixar                     # grava retratos/AAAA-MM-DD.csv
  python vigia_bc.py diff                       # compara os dois retratos mais recentes
  python vigia_bc.py diff --so-cambio-pagamentos
  python vigia_bc.py diff --antes retratos/2026-10-13.csv --depois retratos/2026-10-14.csv
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
import time
import urllib.parse
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import requests

BASE = "https://olinda.bcb.gov.br/olinda/servico/BcBase/versao/v2/odata/"
RECURSO = "EntidadesSupervisionadas"
PASTA = Path("retratos")
UA = {"User-Agent": "vigia-bc/1.0 (dados abertos)", "Accept": "application/json"}
RX_CAMBIO_PAGAMENTOS = r"CAMBIO|PAGAMENTO|ATIVOS VIRTUAIS|CREDITO DIRETO|EMPRESTIMO ENTRE PESSOAS"


def _qs(params: dict | None) -> str | None:
    """Query string com `$` literal (padrão OData) e espaço como %20."""
    if not params:
        return None
    return urllib.parse.urlencode(params, safe="$',()", quote_via=urllib.parse.quote)


def _get(url: str, params: dict | None = None, tentativas: int = 4) -> requests.Response:
    for i in range(tentativas):
        try:
            r = requests.get(url, params=_qs(params), headers=UA, timeout=120)
            r.raise_for_status()
            return r
        except requests.RequestException:
            if i == tentativas - 1:
                raise
            time.sleep(2 ** (i + 1))
    raise RuntimeError("inalcançável")


def sem_acento(s) -> str:
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().upper()


# --------------------------------------------------------------------------- leitura

def esquema(base: str = BASE) -> dict[str, list[str]]:
    """Recursos (EntitySet) e campos de cada tipo, lidos do $metadata do serviço."""
    raiz = ET.fromstring(_get(base + "$metadata").content)
    tipos = {}
    for el in raiz.iter():
        if el.tag.endswith("EntityType"):
            tipos[el.get("Name")] = [p.get("Name") for p in el if p.tag.endswith("Property")]
    out = {}
    for el in raiz.iter():
        if el.tag.endswith("EntitySet"):
            nome_tipo = (el.get("EntityType") or "").rsplit(".", 1)[-1]
            out[el.get("Name")] = tipos.get(nome_tipo, [])
    return out or tipos


def baixar(recurso: str = RECURSO, base: str = BASE, passo: int = 5000) -> pd.DataFrame:
    """Baixa o recurso inteiro com paginação OData ($top/$skip)."""
    linhas, skip = [], 0
    while True:
        r = _get(base + recurso, {"$format": "json", "$top": str(passo), "$skip": str(skip)})
        lote = r.json().get("value", [])
        linhas += lote
        if len(lote) < passo:
            break
        skip += passo
    return pd.DataFrame(linhas).astype("string")


def coluna_chave(df: pd.DataFrame) -> str:
    """Coluna de CNPJ (prefere a de 8 dígitos); se não houver, a primeira coluna."""
    cands = [c for c in df.columns if "cnpj" in c.lower()]
    cands.sort(key=lambda c: ("8" not in c, len(c)))
    return cands[0] if cands else df.columns[0]


def coluna_nome(df: pd.DataFrame) -> str | None:
    cands = [c for c in df.columns if re.search(r"nome|razao|denomina", c, re.I)]
    return min(cands, key=len) if cands else None


# --------------------------------------------------------------------------- diff

def so_cambio_pagamentos(df: pd.DataFrame) -> pd.DataFrame:
    """Linhas cujo texto (tipo, segmento, nome) fala de câmbio, pagamento, ativos virtuais ou crédito direto."""
    texto = df.astype(str).apply(lambda r: sem_acento(" ".join(r.values)), axis=1)
    return df[texto.str.contains(RX_CAMBIO_PAGAMENTOS, regex=True)]


def comparar(antes: pd.DataFrame, depois: pd.DataFrame, chave: str | None = None) -> pd.DataFrame:
    """Entradas, saídas e mudanças de campo entre dois retratos."""
    chave = chave or coluna_chave(depois)
    nome = coluna_nome(depois) or chave
    a = antes.drop_duplicates(chave).set_index(chave)
    d = depois.drop_duplicates(chave).set_index(chave)
    ev = []
    for k in d.index.difference(a.index):
        ev.append({"evento": "entrou", "chave": k, "nome": d.at[k, nome] if nome in d else "", "campo": "", "antes": "", "depois": ""})
    for k in a.index.difference(d.index):
        ev.append({"evento": "saiu", "chave": k, "nome": a.at[k, nome] if nome in a else "", "campo": "", "antes": "", "depois": ""})
    comuns = d.index.intersection(a.index)
    for c in sorted(set(a.columns) & set(d.columns)):
        va, vd = a.loc[comuns, c].fillna(""), d.loc[comuns, c].fillna("")
        for k in comuns[(va != vd).values]:
            ev.append({"evento": "mudou", "chave": k, "nome": d.at[k, nome] if nome in d else "", "campo": c,
                       "antes": va.at[k], "depois": vd.at[k]})
    return pd.DataFrame(ev, columns=["evento", "chave", "nome", "campo", "antes", "depois"])


def retratos(pasta: Path = PASTA) -> list[Path]:
    return sorted(pasta.glob("????-??-??.csv"))


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("esquema")
    b = sub.add_parser("baixar")
    b.add_argument("--recurso", default=RECURSO)
    b.add_argument("--pasta", type=Path, default=PASTA)
    d = sub.add_parser("diff")
    d.add_argument("--antes", type=Path)
    d.add_argument("--depois", type=Path)
    d.add_argument("--pasta", type=Path, default=PASTA)
    d.add_argument("--so-cambio-pagamentos", action="store_true")
    a = ap.parse_args(argv)

    if a.cmd == "esquema":
        for recurso, campos in esquema().items():
            print(f"{recurso}: {', '.join(campos)}")
    elif a.cmd == "baixar":
        df = baixar(a.recurso)
        a.pasta.mkdir(parents=True, exist_ok=True)
        destino = a.pasta / f"{dt.date.today():%Y-%m-%d}.csv"
        df.to_csv(destino, index=False)
        print(f"{len(df)} entidades, {len(df.columns)} campos -> {destino}")
        print("campos:", ", ".join(df.columns))
    else:
        if a.antes and a.depois:
            pa, pd_ = a.antes, a.depois
        else:
            rs = retratos(a.pasta)
            if len(rs) < 2:
                sys.exit("preciso de dois retratos: rode 'baixar' em dois dias diferentes")
            pa, pd_ = rs[-2], rs[-1]
        antes, depois = (pd.read_csv(p, dtype="string") for p in (pa, pd_))
        if a.so_cambio_pagamentos:
            antes, depois = so_cambio_pagamentos(antes), so_cambio_pagamentos(depois)
        ev = comparar(antes, depois)
        destino = pd_.with_name(f"novidades_{pa.stem}_a_{pd_.stem}.csv")
        ev.to_csv(destino, index=False)
        print(ev.groupby("evento").size().to_string() if len(ev) else "nenhuma mudança")
        print("->", destino)


if __name__ == "__main__":
    main()
