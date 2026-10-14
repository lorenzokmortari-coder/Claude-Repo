#!/usr/bin/env python3
"""
Fred · legenda palavra a palavra (estilo reels), local e grátis. Versão 2 (14/10/2026).

Dois passos, com revisão obrigatória no meio:

  1. revisar   vídeo -> áudio pelo ffmpeg -> faster-whisper (medium, int8, CPU) com o tempo de cada palavra
               -> <video>.palavras.json + <video>.revisar.txt (só as palavras com prob < 0,5, com tempo e
               contexto, para corrigir à mão em 2 minutos)
  2. queimar   só com o palavras.json revisado -> blocos de 2 a 3 palavras -> legenda .ass -> ffmpeg (libass
               + x264) -> <video>_legendado.mp4

Uso:
  pip install faster-whisper "av<16"      # e o ffmpeg no PATH (no Windows: build do gyan.dev)
  python legenda_reels.py revisar video.mp4 --termos "Cheetos, Miojo, pappardelle"
  #   corrija o que estiver errado em video.palavras.json (campo "texto"), mude "revisado" para true
  python legenda_reels.py queimar video.mp4 --prints 3
  python legenda_reels.py queimar video.mp4 --prints 3 --guia       # PNG extras com a área segura pintada
  python legenda_reels.py queimar video.mp4 --sem-revisar           # pula a revisão (avisa)
  python legenda_reels.py queimar video.mp4 --zona anuncio          # área segura de anúncio (35% embaixo)

Sem "revisar" ou "queimar" na frente, vale "queimar" (que, sem palavras.json, faz o "revisar" e para).

O que mudou da v1 (cada item tem teste em test_legenda_reels.py):
  1. o áudio vem do ffmpeg e entra como array no faster-whisper: o PyAV 16+ quebrava o 1.2.1 ("metadata_errors");
  2. --guia não pinta mais o MP4: as caixas vão só em PNG à parte (<video>_legendado_guia_N.png);
  3. largura de letra 0,50 do Fontsize (o Fontsize do libass é ascendente + descendente) e espaço vale meia letra;
  4. número partido pelo Whisper volta a ser um ("5" ",45," -> "5H45,"), e hora vira "5H45";
  5. "medium" ou "small" viram o id do modelo no HuggingFace: uma pasta local com esse nome não é lida como modelo;
  6. a área segura de baixo é 25% no orgânico (35% só com --zona anuncio), e a legenda desce para 62% da altura;
  7. palavra de duração zero (ou com o mesmo início da seguinte) também acende.
  E os ajustes validados no PC em 14/10/2026: modelo medium, --termos no initial_prompt e nos hotwords (mais a
  dica de fala coloquial), tamanho 5,8% da altura, blocos de 2 a 3 palavras com até 16 caracteres, posição 0,62.

Área segura: a Meta publica, para anúncio em Reels, "deixe livres ~14% do topo, 35% da base e 6% de cada lado"
(ficha de anúncio de imagem do Reels no Ads Guide). Para Reels orgânico não achei orientação oficial; o padrão
orgânico (25% embaixo) é o que o teste do PC com vídeo real validou sem cobrir botões. A faixa extra de 6% à
direita (botões de curtir, comentar, compartilhar) não tem número oficial: NÃO VERIFICADO.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Callable, Iterable

# --------------------------------------------------------------------------- dados


@dataclass
class Palavra:
    inicio: float
    fim: float
    texto: str
    prob: float | None = None


# A área segura. "organico": o que o PC validou com vídeo real em 14/10/2026. "anuncio": a orientação da Meta para
# anúncio em Reels (14% em cima, 35% embaixo, 6% dos lados). A faixa extra à direita é da casa, sem número oficial.
ZONAS = {
    "organico": {"topo": 0.14, "base": 0.25, "lados": 0.06, "direita_extra": 0.06},
    "anuncio": {"topo": 0.14, "base": 0.35, "lados": 0.06, "direita_extra": 0.06},
}


@dataclass
class Estilo:
    fonte: str = "Arial Black"
    tamanho: int | None = None          # px no quadro; padrão = tamanho_rel da altura (111 px em 1920)
    tamanho_rel: float = 0.058
    cor: str = "#FFFFFF"
    destaque: str = "#FFE14D"
    contorno: str = "#000000"
    posicao: float = 0.62               # centro vertical da legenda, fração da altura
    caixa_alta: bool = True
    zoom_destaque: int = 112            # % de escala da palavra falada (100 = sem zoom)
    topo: float = 0.14                  # área segura (ZONAS["organico"])
    base: float = 0.25
    lados: float = 0.06
    direita_extra: float = 0.06
    min_palavras: int = 2
    max_palavras: int = 3
    max_caracteres: int = 16
    pausa_quebra: float = 0.6           # pausa (s) que sempre começa um bloco novo
    segurar: float = 0.25               # quanto o último bloco fica na tela depois da última palavra
    largura_letra: float = 0.50         # largura de uma maiúscula em fração do Fontsize do libass (medido no PC: ~0,49)
    largura_espaco: float = 0.5         # o espaço vale meia letra (estimativa pela métrica da Arial Black)
    destaque_min: float = 0.08          # duração mínima (s) do destaque de uma palavra


RX_FIM_FORTE = re.compile(r"[.!?…]+[\"'”»)]*$")
RX_FIM_FRACO = re.compile(r"[,;:]+[\"'”»)]*$")

# --------------------------------------------------------------------------- transcrição

TAXA_WHISPER = 16000
PROMPT_COLOQUIAL = "Fala coloquial em português do Brasil, escrita como foi dita: tá, tô, pra, pro, né, cê, o que que."

# Os nomes do faster-whisper e o repositório de cada um (o mesmo mapa do faster_whisper.utils._MODELS 1.2.1; o do
# pacote instalado vence quando existe).
MODELOS_HF = {
    "tiny": "Systran/faster-whisper-tiny", "tiny.en": "Systran/faster-whisper-tiny.en",
    "base": "Systran/faster-whisper-base", "base.en": "Systran/faster-whisper-base.en",
    "small": "Systran/faster-whisper-small", "small.en": "Systran/faster-whisper-small.en",
    "medium": "Systran/faster-whisper-medium", "medium.en": "Systran/faster-whisper-medium.en",
    "large-v1": "Systran/faster-whisper-large-v1", "large-v2": "Systran/faster-whisper-large-v2",
    "large-v3": "Systran/faster-whisper-large-v3", "large": "Systran/faster-whisper-large-v3",
    "large-v3-turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo", "turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
}


def resolver_modelo(nome: str) -> str:
    """O que passar ao WhisperModel. O faster-whisper carrega como modelo qualquer PASTA com o nome pedido, então
    rodar numa pasta que tem uma subpasta "medium" dava "Unable to open file 'model.bin'". Nome conhecido vira o id
    do HuggingFace (mesmo cache, nada baixa de novo); pasta de verdade, com model.bin, passa como está."""
    p = Path(nome)
    if (p / "model.bin").is_file():
        return str(p)
    try:
        from faster_whisper.utils import _MODELS as mapa  # type: ignore
    except Exception:
        mapa = {}
    return mapa.get(nome) or MODELOS_HF.get(nome) or nome


def decodificar_audio(video: Path, taxa: int = TAXA_WHISPER):
    """O áudio do vídeo em float32 mono 16 kHz, pelo ffmpeg. Não usa o PyAV: com o av 16 ou mais novo, o
    decode_audio do faster-whisper 1.2.1 cai em "open() got an unexpected keyword argument 'metadata_errors'"."""
    import numpy as np

    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", str(taxa),
                        "-f", "f32le", "-"], capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"o ffmpeg não leu o áudio de {video}:\n{r.stderr.decode(errors='replace')[-800:]}")
    audio = np.frombuffer(r.stdout, dtype=np.float32).copy()
    if audio.size == 0:
        raise SystemExit(f"{video} não tem áudio.")
    return audio


def montar_dicas(termos: Iterable[str]) -> tuple[str, str | None]:
    """(initial_prompt, hotwords). Os termos do roteiro (marcas, nomes, bordões) vão nos dois; a dica de fala
    coloquial vai sempre no prompt, para o Whisper não "corrigir" pra -> para, tá -> está."""
    t = [x.strip() for x in termos if x and x.strip()]
    prompt = PROMPT_COLOQUIAL + (f" Termos do roteiro: {', '.join(t)}." if t else "")
    return prompt, (", ".join(t) or None)


def ler_termos(texto: str | None, arquivo: Path | None = None) -> list[str]:
    termos = [x for x in re.split(r"[,;\n]+", texto or "") if x.strip()]
    if arquivo:
        termos += [x for x in re.split(r"[,;\n]+", arquivo.read_text(encoding="utf-8")) if x.strip()]
    return [x.strip() for x in termos]


def transcrever(video: Path, modelo: str = "medium", idioma: str = "pt", dispositivo: str = "cpu",
                tipo: str = "int8", pasta_modelo: str | None = None, termos: Iterable[str] = (),
                carregar: Callable | None = None, decodificar: Callable | None = None) -> list[Palavra]:
    """faster-whisper com word_timestamps. `carregar` e `decodificar` existem só para o teste trocar o modelo e o áudio."""
    if carregar is None:
        from faster_whisper import WhisperModel
        carregar = WhisperModel
    audio = (decodificar or decodificar_audio)(video)
    m = carregar(resolver_modelo(modelo), device=dispositivo, compute_type=tipo, download_root=pasta_modelo)
    prompt, quentes = montar_dicas(termos)
    segmentos, _info = m.transcribe(audio, language=idioma, word_timestamps=True, vad_filter=True,
                                    beam_size=5, condition_on_previous_text=False,
                                    initial_prompt=prompt, hotwords=quentes)
    palavras = []
    for s in segmentos:
        for w in getattr(s, "words", None) or []:
            texto = (w.word or "").strip()
            if texto:
                palavras.append(Palavra(round(float(w.start), 3), round(float(w.end), 3), texto,
                                        round(float(w.probability), 3) if w.probability is not None else None))
    return juntar_tokens(palavras)


# --------------------------------------------------------------------------- número partido e hora

RX_HORA = re.compile(r"^(\d{1,2})\s*[:hH]\s*(\d{2})(\W*)$")
RX_RESTO_HORA = re.compile(r"^[,.:]\s*(\d{2})(\W*)$")
MOEDA = re.compile(r"(R\$|US\$|\$|€|£)$|^(reais?|d[oó]lar(es)?|euros?|centavos?)$", re.I)


def _cola_na_anterior(t: str, anterior: str) -> bool:
    """O token começa com pontuação que fecha (",45,", "?", "%") ou é dígito logo depois de número com separador
    ("5:" "45"). Abre-aspas, abre-parêntese e travessão não colam."""
    c = t[0]
    cat = unicodedata.category(c)
    if c in "%‰" or cat in ("Po", "Pe", "Pf") and c not in "¿¡":
        return True
    return c.isdigit() and bool(re.search(r"\d[:,.hH]$", anterior))


def _hora(texto: str) -> str | None:
    m = RX_HORA.match(texto)
    if m and int(m.group(1)) <= 23 and int(m.group(2)) <= 59:
        return f"{int(m.group(1))}H{m.group(2)}{m.group(3)}"
    return None


def juntar_tokens(palavras: list[Palavra]) -> list[Palavra]:
    """Junta à palavra anterior o token que começa com pontuação ou o dígito que continua um número, e escreve hora
    como "5H45". O Whisper partiu "5:45" em "5" e ",45,"; separado, o bloco mostrava "5 ,45,". Número com vírgula
    que já vem inteiro ("5,45") fica como está (é preço); partido depois de "R$" ou antes de "reais" também."""
    out: list[Palavra] = []
    for i, p in enumerate(palavras):
        t = p.texto.strip()
        if not t:
            continue
        if out and _cola_na_anterior(t, out[-1].texto):
            ant = out[-1]
            junto = ant.texto + t
            r = RX_RESTO_HORA.match(t)
            antes = out[-2].texto if len(out) >= 2 else ""
            depois = palavras[i + 1].texto.strip() if i + 1 < len(palavras) else ""
            if (r and re.fullmatch(r"\d{1,2}", ant.texto) and int(ant.texto) <= 23 and int(r.group(1)) <= 59
                    and not MOEDA.search(antes) and not MOEDA.search(re.sub(r"\W+$", "", depois))):
                junto = f"{int(ant.texto)}H{r.group(1)}{r.group(2)}"
            probs = [x for x in (ant.prob, p.prob) if x is not None]
            out[-1] = Palavra(ant.inicio, max(ant.fim, p.fim), junto, min(probs) if probs else None)
        else:
            out.append(Palavra(p.inicio, p.fim, t, p.prob))
    return [replace(p, texto=_hora(p.texto) or p.texto) for p in out]


# --------------------------------------------------------------------------- palavras.json e revisão


def conferencia(palavras: list[Palavra]) -> str:
    return hashlib.sha1(json.dumps([asdict(p) for p in palavras], ensure_ascii=False).encode()).hexdigest()[:16]


def salvar_palavras(palavras: list[Palavra], caminho: Path, revisado: bool = False, **meta) -> None:
    dados = {"revisado": revisado, "conferencia": conferencia(palavras), **meta, "palavras": [asdict(p) for p in palavras]}
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")


def ler_json_palavras(caminho: Path) -> dict:
    """{"revisado", "editado", "palavras"}. Aceita o formato da v1 (uma lista) e o da v2 (objeto)."""
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    if isinstance(dados, list):
        lista, meta = dados, {}
    else:
        lista, meta = dados.get("palavras", []), dados
    palavras = [Palavra(float(d["inicio"]), float(d["fim"]), str(d["texto"]), d.get("prob")) for d in lista]
    editado = bool(meta.get("conferencia")) and meta.get("conferencia") != conferencia(palavras)
    return {"revisado": meta.get("revisado") is True, "editado": editado, "v1": isinstance(dados, list),
            "palavras": palavras}


def ler_palavras(caminho: Path) -> list[Palavra]:
    return ler_json_palavras(caminho)["palavras"]


def mmss(s: float) -> str:
    m, r = divmod(max(0.0, s), 60)
    return f"{int(m):02d}:{r:05.2f}"


def lista_revisao(palavras: list[Palavra], limiar: float = 0.5, contexto: int = 4) -> list[dict]:
    """As palavras com prob abaixo do limiar, com tempo e as palavras em volta."""
    itens = []
    for i, p in enumerate(palavras):
        if p.prob is not None and p.prob < limiar:
            antes = " ".join(x.texto for x in palavras[max(0, i - contexto):i])
            depois = " ".join(x.texto for x in palavras[i + 1:i + 1 + contexto])
            itens.append({"i": i, "inicio": p.inicio, "prob": p.prob, "texto": p.texto,
                          "contexto": f"{antes} ⟦{p.texto}⟧ {depois}".strip()})
    return itens


def escrever_revisao(video: Path, palavras: list[Palavra], destino: Path, limiar: float = 0.5,
                     modelo: str = "", termos: Iterable[str] = ()) -> list[dict]:
    itens = lista_revisao(palavras, limiar)
    json_nome = video.with_suffix(".palavras.json").name
    linhas = [
        f"REVISÃO · {video.name} · {len(itens)} de {len(palavras)} palavras com prob < {limiar:g}"
        + (f" (modelo {modelo}" + (f"; termos: {', '.join(termos)}" if termos else "") + ")" if modelo else ""),
        f"1. Ouça cada trecho e corrija o \"texto\" no {json_nome} (procure pelo \"inicio\").",
        "   Marca, nome e fala coloquial (tá, tô, pra, né) ficam como foram ditos.",
        f"2. Mude \"revisado\": false para \"revisado\": true no {json_nome}.",
        f"3. python legenda_reels.py queimar {video.name}",
        "",
    ]
    if itens:
        linhas.append(f"{'tempo':<9} {'prob':>5}  {'palavra':<18} contexto")
        for it in itens:
            linhas.append(f"{mmss(it['inicio']):<9} {it['prob']:>5.2f}  {it['texto']:<18} {it['contexto']}")
    else:
        linhas.append("Nenhuma palavra abaixo do limiar. Mesmo assim, confira marcas e nomes próprios antes de queimar.")
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return itens


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


# --------------------------------------------------------------------------- blocos de 2 a 3 palavras


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
    custo (programação dinâmica), então "a reunião de hoje começa às nove em ponto" vira blocos
    equilibrados em vez de 3 + 3 + 3 com um "DE" no fim."""
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


