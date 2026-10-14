#!/usr/bin/env python3
"""
Confere os registros de DNS de um domínio de envio de e-mail (SPF, DKIM, DMARC, MX e, se pedir, BIMI)
e diz o que falta. Feito para o domínio separado da prospecção da Ozav (tarefa 22, 14/10/2026).

Só lê DNS público. Não manda e-mail, não abre conexão SMTP, não usa conta nenhuma.

Uso:
  pip install dnspython
  python conferir_dominio.py prospeccao-exemplo.com.br --seletor google
  python conferir_dominio.py prospeccao-exemplo.com.br --seletor s1 --seletor s2 --bimi
  python conferir_dominio.py prospeccao-exemplo.com.br --envelope bounce.prospeccao-exemplo.com.br --json

Sem --seletor, tenta os seletores DKIM mais comuns (google, selector1, selector2, default, k1, s1, s2...).
Saída: uma linha por item, com OK, ATENÇÃO, FALTA, ERRO ou INFO. Código de saída 1 se houver FALTA ou ERRO.

Status:
  OK       está como deveria.
  ATENÇÃO  funciona, mas há risco ou passo seguinte (ex.: DMARC p=none, chave DKIM de 1024 bits).
  FALTA    registro ausente ou inválido; corrija antes de mandar volume.
  ERRO     o DNS não respondeu (timeout, servidor fora); não dá para dizer se falta.
  INFO     opcional ou só informativo.
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
from dataclasses import dataclass, field, asdict

try:
    import dns.exception
    import dns.resolver
except ImportError:  # o script tem de dizer o que fazer, não despejar um traceback
    print("Falta o dnspython: pip install dnspython", file=sys.stderr)
    raise SystemExit(2)

SELETORES_COMUNS = [
    "google", "selector1", "selector2", "default", "k1", "k2", "s1", "s2",
    "dkim", "mail", "smtp", "mxvault", "zoho", "zmail", "sig1", "mandrill", "smtpapi",
]
# Sufixos de dois níveis mais comuns para achar o domínio organizacional (DMARC e alinhamento).
# Não é a Public Suffix List inteira: cobre .com.br e parentes e os ccTLD de segundo nível mais vistos.
SUFIXOS_2 = {
    "com.br", "net.br", "org.br", "art.br", "eco.br", "ind.br", "srv.br", "tec.br", "app.br", "log.br",
    "co.uk", "org.uk", "com.ar", "com.mx", "com.co", "com.pe", "com.uy", "com.au", "co.jp",
}
MECANISMOS_COM_CONSULTA = ("include:", "a", "mx", "ptr", "exists:", "redirect=")


@dataclass
class Item:
    item: str
    status: str  # ok | atencao | falta | erro | info
    msg: str
    registro: str | None = None


@dataclass
class Relatorio:
    dominio: str
    itens: list[Item] = field(default_factory=list)

    def add(self, item, status, msg, registro=None):
        self.itens.append(Item(item, status, msg, registro))

    @property
    def falta(self):
        return [i for i in self.itens if i.status in ("falta", "erro")]

    def como_dict(self):
        return {"dominio": self.dominio, "itens": [asdict(i) for i in self.itens], "ok": not self.falta}


class ErroDNS(Exception):
    """O DNS não respondeu: não dá para dizer que o registro falta."""


def _txt(resolver, nome):
    """Os TXT de `nome`, cada registro com as partes juntadas. [] se o nome ou o TXT não existe."""
    try:
        resp = resolver.resolve(nome, "TXT")
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        return []
    except (dns.exception.Timeout, dns.resolver.NoNameservers) as e:
        raise ErroDNS(f"{nome} TXT: {e.__class__.__name__}") from e
    saida = []
    for rr in resp:
        partes = getattr(rr, "strings", None) or ()
        saida.append(b"".join(p if isinstance(p, bytes) else str(p).encode() for p in partes).decode("utf-8", "replace"))
    return saida


def _mx(resolver, nome):
    try:
        resp = resolver.resolve(nome, "MX")
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        return []
    except (dns.exception.Timeout, dns.resolver.NoNameservers) as e:
        raise ErroDNS(f"{nome} MX: {e.__class__.__name__}") from e
    return sorted((int(rr.preference), str(rr.exchange).rstrip(".").lower()) for rr in resp)


def dominio_organizacional(d):
    partes = d.lower().rstrip(".").split(".")
    if len(partes) >= 3 and ".".join(partes[-2:]) in SUFIXOS_2:
        return ".".join(partes[-3:])
    return ".".join(partes[-2:])


def _tags(txt):
    """'v=DKIM1; k=rsa; p=AAA' -> {'v': 'DKIM1', 'k': 'rsa', 'p': 'AAA'} (chaves minúsculas, sem espaços no valor)."""
    out = {}
    for parte in txt.split(";"):
        if "=" in parte:
            k, v = parte.split("=", 1)
            out[k.strip().lower()] = "".join(v.split())
    return out


# ------------------------------------------------------------------ SPF

def _spf_de(resolver, nome):
    regs = [t for t in _txt(resolver, nome) if t.strip().lower().startswith("v=spf1")]
    return regs


def contar_consultas_spf(resolver, nome, vistos=None, profundidade=0):
    """(consultas, consultas_vazias, problemas) do SPF de `nome`, seguindo include e redirect (RFC 7208, 4.6.4)."""
    vistos = set() if vistos is None else vistos
    problemas = []
    if nome in vistos:
        return 0, 0, [f"laço de include em {nome}"]
    if profundidade > 10:
        return 0, 0, ["include aninhado demais"]
    vistos.add(nome)
    regs = _spf_de(resolver, nome)
    if not regs:
        return 0, 1, [f"{nome} não tem SPF (include vazio conta como consulta vazia)"]
    if len(regs) > 1:
        problemas.append(f"{nome} tem {len(regs)} registros SPF")
    consultas, vazias = 0, 0
    for termo in regs[0].split()[1:]:
        t = termo.lower().lstrip("+-~?")
        if t.startswith("include:") or t.startswith("redirect="):
            alvo = termo.split(":", 1)[1] if t.startswith("include:") else termo.split("=", 1)[1]
            consultas += 1
            c, v, p = contar_consultas_spf(resolver, alvo.rstrip("."), vistos, profundidade + 1)
            consultas += c
            vazias += v
            problemas += p
        elif t == "a" or t.startswith("a:") or t.startswith("a/") or t == "mx" or t.startswith("mx:") or t.startswith("mx/") or t.startswith("exists:") or t == "ptr" or t.startswith("ptr:"):
            consultas += 1
    return consultas, vazias, problemas


def conferir_spf(resolver, dom, rel, rotulo="SPF"):
    regs = _spf_de(resolver, dom)
    if not regs:
        rel.add(rotulo, "falta", f"{dom} não tem registro SPF (TXT começando com v=spf1). Sem ele, Gmail, Yahoo e Microsoft tratam o envio como não autenticado.")
        return None
    if len(regs) > 1:
        rel.add(rotulo, "falta", f"{dom} tem {len(regs)} registros SPF; a RFC 7208 manda falhar (permerror). Junte num só.", " | ".join(regs))
        return regs[0]
    spf = regs[0]
    termos = [t.lower() for t in spf.split()[1:]]
    alls = [t for t in termos if t.lstrip("+-~?") == "all"]
    tem_redirect = any(t.startswith("redirect=") for t in termos)
    if not alls and not tem_redirect:
        rel.add(rotulo, "atencao", "SPF sem 'all' no fim: o resultado padrão é neutro. Termine com ~all ou -all.", spf)
    elif alls:
        q = alls[-1][0] if alls[-1][0] in "+-~?" else "+"
        if q == "+":
            rel.add(rotulo, "falta", "SPF termina em +all (ou 'all' sem sinal): qualquer servidor do mundo pode mandar como você. Use ~all ou -all.", spf)
        elif q == "?":
            rel.add(rotulo, "atencao", "SPF termina em ?all (neutro): não protege. Use ~all ou -all.", spf)
    if any(t.lstrip("+-~?").startswith("ptr") for t in termos):
        rel.add(rotulo, "atencao", "SPF usa 'ptr', que a RFC 7208 desaconselha (lento, e alguns receptores ignoram).", spf)
    try:
        consultas, vazias, problemas = contar_consultas_spf(resolver, dom)
    except ErroDNS as e:
        rel.add(rotulo, "erro", f"não deu para seguir os include do SPF: {e}", spf)
        return spf
    if consultas > 10:
        rel.add(rotulo, "falta", f"SPF faz {consultas} consultas de DNS (include, a, mx, ptr, exists, redirect); o limite é 10 (RFC 7208, 4.6.4) e passar dele dá permerror.", spf)
    if vazias > 2:
        rel.add(rotulo, "falta", f"SPF tem {vazias} consultas vazias (include que não existe); acima de 2 é permerror (RFC 7208, 4.6.4).", spf)
    for p in problemas:
        if "registros SPF" in p or "laço" in p:
            rel.add(rotulo, "falta", p, spf)
    if not any(i.item == rotulo and i.status in ("falta", "atencao") for i in rel.itens):
        rel.add(rotulo, "ok", f"um registro, termina em {alls[-1] if alls else 'redirect'}, {consultas} de 10 consultas.", spf)
    return spf


# ------------------------------------------------------------------ DKIM

def _der_len(b, i):
    n = b[i]
    i += 1
    if n < 0x80:
        return n, i
    k = n & 0x7F
    return int.from_bytes(b[i:i + k], "big"), i + k


def bits_rsa(p_b64):
    """Tamanho em bits da chave RSA no p= do DKIM (SubjectPublicKeyInfo ou RSAPublicKey cru). None se não der."""
    try:
        der = base64.b64decode(p_b64 + "=" * (-len(p_b64) % 4), validate=False)
    except Exception:
        return None

    def inteiro_modulo(b, i):
        # RSAPublicKey ::= SEQUENCE { modulus INTEGER, publicExponent INTEGER }
        if b[i] != 0x30:
            return None
        _, i = _der_len(b, i + 1)
        if b[i] != 0x02:
            return None
        n, i = _der_len(b, i + 1)
        mod = b[i:i + n].lstrip(b"\x00")
        return len(mod) * 8 - (8 - mod[0].bit_length()) if mod else None

    try:
        if der[0] != 0x30:
            return None
        _, i = _der_len(der, 1)
        if der[i] == 0x30:  # SubjectPublicKeyInfo: SEQUENCE { AlgorithmIdentifier, BIT STRING }
            alg_len, j = _der_len(der, i + 1)
            i = j + alg_len
            if der[i] != 0x03:
                return None
            _, i = _der_len(der, i + 1)
            return inteiro_modulo(der, i + 1)  # pula o byte de bits não usados
        return inteiro_modulo(der, 0)
    except (IndexError, ValueError):
        return None


def conferir_dkim(resolver, dom, seletores, rel):
    procurou_comuns = not seletores
    achou = 0
    for sel in seletores or SELETORES_COMUNS:
        nome = f"{sel}._domainkey.{dom}"
        try:
            regs = _txt(resolver, nome)
        except ErroDNS as e:
            rel.add(f"DKIM {sel}", "erro", str(e))
            continue
        regs = [r for r in regs if "p=" in r.lower()]
        if not regs:
            if not procurou_comuns:
                rel.add(f"DKIM {sel}", "falta", f"não há chave DKIM em {nome}. Publique a chave que o seu provedor de envio gerou para este seletor.")
            continue
        achou += 1
        if len(regs) > 1:
            rel.add(f"DKIM {sel}", "falta", f"{nome} tem {len(regs)} registros de chave; deixe um só.", " | ".join(r[:60] for r in regs))
            continue
        t = _tags(regs[0])
        k = t.get("k", "rsa").lower()
        p = t.get("p", "")
        resumo = regs[0][:90] + ("…" if len(regs[0]) > 90 else "")
        if not p:
            rel.add(f"DKIM {sel}", "falta", "p= vazio: a chave foi revogada. Publique a chave atual.", resumo)
            continue
        if "y" in t.get("t", "").split(":"):
            rel.add(f"DKIM {sel}", "atencao", "t=y (modo de teste): alguns receptores tratam a assinatura como não confiável. Tire o t=y quando estiver estável.", resumo)
        if k == "ed25519":
            rel.add(f"DKIM {sel}", "atencao", "chave ed25519: nem todo receptor valida; a RFC 8463 sugere assinar também com RSA.", resumo)
            continue
        bits = bits_rsa(p)
        if bits is None:
            rel.add(f"DKIM {sel}", "falta", "não consegui ler a chave RSA do p= (base64 quebrado ou cortado ao colar no DNS).", resumo)
        elif bits < 1024:
            rel.add(f"DKIM {sel}", "falta", f"chave RSA de {bits} bits: curta demais; Gmail e outros pedem pelo menos 1024 (o recomendado é 2048).", resumo)
        elif bits < 2048:
            rel.add(f"DKIM {sel}", "atencao", f"chave RSA de {bits} bits: aceita, mas o recomendado é 2048. Gere outra se o provedor deixar.", resumo)
        elif not any(i.item == f"DKIM {sel}" for i in rel.itens):
            rel.add(f"DKIM {sel}", "ok", f"chave RSA de {bits} bits.", resumo)
    if procurou_comuns and not achou:
        rel.add("DKIM", "atencao", "não achei DKIM nos seletores comuns. Rode de novo com --seletor <o do seu provedor> (ele aparece no cabeçalho DKIM-Signature, s=).")
    return achou


# ------------------------------------------------------------------ DMARC

def ler_dmarc(resolver, dom):
    """(nome_onde_achou, registros) procurando no próprio domínio e, se não houver, no organizacional."""
    nome = f"_dmarc.{dom}"
    regs = [t for t in _txt(resolver, nome) if t.strip().lower().replace(" ", "").startswith("v=dmarc1")]
    if regs:
        return nome, regs
    org = dominio_organizacional(dom)
    if org != dom:
        nome_org = f"_dmarc.{org}"
        regs = [t for t in _txt(resolver, nome_org) if t.strip().lower().replace(" ", "").startswith("v=dmarc1")]
        if regs:
            return nome_org, regs
    return nome, []


def conferir_dmarc(resolver, dom, rel):
    try:
        onde, regs = ler_dmarc(resolver, dom)
    except ErroDNS as e:
        rel.add("DMARC", "erro", str(e))
        return None
    if not regs:
        rel.add("DMARC", "falta", f"não há DMARC em _dmarc.{dom}. Gmail e Yahoo exigem DMARC de quem manda em volume; comece com v=DMARC1; p=none; rua=mailto:<caixa que lê relatório>.")
        return None
    if len(regs) > 1:
        rel.add("DMARC", "falta", f"{onde} tem {len(regs)} registros DMARC; o receptor ignora todos. Deixe um só.", " | ".join(regs))
        return None
    t = _tags(regs[0])
    herdado = not onde.startswith(f"_dmarc.{dom}")
    politica = (t.get("sp") if herdado and t.get("sp") else t.get("p", "")).lower()
    if politica not in ("none", "quarantine", "reject"):
        rel.add("DMARC", "falta", f"política inválida ou ausente (p={politica or 'vazio'}). Use p=none, quarantine ou reject.", regs[0])
        return t
    if herdado:
        rel.add("DMARC", "info", f"o DMARC vem do domínio organizacional ({onde}); a política que vale aqui é {'sp' if t.get('sp') else 'p'}={politica}.", regs[0])
    if politica == "none":
        rel.add("DMARC", "atencao", "p=none: só monitora. Serve para começar; depois de 2 a 4 semanas de relatório limpo, suba para p=quarantine (e só então pense em BIMI).", regs[0])
    try:
        pct = int(t.get("pct", "100"))
    except ValueError:
        pct = 100
    if pct < 100:
        rel.add("DMARC", "atencao", f"pct={pct}: a política só vale para parte das mensagens.", regs[0])
    if not t.get("rua"):
        rel.add("DMARC", "atencao", "sem rua=: você não recebe o relatório agregado e não vê quem manda pelo domínio.", regs[0])
    if politica in ("quarantine", "reject") and pct == 100 and t.get("rua"):
        rel.add("DMARC", "ok", f"p={politica}, pct=100, com relatório.", regs[0])
    elif politica == "none" and t.get("rua") and pct == 100:
        pass  # a atenção do p=none já diz o que fazer
    t["_politica"] = politica
    t["_pct"] = pct
    return t


# ------------------------------------------------------------------ MX, BIMI, alinhamento

def conferir_mx(resolver, dom, rel):
    try:
        mx = _mx(resolver, dom)
    except ErroDNS as e:
        rel.add("MX", "erro", str(e))
        return
    if not mx:
        rel.add("MX", "atencao", "o domínio não tem MX: resposta de prospect e aviso de devolução não chegam a lugar nenhum. Aponte o MX para a caixa que vai ler as respostas.")
    elif len(mx) == 1 and mx[0][1] in ("", "."):
        rel.add("MX", "falta", "MX nulo (0 .): o domínio declara que não recebe e-mail (RFC 7505), e receptores podem recusar mensagens dele.", "0 .")
    else:
        rel.add("MX", "ok", ", ".join(f"{p} {h}" for p, h in mx))


def conferir_bimi(resolver, dom, dmarc, rel):
    try:
        regs = [t for t in _txt(resolver, f"default._bimi.{dom}") if t.lower().replace(" ", "").startswith("v=bimi1")]
    except ErroDNS as e:
        rel.add("BIMI", "erro", str(e))
        return
    if not regs:
        rel.add("BIMI", "info", "sem BIMI (opcional). Só faz sentido com DMARC em quarantine ou reject e, no Gmail, com certificado VMC ou CMC.")
        return
    t = _tags(regs[0])
    problemas = []
    if not t.get("l", "").lower().startswith("https://") or not t.get("l", "").lower().endswith(".svg"):
        problemas.append("l= tem de ser um SVG em https")
    if not t.get("a"):
        problemas.append("sem a= (certificado VMC/CMC): o Gmail não mostra o logo sem ele")
    if not dmarc or dmarc.get("_politica") not in ("quarantine", "reject") or dmarc.get("_pct", 100) < 100:
        problemas.append("DMARC precisa estar em quarantine ou reject com pct=100")
    if problemas:
        rel.add("BIMI", "atencao", "; ".join(problemas) + ".", regs[0])
    else:
        rel.add("BIMI", "ok", "registro com logo SVG e certificado; DMARC aplicado.", regs[0])


def conferir_envelope(resolver, dom, envelope, rel):
    """O domínio do Return-Path (MAIL FROM) que a ferramenta de envio usa: SPF próprio e alinhamento relaxado."""
    if dominio_organizacional(envelope) != dominio_organizacional(dom):
        rel.add("Alinhamento", "falta", f"o Return-Path ({envelope}) é de outro domínio organizacional: o SPF passa, mas não alinha com o From ({dom}). Peça ao provedor um domínio de retorno personalizado em {dom}.")
    else:
        rel.add("Alinhamento", "ok", f"Return-Path {envelope} alinha (relaxado) com o From {dom}.")
    conferir_spf(resolver, envelope, rel, rotulo="SPF do Return-Path")


# ------------------------------------------------------------------ juntando

def dns_responde(resolver, controle="gmail.com"):
    """O DNS desta máquina responde de verdade? Rede que bloqueia DNS às vezes devolve NXDOMAIN para tudo,
    e aí o relatório diria FALTA em todos os itens. Confere um domínio que sem dúvida tem MX."""
    try:
        return bool(_mx(resolver, controle))
    except ErroDNS:
        return False


def conferir(dominio, seletores=None, bimi=False, envelope=None, resolver=None, controle="gmail.com"):
    dom = dominio.strip().lower().rstrip(".")
    r = resolver or dns.resolver.Resolver()
    rel = Relatorio(dom)
    if controle and not dns_responde(r, controle):
        rel.add("DNS", "erro", f"o DNS desta máquina não achou nem o MX de {controle}: a rede está bloqueando ou desviando DNS. Rode em outra rede (no PC) antes de acreditar em qualquer FALTA.")
        return rel
    try:
        conferir_spf(r, dom, rel)
    except ErroDNS as e:
        rel.add("SPF", "erro", str(e))
    conferir_dkim(r, dom, seletores or [], rel)
    dmarc = conferir_dmarc(r, dom, rel)
    conferir_mx(r, dom, rel)
    if bimi:
        conferir_bimi(r, dom, dmarc, rel)
    if envelope:
        try:
            conferir_envelope(r, dom, envelope.strip().lower().rstrip("."), rel)
        except ErroDNS as e:
            rel.add("Alinhamento", "erro", str(e))
    if not any(i.item.startswith("Alinhamento") for i in rel.itens):
        rel.add("Alinhamento", "info", "o DNS não mostra o alinhamento do DKIM (d=) nem do Return-Path. Mande um e-mail de teste para uma caixa Gmail e confira em 'Mostrar original': SPF, DKIM e DMARC têm de dizer PASS, e o DKIM com d= este domínio.")
    return rel


ROTULO = {"ok": "OK", "atencao": "ATENÇÃO", "falta": "FALTA", "erro": "ERRO", "info": "INFO"}


def imprimir(rel, saida=sys.stdout):
    print(f"Domínio: {rel.dominio}", file=saida)
    for i in rel.itens:
        print(f"  [{ROTULO[i.status]:<7}] {i.item}: {i.msg}", file=saida)
        if i.registro and i.status != "ok":
            print(f"            registro: {i.registro}", file=saida)
    if rel.falta:
        print(f"\nFalta corrigir {len(rel.falta)} item(ns) antes de mandar volume.", file=saida)
    else:
        print("\nNada falta no DNS. Confira o resto (aquecimento, conteúdo, descadastro) no plano.", file=saida)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Confere SPF, DKIM, DMARC, MX e BIMI de um domínio de envio.")
    ap.add_argument("dominio")
    ap.add_argument("--seletor", action="append", default=[], help="seletor DKIM (pode repetir)")
    ap.add_argument("--bimi", action="store_true", help="confere também o BIMI (opcional)")
    ap.add_argument("--envelope", help="domínio do Return-Path usado pela ferramenta de envio")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    rel = conferir(a.dominio, a.seletor, a.bimi, a.envelope)
    if a.json:
        print(json.dumps(rel.como_dict(), ensure_ascii=False, indent=2))
    else:
        imprimir(rel)
    return 1 if rel.falta else 0


if __name__ == "__main__":
    raise SystemExit(main())
