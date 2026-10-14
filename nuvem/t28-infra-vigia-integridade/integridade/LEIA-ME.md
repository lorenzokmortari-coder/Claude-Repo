# Vigia de integridade (tarefa 28)

`integridade.py`: Python 3.10+, só biblioteca padrão, Linux. Ele só avisa: nunca conserta nada e só escreve na pasta `estado` do ini.

## O que vigia
- **Arquivos** (`[arquivos]`): SHA-256, dono e permissão, comparados com `base.json`.
  - JSON com lista de chaves: compara só essas chaves (hash por chave). `*` casa qualquer chave: `projects.*.mcpServers`. Se uma chave fora da lista muda, não avisa.
  - `.env`, `.env.*` e `*.env`: guarda só o hash e a permissão. Acima de 600 avisa sempre, mesmo depois de um aceite.
  - Arquivo sumido, ilegível ou com JSON quebrado: avisa (falha fechada).
- **Pastas** (`[pastas]`, recursivo): arquivo novo, sumido ou mudado avisa.
- **O próprio vigia**: o `integridade.py` e o ini entram na lista sozinhos. Quando um item entra ou sai da lista, também avisa.

## Comandos
```
python3 integridade.py --aceitar "base inicial"      # cria a base (1ª vez)
python3 integridade.py --checar [--resumo]           # de hora em hora
python3 integridade.py --aceitar "<motivo>"          # depois de mudança de propósito
python3 integridade.py --deps [--resumo]             # semanal (osv-scanner)
```
`--ini` aponta outro ini; o padrão é `integridade.ini` ao lado do script.

## Códigos de saída
| comando | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| `--checar` | nada novo a avisar | diferença nova | erro do vigia | — |
| `--aceitar` | aceito | — | recusado/erro | — |
| `--deps` | sem ALTA/CRÍTICA | há ALTA/CRÍTICA | erro | osv-scanner ausente |

Uma mesma diferença avisa uma vez por dia, no fuso do ini (estado em `avisos.json`). Nas outras rodadas do dia, a linha diz "já avisada hoje" e o código é 0. Se o `avisos.json` estragar, o vigia volta a avisar (erra para o lado de avisar).

`--checar` sem base dá código 2. Se a base sumiu e o livro de aceites tem registros, a mensagem diz isso, e o vigia não recria a base sozinho.

## Pasta de estado
`base.json` (600), `aceites.jsonl` (só acréscimo: data, motivo, usuário, caminho, hash antes → depois), `avisos.json`, `relatorio.md`, `deps.md` e `.trava` (uma execução por vez). Se a pasta for gravável por outros, o vigia recusa rodar.

## Saída
Só caminho, hash curto (12) e o que mudou. Nunca vai conteúdo, valor de chave nem token. Há teste que procura um segredo sintético em toda a saída e em todos os arquivos de estado.

## Testes
```
python3 -m pytest -q      # 28 testes, árvore sintética em pasta temporária, sem rede
```
O teste de arquivo ilegível pula quando roda como root (o root lê tudo). Aqui ele foi rodado também como usuário comum: 28 de 28 verdes.

## Limites
- O formato do JSON do `osv-scanner` (`results[].packages[].groups[].max_severity`) e o código de saída 128 (nenhum pacote) vêm da documentação dele, que eu não conferi nesta sessão: **não verificado**. A fixture imita esse formato. Antes de confiar, rode uma vez no servidor.
- Os nomes das chaves do `~/.claude.json` e do `settings.json` no exemplo precisam ser conferidos contra os arquivos reais.
- Root com acesso de escrita pode trocar o vigia e a base juntos. Para isso, a defesa é o livro e o aviso, que mostram a troca, e não há bloqueio.