def largura_rel(t: str, espaco: float = 0.5) -> float:
    """Largura do texto em "letras": cada espaço vale `espaco` de letra."""
    return len(t) - (1 - espaco) * t.count(" ")


def quebrar(textos: list[str], max_linha: float, espaco: float = 0.5) -> int | None:
    """Índice da palavra que começa a 2ª linha, ou None se o bloco cabe numa linha. A quebra é
    decidida aqui (e não pelo libass) para o bloco não mudar de forma quando o destaque com zoom
    passa de uma palavra para outra. Escolhe a divisão mais equilibrada, com a 1ª linha maior ou igual."""
    if len(textos) < 2 or largura_rel(" ".join(textos), espaco) <= max_linha:
        return None
    melhor = None
    for k in range(1, len(textos)):
        a, b = largura_rel(" ".join(textos[:k]), espaco), largura_rel(" ".join(textos[k:]), espaco)
        nota = (max(a, b), 0 if a >= b else 1)
        if melhor is None or nota < melhor[0]:
            melhor = (nota, k)
    return melhor[1]


def tamanho_px(altura: int, e: Estilo) -> int:
    return e.tamanho or round(altura * e.tamanho_rel)


def tempos_destaque(g: list[Palavra], fim_bloco: float, minimo: float = 0.08) -> list[tuple[float, float]]:
    """(início, fim) do destaque de cada palavra do bloco, todos com duração > 0. O Whisper às vezes dá duração zero
    ou o mesmo início a duas palavras; na v1 essa palavra nunca acendia. Cada início fica pelo menos `minimo` depois
    do anterior; se não couber até o fim do bloco, o tempo do bloco é repartido por igual."""
    ini = [g[0].inicio]
    for p in g[1:]:
        ini.append(max(p.inicio, ini[-1] + minimo))
    fim_bloco = max(fim_bloco, g[0].inicio + 0.01 * len(g))
    if ini[-1] + minimo > fim_bloco:
        passo = (fim_bloco - g[0].inicio) / len(g)
        ini = [g[0].inicio + k * passo for k in range(len(g))]
    return [(ini[k], ini[k + 1] if k + 1 < len(g) else fim_bloco) for k in range(len(g))]


