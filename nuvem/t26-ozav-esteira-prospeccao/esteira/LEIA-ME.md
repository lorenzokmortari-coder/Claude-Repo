# Ozav · esteira mensal de prospecção (14/10/2026)

`esteira/esteira.py` encadeia num comando só as quatro peças que já existiam. Elas vão aqui inteiras e sem mudança: o sha256 é o mesmo dos artifacts de origem.

| Etapa | Peça | O que faz |
|---|---|---|
| 1. cnpj | `pipeline.py` (pipeline CNPJ v2) | Lê os zips da Receita de uma pasta local e grava a `base_pontuada.parquet` com todas as qualificadas e a nota CNPJ |
| 2. icp | `icp.ini` + `concorrentes.csv` (vigia) | Aplica o filtro que o dono edita e tira os concorrentes por domínio e por nome, a `exclusao_extra.csv` e, se houver, o retrato do cadastro do BC |
| 3. site | `enriquecer_site.py` | Visita o site dos candidatos. Respeita o robots.txt, faz 1 pedido por segundo por domínio, guarda só e-mail de função e nunca visita o LinkedIn |
| 4. nota | `esteira.py` | Nota final = 0,7 × nota CNPJ + 0,3 × nota do site, mais o motivo em uma linha |
| 5. saídas | `esteira.py` | `top1000.csv`, `novidades.md`, `crm.jsonl`, `excluidos.csv`, `mudancas.csv`, `RODADA.md` |

Tudo sai em `saida/<mês>/esteira/`. O `top1000.csv` que vale é o dessa pasta. O de `saida/<mês>/` é o do pipeline sozinho, sem filtro de ICP, sem concorrentes e sem site.

## Instalar e testar (PC)

```
pip install duckdb requests selectolax phonenumbers pandas pytest
cd esteira
python -m pytest -q          # 36 passam e 2 pulam (motor Crawl4AI e a rede do BC); leva ~1 min
```

## Rodar num mês já baixado

```
python esteira.py --mes 2026-10 --fonte-local C:/Users/<você>/ozav-cnpj/zips/2026-10
python esteira.py --mes 2026-10 --fonte-local ... --dir saida --config icp.ini --workers 6
```

- **Se a pasta do pipeline já processou o mês** (tem `saida/2026-10/top1000.csv` e `base_pontuada.parquet`), a etapa cnpj é reaproveitada. Use o mesmo `--dir` do pipeline.
- **Retomada:** se a rodada cair no meio, rode o mesmo comando. A etapa cnpj não é refeita, e cada site terminado fica em `esteira/site/cache_sites.jsonl` e não é visitado de novo. O teste derruba a rodada no meio do site e confere que a segunda rodada não revisita nada e chega ao mesmo resultado de uma rodada limpa.
- **Mudou o `icp.ini`:** rode o mesmo comando. Só o filtro, os sites novos e a nota são refeitos.
- **Tempo estimado:** 1.500 candidatos com 6 workers levam de 25 a 40 min. É uma conta (5 a 8 s por site), não uma medida.

## O que o dono edita (`icp.ini`)

- **`[icp]`:**
  - UFs que entram e que saem;
  - capital mínimo;
  - portes;
  - faixa de idade;
  - vínculos estrangeiros aceitos;
  - nota CNPJ mínima;
  - grupos e prefixos de CNAE fora;
  - só domínio próprio, sim ou não.

  Os filtros do pipeline ficam e só podem ser apertados: matriz ativa, fora do Simples, vínculo estrangeiro, capital ≥ R$ 100 mil, fora do setor financeiro e CNAE no `cnae_alvo.csv`.
- **`[concorrentes]`:**
  - níveis do `concorrentes.csv` que ficam fora (o padrão é todos);
  - a `exclusao_extra.csv` (colunas `cnpj_raiz`, `dominio`, `motivo`);
  - a pasta dos retratos do `vigia_bc.py`.
- **`[site]`:**
  - candidatos (padrão 1.500);
  - workers;
  - motor.

  `workers = 1` dá 1 pedido por segundo **no total**. O padrão é 1 por segundo **por domínio**, a mesma regra da peça de site.
