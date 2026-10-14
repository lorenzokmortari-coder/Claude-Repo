"""Testes do vigia.py. Tudo SINTÉTICO: o vídeo vem do gerar_teste.py da legenda v2 (voz do espeak-ng, ou
bipes sem ele) e o faster-whisper é trocado por um modelo falso que devolve o gabarito, como nos testes da v2.
Precisa de ffmpeg. Rodar: python -m pytest -q test_vigia.py
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

import gerar_teste
import legenda_reels as lr
import vigia as vg

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
                                reason="precisa de ffmpeg")
TEXTO = "Bom dia, pessoal. Essa aposta é garantida, rende certinho. Quem chegar tarde paga o café da equipe."


class ModeloFalso:
    chamadas: list = []
    gabarito: list = []

    def __init__(self, nome, **kw):
        ModeloFalso.chamadas.append(("init", nome))

    def transcribe(self, audio, **kw):
        ModeloFalso.chamadas.append(("transcribe", kw.get("initial_prompt")))
        ws = [SimpleNamespace(start=p["inicio"], end=p["fim"], word=" " + p["texto"],
                              probability=0.3 if i in (4, 9) else 0.95) for i, p in enumerate(ModeloFalso.gabarito)]
        return iter([SimpleNamespace(words=ws)]), SimpleNamespace(language="pt")


@pytest.fixture(scope="module")
def video_base(tmp_path_factory):
    d = tmp_path_factory.mktemp("base")
    v = gerar_teste.gerar_video(d / "base.mp4", TEXTO, largura=540, altura=960)
    return v, json.loads(v.with_suffix(".gabarito.json").read_text(encoding="utf-8"))


@pytest.fixture
def raiz(tmp_path, video_base):
    ModeloFalso.chamadas, ModeloFalso.gabarito = [], video_base[1]
    (tmp_path / "entrada").mkdir()
    return tmp_path


def copiar(video_base, raiz: Path, nome: str) -> Path:
    destino = raiz / "entrada" / nome
    shutil.copyfile(video_base[0], destino)
    antigo = time.time() - 120                      # cópia já terminada há dois minutos
    os.utime(destino, (antigo, antigo))
    return destino


def vigia(raiz: Path, **kw) -> vg.Vigia:
    op = vg.Opcoes(estavel=0.2, passo=0.1, fonte="DejaVu Sans", **kw)
    return vg.Vigia(raiz, op, carregar=ModeloFalso)


def marcar_ok(raiz: Path, nome: str) -> Path:
    ok = raiz / "revisao" / nome / f"{nome}.ok"
    ok.write_text("", encoding="utf-8")
    js = raiz / "revisao" / nome / f"{nome}.palavras.json"
    t = js.stat().st_mtime + 1
    os.utime(ok, (t, t))
    return ok


def duracao(p: Path) -> float:
    return lr.sondar(p)["duracao"]


# --------------------------------------------------------------------------- revisar, nunca queimar sozinho

def test_video_novo_vira_revisao_e_nada_e_queimado(raiz, video_base):
    copiar(video_base, raiz, "reuniao.mp4")
    resumo = vigia(raiz).rodada()
    assert resumo == {"reuniao": "aguardando revisão"}
    pasta = raiz / "revisao" / "reuniao"
    rev = (pasta / "reuniao.revisar.txt").read_text(encoding="utf-8")
    assert rev.startswith("PELO VIGIA") and "reuniao.ok" in rev and "2 de " in rev      # as 2 palavras duvidosas
    js = json.loads((pasta / "reuniao.palavras.json").read_text(encoding="utf-8"))
    assert js["revisado"] is False and len(js["palavras"]) == len(video_base[1])
    assert sorted(p.name for p in pasta.glob("*_previa_*.png")) == [f"reuniao_previa_{k}.png" for k in (1, 2, 3)]
    assert list((raiz / "saida").iterdir()) == []                                      # nada queimado
    assert not (pasta / "publi-checklist.rascunho.md").exists()


def test_previa_tem_legenda_desenhada(raiz, video_base):
    copiar(video_base, raiz, "reuniao.mp4")
    vigia(raiz).rodada()
    png = raiz / "revisao" / "reuniao" / "reuniao_previa_1.png"
    p = video_base[1][1]
    cru = raiz / "cru.png"
    subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{(p['inicio'] + p['fim']) / 2:.3f}", "-i", str(video_base[0]),
                    "-frames:v", "1", str(cru)], check=True)
    def cinza(arq):
        return subprocess.run(["ffmpeg", "-v", "error", "-i", str(arq), "-vf", "crop=iw:ih*0.16:0:ih*0.54",
                               "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
    a, b = cinza(png), cinza(cru)
    assert sum(abs(x - y) for x, y in zip(a, b)) / len(a) > 5                      # a faixa da legenda mudou


def test_segunda_rodada_nao_refaz(raiz, video_base):
    copiar(video_base, raiz, "reuniao.mp4")
    v = vigia(raiz)
    v.rodada()
    js = raiz / "revisao" / "reuniao" / "reuniao.palavras.json"
    antes = (js.read_bytes(), js.stat().st_mtime_ns)
    n = len(ModeloFalso.chamadas)
    assert v.rodada() == {"reuniao": "aguardando revisão"}
    assert len(ModeloFalso.chamadas) == n                                              # o modelo não roda de novo
    assert (js.read_bytes(), js.stat().st_mtime_ns) == antes                          # a correção do dono não é pisada


def test_arquivo_ainda_copiando_nao_e_lido(raiz, video_base):
    destino = raiz / "entrada" / "chegando.mp4"
    dados = video_base[0].read_bytes()
    destino.write_bytes(dados[: len(dados) // 2])
    v = vigia(raiz)
    resto = [dados[len(dados) // 2:]]

    def dormir_copiando(s):                        # enquanto o vigia espera, a cópia continua
        if resto:
            with open(destino, "ab") as f:
                f.write(resto.pop())
        time.sleep(s)
    v.dormir = dormir_copiando
    assert v.rodada() == {"chegando": "copiando"}
    assert not (raiz / "revisao" / "chegando").exists() and ModeloFalso.chamadas == []
    v.dormir = time.sleep
    assert v.rodada() == {"chegando": "aguardando revisão"}                           # parou de crescer: agora vai


def test_ignora_temporario_e_o_que_nao_e_video(raiz, video_base):
    copiar(video_base, raiz, "baixando.mp4.crdownload")
    (raiz / "entrada" / "notas.txt").write_text("x", encoding="utf-8")
    (raiz / "entrada" / "~$rascunho.mp4").write_bytes(b"x")
    assert vigia(raiz).rodada() == {}


# --------------------------------------------------------------------------- queimar só com o .ok

def test_ok_queima_e_a_saida_tem_a_mesma_duracao(raiz, video_base, monkeypatch):
    bruto = copiar(video_base, raiz, "reuniao.mp4")
    v = vigia(raiz)
    v.rodada()
    js = raiz / "revisao" / "reuniao" / "reuniao.palavras.json"
    d = json.loads(js.read_text(encoding="utf-8"))
    d["palavras"][4]["texto"] = "aposta"                                              # a correção do dono
    js.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    assert v.rodada() == {"reuniao": "aguardando revisão"}                            # sem .ok, nada
    marcar_ok(raiz, "reuniao")
    comandos = []
    real = subprocess.run

    def gravar(cmd, *a, **k):
        comandos.append(" ".join(map(str, cmd)))
        return real(cmd, *a, **k)
    monkeypatch.setattr(subprocess, "run", gravar)
    assert v.rodada() == {"reuniao": "queimado"}
    saida = raiz / "saida" / "reuniao_legendado.mp4"
    assert saida.exists() and abs(duracao(saida) - duracao(bruto)) < 0.15             # não cortou nada
    assert len(list((raiz / "saida").glob("reuniao_legendado_print_*.png"))) == 3
    assert "APOSTA" in (raiz / "saida" / "reuniao_legendado.ass").read_text(encoding="utf-8")
    for c in comandos:
        for proibido in ("silenceremove", "silencedetect", "atrim", "trim=", "-t ", "-to "):
            assert proibido not in c, c
    n = len(comandos)
    assert v.rodada() == {"reuniao": "queimado"} and len(comandos) == n                # não queima de novo


def test_json_mexido_depois_do_ok_espera_novo_ok(raiz, video_base):
    copiar(video_base, raiz, "reuniao.mp4")
    v = vigia(raiz)
    v.rodada()
    marcar_ok(raiz, "reuniao")
    v.rodada()
    saida = raiz / "saida" / "reuniao_legendado.mp4"
    primeira = saida.stat().st_mtime_ns
    js = raiz / "revisao" / "reuniao" / "reuniao.palavras.json"
    d = json.loads(js.read_text(encoding="utf-8"))
    d["palavras"][0]["texto"] = "Boa"
    time.sleep(0.02)
    js.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    t = time.time() + 5
    os.utime(js, (t, t))
    assert v.rodada() == {"reuniao": "aguardando novo .ok"}
    assert saida.stat().st_mtime_ns == primeira
    marcar_ok(raiz, "reuniao")
    assert v.rodada() == {"reuniao": "queimado"}
    assert saida.stat().st_mtime_ns != primeira and "BOA" in saida.with_suffix(".ass").read_text(encoding="utf-8")


def test_json_quebrado_nao_queima_e_avisa(raiz, video_base):
    copiar(video_base, raiz, "reuniao.mp4")
    v = vigia(raiz)
    v.rodada()
    js = raiz / "revisao" / "reuniao" / "reuniao.palavras.json"
    js.write_text('{"revisado": true, "palavras": [', encoding="utf-8")
    marcar_ok(raiz, "reuniao")
    assert v.rodada() == {"reuniao": "erro"}
    assert not (raiz / "saida" / "reuniao_legendado.mp4").exists()
    assert "Nada foi queimado" in (raiz / "revisao" / "reuniao" / "ERRO.txt").read_text(encoding="utf-8")


def test_bruto_trocado_depois_da_revisao_para_tudo(raiz, video_base):
    bruto = copiar(video_base, raiz, "reuniao.mp4")
    v = vigia(raiz)
    v.rodada()
    marcar_ok(raiz, "reuniao")
    os.utime(bruto, (time.time(), time.time()))                                       # outro arquivo com o mesmo nome
    n = len(ModeloFalso.chamadas)
    assert v.rodada() == {"reuniao": "bruto mudou: parado"}
    assert not (raiz / "saida" / "reuniao_legendado.mp4").exists() and len(ModeloFalso.chamadas) == n


# --------------------------------------------------------------------------- o bruto, a rede e a trava

def test_bruto_nunca_e_apagado_nem_movido(raiz, video_base, monkeypatch):
    bruto = copiar(video_base, raiz, "reuniao.mp4")
    entrada = (raiz / "entrada").resolve()
    antes = (hashlib.sha256(bruto.read_bytes()).hexdigest(), bruto.stat().st_mtime_ns, sorted(os.listdir(entrada)))

    def guarda(nome, real):
        def f(*a, **k):
            for x in a[:2]:
                if isinstance(x, (str, os.PathLike)) and entrada in Path(x).resolve().parents:
                    pytest.fail(f"{nome} em entrada/: {x}")
            return real(*a, **k)
        return f
    for mod, nome in ((os, "remove"), (os, "unlink"), (os, "rename"), (os, "replace"), (shutil, "move"), (shutil, "rmtree")):
        monkeypatch.setattr(mod, nome, guarda(nome, getattr(mod, nome)))
    v = vigia(raiz)
    v.rodada()
    marcar_ok(raiz, "reuniao")
    v.rodada()
    assert (raiz / "saida" / "reuniao_legendado.mp4").exists()
    assert (hashlib.sha256(bruto.read_bytes()).hexdigest(), bruto.stat().st_mtime_ns, sorted(os.listdir(entrada))) == antes


def test_nunca_usa_rede(raiz, video_base, monkeypatch):
    def proibido(*a, **k):
        raise AssertionError("o vigia tentou abrir conexão de rede")
    monkeypatch.setattr(socket.socket, "connect", proibido)
    monkeypatch.setattr(socket.socket, "connect_ex", proibido)
    copiar(video_base, raiz, "reuniao.mp4")
    v = vigia(raiz)
    v.rodada()
    marcar_ok(raiz, "reuniao")
    assert v.rodada() == {"reuniao": "queimado"}
    fonte = (Path(vg.__file__)).read_text(encoding="utf-8").lower()
    for termo in ("requests", "urllib", "http.client", "instagram", "graph.facebook", "smtplib"):
        assert termo not in fonte, termo


def test_trava_impede_duas_rodadas_e_trava_velha_e_tomada(raiz, video_base):
    copiar(video_base, raiz, "reuniao.mp4")
    (raiz / ".vigia").mkdir()
    trava = raiz / ".vigia" / "trava"
    trava.write_text("pid=1", encoding="utf-8")
    assert vigia(raiz).rodada() == {"_ocupado": True}
    assert not (raiz / "revisao" / "reuniao").exists()
    velho = time.time() - 7 * 3600
    os.utime(trava, (velho, velho))
    assert vigia(raiz).rodada() == {"reuniao": "aguardando revisão"}
    assert not trava.exists()                                                          # solta no fim


# --------------------------------------------------------------------------- publi

def test_publi_gera_checklist_rascunho_com_dicas(raiz, video_base):
    copiar(video_base, raiz, "publi_marca-teste_2026-10-20.mp4")
    copiar(video_base, raiz, "republica.mp4")
    vigia(raiz).rodada()
    ck = (raiz / "revisao" / "publi_marca-teste_2026-10-20" / "publi-checklist.rascunho.md").read_text(encoding="utf-8")
    assert "RASCUNHO" in ck and "Nenhum item está aprovado" in ck and "marca-teste" in ck
    assert ck.count("[ ]") == 10 and "[x]" not in ck.lower()
    assert "\"aposta\"" in ck.split("## 1.")[1].split("## 2.")[0]                     # "aposta" -> autorização
    assert "\"garantida\"" in ck.split("## 5.")[1].split("## 6.")[0]                  # promessa -> prova da marca
    assert "Dica da transcrição" in ck.split("## 8.")[1].split("## 9.")[0]           # "aposta" -> item da bet
    assert "\"rende\"" in ck.split("## 7.")[1].split("## 8.")[0]                     # "rende" -> financeiro
    assert not (raiz / "revisao" / "republica" / "publi-checklist.rascunho.md").exists()


def test_status(raiz, video_base):
    copiar(video_base, raiz, "a.mp4")
    copiar(video_base, raiz, "b.mp4")
    v = vigia(raiz)
    v.rodada()
    marcar_ok(raiz, "b")
    assert dict(v.status()) == {"a.mp4": "aguardando revisão (crie o .ok)", "b.mp4": ".ok criado: queima na próxima rodada"}
    estado = json.loads((raiz / ".vigia" / "estado.json").read_text(encoding="utf-8"))
    assert estado["videos"] == {"a": "aguardando revisão", "b": "aguardando revisão"}
