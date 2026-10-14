# Para a 00 · tarefa 24 · triagem das entregas 11 a 23

**O que é:** as entregas 11 a 23 por prioridade, uma linha cada. Patches aplicados em cópias limpas, suítes inteiras rodadas; 6 diffs prontos em `aplicar/` e uma mensagem por dona em `mensagens/`.

**Status:** completo, as 13 entregas publicadas.

**X01 (ALTO, novo):** o backup e a restauração da VPS não levavam o disjuntor do governador. A correção já está no `infra-vps.diff`.

**Prioridade 1, aplicar hoje:**
- **15 VPS → 01 Infra.** Renovar o contrato até 17/10 e tirar snapshot. `infra-vps.diff`, 4 CRÍT. + 3 ALTO + X01: 8/8.
- **12 Catraca + 18 Banimento → 13 Motor e CRM.** `ozav-envio.diff`, 6 CRÍT. + 4 ALTO: 33 + 20 + 8 ok. Deploy com `--reiniciar`.
- **13 Gateway → 13 Motor e CRM.** `ozav-gateway-llm.diff`, 7 ALTO: 17/17. O `<IP_VPS>` sai com o comando da mensagem.
- **14 Red team + patch da 20 → 23 Veedha Motor; decisões na 20.** `veedha-portao.diff`: 773 + 12 ok.
- **16 Setup → 02 Setup.** Fazer o `faca-em-10-minutos` e o K1–K3 (CRÍT.). `setup-claude.diff`: 6/6.
- **17 Próximas frentes → 00 Orquestrador geral.** Decidir as 3 primeiras. Esta triagem já é metade da 1ª.
- **23 Legenda v2 → 31 Fred Conteúdo.** `fred-legenda.diff` ou `v2/`: 29/29.

**Prioridade 2, esta semana:**
- **20 Modelos → 20 Veedha Orquestrador.** Aprovar um por um; os de produto dependem do rodapé (19).
- **19 Obrigações do AAI → 23 e 20 Veedha.** V01 e V02 ALTO, ainda sem teste; perguntas à XP.
- **22 E-mail frio → 13 e 16 Hunting.** Script com 33 testes; 4 semanas de aquecimento antes do 1º e-mail frio.
- **21 Publi → 32 Fred Comercial.** Checklist à agência; decidir bet.

**Prioridade 3, guardar:**
- **11 Canais → 10 Orquestrador e 17 Canhões.** Pesquisa só por busca; decidir a oferta ao contador.

**Como aplicar:** `cp -r aplicar/testes/<pacote>/. .`, rodar os testes (falham), `patch -p1 < aplicar/<pacote>.diff`, rodar de novo (passam). Os comandos exatos estão em cada mensagem.

**Conflitos resolvidos:**
- na 13, o 09 e o 11 batem no 03;
- na 15, o 06 bate no 03.

12 com 18 e 14 com 20 só deslocam linhas.

**Só com dado real:**
- o dreno (`marcarEnviando`);
- o IP do `llm.js`;
- o `restaurar-estado.sh --seco` num pacote real;
- os vídeos de 14/10;
- o corpus do escritório;
- o DNS novo;
- os hooks no Windows.