- **`[nota]` e `[nota_site]`:**
  - pesos;
  - tamanho do top;
  - pontos por sinal do site. "global" vale 0, porque dá falso positivo demais.

## Concorrente fica fora

- **Domínio:** o registrável do site no `concorrentes.csv`, comparado com o e-mail cadastral e com o destino do site. Exemplo: um site que redireciona para `br.ebury.com` sai.
- **Nome:** o nome-chave como palavra inteira na razão social ou no fantasia. Pega Deel, dLocal, Airwallex, Husky, Trace Finance, Conta Simples e o nome antigo "Bexs", que passam pelo filtro de nome do pipeline.
  - Palavra comum só casa com o nome completo: Inter, Frente, Wise, Circle, Rendimento. "INTER TRANSPORTES" não sai, e há teste disso.
  - Sigla curta (B&T, MB) fica só no domínio.
- **Onde conferir:** cada exclusão vai para `excluidos.csv` com o motivo.

## Saídas

- **`top1000.csv`:**
  - posição, CNPJ, razão, fantasia, UF, município, CNAE, grupo, capital, porte, início;
  - vínculo estrangeiro (tipo, país e nome da PJ estrangeira);
  - site e e-mail de função;
  - nota, nota CNPJ e nota do site;
  - motivo, status do site e sinais.

  Sem telefone, sem LinkedIn e sem nome de pessoa.
- **`crm.jsonl`:** um objeto por linha, com `id_externo` (= CNPJ, para o upsert), `mes`, `posicao`, `nome`, `nome_fantasia`, `cnpj`, `site`, `email_funcao`, `emails_funcao`, `nota`, `motivo` e `origem`. A esteira só grava o arquivo; quem sobe é o PC.
- **`novidades.md`:**
  - o que entrou, saiu (com o porquê: concorrente, fora do ICP, saiu da base da Receita ou caiu de posição) e mudou (nota ±5, site, e-mail) desde o mês anterior da mesma pasta;
  - os eventos do pipeline (sócio estrangeiro novo, filial, CNAE);
  - o bloco do vigia: quem entrou e saiu do cadastro do BC (câmbio e pagamentos) nos retratos do mês. Sem retrato, o bloco diz isso e como ter.
- **`excluidos.csv`, `mudancas.csv`, `RODADA.md`, `estado.json`:** as exclusões, as mudanças em tabela, as contagens e as etapas feitas.

## Testes (`test_esteira.py`, 14)

Usam a Receita sintética do `gerar_receita.py`: dois meses, com mudanças plantadas. Os sites vêm de um servidor HTTP local de verdade, usado como proxy, que atende cada domínio falso pelo Host. Nenhum dado é real.

O que cobrem:
- top, CRM e nota;
- concorrente pelo nome, pelo domínio e pelo redirecionamento, sem ser visitado;
- robots.txt;
- 1 pedido por segundo por domínio, medido no envio;
- só GET;
- nenhum nome de pessoa, e-mail pessoal ou LinkedIn nas saídas;
- novidades;
- retomada;
- rodar de novo não refaz nada;
- `icp.ini` editado sem refazer o CNPJ;
- bloco do vigia e exclusão pelo cadastro do BC;
- unidades da exclusão.

As suítes antigas do pipeline (11), do site (9) e do vigia (2) continuam verdes nesta pasta.

## Limitações

- **Dado real:** nada rodou contra a Receita nem contra sites reais. A Receita é bloqueada nesta nuvem e os domínios do teste são inventados.
- **Exclusão por nome:** pode dar falso positivo ou falso negativo com nomes reais. Confira o `excluidos.csv` na primeira rodada.
- **Nota do site:** empresa sem site lido fica com 0 nela e perde até 30 pontos na nota final. Ajuste `peso_site` se isso pesar demais.
- **Bloco do vigia:** usa `pandas` e os retratos do `vigia_bc.py`, que o PC baixa (o Olinda também é bloqueado aqui).
