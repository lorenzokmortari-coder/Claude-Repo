#!/usr/bin/env python3
"""Ozav · esteira mensal de prospecção (14/10/2026).

Um comando só encadeia as quatro peças que já existiam:
  1. cnpj   pipeline.py (pipeline CNPJ v2): Dados Abertos da Receita de uma pasta local -> base_pontuada.parquet
  2. icp    filtro de ICP do icp.ini (que o dono edita) + exclusão dos concorrentes (concorrentes.csv do vigia,
            exclusao_extra.csv do dono e, se houver, o retrato do cadastro do BC)
  3. site   enriquecer_site.py nos candidatos (robots.txt respeitado, 1 pedido por segundo por domínio, só e-mail
            de função, LinkedIn nunca visitado)
  4. nota   nota final = peso_cnpj x nota CNPJ + peso_site x nota do site, com o motivo em uma linha
  5. saídas top1000.csv, novidades.md (entrou, saiu e mudou desde o mês anterior + o bloco do vigia de
            concorrentes) e crm.jsonl (um registro por empresa, para o PC subir pela API)

A esteira nunca escreve no CRM, nunca manda mensagem e não acessa rede nenhuma além dos sites das empresas na
etapa 3. Retomada: a etapa cnpj não refaz um mês já processado e a etapa site guarda cada domínio no cache assim
que termina; se a rodada cair no meio, o mesmo comando recomeça de onde parou.

Uso (no PC, com o mês já baixado):
  python esteira.py --mes 2026-10 --fonte-local C:/Users/.../ozav-cnpj/zips/2026-10
  python esteira.py --mes 2026-10 --fonte-local ... --config icp.ini --dir saida --workers 6
Saídas em <dir>/<mes>/esteira/.
"""
from __future__ import annotations

import argparse
import configparser
import csv
import datetime as dt
import json
import math
import os
import re
import sys
import time
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

import enriquecer_site as es  # noqa: E402
import pipeline as pl  # noqa: E402

CONFIG_PADRAO = AQUI / "icp.ini"
INTERVALO_MIN_S = es.INTERVALO_MIN_S          # 1 pedido por segundo por domínio (regra do dono)

VINCULO = {"PJ": "PJ estrangeira", "PJ_INDIRETO": "PJ estrangeira via holding BR",
           "FILIAL_SOC_ESTRANGEIRA": "filial de sociedade estrangeira", "ND": "estrangeiro (tipo não identificado)",
           "PF": "PF estrangeira"}
SINAIS_TEXTO = {"sinal_matriz_exterior": "matriz no exterior", "sinal_comex": "comércio exterior",
                "sinal_importa": "importa", "sinal_exporta": "exporta", "sinal_clientes_exterior": "clientes no exterior",
                "escritorio_exterior": "escritório no exterior", "menciona_cambio": "fala de câmbio",
                "sinal_global": "se diz global", "vagas_alvo": "vaga de comex/finanças"}

COLUNAS_TOP = ["posicao", "cnpj", "razao_social", "nome_fantasia", "uf", "municipio", "cnae_principal", "grupo_cnae",
               "capital_social", "porte", "data_inicio", "vinculo_estrangeiro", "pais_socio_estrangeiro",
               "empresa_estrangeira_socia", "site", "email_funcao", "emails_funcao", "nota", "nota_cnpj", "nota_site",
               "motivo", "status_site", "sinais_site"]


def log(msg: str) -> None:
    print(f"[{dt.datetime.now():%H:%M:%S}] {msg}", flush=True)


# --------------------------------------------------------------------------- configuração

def _lista(v: str) -> list[str]:
    return [x.strip() for x in (v or "").split(",") if x.strip()]


