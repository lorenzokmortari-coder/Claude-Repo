"""Testes do vigia numa árvore sintética em pasta temporária (sem rede)."""
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import integridade as ig  # noqa: E402

FIX = Path(__file__).with_name("fixtures")
SEGREDO = "TOKEN_SINTETICO_NAO_PODE_VAZAR_123"


@pytest.fixture
def arvore(tmp_path, monkeypatch):
    casa = tmp_path / "casa"
    (casa / ".claude" / "hooks").mkdir(parents=True)
    settings = casa / ".claude" / "settings.json"
    settings.write_text(json.dumps({
        "hooks": {"PreToolUse": [{"command": "~/.claude/hooks/log.sh"}]},
        "permissions": {"allow": ["Bash(git status)"]},
        "env": {"CHAVE": SEGREDO},
        "feedbackSurveyState": {"vezes": 1},
    }), encoding="utf-8")
    claude_json = casa / ".claude.json"
    claude_json.write_text(json.dumps({
        "numStartups": 10,
        "mcpServers": {},
        "projects": {"/srv/robo": {"allowedTools": [], "mcpServers": {}, "lastCost": 0.1}},
    }), encoding="utf-8")
    (casa / ".claude" / "hooks" / "log.sh").write_text("#!/bin/sh\necho ok\n")
    env = casa / "robo" / ".env"
    env.parent.mkdir()
    env.write_text(f"SLACK_TOKEN={SEGREDO}\n")
    os.chmod(env, 0o600)
    estado = tmp_path / "estado"
    ini = tmp_path / "integridade.ini"
    ini.write_text(f"""[geral]
estado = {estado}
comando_osv = {sys.executable} {FIX / 'osv_falso.py'} {{pasta}}

[arquivos]
{settings} = hooks, permissions, env, mcpServers
{claude_json} = mcpServers, projects.*.allowedTools, projects.*.mcpServers
{env} =

[pastas]
{casa / '.claude' / 'hooks'} =

[deps]
{casa / 'robo'} =
""", encoding="utf-8")
    monkeypatch.setattr(ig, "hoje", lambda fuso: "2026-10-14")
    return {"casa": casa, "settings": settings, "claude_json": claude_json, "env": env,
            "estado": estado, "ini": ini, "hooks": casa / ".claude" / "hooks"}


def rodar(arv, *args, capsys=None):
    cod = ig.main([*args, "--ini", str(arv["ini"])])
    saida = capsys.readouterr().out if capsys else ""
    return cod, saida


def iniciar(arv, capsys):
    cod, _ = rodar(arv, "--aceitar", "base inicial", capsys=capsys)
    assert cod == 0


def mexer_json(caminho, f):
    d = json.loads(caminho.read_text(encoding="utf-8"))
    f(d)
    caminho.write_text(json.dumps(d), encoding="utf-8")


def sem_segredo(arv, *textos):
    tudo = "".join(textos) + "".join(
        p.read_text(encoding="utf-8") for p in arv["estado"].iterdir() if p.is_file())
    assert SEGREDO not in tudo


# ------------------------------------------------------------------ base

def test_sem_base_checar_e_erro(arvore, capsys):
    cod, out = rodar(arvore, "--checar", capsys=capsys)
    assert cod == 2 and "--aceitar" in out


def test_base_nova(arvore, capsys):
    iniciar(arvore, capsys)
    base = json.loads((arvore["estado"] / "base.json").read_text())
    assert str(arvore["settings"]) in base["arquivos"]
    assert oct(os.stat(arvore["estado"] / "base.json").st_mode & 0o777) == "0o600"
    livro = (arvore["estado"] / "aceites.jsonl").read_text().splitlines()
    assert json.loads(livro[0])["motivo"] == "base inicial"
    cod, out = rodar(arvore, "--checar", "--resumo", capsys=capsys)
    assert cod == 0 and out.startswith("INTEGRIDADE OK") and out.count("\n") == 1
    sem_segredo(arvore, out)


def test_base_apagada_com_livro_falha_fechada(arvore, capsys):
    iniciar(arvore, capsys)
    (arvore["estado"] / "base.json").unlink()
    cod, out = rodar(arvore, "--checar", capsys=capsys)
    assert cod == 2 and "sumiu" in out


def test_base_corrompida_e_erro(arvore, capsys):
    iniciar(arvore, capsys)
    (arvore["estado"] / "base.json").write_text("{quebrado")
    assert rodar(arvore, "--checar", capsys=capsys)[0] == 2


# ------------------------------------------------------------------ JSON

def test_chave_vigiada_mudou(arvore, capsys):
    iniciar(arvore, capsys)
    mexer_json(arvore["settings"], lambda d: d["hooks"].setdefault("Stop", [{"command": "curl x"}]))
    cod, out = rodar(arvore, "--checar", capsys=capsys)
    assert cod == 1 and "chave vigiada mudou: hooks" in out
    sem_segredo(arvore, out)


