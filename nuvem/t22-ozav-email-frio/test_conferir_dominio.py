"""Testes do conferir_dominio.py com um resolvedor falso: nenhuma consulta sai para a rede.

    pip install dnspython pytest
    python -m pytest -q test_conferir_dominio.py
"""
import base64
import io
import json

import dns.exception
import dns.resolver
import pytest

import conferir_dominio as cd

DOM = "prospeccao-exemplo.com.br"


# ------------------------------------------------------------------ o resolvedor falso

class TXT:
    def __init__(self, *partes):
        self.strings = tuple(p.encode() for p in partes)


class MX:
    def __init__(self, preference, exchange):
        self.preference = preference
        self.exchange = exchange


class Resolvedor:
    """{(nome, tipo): [registros]}; nome ausente = NXDOMAIN; 'TIMEOUT' = dns.exception.Timeout."""

    def __init__(self, zona):
        self.zona = zona
        self.perguntas = []

    def resolve(self, nome, tipo):
        self.perguntas.append((nome, tipo))
        v = self.zona.get((nome, tipo))
        if v == "TIMEOUT":
            raise dns.exception.Timeout()
        if v is None:
            if any(n == nome for n, _ in self.zona):
                raise dns.resolver.NoAnswer()
            raise dns.resolver.NXDOMAIN()
        return v


def der_len(n):
    if n < 0x80:
        return bytes([n])
    b = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(b)]) + b