def ler_config(caminho: Path | None = None) -> dict:
    """O icp.ini (configparser: vem com o Python, aceita comentário com #). Caminhos relativos valem a partir da
    pasta do próprio arquivo."""
    caminho = Path(caminho or CONFIG_PADRAO)
    cp = configparser.ConfigParser(inline_comment_prefixes=("#",), interpolation=None)
    if not cp.read(caminho, encoding="utf-8"):
        raise SystemExit(f"Não achei a configuração {caminho}")
    base = caminho.resolve().parent

    def g(sec, k, padrao=""):
        return cp.get(sec, k, fallback=padrao).strip()

    def arq(v):
        return (base / v) if v else None

    return {
        "ufs_incluir": [u.upper() for u in _lista(g("icp", "ufs_incluir"))],
        "ufs_excluir": [u.upper() for u in _lista(g("icp", "ufs_excluir"))],
        "capital_minimo": float(g("icp", "capital_minimo", "100000") or 0),
        "portes": [int(x) for x in _lista(g("icp", "portes", "0,1,3,5"))],
        "idade_min_anos": float(g("icp", "idade_min_anos", "0") or 0),
        "idade_max_anos": float(g("icp", "idade_max_anos", "200") or 200),
        "vinculos": _lista(g("icp", "vinculos", ",".join(VINCULO))),
        "nota_cnpj_minima": float(g("icp", "nota_cnpj_minima", "0") or 0),
        "grupos_cnae_fora": [normalizar(x) for x in _lista(g("icp", "grupos_cnae_fora"))],
        "cnae_prefixos_fora": _lista(g("icp", "cnae_prefixos_fora")),
        "so_dominio_proprio": g("icp", "so_dominio_proprio", "nao").lower() in ("sim", "s", "1", "true"),
        "concorrentes": arq(g("concorrentes", "arquivo", "concorrentes.csv")),
        "niveis": [normalizar(x) for x in _lista(g("concorrentes", "niveis", "alta,média,baixa,a verificar"))],
        "exclusao_extra": arq(g("concorrentes", "exclusao_extra", "exclusao_extra.csv")),
        "pasta_vigia_bc": arq(g("concorrentes", "pasta_vigia_bc")),
        "candidatos": int(g("site", "candidatos", "1500") or 1500),
        "workers": int(g("site", "workers", "6") or 6),
        "motor": g("site", "motor", "auto") or "auto",
        "peso_cnpj": float(g("nota", "peso_cnpj", "0.7")),
        "peso_site": float(g("nota", "peso_site", "0.3")),
        "top": int(g("nota", "top", "1000") or 1000),
        "variacao_nota": float(g("nota", "variacao_relevante", "5") or 5),
        "pontos_site": {k: float(v) for k, v in (cp.items("nota_site") if cp.has_section("nota_site") else [])},
        "arquivo": str(caminho),
    }


# --------------------------------------------------------------------------- exclusão de concorrentes

GENERICAS = set("""banco bank empresas empresa business de do da dos das e the cambio corretora pagamentos payments
pay brasil br sa s a ltda pj infra prime desk by for""".split())
AMBIGUOS = {"inter", "frente", "circle", "rendimento", "wise", "rapyd", "convera", "transfero"}
SUFIXOS_2 = {"com", "net", "org", "gov", "edu", "art", "adv", "eng", "ind", "inf", "co", "ac", "ltd", "biz", "nom"}


def normalizar(t: str) -> str:
    t = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def registravel(dominio_ou_url: str) -> str:
    """Domínio registrável, sem www e sem porta: br.ebury.com -> ebury.com; www.c6bank.com.br -> c6bank.com.br."""
    s = (dominio_ou_url or "").strip().lower()
    if "://" in s:
        s = urlsplit(s).netloc
    s = s.split("@")[-1].split("/")[0].split(":")[0].strip(".")
    partes = [p for p in s.split(".") if p]
    if len(partes) <= 2:
        return ".".join(partes)
    if partes[-2] in SUFIXOS_2 and len(partes[-1]) == 2:
        return ".".join(partes[-3:])
    return ".".join(partes[-2:])


def _chave_nome(nome: str) -> str | None:
    """Nome-chave do concorrente para casar como palavra inteira na razão social ou no fantasia. Palavra comum
    (Inter, Frente, Wise...) só casa com o nome completo; sigla curta demais (B&T, MB) fica só no domínio."""
    completo = normalizar(nome)
    toks = [t for t in completo.split() if t not in GENERICAS]
    chave = " ".join(toks)
    if not chave or chave in AMBIGUOS:
        chave = completo
    letras = re.sub(r"[^a-z]", "", chave)
    if len(letras) < 4 and not re.search(r"\d", chave):
        return None
    return chave


def ler_concorrentes(caminho: Path | None, niveis: list[str]) -> dict:
    """{"dominios": {dominio: empresa}, "nomes": [(chave, empresa)]} a partir do concorrentes.csv do vigia."""
    out = {"dominios": {}, "nomes": []}
    if not caminho or not Path(caminho).exists():
        return out
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if niveis and normalizar(r.get("concorrencia_com_ozav", "")) not in niveis:
                continue
            empresa = r.get("empresa", "").strip()
            if (r.get("site") or "").strip():
                out["dominios"][registravel(r["site"])] = empresa
            base = re.sub(r"\(.*?\)", " ", empresa)
            nomes = [base] + [m.group(2) for m in re.finditer(r"\((hoje|ex-?)\s*([^)]+)\)", empresa, re.I)]
            for n in nomes:
                chave = _chave_nome(n)
                if chave and (chave, empresa) not in out["nomes"]:
                    out["nomes"].append((chave, empresa))
    return out


