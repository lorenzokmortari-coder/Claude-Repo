# Para a 00 · tarefa 18 · Nuvem · Ozav · risco de banimento no WhatsApp

**O que é:** gatilhos de restrição e de ban (2025–2026) × governador, catraca e convivência. São 2 patches com 8 testes, mais o plano B.

**Status:** completo. As páginas oficiais estavam bloqueadas na rede: o oficial veio do trecho do buscador.

**Comandos (na pasta do pacote ozav-envio):**
```
cp <entrega>/testes/banimento.test.js testes/
node --test testes/banimento.test.js   # 6 de 8 falham antes
patch -p1 < <entrega>/patches/todos.diff
node --test testes/*.test.js && node whatsapp-governador.js --testar
node whatsapp-governador.js --sem-resposta   # no servidor
```
Aplica limpo junto com o todos.diff da tarefa 12.

**Dona:** 13 · Ozav · Motor e CRM.

**Prioridade:** 1. O W01 é ALTO: o erro 463 ("reach-out timelock", sinal de restrição) não arma o disjuntor nem avisa.

**Decidir:**
- se liga o teto de mensagens sem resposta (`OZAV_WPP_SEM_RESPOSTA_30D`, padrão 0 = só mede);
- teste do Baileys 7.x num número de laboratório;
- a rotina de abrir o celular a cada 10 dias.

**Só com dado real:**
- o texto exato que o dreno passa ao `sinal()`;
- quantas mensagens sem resposta o número faz por mês;
- se o `hunting.js` usa `onWhatsApp`;
- quantos clientes ativos não têm e-mail no CRM.
