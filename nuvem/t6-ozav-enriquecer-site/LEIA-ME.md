# Ozav · enriquecer site da lista

`enriquecer_site.py` lê o `top1000.csv` da lista quente CNPJ (tarefas 1 e 5) e visita o site das
empresas com domínio de e-mail próprio (`marca_email = próprio`). De cada site lê a home e até 3
páginas internas óbvias e extrai, **sem IA**, só com regras fixas:

| Coluna | O que é |
|---|---|
| `status_site`, `site`, `redireciona_para` | se deu para ler, a URL final da home e o domínio de destino quando a home manda para outro domínio (ex.: o site global da matriz) |
| `paginas`, `paginas_lidas`, `texto_chars` | quais páginas foram lidas (home, contato, sobre, carreiras, equipe) e quanto texto havia |
| `emails_funcao`, `emails_funcao_outros_dominios` | e-mails de função publicados (contato@, comercial@, financeiro@...), do domínio do site e de outros domínios |
| `n_emails_pessoais_descartados` | quantos e-mails que podem ser de pessoa (joao.silva@) foram vistos e descartados |
| `telefones_br`, `telefones_exterior` | telefones validados pela biblioteca `phonenumbers`, no formato internacional |
| `linkedin_empresa` | link da página da empresa no LinkedIn (`/company/`, `/showcase/`, `/school/`); o LinkedIn não é visitado |
| `plataforma_vagas` | Gupy, Vagas.com, Workday, LinkedIn Vagas etc., quando o site linka para uma |
| `sinal_importa`, `sinal_exporta`, `sinal_comex` | menção a importação, exportação e termos de comércio exterior |
| `sinal_matriz_exterior`, `matriz_em` | matriz, sede ou "headquartered in" num lugar do exterior, ou "subsidiária brasileira", "subsidiary of"... |
| `escritorios`, `escritorio_exterior` | lugares citados depois de "escritórios em", "offices in", "filiais em"... |
| `sinal_global`, `sinal_clientes_exterior`, `menciona_cambio` | "global", "em 12 países", "clientes no exterior", câmbio, dólar, pagamentos internacionais |
| `vagas_alvo` | cargos de comex, finanças, tesouraria, fiscal ou supply chain, **só da página de carreiras** |
| `idioma`, `lang_html`, `hreflangs` | idioma pelo texto (pt, en, es ou indefinido), o `lang` do HTML e as versões de idioma declaradas |
| `n_sinais`, `evidencias` | soma dos sinais e os termos fixos que dispararam cada um |

O `enriquecido.csv` tem todas as linhas da entrada, na mesma ordem e com as mesmas colunas, mais as
colunas acima. Empresa sem domínio próprio sai com `status_site` "não visitado: domínio genérico ou
de contador" ou "sem e-mail cadastral". O `relatorio.md` traz a cobertura, os status, a frequência de
cada sinal, as 25 empresas com mais sinais e os domínios que o robots.txt bloqueou.

## Como rodar no PC

```bash
pip install requests selectolax phonenumbers
python enriquecer_site.py C:/Users/loren/ozav-cnpj/saida/2026-10/top1000.csv --limite 20   # teste curto
python enriquecer_site.py C:/Users/loren/ozav-cnpj/saida/2026-10/top1000.csv              # tudo
python -m pytest -q        # 9 testes; o 10º (motor crawl4ai) roda só com ENRIQUECER_CDP_URL
```

Grava `enriquecido.csv`, `relatorio.md` e `cache_sites.jsonl` na pasta do `top1000.csv` (ou em
`--saida`). Se a rodada cair no meio, rode de novo o mesmo comando: os domínios que já estão no
cache não são visitados outra vez (`--refazer` ignora o cache). O cache guarda só o resultado já
filtrado, nunca o HTML.

Tempo: com 1 requisição por segundo por domínio, cada site leva de 5 a 8 s (robots.txt, home, até 3
páginas e às vezes um redirecionamento). Com `--workers 6` (padrão), 500 domínios levam por volta de
10 a 15 minutos no motor leve. É uma estimativa por conta, não foi medida em sites reais.

## Motor: Crawl4AI ou leve

A tarefa pedia o Crawl4AI como biblioteca se ele coubesse em 4 GB. Medi nesta sessão, em
14/10/2026, com Crawl4AI 0.9.4 (Playwright 1.64) ligado a um Chromium headless por CDP, num site
sintético local de 4 páginas:

| Motor | Pico de memória (soma do RSS de todos os processos) | Tempo por página | JavaScript |
|---|---|---|---|
| crawl4ai | ~1.190 MB (40 páginas) | 0,26 s, sem espera entre páginas | renderiza |
| leve (requests + selectolax) | 57 MB (40 páginas) | 40 páginas em 5 s, com espera de 0,05 s no teste (no uso real a espera é de 1 s) | não |