def chave_rsa(bits):
    """Uma SubjectPublicKeyInfo RSA com módulo de `bits` bits (não é chave de verdade: só o formato)."""
    modulo = b"\x00" + (b"\xc3" + b"\x5a" * (bits // 8 - 1))
    expo = b"\x01\x00\x01"
    rsa = b"\x02" + der_len(len(modulo)) + modulo + b"\x02" + der_len(len(expo)) + expo
    rsa = b"\x30" + der_len(len(rsa)) + rsa
    alg = bytes.fromhex("300d06092a864886f70d0101010500")
    bitstr = b"\x03" + der_len(len(rsa) + 1) + b"\x00" + rsa
    spki = alg + bitstr
    return base64.b64encode(b"\x30" + der_len(len(spki)) + spki).decode()


def zona_completa(troca=None):
    z = {
        (DOM, "TXT"): [TXT("v=spf1 include:_spf.google.com ~all"), TXT("google-site-verification=abc")],
        ("_spf.google.com", "TXT"): [TXT("v=spf1 include:_netblocks.google.com include:_netblocks2.google.com ~all")],
        ("_netblocks.google.com", "TXT"): [TXT("v=spf1 ip4:35.190.247.0/24 ~all")],
        ("_netblocks2.google.com", "TXT"): [TXT("v=spf1 ip6:2001:4860:4000::/36 ~all")],
        (f"google._domainkey.{DOM}", "TXT"): [TXT("v=DKIM1; k=rsa; p=" + chave_rsa(2048)[:200], chave_rsa(2048)[200:])],
        (f"_dmarc.{DOM}", "TXT"): [TXT("v=DMARC1; p=quarantine; rua=mailto:dmarc@" + DOM + "; pct=100")],
        (DOM, "MX"): [MX(1, "smtp.google.com.")],
        ("gmail.com", "MX"): [MX(5, "gmail-smtp-in.l.google.com.")],
    }
    z.update(troca or {})
    return {k: v for k, v in z.items() if v is not None}


def rodar(zona, **kw):
    return cd.conferir(DOM, resolver=Resolvedor(zona), **kw)


def status(rel, item):
    return [i.status for i in rel.itens if i.item == item]


# ------------------------------------------------------------------ os casos

def test_dominio_completo_passa_sem_falta():
    rel = rodar(zona_completa(), seletores=["google"])
    assert rel.falta == []
    assert status(rel, "SPF") == ["ok"]
    assert status(rel, "DKIM google") == ["ok"]
    assert status(rel, "DMARC") == ["ok"]
    assert status(rel, "MX") == ["ok"]


def test_chave_dividida_em_partes_do_txt_e_juntada():
    rel = rodar(zona_completa(), seletores=["google"])
    assert "2048 bits" in [i.msg for i in rel.itens if i.item == "DKIM google"][0]


def test_sem_dmarc_falta():
    rel = rodar(zona_completa({(f"_dmarc.{DOM}", "TXT"): None}), seletores=["google"])
    assert status(rel, "DMARC") == ["falta"]
    assert rel.falta


def test_dmarc_p_none_e_atencao_nao_falta():
    rel = rodar(zona_completa({(f"_dmarc.{DOM}", "TXT"): [TXT("v=DMARC1; p=none; rua=mailto:x@" + DOM)]}), seletores=["google"])
    assert status(rel, "DMARC") == ["atencao"]
    assert not rel.falta


def test_dois_dmarc_falta():
    z = zona_completa({(f"_dmarc.{DOM}", "TXT"): [TXT("v=DMARC1; p=none"), TXT("v=DMARC1; p=reject")]})
    assert status(rodar(z, seletores=["google"]), "DMARC") == ["falta"]


def test_dmarc_sem_rua_e_pct_parcial_avisam():
    z = zona_completa({(f"_dmarc.{DOM}", "TXT"): [TXT("v=DMARC1; p=reject; pct=50")]})
    msgs = [i.msg for i in rodar(z, seletores=["google"]).itens if i.item == "DMARC"]
    assert any("pct=50" in m for m in msgs) and any("rua" in m for m in msgs)


def test_subdominio_herda_dmarc_do_organizacional_pelo_sp():
    sub = "envio." + DOM
    z = {
        (sub, "TXT"): [TXT("v=spf1 include:mailgun.org -all")],
        ("mailgun.org", "TXT"): [TXT("v=spf1 ip4:198.51.100.0/24 -all")],
        (f"_dmarc.{DOM}", "TXT"): [TXT("v=DMARC1; p=reject; sp=none; rua=mailto:x@" + DOM)],
        (sub, "MX"): [MX(10, "mxa.mailgun.org.")],
    }
    rel = cd.conferir(sub, resolver=Resolvedor(z), seletores=[], controle=None)
    dm = [(i.status, i.msg) for i in rel.itens if i.item == "DMARC"]
    assert ("info" in [s for s, _ in dm]) and any("sp=none" in m for _, m in dm)
    assert "atencao" in [s for s, _ in dm]


def test_dominio_organizacional_com_br():
    assert cd.dominio_organizacional("a.b.prospeccao-exemplo.com.br") == "prospeccao-exemplo.com.br"
    assert cd.dominio_organizacional("mail.exemplo.com") == "exemplo.com"


def test_dois_spf_falta():
    z = zona_completa({(DOM, "TXT"): [TXT("v=spf1 include:_spf.google.com ~all"), TXT("v=spf1 -all")]})
    assert "falta" in status(rodar(z, seletores=["google"]), "SPF")


def test_spf_mais_all_falta_e_interrogacao_avisa():
    z = zona_completa({(DOM, "TXT"): [TXT("v=spf1 ip4:203.0.113.5 +all")]})
    assert "falta" in status(rodar(z, seletores=["google"]), "SPF")
    z = zona_completa({(DOM, "TXT"): [TXT("v=spf1 ip4:203.0.113.5 ?all")]})
    assert "atencao" in status(rodar(z, seletores=["google"]), "SPF")


def test_spf_sem_registro_falta():
    z = zona_completa({(DOM, "TXT"): [TXT("google-site-verification=abc")]})
    assert status(rodar(z, seletores=["google"]), "SPF") == ["falta"]


def test_spf_acima_de_10_consultas_falta():
    incs = " ".join(f"include:i{n}.exemplo.net" for n in range(11))
    z = zona_completa({(DOM, "TXT"): [TXT(f"v=spf1 {incs} -all")]})
    for n in range(11):
        z[(f"i{n}.exemplo.net", "TXT")] = [TXT("v=spf1 ip4:192.0.2.1 -all")]
    msgs = [i.msg for i in rodar(z, seletores=["google"]).itens if i.item == "SPF" and i.status == "falta"]
    assert any("11 consultas" in m for m in msgs)


def test_spf_conta_include_aninhado():
    c, v, _ = cd.contar_consultas_spf(Resolvedor(zona_completa()), DOM)
    assert (c, v) == (3, 0)  # include:_spf.google.com + os dois _netblocks


def test_spf_include_inexistente_conta_como_vazia():
    incs = "include:nao1.exemplo.net include:nao2.exemplo.net include:nao3.exemplo.net"
    z = zona_completa({(DOM, "TXT"): [TXT(f"v=spf1 {incs} -all")]})
    msgs = [i.msg for i in rodar(z, seletores=["google"]).itens if i.status == "falta"]
    assert any("consultas vazias" in m for m in msgs)


def test_spf_laco_de_include_nao_trava():
    z = {("a.exemplo.net", "TXT"): [TXT("v=spf1 include:b.exemplo.net -all")], ("b.exemplo.net", "TXT"): [TXT("v=spf1 include:a.exemplo.net -all")]}
    _, _, probs = cd.contar_consultas_spf(Resolvedor(z), "a.exemplo.net")
    assert any("laço" in p for p in probs)


@pytest.mark.parametrize("bits,esperado", [(512, "falta"), (1024, "atencao"), (2048, "ok"), (4096, "ok")])
def test_tamanho_da_chave_dkim(bits, esperado):
    z = zona_completa({(f"google._domainkey.{DOM}", "TXT"): [TXT("v=DKIM1; k=rsa; p=" + chave_rsa(bits))]})
    assert status(rodar(z, seletores=["google"]), "DKIM google") == [esperado]


def test_bits_rsa_le_chave_crua_e_spki():
    assert cd.bits_rsa(chave_rsa(2048)) == 2048
    assert cd.bits_rsa("nao-e-base64!!") is None


def test_dkim_revogado_falta():
    z = zona_completa({(f"google._domainkey.{DOM}", "TXT"): [TXT("v=DKIM1; k=rsa; p=")]})
    assert status(rodar(z, seletores=["google"]), "DKIM google") == ["falta"]


def test_dkim_seletor_pedido_e_ausente_falta():
    assert status(rodar(zona_completa(), seletores=["s1"]), "DKIM s1") == ["falta"]


def test_sem_seletor_procura_os_comuns():
    r = Resolvedor(zona_completa())
    rel = cd.conferir(DOM, resolver=r)
    assert status(rel, "DKIM google") == ["ok"]
    assert (f"selector1._domainkey.{DOM}", "TXT") in r.perguntas


def test_sem_seletor_e_sem_chave_avisa_para_informar():
    z = zona_completa({(f"google._domainkey.{DOM}", "TXT"): None})
    assert status(cd.conferir(DOM, resolver=Resolvedor(z)), "DKIM") == ["atencao"]


def test_dkim_modo_teste_avisa():
    z = zona_completa({(f"google._domainkey.{DOM}", "TXT"): [TXT("v=DKIM1; t=y; k=rsa; p=" + chave_rsa(2048))]})
    assert "atencao" in status(rodar(z, seletores=["google"]), "DKIM google")


def test_mx_ausente_avisa_e_mx_nulo_falta():
    z = zona_completa({(DOM, "MX"): None})
    assert status(rodar(z, seletores=["google"]), "MX") == ["atencao"]
    z = zona_completa({(DOM, "MX"): [MX(0, ".")]})
    assert status(rodar(z, seletores=["google"]), "MX") == ["falta"]


def test_timeout_e_erro_e_nao_falta_inventada():
    z = zona_completa({(f"_dmarc.{DOM}", "TXT"): "TIMEOUT"})
    rel = rodar(z, seletores=["google"])
    assert status(rel, "DMARC") == ["erro"]


def test_bimi_com_dmarc_none_avisa():
    z = zona_completa({
        (f"_dmarc.{DOM}", "TXT"): [TXT("v=DMARC1; p=none; rua=mailto:x@" + DOM)],
        (f"default._bimi.{DOM}", "TXT"): [TXT("v=BIMI1; l=https://exemplo.com.br/logo.svg; a=https://exemplo.com.br/vmc.pem")],
    })
    msgs = [i.msg for i in rodar(z, seletores=["google"], bimi=True).itens if i.item == "BIMI"]
    assert msgs and "quarantine" in msgs[0]


def test_bimi_completo_ok_e_ausente_e_info():
    z = zona_completa({(f"default._bimi.{DOM}", "TXT"): [TXT("v=BIMI1; l=https://exemplo.com.br/logo.svg; a=https://exemplo.com.br/vmc.pem")]})
    assert status(rodar(z, seletores=["google"], bimi=True), "BIMI") == ["ok"]
    assert status(rodar(zona_completa(), seletores=["google"], bimi=True), "BIMI") == ["info"]


def test_envelope_de_outro_dominio_nao_alinha():
    z = zona_completa({("bounce.ferramenta-exemplo.net", "TXT"): [TXT("v=spf1 ip4:192.0.2.0/24 -all")]})
    rel = rodar(z, seletores=["google"], envelope="bounce.ferramenta-exemplo.net")
    assert status(rel, "Alinhamento") == ["falta"]
    z = zona_completa({(f"bounce.{DOM}", "TXT"): [TXT("v=spf1 include:_spf.google.com ~all")]})
    rel = rodar(z, seletores=["google"], envelope=f"bounce.{DOM}")
    assert status(rel, "Alinhamento") == ["ok"]


def test_saida_json_e_codigo_de_saida(monkeypatch, capsys):
    monkeypatch.setattr(cd.dns.resolver, "Resolver", lambda: Resolvedor(zona_completa({(f"_dmarc.{DOM}", "TXT"): None})))
    assert cd.main([DOM, "--seletor", "google", "--json"]) == 1
    j = json.loads(capsys.readouterr().out)
    assert j["ok"] is False and any(i["item"] == "DMARC" and i["status"] == "falta" for i in j["itens"])


def test_texto_legivel():
    buf = io.StringIO()
    cd.imprimir(rodar(zona_completa(), seletores=["google"]), buf)
    assert "Nada falta no DNS" in buf.getvalue()


def test_rede_que_desvia_dns_vira_erro_e_nao_falta_em_tudo():
    # Nesta nuvem o DNS devolve NXDOMAIN até para gmail.com: o relatório não pode culpar o domínio.
    rel = cd.conferir(DOM, resolver=Resolvedor({}), seletores=["google"])
    assert [i.item for i in rel.itens] == ["DNS"] and rel.itens[0].status == "erro"
