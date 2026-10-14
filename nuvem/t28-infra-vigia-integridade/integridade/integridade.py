#!/usr/bin/env python3
"""Vigia de integridade do servidor (Python 3.10+, só biblioteca padrão).

Vigia arquivos de configuração do Claude Code, hooks, .env e dependências.
Só avisa: nunca conserta nada e só escreve na própria pasta de estado.

  integridade.py --checar [--resumo]        compara com a base (de hora em hora)
  integridade.py --aceitar "<motivo>"       regrava a base e anota no livro
  integridade.py --deps [--resumo]          osv-scanner nas pastas do ini (semanal)

Códigos de saída:
  --checar / --aceitar: 0 nada novo a avisar · 1 mudou (aviso novo) · 2 erro do vigia
  --deps: 0 sem ALTA/CRÍTICA · 1 alguma ALTA/CRÍTICA · 2 erro · 3 osv-scanner ausente
A saída nunca traz conteúdo de arquivo: só caminho, hash curto e o que mudou.
"""
from __future__ import annotations

import argparse
import configparser
import datetime as dt
import fcntl
import grp
import hashlib
import json
import os
import pwd
import shlex
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path

OK, MUDOU, ERRO, SEM_OSV = 0, 1, 2, 3
INI_PADRAO = Path(__file__).with_name("integridade.ini")
OSV_PADRAO = "osv-scanner --format json -r {pasta}"


class ErroVigia(Exception):
    """Erro do próprio vigia (código 2)."""


# ---------------------------------------------------------------- config

def ler_ini(caminho: Path) -> dict:
    if not caminho.is_file():
        raise ErroVigia(f"ini não encontrado: {caminho}")
    cp = configparser.ConfigParser(allow_no_value=True, delimiters=("=",),
                                   interpolation=None)
    cp.optionxform = str  # caminhos diferenciam maiúscula
    try:
        cp.read(caminho, encoding="utf-8")
    except configparser.Error as e:
        raise ErroVigia(f"ini inválido: {e.__class__.__name__}") from None
    if not cp.has_option("geral", "estado"):
        raise ErroVigia("ini sem [geral] estado")

    def caminhos(secao):
        if not cp.has_section(secao):
            return {}
        return {expandir(k): (v or "") for k, v in cp.items(secao)}

    arquivos = {}
    for k, v in caminhos("arquivos").items():
        arquivos[k] = [c.strip() for c in v.split(",") if c.strip()]
    # quem vigia o vigia: o próprio script e o ini entram sempre
    arquivos.setdefault(str(Path(__file__).resolve()), [])
    arquivos.setdefault(str(caminho.resolve()), [])
    return {
        "estado": Path(expandir(cp.get("geral", "estado"))),
        "fuso": cp.get("geral", "fuso", fallback="America/Sao_Paulo"),
        "comando_osv": cp.get("geral", "comando_osv", fallback=OSV_PADRAO),
        "arquivos": arquivos,
        "pastas": list(caminhos("pastas")),
        "deps": list(caminhos("deps")),
    }


def expandir(p: str) -> str:
    return os.path.abspath(os.path.expanduser(p.strip()))


def hoje(fuso: str) -> str:
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo(fuso)).date().isoformat()
    except Exception:  # sem tzdata: horário de Brasília fixo
        return dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).date().isoformat()


def agora_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------- estado

def preparar_estado(pasta: Path) -> None:
    pasta.mkdir(parents=True, exist_ok=True, mode=0o700)
    st = pasta.stat()
    if st.st_mode & 0o022:
        raise ErroVigia(f"pasta de estado gravável por outros ({oct(st.st_mode & 0o777)}): {pasta}")


def gravar_atomico(caminho: Path, texto: str) -> None:
    tmp = caminho.with_name(f".{caminho.name}.{os.getpid()}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(texto)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, caminho)


def ler_json_estado(caminho: Path, padrao):
    if not caminho.exists():
        return padrao
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ErroVigia(f"estado corrompido: {caminho.name}") from None


class Trava:
    """Uma execução por vez (cron de hora em hora + semanal + manual)."""

    def __init__(self, pasta: Path, espera: float = 60):
        self.caminho, self.espera, self.fd = pasta / ".trava", espera, None

    def __enter__(self):
        self.fd = os.open(self.caminho, os.O_RDWR | os.O_CREAT, 0o600)
        limite = time.monotonic() + self.espera
        while True:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except BlockingIOError:
                if time.monotonic() > limite:
                    os.close(self.fd)
                    raise ErroVigia("outra execução do vigia segura a trava") from None
                time.sleep(0.5)

    def __exit__(self, *_):
        fcntl.flock(self.fd, fcntl.LOCK_UN)
        os.close(self.fd)


# ---------------------------------------------------------------- foto

def sha256_arquivo(caminho: str) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 16), b""):
            h.update(bloco)
    return h.hexdigest()


