Para 00 · Orquestrador geral · entrega 17 · prioridade 1 (decidir)

Artifact: "Nuvem · Geral · próximas frentes" https://claude.ai/artifact/G8CyPWScUMzSWiY18EHgpE

Sem código. São 10 frentes, cada uma com ganho, custo, risco e o primeiro passo (`frentes.md` e `frentes.csv`).

**As 3 que ela propõe primeiro:**
1. **Esteira de aplicação dos patches.** A triagem https://claude.ai/artifact/QiqEBkSYXwY2PX5pMQEMaT já faz metade: 6 diffs consolidados e testados em `aplicar/`, com os conflitos resolvidos. Falta o `aplicar.sh` no PC: mapa reverso → `git apply --check` → testes → aplica → reverte se quebrar.
2. **Alarme de falha calada com vigia de fora.** O `pc/vigiar-vps.js` já vai no `infra-vps.diff`.
3. **Trilha de compliance da Veedha:** registro de 5 anos e barreira de anexo (V01 e V02 da 19, ainda sem teste).

**Decidir:**
- as 3 primeiras;
- a ordem do resto (saúde do número, dieta de contexto, biblioteca de modelos, prospecção, canal contador, vídeo, Olami).

**Só com dado real:**
- o volume semanal de mensagens que pedem OK;
- os vídeos por semana;
- as listas montadas à mão;
- o ticket e a conversão do canal contador.