def gerar_ass(grupos: list[list[Palavra]], largura: int, altura: int, e: Estilo) -> str:
    tam = tamanho_px(altura, e)
    contorno = max(2, round(tam * 0.08))
    sombra = max(1, round(tam * 0.05))
    margem_e = round(largura * e.lados)
    margem_d = round(largura * (e.lados + e.direita_extra))
    x = round((margem_e + (largura - margem_d)) / 2)
    y_min = altura * e.topo + tam
    y_max = altura * (1 - e.base) - tam
    y = round(min(max(altura * e.posicao, y_min), y_max))
    cor, destaque = cor_ass(e.cor), cor_ass(e.destaque)
    max_linha = max(6.0, (largura - margem_e - margem_d) / (e.largura_letra * tam))
    linhas = [
        "[Script Info]",
        "; Gerado por legenda_reels.py v2",
        "ScriptType: v4.00+",
        f"PlayResX: {largura}",
        f"PlayResY: {altura}",
        "WrapStyle: 2",
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
        segunda = quebrar(textos, max_linha, e.largura_espaco)
        for i, (ini, fim) in enumerate(tempos_destaque(g, fim_bloco, e.destaque_min)):
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


def filtro_guia(g: Estilo) -> str:
    """Caixas translúcidas com o que fica fora da área segura. Só para PNG de conferência, nunca no MP4."""
    return (f"drawbox=x=0:y=0:w=iw:h=ih*{g.topo}:color=red@0.35:t=fill,"
            f"drawbox=x=0:y=ih*{1 - g.base}:w=iw:h=ih*{g.base}:color=red@0.35:t=fill,"
            f"drawbox=x=iw*{1 - g.lados - g.direita_extra}:y=ih*{g.topo}:w=iw*{g.lados + g.direita_extra}:"
            f"h=ih*{1 - g.topo - g.base}:color=red@0.20:t=fill,"
            f"drawbox=x=iw*{g.lados}:y=ih*{g.topo}:w=iw*{1 - 2 * g.lados - g.direita_extra}:"
            f"h=ih*{1 - g.topo - g.base}:color=white@0.7:t=4")


def queimar(video: Path, ass: Path, saida: Path, crf: int = 18, preset: str = "medium",
            pasta_fontes: Path | None = None) -> None:
    copia = ass.parent / "_legenda_reels_queima.ass"   # nome sem espaço nem acento para o filtro do ffmpeg
    shutil.copyfile(ass, copia)
    filtro = f"subtitles={copia.name}"
    if pasta_fontes:
        filtro += f":fontsdir={escapar_filtro(str(pasta_fontes.resolve()))}"
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


def tirar_prints(saida: Path, grupos: list[list[Palavra]], n: int, pasta: Path, guia: Estilo | None = None) -> list[Path]:
    """n quadros do vídeo legendado, espalhados pelo vídeo, cada um no meio de uma palavra. Com `guia`, cada quadro
    sai também em <saida>_guia_N.png com a área segura pintada (o MP4 fica limpo)."""
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
        if guia is not None:
            destino_g = pasta / f"{saida.stem}_guia_{k}.png"
            subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", str(saida),
                            "-vf", filtro_guia(guia), "-frames:v", "1", str(destino_g)], check=True)
            arquivos.append(destino_g)
    return arquivos