def sha256_valor(valor) -> str:
    bruto = json.dumps(valor, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()


def dono_e_modo(st: os.stat_result) -> tuple[str, str]:
    try:
        u = pwd.getpwuid(st.st_uid).pw_name
    except KeyError:
        u = str(st.st_uid)
    try:
        g = grp.getgrgid(st.st_gid).gr_name
    except KeyError:
        g = str(st.st_gid)
    return f"{u}:{g}", format(stat.S_IMODE(st.st_mode), "04o")


def eh_env(caminho: str) -> bool:
    nome = os.path.basename(caminho)
    return nome == ".env" or nome.startswith(".env.") or nome.endswith(".env")


def extrair(obj, padrao: str) -> dict:
    """Chave pontuada com * para qualquer chave: 'projects.*.allowedTools'."""
    atuais = [((), obj)]
    for parte in padrao.split("."):
        prox = []
        for trilha, v in atuais:
            if not isinstance(v, dict):
                continue
            if parte == "*":
                prox += [(trilha + (k,), v[k]) for k in sorted(v)]
            elif parte in v:
                prox.append((trilha + (parte,), v[parte]))
        atuais = prox
    return {json.dumps(list(t), ensure_ascii=False): sha256_valor(v) for t, v in atuais}


def foto_arquivo(caminho: str, chaves: list[str]) -> dict:
    tipo = "env" if eh_env(caminho) else ("json" if chaves else "arquivo")
    e = {"tipo": tipo}
    try:
        st = os.stat(caminho)
        if not stat.S_ISREG(st.st_mode):
            return e | {"erro": "não é arquivo comum"}
        e["dono"], e["modo"] = dono_e_modo(st)
        if tipo == "json":
            with open(caminho, encoding="utf-8") as f:
                obj = json.load(f)
            e["chaves"] = {}
            for p in chaves:
                e["chaves"].update(extrair(obj, p))
            e["sha256"] = sha256_valor(e["chaves"])
        else:
            e["sha256"] = sha256_arquivo(caminho)
    except FileNotFoundError:
        return e | {"erro": "sumiu"}
    except PermissionError:
        return e | {"erro": "ilegível (sem permissão)"}
    except (ValueError, UnicodeDecodeError):
        return e | {"erro": "JSON ilegível"}
    except OSError as x:
        return e | {"erro": f"ilegível ({x.__class__.__name__})"}
    return e


def foto_pasta(caminho: str) -> dict:
    e = {"tipo": "pasta", "itens": {}}
    if not os.path.isdir(caminho):
        return e | {"erro": "sumiu" if not os.path.exists(caminho) else "não é pasta"}
    try:
        e["dono"], e["modo"] = dono_e_modo(os.stat(caminho))
        for raiz, dirs, nomes in os.walk(caminho, onerror=_levantar):
            dirs.sort()
            for n in sorted(nomes):
                p = os.path.join(raiz, n)
                rel = os.path.relpath(p, caminho)
                try:
                    st = os.stat(p)
                    dono, modo = dono_e_modo(st)
                    e["itens"][rel] = {"sha256": sha256_arquivo(p), "dono": dono, "modo": modo}
                except OSError as x:
                    e["itens"][rel] = {"erro": f"ilegível ({x.__class__.__name__})"}
    except OSError as x:
        return e | {"erro": f"ilegível ({x.__class__.__name__})"}
    return e


def _levantar(erro):
    raise erro


def tirar_foto(cfg: dict) -> dict:
    arquivos = {c: foto_arquivo(c, ch) for c, ch in sorted(cfg["arquivos"].items())}
    arquivos |= {p: foto_pasta(p) for p in sorted(cfg["pastas"])}
    return arquivos


# ---------------------------------------------------------------- comparar

def curto(h) -> str:
    return h[:12] if h else "—"


def nome_chave(ident: str) -> str:
    return ".".join(json.loads(ident))


def comparar(base: dict, atual: dict) -> list[tuple[str, str]]:
    """Lista de (caminho, o que mudou). Nunca inclui conteúdo."""
    d = []
    for c in sorted(set(base) | set(atual)):
        a, n = base.get(c), atual.get(c)
        if n is None:
            d.append((c, "saiu da lista vigiada (o ini mudou)"))
            continue
        if n.get("erro"):
            d.append((c, f"{n['erro']} (falha fechada)"))
        if n["tipo"] == "env" and not n.get("erro") and int(n["modo"], 8) & ~0o600:
            d.append((c, f".env com permissão {n['modo'][1:]} (máximo 600)"))
        if n.get("erro"):
            continue
        if a is None:
            d.append((c, f"novo na lista vigiada, sem base (sha {curto(n['sha256'] if 'sha256' in n else None)})"))
            continue
        if a.get("erro"):
            d.append((c, "voltou a ser legível; confira e rode --aceitar"))
            continue
        if a.get("dono") != n.get("dono"):
            d.append((c, f"dono {a.get('dono')} → {n.get('dono')}"))
        if a.get("modo") != n.get("modo"):
            d.append((c, f"permissão {a.get('modo')} → {n.get('modo')}"))
        if n["tipo"] == "pasta":
            d += _comparar_pasta(c, a.get("itens", {}), n["itens"])
        elif n["tipo"] == "json" and a.get("tipo") == "json":
            ka, kn = a.get("chaves", {}), n["chaves"]
            for k in sorted(set(ka) | set(kn)):
                if k not in kn:
                    d.append((c, f"chave vigiada removida: {nome_chave(k)}"))
                elif k not in ka:
                    d.append((c, f"chave vigiada nova: {nome_chave(k)} (sha {curto(kn[k])})"))
                elif ka[k] != kn[k]:
                    d.append((c, f"chave vigiada mudou: {nome_chave(k)} (sha {curto(ka[k])} → {curto(kn[k])})"))
        elif a.get("sha256") != n.get("sha256"):
            d.append((c, f"conteúdo mudou (sha {curto(a.get('sha256'))} → {curto(n.get('sha256'))})"))
    return d


def _comparar_pasta(c: str, ia: dict, in_: dict) -> list[tuple[str, str]]:
    d = []
    for rel in sorted(set(ia) | set(in_)):
        a, n = ia.get(rel), in_.get(rel)
        p = os.path.join(c, rel)
        if n is None:
            d.append((p, "arquivo sumiu da pasta vigiada"))
        elif n.get("erro"):
            d.append((p, f"{n['erro']} (falha fechada)"))
        elif a is None:
            d.append((p, f"arquivo novo na pasta vigiada (sha {curto(n['sha256'])}, {n['modo']})"))
        elif a.get("sha256") != n["sha256"]:
            d.append((p, f"conteúdo mudou (sha {curto(a.get('sha256'))} → {curto(n['sha256'])})"))
        elif (a.get("modo"), a.get("dono")) != (n["modo"], n["dono"]):
            d.append((p, f"permissão/dono {a.get('modo')} {a.get('dono')} → {n['modo']} {n['dono']}"))
    return d


def assinatura(dif: tuple[str, str]) -> str:
    return hashlib.sha256("\x00".join(dif).encode("utf-8")).hexdigest()[:20]


# ---------------------------------------------------------------- comandos

def checar(cfg: dict, resumo: bool) -> int:
    est = cfg["estado"]
    base_arq = est / "base.json"
    if not base_arq.exists():
        livro = est / "aceites.jsonl"
        if livro.exists() and livro.stat().st_size:
            raise ErroVigia("base.json sumiu mas o livro de aceites tem registros (falha fechada)")
        raise ErroVigia('sem base: rode --aceitar "base inicial"')
    base = ler_json_estado(base_arq, None)
    if not isinstance(base, dict) or "arquivos" not in base:
        raise ErroVigia("base.json sem o formato esperado")
    atual = tirar_foto(cfg)
    difs = comparar(base["arquivos"], atual)

    dia = hoje(cfg["fuso"])
    avisos_arq = est / "avisos.json"
    try:
        avisos = {k: v for k, v in ler_json_estado(avisos_arq, {}).items() if v == dia}
    except (ErroVigia, AttributeError):
        avisos = {}  # estado de avisos estragado: erra para avisar de novo, não para calar
    novas = [x for x in difs if assinatura(x) not in avisos]
    for x in novas:
        avisos[assinatura(x)] = dia
    gravar_atomico(avisos_arq, json.dumps(avisos, indent=1, sort_keys=True))

    linhas = [f"# Vigia de integridade · {agora_iso()}", "",
              f"Itens vigiados: {len(atual)} · diferenças: {len(difs)} · novas hoje: {len(novas)}", ""]
    ja = set(map(assinatura, novas))
    for c, t in difs:
        marca = "NOVO" if assinatura((c, t)) in ja else "já avisado hoje"
        linhas.append(f"- `{c}`: {t} · {marca}")
    if difs:
        linhas += ["", 'Se a mudança foi de propósito: `integridade.py --aceitar "<motivo>"`.',
                   "O vigia não conserta nada sozinho."]
    gravar_atomico(est / "relatorio.md", "\n".join(linhas) + "\n")

    if not difs:
        print(f"INTEGRIDADE OK · {len(atual)} itens vigiados")
        return OK
    if not novas:
        print(f"INTEGRIDADE OK · {len(difs)} diferença(s) já avisada(s) hoje, pendente(s) de --aceitar")
        return OK
    nomes = ", ".join(sorted({os.path.basename(c.rstrip('/')) for c, _ in novas}))
    print(f"INTEGRIDADE MUDOU · {len(novas)} nova(s): {nomes} · detalhe em {est / 'relatorio.md'}")
    if not resumo:
        for c, t in novas:
            print(f"  {c}: {t}")
    return MUDOU


def aceitar(cfg: dict, motivo: str | None) -> int:
    motivo = (motivo or "").strip()
    if len(motivo) < 3:
        raise ErroVigia('aceite recusado: diga o motivo, ex.: --aceitar "novo hook de log"')
    est = cfg["estado"]
    base = ler_json_estado(est / "base.json", {"arquivos": {}})
    antigo = base.get("arquivos", {})
    atual = tirar_foto(cfg)
    ruins = [c for c, e in atual.items() if e.get("erro")]
    if ruins:
        raise ErroVigia("aceite recusado: itens sumidos/ilegíveis (tire do ini ou conserte): "
                        + ", ".join(ruins))
    mudados = []
    for c in sorted(set(antigo) | set(atual)):
        a, n = antigo.get(c, {}), atual.get(c, {})
        if (a.get("sha256"), a.get("modo"), a.get("dono"), a.get("itens")) != \
           (n.get("sha256"), n.get("modo"), n.get("dono"), n.get("itens")):
            mudados.append({"caminho": c, "antes": curto(a.get("sha256")) if a else None,
                            "depois": curto(n.get("sha256")) if n else None})
    registro = {"data": agora_iso(), "motivo": motivo, "usuario": _usuario(), "arquivos": mudados}
    fd = os.open(est / "aceites.jsonl", os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    gravar_atomico(est / "base.json", json.dumps(
        {"versao": 1, "gravada": registro["data"], "arquivos": atual}, indent=1, sort_keys=True))
    gravar_atomico(est / "avisos.json", "{}")
    print(f"INTEGRIDADE ACEITA · {len(mudados)} item(ns) · motivo anotado em aceites.jsonl")
    for c, t in comparar(atual, atual):  # o que o aceite não cala (ex.: .env aberto)
        print(f"  atenção: {c}: {t}")
    return OK


def _usuario() -> str:
    try:
        return pwd.getpwuid(os.getuid()).pw_name
    except KeyError:
        return str(os.getuid())


# ---------------------------------------------------------------- deps

ORDEM = {"CRÍTICA": 4, "ALTA": 3, "MÉDIA": 2, "BAIXA": 1, "?": 0}


def nivel_cvss(nota) -> str:
    try:
        n = float(nota)
    except (TypeError, ValueError):
        return "?"
    return "CRÍTICA" if n >= 9 else "ALTA" if n >= 7 else "MÉDIA" if n >= 4 else "BAIXA" if n > 0 else "?"


def nivel_texto(t) -> str:
    return {"CRITICAL": "CRÍTICA", "HIGH": "ALTA", "MODERATE": "MÉDIA", "MEDIUM": "MÉDIA",
            "LOW": "BAIXA"}.get(str(t or "").upper(), "?")


def resumir_osv(dados: dict) -> list[dict]:
    """Uma entrada por vulnerabilidade (grupo de aliases), com o nível."""
    saida = []
    for r in dados.get("results") or []:
        for p in r.get("packages") or []:
            pkg = p.get("package", {})
            vulns = {v.get("id"): v for v in p.get("vulnerabilities") or []}
            grupos = p.get("groups") or [{"ids": [i]} for i in vulns]
            for g in grupos:
                ids = g.get("ids") or []
                niv = nivel_cvss(g.get("max_severity"))
                if niv == "?":
                    niv = max((nivel_texto((vulns.get(i) or {}).get("database_specific", {}).get("severity"))
                               for i in ids), key=ORDEM.get, default="?")
                saida.append({"arquivo": (r.get("source") or {}).get("path", "?"),
                              "pacote": f"{pkg.get('name', '?')}@{pkg.get('version', '?')}",
                              "id": ids[0] if ids else "?", "nivel": niv})
    return saida


def deps(cfg: dict, resumo: bool) -> int:
    partes = shlex.split(cfg["comando_osv"])
    if not partes or shutil.which(partes[0]) is None:
        print(f"DEPS SEM OSV · '{partes[0] if partes else '?'}' não instalado; nada verificado")
        return SEM_OSV
    linhas = [f"# Dependências · {agora_iso()}", ""]
    total_altas, falhas, por_proj = 0, [], []
    for pasta in cfg["deps"]:
        if not os.path.isdir(pasta):
            falhas.append(f"{pasta}: pasta sumiu")
            continue
        cmd = [x.replace("{pasta}", pasta) for x in partes]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        except (OSError, subprocess.TimeoutExpired) as x:
            falhas.append(f"{pasta}: osv-scanner falhou ({x.__class__.__name__})")
            continue
        if r.returncode not in (0, 1, 128):  # 1 = achou vuln; 128 = sem lockfile
            falhas.append(f"{pasta}: osv-scanner saiu com {r.returncode}")
            continue
        try:
            vulns = resumir_osv(json.loads(r.stdout or '{"results": []}'))
        except ValueError:
            falhas.append(f"{pasta}: saída do osv-scanner não é JSON")
            continue
        altas = [v for v in vulns if v["nivel"] in ("ALTA", "CRÍTICA")]
        total_altas += len(altas)
        crit = sum(v["nivel"] == "CRÍTICA" for v in vulns)
        por_proj.append(f"{os.path.basename(pasta)} {len(altas)}A/C")
        linhas.append(f"## {pasta}")
        linhas.append(f"{len(vulns)} vulnerabilidade(s) · CRÍTICA {crit} · ALTA {len(altas) - crit} · "
                      f"outras {len(vulns) - len(altas)}")
        for v in sorted(vulns, key=lambda v: -ORDEM[v["nivel"]]):
            if v["nivel"] in ("ALTA", "CRÍTICA"):
                linhas.append(f"- {v['nivel']} · {v['pacote']} · {v['id']} · {os.path.relpath(v['arquivo'], pasta) if v['arquivo'].startswith(pasta) else v['arquivo']}")
        linhas.append("")
    if falhas:
        linhas += ["## Falhas", *[f"- {f}" for f in falhas]]
    gravar_atomico(cfg["estado"] / "deps.md", "\n".join(linhas) + "\n")
    texto = (f"DEPS · {total_altas} ALTA/CRÍTICA em {len(por_proj)} projeto(s)"
             + (f" ({', '.join(por_proj)})" if por_proj else "")
             + (f" · {len(falhas)} falha(s)" if falhas else "")
             + f" · detalhe em {cfg['estado'] / 'deps.md'}")
    print(texto)
    if not resumo:
        print("\n".join(linhas))
    if falhas and not total_altas:
        return ERRO
    return MUDOU if total_altas else OK


# ---------------------------------------------------------------- entrada

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Vigia de integridade (só avisa, nunca conserta).")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--checar", action="store_true")
    g.add_argument("--aceitar", metavar="MOTIVO", nargs="?", const="")
    g.add_argument("--deps", action="store_true")
    ap.add_argument("--resumo", action="store_true", help="uma linha só na saída")
    ap.add_argument("--ini", type=Path, default=INI_PADRAO)
    a = ap.parse_args(argv)
    try:
        cfg = ler_ini(a.ini)
        preparar_estado(cfg["estado"])
        with Trava(cfg["estado"]):
            if a.checar:
                return checar(cfg, a.resumo)
            if a.deps:
                return deps(cfg, a.resumo)
            return aceitar(cfg, a.aceitar)
    except ErroVigia as e:
        print(f"INTEGRIDADE ERRO · {e}")
        return ERRO
    except Exception as e:  # qualquer surpresa vira código 2, sem despejar conteúdo
        print(f"INTEGRIDADE ERRO · falha interna ({e.__class__.__name__})")
        return ERRO


if __name__ == "__main__":
    sys.exit(main())
