"""Testes offline do radar_temas com RSS de exemplo no formato do Google Trends e do Google News.
As manchetes abaixo são inventadas para o teste. Rodar: python -m pytest -q test_radar_temas.py"""
import datetime as dt

import radar_temas as rt

TRENDS = """<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:ht="https://trends.google.com/trending/rss" version="2.0"><channel>
<item><title>volta ao escritório</title><ht:approx_traffic>20.000+</ht:approx_traffic>
<pubDate>Wed, 14 Oct 2026 09:00:00 -0300</pubDate>
<ht:news_item><ht:news_item_title>Empresa X passa a exigir cinco dias presenciais</ht:news_item_title>
<ht:news_item_url>https://exemplo.com/a</ht:news_item_url><ht:news_item_source>Jornal A</ht:news_item_source></ht:news_item>
</item>
<item><title>final do campeonato</title><ht:approx_traffic>500.000+</ht:approx_traffic>
<pubDate>Wed, 14 Oct 2026 08:00:00 -0300</pubDate>
<ht:news_item><ht:news_item_title>Time vence a final com gol no fim</ht:news_item_title>
<ht:news_item_url>https://exemplo.com/b</ht:news_item_url><ht:news_item_source>Jornal B</ht:news_item_source></ht:news_item>
</item>
</channel></rss>"""

NEWS = """<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>
<item><title>Empresa X exige cinco dias presenciais e funcionários reclamam - Jornal C</title>
<link>https://exemplo.com/c</link><pubDate>Wed, 14 Oct 2026 10:00:00 GMT</pubDate><source url="https://c">Jornal C</source></item>
<item><title>Banco lucra recorde e demite 2 mil funcionários - Jornal D</title>
<link>https://exemplo.com/d</link><pubDate>Tue, 13 Oct 2026 10:00:00 GMT</pubDate><source url="https://d">Jornal D</source></item>
<item><title>Receita de bolo de cenoura - Jornal E</title>
<link>https://exemplo.com/e</link><pubDate>Tue, 13 Oct 2026 10:00:00 GMT</pubDate><source url="https://e">Jornal E</source></item>
</channel></rss>"""

AGORA = dt.datetime(2026, 10, 14, 12, 0, tzinfo=dt.timezone(dt.timedelta(hours=-3)))


def test_parse():
    t = rt.parse_trends(TRENDS)
    assert t[0].trafego == 20000 and t[0].fonte == "Google Trends · Jornal A"
    n = rt.parse_news(NEWS, "teste")
    assert n[0].titulo == "Empresa X exige cinco dias presenciais e funcionários reclamam" and n[0].fonte == "Jornal C"


def test_filtro_agrupamento_nota_e_digest():
    itens = rt.parse_trends(TRENDS) + rt.parse_news(NEWS, "teste")
    filtrados = [i for i in itens if rt.eh_tema_de_escritorio(i)]
    titulos = {i.titulo for i in filtrados}
    assert "final do campeonato" not in titulos and "Receita de bolo de cenoura" not in titulos
    temas = rt.agrupar(filtrados, limiar=0.15)
    assert len(temas) == 2  # presencial (Trends + Jornal C) e banco
    notas = {t.principal.fonte: rt.pontuar(t, AGORA) for t in temas}
    banco = notas["Jornal D"]
    assert "lucro e corte na mesma notícia" in "; ".join(banco[1])
    md = rt.digest(temas, AGORA, top=15)
    assert md.startswith("# Radar de temas · 2026-10-14") and "**Ângulo:**" in md


def test_tema_e_angulo_forcados(tmp_path):
    p = tmp_path / "c.json"
    p.write_text('[{"titulo": "Senado vota PEC da jornada", "link": "https://x", "fonte": "F", '
                 '"data": "2026-10-13T10:00:00-03:00", "tema": "PEC da jornada", "angulo": "Ângulo escrito à mão."}]',
                 encoding="utf-8")
    temas = rt.agrupar([i for i in rt.carregar_json(p) if rt.eh_tema_de_escritorio(i)])
    md = rt.digest(temas, AGORA)
    assert "## 1. PEC da jornada" in md and "Ângulo escrito à mão." in md