def test_segredo_no_env_do_settings_nao_vaza(arvore, capsys):
    iniciar(arvore, capsys)
    mexer_json(arvore["settings"], lambda d: d["env"].update(CHAVE=SEGREDO + "2"))
    cod, out = rodar(arvore, "--checar", capsys=capsys)
    assert cod == 1 and "chave vigiada mudou: env" in out
    sem_segredo(arvore, out)


def test_chave_ignorada_nao_avisa(arvore, capsys):
    iniciar(arvore, capsys)
    mexer_json(arvore["settings"], lambda d: d.update(feedbackSurveyState={"vezes": 99}))
    mexer_json(arvore["claude_json"], lambda d: (d.update(numStartups=11),
                                                  d["projects"]["/srv/robo"].update(lastCost=9)))
    cod, out = rodar(arvore, "--checar", capsys=capsys)
    assert cod == 0, out


def test_curinga_de_projeto_pega_mcp_novo(arvore, capsys):
    iniciar(arvore, capsys)
    mexer_json(arvore["claude_json"],
               lambda d: d["projects"]["/srv/robo"]["mcpServers"].update(x={"command": "npx y"}))
    cod, out = rodar(arvore, "--checar", capsys=capsys)
    assert cod == 1 and "projects./srv/robo.mcpServers" in out


def test_json_quebrado_falha_fechada(arvore, capsys):
    iniciar(arvore, capsys)
    arvore["settings"].write_text("{nao é json")
    cod, out = rodar(arvore, "--checar", capsys=capsys)
    assert cod == 1 and "JSON ilegível" in out


# ------------------------------------------------------------------ hooks

def test_hook_novo(arvore, capsys):
    iniciar(arvore, capsys)
    (arvore["hooks"] / "sub").mkdir()
    (arvore["hooks"] / "sub" / "novo.py").write_text("print(1)")
    cod, out = rodar(arvore, "--checar", capsys=capsys)
    assert cod == 1 and "arquivo novo na pasta vigiada" in out and "novo.py" in out


def test_hook_mudou_e_sumiu(arvore, capsys):
    iniciar(arvore, capsys)
    (arvore["hooks"] / "log.sh").write_text("#!/bin/sh\ncurl http://x\n")
    cod, out = rodar(arvore, "--checar", capsys=capsys)
    assert cod == 1 and "conteúdo mudou" in out
    (arvore["hooks"] / "log.sh").unlink()
    cod, out = rodar(arvore, "--checar", capsys=capsys)
    assert cod == 1 and "arquivo sumiu da pasta vigiada" in out


# ------------------------------------------------------------------ .env e sumiço

def test_env_644(arvore, capsys):
    iniciar(arvore, capsys)
    os.chmod(arvore["env"], 0o644)
    cod, out = rodar(arvore, "--checar", capsys=capsys)
    assert cod == 1 and "permissão 644 (máximo 600)" in out and "0600 → 0644" in out
    sem_segredo(arvore, out)


def test_env_644_nao_se_cala_com_aceite(arvore, capsys):
    os.chmod(arvore["env"], 0o644)
    cod, out = rodar(arvore, "--aceitar", "base inicial", capsys=capsys)
    assert cod == 0 and "atenção" in out
    cod, out = rodar(arvore, "--checar", capsys=capsys)
    assert cod == 1 and "máximo 600" in out


def test_arquivo_sumiu(arvore, capsys):
    iniciar(arvore, capsys)
    arvore["claude_json"].unlink()
    cod, out = rodar(arvore, "--checar", capsys=capsys)
    assert cod == 1 and "sumiu (falha fechada)" in out


@pytest.mark.skipif(os.geteuid() == 0, reason="root lê tudo")
def test_arquivo_ilegivel(arvore, capsys):
    iniciar(arvore, capsys)
    os.chmod(arvore["env"], 0o000)
    try:
        cod, out = rodar(arvore, "--checar", capsys=capsys)
    finally:
        os.chmod(arvore["env"], 0o600)
    assert cod == 1 and "ilegível" in out


def test_ini_mudado_avisa(arvore, capsys):
    iniciar(arvore, capsys)
    with open(arvore["ini"], "a", encoding="utf-8") as f:
        f.write("\n; comentário novo\n")
    cod, out = rodar(arvore, "--checar", capsys=capsys)
    assert cod == 1 and "integridade.ini" in out


# ------------------------------------------------------------------ aceite

def test_aceite_com_motivo(arvore, capsys):
    iniciar(arvore, capsys)
    antes = ig.curto(json.loads((arvore["estado"] / "base.json").read_text())
                     ["arquivos"][str(arvore["settings"])]["sha256"])
    mexer_json(arvore["settings"], lambda d: d["permissions"]["allow"].append("Bash(ls)"))
    assert rodar(arvore, "--checar", capsys=capsys)[0] == 1
    cod, _ = rodar(arvore, "--aceitar", "liberei ls para o robô", capsys=capsys)
    assert cod == 0
    reg = json.loads((arvore["estado"] / "aceites.jsonl").read_text().splitlines()[-1])
    assert reg["motivo"] == "liberei ls para o robô"
    item = [a for a in reg["arquivos"] if a["caminho"] == str(arvore["settings"])][0]
    assert item["antes"] == antes and item["depois"] != antes
    assert len((arvore["estado"] / "aceites.jsonl").read_text().splitlines()) == 2  # só acréscimo
    assert rodar(arvore, "--checar", capsys=capsys)[0] == 0