A soma do RSS conta duas vezes a memória que os processos do Chrome dividem, então o número real é
menor. **Cabe em 4 GB.** Por isso o padrão (`--motor auto`) usa o Crawl4AI quando ele está instalado e
o motor leve quando não está. Site real pesa mais que o sintético; a folga é grande, mas o número em
site real não foi medido.

```bash
pip install crawl4ai && crawl4ai-setup      # instala o Chromium do Playwright (o pacote ocupou 832 MB aqui)
python enriquecer_site.py top1000.csv --motor crawl4ai --workers 2
# ou, com um Chrome já aberto em modo de depuração:
python enriquecer_site.py top1000.csv --motor crawl4ai --cdp-url http://127.0.0.1:9222
```

Nos dois motores, o robots.txt, o ritmo, o teto de páginas e a extração são do nosso código; o
Crawl4AI só busca e renderiza a página. Duas diferenças do motor crawl4ai:
- O navegador segue redirecionamentos sozinho. O coletor confere o robots.txt do destino e descarta
  o conteúdo se o destino for proibido; no motor leve cada redirecionamento é conferido antes de ser
  seguido.
- O Crawl4AI 0.9 marca como "bloqueado por anti-bot" uma página legítima curta (menos de 50
  caracteres visíveis em menos de 5 KB, como uma página de contato simples). O HTML continua no
  resultado, então o coletor usa a página quando ela veio com HTTP 200.

## Regras de coleta

- **robots.txt** de cada host, pela biblioteca padrão (`urllib.robotparser`), com o user-agent
  `OzavSiteEnricher`. Segue a RFC 9309: 4xx = pode tudo; 5xx = não pode nada ("robots.txt
  inacessível"); sem conexão = "sem resposta". Vale o `Crawl-delay`, até 30 s.
- **Ritmo:** no máximo 1 requisição por segundo por domínio (`www.` e sem `www.` contam como o mesmo),
  entre todas as threads. O robots.txt e cada redirecionamento contam como requisição.
- **Teto:** 4 páginas por site (home + 3), 2 MB por página, só HTML, até 5 redirecionamentos.
- **Ordem da home:** `https://dominio/`, `https://www.dominio/`, `http://dominio/`, `http://www.dominio/`.
- **Páginas internas:** uma de cada, nesta ordem: contato, sobre, carreiras e equipe. Escolhe pelo
  caminho da URL e depois pelo texto do link, só no mesmo domínio, e pula PDF, imagem e arquivos.

## Privacidade

- E-mail só entra se **todo** pedaço do nome antes do @ for palavra de função ou neutra (contato,
  financeiro, rh, sp, br...). `joao.silva@`, `maria.financeiro@` e `ana@` são descartados e só contados.
- Perfil pessoal do LinkedIn (`/in/`) é ignorado; o LinkedIn nunca é visitado.
- O texto do site não vai para a saída. `evidencias` traz só os termos fixos que dispararam cada sinal,
  `escritorios` e `matriz_em` só mostram nomes de uma lista fechada de países e cidades (e a janela de
  busca para antes de "liderado por", "com", "que"...), e `vagas_alvo` só lê a página de carreiras.
- O teste de ponta a ponta confere byte a byte que nenhum nome de pessoa, e-mail pessoal ou link
  `/in/` do site sintético aparece no `enriquecido.csv`, no `relatorio.md` ou no cache.
- Telefone publicado pela empresa entra. Num site pequeno ele pode ser o celular do dono; ele vai sem
  nome, mas trate como dado de contato comercial (LGPD: uso legítimo, com opção de sair).

## Limitações

- Nada foi rodado contra sites reais: o `top1000.csv` real ainda não existe (a base da Receita estava
  baixando no PC) e a rede desta nuvem bloqueia a maior parte dos domínios. Os testes usam sites
  sintéticos (transporte falso com relógio falso) e um servidor HTTP local de verdade.
- As regras são simples de propósito: "global" pega muito falso positivo; "importação"/"exportação"
  ignoram "de dados, relatórios, planilhas, XML..." mas outros usos de software podem escapar; a lista
  de lugares é fechada (cidade fora dela não aparece; Lima ficou de fora porque é sobrenome comum).
- No motor leve, site feito só em JavaScript sai como "ok, pouco texto (site em JavaScript?)".
- Plataforma de vagas externa (Gupy etc.) é só registrada, não é visitada.
- O `urllib.robotparser` aplica a primeira regra que casa, não a mais específica como manda a RFC
  9309. Em robots.txt com Allow e Disallow sobrepostos ele pode ser mais restritivo ou mais
  permissivo que o esperado.
