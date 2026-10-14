# Infra · cota real do plano

Três peças, sem dependência nova:

| Arquivo | O que faz |
|---|---|
| `statusline-cota.mjs` | Barra de status do Claude Code em Node. Mostra modelo, pasta, contexto e a cota de 5 h e de 7 dias com o horário do reset, e grava no máximo 1 linha por minuto em `~/.claude/cota.jsonl`. |
| `statusline-cota.sh` | A mesma barra em Git Bash, para quem não tem Node. Não usa jq nem date e não cria processo nenhum no caminho normal (no Windows cada processo do Git Bash é lento). A saída é idêntica à do `.mjs`, byte a byte, e o teste confere isso. |
| `relatorio.py` | Lê o `cota.jsonl` e mostra o estado atual, o consumo por dia e por hora e os alertas: passou de 80% da cota semanal antes de quarta, ou o ritmo das últimas 24 h acaba com a cota antes do reset. |

Linha gravada (uma por minuto, só quando o Claude Code mandou alguma janela):

```json
{"hora":"2025-02-01T05:53:20-03:00","pct_5h":23.5,"reset_5h":1738425600,"pct_7d":41.2,"reset_7d":1738857600,"modelo":"claude-opus-5-5","modelo_nome":"Opus","sessao":"abc123..."}
```

Barra (com cores: verde abaixo de 50%, amarelo de 50% a 79%, vermelho a partir de 80%):

```
[Opus] directory | ctx 8% | 5h ▓▓░░░░░░░░ 24% ↻13:00 · 7d 41% ↻qui 13:00
```

## O que a documentação oficial diz (conferido em 14/10/2026)

Fonte: <https://code.claude.com/docs/en/statusline>, seção "Available data" e o "Full JSON schema".

- Os nomes exatos são `rate_limits.five_hour.used_percentage` e `rate_limits.seven_day.used_percentage`
  ("de 0 a 100") e `rate_limits.five_hour.resets_at` e `rate_limits.seven_day.resets_at` (Unix epoch
  em segundos). Atrás de um Claude apps gateway com limite de gasto também vem
  `rate_limits.spend_limit`, que estes scripts ignoram.
- `rate_limits` só aparece para assinante claude.ai Pro e Max (ou atrás desse gateway) e só depois da
  primeira resposta da API na sessão. Cada janela pode faltar sozinha, e o Claude Code tira a janela
  do JSON quando passa o `resets_at` dela. Por isso os scripts tratam cada janela como opcional e não
  gravam nada quando nenhuma veio.
- Os outros campos usados são `model.id`, `model.display_name`, `session_id`, `workspace.current_dir`
  (ou `cwd`) e `context_window.used_percentage`, que pode vir `null` no começo da sessão.
- A barra roda quando a sessão abre, a cada evento da conversa (com debounce de 300 ms), quando uma
  janela de cota chega ao `resets_at` e, se configurado, a cada `refreshInterval` segundos (mínimo 1).
  Se um evento novo chega com o script ainda rodando, o Claude Code cancela o script. Os scripts usam
  `refreshInterval: 60` para gravar também com a sessão parada.
- No Windows o comando roda pelo Git Bash quando ele está instalado e pelo PowerShell quando não está.
  O caminho no `command` tem de usar barra normal (`C:/Users/...` ou `~/.claude/...`).

**E no `claude -p`?** A página da barra de status não fala do `-p`. A barra é a linha de baixo da
interface interativa, e o `-p` não tem essa interface, então o script não deve rodar. Não verifiquei
rodando o `claude -p`. No `-p` os números chegam por outros caminhos e com outros nomes:

- Com `--output-format stream-json`, o evento `rate_limit_event` traz `rate_limit_info` com `status`
  (`allowed`, `allowed_warning` ou `rejected`), `resetsAt` e `utilization`, que vai de 0,0 a 1,0 e
  não de 0 a 100. O SDK em Python também lê `rate_limit_type` (`five_hour`, `seven_day`,
  `seven_day_opus`, `seven_day_sonnet` ou `overage`). Segundo a documentação, o evento sai "quando a
  sessão encontra um limite" (TypeScript) ou "quando o status muda, por exemplo de allowed para
  allowed_warning" (Python). Fontes:
  <https://code.claude.com/docs/en/agent-sdk/typescript> (`SDKRateLimitEvent`) e
  <https://code.claude.com/docs/en/agent-sdk/python> (`RateLimitEvent`, `RateLimitInfo`).