@pytest.mark.parametrize("motivo", [None, "", "   "])
def test_aceite_sem_motivo_recusa(arvore, capsys, motivo):
    iniciar(arvore, capsys)
    mexer_json(arvore["settings"], lambda d: d["permissions"]["allow"].append("Bash(*)"))
    args = ["--aceitar"] if motivo is None else ["--aceitar", motivo]
    cod, out = rodar(arvore, *args, capsys=capsys)
    assert cod == 2 and "recusado" in out
    assert len((arvore["estado"] / "aceites.jsonl").read_text().splitlines()) == 1
    assert rodar(arvore, "--checar", capsys=capsys)[0] == 1


def test_aceite_recusa_arquivo_sumido(arvore, capsys):
    iniciar(arvore, capsys)
    arvore["env"].unlink()
    cod, out = rodar(arvore, "--aceitar", "tirei o env", capsys=capsys)
    assert cod == 2 and "sumidos" in out


# ------------------------------------------------------------------ repetição

def test_repeticao_no_mesmo_dia_cala(arvore, capsys, monkeypatch):
    iniciar(arvore, capsys)
    (arvore["hooks"] / "x.sh").write_text("echo")
    assert rodar(arvore, "--checar", capsys=capsys)[0] == 1
    cod, out = rodar(arvore, "--checar", "--resumo", capsys=capsys)
    assert cod == 0 and "já avisada" in out
    assert "já avisado hoje" in (arvore["estado"] / "relatorio.md").read_text()
    # diferença nova no mesmo dia avisa
    (arvore["hooks"] / "y.sh").write_text("echo")
    cod, out = rodar(arvore, "--checar", "--resumo", capsys=capsys)
    assert cod == 1 and "1 nova" in out
    # dia seguinte avisa de novo
    monkeypatch.setattr(ig, "hoje", lambda fuso: "2026-10-15")
    assert rodar(arvore, "--checar", capsys=capsys)[0] == 1


def test_avisos_corrompido_erra_para_avisar(arvore, capsys):
    iniciar(arvore, capsys)
    (arvore["hooks"] / "x.sh").write_text("echo")
    assert rodar(arvore, "--checar", capsys=capsys)[0] == 1
    (arvore["estado"] / "avisos.json").write_text("[[[")
    assert rodar(arvore, "--checar", capsys=capsys)[0] == 1


def test_so_escreve_na_pasta_de_estado(arvore, capsys):
    antes = {p: p.stat().st_mtime_ns for p in arvore["casa"].rglob("*")}
    iniciar(arvore, capsys)
    os.chmod(arvore["env"], 0o644)
    antes[arvore["env"]] = arvore["env"].stat().st_mtime_ns
    rodar(arvore, "--checar", capsys=capsys)
    assert {p: p.stat().st_mtime_ns for p in arvore["casa"].rglob("*")} == antes
    assert oct(arvore["env"].stat().st_mode & 0o777) == "0o644"  # não conserta sozinho


def test_ini_ausente_e_erro(tmp_path, capsys):
    assert ig.main(["--checar", "--ini", str(tmp_path / "nao.ini")]) == 2


# ------------------------------------------------------------------ deps

def test_fixture_osv_uma_critica():
    dados = json.loads((FIX / "osv-saida.json").read_text())
    vulns = ig.resumir_osv(dados)
    assert [v["nivel"] for v in vulns] == ["CRÍTICA", "MÉDIA"]  # aliases contam uma vez


def test_deps_com_osv_falso(arvore, capsys):
    cod, out = rodar(arvore, "--deps", "--resumo", capsys=capsys)
    assert cod == 1 and out.startswith("DEPS · 1 ALTA/CRÍTICA") and out.count("\n") == 1
    rel = (arvore["estado"] / "deps.md").read_text()
    assert "CRÍTICA · pacote-sintetico-a@1.0.0 · GHSA-xxxx-0001-sint" in rel
    assert "CRÍTICA 1 · ALTA 0 · outras 1" in rel
    assert "pacote-sintetico-b" not in rel  # só ALTA/CRÍTICA vão para a lista


def test_osv_ausente(arvore, capsys):
    txt = arvore["ini"].read_text().replace(f"comando_osv = {sys.executable}", "comando_osv = osv-scanner-que-nao-existe")
    arvore["ini"].write_text(txt)
    cod, out = rodar(arvore, "--deps", "--resumo", capsys=capsys)
    assert cod == 3 and "não instalado" in out and out.count("\n") == 1
