"""Testes com JSON SINTÉTICO da barra de status (statusline-cota.mjs e statusline-cota.sh) e do
relatorio.py. A base é o JSON de exemplo da documentação oficial (exemplo_docs.json, copiado de
code.claude.com/docs/en/statusline em 14/10/2026). Os testes do .mjs pulam sem `node`; os do .sh
pulam sem `bash`. Rodar: python -m pytest -q
"""
from __future__ import annotations

import copy
import datetime as dt
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

import relatorio

AQUI = Path(__file__).resolve().parent
DOCS = json.loads((AQUI / "exemplo_docs.json").read_text(encoding="utf-8"))
AGORA = 1738400000                      # 2025-02-01 05:53:20 em São Paulo (-03:00)
TZ = "America/Sao_Paulo"
VERDE, AMARELO, VERMELHO, FIM = "\x1b[32m", "\x1b[33m", "\x1b[31m", "\x1b[0m"

SCRIPTS = []
if shutil.which("node"):
    SCRIPTS.append("mjs")
if shutil.which("bash"):
    SCRIPTS.append("sh")


def rodar(qual: str, entrada: str, pasta: Path, agora: int = AGORA) -> str:
    env = dict(os.environ, TZ=TZ, COTA_DIR=str(pasta), COTA_AGORA=str(agora), COTA_AGORA_MS=str(agora * 1000))
    cmd = ["node", str(AQUI / "statusline-cota.mjs")] if qual == "mjs" else ["bash", str(AQUI / "statusline-cota.sh")]
    r = subprocess.run(cmd, input=entrada.encode("utf-8"), capture_output=True, env=env, timeout=20)
    assert r.returncode == 0, r.stderr.decode()
    return r.stdout.decode("utf-8")


def linhas(pasta: Path) -> list[dict]:
    arq = pasta / "cota.jsonl"
    return [json.loads(l) for l in arq.read_text(encoding="utf-8").splitlines()] if arq.exists() else []


def sem_cor(s: str) -> str:
    for c in (VERDE, AMARELO, VERMELHO, FIM, "\x1b[2m"):
        s = s.replace(c, "")
    return s


@pytest.fixture(params=SCRIPTS)
def qual(request):
    return request.param


# --------------------------------------------------------------------------- barra de status

def test_exemplo_da_documentacao(qual, tmp_path):
    saida = rodar(qual, json.dumps(DOCS, indent=2), tmp_path)
    assert sem_cor(saida) == "[Opus] directory | ctx 8% | 5h ▓▓░░░░░░░░ 24% ↻13:00 · 7d 41% ↻qui 13:00\n"
    assert linhas(tmp_path) == [{
        "hora": "2025-02-01T05:53:20-03:00", "pct_5h": 23.5, "reset_5h": 1738425600, "pct_7d": 41.2,
        "reset_7d": 1738857600, "modelo": "claude-opus-5-5", "modelo_nome": "Opus", "sessao": "abc123..."}]


@pytest.mark.skipif(len(SCRIPTS) < 2, reason="precisa de node e bash")
def test_node_e_bash_dao_a_mesma_saida(tmp_path):
    casos = [DOCS]
    for p5, p7 in ((55.4, 79.6), (85, 100), (0, 49.5)):
        d = copy.deepcopy(DOCS)
        d["rate_limits"]["five_hour"]["used_percentage"] = p5
        d["rate_limits"]["seven_day"]["used_percentage"] = p7
        casos.append(d)
    for i, caso in enumerate(casos):
        for compacto in (True, False):
            texto = json.dumps(caso, separators=(",", ":")) if compacto else json.dumps(caso, indent=4)
            a = rodar("mjs", texto, tmp_path / f"n{i}{compacto}")
            b = rodar("sh", texto, tmp_path / f"b{i}{compacto}")
            assert a == b, (a, b)
            assert (tmp_path / f"n{i}{compacto}" / "cota.jsonl").read_text() == (tmp_path / f"b{i}{compacto}" / "cota.jsonl").read_text()


