#!/usr/bin/env python3
"""
Gera um vídeo de teste SINTÉTICO 9:16 com voz sintética (espeak-ng, pt-br) e o gabarito com o tempo
exato de cada palavra, para testar o legenda_reels.py sem gravar nada. Também compara uma
transcrição do faster-whisper com o gabarito (acerto de palavras e erro médio de tempo).

Como o gabarito é exato: cada palavra é sintetizada sozinha, o silêncio da ponta é cortado e as
palavras são coladas com pausas conhecidas (mais longas depois de vírgula e de ponto). A voz fica
robótica, mas o tempo de cada palavra é conhecido até a amostra.

Uso:
  python gerar_teste.py --saida teste.mp4                  # teste.mp4 + teste.gabarito.json
  python gerar_teste.py --saida teste.mp4 --largura 540 --altura 960
  python legenda_reels.py teste.mp4                         # transcreve com o faster-whisper e legenda
  python gerar_teste.py --comparar teste.palavras.json teste.gabarito.json
Precisa de ffmpeg e espeak-ng no PATH (no Windows, o instalador .msi do espeak-ng no GitHub do projeto).
"""
from __future__ import annotations

import argparse
import array
import difflib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import wave
from pathlib import Path

TEXTO_PADRAO = ("Bom dia, pessoal. A reunião de hoje começa às nove em ponto. "
                "Quem chegar atrasado apresenta o relatório do trimestre inteiro.")
PAUSA_PALAVRA, PAUSA_VIRGULA, PAUSA_PONTO = 0.08, 0.30, 0.55
INICIO, FINAL = 0.50, 0.80
LIMIAR = 400   # amplitude (16 bits) abaixo disso conta como silêncio


def _amostras(caminho: Path) -> tuple[array.array, int]:
    with wave.open(str(caminho)) as w:
        assert w.getsampwidth() == 2 and w.getnchannels() == 1, "espeak-ng devolve PCM 16 bits mono"
        dados = array.array("h", w.readframes(w.getnframes()))
        return dados, w.getframerate()


def _cortar(dados: array.array, taxa: int) -> array.array:
    margem = int(0.005 * taxa)
    ini = next((i for i, v in enumerate(dados) if abs(v) > LIMIAR), 0)
    fim = next((i for i in range(len(dados) - 1, -1, -1) if abs(dados[i]) > LIMIAR), len(dados) - 1)
    return dados[max(0, ini - margem): min(len(dados), fim + margem + 1)]


def sintetizar(texto: str, wav: Path, voz: str = "pt-br", velocidade: int = 165) -> list[dict]:
    """Grava o WAV e devolve o gabarito [{inicio, fim, texto}] (segundos)."""
    if shutil.which("espeak-ng") is None:
        raise SystemExit("espeak-ng não está no PATH.")
    palavras = texto.split()
    trilha = array.array("h")
    taxa = None
    gabarito = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, palavra in enumerate(palavras):
            falada = re.sub(r"[^\w'-]", "", palavra)
            destino = Path(tmp) / f"p{i}.wav"
            subprocess.run(["espeak-ng", "-v", voz, "-s", str(velocidade), "-w", str(destino), falada], check=True)
            dados, taxa_p = _amostras(destino)
            taxa = taxa or taxa_p
            if not trilha:
                trilha.extend([0] * int(INICIO * taxa))
            dados = _cortar(dados, taxa)
            inicio = len(trilha) / taxa
            trilha.extend(dados)
            gabarito.append({"inicio": round(inicio, 3), "fim": round(len(trilha) / taxa, 3), "texto": palavra, "prob": None})
            pausa = PAUSA_PONTO if re.search(r"[.!?]$", palavra) else PAUSA_VIRGULA if re.search(r"[,;:]$", palavra) else PAUSA_PALAVRA
            trilha.extend([0] * int(pausa * taxa))
        trilha.extend([0] * int(FINAL * taxa))
    with wave.open(str(wav), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(taxa)
        w.writeframes(trilha.tobytes())
    return gabarito


def _fonte_rotulo() -> str | None:
    if shutil.which("fc-match"):
        r = subprocess.run(["fc-match", "-f", "%{file}", "DejaVu Sans:bold"], capture_output=True, text=True)
        if r.returncode == 0 and Path(r.stdout).exists():
            return r.stdout
    for p in ("C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf"):
        if Path(p).exists():
            return p
    return None


def gerar_video(saida: Path, texto: str = TEXTO_PADRAO, largura: int = 1080, altura: int = 1920) -> Path:
    """saida.mp4 (fundo em degradê animado + voz sintética) e saida.gabarito.json."""
    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg não está no PATH.")
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "voz.wav"
        gabarito = sintetizar(texto, wav)
        with wave.open(str(wav)) as w:
            duracao = w.getnframes() / w.getframerate()
        fundo = (f"gradients=s={largura}x{altura}:r=30:d={duracao:.3f}:speed=0.02:"
                 f"c0=0x173042:c1=0x2f6170:c2=0x24344a:nb_colors=3:seed=7")
        fonte = _fonte_rotulo()
        rotulo = ""
        if fonte:
            tam = round(altura * 0.022)
            ff = fonte.replace("\\", "/").replace(":", "\\:")
            rotulo = (f",drawtext=fontfile='{ff}':text='VIDEO DE TESTE SINTETICO · voz espeak-ng':"
                      f"fontcolor=white@0.75:fontsize={tam}:x=(w-text_w)/2:y=h*0.06")
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", fundo, "-i", str(wav),
                        "-filter_complex", f"[0:v]format=yuv420p{rotulo}[v]", "-map", "[v]", "-map", "1:a",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "128k",
                        "-shortest", str(saida)], check=True)
    saida.with_suffix(".gabarito.json").write_text(json.dumps(gabarito, ensure_ascii=False, indent=1), encoding="utf-8")
    return saida


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^\w]", "", t)


def comparar(transcricao: list[dict], gabarito: list[dict]) -> dict:
    """Alinha as palavras e devolve o acerto e o erro médio de início e de fim (s)."""
    a = [_norm(p["texto"]) for p in transcricao]
    b = [_norm(p["texto"]) for p in gabarito]
    pares = []
    for bloco in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        pares += [(transcricao[bloco.a + k], gabarito[bloco.b + k]) for k in range(bloco.size)]
    if not pares:
        return {"acerto": 0.0, "erro_inicio_s": None, "erro_fim_s": None, "palavras_gabarito": len(b)}
    return {"acerto": round(len(pares) / max(1, len(b)), 3),
            "erro_inicio_s": round(sum(abs(t["inicio"] - g["inicio"]) for t, g in pares) / len(pares), 3),
            "erro_fim_s": round(sum(abs(t["fim"] - g["fim"]) for t, g in pares) / len(pares), 3),
            "palavras_gabarito": len(b)}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--saida", type=Path, default=Path("teste.mp4"))
    ap.add_argument("--texto", default=TEXTO_PADRAO)
    ap.add_argument("--largura", type=int, default=1080)
    ap.add_argument("--altura", type=int, default=1920)
    ap.add_argument("--comparar", nargs=2, type=Path, metavar=("PALAVRAS", "GABARITO"))
    a = ap.parse_args(argv)
    if a.comparar:
        t, g = (json.loads(p.read_text(encoding="utf-8")) for p in a.comparar)
        print(json.dumps(comparar(t, g), ensure_ascii=False))
        return
    gerar_video(a.saida, a.texto, a.largura, a.altura)
    print(f"ok: {a.saida} e {a.saida.with_suffix('.gabarito.json')}", file=sys.stderr)


if __name__ == "__main__":
    main()
