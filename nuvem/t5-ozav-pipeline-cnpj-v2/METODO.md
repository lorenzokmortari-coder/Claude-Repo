# Ozav · lista quente CNPJ · método (v2, fonte WebDAV)

Pipeline que lê os Dados Abertos do CNPJ da Receita Federal e devolve as empresas com mais
chance de pagar ou receber do exterior todo mês. A hipótese testada é que a filial ou
subsidiária de empresa estrangeira (sócio pessoa jurídica no exterior) faz remessa intercompany
o tempo todo.

## 1. Fonte (v2: WebDAV)

| Item | Valor | Status |
|---|---|---|
| Fonte padrão (v2) | Compartilhamento público da Receita (Nextcloud), lido por WebDAV: `https://arquivos.receitafederal.gov.br/public.php/webdav/Dados/Cadastros/CNPJ/` com pastas `AAAA-MM/` | Usado com sucesso pela conversa 00 no PC em 14/10/2026 (listagem e download de 2026-10). Daqui da nuvem dá 403 no proxy, então **não conferido nesta sessão**. |
| Autenticação | Basic: usuário = token do link público `gn672Ad4CF8N6TK`, senha vazia | É o token do link público, não credencial pessoal. Se a Receita trocar o link, passe o novo com `--token`. |
| Listagem | `PROPFIND` com `Depth: 1` devolve `207 Multi-Status` com nome, tamanho (`getcontentlength`) e data de cada arquivo | O parser ignora a própria pasta e os `propstat` com status diferente de 200 (o Nextcloud manda 404 de `getcontentlength` nas pastas). |
| Download | `GET` com a mesma autenticação | O servidor **não aceita retomar** (Range). Em qualquer falha o pipeline apaga o parcial e baixa de novo do zero (até 6 tentativas, espera 2-4-8-16-32 s) e só aceita o arquivo se o tamanho bater com a listagem e o zip abrir. |
| Mês | O pipeline acha sozinho o mês mais recente **completo** | Completo = tem `Empresas*`, `Estabelecimentos*`, `Socios*` e `Simples*`, nenhum arquivo com 0 byte e pelo menos tantas partes de cada tipo quanto o mês anterior. Um mês ainda subindo é pulado (com aviso) e vale o anterior. |
| Endereço antigo (v1) | `https://arquivos.receitafederal.gov.br/dados/cnpj/dados_abertos_cnpj/` | Saiu do código. A v1 lia a página HTML; a Receita passou para o compartilhamento acima. |
| Dicionário de dados (layout) | `https://www.gov.br/receitafederal/dados/cnpj-metadados.pdf` | O layout usado no código é o descrito nesse PDF. Não verificado nesta sessão. |
| Regime tributário (lucro real por ano) | Com `--regime`, procura no WebDAV uma pasta com "regime" no nome ao lado de `CNPJ/` (até 2 níveis) e um zip com "real" no nome, do ano mais recente; se não achar, tenta o endereço antigo `https://arquivos.receitafederal.gov.br/dados/cnpj/regime_tributario/` | **Não verificado.** Local e layout não confirmados; o código procura as colunas pelo nome e, se falhar, segue sem regime. |

Mudanças de 2026 que o código já trata (vistas em fontes secundárias, **não verificado** no texto
oficial):
- CNPJ alfanumérico para novas inscrições a partir de julho de 2026 (IN RFB nº 2.229/2024). O
  pipeline trata CNPJ sempre como texto e aceita letras no CNPJ do sócio PJ.
- Relato de troca de codificação após uma migração em fevereiro de 2026 (arquivo com BOM
  UTF-16). O pipeline detecta a codificação de cada CSV (BOM UTF-8, BOM UTF-16, UTF-8 ou latin-1)
  e converte UTF-16 para UTF-8 antes de ler.

## 2. Como rodar (no PC)

Requisitos: Python 3.10+, `pip install duckdb requests` (e `pytest` para os testes), cerca de 10 GB
livres (o pico é um zip mais o CSV extraído) e conexão com o servidor da Receita, que costuma ser
lento. A base de 2026-10 tem perto de 7,8 GB em zips (número da conversa 00, que baixou pelo PC).