def test_cores_por_faixa(qual, tmp_path):
    d = copy.deepcopy(DOCS)
    d["rate_limits"]["five_hour"]["used_percentage"] = 85
    d["rate_limits"]["seven_day"]["used_percentage"] = 55
    saida = rodar(qual, json.dumps(d), tmp_path)
    assert f"5h {VERMELHO}▓▓▓▓▓▓▓▓▓░ 85%{FIM}" in saida
    assert f"7d {AMARELO}55%{FIM}" in saida


def test_no_maximo_uma_linha_por_minuto(qual, tmp_path):
    texto = json.dumps(DOCS)
    rodar(qual, texto, tmp_path, AGORA)
    rodar(qual, texto, tmp_path, AGORA + 30)       # mesmo minuto (05:53)
    assert len(linhas(tmp_path)) == 1
    rodar(qual, texto, tmp_path, AGORA + 45)       # 05:54:05, minuto novo
    assert [l["hora"] for l in linhas(tmp_path)] == ["2025-02-01T05:53:20-03:00", "2025-02-01T05:54:05-03:00"]


def test_sem_rate_limits_nao_grava_e_mostra_a_barra(qual, tmp_path):
    d = copy.deepcopy(DOCS)
    del d["rate_limits"]
    assert sem_cor(rodar(qual, json.dumps(d), tmp_path)) == "[Opus] directory | ctx 8%\n"
    assert linhas(tmp_path) == []


def test_so_uma_janela(qual, tmp_path):
    d = copy.deepcopy(DOCS)
    del d["rate_limits"]["five_hour"]
    assert sem_cor(rodar(qual, json.dumps(d), tmp_path)).endswith("| 7d 41% ↻qui 13:00\n")
    l = linhas(tmp_path)[0]
    assert l["pct_5h"] is None and l["reset_5h"] is None and l["pct_7d"] == 41.2


def test_contexto_nulo_nao_pega_o_percentual_da_cota(qual, tmp_path):
    d = copy.deepcopy(DOCS)
    d["context_window"]["used_percentage"] = None
    assert sem_cor(rodar(qual, json.dumps(d), tmp_path)).startswith("[Opus] directory | ctx -- | 5h")


def test_entrada_vazia_ou_quebrada(qual, tmp_path):
    for entrada in ("", "isto não é json", "{"):
        assert rodar(qual, entrada, tmp_path) == "[?] | ctx --\n"
    assert linhas(tmp_path) == []


def test_caminho_do_windows(qual, tmp_path):
    d = copy.deepcopy(DOCS)
    d["workspace"]["current_dir"] = "C:\\Users\\loren\\OneDrive\\Claude\\projetos\\fred"
    assert sem_cor(rodar(qual, json.dumps(d), tmp_path)).startswith("[Opus] fred | ctx 8%")


def test_barra_que_voce_ja_usava(qual, tmp_path):
    (tmp_path / "cota-base.txt").write_text("echo BARRA-ANTIGA\n", encoding="utf-8")
    assert sem_cor(rodar(qual, json.dumps(DOCS), tmp_path)).startswith("BARRA-ANTIGA | 5h ")
    (tmp_path / "cota-base.txt").write_text("printf 'linha 1\\nlinha 2\\n'\n", encoding="utf-8")
    assert sem_cor(rodar(qual, json.dumps(DOCS), tmp_path)).startswith("linha 1\nlinha 2\n5h ")


# --------------------------------------------------------------------------- relatorio.py

SP = dt.timezone(dt.timedelta(hours=-3))


def ts(s: str) -> int:
    return int(dt.datetime.fromisoformat(s).timestamp())


def gravar(arq: Path, amostras: list[tuple]) -> None:
    with open(arq, "w", encoding="utf-8") as f:
        for hora, p5, r5, p7, r7, sessao in amostras:
            f.write(json.dumps({"hora": hora, "pct_5h": p5, "reset_5h": ts(r5) if r5 else None,
                                "pct_7d": p7, "reset_7d": ts(r7) if r7 else None,
                                "modelo": "claude-opus-5-5", "modelo_nome": "Opus", "sessao": sessao}) + "\n")
        f.write("linha quebrada\n")


RA, RB = "2026-10-08T13:00:00-03:00", "2026-10-15T13:00:00-03:00"
X1, X2, X3 = "2026-10-06T14:00:00-03:00", "2026-10-07T13:00:00-03:00", "2026-10-08T18:00:00-03:00"


