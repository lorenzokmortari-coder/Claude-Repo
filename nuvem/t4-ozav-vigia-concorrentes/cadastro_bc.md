# Cadastro do Banco Central: quem entrou e quem saiu

Como usar o cadastro diário de instituições autorizadas do Banco Central (Portal de Dados
Abertos, serviço Olinda/OData) para vigiar concorrentes de câmbio e pagamentos.

## 1. Qual base usar

| Base | Endereço OData | Atualização | Para quê |
|---|---|---|---|
| **Dados cadastrais de entidades supervisionadas** (BcBase v2) | `https://olinda.bcb.gov.br/olinda/servico/BcBase/versao/v2/odata/EntidadesSupervisionadas` | diária (origem: Unicad) | Base principal: todas as entidades autorizadas a funcionar, cooperativas incluídas. É a que o vigia usa. |
| Tabelas de domínio do mesmo serviço | `.../BcBase/versao/v2/odata/TipoEntidadeSupervisionada`, `.../TipoSituacaoPessoaJuridica`, `.../NaturezaJuridica`, `.../EsferaPublica` | diária | Traduzir os códigos de tipo (segmento), situação e natureza jurídica. |
| Relação de Instituições em Funcionamento no País | `https://olinda.bcb.gov.br/olinda/servico/Instituicoes_em_funcionamento/versao/v1/odata/SedesSociedades` | diária (origem: Unicad) | Relação por segmento (bancos de investimento, financeiras, instituições de pagamento, SCD…). Serve para conferir. |

Páginas do portal onde esses endereços aparecem, confirmadas pelo buscador em 14/10/2026:
- Conjunto: https://dadosabertos.bcb.gov.br/dataset/dados-cadastrais-de-entidades-autorizadas
- Recurso OData: https://dadosabertos.bcb.gov.br/dataset/dados-cadastrais-de-entidades-autorizadas/resource/7ee86213-bf14-4123-892c-0b3202c38827
- Swagger: https://dadosabertos.bcb.gov.br/dataset/dados-cadastrais-de-entidades-autorizadas/resource/8600cf18-b981-456c-9ed1-bddec2690b71
- Tipo de entidade: https://dadosabertos.bcb.gov.br/dataset/dados-cadastrais-de-entidades-autorizadas/resource/655ea45d-cb87-4a90-a446-a66b25b1cd11
- Relação de instituições em funcionamento: https://dadosabertos.bcb.gov.br/dataset/relacao-de-instituicoes-em-funcionamento-no-pais

## 2. Consultas exatas

```text
# esquema (lista recursos e campos; é o primeiro passo, porque os nomes de campo não estão nesta nota)
https://olinda.bcb.gov.br/olinda/servico/BcBase/versao/v2/odata/$metadata

# amostra de 5 linhas em JSON
https://olinda.bcb.gov.br/olinda/servico/BcBase/versao/v2/odata/EntidadesSupervisionadas?$top=5&$format=json

# base inteira, paginada (repita somando 5000 ao $skip até vir menos de 5000 linhas)
https://olinda.bcb.gov.br/olinda/servico/BcBase/versao/v2/odata/EntidadesSupervisionadas?$format=json&$top=5000&$skip=0

# a mesma base em CSV
https://olinda.bcb.gov.br/olinda/servico/BcBase/versao/v2/odata/EntidadesSupervisionadas?$format=text/csv

# domínio dos tipos de entidade (para filtrar câmbio e pagamentos)
https://olinda.bcb.gov.br/olinda/servico/BcBase/versao/v2/odata/TipoEntidadeSupervisionada?$format=json
```

Os parâmetros `$top`, `$skip`, `$filter`, `$select`, `$orderby` e `$format` são do padrão OData e
os serviços Olinda os aceitam. Depois de ver os nomes no `$metadata`, dá para filtrar no próprio
servidor, por exemplo `$filter=<campo de tipo> eq <código de corretora de câmbio>`.

**Status desta nota:** os endereços acima são os documentados no portal, segundo o buscador. Eles
**não foram chamados** nesta sessão, porque `olinda.bcb.gov.br` e `dadosabertos.bcb.gov.br` estão
bloqueados pela política de rede da nuvem (HTTP 403 no proxy). O formato CSV
(`$format=text/csv`) e os nomes de campo **não foram verificados**.

## 3. Rotina para saber quem entrou e quem saiu

O cadastro é um retrato do dia, sem histórico de eventos. O jeito confiável é guardar um retrato
por dia e comparar. `vigia_bc.py` faz isso:

```bash
pip install pandas requests
python vigia_bc.py esquema                        # 1ª vez: confere recursos e campos
python vigia_bc.py baixar                         # todo dia: grava retratos/AAAA-MM-DD.csv
python vigia_bc.py diff --so-cambio-pagamentos    # compara os dois retratos mais recentes
```

Agende `baixar` e `diff` uma vez por dia, de manhã (cron ou Agendador de Tarefas). O diff grava
`retratos/novidades_<antes>_a_<depois>.csv`, com uma linha por evento:

| coluna | conteúdo |
|---|---|
| `evento` | `entrou` (CNPJ novo no cadastro), `saiu` (CNPJ que sumiu) ou `mudou` (algum campo mudou) |
| `chave` | o CNPJ da entidade (o script acha sozinho a coluna com "cnpj" no nome) |
| `nome` | razão social |
| `campo`, `antes`, `depois` | para `mudou`: qual campo mudou e os dois valores (situação, tipo, nome, endereço…) |

`--so-cambio-pagamentos` mantém só as linhas cujo texto fala de câmbio, pagamento, ativos virtuais,
crédito direto ou empréstimo entre pessoas: corretoras e bancos de câmbio, instituições de
pagamento, prestadoras de serviço de ativos virtuais, SCD e SEP. Entidade que "sai" muitas vezes
não some do cadastro, mas muda de situação (liquidação, cancelamento), e isso aparece como
`mudou` no campo de situação.

Para a Ozav, os sinais que valem alerta:
- `entrou` com tipo de câmbio ou instituição de pagamento: concorrente novo autorizado.
- `mudou` no tipo ou segmento: fintech que virou IP, corretora que virou banco de câmbio.
- `mudou` na situação para liquidação ou cancelamento: concorrente saindo, e carteira de clientes à venda.
- `mudou` no nome: aquisição ou rebranding (cruze com `concorrentes.csv`).

## 4. Exemplo real da saída de hoje

**Não foi possível.** `olinda.bcb.gov.br` estava bloqueado nesta sessão, então não há retrato real
de 14/10/2026, nem contagem de entidades, nem nomes de campo confirmados. Nenhum exemplo foi
inventado. No PC, `python vigia_bc.py esquema` e `python vigia_bc.py baixar` produzem o exemplo
real em menos de um minuto. O primeiro diff precisa de dois dias de retrato.

O teste `test_vigia_bc.py` usa dois retratos **sintéticos** para conferir a lógica (entrou, saiu,
mudou e o filtro de câmbio/pagamentos). Ele não é saída real.

## 5. Limites

- O cadastro diz quem está autorizado, não quem vende câmbio para empresa. Plataformas que operam
  por meio de um parceiro autorizado (modelo eFX, parceria com banco de câmbio) não aparecem com
  o próprio CNPJ. Para essas, a vigia é pelo site (`concorrentes.csv`).
- Plataformas estrangeiras sem entidade brasileira também não aparecem.
- A data em que o BC atualiza o Unicad pode atrasar alguns dias em relação ao ato de autorização
  publicado no Diário Oficial.