# --------------------------------------------------------------------------- legenda já queimada (aviso)


def detectar_legenda_queimada(video: Path, info: dict | None = None, quadros: int = 6, limiar: float = 0.02) -> dict:
    """Heurística: procura texto claro com contorno ou sombra escura (o jeito de legenda de edição) na metade de baixo
    do quadro, em vários quadros. Devolve {"aviso", "quadros_com_texto", "quadros", "faixa"}. É AVISO, nunca bloqueio:
    vídeo com placa, prateleira ou camiseta escrita pode acusar, e legenda fina sem contorno pode passar."""
    import numpy as np

    info = info or sondar(video)
    dur = info.get("duracao") or 0
    if dur <= 0:
        return {"aviso": False, "quadros_com_texto": 0, "quadros": 0, "faixa": None}
    L, A = 360, 640
    y0, y1 = int(A * 0.40), int(A * 0.92)        # onde a edição costuma pôr legenda
    janela = 32                                   # 5% da altura
    acertos, faixas, lidos = 0, [], 0
    for k in range(quadros):
        t = dur * (k + 0.5) / quadros
        r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
                            "-vf", f"scale={L}:{A},crop={L}:{y1 - y0}:0:{y0}", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                           capture_output=True)
        if r.returncode != 0 or len(r.stdout) < L * (y1 - y0):
            continue
        lidos += 1
        a = np.frombuffer(r.stdout[:L * (y1 - y0)], dtype=np.uint8).reshape(y1 - y0, L)
        claro, escuro = a >= 225, a <= 45
        perto = np.zeros_like(escuro)
        for d in (1, 2, 3):
            perto[:, d:] |= escuro[:, :-d]
            perto[:, :-d] |= escuro[:, d:]
            perto[d:, :] |= escuro[:-d, :]
            perto[:-d, :] |= escuro[d:, :]
        por_linha = (claro & perto).mean(axis=1)
        media = np.convolve(por_linha, np.ones(janela) / janela, mode="valid")
        if media.size and media.max() >= limiar:
            acertos += 1
            faixas.append((y0 + int(media.argmax()) + janela / 2) / A)
    aviso = lidos > 0 and acertos >= max(2, (lidos + 1) // 2)
    faixa = round(sorted(faixas)[len(faixas) // 2], 2) if faixas else None
    return {"aviso": aviso, "quadros_com_texto": acertos, "quadros": lidos, "faixa": faixa}


def avisar_legenda_queimada(video: Path, info: dict) -> dict:
    r = detectar_legenda_queimada(video, info)
    if r["aviso"]:
        print(f"AVISO: {video.name} parece já ter legenda queimada (texto claro com contorno em {r['quadros_com_texto']} "
              f"de {r['quadros']} quadros, perto de {round((r['faixa'] or 0) * 100)}% da altura). As duas legendas juntas "
              "poluem a tela: use o vídeo bruto, sem a legenda da edição, ou confira os prints antes de postar.",
              file=sys.stderr)
    return r


# --------------------------------------------------------------------------- CLI


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("passo", nargs="?", choices=["revisar", "queimar"], default="queimar")
    ap.add_argument("video", type=Path)
    ap.add_argument("-o", "--saida", type=Path, help="padrão: <video>_legendado.mp4")
    ap.add_argument("--palavras", type=Path, help="palavras.json pronto, de outra fonte (conta como revisado)")
    ap.add_argument("--retranscrever", action="store_true", help="ignora o <video>.palavras.json salvo")
    ap.add_argument("--modelo", default="medium", help="modelo do faster-whisper (padrão medium)")
    ap.add_argument("--pasta-modelo", help="onde guardar ou achar o modelo baixado")
    ap.add_argument("--termos", default="", help='marcas, nomes e bordões do roteiro, separados por vírgula')
    ap.add_argument("--termos-arquivo", type=Path, help="arquivo com os termos (um por linha ou por vírgula)")
    ap.add_argument("--limiar", type=float, default=0.5, help="prob abaixo disto vai para o revisar.txt (padrão 0,5)")
    ap.add_argument("--sem-revisar", action="store_true", help="queima sem a revisão (avisa)")
    ap.add_argument("--sem-aviso-legenda", action="store_true", help="não procura legenda já queimada no vídeo")
    ap.add_argument("--sem-legenda", default="", help="trechos sem legenda, ex.: 0:12-0:15,1:02-1:05.5")
    ap.add_argument("--fonte", default=Estilo.fonte, help='padrão "Arial Black" (vem no Windows)')
    ap.add_argument("--pasta-fontes", type=Path, help="pasta com .ttf/.otf para a fonte escolhida")
    ap.add_argument("--tamanho", type=int, help="tamanho da fonte em px (padrão: 5,8%% da altura)")
    ap.add_argument("--cor", default=Estilo.cor)
    ap.add_argument("--destaque", default=Estilo.destaque, help="cor da palavra falada")
    ap.add_argument("--posicao", type=float, default=Estilo.posicao, help="centro vertical, fração da altura (padrão 0,62)")
    ap.add_argument("--zona", choices=sorted(ZONAS), default="organico", help="área segura (padrão organico)")
    ap.add_argument("--caixa", choices=["alta", "normal"], default="alta")
    ap.add_argument("--sem-zoom", action="store_true", help="palavra falada sem o zoom de 112%%")
    ap.add_argument("--palavras-por-bloco", default="2-3", help="mínimo-máximo, padrão 2-3")
    ap.add_argument("--max-caracteres", type=int, default=Estilo.max_caracteres)
    ap.add_argument("--so-ass", action="store_true", help="só gera o .ass, sem queimar")
    ap.add_argument("--prints", type=int, default=0, help="quantos PNG de quadros legendados salvar")
    ap.add_argument("--guia", action="store_true", help="PNG extras com a área segura pintada (o MP4 fica limpo)")
    ap.add_argument("--crf", type=int, default=18)
    return ap


def revisar(a, carregar: Callable | None = None, decodificar: Callable | None = None, info: dict | None = None) -> Path:
    """Passo 1: transcreve (ou reaproveita o palavras.json) e escreve o revisar.txt."""
    cache = a.video.with_suffix(".palavras.json")
    termos = ler_termos(a.termos, a.termos_arquivo)
    if cache.exists() and not a.retranscrever:
        palavras = ler_palavras(cache)
        print(f"Usando a transcrição salva em {cache} (--retranscrever para refazer).", file=sys.stderr)
    else:
        print(f"Transcrevendo com faster-whisper ({a.modelo}, int8, CPU)...", file=sys.stderr)
        palavras = transcrever(a.video, a.modelo, pasta_modelo=a.pasta_modelo, termos=termos,
                               carregar=carregar, decodificar=decodificar)
        salvar_palavras(palavras, cache, revisado=False, modelo=a.modelo, termos=termos)
    rev = a.video.with_suffix(".revisar.txt")
    itens = escrever_revisao(a.video, palavras, rev, a.limiar, a.modelo, termos)
    if not a.sem_aviso_legenda:
        avisar_legenda_queimada(a.video, info or sondar(a.video))
    print(f"{len(itens)} palavra(s) para conferir em {rev}. Depois: python legenda_reels.py queimar {a.video.name}",
          file=sys.stderr)
    return rev


def main(argv: Iterable[str] | None = None, carregar: Callable | None = None,
         decodificar: Callable | None = None) -> Path:
    a = _parser().parse_args(list(argv) if argv is not None else None)
    exigir_ffmpeg()
    if not a.video.exists():
        raise SystemExit(f"Não achei {a.video}")
    info = sondar(a.video)
    if abs(info["largura"] / info["altura"] - 9 / 16) > 0.02:
        print(f"Aviso: o vídeo é {info['largura']}x{info['altura']}, não 9:16. A legenda sai mesmo assim.", file=sys.stderr)

    if a.passo == "revisar":
        return revisar(a, carregar, decodificar, info)

    cache = a.video.with_suffix(".palavras.json")
    if a.palavras:
        palavras = ler_palavras(a.palavras)
    else:
        if a.retranscrever or not cache.exists():
            rev = revisar(a, carregar, decodificar, info)
            if not a.sem_revisar:
                raise SystemExit(f"Revisão primeiro: confira {rev}, corrija {cache.name}, ponha \"revisado\": true e rode "
                                 f"de novo (ou use --sem-revisar, por sua conta).")
        lido = ler_json_palavras(cache)
        palavras = lido["palavras"]
        if not (lido["revisado"] or lido["editado"]):
            baixas = len(lista_revisao(palavras, a.limiar))
            if not a.sem_revisar:
                raise SystemExit(f"{cache.name} ainda não foi revisado ({baixas} palavra(s) com prob < {a.limiar:g}). "
                                 f"Confira {a.video.with_suffix('.revisar.txt').name}, ponha \"revisado\": true e rode de "
                                 "novo. Para queimar assim mesmo: --sem-revisar.")
            print(f"AVISO: queimando SEM revisão ({baixas} palavra(s) com prob < {a.limiar:g} não conferidas).", file=sys.stderr)

    mn, mx = (int(x) for x in a.palavras_por_bloco.split("-"))
    e = Estilo(fonte=a.fonte, tamanho=a.tamanho, cor=a.cor, destaque=a.destaque, posicao=a.posicao,
               caixa_alta=a.caixa == "alta", zoom_destaque=100 if a.sem_zoom else 112, min_palavras=mn,
               max_palavras=mx, max_caracteres=a.max_caracteres, **ZONAS[a.zona])
    palavras = tirar_trechos(juntar_tokens(palavras), ler_trechos(a.sem_legenda))
    grupos = agrupar(palavras, e)

    saida = a.saida or a.video.with_name(f"{a.video.stem}_legendado.mp4")
    ass = saida.with_suffix(".ass")
    ass.write_text(gerar_ass(grupos, info["largura"], info["altura"], e), encoding="utf-8")
    print(f"{len(palavras)} palavras em {len(grupos)} blocos -> {ass}", file=sys.stderr)
    if a.so_ass:
        return ass
    queimar(a.video, ass, saida, a.crf, pasta_fontes=a.pasta_fontes)
    print(f"ok: {saida}", file=sys.stderr)
    n_prints = a.prints or (3 if a.guia else 0)
    for p in tirar_prints(saida, grupos, n_prints, saida.parent, guia=e if a.guia else None):
        print(f"print: {p}", file=sys.stderr)
    return saida


if __name__ == "__main__":
    main()