```bash
python pipeline.py listar                   # meses publicados e os arquivos do mais recente, com tamanho
python pipeline.py rodar                    # acha o mês mais recente completo, baixa um zip por vez e roda tudo
python pipeline.py rodar --mes 2026-10      # um mês específico
python pipeline.py rodar --manter-zips      # guarda os zips em saida/<mês>/zips; se cair no meio, a rodada
                                            # seguinte (com --refazer) reaproveita os que já estão inteiros
python pipeline.py rodar --regime           # tenta usar a base de lucro real
python pipeline.py rodar --fonte-local C:/Users/loren/ozav-cnpj/zips/2026-10   # zips já baixados; o mês sai
                                            # do nome da pasta (ou passe --mes)
python pipeline.py pontuar --mes 2026-10    # refaz só a nota (ex.: depois de mudar cnae_alvo.csv)
python -m pytest -q                         # 11 testes: ponta a ponta local + WebDAV falso
```

Se a pasta do mês já tem `top1000.csv`, `rodar` avisa e não faz nada; use `--refazer` para
processar de novo. Com isso o agendamento semanal pode rodar sempre o mesmo comando.

Ordem de processamento (um arquivo por vez: baixa → confere o tamanho → extrai → filtra para
`.parquet` → apaga o zip e o CSV):
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
6. Nota e saídas: `top1000.csv`, `contagens.csv`, `base_pontuada.parquet`, `FONTE.txt` (fonte,
   mês, número de arquivos, data da rodada) e, se o mês anterior já foi processado na mesma
   pasta, `novidades.csv`.

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
isso, agende o mesmo comando toda semana. O pipeline escolhe sozinho o mês mais recente
completo, pula o mês que já foi processado e, quando processa um mês novo, faz o diff contra o
mês anterior que estiver na mesma pasta de saída.

```bash
# Linux/macOS (cron, segunda 7h). No Windows, use o Agendador de Tarefas com o mesmo comando.
0 7 * * 1  cd ~/ozav-cnpj && python pipeline.py rodar --dir saida >> rodadas.log 2>&1

# diff manual entre dois meses quaisquer:
python pipeline.py diff --anterior saida/2026-09 --atual saida/2026-10
```

`novidades.csv` (grava em `saida/<mês atual>/`) tem uma linha por evento:
- `ganhou_socio_estrangeiro`: vínculo estrangeiro novo (tipo, país e, se PJ, nome da empresa).
  O detalhe marca `[primeiro sócio estrangeiro]` quando a empresa não tinha nenhum.
- `abriu_filial`: filial ativa que não existia (ou não estava ativa) no mês anterior.
- `mudou_cnae_principal`: CNAE principal da matriz diferente do mês anterior.

Cada evento traz a nota atual e se a empresa está na base pontuada. O sinal mais quente é a
empresa que entra na base pontuada com `ganhou_socio_estrangeiro [primeiro sócio estrangeiro]`.

## 7. Limitações

- Sócio estrangeiro é indício, não prova de remessa. Não existe dado público de volume de câmbio
  por empresa.
- O nome da PJ estrangeira vem como está no cadastro (às vezes truncado ou desatualizado).
- O capital social é o registrado, muitas vezes antigo. O porte é autodeclarado.
- O controle indireto só sobe um nível (empresa → holding BR → PJ estrangeira).
- `ignore_errors` do DuckDB descarta linhas malformadas dos CSVs da Receita (raras, mas existem).
- A base de regime tributário tem defasagem de cerca de um ano e o layout não foi verificado.
- Nada disso foi rodado contra os arquivos reais nesta sessão (a rede da nuvem bloqueia
  `arquivos.receitafederal.gov.br`). Os testes usam arquivos sintéticos no layout oficial e um
  servidor WebDAV falso que imita o Nextcloud; códigos de qualificação e natureza reais vêm das
  tabelas da própria Receita, e o código lê as descrições em vez de depender de números decorados.
- O teste do WebDAV imita o formato de resposta do Nextcloud, mas não é o servidor da Receita.
  Se a Receita mudar o caminho ou o token do compartilhamento, a listagem falha com uma
  mensagem clara (401/403/404) e basta passar `--webdav` e `--token` novos.
- O pipeline não detecta um arquivo que ainda está subindo e já aparece com tamanho parcial na
  listagem; a regra de "mês completo" (tipos, partes e 0 byte) reduz esse risco, mas não zera.

## 8. Privacidade

- O nome de sócio pessoa física nunca é gravado, nem nos `.parquet` intermediários. O teste
  verifica isso byte a byte em todas as saídas.
- Do e-mail cadastral só o domínio é gravado; o endereço completo é descartado na leitura.
- CPF, representante legal e faixa etária nem são lidos para as saídas.
