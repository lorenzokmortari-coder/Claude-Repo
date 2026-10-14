# Triagem 00 · verificação dos patches (tarefa 24, 14/10/2026)

Atualizado no fim da rodada, com as entregas 16 e 17 da outra sessão.

**O que foi verificado:** todos os patches das entregas 12 a 23, aplicados sobre cópias limpas dos pacotes privados "Ozav · envio", "Ozav · gateway LLM", "Veedha · portão", "Infra · VPS" e "Setup · Claude Code", e sobre os arquivos da v1 da legenda.

**Como:** com `patch -p1 --fuzz=0`, de três jeitos:
- cada patch sozinho;
- em sequência, na ordem dos números;
- todos juntos.

Depois, a suíte inteira: os testes que já existiam, os harnesses e os testes novos.

**Ambiente:** Linux, Node 22.22 e Python 3, com e sem faster-whisper 1.2.1 e PyAV 19. Nada foi executado em servidor.

## Resumo por pacote

| Pacote | Entregas | Consolidado | Isolados | Em sequência | Suíte com o consolidado |
|---|---|---|---|---|---|
| Ozav · envio | 12 + 18 | `aplicar/ozav-envio.diff` | 9/9 (12), 2/2 (18) | 01→09 da 12 e 01→02 da 18: ok, só deslocamento de linhas | 33 do pacote; 12: 20 ok + 1 todo (10 falhavam); 18: 8 ok (6 falhavam); governador, convivência, `eu.js` e pulso ok; harness da catraca 148/158, com as mesmas 10 falhas antes e depois (sanitização) |
| Ozav · gateway LLM | 13 | `aplicar/ozav-gateway-llm.diff` | 13/13 | **Conflito:** o 09 e o 11 falham depois do 03 (o mesmo bloco `catch`). O `todos.diff` da 13 resolve | 17 ok + 1 todo (13 falhavam); harnesses disjuntor 7, plano 13 e anexos 8 ok; `llm-anexos` 5/6 antes e depois (falta o `midia-ler.js` no pacote) |
| Veedha · portão | 14 + 20 | `aplicar/veedha-portao.diff` | 1/1 (14), 1/1 (20) | 14→20 e 20→14: ok, com deslocamento de 20 linhas e o mesmo `portao.js` final | bateria 773 ok; redteam 8/8 (8 falhavam); dispensa 3/3 (1 falhava); modelos20 1/1 (falhava); `conferir.teste.js` falha antes e depois (falta o `coletor/coletar` no pacote) |
| Infra · VPS | 15 + X01 | `aplicar/infra-vps.diff` | 7/7 | **Conflito:** o 06 falha depois do 03 (o mesmo bloco do `tar` no `backup.sh`). O `todos.diff` da 15 resolve | V01–V07 7/7 (0/7 antes); X01 1/1 (falha só com a 15); `bash -n` e `node --check` ok |
| Setup · Claude Code | 16 | `aplicar/setup-claude.diff` | 5/5 | 01→05: ok, sem deslocamento; igual ao `todos.diff` da 16 | H00–H05 6/6 (5 falhavam); `bash -n` e `node --check` ok |
| Fred · legenda | 23 | `aplicar/fred-legenda.diff` | 1/1 sobre a v1 da tarefa 8 | n/a | dá os 4 arquivos idênticos à `v2/`; pytest 28 ok + 1 pulado com o PyAV antigo; 29 ok com faster-whisper 1.2.1 + PyAV 19 |

## Juntos na mesma pasta

O `ozav-envio.diff` e o `ozav-gateway-llm.diff` mexem em arquivos diferentes da pasta do CRM. Foram aplicados juntos numa cópia com o IP no lugar do marcador, como o arquivo real, e passaram:
- `node --test testes/*.test.js`: 78 ok + 2 todo (antes, 29 falhas);
- os harnesses do `llm.js`.

Os seis consolidados aplicam com `patch -p1` e com `git apply`. Nos cinco de pacote, os dois comandos dão o mesmo resultado.

## O marcador do gateway