def ler_exclusao_extra(caminho: Path | None) -> dict:
    """exclusao_extra.csv do dono: colunas `cnpj_raiz` e/ou `dominio`, mais `motivo` (opcional)."""
    out = {"raizes": {}, "dominios": {}}
    if not caminho or not Path(caminho).exists():
        return out
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            motivo = (r.get("motivo") or "lista do dono").strip()
            raiz = re.sub(r"\D", "", r.get("cnpj_raiz") or "")[:8]
            if raiz:
                out["raizes"][raiz] = motivo
            if (r.get("dominio") or "").strip():
                out["dominios"][registravel(r["dominio"])] = motivo
    return out


def retratos_bc(pasta: Path | None) -> list[Path]:
    if not pasta or not Path(pasta).is_dir():
        return []
    return sorted(Path(pasta).glob("????-??-??.csv"))


def raizes_bc(pasta: Path | None) -> set[str]:
    """CNPJ raiz das entidades do último retrato do cadastro do BC (vigia_bc.py baixar). Sem pandas."""
    rs = retratos_bc(pasta)
    if not rs:
        return set()
    with open(rs[-1], encoding="utf-8-sig", newline="") as f:
        leitor = csv.DictReader(f)
        cols = [c for c in (leitor.fieldnames or []) if "cnpj" in c.lower()]
        col = next((c for c in cols if "8" in c), cols[0] if cols else None)
        if not col:
            return set()
        return {re.sub(r"\D", "", r[col] or "").zfill(8)[:8] for r in leitor if re.sub(r"\D", "", r[col] or "")}


def motivo_concorrente(emp: dict, conc: dict, extra: dict, bc: set[str], dominios_site=()) -> str | None:
    raiz = (emp.get("cnpj_basico") or emp.get("cnpj", "")[:8])
    if raiz in extra["raizes"]:
        return f"exclusão do dono (CNPJ raiz): {extra['raizes'][raiz]}"
    if raiz in bc:
        return "entidade supervisionada pelo BC (retrato do vigia)"
    for d in [emp.get("dominio_email") or "", *dominios_site]:
        r = registravel(d)
        if r and r in extra["dominios"]:
            return f"exclusão do dono (domínio {r}): {extra['dominios'][r]}"
        if r and r in conc["dominios"]:
            return f"concorrente pelo domínio {r} ({conc['dominios'][r]})"
    nome = f" {normalizar(emp.get('razao_social'))} | {normalizar(emp.get('nome_fantasia'))} "
    for chave, empresa in conc["nomes"]:
        if re.search(rf"(?<![a-z0-9]){re.escape(chave)}(?![a-z0-9])", nome):
            return f"concorrente pelo nome \"{chave}\" ({empresa})"
    return None


# --------------------------------------------------------------------------- filtro de ICP

def motivo_fora_icp(e: dict, cfg: dict) -> str | None:
    uf = (e.get("uf") or "").upper()
    if cfg["ufs_incluir"] and uf not in cfg["ufs_incluir"]:
        return f"UF {uf} fora de ufs_incluir"
    if uf in cfg["ufs_excluir"]:
        return f"UF {uf} em ufs_excluir"
    if float(e.get("capital_social") or 0) < cfg["capital_minimo"]:
        return f"capital abaixo de {cfg['capital_minimo']:,.0f}"
    porte = int(e.get("porte") or 0)
    if cfg["portes"] and porte not in cfg["portes"]:
        return f"porte {porte} fora de portes"
    idade = float(e.get("idade_anos") or 0)
    if not (cfg["idade_min_anos"] <= idade <= cfg["idade_max_anos"]):
        return f"idade de {idade:.1f} anos fora da faixa"
    tipo = e.get("tipo_socio") or "PF"
    tipo = tipo if tipo in VINCULO else "PF"
    if cfg["vinculos"] and tipo not in cfg["vinculos"]:
        return f"vínculo {tipo} fora de vinculos"
    if float(e.get("nota") or 0) < cfg["nota_cnpj_minima"]:
        return f"nota CNPJ abaixo de {cfg['nota_cnpj_minima']:g}"
    if normalizar(e.get("grupo_cnae")) in cfg["grupos_cnae_fora"]:
        return f"grupo de CNAE \"{e.get('grupo_cnae')}\" fora"
    cnae = str(e.get("cnae_principal") or "")
    if any(cnae.startswith(p) for p in cfg["cnae_prefixos_fora"]):
        return f"CNAE {cnae} em cnae_prefixos_fora"
    if cfg["so_dominio_proprio"] and e.get("marca_email") != "próprio":
        return "sem domínio próprio (so_dominio_proprio = sim)"
    return None