def test_relatorio_por_dia_e_hora(tmp_path):
    arq = tmp_path / "cota.jsonl"
    gravar(arq, [
        ("2026-10-06T10:00:00-03:00", 10, X1, 50, RA, "s1"),
        ("2026-10-06T11:00:10-03:00", 40, X1, 53, RA, "s1"),   # +3 p.p. (7d) e +30 p.p. (5h) às 11h
        ("2026-10-07T09:00:00-03:00", 5, X2, 60, RA, "s1"),    # janela de 5 h nova: +5; 7d +7 às 9h
        ("2026-10-08T14:00:00-03:00", 1, X3, 2, RB, "s1"),     # semana nova: +2 às 14h
        ("2026-10-08T15:00:00-03:00", 4, X3, 5, RB, "s1"),     # +3 às 15h
        ("2026-10-08T15:00:40-03:00", 4, X3, 4.9, RB, "s2"),   # outra sessão no mesmo minuto: fica o maior
    ])
    amostras, invalidas = relatorio.ler(arq)
    assert len(amostras) == 5 and invalidas == 1
    c7 = relatorio.consumos(amostras, "7d")
    assert [(h.strftime("%d %H"), v) for h, v in c7] == [("06 11", 3), ("07 09", 7), ("08 14", 2), ("08 15", 3)]
    texto, codigo = relatorio.montar(amostras, invalidas, arq, 14, 80, 2)
    assert codigo == 0
    assert "| ter 06/10 | 3,0 p.p. | 30,0 p.p. | 40,0% | 2 |" in texto
    assert "| qua 07/10 | 7,0 p.p. | 5,0 p.p. | 5,0% | 1 |" in texto
    assert "| qui 08/10 | 5,0 p.p. | 4,0 p.p. | 4,0% | 2 |" in texto
    assert "| 09h | 7,0 p.p. | 2,33 p.p. |" in texto and "| 15h | 3,0 p.p. | 1,00 p.p. |" in texto
    assert "| 7 dias | 5,0% (às 15:00) | qui 15/10 13:00 (em 6d 22h) |" in texto
    assert "Ritmo: menos de 3 h de registro" in texto


def test_alerta_80_antes_de_quarta(tmp_path):
    arq = tmp_path / "cota.jsonl"
    rc = "2026-10-22T13:00:00-03:00"      # janela de qui 15/10 13:00 a qui 22/10 13:00; marco: qua 21/10 00:00
    gravar(arq, [("2026-10-19T10:00:00-03:00", 20, None, 70, rc, "s1"),
                 ("2026-10-20T18:00:00-03:00", 30, None, 82, rc, "s1")])
    texto, codigo = relatorio.montar(*relatorio.ler(arq), arq, 14, 80, 2)
    assert codigo == 2
    assert "ALERTA: a cota de 7 dias passou de 80% antes de qua (82,0% em ter 20/10 18:00)." in texto
    assert relatorio.main(["--arquivo", str(arq), "--saida", str(tmp_path / "r.md")]) == 2
    assert (tmp_path / "r.md").read_text(encoding="utf-8") == texto


def test_alerta_de_ritmo(tmp_path):
    arq = tmp_path / "cota.jsonl"
    rd = "2026-10-29T13:00:00-03:00"      # marco: qua 28/10 00:00
    gravar(arq, [("2026-10-23T08:00:00-03:00", 10, None, 10, rd, "s1"),
                 ("2026-10-23T14:00:00-03:00", 60, None, 40, rd, "s1")])   # 30 p.p. em 6 h = 5 p.p./h
    texto, codigo = relatorio.montar(*relatorio.ler(arq), arq, 14, 80, 2)
    assert codigo == 2
    assert "chega a 80% em sex 23/10 22:00, antes de qua." in texto
    assert "acaba em sáb 24/10 02:00, antes do reset (qui 29/10 13:00)." in texto


def test_sem_dados(tmp_path):
    arq = tmp_path / "cota.jsonl"
    arq.write_text("lixo\n", encoding="utf-8")
    assert relatorio.main(["--arquivo", str(arq)]) == 1
    assert relatorio.main(["--arquivo", str(tmp_path / "nao-existe.jsonl")]) == 1
