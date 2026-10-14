#!/usr/bin/env python3
"""
Fred · legenda palavra a palavra (estilo reels), local e grátis.

vídeo vertical 9:16 em português
  -> faster-whisper (modelo small, int8, CPU) com o tempo de cada palavra
  -> <video>.palavras.json (dá para corrigir uma palavra à mão e rodar de novo)
  -> legenda .ass: 2 a 4 palavras por vez, a palavra falada destacada (cor e leve zoom), fonte
     grande com contorno e sombra, dentro da área segura do Instagram
  -> ffmpeg queima a legenda e devolve o mesmo vídeo (mesmo tamanho, mesmo áudio).

Uso:
  pip install faster-whisper            # e o ffmpeg no PATH (no Windows: build do gyan.dev)
  python legenda_reels.py video.mp4                                  # -> video_legendado.mp4
  python legenda_reels.py video.mp4 --sem-legenda 0:12-0:15,1:02-1:05.5
  python legenda_reels.py video.mp4 --tamanho 96 --cor "#FFFFFF" --destaque "#FFE14D" --posicao 0.58
  python legenda_reels.py video.mp4 --palavras video.palavras.json    # transcrição já corrigida
  python legenda_reels.py video.mp4 --so-ass                           # só gera o .ass (abre no Aegisub)
  python legenda_reels.py video.mp4 --prints 3 --guia                  # 3 PNG de quadros legendados, com a área segura

Primeira vez: o faster-whisper baixa o modelo "small" (~480 MB) do HuggingFace e guarda no cache;
depois roda sem internet. Nenhum serviço pago.

Área segura padrão (fração do quadro, ajustável): 14% em cima, 35% embaixo, 6% nas laterais e
mais 6% à direita por causa dos botões do Reels. A legenda fica centrada em --posicao (0,58 da
altura), dentro dessa área.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable

# --------------------------------------------------------------------------- dados


@dataclass
class Palavra:
    inicio: float
    fim: float
    texto: str
    prob: float | None = None


@dataclass
class Estilo:
    fonte: str = "Arial Black"
    tamanho: int | None = None          # px no quadro; padrão = 4,5% da altura
    cor: str = "#FFFFFF"
    destaque: str = "#FFE14D"
    contorno: str = "#000000"
    posicao: float = 0.58               # centro vertical da legenda, fração da altura
    caixa_alta: bool = True
    zoom_destaque: int = 112            # % de escala da palavra falada (100 = sem zoom)
    topo: float = 0.14                  # área segura
    base: float = 0.35
    lados: float = 0.06
    direita_extra: float = 0.06
    min_palavras: int = 2
    max_palavras: int = 4
    max_caracteres: int = 22
    pausa_quebra: float = 0.6           # pausa (s) que sempre começa um bloco novo
    segurar: float = 0.25               # quanto o último bloco fica na tela depois da última palavra
    largura_letra: float = 0.72         # largura média de uma letra maiúscula, em fração do tamanho da fonte


RX_FIM_FORTE = re.compile(r"[.!?…]+[\"'”»)]*$")
RX_FIM_FRACO = re.compile(r"[,;:]+[\"'”»)]*$")

# --------------------------------------------------------------------------- transcrição


def transcrever(video: Path, modelo: str = "small", idioma: str = "pt", dispositivo: str = "cpu",
                tipo: str = "int8", pasta_modelo: str | None = None,
                carregar: Callable | None = None) -> list[Palavra]:
    """faster-whisper com word_timestamps. `carregar` existe só para o teste trocar o modelo."""
    if carregar is None:
        from faster_whisper import WhisperModel
        carregar = WhisperModel
    m = carregar(modelo, device=dispositivo, compute_type=tipo, download_root=pasta_modelo)
    segmentos, _info = m.transcribe(str(video), language=idioma, word_timestamps=True, vad_filter=True,
                                    beam_size=5, condition_on_previous_text=False)
    palavras = []
    for s in segmentos:
        for w in getattr(s, "words", None) or []:
            texto = (w.word or "").strip()
            if texto:
                palavras.append(Palavra(round(float(w.start), 3), round(float(w.end), 3), texto,
                                        round(float(w.probability), 3) if w.probability is not None else None))
    return palavras


def salvar_palavras(palavras: list[Palavra], caminho: Path) -> None:
    caminho.write_text(json.dumps([asdict(p) for p in palavras], ensure_ascii=False, indent=1), encoding="utf-8")


def ler_palavras(caminho: Path) -> list[Palavra]:
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    return [Palavra(float(d["inicio"]), float(d["fim"]), str(d["texto"]), d.get("prob")) for d in dados]


# --------------------------------------------------------------------------- trechos sem legenda


def segundos(t: str) -> float:
    partes = t.strip().replace(",", ".").split(":")
    if not 1 <= len(partes) <= 3 or not all(re.fullmatch(r"\d+(\.\d+)?", p) for p in partes):
        raise ValueError(f"tempo inválido: {t!r} (use 12.5, 0:12 ou 1:02:03)")
    total = 0.0
    for p in partes:
        total = total * 60 + float(p)
    return total


def ler_trechos(texto: str | None) -> list[tuple[float, float]]:
    """'0:12-0:15, 1:02-1:05.5' -> [(12, 15), (62, 65.5)]."""
    trechos = []
    for item in re.split(r"[\s,;]+", texto or ""):
        if not item:
            continue
        if item.count("-") != 1:
            raise ValueError(f"trecho inválido: {item!r} (use início-fim, ex.: 0:12-0:15)")
        a, b = (segundos(x) for x in item.split("-"))
        if b <= a:
            raise ValueError(f"trecho com fim antes do início: {item!r}")
        trechos.append((a, b))
    return sorted(trechos)


def tirar_trechos(palavras: list[Palavra], trechos: list[tuple[float, float]]) -> list[Palavra]:
    """Some com a palavra que encosta em qualquer trecho marcado."""
    return [p for p in palavras if not any(p.inicio < b and p.fim > a for a, b in trechos)]


# --------------------------------------------------------------------------- blocos de 2 a 4 palavras


PALAVRAS_FRACAS = set("""a o as os um uma uns umas de do da dos das em no na nos nas ao aos à às e ou que
se por pelo pela para pra com sem sob sobre entre até mas nem meu minha seu sua the of to and""".split())


def _custo(bloco: list[Palavra], depois: Palavra | None, e: Estilo, frase_curta: bool) -> float:
    """Custo de um bloco: o ideal é 3 palavras; quebrar em vírgula ou numa pausa é bom; terminar
    em artigo ou preposição ("de", "às", "em"...) no meio da frase é ruim; passar do limite de
    caracteres é proibido (a não ser uma palavra sozinha que já não cabe)."""
    n = len(bloco)
    texto = " ".join(p.texto for p in bloco)
    if n > e.max_palavras or (len(texto) > e.max_caracteres and n > 1):
        return float("inf")
    custo = {1: 0.0 if frase_curta else 4.0, 2: 0.6, 3: 0.0, 4: 0.4}.get(n, 1.0 + 0.4 * abs(n - 3))
    if n < e.min_palavras and not frase_curta:
        custo += 2.0
    if depois is not None:
        ultima = bloco[-1].texto
        if RX_FIM_FRACO.search(ultima):
            custo -= 1.5
        elif depois.inicio - bloco[-1].fim > 0.25:
            custo -= 1.0
        elif re.sub(r"[^\w]", "", ultima.lower()) in PALAVRAS_FRACAS:
            custo += 2.0
    return custo


def _frases(palavras: list[Palavra], e: Estilo) -> list[list[Palavra]]:
    """Corta em frase depois de ponto final, exclamação, interrogação ou reticências e em pausa
    maior que pausa_quebra."""
    frases: list[list[Palavra]] = []
    atual: list[Palavra] = []
    for p in palavras:
        if atual and (RX_FIM_FORTE.search(atual[-1].texto) or p.inicio - atual[-1].fim > e.pausa_quebra):
            frases.append(atual)
            atual = []
        atual.append(p)
    if atual:
        frases.append(atual)
    return frases


def agrupar(palavras: list[Palavra], e: Estilo) -> list[list[Palavra]]:
    """Blocos de min_palavras a max_palavras palavras. Cada frase é dividida pela partição de menor
    custo (programação dinâmica), então "a reunião de hoje começa às nove em ponto" vira três blocos
    equilibrados em vez de 4 + 4 + 1."""
    grupos: list[list[Palavra]] = []
    for frase in _frases(palavras, e):
        n = len(frase)
        curta = n < e.min_palavras
        melhor = [0.0] + [float("inf")] * n
        corte = [0] * (n + 1)
        for i in range(1, n + 1):
            for j in range(max(0, i - e.max_palavras), i):
                c = melhor[j] + _custo(frase[j:i], frase[i] if i < n else None, e, curta)
                if c < melhor[i]:
                    melhor[i], corte[i] = c, j
        if melhor[n] == float("inf"):     # palavra enorme: cai para um bloco por palavra
            grupos += [[p] for p in frase]
            continue
        blocos, i = [], n
        while i > 0:
            blocos.append(frase[corte[i]:i])
            i = corte[i]
        grupos += reversed(blocos)
    return grupos


# --------------------------------------------------------------------------- .ass


def cor_ass(hexa: str, alfa: int = 0) -> str:
    """'#RRGGBB' -> '&HAABBGGRR' (o ASS guarda azul, verde, vermelho; alfa 0 = opaco)."""
    h = hexa.strip().lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", h):
        raise ValueError(f"cor inválida: {hexa!r} (use #RRGGBB)")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H{alfa:02X}{b}{g}{r}".upper()


def tempo_ass(s: float) -> str:
    cs = max(0, int(round(s * 100)))
    h, resto = divmod(cs, 360000)
    m, resto = divmod(resto, 6000)
    seg, cent = divmod(resto, 100)
    return f"{h}:{m:02d}:{seg:02d}.{cent:02d}"


def limpar_texto(t: str, caixa_alta: bool) -> str:
    t = t.replace("\\", "").replace("{", "(").replace("}", ")").strip()
    return t.upper() if caixa_alta else t


def quebrar(textos: list[str], max_linha: int) -> int | None:
    """Índice da palavra que começa a 2ª linha, ou None se o bloco cabe numa linha. A quebra é
    decidida aqui (e não pelo libass) para o bloco não mudar de forma quando o destaque com zoom
    passa de uma palavra para outra. Escolhe a divisão mais equilibrada, com a 1ª linha maior ou igual."""
    if len(textos) < 2 or len(" ".join(textos)) <= max_linha:
        return None
    melhor = None
    for k in range(1, len(textos)):
        a, b = len(" ".join(textos[:k])), len(" ".join(textos[k:]))
        nota = (max(a, b), 0 if a >= b else 1)
        if melhor is None or nota < melhor[0]:
            melhor = (nota, k)
    return melhor[1]


def gerar_ass(grupos: list[list[Palavra]], largura: int, altura: int, e: Estilo) -> str:
    tam = e.tamanho or round(altura * 0.045)
    contorno = max(2, round(tam * 0.08))
    sombra = max(1, round(tam * 0.05))
    margem_e = round(largura * e.lados)
    margem_d = round(largura * (e.lados + e.direita_extra))
    x = round((margem_e + (largura - margem_d)) / 2)
    y_min = altura * e.topo + tam
    y_max = altura * (1 - e.base) - tam
    y = round(min(max(altura * e.posicao, y_min), y_max))
    cor, destaque = cor_ass(e.cor), cor_ass(e.destaque)
    max_linha = max(6, int((largura - margem_e - margem_d) / (e.largura_letra * tam)))
    linhas = [
        "[Script Info]",
        "; Gerado por legenda_reels.py",
        "ScriptType: v4.00+",
        f"PlayResX: {largura}",
        f"PlayResY: {altura}",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "YCbCr Matrix: TV.709",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
        "MarginR, MarginV, Encoding",
        f"Style: Reels,{e.fonte},{tam},{cor},{destaque},{cor_ass(e.contorno)},{cor_ass('#000000', 0x60)},"
        f"-1,0,0,0,100,100,0,0,1,{contorno},{sombra},5,{margem_e},{margem_d},0,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    zoom = "" if e.zoom_destaque == 100 else f"\\fscx{e.zoom_destaque}\\fscy{e.zoom_destaque}"
    for gi, g in enumerate(grupos):
        proximo = grupos[gi + 1][0].inicio if gi + 1 < len(grupos) else None
        fim_bloco = g[-1].fim + e.segurar          # segura o bloco um pouco, sem invadir o próximo
        if proximo is not None:
            fim_bloco = min(fim_bloco, proximo)
        textos = [limpar_texto(p.texto, e.caixa_alta) for p in g]
        segunda = quebrar(textos, max_linha)
        for i, p in enumerate(g):
            ini = p.inicio
            fim = g[i + 1].inicio if i + 1 < len(g) else fim_bloco
            if fim - ini < 0.01:
                continue
            partes = [(f"{{\\c{destaque}{zoom}}}{t}{{\\r}}" if j == i else t) for j, t in enumerate(textos)]
            texto = " ".join(partes) if segunda is None else " ".join(partes[:segunda]) + "\\N" + " ".join(partes[segunda:])
            linhas.append(f"Dialogue: 0,{tempo_ass(ini)},{tempo_ass(fim)},Reels,,0,0,0,,"
                          f"{{\\an5\\pos({x},{y})}}" + texto)
    return "\n".join(linhas) + "\n"


# --------------------------------------------------------------------------- ffmpeg


def exigir_ffmpeg() -> None:
    for prog in ("ffmpeg", "ffprobe"):
        if shutil.which(prog) is None:
            raise SystemExit(f"{prog} não está no PATH. No Windows, baixe o build do gyan.dev e ponha a pasta bin no PATH.")


def sondar(video: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height:stream_side_data=rotation:stream_tags=rotate:format=duration",
                        "-of", "json", str(video)], capture_output=True, text=True, check=True)
    d = json.loads(r.stdout)
    s = d["streams"][0]
    largura, altura = int(s["width"]), int(s["height"])
    rot = 0
    for sd in s.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(float(sd["rotation"]))
    rot = rot or int(float((s.get("tags") or {}).get("rotate", 0) or 0))
    if abs(rot) % 180 == 90:          # celular grava deitado e marca a rotação; o ffmpeg gira ao filtrar
        largura, altura = altura, largura
    return {"largura": largura, "altura": altura, "duracao": float(d.get("format", {}).get("duration", 0) or 0)}


def escapar_filtro(caminho: str) -> str:
    return caminho.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def queimar(video: Path, ass: Path, saida: Path, crf: int = 18, preset: str = "medium",
            pasta_fontes: Path | None = None, guia: Estilo | None = None) -> None:
    copia = ass.parent / "_legenda_reels_queima.ass"   # nome sem espaço nem acento para o filtro do ffmpeg
    shutil.copyfile(ass, copia)
    filtro = f"subtitles={copia.name}"
    if pasta_fontes:
        filtro += f":fontsdir={escapar_filtro(str(pasta_fontes.resolve()))}"
    if guia is not None:   # caixas translúcidas mostrando o que fica fora da área segura (só para conferir)
        g = guia
        filtro = (f"drawbox=x=0:y=0:w=iw:h=ih*{g.topo}:color=red@0.10:t=fill,"
                  f"drawbox=x=0:y=ih*{1 - g.base}:w=iw:h=ih*{g.base}:color=red@0.10:t=fill,"
                  f"drawbox=x=iw*{g.lados}:y=ih*{g.topo}:w=iw*{1 - 2 * g.lados - g.direita_extra}:"
                  f"h=ih*{1 - g.topo - g.base}:color=white@0.55:t=4,"
                  + filtro)
    base = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(video.resolve()), "-vf", filtro,
            "-c:v", "libx264", "-crf", str(crf), "-preset", preset, "-pix_fmt", "yuv420p"]
    fim = ["-movflags", "+faststart", str(saida.resolve())]
    try:
        r = subprocess.run(base + ["-c:a", "copy"] + fim, cwd=ass.parent, capture_output=True, text=True)
        if r.returncode != 0:   # áudio que o MP4 não aceita em cópia: recodifica em AAC
            r = subprocess.run(base + ["-c:a", "aac", "-b:a", "192k"] + fim, cwd=ass.parent, capture_output=True, text=True)
    finally:
        copia.unlink(missing_ok=True)
    if r.returncode != 0:
        raise SystemExit(f"ffmpeg falhou:\n{r.stderr[-2000:]}")


def tirar_prints(saida: Path, grupos: list[list[Palavra]], n: int, pasta: Path) -> list[Path]:
    """n quadros do vídeo legendado, espalhados pelo vídeo, cada um no meio de uma palavra."""
    if not grupos or n <= 0:
        return []
    escolhidos = sorted({round(k * (len(grupos) - 1) / max(1, n - 1)) for k in range(n)}) if n > 1 else [0]
    arquivos = []
    for k, gi in enumerate(escolhidos, 1):
        g = grupos[gi]
        p = g[min(1, len(g) - 1)]
        t = (p.inicio + p.fim) / 2
        destino = pasta / f"{saida.stem}_print_{k}.png"
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", str(saida),
                        "-frames:v", "1", str(destino)], check=True)
        arquivos.append(destino)
    return arquivos


# --------------------------------------------------------------------------- CLI


def main(argv: Iterable[str] | None = None, carregar: Callable | None = None) -> Path:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", type=Path)
    ap.add_argument("-o", "--saida", type=Path, help="padrão: <video>_legendado.mp4")
    ap.add_argument("--palavras", type=Path, help="palavras.json já pronto (pula a transcrição)")
    ap.add_argument("--retranscrever", action="store_true", help="ignora o <video>.palavras.json salvo")
    ap.add_argument("--modelo", default="small", help="modelo do faster-whisper (padrão small)")
    ap.add_argument("--pasta-modelo", help="onde guardar ou achar o modelo baixado")
    ap.add_argument("--sem-legenda", default="", help="trechos sem legenda, ex.: 0:12-0:15,1:02-1:05.5")
    ap.add_argument("--fonte", default=Estilo.fonte, help='padrão "Arial Black" (vem no Windows)')
    ap.add_argument("--pasta-fontes", type=Path, help="pasta com .ttf/.otf para a fonte escolhida")
    ap.add_argument("--tamanho", type=int, help="tamanho da fonte em px (padrão: 4,5%% da altura)")
    ap.add_argument("--cor", default=Estilo.cor)
    ap.add_argument("--destaque", default=Estilo.destaque, help="cor da palavra falada")
    ap.add_argument("--posicao", type=float, default=Estilo.posicao, help="centro vertical, fração da altura (padrão 0,58)")
    ap.add_argument("--caixa", choices=["alta", "normal"], default="alta")
    ap.add_argument("--sem-zoom", action="store_true", help="palavra falada sem o zoom de 112%%")
    ap.add_argument("--palavras-por-bloco", default="2-4", help="mínimo-máximo, padrão 2-4")
    ap.add_argument("--so-ass", action="store_true", help="só gera o .ass, sem queimar")
    ap.add_argument("--prints", type=int, default=0, help="quantos PNG de quadros legendados salvar")
    ap.add_argument("--guia", action="store_true", help="pinta de vermelho o que fica fora da área segura (conferência)")
    ap.add_argument("--crf", type=int, default=18)
    a = ap.parse_args(list(argv) if argv is not None else None)

    exigir_ffmpeg()
    if not a.video.exists():
        raise SystemExit(f"Não achei {a.video}")
    mn, mx = (int(x) for x in a.palavras_por_bloco.split("-"))
    e = Estilo(fonte=a.fonte, tamanho=a.tamanho, cor=a.cor, destaque=a.destaque, posicao=a.posicao,
               caixa_alta=a.caixa == "alta", zoom_destaque=100 if a.sem_zoom else 112, min_palavras=mn, max_palavras=mx)
    info = sondar(a.video)
    if abs(info["largura"] / info["altura"] - 9 / 16) > 0.02:
        print(f"Aviso: o vídeo é {info['largura']}x{info['altura']}, não 9:16. A legenda sai mesmo assim.", file=sys.stderr)

    cache = a.video.with_suffix(".palavras.json")
    if a.palavras:
        palavras = ler_palavras(a.palavras)
    elif cache.exists() and not a.retranscrever:
        palavras = ler_palavras(cache)
        print(f"Usando a transcrição salva em {cache} (--retranscrever para refazer).", file=sys.stderr)
    else:
        print(f"Transcrevendo com faster-whisper ({a.modelo}, int8, CPU)...", file=sys.stderr)
        palavras = transcrever(a.video, a.modelo, pasta_modelo=a.pasta_modelo, carregar=carregar)
        salvar_palavras(palavras, cache)
    palavras = tirar_trechos(palavras, ler_trechos(a.sem_legenda))
    grupos = agrupar(palavras, e)

    saida = a.saida or a.video.with_name(f"{a.video.stem}_legendado.mp4")
    ass = saida.with_suffix(".ass")
    ass.write_text(gerar_ass(grupos, info["largura"], info["altura"], e), encoding="utf-8")
    print(f"{len(palavras)} palavras em {len(grupos)} blocos -> {ass}", file=sys.stderr)
    if a.so_ass:
        return ass
    queimar(a.video, ass, saida, a.crf, pasta_fontes=a.pasta_fontes, guia=e if a.guia else None)
    print(f"ok: {saida}", file=sys.stderr)
    for p in tirar_prints(saida, grupos, a.prints, saida.parent):
        print(f"print: {p}", file=sys.stderr)
    return saida


if __name__ == "__main__":
    main()
