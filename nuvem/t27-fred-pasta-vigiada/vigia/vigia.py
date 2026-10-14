#!/usr/bin/env python3
"""Fred · pasta vigiada de vídeo (14/10/2026). Windows, Python, nada pago; roda sob demanda ou pelo Agendador.

Para cada vídeo novo em <raiz>/entrada/:
  1. espera o arquivo terminar de copiar (tamanho e data parados por --estavel segundos);
  2. roda o passo `revisar` da legenda v2 e deixa em <raiz>/revisao/<nome>/:
       <nome>.palavras.json   a transcrição, para corrigir
       <nome>.revisar.txt     só as palavras duvidosas (prob < 0,5), com tempo e contexto
       <nome>_previa_1..3.png três quadros do bruto com a legenda AINDA NÃO REVISADA desenhada por cima
       publi-checklist.rascunho.md  se o nome do arquivo tiver "publi": os 10 itens, todos em aberto
  3. NUNCA queima sozinho. Só quando você cria o marcador <raiz>/revisao/<nome>/<nome>.ok (arquivo vazio),
     depois de corrigir o palavras.json, a próxima rodada queima a legenda e põe em <raiz>/saida/:
       <nome>_legendado.mp4 e 3 prints.
     Mexeu no palavras.json depois do .ok? Crie o .ok de novo: o vigia só queima a versão que o .ok marcou.

Nunca publica, nunca corta silêncio, nunca apaga nem move o bruto (entrada/ é só leitura). Não refaz o que já
fez: o que decide é o que está no disco (revisao/ e saida/), então dá para rodar quantas vezes quiser.

Uso:
  python vigia.py --raiz D:\\Fred\\video --uma-vez            # uma rodada (o Agendador chama assim)
  python vigia.py --raiz D:\\Fred\\video --intervalo 60       # fica vigiando, uma rodada por minuto
  python vigia.py --raiz D:\\Fred\\video --status             # mostra em que pé está cada vídeo
Termos do roteiro: --termos "Marca, Nome" ou --termos-arquivo termos.txt, e/ou um <nome>.termos.txt ao lado do
vídeo em entrada/ (só para aquele vídeo).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

import legenda_reels as lr  # noqa: E402

EXTENSOES = {".mp4", ".mov", ".m4v"}
TEMPORARIOS = (".part", ".crdownload", ".tmp", ".download", ".partial", ".opdownload")
RX_PUBLI = re.compile(r"(?<![a-z0-9])publi(?![a-z])")      # publi_..., ..._publi, "#publi"; "republica" não


@dataclass
class Opcoes:
    modelo: str = "medium"
    pasta_modelo: str | None = None
    termos: list[str] = field(default_factory=list)
    limiar: float = 0.5
    zona: str = "organico"
    fonte: str | None = None
    pasta_fontes: Path | None = None
    estavel: float = 10.0           # segundos com tamanho e data parados antes de ler
    passo: float = 2.0              # de quanto em quanto tempo olha o tamanho
    trava_horas: float = 6.0        # trava mais velha que isso é de uma rodada que morreu


class Vigia:
    def __init__(self, raiz: Path, op: Opcoes | None = None, carregar: Callable | None = None,
                 decodificar: Callable | None = None, relogio: Callable[[], float] = time.monotonic,
                 dormir: Callable[[float], None] = time.sleep):
        self.raiz = Path(raiz)
        self.op = op or Opcoes()
        self.carregar, self.decodificar = carregar, decodificar
        self.relogio, self.dormir = relogio, dormir
        self.entrada = self.raiz / "entrada"
        self.revisao = self.raiz / "revisao"
        self.saida = self.raiz / "saida"
        self.interna = self.raiz / ".vigia"

    # ------------------------------------------------------------------ registro

    def log(self, msg: str) -> None:
        linha = f"[{dt.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
        print(linha, flush=True)
        try:
            with open(self.interna / "vigia.log", "a", encoding="utf-8") as f:
                f.write(linha + "\n")
        except OSError:
            pass

    def _gravar(self, caminho: Path, texto: str) -> None:
        """Escrita atômica, só fora de entrada/."""
        assert self.entrada.resolve() not in caminho.resolve().parents, "o vigia não escreve em entrada/"
        tmp = caminho.with_name(caminho.name + ".tmp")
        tmp.write_text(texto, encoding="utf-8")
        os.replace(tmp, caminho)

    # ------------------------------------------------------------------ trava

    def _travar(self) -> bool:
        trava = self.interna / "trava"
        for _ in range(2):
            try:
                fd = os.open(trava, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, "w") as f:
                    f.write(f"pid={os.getpid()} desde={dt.datetime.now().isoformat(timespec='seconds')}\n")
                return True
            except FileExistsError:
                try:
                    idade_h = (time.time() - trava.stat().st_mtime) / 3600
                except FileNotFoundError:
                    continue
                if idade_h < self.op.trava_horas:
                    return False
                self.log(f"trava de {idade_h:.1f} h sem dono (rodada que morreu): tomando")
                trava.unlink(missing_ok=True)
        return False

    def _destravar(self) -> None:
        (self.interna / "trava").unlink(missing_ok=True)

    # ------------------------------------------------------------------ arquivos

    def videos(self) -> list[Path]:
        if not self.entrada.is_dir():
            return []
        vs = [p for p in self.entrada.iterdir() if p.is_file() and p.suffix.lower() in EXTENSOES
              and not p.name.startswith((".", "~$")) and not p.name.lower().endswith(TEMPORARIOS)]
        return sorted(vs, key=lambda p: p.name.lower())

    def nome_de(self, bruto: Path, todos: list[Path]) -> str:
        """Nome da pasta em revisao/ e base dos arquivos. Dois vídeos com o mesmo nome e extensões diferentes
        (corte.mp4 e corte.mov) não se misturam."""
        mesmo = [p for p in todos if p.stem.lower() == bruto.stem.lower()]
        return bruto.stem if len(mesmo) == 1 else f"{bruto.stem}_{bruto.suffix[1:].lower()}"

    @staticmethod
    def assinatura(p: Path) -> dict:
        s = p.stat()
        return {"arquivo": p.name, "tamanho": s.st_size, "mtime_ns": s.st_mtime_ns}

    def estavel(self, p: Path) -> bool:
        """Tamanho e data parados por `estavel` segundos e o arquivo abre para leitura (no Windows, o Explorer
        segura o arquivo enquanto copia)."""
        try:
            antes = self.assinatura(p)
            inicio = self.relogio()
            while self.relogio() - inicio < self.op.estavel:
                self.dormir(self.op.passo)
                agora = self.assinatura(p)
                if agora != antes or agora["tamanho"] == 0:
                    return False
            with open(p, "rb") as f:
                f.read(1)
            return True
        except (OSError, PermissionError):
            return False

    # ------------------------------------------------------------------ rodada

    def rodada(self) -> dict:
        """Uma passada pela entrada/. Devolve o resumo {nome: etapa}."""
        for d in (self.revisao, self.saida, self.interna):
            d.mkdir(parents=True, exist_ok=True)
        if not self.entrada.is_dir():
            self.entrada.mkdir(parents=True)
            self.log(f"criei {self.entrada}: ponha os vídeos brutos aí")
        if not self._travar():
            self.log("outra rodada está em andamento (trava em .vigia/trava): saindo sem fazer nada")
            return {"_ocupado": True}
        resumo = {}
        try:
            todos = self.videos()
            for bruto in todos:
                nome = self.nome_de(bruto, todos)
                try:
                    resumo[nome] = self.cuidar(bruto, nome)
                except SystemExit as e:              # o legenda_reels avisa erro com SystemExit
                    resumo[nome] = "erro"
                    self._erro(nome, str(e))
                except Exception as e:  # noqa: BLE001
                    resumo[nome] = "erro"
                    self._erro(nome, f"{type(e).__name__}: {e}")
            self._gravar(self.interna / "estado.json", json.dumps(
                {"rodada": dt.datetime.now().isoformat(timespec="seconds"), "videos": resumo}, ensure_ascii=False, indent=1))
        finally:
            self._destravar()
        return resumo

    def _erro(self, nome: str, msg: str) -> None:
        self.log(f"{nome}: ERRO {msg}")
        pasta = self.revisao / nome
        if pasta.is_dir():
            self._gravar(pasta / "ERRO.txt", f"{dt.datetime.now():%Y-%m-%d %H:%M}\n{msg}\n"
                         "Nada foi queimado. Corrija e o vigia tenta de novo na próxima rodada.\n")

    def cuidar(self, bruto: Path, nome: str) -> str:
        pasta = self.revisao / nome
        js = pasta / f"{nome}.palavras.json"
        origem = pasta / ".origem.json"
        if not js.exists():
            if not self.estavel(bruto):
                self.log(f"{bruto.name}: ainda copiando (tamanho mudando ou arquivo preso); fica para a próxima")
                return "copiando"
            self.revisar(bruto, nome)
            return "aguardando revisão"
        try:
            orig = json.loads(origem.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            orig = None
        if orig is None or {k: orig.get(k) for k in ("tamanho", "mtime_ns")} != \
                {k: v for k, v in self.assinatura(bruto).items() if k != "arquivo"}:
            self.log(f"{bruto.name}: o bruto mudou depois da revisão (ou .origem.json sumiu). Nada é queimado. "
                     f"Para recomeçar, dê outro nome ao vídeo ou apague a pasta {pasta}.")
            return "bruto mudou: parado"
        ok = pasta / f"{nome}.ok"
        if not ok.exists():
            return "aguardando revisão"
        if ok.stat().st_mtime_ns < js.stat().st_mtime_ns:
            self.log(f"{nome}: o palavras.json mudou depois do .ok. Crie o {ok.name} de novo quando terminar.")
            return "aguardando novo .ok"
        conf = hashlib.sha256(js.read_bytes()).hexdigest()
        try:
            feito = json.loads((pasta / ".queimado.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            feito = {}
        destino = self.saida / f"{nome}_legendado.mp4"
        if feito.get("conferencia") == conf and destino.exists():
            return "queimado"
        self.queimar(bruto, nome, js, destino, conf)
        return "queimado"

    # ------------------------------------------------------------------ passos

    def _termos(self, bruto: Path) -> list[str]:
        termos = list(self.op.termos)
        extra = bruto.with_name(bruto.stem + ".termos.txt")
        if extra.exists():
            termos += lr.ler_termos(None, extra)
        return termos

    def _estilo(self) -> "lr.Estilo":
        e = lr.Estilo(**lr.ZONAS[self.op.zona])
        if self.op.fonte:
            e.fonte = self.op.fonte
        return e

    def revisar(self, bruto: Path, nome: str) -> None:
        pasta = self.revisao / nome
        pasta.mkdir(parents=True, exist_ok=True)
        termos = self._termos(bruto)
        sig = self.assinatura(bruto)
        self.log(f"{bruto.name}: transcrevendo ({self.op.modelo}, int8, CPU)")
        info = lr.sondar(bruto)
        palavras = lr.transcrever(bruto, self.op.modelo, pasta_modelo=self.op.pasta_modelo, termos=termos,
                                  carregar=self.carregar, decodificar=self.decodificar)
        js = pasta / f"{nome}.palavras.json"
        rev = pasta / f"{nome}.revisar.txt"
        itens = lr.escrever_revisao(pasta / f"{nome}{bruto.suffix}", palavras, rev, self.op.limiar, self.op.modelo, termos)
        aviso = {"aviso": False}
        try:
            aviso = lr.detectar_legenda_queimada(bruto, info)
        except Exception as e:  # noqa: BLE001
            self.log(f"{bruto.name}: não consegui procurar legenda já queimada ({type(e).__name__})")
        topo = [f"PELO VIGIA · {bruto.name}",
                f"1. Corrija o \"texto\" das palavras erradas em {js.name} (esta pasta).",
                f"2. Quando terminar, crie nesta pasta um arquivo vazio chamado {nome}.ok.",
                "3. A próxima rodada do vigia queima a legenda e põe o vídeo em saida/. Não rode o queimar à mão.",
                f"   Os {nome}_previa_N.png mostram a legenda AINDA SEM REVISÃO, só para ver posição e tamanho."]
        if aviso.get("aviso"):
            topo.append(f"AVISO: o vídeo parece já ter legenda queimada pela edição (perto de "
                        f"{round((aviso.get('faixa') or 0) * 100)}% da altura). Duas legendas poluem: use o bruto.")
        # as instruções da v2 mandam rodar o queimar à mão; aqui quem queima é o vigia, com o .ok
        resto = [l for l in rev.read_text(encoding="utf-8").splitlines()
                 if not re.match(r"(1\. Ouça|2\. Mude|3\. python legenda_reels)", l)]
        resto = [l.replace("   Marca, nome", "Marca, nome") for l in resto]
        rev.write_text("\n".join(topo) + "\n\n" + "\n".join(resto) + "\n", encoding="utf-8")
        self.previas(bruto, palavras, info, pasta, nome)
        publi = bool(RX_PUBLI.search(normalizar(bruto.stem)))
        if publi:
            self._gravar(pasta / "publi-checklist.rascunho.md", checklist_publi(bruto.name, palavras))
        # o palavras.json por último: se a rodada cair antes dele, a próxima refaz a revisão inteira
        self._gravar(pasta / ".origem.json", json.dumps(sig, ensure_ascii=False))
        lr.salvar_palavras(palavras, js, revisado=False, modelo=self.op.modelo, termos=termos, video=bruto.name)
        self.log(f"{bruto.name}: revisão pronta em {pasta} ({len(itens)} palavra(s) duvidosa(s)"
                 + ("; checklist de publi em rascunho" if publi else "") + f"). Falta o {nome}.ok.")

    def previas(self, bruto: Path, palavras: list, info: dict, pasta: Path, nome: str, n: int = 3) -> list[Path]:
        """Três quadros do bruto com a legenda não revisada por cima (só PNG; o vídeo não é tocado)."""
        e = self._estilo()
        grupos = lr.agrupar(lr.juntar_tokens(palavras), e) if palavras else []
        ass = pasta / "previa.ass"
        ass.write_text(lr.gerar_ass(grupos, info["largura"], info["altura"], e), encoding="utf-8")
        dur = info.get("duracao") or 1.0
        if grupos:
            idx = sorted({round(k * (len(grupos) - 1) / max(1, n - 1)) for k in range(n)})
            tempos = [(g[min(1, len(g) - 1)].inicio + g[min(1, len(g) - 1)].fim) / 2 for g in (grupos[i] for i in idx)]
        else:
            tempos = [dur * (k + 1) / (n + 1) for k in range(n)]
        filtro = "subtitles=previa.ass"
        if self.op.pasta_fontes:
            filtro += f":fontsdir={lr.escapar_filtro(str(Path(self.op.pasta_fontes).resolve()))}"
        saidas = []
        for k, t in enumerate(tempos, 1):
            destino = pasta / f"{nome}_previa_{k}.png"
            r = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{t:.3f}", "-copyts",   # o relógio da legenda segue o do vídeo
                                "-i", str(bruto.resolve()), "-vf", filtro, "-frames:v", "1", destino.name],
                               cwd=pasta, capture_output=True, text=True)
            if r.returncode == 0:
                saidas.append(destino)
            else:
                self.log(f"{nome}: prévia {k} falhou: {r.stderr[-300:]}")
        return saidas

    def queimar(self, bruto: Path, nome: str, js: Path, destino: Path, conf: str) -> Path:
        lido = lr.ler_json_palavras(js)              # json quebrado levanta erro aqui: nada é queimado
        if not (lido["revisado"] or lido["editado"]):
            self.log(f"{nome}: o .ok veio sem nenhuma correção no palavras.json; queimando assim mesmo (o .ok é o OK)")
        self.log(f"{nome}: queimando (o .ok está lá)")
        args = ["queimar", str(bruto), "--palavras", str(js), "-o", str(destino), "--prints", "3",
                "--zona", self.op.zona, "--sem-aviso-legenda"]
        if self.op.fonte:
            args += ["--fonte", self.op.fonte]
        if self.op.pasta_fontes:
            args += ["--pasta-fontes", str(self.op.pasta_fontes)]
        saida = lr.main(args)
        self._gravar(js.parent / ".queimado.json", json.dumps(
            {"conferencia": conf, "saida": str(saida), "em": dt.datetime.now().isoformat(timespec="seconds")}))
        (js.parent / "ERRO.txt").unlink(missing_ok=True)
        self.log(f"{nome}: pronto em {saida}")
        return saida

    # ------------------------------------------------------------------ status

    def status(self) -> list[tuple[str, str]]:
        linhas = []
        todos = self.videos()
        for bruto in todos:
            nome = self.nome_de(bruto, todos)
            pasta = self.revisao / nome
            if (self.saida / f"{nome}_legendado.mp4").exists() and (pasta / ".queimado.json").exists():
                etapa = "queimado"
            elif (pasta / f"{nome}.ok").exists():
                etapa = ".ok criado: queima na próxima rodada"
            elif (pasta / f"{nome}.palavras.json").exists():
                etapa = "aguardando revisão (crie o .ok)"
            else:
                etapa = "novo"
            linhas.append((bruto.name, etapa))
        return linhas


# --------------------------------------------------------------------------- checklist de publi (rascunho)

def normalizar(t: str) -> str:
    return unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode()


ITENS_PUBLI = [  # "Nuvem · Fred · publi sem risco", checklist-10.md (14/10/2026); não é parecer jurídico
    ("O anunciante pode anunciar", "Bet: na lista de operadores autorizados da SPA/MF, com print e data. Financeiro: "
     "instituição autorizada. Crédito: o texto não diz \"sem consulta\" nem \"sem análise\".",
     "Portaria Interministerial 73/2026; CDC, art. 54-C"),
    ("\"Parceria paga\" ligada", "No post, nos stories e no reels, um por um, marcando a marca.",
     "Política de conteúdo de marca da Meta"),
    ("\"#publi\" ou \"Publicidade\" no começo da legenda e na tela", "Legível sem tocar em \"ver mais\". Nada de só "
     "\"#ad\" ou \"#parceiro\". Falar \"publi\" no vídeo não substitui.", "Guia CONAR 2026; CBAP, arts. 9º e 28; CDC, art. 36"),
    ("Presente, convite ou viagem também se declaram", "Mesmo sem contrato. Repost da marca vira publicidade.",
     "Guia CONAR 2026 (fonte secundária)"),
    ("Toda afirmação da marca tem prova da marca", "Número, \"o melhor\", \"mais rápido\", \"garantido\". Sem prova, a "
     "piada não faz a afirmação.", "CDC, arts. 36, 37 e 38"),
    ("A sátira é da própria marca, nunca de concorrente nomeado", "Comparar com outra marca é publicidade comparativa.",
     "CBAP, art. 32; Lei 9.279, art. 195; Lei 9.610, art. 47"),
    ("Financeiro: só institucional", "Nada de recomendar produto ou ativo, de rentabilidade ou de oferta pública. "
     "A instituição contratante aparece.", "Res. CVM 20; Ofício-Circular CVM 13/2020; Res. CVM 160; regras ANBIMA"),
    ("Bet: público adulto, 18+, advertência", "Print do Insights; selo \"18+\"; uma frase \"Ministério da Fazenda "
     "adverte\"; nenhuma dica de aposta; nada de aposta como renda; quem aparece apostando parece ter 21 anos ou mais.",
     "Lei 14.790/2023, arts. 16 e 17; Portarias SPA/MF 1.231/2024 e 1.964/2026; Anexo X do CONAR"),
    ("Contrato assinado antes de postar", "Escopo e roteiro aprovados; uso e impulsionamento com prazo; correção em "
     "24 h; cláusula de sigilo da identidade do criador.", "Guia CONAR 2026; anonimato.md"),
    ("Guardar a prova", "Print do post no ar com rótulo e hashtag; roteiro aprovado; contrato; autorização da bet. "
     "Regra da casa: 1 ano.", "Regras ANBIMA (1 ano de prints)"),
]

# termo (sem acento, minúsculo) -> itens do checklist que ele pede para olhar com mais cuidado
GATILHOS = {
    "aposta": (1, 8), "apostar": (1, 8), "aposte": (1, 8), "bet": (1, 8), "bets": (1, 8), "cassino": (1, 8),
    "odd": (8,), "odds": (8,), "palpite": (8,), "tigrinho": (1, 8),
    "rende": (7,), "rendimento": (7,), "rentabilidade": (7,), "investimento": (7,), "investir": (7,),
    "juros": (1, 7), "cdb": (7,), "cripto": (7,), "bitcoin": (7,), "acoes": (7,), "lucro": (5, 7),
    "credito": (1,), "emprestimo": (1,), "consulta": (1,), "analise": (1,),
    "garantido": (5,), "garantida": (5,), "garantia": (5,), "certinho": (5, 7), "melhor": (5,), "barato": (5,), "rapido": (5,), "nunca": (5,),
    "100%": (5,), "gratis": (4, 5), "presente": (4,), "ganhei": (4,), "viagem": (4,),
    "publi": (3,), "publicidade": (3,), "parceria": (2, 3), "patrocinado": (3,),
}


def checklist_publi(arquivo: str, palavras: list) -> str:
    marca = ""
    m = re.search(r"publi[_\- ]+([^_]+)", Path(arquivo).stem, re.I)
    if m:
        marca = m.group(1)
    dicas: dict[int, list[str]] = {}
    for i, p in enumerate(palavras):
        t = re.sub(r"[^\w%]", "", normalizar(p.texto))
        for item in GATILHOS.get(t, ()):
            ctx = " ".join(x.texto for x in palavras[max(0, i - 3):i + 4])
            dicas.setdefault(item, []).append(f"{lr.mmss(p.inicio)} \"{t}\" em: {ctx}")
    linhas = [f"# Publi · checklist em RASCUNHO · {arquivo}", "",
              "**RASCUNHO preenchido pelo vigia. Nenhum item está aprovado. O vigia não marca nada e não publica. "
              "A publi só vai ao ar com o OK do dono, item por item.**", "",
              f"- Marca pelo nome do arquivo: {marca or 'não achei (use publi_<marca>_... no nome)'}",
              f"- Gerado em {dt.datetime.now():%Y-%m-%d %H:%M}, da transcrição AINDA NÃO REVISADA "
              f"({len(palavras)} palavras). As dicas apontam onde olhar; ausência de dica não quer dizer que está ok.",
              "- Fonte: checklist de 10 itens do artifact \"Nuvem · Fred · publi sem risco\" (14/10/2026). "
              "Não é parecer jurídico.", ""]
    for n, (titulo, confira, base) in enumerate(ITENS_PUBLI, 1):
        linhas.append(f"## {n}. [ ] {titulo}")
        linhas.append(f"- Confira: {confira}")
        linhas.append(f"- Base: {base}")
        for d in dicas.get(n, [])[:5]:
            linhas.append(f"- Dica da transcrição: {d}")
        linhas += ["- OK do dono: ______  Data: ______", ""]
    linhas += ["## Não aceitar sem falar com o dono antes", "",
               "- bet sem o print da autorização;", "- financeiro que peça para falar de rendimento;",
               "- qualquer roteiro que mire a marca de um concorrente.", ""]
    return "\n".join(linhas)


# --------------------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raiz", type=Path, required=True, help="pasta com entrada/, revisao/ e saida/")
    modo = ap.add_mutually_exclusive_group()
    modo.add_argument("--uma-vez", action="store_true", help="uma rodada e sai (padrão; é o que o Agendador chama)")
    modo.add_argument("--intervalo", type=float, help="fica vigiando: uma rodada a cada N segundos")
    modo.add_argument("--status", action="store_true", help="mostra a etapa de cada vídeo e sai")
    ap.add_argument("--modelo", default="medium")
    ap.add_argument("--pasta-modelo")
    ap.add_argument("--termos", default="")
    ap.add_argument("--termos-arquivo", type=Path)
    ap.add_argument("--limiar", type=float, default=0.5)
    ap.add_argument("--zona", choices=sorted(lr.ZONAS), default="organico")
    ap.add_argument("--fonte")
    ap.add_argument("--pasta-fontes", type=Path)
    ap.add_argument("--estavel", type=float, default=10.0, help="segundos com o tamanho parado antes de ler (padrão 10)")
    a = ap.parse_args(argv)
    op = Opcoes(modelo=a.modelo, pasta_modelo=a.pasta_modelo, termos=lr.ler_termos(a.termos, a.termos_arquivo),
                limiar=a.limiar, zona=a.zona, fonte=a.fonte, pasta_fontes=a.pasta_fontes, estavel=a.estavel)
    v = Vigia(a.raiz, op)
    if a.status:
        for arq, etapa in v.status():
            print(f"{arq:<40} {etapa}")
        return 0
    lr.exigir_ffmpeg()
    if a.intervalo:
        while True:
            v.rodada()
            time.sleep(max(5.0, a.intervalo))
    v.rodada()
    return 0


if __name__ == "__main__":
    sys.exit(main())
