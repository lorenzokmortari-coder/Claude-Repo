Para 13 · Ozav · Motor e CRM · entrega 18 · prioridade 1

Artifact: "Nuvem · Ozav · risco de banimento no WhatsApp" https://claude.ai/artifact/JVuhY21FGroBjuuWgEH2AZ

Os 2 patches já vão no aplicar/ozav-envio.diff da triagem https://claude.ai/artifact/QiqEBkSYXwY2PX5pMQEMaT, junto com a 12. Não aplicar de novo. No `whatsapp-governador.js` é só deslocamento de linhas, sem conflito.

**Teste:** `testes/banimento.test.js`. Antes falham 6 de 8; depois passam os 8.

**W01 (ALTO):** o erro 463 ("reach-out timelock") não armava o disjuntor nem avisava.

**No servidor, depois do deploy:** `node whatsapp-governador.js --sem-resposta`. Ele só mede: o teto fica em 0.

**Decidir:**
- se liga `OZAV_WPP_SEM_RESPOSTA_30D`, e com que número;
- o teste do Baileys 7.x num número de laboratório;
- a rotina de abrir o celular a cada 10 dias;
- o `plano-b.md`: a lista de e-mail dos clientes ativos e o aviso que o dono aprova antes.

**Só com dado real:**
- o texto que o dreno passa ao `sinal()`;
- quantas mensagens sem resposta saem por mês;
- se o `hunting.js` usa `onWhatsApp`;
- quantos clientes ativos não têm e-mail no CRM.
