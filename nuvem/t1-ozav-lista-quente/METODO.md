# Ozav · lista quente CNPJ · método

Pipeline que lê os Dados Abertos do CNPJ da Receita Federal e devolve as empresas com mais
chance de pagar ou receber do exterior todo mês. A hipótese testada é que a filial ou
subsidiária de empresa estrangeira (sócio pessoa jurídica no exterior) faz remessa intercompany
o tempo todo.

## 1. Fonte

| Item | Valor | Status |
|---|---|---|
| Endereço oficial (pastas mensais `AAAA-MM/`) | `https://arquivos.receitafederal.gov.br/dados/cnpj/dados_abertos_cnpj/` | Endereço confirmado pelo índice do buscador. Acesso direto bloqueado nesta sessão. |
| Endereço antigo (o pipeline tenta como reserva) | `https://dadosabertos.rfb.gov.br/CNPJ/dados_abertos_cnpj/` | Não verificado |
| Página do conjunto no portal federal | `https://dados.gov.br/dados/conjuntos-dados/cadastro-nacional-da-pessoa-juridica---cnpj` | Não verificado |
| Dicionário de dados (layout) | `https://www.gov.br/receitafederal/dados/cnpj-metadados.pdf` | O layout usado no código é o descrito nesse PDF. Não verificado nesta sessão. |
| Última publicação | **Não verificado.** A cópia do índice no buscador mostrava a pasta `2026-01/` (modificada em 2026-01-11) e um `cnpj.tar.gz` de cerca de 60 GB (2026-01-27). Essa cópia é antiga; a publicação mensal atual (provavelmente 2026-09 ou 2026-10) não pôde ser conferida. | Pendente |
| Regime tributário (lucro real/presumido por ano) | O pipeline tenta `https://arquivos.receitafederal.gov.br/dados/cnpj/regime_tributario/` (opção `--regime`) | **Não verificado.** Endereço e layout não confirmados; o código procura as colunas pelo nome e, se falhar, segue sem regime. |

Por que não há resultado real: a política de rede desta sessão de nuvem recusou (HTTP 403 no
proxy) `arquivos.receitafederal.gov.br`, `dadosabertos.rfb.gov.br`, `www.gov.br` e `dados.gov.br`.
Também não há espelho confiável e atual que seja alcançável daqui: o bucket público da Base dos
Dados (`storage.googleapis.com/basedosdados-public`) só tem o dicionário do CNPJ (2024-07-18); a
tabela em si está no BigQuery, que exige login e projeto de cobrança, e isso as regras proíbem.

Mudanças de 2026 que o código já trata (vistas em fontes secundárias, **não verificado** no texto
oficial):
- CNPJ alfanumérico para novas inscrições a partir de julho de 2026 (IN RFB nº 2.229/2024). O
  pipeline trata CNPJ sempre como texto e aceita letras no CNPJ do sócio PJ.
- Relato de troca de codificação após uma migração em fevereiro de 2026 (arquivo com BOM
  UTF-16). O pipeline detecta a codificação de cada CSV (BOM UTF-8, BOM UTF-16, UTF-8 ou latin-1)
  e converte UTF-16 para UTF-8 antes de ler.

## 2. Como rodar (no PC)

Requisitos: Python 3.10+, `pip install duckdb requests`, cerca de 10 GB livres (o pico é um zip
mais o CSV extraído; o maior, `Estabelecimentos0.zip`, é bem maior que os outros) e conexão com o
servidor da Receita, que costuma ser lento.

```bash
python pipeline.py rodar                    # descobre a pasta AAAA-MM mais recente e roda tudo
python pipeline.py rodar --mes 2026-10      # um mês específico
python pipeline.py rodar --regime           # tenta usar a base de lucro real
python pipeline.py rodar --fonte-local ~/Downloads/cnpj_2026-10 --mes 2026-10   # zips baixados pelo navegador
python pipeline.py pontuar --mes 2026-10    # refaz só a nota (ex.: depois de mudar cnae_alvo.csv)
python -m pytest -q test_pipeline.py        # teste de ponta a ponta com dados sintéticos
```

Ordem de processamento (um arquivo por vez: baixa → extrai → filtra para `.parquet` → apaga):
1. Tabelas auxiliares (Cnaes, Naturezas, Qualificacoes, Paises, Municipios, Motivos).
2. `Socios0..9`: guarda só os vínculos com estrangeiro. Para PJ estrangeira guarda o nome da
   empresa; para PF só guarda tipo e país, nunca o nome. Guarda também a aresta
   empresa → holding brasileira (só CNPJs), para achar controle estrangeiro indireto.
3. `Empresas0..9`: só as empresas do universo acima mais as de natureza "estabelecimento no Brasil
   de sociedade estrangeira".
4. `Simples.zip`: quem é optante do Simples ou MEI dentro do universo.
5. `Estabelecimentos0..9`: estabelecimentos do universo (para matriz, filiais e diff) e a contagem
   de empresas ativas por domínio de e-mail, sobre a base inteira (para achar contador). Do
   e-mail só se guarda o domínio.
