"""Testes do legenda_reels.py (v2). Tudo SINTÉTICO: palavras inventadas e vídeos gerados pelo
gerar_teste.py (fundo em degradê + voz do espeak-ng, ou bipes sem ele) ou pelo ffmpeg. O faster-whisper
é trocado por um modelo falso que devolve o gabarito, porque o modelo de verdade vem do HuggingFace. A
parte de ponta a ponta pula sem ffmpeg. Rodar: python -m pytest -q

Os testes da v1 continuam aqui. Cinco tiveram de mudar porque o padrão mudou por ordem (14/10/2026), e cada
mudança está marcada com "v2:" no próprio teste:
  - test_blocos_equilibrados_sem_palavra_sozinha e test_pausa_e_frase_curta: passam a usar os limites da v1 (4
    palavras, 22 caracteres) de forma explícita, porque medem o algoritmo; com o padrão novo (3 e 16) uma palavra
    sozinha às vezes é inevitável;
  - test_ass_um_destaque_por_evento_e_layout_estavel: o tamanho padrão passou de 4,5% (86 px) para 5,8% (111 px);
  - test_transcrever_pede_tempo_por_palavra: o modelo padrão passou de small para medium (pelo id do HuggingFace)
    e o áudio chega como array (o teste passa um decodificador falso);
  - test_ponta_a_ponta_video_sintetico: a revisão virou obrigatória (o teste usa --sem-revisar) e roda sem
    espeak-ng (bipes no lugar da voz).
Os testes novos da v2 ficam no fim, um bloco por defeito (D1 a D7) e por pedido (ajustes, revisão, aviso).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import numpy as np
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
    # v2: o padrão virou 2 a 3 palavras e 16 caracteres, e com ele "Quem" fica sozinho (não há partição sem palavra
    # sozinha em que "atrasado apresenta", 18 caracteres, caiba). Este teste mede o algoritmo com os limites da v1.
    e = lr.Estilo(max_palavras=4, max_caracteres=22)
    ps = frase("A reunião de hoje começa às nove em ponto. Quem chegar atrasado apresenta o relatório do trimestre inteiro.")
    blocos = [[p.texto for p in b] for b in lr.agrupar(ps, e)]
    assert all(2 <= len(b) <= 4 for b in blocos), blocos
    assert ["ponto."] not in blocos
    for b in blocos[:-1]:
        assert b[-1].lower() not in {"de", "às", "em", "o", "do"} or b[-1].endswith("."), blocos
    assert any(b[-1] == "ponto." for b in blocos)          # o ponto final fecha o bloco
    assert all(len(" ".join(b)) <= e.max_caracteres for b in blocos)


def test_pausa_e_frase_curta():
    e = lr.Estilo(max_palavras=4, max_caracteres=22)  # v2: limites da v1 ("quatro cinco seis" tem 17 caracteres)
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
    # v2: tamanho padrão 5,8% da altura (111 px em 1920); era 4,5% (86 px)
    assert "Style: Reels,Arial Black,111,&H00FFFFFF,&H004DE1FF,&H00000000,&H60000000,-1," in ass
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
    # v2: o áudio chega como array (decodificador falso aqui) e o padrão é o medium, pelo id do HuggingFace
    ps = lr.transcrever(Path("x.mp4"), carregar=ModeloFalso, decodificar=lambda v: np.zeros(16000, dtype=np.float32))
    assert [(p.texto, p.inicio, p.prob) for p in ps] == [("Bom", 0.5, 0.9), ("dia.", 0.9, 0.9)]
    (_, nome, kw_init), (_, _, kw) = ModeloFalso.chamadas
    assert nome == "Systran/faster-whisper-medium" and kw_init["device"] == "cpu" and kw_init["compute_type"] == "int8"
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


@pytest.mark.skipif(not TEM_FFMPEG, reason="precisa de ffmpeg")  # v2: sem espeak-ng, o gerar_teste usa bipes
def test_ponta_a_ponta_video_sintetico(tmp_path: Path):
    video = gerar_teste.gerar_video(tmp_path / "teste.mp4", largura=540, altura=960)
    gabarito = json.loads(video.with_suffix(".gabarito.json").read_text(encoding="utf-8"))
    ModeloFalso.chamadas, ModeloFalso.gabarito = [], gabarito
    # tira a legenda das palavras 5 a 8 ("de hoje começa às")
    a, b = gabarito[5]["inicio"] - 0.01, gabarito[8]["fim"] + 0.01
    # v2: a revisão é obrigatória; este teste mede a legenda, então pula a revisão de propósito
    saida = lr.main([str(video), "--sem-legenda", f"{a:.2f}-{b:.2f}", "--fonte", "DejaVu Sans", "--prints", "3",
                     "--sem-revisar", "--sem-aviso-legenda"], carregar=ModeloFalso)
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
    lr.main([str(video), "--so-ass", "--sem-revisar"], carregar=ModeloFalso)
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


# =========================================================================== v2: um bloco por defeito

def eventos_de(ass: str) -> list[str]:
    return [l for l in ass.splitlines() if l.startswith("Dialogue:")]


def video_simples(destino: Path, s: str = "540x960", dur: float = 2.0, texto: str | None = None) -> Path:
    """Vídeo curto com degradê e um tom; com `texto`, uma "legenda da edição" queimada (branca com contorno preto)
    que troca de frase a cada 0,7 s, na faixa de baixo."""
    vf = "format=yuv420p"
    if texto:
        fonte = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        frases = texto.split("|")
        partes = []
        for k, f in enumerate(frases):
            a, b = k * dur / len(frases), (k + 1) * dur / len(frases)
            partes.append(f"drawtext=fontfile='{fonte}':text='{f}':fontsize=h*0.045:fontcolor=white:borderw=4:"
                          f"bordercolor=black:x=(w-text_w)/2:y=h*0.70:enable='between(t,{a:.2f},{b:.2f})'")
        vf += "," + ",".join(partes)
    w, h = s.split("x")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                    f"gradients=s={s}:r=25:d={dur}:speed=0.02:c0=0x173042:c1=0x2f6170:nb_colors=2:seed=3",
                    "-f", "lavfi", "-i", f"sine=frequency=330:duration={dur}", "-vf", vf, "-c:v", "libx264",
                    "-preset", "veryfast", "-c:a", "aac", "-shortest", str(destino)], check=True)
    return destino


# --- D1. PyAV novo quebrava o faster-whisper 1.2.1: o áudio vem do ffmpeg, como array

@pytest.mark.skipif(not TEM_FFMPEG, reason="precisa de ffmpeg")
def test_d1_transcrever_manda_ao_modelo_o_audio_decodificado_pelo_ffmpeg(tmp_path: Path):
    wav = tmp_path / "tom.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=1", "-ar", "44100", str(wav)], check=True)
    ModeloFalso.chamadas, ModeloFalso.gabarito = [], [{"inicio": 0.1, "fim": 0.4, "texto": "oi"}]
    lr.transcrever(wav, carregar=ModeloFalso)
    audio = ModeloFalso.chamadas[1][1]
    assert isinstance(audio, np.ndarray) and audio.dtype == np.float32      # nunca o caminho: o PyAV fica de fora
    assert abs(audio.size - 16000) < 400                                       # 1 s em 16 kHz, mono


def _pyav_major():
    try:
        import av
        return int(str(av.__version__).split(".")[0])
    except Exception:
        return None


@pytest.mark.skipif(not TEM_FFMPEG or _pyav_major() is None or _pyav_major() < 16, reason="só reproduz com PyAV 16+")
def test_d1_reproduz_o_defeito_do_pyav_e_o_contorno(tmp_path: Path):
    fw_audio = pytest.importorskip("faster_whisper.audio")
    wav = tmp_path / "tom.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=1", str(wav)], check=True)
    with pytest.raises(TypeError, match="metadata_errors"):
        fw_audio.decode_audio(str(wav))                     # o caminho da v1 (o faster-whisper decodifica com o PyAV)
    assert lr.decodificar_audio(wav).size > 15000          # o caminho da v2


# --- D2. --guia pintava o MP4 final

def media_vermelho_menos_verde(caminho: Path, t: float | None, y0: float, y1: float) -> float:
    args = ["ffmpeg", "-v", "error"] + (["-ss", f"{t:.3f}"] if t is not None else []) + ["-i", str(caminho), "-frames:v", "1",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(args, capture_output=True, check=True).stdout
    info = lr.sondar(caminho) if caminho.suffix == ".mp4" else None
    w, h = (info["largura"], info["altura"]) if info else (540, 960)
    a = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3).astype(int)
    faixa = a[int(h * y0):int(h * y1)]
    return float((faixa[..., 0] - faixa[..., 1]).mean())


@pytest.mark.skipif(not TEM_FFMPEG, reason="precisa de ffmpeg")
def test_d2_guia_vai_so_nos_png_e_o_mp4_sai_limpo(tmp_path: Path):
    video = gerar_teste.gerar_video(tmp_path / "teste.mp4", largura=540, altura=960)
    gabarito = json.loads(video.with_suffix(".gabarito.json").read_text(encoding="utf-8"))
    ModeloFalso.chamadas, ModeloFalso.gabarito = [], gabarito
    saida = lr.main([str(video), "--fonte", "DejaVu Sans", "--prints", "2", "--guia", "--sem-revisar", "--sem-aviso-legenda"],
                    carregar=ModeloFalso)
    t = (gabarito[0]["inicio"] + gabarito[0]["fim"]) / 2
    # topo (fora da área segura): no MP4 a cor é a do vídeo original; nos PNG de guia, avermelhada
    assert abs(media_vermelho_menos_verde(saida, t, 0.0, 0.10) - media_vermelho_menos_verde(video, t, 0.0, 0.10)) < 4
    guias = sorted(tmp_path.glob("teste_legendado_guia_*.png"))
    assert len(guias) == 2 and len(list(tmp_path.glob("teste_legendado_print_*.png"))) == 2
    assert media_vermelho_menos_verde(guias[0], None, 0.0, 0.10) - media_vermelho_menos_verde(video, t, 0.0, 0.10) > 30


# --- D3. largura de letra 0,72 quebrava em duas linhas bloco que cabia em uma

def test_d3_bloco_de_ate_16_caracteres_cabe_numa_linha_no_padrao():
    e = lr.Estilo()
    for texto in ("CHEGAR ATRASADO", "QUEM CHEGAR CEDO", "PRA REUNIÃO, NÉ?"):
        assert len(texto) <= e.max_caracteres
        ass = lr.gerar_ass([frase(texto)], 1080, 1920, e)
        assert all("\\N" not in ev for ev in eventos_de(ass)), texto
    # e o que não cabe continua quebrando, sempre no mesmo lugar em todos os eventos do bloco
    ass = lr.gerar_ass([frase("RELATÓRIO TRIMESTRAL CONSOLIDADO")], 1080, 1920, lr.Estilo(max_caracteres=40))
    assert all(ev.count("\\N") == 1 for ev in eventos_de(ass))


def test_d3_espaco_vale_meia_letra():
    assert lr.largura_rel("AB CD") == 4.5
    assert lr.quebrar(["QUEM", "CHEGAR", "CEDO"], 15.0) is None      # 16 caracteres, 2 espaços = 15 letras


# --- D4. número partido pelo Whisper ("5 ,45,") e hora

def P(*tokens):
    return [lr.Palavra(0.3 * i, 0.3 * i + 0.25, t, 0.9 - 0.1 * i) for i, t in enumerate(tokens)]


def test_d4_numero_partido_volta_a_ser_um_e_hora_vira_5H45():
    out = lr.juntar_tokens(P("às", "5", ",45,", "da", "manhã"))
    assert [p.texto for p in out] == ["às", "5H45,", "da", "manhã"]
    assert out[1].inicio == 0.3 and out[1].fim == 0.85 and out[1].prob == pytest.approx(0.7)   # junta tempo; prob mínima
    assert [p.texto for p in lr.juntar_tokens(P("acorda", "5:45", "todo", "dia"))] == ["acorda", "5H45", "todo", "dia"]
    assert [p.texto for p in lr.juntar_tokens(P("às", "5:", "45"))] == ["às", "5H45"]
    assert [p.texto for p in lr.juntar_tokens(P("tá", "bom", "?"))] == ["tá", "bom?"]
    assert [p.texto for p in lr.juntar_tokens(P("subiu", "5", "%"))] == ["subiu", "5%"]


def test_d4_preco_e_numero_comum_nao_viram_hora():
    assert [p.texto for p in lr.juntar_tokens(P("custa", "5,45"))] == ["custa", "5,45"]
    assert [p.texto for p in lr.juntar_tokens(P("R$", "5", ",45"))] == ["R$", "5,45"]
    assert [p.texto for p in lr.juntar_tokens(P("5", ",45", "reais"))] == ["5,45", "reais"]
    assert [p.texto for p in lr.juntar_tokens(P("às", "nove", "em", "ponto."))] == ["às", "nove", "em", "ponto."]
    assert [p.texto for p in lr.juntar_tokens(P("1.", "000", "pessoas"))] == ["1.000", "pessoas"]
    assert [p.texto for p in lr.juntar_tokens(P("(", "risos", ")"))] == ["(", "risos)"]


def test_d4_transcrever_ja_entrega_o_numero_junto():
    ModeloFalso.chamadas = []
    ModeloFalso.gabarito = [{"inicio": 0.1, "fim": 0.3, "texto": "às"}, {"inicio": 0.3, "fim": 0.5, "texto": "5"},
                            {"inicio": 0.5, "fim": 0.8, "texto": ",45,"}]
    ps = lr.transcrever(Path("x.mp4"), carregar=ModeloFalso, decodificar=lambda v: np.zeros(160, dtype=np.float32))
    assert [p.texto for p in ps] == ["às", "5H45,"]


# --- D5. pasta local chamada "medium" ou "small" era lida como modelo

def test_d5_nome_de_modelo_nao_colide_com_pasta_local(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "medium").mkdir()          # uma pasta qualquer com o nome do modelo, sem model.bin
    (tmp_path / "small").mkdir()
    assert lr.resolver_modelo("medium") == "Systran/faster-whisper-medium"
    assert lr.resolver_modelo("small") == "Systran/faster-whisper-small"
    meu = tmp_path / "meu-modelo"
    meu.mkdir()
    (meu / "model.bin").write_bytes(b"x")
    assert lr.resolver_modelo(str(meu)) == str(meu)        # pasta de modelo de verdade passa como está
    ModeloFalso.chamadas, ModeloFalso.gabarito = [], []
    lr.transcrever(Path("x.mp4"), modelo="medium", carregar=ModeloFalso, decodificar=lambda v: np.zeros(160, dtype=np.float32))
    assert ModeloFalso.chamadas[0][1] == "Systran/faster-whisper-medium"


# --- D6. com base 0,35 a legenda grande ficava travada em ~59% da altura

def test_d6_legenda_desce_para_62_por_cento_no_organico():
    e = lr.Estilo()
    assert (e.topo, e.base, e.lados, e.direita_extra) == (0.14, 0.25, 0.06, 0.06)
    y = int(re.search(r"\\pos\(\d+,(\d+)\)", lr.gerar_ass([frase("oi gente")], 1080, 1920, e)).group(1))
    assert y == round(0.62 * 1920)
    anuncio = lr.Estilo(**lr.ZONAS["anuncio"])                  # 35% embaixo (orientação da Meta para anúncio)
    y = int(re.search(r"\\pos\(\d+,(\d+)\)", lr.gerar_ass([frase("oi gente")], 1080, 1920, anuncio)).group(1))
    assert y == round(1920 * 0.65 - 111)


# --- D7. palavra de duração zero (ou com o mesmo início da seguinte) nunca acendia

def test_d7_toda_palavra_acende_mesmo_com_duracao_zero():
    e = lr.Estilo()
    g = [lr.Palavra(1.00, 1.30, "o"), lr.Palavra(1.30, 1.30, "que"), lr.Palavra(1.30, 1.60, "que"),
         lr.Palavra(1.60, 1.60, "é?")]
    ass = lr.gerar_ass([g[:2], g[2:]], 1080, 1920, e)
    evs = eventos_de(ass)
    assert len(evs) == 4
    for i, ev in enumerate(evs):
        assert ev.count("\\c&H004DE1FF") == 1
        ini, fim = ev.split(",")[1:3]
        assert ini < fim

    def t(s):
        h, m, r = s.split(":")
        return int(h) * 3600 + int(m) * 60 + float(r)
    tempos = [(t(ev.split(",")[1]), t(ev.split(",")[2])) for ev in evs]
    assert all(tempos[k][1] <= tempos[k + 1][0] + 1e-9 for k in range(len(tempos) - 1))


def test_d7_tempos_destaque_reparte_quando_nao_cabe():
    g = [lr.Palavra(2.0, 2.0, "a"), lr.Palavra(2.0, 2.0, "b"), lr.Palavra(2.0, 2.0, "c")]
    ts = lr.tempos_destaque(g, 2.06, minimo=0.08)
    assert all(b > a for a, b in ts) and ts[0][0] == 2.0 and ts[-1][1] == pytest.approx(2.06)


# =========================================================================== v2: os ajustes validados no PC

def test_padroes_validados_no_pc():
    e = lr.Estilo()
    assert (e.fonte, e.cor, e.destaque, e.contorno) == ("Arial Black", "#FFFFFF", "#FFE14D", "#000000")
    assert (e.min_palavras, e.max_palavras, e.max_caracteres) == (2, 3, 16)
    assert e.largura_letra == 0.50 and e.posicao == 0.62 and lr.tamanho_px(1920, e) == 111
    a = lr._parser().parse_args(["video.mp4"])
    assert a.modelo == "medium" and a.palavras_por_bloco == "2-3" and a.passo == "queimar"
    blocos = lr.agrupar(frase("Quem chegar atrasado apresenta o relatório do trimestre inteiro."), e)
    assert all(len(b) <= 3 and (len(" ".join(p.texto for p in b)) <= 16 or len(b) == 1) for b in blocos)


def test_termos_vao_no_prompt_e_nos_hotwords_com_a_dica_coloquial():
    ModeloFalso.chamadas, ModeloFalso.gabarito = [], []
    lr.transcrever(Path("x.mp4"), termos=["Cheetos", "Miojo", " pappardelle "], carregar=ModeloFalso,
                   decodificar=lambda v: np.zeros(160, dtype=np.float32))
    kw = ModeloFalso.chamadas[1][2]
    assert "Cheetos, Miojo, pappardelle" in kw["initial_prompt"] and "tá, tô, pra" in kw["initial_prompt"]
    assert kw["hotwords"] == "Cheetos, Miojo, pappardelle"
    ModeloFalso.chamadas = []
    lr.transcrever(Path("x.mp4"), carregar=ModeloFalso, decodificar=lambda v: np.zeros(160, dtype=np.float32))
    kw = ModeloFalso.chamadas[1][2]
    assert kw["hotwords"] is None and "tá, tô, pra" in kw["initial_prompt"]
    assert lr.ler_termos("Cheetos, Miojo;pappardelle") == ["Cheetos", "Miojo", "pappardelle"]


# =========================================================================== v2: revisão obrigatória em dois passos

GAB_REV = [{"inicio": 0.10, "fim": 0.30, "texto": "Comprei", "prob": 0.95},
           {"inicio": 0.32, "fim": 0.55, "texto": "um", "prob": 0.91},
           {"inicio": 0.57, "fim": 0.90, "texto": "chitos", "prob": 0.31},
           {"inicio": 0.92, "fim": 1.20, "texto": "no", "prob": 0.88},
           {"inicio": 1.22, "fim": 1.60, "texto": "mercado.", "prob": 0.49}]


class ModeloComProb(ModeloFalso):
    def transcribe(self, caminho, **kw):
        ModeloFalso.chamadas.append(("transcribe", caminho, kw))
        ws = [SimpleNamespace(start=p["inicio"], end=p["fim"], word=" " + p["texto"], probability=p["prob"]) for p in GAB_REV]
        return iter([SimpleNamespace(words=ws)]), SimpleNamespace(language="pt")


@pytest.mark.skipif(not TEM_FFMPEG, reason="precisa de ffmpeg")
def test_revisar_grava_o_json_e_lista_so_as_palavras_duvidosas(tmp_path: Path):
    video = video_simples(tmp_path / "bruto.mp4")
    ModeloFalso.chamadas = []
    rev = lr.main(["revisar", str(video), "--termos", "Cheetos"], carregar=ModeloComProb)
    assert rev == tmp_path / "bruto.revisar.txt"
    dados = json.loads((tmp_path / "bruto.palavras.json").read_text(encoding="utf-8"))
    assert dados["revisado"] is False and dados["termos"] == ["Cheetos"] and len(dados["palavras"]) == 5
    txt = rev.read_text(encoding="utf-8")
    assert "2 de 5 palavras" in txt
    assert "00:00.57" in txt and "⟦chitos⟧" in txt and "Comprei um ⟦chitos⟧ no mercado." in txt
    assert "⟦mercado.⟧" in txt and "⟦Comprei⟧" not in txt and "⟦no⟧" not in txt


@pytest.mark.skipif(not TEM_FFMPEG, reason="precisa de ffmpeg")
def test_queimar_so_com_o_json_revisado(tmp_path: Path, capsys):
    video = video_simples(tmp_path / "bruto.mp4")
    ModeloFalso.chamadas = []
    # sem palavras.json, "queimar" faz a revisão e PARA
    with pytest.raises(SystemExit, match="Revisão primeiro"):
        lr.main(["queimar", str(video), "--so-ass", "--sem-aviso-legenda"], carregar=ModeloComProb)
    assert (tmp_path / "bruto.revisar.txt").exists()
    # com o json ainda não revisado, recusa
    with pytest.raises(SystemExit, match="ainda não foi revisado"):
        lr.main(["queimar", str(video), "--so-ass"], carregar=ModeloComProb)
    # --sem-revisar queima e avisa
    lr.main(["queimar", str(video), "--so-ass", "--sem-revisar"], carregar=ModeloComProb)
    assert "SEM revisão" in capsys.readouterr().err
    # corrigir a palavra conta como revisão
    j = tmp_path / "bruto.palavras.json"
    dados = json.loads(j.read_text(encoding="utf-8"))
    dados["palavras"][2]["texto"] = "Cheetos"
    j.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    ass = lr.main(["queimar", str(video), "--so-ass"], carregar=ModeloComProb)
    assert "CHEETOS" in ass.read_text(encoding="utf-8")
    # e "revisado": true também (sem mexer em nada)
    dados = json.loads(j.read_text(encoding="utf-8"))
    dados["palavras"][2]["texto"] = "chitos"
    dados["revisado"] = True
    j.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    assert lr.main(["queimar", str(video), "--so-ass"], carregar=ModeloComProb).exists()


def test_palavras_json_da_v1_continua_legivel(tmp_path: Path):
    j = tmp_path / "v1.palavras.json"
    j.write_text(json.dumps([{"inicio": 0.1, "fim": 0.2, "texto": "oi", "prob": 0.9}]), encoding="utf-8")
    lido = lr.ler_json_palavras(j)
    assert lido["v1"] and not lido["revisado"] and [p.texto for p in lido["palavras"]] == ["oi"]


# =========================================================================== v2: aviso de legenda já queimada

@pytest.mark.skipif(not TEM_FFMPEG, reason="precisa de ffmpeg")
def test_aviso_quando_o_video_ja_tem_legenda_queimada(tmp_path: Path, capsys):
    limpo = video_simples(tmp_path / "limpo.mp4", dur=3.0)
    sujo = video_simples(tmp_path / "sujo.mp4", dur=3.0, texto="ESSA REUNIÃO|PODIA SER|UM E-MAIL|SÉRIO")
    r_limpo, r_sujo = lr.detectar_legenda_queimada(limpo), lr.detectar_legenda_queimada(sujo)
    assert r_limpo["aviso"] is False and r_limpo["quadros_com_texto"] == 0
    assert r_sujo["aviso"] is True and 0.6 <= r_sujo["faixa"] <= 0.8
    # o revisar avisa, e não bloqueia
    ModeloFalso.chamadas = []
    lr.main(["revisar", str(sujo)], carregar=ModeloComProb)
    assert "parece já ter legenda queimada" in capsys.readouterr().err
    assert (tmp_path / "sujo.palavras.json").exists()


@pytest.mark.skipif(not TEM_FFMPEG, reason="precisa de ffmpeg")
def test_a_propria_saida_legendada_acusa_legenda(tmp_path: Path):
    video = gerar_teste.gerar_video(tmp_path / "teste.mp4", largura=540, altura=960)
    ModeloFalso.chamadas, ModeloFalso.gabarito = [], json.loads(video.with_suffix(".gabarito.json").read_text(encoding="utf-8"))
    saida = lr.main([str(video), "--fonte", "DejaVu Sans", "--sem-revisar", "--sem-aviso-legenda"], carregar=ModeloFalso)
    assert lr.detectar_legenda_queimada(saida)["aviso"] is True
    assert lr.detectar_legenda_queimada(video)["aviso"] is False
