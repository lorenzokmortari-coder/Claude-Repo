#!/usr/bin/env python3
"""
Relatório da cota real do plano, a partir de ~/.claude/cota.jsonl (gravado pela barra de status
statusline-cota.mjs ou statusline-cota.sh, no máximo uma linha por minuto).

Mostra o estado atual das janelas de 5 h e de 7 dias, o consumo por dia e por hora do dia em pontos
percentuais (p.p.) e avisa quando:
  - a cota de 7 dias passou de 80% antes de quarta-feira na janela atual (limite e dia ajustáveis);
  - no ritmo das últimas 24 h, a cota de 7 dias vai passar de 80% antes de quarta ou acabar antes do reset.

Saída: o relatório em Markdown no terminal (e em --saida, se der). Código de saída 2 quando há
alerta (o Agendador de Tarefas pode avisar), 1 quando não há dado, 0 quando está tudo bem.

Uso:
  python relatorio.py
  python relatorio.py --arquivo C:/Users/loren/.claude/cota.jsonl --dias 14 --limite 80 --dia qua --saida cota.md

Só biblioteca padrão. Python 3.10 ou mais novo.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from dataclasses import dataclass
from pathlib import Path

DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]   # índice = datetime.weekday()
TOLERANCIA_RESET_S = 120   # resets_at que muda menos que isso é a mesma janela
JANELA_RITMO = dt.timedelta(hours=24)
RITMO_MINIMO = dt.timedelta(hours=3)   # menos que isso de dados não dá projeção


@dataclass
class Amostra:
    hora: dt.datetime
    p5: float | None
    r5: int | None
    p7: float | None
    r7: int | None
    modelo: str | None
    sessao: str | None


def _num(x) -> float | None:
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def ler(arquivo: Path) -> tuple[list[Amostra], int]:
    """Lê o JSONL, ignora linha inválida e junta as amostras do mesmo minuto (várias sessões
    abertas gravam o mesmo número; fica o maior)."""
    por_minuto: dict[dt.datetime, Amostra] = {}
    invalidas = 0
    with open(arquivo, encoding="utf-8", errors="replace") as f:
        for linha in f:
            if not linha.strip():
                continue
            try:
                o = json.loads(linha)
                hora = dt.datetime.fromisoformat(o["hora"])
            except (ValueError, KeyError, TypeError):
                invalidas += 1
                continue
            if hora.tzinfo is None:
                hora = hora.astimezone()
            a = Amostra(hora, _num(o.get("pct_5h")), _int(o.get("reset_5h")), _num(o.get("pct_7d")),
                        _int(o.get("reset_7d")), o.get("modelo"), o.get("sessao"))
            if a.p5 is None and a.p7 is None:
                invalidas += 1
                continue
            chave = a.hora.astimezone(dt.timezone.utc).replace(second=0, microsecond=0)
            velha = por_minuto.get(chave)
            por_minuto[chave] = a if velha is None else _juntar(velha, a)
    return sorted(por_minuto.values(), key=lambda a: a.hora), invalidas


def _int(x) -> int | None:
    n = _num(x)
    return int(n) if n is not None else None


def _juntar(a: Amostra, b: Amostra) -> Amostra:
    def maior(x, y):
        return y if x is None else x if y is None else max(x, y)
    return Amostra(min(a.hora, b.hora), maior(a.p5, b.p5), maior(a.r5, b.r5), maior(a.p7, b.p7),
                   maior(a.r7, b.r7), a.modelo or b.modelo, a.sessao or b.sessao)


def mesma_janela(r1: int | None, r2: int | None) -> bool:
    if r1 is None or r2 is None:
        return r1 is None and r2 is None
    return abs(r1 - r2) <= TOLERANCIA_RESET_S


def consumos(amostras: list[Amostra], qual: str) -> list[tuple[dt.datetime, float]]:
    """(hora, p.p.) consumidos entre amostras seguidas da mesma janela. Quando a janela vira
    (resets_at novo), o percentual que aparece foi gasto depois do reset e conta inteiro."""
    out: list[tuple[dt.datetime, float]] = []
    anterior: tuple[float, int | None] | None = None
    for a in amostras:
        p, r = (a.p5, a.r5) if qual == "5h" else (a.p7, a.r7)
        if p is None:
            continue
        if anterior is not None:
            pa, ra = anterior
            if mesma_janela(ra, r):
                if p > pa:
                    out.append((a.hora, p - pa))
            elif p > 0:
                out.append((a.hora, p))
        anterior = (p, r)
    return out


def br(x: float, casas: int = 1) -> str:
    return f"{x:.{casas}f}".replace(".", ",")


def quando(d: dt.datetime, agora: dt.datetime) -> str:
    falta = d - agora
    if falta.total_seconds() <= 0:
        tempo = "já passou"
    else:
        h = int(falta.total_seconds() // 3600)
        m = int(falta.total_seconds() % 3600 // 60)
        tempo = f"em {h // 24}d {h % 24}h" if h >= 24 else f"em {h}h{m:02d}"
    return f"{DIAS[d.weekday()]} {d:%d/%m %H:%M} ({tempo})"


def primeiro_dia_depois(inicio: dt.datetime, dia: int) -> dt.datetime:
    """Primeira meia-noite do dia da semana `dia` depois de `inicio`."""
    d = (inicio + dt.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    while d.weekday() != dia:
        d += dt.timedelta(days=1)
    return d


def alertas(amostras: list[Amostra], limite: float, dia: int) -> tuple[list[str], dict]:
    com7 = [a for a in amostras if a.p7 is not None]
    info: dict = {}
    if not com7:
        return [], info
    ult = com7[-1]
    msgs = []
    if ult.r7 is None:
        return msgs, info
    tz = ult.hora.tzinfo
    fim = dt.datetime.fromtimestamp(ult.r7, tz)
    inicio = fim - dt.timedelta(days=7)
    marco = primeiro_dia_depois(inicio, dia)
    janela = [a for a in com7 if mesma_janela(a.r7, ult.r7)]
    info.update(fim=fim, inicio=inicio, marco=marco)
    passou = next((a for a in janela if a.hora < marco and a.p7 >= limite), None)
    if passou:
        msgs.append(f"ALERTA: a cota de 7 dias passou de {br(limite, 0)}% antes de {DIAS[dia]} "
                    f"({br(passou.p7)}% em {DIAS[passou.hora.weekday()]} {passou.hora:%d/%m %H:%M}).")

    recentes = [a for a in janela if a.hora >= ult.hora - JANELA_RITMO]
    if len(recentes) >= 2 and ult.hora - recentes[0].hora >= RITMO_MINIMO:
        horas = (ult.hora - recentes[0].hora).total_seconds() / 3600
        ritmo = max(0.0, (ult.p7 - recentes[0].p7) / horas)
        info["ritmo"] = ritmo
        if ritmo > 0:
            eta_lim = ult.hora + dt.timedelta(hours=(limite - ult.p7) / ritmo) if ult.p7 < limite else None
            eta_100 = ult.hora + dt.timedelta(hours=(100 - ult.p7) / ritmo) if ult.p7 < 100 else ult.hora
            info.update(eta_lim=eta_lim, eta_100=eta_100)
            if eta_lim and eta_lim < marco and not passou:
                msgs.append(f"AVISO: no ritmo das últimas {br(horas, 0)} h ({br(ritmo, 2)} p.p./h), a cota de 7 dias "
                            f"chega a {br(limite, 0)}% em {DIAS[eta_lim.weekday()]} {eta_lim:%d/%m %H:%M}, antes de {DIAS[dia]}.")
            if eta_100 < fim:
                msgs.append(f"AVISO: nesse ritmo a cota de 7 dias acaba em {DIAS[eta_100.weekday()]} "
                            f"{eta_100:%d/%m %H:%M}, antes do reset ({DIAS[fim.weekday()]} {fim:%d/%m %H:%M}).")
    return msgs, info


def montar(amostras: list[Amostra], invalidas: int, arquivo: Path, dias: int, limite: float, dia: int) -> tuple[str, int]:
    if not amostras:
        return (f"# Cota do plano\n\nNenhuma amostra válida em `{arquivo}`. A barra de status grava só quando o "
                "Claude Code recebe `rate_limits` (plano Pro/Max, depois da primeira resposta da sessão).\n", 1)
    ult = amostras[-1]
    agora = ult.hora
    L = [f"# Cota do plano · {agora:%d/%m/%Y %H:%M}", "",
         f"Fonte: `{arquivo}` · {len(amostras)} minutos com registro, de {amostras[0].hora:%d/%m %H:%M} "
         f"a {agora:%d/%m %H:%M}" + (f" · {invalidas} linha(s) inválida(s) ignorada(s)" if invalidas else "") + ".", ""]

    L += ["## Agora", "", "| Janela | Usado | Reinicia |", "|---|---|---|"]
    for nome, p, r in (("5 horas", "p5", "r5"), ("7 dias", "p7", "r7")):
        a = next((x for x in reversed(amostras) if getattr(x, p) is not None), None)
        if a is None:
            L.append(f"| {nome} | sem dado | |")
            continue
        reset = getattr(a, r)
        texto = quando(dt.datetime.fromtimestamp(reset, agora.tzinfo), agora) if reset else "?"
        L.append(f"| {nome} | {br(getattr(a, p))}% (às {a.hora:%H:%M}) | {texto} |")

    msgs, info = alertas(amostras, limite, dia)
    L += ["", "## Alertas", ""]
    L += [f"- {m}" for m in msgs] or [f"- Nenhum: a cota de 7 dias não passou de {br(limite, 0)}% antes de {DIAS[dia]} "
                                      "e o ritmo recente não acaba com ela antes do reset."]
    if "ritmo" in info:
        L.append(f"- Ritmo das últimas 24 h na janela atual: {br(info['ritmo'], 2)} p.p. por hora da cota de 7 dias.")
    else:
        L.append("- Ritmo: menos de 3 h de registro na janela atual, sem projeção.")

    desde = (agora - dt.timedelta(days=dias)).date()
    c7 = [(h, v) for h, v in consumos(amostras, "7d") if h.date() >= desde]
    c5 = [(h, v) for h, v in consumos(amostras, "5h") if h.date() >= desde]
    por_dia: dict[dt.date, dict] = {}
    for a in amostras:
        if a.hora.date() >= desde:
            d = por_dia.setdefault(a.hora.date(), {"p7": 0.0, "p5": 0.0, "max5": 0.0, "horas": set()})
            d["horas"].add(a.hora.hour)
            if a.p5 is not None:
                d["max5"] = max(d["max5"], a.p5)
    for h, v in c7:
        por_dia.setdefault(h.date(), {"p7": 0.0, "p5": 0.0, "max5": 0.0, "horas": set()})["p7"] += v
    for h, v in c5:
        por_dia.setdefault(h.date(), {"p7": 0.0, "p5": 0.0, "max5": 0.0, "horas": set()})["p5"] += v
    L += ["", f"## Por dia (últimos {dias} dias)", "",
          "| Dia | Cota de 7 dias gasta | Janelas de 5 h gastas (soma) | Maior % numa janela de 5 h | Horas com registro |",
          "|---|---|---|---|---|"]
    for d in sorted(por_dia):
        x = por_dia[d]
        L.append(f"| {DIAS[d.weekday()]} {d:%d/%m} | {br(x['p7'])} p.p. | {br(x['p5'])} p.p. | {br(x['max5'])}% | {len(x['horas'])} |")

    por_hora = [0.0] * 24
    dias_ativos = len({a.hora.date() for a in amostras if a.hora.date() >= desde}) or 1
    for h, v in c7:
        por_hora[h.hour] += v
    L += ["", f"## Por hora do dia (cota de 7 dias, últimos {dias} dias)", "",
          "| Hora | Gasto total | Média por dia com registro |", "|---|---|---|"]
    L += [f"| {hh:02d}h | {br(v)} p.p. | {br(v / dias_ativos, 2)} p.p. |" for hh, v in enumerate(por_hora) if v > 0]
    L += ["", "## Como ler", "",
          "- p.p. = pontos percentuais da cota. \"5 p.p. da cota de 7 dias\" = 5% do limite semanal.",
          "- O gasto entra na hora da amostra em que apareceu. Com o Claude Code fechado não há amostra, então o que foi "
          "gasto nesse tempo (inclusive no claude.ai, no app e em sessões na nuvem, que dividem a mesma cota) aparece "
          "de uma vez na primeira amostra seguinte.",
          "- Quando a janela vira (reset), o que foi gasto entre a última amostra e o reset fica de fora.",
          "- Código de saída: 2 com alerta, 0 sem alerta, 1 sem dado."]
    return "\n".join(L) + "\n", (2 if msgs else 0)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arquivo", type=Path, default=Path.home() / ".claude" / "cota.jsonl")
    ap.add_argument("--dias", type=int, default=14, help="quantos dias entram nas tabelas (padrão 14)")
    ap.add_argument("--limite", type=float, default=80.0, help="percentual da cota de 7 dias para o alerta (padrão 80)")
    ap.add_argument("--dia", default="qua", choices=DIAS, help="dia da semana do alerta (padrão qua)")
    ap.add_argument("--saida", type=Path, help="grava o relatório também neste arquivo .md")
    a = ap.parse_args(argv)
    if not a.arquivo.exists():
        print(f"Não achei {a.arquivo}. A barra de status (statusline-cota) ainda não gravou nada?", file=sys.stderr)
        return 1
    amostras, invalidas = ler(a.arquivo)
    texto, codigo = montar(amostras, invalidas, a.arquivo, a.dias, a.limite, DIAS.index(a.dia))
    sys.stdout.write(texto)
    if a.saida:
        a.saida.write_text(texto, encoding="utf-8")
    return codigo


if __name__ == "__main__":
    sys.exit(main())
