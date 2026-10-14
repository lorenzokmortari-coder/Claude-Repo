# Enriquecimento de site · EXEMPLO COM SITES SINTÉTICOS (nenhuma empresa real)

Entrada: `top1000.csv` sintético (7 linhas) · motor `falso (sites sintéticos)` · 1.0 s entre requisições por domínio · até 4 páginas por site · 0.0 min nesta rodada.

## Cobertura

| Item | Quantidade |
|---|---|
| Linhas na entrada | 7 |
| Com domínio próprio (marca_email = próprio) | 4 |
| Domínios distintos visitados | 3 |
| Sites lidos | 2 |
| Páginas lidas | 6 |

## Resultado por site

| Status | Sites |
|---|---|
| ok | 2 |
| robots.txt bloqueia | 1 |

## Sinais nos sites lidos

| Sinal | Sites |
|---|---|
| importa | 1 (50%) |
| exporta | 1 (50%) |
| comex | 2 (100%) |
| matriz_exterior | 2 (100%) |
| escritorio_exterior | 2 (100%) |
| global | 2 (100%) |
| clientes_exterior | 2 (100%) |
| menciona_cambio | 1 (50%) |
| vagas de comex/finanças/tesouraria | 1 (50%) |
| com e-mail de função publicado | 1 (50%) |
| com telefone no Brasil | 1 (50%) |
| com telefone no exterior | 1 (50%) |
| com página da empresa no LinkedIn | 1 (50%) |
| e-mails pessoais descartados (só contados) | 2 |

## Mais sinais (até 25)

| CNPJ | Empresa | Nota | Sinais | Evidências |
|---|---|---|---|---|
| 11111111000191 | ALFA | 84.3 | 9 | exporta: exportamos · global: global, em 12 paises · clientes_exterior: clientes em 12 paises · menciona_cambio: pagamentos internacionais, dolar · importa: imp |
| 33333333000101 | ZETA LOGISTICA TESTE LTDA | 66.0 | 5 | comex: freight forwarding, international trade · global: in 40 countries · clientes_exterior: customers in 40 countries · matriz_exterior: matriz/sede: Roterdã |

## robots.txt bloqueou (1)

beta-teste.com.br

## Como ler

- `n_sinais` soma os sinais binários e conta 1 se houver vaga-alvo. É indício, não prova de remessa.
- `evidencias` traz só os termos fixos que dispararam cada sinal, sem trecho do site.
- `escritorios` e `matriz_em` só mostram lugares de uma lista fechada (países e cidades).
- "ok, pouco texto" quase sempre é site feito em JavaScript; com o motor crawl4ai ele é renderizado.