- O comando `/usage` mandado como prompt devolve um `usage_report` com `rate_limits.limits`. Cada
  linha tem `kind` (`session`, `weekly_all`, `weekly_scoped`...), `percent` de 0 a 100 e `resets_at`
  em ISO 8601. A documentação marca esse tipo como experimental (Agent SDK v0.3.273 ou mais novo).

## Como instalar no PC (Windows)

1. Copie `statusline-cota.mjs` (ou `statusline-cota.sh`) e `relatorio.py` para `C:\Users\loren\.claude\`.
   Para saber se há Node, rode `node -v` no Git Bash. Sem Node, use o `.sh`.
2. Se já existe uma barra de status no `settings.json`, copie o `command` dela para
   `C:\Users\loren\.claude\cota-base.txt` (uma linha só). A barra antiga continua aparecendo, e a cota
   vem depois dela.
3. No `C:\Users\loren\.claude\settings.json`, ponha (ou troque) o bloco:

   ```json
   "statusLine": { "type": "command", "command": "node ~/.claude/statusline-cota.mjs", "refreshInterval": 60 }
   ```

   ou, sem Node: `"command": "bash ~/.claude/statusline-cota.sh"`.
4. Abra o Claude Code e mande uma mensagem. Depois da primeira resposta aparecem o 5h e o 7d, e o
   `cota.jsonl` ganha uma linha por minuto enquanto alguma sessão estiver aberta.
5. Relatório: `python C:/Users/loren/.claude/relatorio.py` (ou com `--saida C:/Users/loren/.claude/cota.md`).
   Opções: `--limite 80`, `--dia qua`, `--dias 14`. O código de saída é 2 com alerta, 0 sem alerta e
   1 sem dado. Um agendamento pode usar isso para avisar.

Com várias sessões abertas ao mesmo tempo, todas gravam no mesmo arquivo. A trava `cota.ultimo` deixa
passar no máximo uma linha por minuto. Se duas escreverem no mesmo segundo, o relatório junta as
linhas do minuto e fica com o maior valor (a cota é a mesma para todas). O arquivo cresce no máximo
uns 290 KB por dia (1.440 linhas de 200 bytes). Não há rotação; apague linhas antigas quando quiser.

## Como o relatório conta

- **p.p.** = pontos percentuais da cota. "5 p.p. da cota de 7 dias" = 5% do limite semanal.
- O consumo é a diferença entre duas amostras seguidas da mesma janela (mesmo `resets_at`, com 2 min
  de tolerância). Quando a janela vira, o percentual que aparece foi gasto depois do reset e conta
  inteiro. O que foi gasto entre a última amostra e o reset fica de fora.
- O gasto entra na hora da amostra em que apareceu. Com o Claude Code fechado não há amostra, então
  o gasto desse tempo (inclusive no claude.ai, no app e nas sessões na nuvem, que dividem a mesma
  cota) aparece todo na primeira amostra seguinte.
- **Alerta de quarta:** a janela atual vai de `resets_at - 7 dias` até `resets_at`. O marco é a
  primeira quarta 00:00 depois do começo da janela. Se alguma amostra da janela antes do marco passou
  do limite, sai um ALERTA. O dia e o limite mudam com `--dia` e `--limite`.
- **Ritmo:** p.p. por hora nas últimas 24 h da janela atual. Só sai quando há pelo menos 3 h de
  registro. Dele saem dois AVISOS: quando chega ao limite antes do marco e quando a cota acaba antes
  do reset.

## Testes

`python -m pytest -q` roda 23 testes. Eles usam o JSON de exemplo da documentação (`exemplo_docs.json`)
e variações dele: cores, uma linha por minuto, janela faltando, contexto `null`, entrada vazia ou
quebrada, caminho do Windows, barra antiga, JSON compacto e indentado, Node igual a bash, e o relatório
por dia e por hora, o alerta de quarta, o alerta de ritmo e o caso sem dados. Os testes do `.mjs`
pulam sem `node` e os do `.sh` pulam sem `bash`.

## Limitações

- Testado no Linux da nuvem (bash 5.2 e Node 22), não no Windows. O `.sh` usa só recursos do bash 5
  (`EPOCHSECONDS`, `printf '%(...)T'`), que o Git Bash atual tem. Se o Git Bash for muito antigo e a
  hora sair errada, use o `.mjs`.
- Não verificado: que o Claude Code no Windows passa o fuso certo para o script. A hora gravada é a do
  relógio do PC, com o deslocamento (`-03:00`).
- O `.sh` lê o JSON com expressões regulares. Elas funcionam para estes campos porque as janelas e
  o `model` não têm objeto dentro. Se a Anthropic mudar esse formato, o `.mjs`, que usa `JSON.parse`,
  continua certo.