6. Nota e saídas: `top1000.csv`, `contagens.csv`, `base_pontuada.parquet`.

Saída em `saida/<AAAA-MM>/`. Os `.parquet` que ficam (alguns MB) são o que o diff usa.

## 3. Filtros

- Estabelecimento **matriz** (`identificador_matriz_filial = 1`) com situação **ativa** (`2`).
- **Fora do Simples e do MEI** (arquivo Simples, opção atual = "S" exclui).
- **Pelo menos um vínculo estrangeiro**, em ordem de força:
  1. **PJ estrangeira direta**: qualificação com "Pessoa Jurídica … Exterior" (ex.: "Sócio Pessoa
     Jurídica Domiciliado no Exterior"), ou sócio PJ com país diferente de Brasil, ou sócio
     estrangeiro com sufixo societário forte no nome (LTD, LLC, INC, GMBH, B.V., PLC…). "SA"
     solto não conta, porque Sá é sobrenome.
  2. **Filial de sociedade estrangeira**: natureza jurídica cuja descrição oficial contém
     "Sociedade Estrangeira" ou "Empresa Binacional".
  3. **PJ estrangeira via holding brasileira**: o sócio é uma PJ brasileira que tem sócio PJ estrangeiro.
  4. **Estrangeiro sem tipo identificado**: vale menos que PJ e mais que PF.
  5. **PF estrangeira**: sócio ou administrador pessoa física no exterior, ou com país estrangeiro.
- **CNAE principal** na lista-alvo `cnae_alvo.csv` (prefixo; vale o prefixo mais longo).
- **Capital social ≥ R$ 100 mil.**
- **Natureza jurídica** de entidade empresarial (código começando com 2), excluídas pela descrição
  oficial: empresa pública, sociedade de economia mista, entidade domiciliada no exterior,
  fundo, clube, cooperativa, consórcio, grupo de sociedades, empresário individual e sociedade em
  conta de participação. Órgão público (código 1xxx), entidade sem fins lucrativos (3xxx), pessoa
  física (4xxx) e organização internacional (5xxx) ficam todos de fora.
- **Exclusão de bancos, corretoras, instituições de pagamento e concorrentes de câmbio/pagamentos**:
  CNAE principal **ou qualquer secundário** nas divisões 64, 65 ou 66 (serviços financeiros,
  seguros e auxiliares: banco, corretora de câmbio, IP, correspondente) e razão social ou nome
  fantasia com BANCO, BANK, CAMBIO, EXCHANGE, FOREX, PAGAMENTO(S), PAYMENT(S), PAY, REMESSA,
  CORRETORA, DTVM, CTVM, FINTECH, CRIPTO/CRYPTO, BITCOIN, BLOCKCHAIN, STABLECOIN ou SECURITIZADORA.

## 4. Lista-alvo de CNAE (resumo; detalhe e justificativa em `cnae_alvo.csv`)

| Grupo | Prefixos | Peso | Por quê |
|---|---|---|---|
| Software e TI, SaaS e plataformas | 62, 631 | 1,00 | Licença, royalty e serviço intercompany; nuvem paga no exterior; exportação de serviço. |
| Logística internacional | 5250 · 5232 · 5011 · 5120 | 1,00 · 0,90 · 0,70 · 0,60 | O agente de carga paga o agente do exterior a cada embarque. É o perfil de maior frequência. |
| Trading, representação e atacado importador | 461, 4693, 4651, 4652 (0,90); 466, 4644, 4645 (0,85); 4684 (0,80); 464, 4689 (0,75); 4692 (0,70); 4691 (0,65); 462 (0,60) | 0,60–0,90 | Pagamento a fornecedor estrangeiro e comissão recebida de fabricante. |
| Agência e publicidade | 7311, 7312 (0,85); 7319 (0,80); 7320 (0,70) | 0,70–0,85 | Compra de mídia em plataforma estrangeira; repasse para a matriz. |
| Consultoria e intangíveis | 7020, 7490104, 7740 (0,80); 7210 (0,60); 7112 (0,50) | 0,50–0,80 | Honorários intercompany, royalties e P&D para patrocinador estrangeiro. |
| Serviços exportados | 8220 (0,60); 8211 (0,50) | 0,50–0,60 | Centrais e BPO que atendem a matriz e recebem do exterior. |
| Educação, games e conteúdo | 5913 (0,70); 5911, 5920, 8599, 8593, 8550 (0,60) | 0,60–0,70 | Licença de conteúdo e plataforma; franquia estrangeira. Desenvolvedora de games costuma estar no 62. |
| E-commerce e varejo importado | 4781, 4751 (0,60/0,55); 4789, 4772 (0,50) | 0,50–0,60 | Não existe CNAE próprio para e-commerce; estes são os códigos mais comuns em cross-border. |
| Turismo | 7911, 7912 | 0,50 | Pagam hotel e receptivo no exterior. |

Ficam de fora de propósito: holdings (6462/6463), que não operam; apostas (9200), que são
reguladas à parte; e todo o setor financeiro. Para mudar a lista, edite `cnae_alvo.csv` e rode
`pontuar`.

## 5. Nota (0 a 100)

| Componente | Pontos | Regra |
|---|---|---|
| Vínculo estrangeiro | até 30 | PJ estrangeira direta ou filial de sociedade estrangeira = 30; PJ estrangeira via holding BR = 24; estrangeiro de tipo não identificado = 18; PF sócio = 12; PF só administrador = 8 |
| CNAE | até 25 | 25 × peso do CNAE (0,50 a 1,00) |
| Capital social | até 20 | escala logarítmica: R$ 100 mil = 0, R$ 1 mi ≈ 6,7, R$ 10 mi ≈ 13,3, R$ 100 mi ou mais = 20 |
| Porte / regime | até 10 | lucro real no último ano disponível ou porte "Demais" = 10; EPP = 4; ME = 2; não informado = 3 |
| Idade (data de início da matriz) | até 10 | menos de 1 ano = 6; 1 a 3 anos = 10 (a subsidiária acabou de chegar e ainda está escolhendo fornecedor de câmbio); 3 a 10 = 8; 10 a 20 = 6; mais de 20 = 4 (relação com banco já consolidada) |
| Filiais ativas | até 5 | 5 ou mais estabelecimentos ativos = 5; 2 a 4 = 3; só a matriz = 0 |

Desempate: capital social maior primeiro. Os pesos estão no SQL de `Pipeline.pontuar` e podem ser
ajustados depois que o time comercial disser quais contas fecharam.

**E-mail.** A coluna `dominio_email` traz só o domínio do e-mail cadastral da matriz. A coluna
`marca_email` diz "provável contador (domínio genérico)" quando é Gmail, Hotmail, Outlook, UOL,
BOL, Terra etc., e "provável contador (domínio em N empresas)" quando o domínio aparece em 20 ou
mais empresas ativas da base inteira (limiar `LIMIAR_DOMINIO_REPETIDO`). Um grupo grande com
muitos CNPJs também cai nessa marca; olhe o domínio antes de descartar.

## 6. Rotina mensal e diff

A Receita publica uma pasta nova por mês. A data exata de publicação não foi verificada; por
isso, agende o pipeline para rodar toda semana. Se a pasta do mês já foi processada, basta não
rodar de novo.

```bash
# Linux/macOS (cron, segunda 7h). No Windows, use o Agendador de Tarefas com o mesmo comando.
0 7 * * 1  cd ~/ozav-cnpj && python pipeline.py rodar >> rodadas.log 2>&1

# depois que existirem dois meses processados:
python pipeline.py diff --anterior saida/2026-09 --atual saida/2026-10
```

`novidades.csv` (grava em `saida/<mês atual>/`) tem uma linha por evento:
- `ganhou_socio_estrangeiro`: vínculo estrangeiro novo (tipo, país e, se PJ, nome da empresa).
  O detalhe marca `[primeiro sócio estrangeiro]` quando a empresa não tinha nenhum.
- `abriu_filial`: filial ativa que não existia (ou não estava ativa) no mês anterior.
- `mudou_cnae_principal`: CNAE principal da matriz diferente do mês anterior.

Cada evento traz a nota atual e se a empresa está na base pontuada. O sinal mais quente é a
empresa que entra na base pontuada com `ganhou_socio_estrangeiro [primeiro sócio estrangeiro]`.
`novidades.csv` não foi entregue porque não houve acesso a nenhuma publicação.

## 7. Limitações

- Sócio estrangeiro é indício, não prova de remessa. Não existe dado público de volume de câmbio
  por empresa.
- O nome da PJ estrangeira vem como está no cadastro (às vezes truncado ou desatualizado).
- O capital social é o registrado, muitas vezes antigo. O porte é autodeclarado.
- O controle indireto só sobe um nível (empresa → holding BR → PJ estrangeira).
- `ignore_errors` do DuckDB descarta linhas malformadas dos CSVs da Receita (raras, mas existem).
- A base de regime tributário tem defasagem de cerca de um ano e o layout não foi verificado.
- Nada disso foi rodado contra os arquivos reais nesta sessão. O teste usa arquivos sintéticos no
  layout oficial; códigos de qualificação e natureza reais vêm das tabelas da própria Receita, e
  o código lê as descrições em vez de depender de números decorados.

## 8. Privacidade

- O nome de sócio pessoa física nunca é gravado, nem nos `.parquet` intermediários. O teste
  verifica isso byte a byte em todas as saídas.
- Do e-mail cadastral só o domínio é gravado; o endereço completo é descartado na leitura.
- CPF, representante legal e faixa etária nem são lidos para as saídas.