# --------------------------------------------------------------------------- nota

def nota_site(s: dict, cfg: dict) -> tuple[float, list[str]]:
    """Pontos dos sinais do site (pesos em [nota_site] do icp.ini), de 0 a 100, e os sinais que pontuaram."""
    pts, quais = 0.0, []
    for campo, peso in cfg["pontos_site"].items():
        v = s.get(campo)
        ligado = bool(str(v).strip()) if campo == "vagas_alvo" else str(v).strip() in ("1", "True", "true")
        if ligado and peso:
            pts += peso
            txt = SINAIS_TEXTO.get(campo, campo)
            if campo == "sinal_matriz_exterior" and s.get("matriz_em"):
                txt += f" ({s['matriz_em'].split(';')[0].strip()})"
            quais.append(txt)
    return min(100.0, pts), quais


def _capital(v) -> str:
    v = float(v or 0)
    return f"R$ {v / 1e6:.1f} mi".replace(".", ",") if v >= 1e6 else f"R$ {v / 1e3:.0f} mil"


def montar_motivo(e: dict, s: dict, quais: list[str]) -> str:
    tipo = VINCULO.get(e.get("tipo_socio") or "", "PF estrangeira")
    socio = e.get("empresa_estrangeira_socia") or ""
    pais = e.get("pais_socio") or ""
    detalhe = ", ".join(x for x in (socio.split(" | ")[0], pais) if x)
    partes = [tipo + (f" ({detalhe})" if detalhe else ""),
              f"CNAE {e.get('grupo_cnae')} ({float(e.get('peso_cnae') or 0):.2f})".replace(".", ","),
              f"capital {_capital(e.get('capital_social'))}"]
    st = s.get("status_site") or ""
    if quais:
        partes.append("site: " + ", ".join(quais))
    elif st.startswith("ok"):
        partes.append("site sem sinal")
    else:
        partes.append(f"site {st}" if st else "site não visitado")
    return "; ".join(partes)


# --------------------------------------------------------------------------- arquivos

def gravar_atomico(caminho: Path, texto: str) -> None:
    tmp = caminho.with_name(caminho.name + ".tmp")
    tmp.write_text(texto, encoding="utf-8")
    os.replace(tmp, caminho)


def gravar_csv(caminho: Path, linhas: list[dict], colunas: list[str]) -> None:
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=colunas, extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    w.writerows(linhas)
    gravar_atomico(caminho, buf.getvalue())


def ler_csv(caminho: Path) -> list[dict]:
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


class Estado:
    """estado.json da rodada: o que cada etapa fez e quando (escrita atômica)."""

    def __init__(self, caminho: Path, mes: str):
        self.caminho = caminho
        try:
            self.d = json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.d = {}
        if self.d.get("mes") != mes:
            self.d = {"mes": mes, "etapas": {}}
        self.d.setdefault("etapas", {})

    def feito(self, etapa: str) -> bool:
        return etapa in self.d["etapas"]

    def marcar(self, etapa: str, **info) -> None:
        self.d["etapas"][etapa] = {"em": dt.datetime.now().isoformat(timespec="seconds"), **info}
        gravar_atomico(self.caminho, json.dumps(self.d, ensure_ascii=False, indent=1))


def ler_base(parquet: Path) -> list[dict]:
    import duckdb
    con = duckdb.connect()
    rel = con.execute(f"SELECT * FROM read_parquet('{str(parquet).replace(chr(39), chr(39) * 2)}') "
                      "ORDER BY nota DESC, capital_social DESC, cnpj")
    cols = [c[0] for c in rel.description]
    out = []
    for linha in rel.fetchall():
        d = dict(zip(cols, linha))
        for k, v in d.items():
            if isinstance(v, (dt.date, dt.datetime)):
                d[k] = v.strftime("%Y-%m-%d")
        out.append(d)
    return out


