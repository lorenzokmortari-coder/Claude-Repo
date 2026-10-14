Para 02 · Setup do Claude · entrega 16 · prioridade 1

Artifact: "Nuvem · Setup · revisão do Claude Code" https://claude.ai/artifact/T3igcdiV2nsqPbRmTiFEsx
Consolidado em aplicar/setup-claude.diff na triagem https://claude.ai/artifact/QiqEBkSYXwY2PX5pMQEMaT. É o todos.diff da 16; os 5 aplicam em sequência sem conflito.

Na raiz do pacote "Setup · Claude Code":
```
cp -r <t24>/aplicar/testes/setup-claude/. .
node --test testes/hooks.test.js   # 5 falham
patch -p1 < <t24>/aplicar/setup-claude.diff
node --test testes/hooks.test.js   # 6 ok
```
Depois:
- os 3 arquivos vão para `~\.claude\hooks\` e `OneDrive\Claude\automacao\`;
- o bloco `PreToolUse` da guarda entra no `settings.json`.

**Hoje:**
- o `faca-em-10-minutos.md`;
- o K1 a K3 do `skills.md` (CRÍTICOS: `/followup`, `/fechamento` e `/cliente` disparando fora da Ozav).

**Esta semana:** os patches 02 a 04 e a dieta.

**Saiba:** a guarda barra todo comando que cita `~/.ozav`, inclusive manutenção, como o `sed` do `OZAV_CANAL` que o `subir.sh` sugere. Esse o dono roda à mão.

**Conferir no PC:**
- se o Stop do plugin falha a cada resposta;
- se o `PreToolUse` com saída 2 barra com o bypass ligado.
