# dadospub · kit de dados públicos (Veedha)

Módulo Python pequeno para comparar produtos de investimento com o CDI usando só dado público
e aberto, sem login. Não usa nada da ANBIMA (os termos de uso proíbem acesso automatizado) e não
contém nem deve conter dado de cliente.

## Instalação

```bash
pip install pandas requests pytest
```

Basta copiar `dadospub.py` para a pasta do projeto. O cache dos downloads fica em `~/.cache/dadospub/`.

## O que tem

| Função | Fonte | Devolve |
|---|---|---|
| `cdi_diario(ini, fim)` | BCB SGS, série 12 | `Series` com o CDI em % ao dia, por dia útil |
| `cdi_acumulado(ini, fim)` | BCB SGS, série 12 | retorno (fração) de quem aplica em `ini` e resgata em `fim` |
| `selic_diaria`, `selic_meta` | BCB SGS, séries 11 e 432 | `Series` |
| `ipca_mensal`, `ipca_acumulado` | BCB SGS, série 433 | `Series` / fração |
| `sgs(codigo, ini, fim)` | BCB SGS | qualquer série; quebra em janelas de até 10 anos |
| `focus_mais_recente()` | BCB Olinda, `ExpectativasMercadoAnuais` | medianas do Focus mais recente (IPCA, Selic, PIB, câmbio) |
| `cotas_fundo(cnpj, ini, fim)` | CVM, Informe Diário | cota, PL e cotistas por dia |
| `rentabilidade_vs_cdi(cnpj, ini, fim)` | CVM + SGS | retorno do fundo, retorno do CDI, % do CDI e datas efetivas |
| `tesouro(titulo, vencimento)` | Tesouro Transparente | taxa e PU de compra, venda e base por dia |
| `titulos_disponiveis()` | Tesouro Transparente | títulos, vencimentos e período coberto |
| `dias_uteis`, `n_dias_uteis`, `eh_dia_util`, `somar_dias_uteis`, `feriados_nacionais` | calculado | calendário bancário nacional |
| `exemplo(12)` / `python dadospub.py exemplo` | CVM + SGS | maior fundo do Informe Diário, últimos 12 meses contra o CDI |

```python
import dadospub as dp
dp.cdi_acumulado("2025-10-01", "2026-10-01")                    # 0.14... = 14,...%
dp.rentabilidade_vs_cdi("00.000.000/0001-00", "2025-10-01", "2026-10-01")
dp.tesouro("Tesouro IPCA+", "2035-05-15").tail()
dp.focus_mais_recente()
dp.n_dias_uteis("2026-01-01", "2027-01-01")                     # 249
```

## Convenções

- **CDI acumulado** usa as taxas dos dias úteis em `[início, fim)`: o DI de cada dia remunera a
  aplicação até o dia útil seguinte. É a mesma janela de `cota(fim) / cota(início) − 1`, e por
  isso `rentabilidade_vs_cdi` compara o fundo e o CDI exatamente nas datas das cotas usadas.
- **Datas sem cota** (feriado, fim de semana, fundo que não divulgou): vale a última cota em ou
  antes da data pedida. As datas efetivas voltam no resultado.
- **Retornos** saem em fração; taxas do SGS saem em % (como o BC publica).
- **Calendário**: feriados nacionais fixos, Carnaval (segunda e terça), Sexta-feira Santa, Corpus
  Christi e 20/11 a partir de 2024. Feriado municipal não entra. O teste de rede compara o
  calendário com os dias em que o BC publicou CDI nos últimos 2 anos.
- **CNPJ** é normalizado para dígitos e letras, o que já cobre o CNPJ alfanumérico de 2026.
- **Fundos com subclasse** (CVM 175): sem `subclasse=`, o módulo usa a linha da classe. Se só
  houver subclasses, ele pede para você escolher uma.

## Endereços usados

| Fonte | Endereço | Status nesta sessão |
|---|---|---|
| SGS | `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados?formato=json&dataInicial=dd/mm/aaaa&dataFinal=dd/mm/aaaa` | Padrão do endereço e limite de 10 anos por consulta (filtro obrigatório desde 26/03/2025) confirmados na página de dados abertos do BC, pelo buscador. Host bloqueado. |
| Focus | `https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais` | Não verificado (host bloqueado). |
| CVM Informe Diário | `https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/inf_diario_fi_AAAAMM.zip` (anos antigos em `.../DADOS/HIST/inf_diario_fi_AAAA.zip`) | Nome mensal confirmado pelo buscador; o arquivo de outubro/2026 aparecia atualizado em 10/10/2026. Pasta HIST e colunas pós-CVM 175 (`CNPJ_FUNDO_CLASSE`, `ID_SUBCLASSE`) não verificadas; o leitor aceita os dois layouts. |
| CVM cadastro | `https://dados.cvm.gov.br/dados/FI/CAD/DADOS/cad_fi.csv` | Não verificado; usado só para o nome do fundo. Se falhar, o nome sai vazio. |
| Tesouro Direto | `https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/PrecoTaxaTesouroDireto.csv` | O conjunto `df56aa42…` existe (o buscador acha o PDF de metadados nele); o recurso do CSV e as colunas não foram verificados. O arquivo tem centenas de MB. |

Se um endereço mudar, troque a constante no topo de `dadospub.py`.

## Testes

```bash
python -m pytest -q test_dadospub.py               # offline + rede
python -m pytest -q -m "not rede" test_dadospub.py # só offline
```

- **13 offline** cobrem as contas, o calendário e a leitura dos formatos oficiais. As amostras
  foram escritas à mão no layout de cada fonte e os valores delas são de teste.
- **5 de rede** cobrem CDI e calendário contra o BC, Selic e IPCA, Focus, o maior fundo da CVM em
  12 meses e o Tesouro IPCA+. Quando o host não responde, o teste é pulado e o motivo diz qual host.

Resultado nesta sessão de nuvem: 13 passaram e 5 foram pulados, porque `api.bcb.gov.br`,
`olinda.bcb.gov.br`, `dados.cvm.gov.br` e `www.tesourotransparente.gov.br` estão bloqueados pela
política de rede. No PC, rode a suíte completa antes de usar o módulo em material de cliente.

## Limites

- O Informe Diário é o que o administrador envia à CVM e pode ser reapresentado. A cota é bruta
  de IR e líquida de taxas.
- O `exemplo` pega o maior PL da data mais recente, que pode ser um fundo exclusivo ou de
  previdência. Para comparar produtos de prateleira, passe o CNPJ.
- O Tesouro Transparente traz o preço da manhã (abertura do mercado do Tesouro Direto), não o de
  fechamento.
- Comparação com o CDI não é recomendação. Para material de cliente, siga as regras de
  divulgação de rentabilidade da CVM e da XP.