# --------------------------------------------------------------------------- novidades

def mes_anterior_esteira(pasta: Path, mes: str) -> Path | None:
    if not pasta.is_dir():
        return None
    ant = sorted(p for p in pasta.iterdir() if p.is_dir() and pl.RX_MES.fullmatch(p.name) and p.name < mes
                 and (p / "esteira" / "top1000.csv").exists())
    return ant[-1] if ant else None


def bloco_vigia(pasta: Path | None, mes: str) -> list[str]:
    """Saída do vigia de concorrentes no mês: quem entrou e saiu do cadastro do BC (câmbio e pagamentos), do
    primeiro ao último retrato do mês (ou do último retrato anterior ao mês até o último do mês)."""
    linhas = ["## Vigia de concorrentes (cadastro do BC)", ""]
    rs = retratos_bc(pasta)
    do_mes = [r for r in rs if r.stem.startswith(mes)]
    if not do_mes:
        return linhas + [f"Sem retrato do vigia em {mes}" + (f" na pasta {pasta}." if pasta else
                         " (pasta_vigia_bc vazia no icp.ini).")
                         + " Rode `python vigia_bc.py baixar` no PC para ter este bloco no mês que vem.", ""]
    antes = [r for r in rs if r.stem < mes]
    a, b = (antes[-1] if antes else do_mes[0]), do_mes[-1]
    if a == b:
        return linhas + [f"Só um retrato ({b.stem}): ainda não há com o que comparar.", ""]
    try:
        import pandas as pd
        import vigia_bc as vb
        da, db = (vb.so_cambio_pagamentos(pd.read_csv(p, dtype=str).fillna("")) for p in (a, b))
        d = vb.comparar(da, db)
    except Exception as e:  # noqa: BLE001
        return linhas + [f"Não consegui comparar {a.name} e {b.name}: {type(e).__name__}: {e}", ""]
    linhas.append(f"De {a.stem} a {b.stem}, só câmbio e pagamentos: "
                  f"{(d['evento'] == 'entrou').sum()} entraram, {(d['evento'] == 'saiu').sum()} saíram, "
                  f"{(d['evento'] == 'mudou').sum()} mudanças de campo.")
    linhas.append("")
    for ev in ("entrou", "saiu"):
        sub = d[d["evento"] == ev]
        for _, r in sub.head(30).iterrows():
            linhas.append(f"- {ev}: {r['nome'] or r['chave']} ({r['chave']})")
    return linhas + [""]