O patch 05 da 13 troca a linha do aviso que tem o link do painel. No pacote, o IP virou `<IP_VPS>`; no arquivo real está o IP. Sem trocar, o hunk não aplica, o que foi testado aqui. O comando da página lê o IP do próprio `llm.js` e troca antes de aplicar:
```
IP=$(grep -oE 'http://[0-9.]+:8778' llm.js | head -1 | cut -d/ -f3 | cut -d: -f1); echo $IP
sed "s/<IP_VPS>/$IP/g" aplicar/ozav-gateway-llm.diff | patch -p1
```
Se o `echo` sair vazio (link com nome em vez de IP), passe o diff pelo mapa reverso do PC.

## Achado novo da triagem

### X01 · ALTO · o backup e a restauração deixam fora o estado do governador e as regras vivas da catraca

| | |
|---|---|
| **Onde** | `ozav/deploy/backup.sh` (lista do patch 06 da 15) e `ozav/deploy/restaurar-estado.sh` (lista do patch 07 da 15) × `whatsapp-governador.js:91` e `catraca.js:178` (pacote "Ozav · envio") |
| **Patch** | `patches/01-backup-leva-estado-do-governador.diff` (já dentro do `aplicar/infra-vps.diff`) |
| **Teste** | `testes/estado-do-governador.test.js`: falha só com a 15 e passa com o X01. As outras 7 da 15 seguem ok |
| **Confiança** | alta no mecanismo, lido no código; baixa na frequência, porque só pesa no dia de restaurar |

**Os arquivos que ficam fora.** O código do envio chama os dois de "estado do servidor, fora do deploy":
- `whatsapp-governador.json` guarda `disjuntor_tudo_ate`, `disjuntor_novas_ate`, `aquecimento_desde` e `pausa_ate`;
- `catraca-regras.json` guarda as regras vivas editadas no servidor.

**Cenário:** o 463 arma o disjuntor (patch 01 da 18), e a VPS cai antes de ele vencer. Restaurado o pacote, o governador lê `ENOENT` e volta ao padrão. O volume volta ao normal no meio da restrição, sem aviso.

O patch 03 da 12 não pega esse caso: ele trata arquivo ilegível, e aqui o arquivo não existe.

**Patch:** os dois nomes entram nas duas listas (2 linhas).

## Outros cruzamentos conferidos

- **12 e 18** mexem no `whatsapp-governador.js`. Aplicados em ordem, o 18 entra com deslocamento de 13 linhas, sem conflito. Testado nas duas suítes.
- **14 e 20** mexem no `lib/portao.js`. A ordem não importa.
- **12, 13 e 18 mudam arquivos dentro de `lib/` e `whatsapp/lib/`** (`conta-nominal`, `custos`, `outbox`). O `subir.sh` reinicia as capturas quando a assinatura dessas pastas muda.

  O `whatsapp-governador.js` e o `catraca.js` ficam na raiz, fora da assinatura. Por isso o deploy indicado é com `--reiniciar`, fora do horário comercial e com o OK do dono.

- **Guarda (16, patch 05) × manutenção da Ozav:** a guarda barra todo comando Bash que cita `~/.ozav`, não só leitura. Testado aqui:
  - barra o `sed -i "/^OZAV_CANAL/d" ~/.ozav/.env` (o conserto que o próprio `subir.sh` sugere), o `chmod 600 ~/.ozav/.env` e `tar tzf <pacote> | grep .ozav`;
  - deixa passar o `ssh ... restaurar-estado.sh ... --seco` e os testes.

  É o desenho da 16 (peça ao dono ou use o script). Esses comandos o dono roda à mão. BAIXO, sem patch.
- **Segunda leitura (13, patch 09):** só age quando quem chama passa `evitarFornecedor`. O chamador não está no pacote.

## O que não deu para conferir aqui

- O dreno real (`whatsapp/conectar.js`): o patch 09 da 12 depende dele chamar `outbox.marcarEnviando(m)`.
- O `claude` real, o OpenRouter real e o Whisper real.
- O servidor: nada foi conectado.
- Os testes foram rodados no Linux, não no Windows do PC. Os da VPS precisam de bash, flock e tar.
