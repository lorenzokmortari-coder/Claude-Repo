"""Testes do legenda_reels.py. Tudo SINTÉTICO: palavras inventadas e um vídeo gerado pelo
gerar_teste.py (fundo em degradê + voz do espeak-ng). O faster-whisper é trocado por um modelo
falso que devolve o gabarito, porque o modelo de verdade vem do HuggingFace. A parte de ponta a
ponta pula sem ffmpeg ou sem espeak-ng. Rodar: python -m pytest -q
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import gerar_teste
import legenda_reels as lr

TEM_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
TEM_ESPEAK = shutil.which("espeak-ng") is not None


def frase(texto: str, inicio: float = 0.5, passo: float = 0.35, pausas: dict[int, float] | None = None) -> list[lr.Palavra]:
    out, t = [], inicio
    for i, w in enumerate(texto.split()):
        t += (pausas or {}).get(i, 0.0)
        out.append(lr.Palavra(round(t, 3), round(t + passo - 0.05, 3), w))
        t += passo
    return out


def sem_tags(linha: str) -> str:
    return re.sub(r"\{[^}]*\}", "", linha.split(",,", 1)[1].split(",", 4)[-1])


# --------------------------------------------------------------------------- unidades

def test_cor_tempo_e_trechos():
    assert lr.cor_ass("#FFE14D") == "&H004DE1FF"
    assert lr.cor_ass("ffffff", 0x60) == "&H60FFFFFF"
    with pytest.raises(ValueError):
        lr.cor_ass("amarelo")
    assert lr.tempo_ass(3725.456) == "1:02:05.46"
    assert lr.ler_trechos("0:12-0:15, 1:02-1:05.5") == [(12.0, 15.0), (62.0, 65.5)]
    assert lr.ler_trechos("") == []
    for ruim in ("12", "15-12", "a-b"):
        with pytest.raises(ValueError):
            lr.ler_trechos(ruim)
    ps = frase("um dois três quatro")       # 0.5-0.8, 0.85-1.15, 1.2-1.5, 1.55-1.85
    assert [p.texto for p in lr.tirar_trechos(ps, [(1.0, 1.3)])] == ["um", "quatro"]


def test_blocos_equilibrados_sem_palavra_sozinha():
    e = lr.Estilo()
    ps = frase("A reunião de hoje começa às nove em ponto. Quem chegar atrasado apresenta o relatório do trimestre inteiro.")
    blocos = [[p.texto for p in b] for b in lr.agrupar(ps, e)]
    assert all(2 <= len(b) <= 4 for b in blocos), blocos
    assert ["ponto."] not in blocos
    for b in blocos[:-1]:
        assert b[-1].lower() not in {"de", "às", "em", "o", "do"} or b[-1].endswith("."), blocos
    assert any(b[-1] == "ponto." for b in blocos)          # o ponto final fecha o bloco
    assert all(len(" ".join(b)) <= e.max_caracteres for b in blocos)


def test_pausa_e_frase_curta():
    e = lr.Estilo()
    ps = frase("Não. Eu falei que a reunião era hoje", pausas={1: 0.9})
    blocos = [[p.texto for p in b] for b in lr.agrupar(ps, e)]
    assert blocos[0] == ["Não."]                 # frase de uma palavra fica sozinha
    assert sum(len(b) for b in blocos) == 8
    longa = frase("um dois três quatro cinco seis", pausas={3: 0.8})
    assert [len(b) for b in lr.agrupar(longa, e)] == [3, 3]   # pausa longa sempre corta


def test_quebra_de_linha_equilibrada():
    assert lr.quebrar(["BOM", "DIA"], 14) is None
    assert lr.quebrar(["BOM", "DIA,", "PESSOAL."], 14) == 2
    assert lr.quebrar(["DO", "TRIMESTRE", "INTEIRO."], 14) == 2


def test_ass_um_destaque_por_evento_e_layout_estavel():
    e = lr.Estilo()
    ps = frase("Bom dia, pessoal. A {reunião} de hoje começa às nove em ponto.")
    grupos = lr.agrupar(ps, e)
    ass = lr.gerar_ass(grupos, 1080, 1920, e)
    assert "PlayResX: 1080" in ass and "PlayResY: 1920" in ass
    assert "Style: Reels,Arial Black,86,&H00FFFFFF,&H004DE1FF,&H00000000,&H60000000,-1," in ass
    eventos = [l for l in ass.splitlines() if l.startswith("Dialogue:")]
    assert len(eventos) == len(ps)
    for ev in eventos:
        assert ev.count("\\c&H004DE1FF\\fscx112\\fscy112") == 1
        x, y = map(int, re.search(r"\\pos\((\d+),(\d+)\)", ev).groups())
        assert 1920 * 0.14 < y < 1920 * 0.65 and 1080 * 0.06 < x < 1080 * 0.88
    assert "(REUNIÃO)" in ass and "{reunião}" not in ass   # chave vira parêntese, nunca tag
    # todos os eventos de um bloco têm o mesmo texto e a mesma quebra de linha
    i = 0
    for g in grupos:
        textos = {sem_tags(ev) for ev in eventos[i:i + len(g)]}
        assert len(textos) == 1, textos
        i += len(g)
    # tempos: começam na palavra, sem sobrepor o bloco seguinte
    def t(s):
        h, m, r = s.split(":")
        return int(h) * 3600 + int(m) * 60 + float(r)
    tempos = [(t(ev.split(",")[1]), t(ev.split(",")[2])) for ev in eventos]
    assert all(a < b for a, b in tempos)
    assert all(tempos[k][1] <= tempos[k + 1][0] + 1e-9 for k in range(len(tempos) - 1))
    assert tempos[0][0] == pytest.approx(ps[0].inicio, abs=0.01)


def test_posicao_fica_dentro_da_area_segura():
    e = lr.Estilo(posicao=0.95)                       # pedido fora da área: puxa para dentro
    ass = lr.gerar_ass([frase("oi gente")], 1080, 1920, e)
    y = int(re.search(r"\\pos\(\d+,(\d+)\)", ass).group(1))
    assert y <= 1920 * (1 - e.base)


class ModeloFalso:
    chamadas: list = []

    def __init__(self, nome, **kw):
        ModeloFalso.chamadas.append(("init", nome, kw))
        self.palavras = []

    def transcribe(self, caminho, **kw):
        ModeloFalso.chamadas.append(("transcribe", caminho, kw))
        palavras = [SimpleNamespace(start=p["inicio"], end=p["fim"], word=" " + p["texto"], probability=0.9)
                    for p in ModeloFalso.gabarito]
        return iter([SimpleNamespace(words=palavras)]), SimpleNamespace(language="pt")


def test_transcrever_pede_tempo_por_palavra():
    ModeloFalso.chamadas, ModeloFalso.gabarito = [], [{"inicio": 0.5, "fim": 0.8, "texto": "Bom"},
                                                       {"inicio": 0.9, "fim": 1.2, "texto": "dia."}]
    ps = lr.transcrever(Path("x.mp4"), carregar=ModeloFalso)
    assert [(p.texto, p.inicio, p.prob) for p in ps] == [("Bom", 0.5, 0.9), ("dia.", 0.9, 0.9)]
    (_, nome, kw_init), (_, _, kw) = ModeloFalso.chamadas
    assert nome == "small" and kw_init["device"] == "cpu" and kw_init["compute_type"] == "int8"
    assert kw["language"] == "pt" and kw["word_timestamps"] is True and kw["vad_filter"] is True


def test_comparar_com_gabarito():
    g = [{"inicio": 0.5, "fim": 0.8, "texto": "Bom"}, {"inicio": 0.9, "fim": 1.2, "texto": "dia,"},
         {"inicio": 1.5, "fim": 2.0, "texto": "pessoal."}]
    assert gerar_teste.comparar(g, g) == {"acerto": 1.0, "erro_inicio_s": 0.0, "erro_fim_s": 0.0, "palavras_gabarito": 3}
    t = [{"inicio": 0.55, "fim": 0.8, "texto": "bom"}, {"inicio": 1.6, "fim": 2.1, "texto": "Pessoal"}]
    r = gerar_teste.comparar(t, g)
    assert r["acerto"] == pytest.approx(0.667, abs=0.001) and r["erro_inicio_s"] == pytest.approx(0.075)


# --------------------------------------------------------------------------- ponta a ponta

def quadro_cinza(video: Path, t: float) -> tuple[bytes, int, int]:
    info = lr.sondar(video)
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
                        "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True)
    return r.stdout, info["largura"], info["altura"]


def diferenca(a: Path, b: Path, t: float, y0: float, y1: float) -> float:
    qa, w, h = quadro_cinza(a, t)
    qb, _, _ = quadro_cinza(b, t)
    linhas = range(int(h * y0), int(h * y1))
    total = sum(abs(qa[r * w + c] - qb[r * w + c]) for r in linhas for c in range(0, w, 2))
    return total / (len(linhas) * len(range(0, w, 2)))


@pytest.mark.skipif(not (TEM_FFMPEG and TEM_ESPEAK), reason="precisa de ffmpeg e espeak-ng")
def test_ponta_a_ponta_video_sintetico(tmp_path: Path):
    video = gerar_teste.gerar_video(tmp_path / "teste.mp4", largura=540, altura=960)
    gabarito = json.loads(video.with_suffix(".gabarito.json").read_text(encoding="utf-8"))
    ModeloFalso.chamadas, ModeloFalso.gabarito = [], gabarito
    # tira a legenda das palavras 5 a 8 ("de hoje começa às")
    a, b = gabarito[5]["inicio"] - 0.01, gabarito[8]["fim"] + 0.01
    saida = lr.main([str(video), "--sem-legenda", f"{a:.2f}-{b:.2f}", "--fonte", "DejaVu Sans", "--prints", "3"],
                    carregar=ModeloFalso)
    assert saida == tmp_path / "teste_legendado.mp4"
    assert video.with_suffix(".palavras.json").exists()                 # transcrição salva para corrigir
    i0, i1 = lr.sondar(video), lr.sondar(saida)
    assert (i1["largura"], i1["altura"]) == (540, 960) and abs(i1["duracao"] - i0["duracao"]) < 0.15
    canais = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(saida)],
                            capture_output=True, text=True).stdout.split()
    assert "audio" in canais
    assert len(list(tmp_path.glob("teste_legendado_print_*.png"))) == 3

    p0 = gabarito[0]
    assert diferenca(video, saida, (p0["inicio"] + p0["fim"]) / 2, 0.50, 0.66) > 8      # tem legenda
    meio = (gabarito[7]["inicio"] + gabarito[7]["fim"]) / 2                             # trecho sem legenda
    assert diferenca(video, saida, meio, 0.50, 0.66) < 3

    # segunda rodada usa o palavras.json salvo: o modelo não é chamado de novo
    n = len(ModeloFalso.chamadas)
    lr.main([str(video), "--so-ass"], carregar=ModeloFalso)
    assert len(ModeloFalso.chamadas) == n


@pytest.mark.skipif(not TEM_FFMPEG, reason="precisa de ffmpeg")
def test_video_de_celular_com_rotacao(tmp_path: Path):
    deitado = tmp_path / "deitado.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=gray:s=640x360:d=1", "-c:v", "libx264",
                    str(deitado)], check=True)
    girado = tmp_path / "girado.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-display_rotation", "90", "-i", str(deitado), "-c", "copy", str(girado)], check=True)
    assert (lr.sondar(deitado)["largura"], lr.sondar(deitado)["altura"]) == (640, 360)
    assert (lr.sondar(girado)["largura"], lr.sondar(girado)["altura"]) == (360, 640)