def escrever_novidades(destino: Path, mes: str, top: list[dict], anterior: Path | None, excluidos: dict,
                       base_cnpjs: set[str], fora_icp: dict, cfg: dict, pasta_cnpj: Path) -> dict:
    linhas = [f"# Novidades da esteira · {mes}", ""]
    contagem = {"entraram": 0, "sairam": 0, "mudaram": 0}
    mudancas = []
    if anterior is None:
        linhas += ["Primeiro mês da esteira nesta pasta: não há mês anterior para comparar. Todas as "
                   f"{len(top)} empresas do top são novas.", ""]
    else:
        ant = {r["cnpj"]: r for r in ler_csv(anterior / "esteira" / "top1000.csv")}
        atu = {r["cnpj"]: r for r in top}
        entraram = [atu[c] for c in atu if c not in ant]
        sairam = [ant[c] for c in ant if c not in atu]
        mudaram = []
        for c in atu:
            if c in ant:
                a, b = ant[c], atu[c]
                o_que = []
                dn = float(b["nota"]) - float(a["nota"] or 0)
                if abs(dn) >= cfg["variacao_nota"]:
                    o_que.append(f"nota {float(a['nota']):.1f} → {float(b['nota']):.1f}")
                if (a.get("site") or "") != (b.get("site") or ""):
                    o_que.append(f"site {a.get('site') or '—'} → {b.get('site') or '—'}")
                if (a.get("emails_funcao") or "") != (b.get("emails_funcao") or ""):
                    o_que.append("e-mail de função mudou")
                if o_que:
                    mudaram.append((b, o_que))
        contagem = {"entraram": len(entraram), "sairam": len(sairam), "mudaram": len(mudaram)}
        linhas += [f"Comparado com {anterior.name}: **{len(entraram)} entraram, {len(sairam)} saíram e "
                   f"{len(mudaram)} mudaram** no top {cfg['top']}.", ""]
        linhas += ["## Entraram", ""]
        for r in sorted(entraram, key=lambda r: -float(r["nota"]))[:50]:
            linhas.append(f"- {r['razao_social']} ({r['cnpj']}) · nota {float(r['nota']):.1f} · {r['motivo']}")
            mudancas.append({"evento": "entrou", "cnpj": r["cnpj"], "razao_social": r["razao_social"],
                             "detalhe": r["motivo"], "nota": r["nota"]})
        linhas += ([] if entraram else ["Nenhuma."]) + ["", "## Saíram", ""]
        for r in sairam:
            c = r["cnpj"]
            if c in excluidos:
                pq = f"excluída: {excluidos[c]}"
            elif c in fora_icp:
                pq = f"fora do ICP: {fora_icp[c]}"
            elif c not in base_cnpjs:
                pq = "saiu da base qualificada da Receita (situação, sócio estrangeiro, Simples, capital ou CNAE)"
            else:
                pq = "caiu de posição (outras passaram à frente)"
            linhas.append(f"- {r['razao_social']} ({c}) · nota anterior {float(r['nota'] or 0):.1f} · {pq}")
            mudancas.append({"evento": "saiu", "cnpj": c, "razao_social": r["razao_social"], "detalhe": pq,
                             "nota": r["nota"]})
        linhas += ([] if sairam else ["Nenhuma."]) + ["", "## Mudaram", ""]
        for r, o_que in mudaram:
            linhas.append(f"- {r['razao_social']} ({r['cnpj']}) · " + "; ".join(o_que))
            mudancas.append({"evento": "mudou", "cnpj": r["cnpj"], "razao_social": r["razao_social"],
                             "detalhe": "; ".join(o_que), "nota": r["nota"]})
        linhas += ([] if mudaram else ["Nenhuma."]) + [""]

    nov = pasta_cnpj / "novidades.csv"
    linhas += ["## Eventos da Receita no mês (pipeline CNPJ)", ""]
    if nov.exists():
        no_top = {r["cnpj"] for r in top}
        evs = [r for r in ler_csv(nov) if r.get("esta_na_base_pontuada") == "true"]
        evs.sort(key=lambda r: (r["cnpj"] not in no_top, -float(r.get("nota_atual") or 0)))
        for r in evs[:40]:
            marca = " · no top" if r["cnpj"] in no_top else ""
            linhas.append(f"- {r['evento']}: {r['razao_social']} ({r['cnpj']}) · {r['detalhe']}{marca}")
        linhas += ([] if evs else ["Nenhum evento em empresa da base pontuada."]) + [""]
    else:
        linhas += ["Sem `novidades.csv` do pipeline (primeiro mês processado nesta pasta).", ""]

    linhas += bloco_vigia(cfg["pasta_vigia_bc"], mes)
    gravar_atomico(destino, "\n".join(linhas) + "\n")
    gravar_csv(destino.with_name("mudancas.csv"), mudancas, ["evento", "cnpj", "razao_social", "detalhe", "nota"])
    return contagem


# --------------------------------------------------------------------------- rodada

def rodar(mes: str, fonte_local: Path, pasta: Path = Path("saida"), config: Path | None = None,
          workers: int | None = None, motor: str | None = None, cdp_url: str | None = None,
          intervalo: float = INTERVALO_MIN_S, transporte=None, hoje: dt.date | None = None,
          refazer_site: bool = False) -> Path:
    """Roda (ou retoma) a esteira de um mês. Devolve a pasta <pasta>/<mes>/esteira."""
    if not pl.RX_MES.fullmatch(mes or ""):
        raise SystemExit(f"--mes tem de ser AAAA-MM (veio {mes!r})")
    if intervalo < INTERVALO_MIN_S and transporte is None:
        raise SystemExit(f"o intervalo mínimo entre pedidos ao mesmo domínio é {INTERVALO_MIN_S:g} s")
    cfg = ler_config(config)
    t0 = time.time()
    pasta_mes = pasta / mes
    destino = pasta_mes / "esteira"
    destino.mkdir(parents=True, exist_ok=True)
    estado = Estado(destino / "estado.json", mes)

    # 1. cnpj
    base_parquet = pasta_mes / "base_pontuada.parquet"
    if not base_parquet.exists() or not (pasta_mes / "top1000.csv").exists():
        if not fonte_local or not Path(fonte_local).is_dir():
            raise SystemExit(f"Não achei a pasta da Receita {fonte_local} (use --fonte-local com os zips do mês)")
        log(f"etapa cnpj: pipeline CNPJ v2 sobre {fonte_local}")
        pl.rodar(mes, pasta, Path(fonte_local), hoje=hoje, refazer=True)
    else:
        log(f"etapa cnpj: {mes} já processado em {pasta_mes} (reaproveitado)")
        ant = pl.mes_anterior_processado(pasta, mes)
        if ant and not (pasta_mes / "novidades.csv").exists():
            pl.diff(ant, pasta_mes)
    base = ler_base(base_parquet)
    estado.marcar("cnpj", qualificadas=len(base))

    # 2. icp + concorrentes
    conc = ler_concorrentes(cfg["concorrentes"], cfg["niveis"])
    extra = ler_exclusao_extra(cfg["exclusao_extra"])
    bc = raizes_bc(cfg["pasta_vigia_bc"])
    excluidos, fora_icp, aceitas = {}, {}, []
    for e in base:
        m = motivo_concorrente(e, conc, extra, bc)
        if m:
            excluidos[e["cnpj"]] = m
            continue
        m = motivo_fora_icp(e, cfg)
        if m:
            fora_icp[e["cnpj"]] = m
            continue
        aceitas.append(e)
    candidatos = aceitas[:cfg["candidatos"]]
    estado.marcar("icp", aceitas=len(aceitas), candidatos=len(candidatos), concorrentes=len(excluidos),
                  fora_icp=len(fora_icp), config=cfg["arquivo"])
    log(f"etapa icp: {len(aceitas)} no ICP, {len(excluidos)} concorrentes fora, {len(fora_icp)} fora do ICP; "
        f"{len(candidatos)} vão ao site")

    # 3. site
    pasta_site = destino / "site"
    pasta_site.mkdir(exist_ok=True)
    entrada = pasta_site / "candidatos.csv"
    gravar_csv(entrada, [{"cnpj": e["cnpj"], "razao_social": e["razao_social"], "nome_fantasia": e["nome_fantasia"] or "",
                          "uf": e["uf"], "dominio_email": e["dominio_email"] or "", "marca_email": e["marca_email"] or "",
                          "nota": e["nota"]} for e in candidatos],
               ["cnpj", "razao_social", "nome_fantasia", "uf", "dominio_email", "marca_email", "nota"])
    coletor = None
    if transporte is not None:
        coletor = es.Coletor(transporte, intervalo=intervalo, nome_motor=getattr(transporte, "nome", "leve"))
    log("etapa site: enriquecer_site (robots.txt, 1 pedido/s por domínio, só e-mail de função)")
    enr = es.rodar(entrada, pasta_site, workers=workers or cfg["workers"], motor=motor or cfg["motor"],
                   cdp_url=cdp_url, refazer=refazer_site, coletor=coletor, intervalo=max(intervalo, INTERVALO_MIN_S))
    site = {r["cnpj"]: r for r in ler_csv(enr)}
    estado.marcar("site", lidos=sum(1 for r in site.values() if r.get("status_site", "").startswith("ok")),
                  candidatos=len(site))

    # 4. nota (e a segunda passada de concorrentes, agora com o domínio de destino do site)
    final = []
    for e in candidatos:
        s = site.get(e["cnpj"], {})
        m = motivo_concorrente(e, conc, extra, bc, [s.get("site") or "", s.get("redireciona_para") or ""])
        if m:
            excluidos[e["cnpj"]] = m
            continue
        ns, quais = nota_site(s, cfg)
        nota = round(cfg["peso_cnpj"] * float(e["nota"]) + cfg["peso_site"] * ns, 1)
        emails = [x.strip() for x in (s.get("emails_funcao") or "").split(";") if x.strip()]
        emails += [x.strip() for x in (s.get("emails_funcao_outros_dominios") or "").split(";") if x.strip()]
        final.append({
            "cnpj": e["cnpj"], "razao_social": e["razao_social"], "nome_fantasia": e["nome_fantasia"] or "",
            "uf": e["uf"], "municipio": e["municipio"], "cnae_principal": e["cnae_principal"],
            "grupo_cnae": e["grupo_cnae"], "capital_social": e["capital_social"],
            "porte": pl.PORTE.get(int(e["porte"] or 0), "Não informado"), "data_inicio": e["data_inicio"],
            "vinculo_estrangeiro": VINCULO.get(e["tipo_socio"] or "", "PF estrangeira"),
            "pais_socio_estrangeiro": e["pais_socio"] or "", "empresa_estrangeira_socia": e["empresa_estrangeira_socia"] or "",
            "site": s.get("site") or "", "email_funcao": emails[0] if emails else "", "emails_funcao": ";".join(emails),
            "nota": nota, "nota_cnpj": e["nota"], "nota_site": ns, "motivo": montar_motivo(e, s, quais),
            "status_site": s.get("status_site") or "", "sinais_site": s.get("evidencias") or "",
            "_capital": float(e["capital_social"] or 0)})
    final.sort(key=lambda r: (-r["nota"], -float(r["nota_cnpj"]), -r["_capital"], r["cnpj"]))
    top = final[:cfg["top"]]
    for i, r in enumerate(top, 1):
        r["posicao"] = i
    estado.marcar("nota", ranqueadas=len(final), top=len(top))

    # 5. saídas
    gravar_csv(destino / "top1000.csv", top, COLUNAS_TOP)
    for r in top:
        r["nota"] = f"{r['nota']:.1f}"
    gravar_csv(destino / "excluidos.csv",
               [{"cnpj": e["cnpj"], "razao_social": e["razao_social"], "motivo": excluidos.get(e["cnpj"]) or fora_icp[e["cnpj"]],
                 "tipo": "concorrente" if e["cnpj"] in excluidos else "fora do ICP"}
                for e in base if e["cnpj"] in excluidos or e["cnpj"] in fora_icp],
               ["cnpj", "razao_social", "tipo", "motivo"])
    crm = [json.dumps({"id_externo": r["cnpj"], "mes": mes, "posicao": r["posicao"], "nome": r["razao_social"],
                       "nome_fantasia": r["nome_fantasia"], "cnpj": r["cnpj"], "site": r["site"],
                       "email_funcao": r["email_funcao"], "emails_funcao": [x for x in r["emails_funcao"].split(";") if x],
                       "nota": float(r["nota"]), "motivo": r["motivo"], "origem": f"esteira Ozav {mes}"},
                      ensure_ascii=False) for r in top]
    gravar_atomico(destino / "crm.jsonl", "\n".join(crm) + ("\n" if crm else ""))
    anterior = mes_anterior_esteira(pasta, mes)
    cont = escrever_novidades(destino / "novidades.md", mes, [dict(r, nota=str(r["nota"])) for r in top], anterior,
                              excluidos, {e["cnpj"] for e in base}, fora_icp, cfg, pasta_mes)
    seg = time.time() - t0
    gravar_atomico(destino / "RODADA.md", "\n".join([
        f"# Rodada da esteira · {mes}", "",
        f"- Processado em {dt.datetime.now():%Y-%m-%d %H:%M}, em {seg:.0f} s; configuração {cfg['arquivo']}",
        f"- Base qualificada (Receita): {len(base)}",
        f"- Concorrentes excluídos: {len(excluidos)} · fora do ICP: {len(fora_icp)} (lista em excluidos.csv)",
        f"- Candidatos ao site: {len(candidatos)} · sites lidos: {estado.d['etapas']['site']['lidos']}",
        f"- Top: {len(top)} (top1000.csv e crm.jsonl)",
        f"- Novidades: {cont['entraram']} entraram, {cont['sairam']} saíram, {cont['mudaram']} mudaram"
        + (f" (contra {anterior.name})" if anterior else " (primeiro mês)"),
        "- A esteira não escreveu em CRM nenhum e não mandou mensagem a ninguém.", ""]))
    estado.marcar("saidas", top=len(top), **cont)
    log(f"ok: {destino} ({len(top)} no top, {seg:.0f} s)")
    return destino


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mes", required=True, help="AAAA-MM")
    ap.add_argument("--fonte-local", type=Path, required=True, help="pasta com os zips da Receita do mês")
    ap.add_argument("--dir", type=Path, default=Path("saida"), help="pasta de saída (padrão: saida)")
    ap.add_argument("--config", type=Path, default=CONFIG_PADRAO, help="icp.ini (padrão: o desta pasta)")
    ap.add_argument("--workers", type=int, help="domínios em paralelo (cada domínio tem 1 pedido por segundo)")
    ap.add_argument("--motor", choices=["auto", "crawl4ai", "leve"])
    ap.add_argument("--cdp-url")
    ap.add_argument("--refazer-site", action="store_true", help="ignora o cache e visita os sites de novo")
    a = ap.parse_args(argv)
    rodar(a.mes, a.fonte_local, a.dir, a.config, a.workers, a.motor, a.cdp_url, refazer_site=a.refazer_site)


if __name__ == "__main__":
    main()
