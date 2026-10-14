Para 13 · Ozav · Motor e CRM · entrega 12 · prioridade 1

Artifact: "Nuvem · Ozav · auditoria da catraca" https://claude.ai/artifact/VLDe1MYMQhLLQDhg3vvsnK
Consolidado 12 + 18 em aplicar/ozav-envio.diff na triagem https://claude.ai/artifact/QiqEBkSYXwY2PX5pMQEMaT (<t24> = pasta baixada dela).

Na pasta do CRM no PC:
```
cp -r <t24>/aplicar/testes/ozav-envio/. .
node --test testes/catraca-auditoria.test.js testes/banimento.test.js   # 16 falham
patch -p1 < <t24>/aplicar/ozav-envio.diff
node --test testes/*.test.js && node catraca.js --harness && node whatsapp-governador.js --testar
```

**O que corrige:**
- 6 CRÍTICOS:
  - painel ilegível solta e apaga travas;
  - duplicata depois de queda;
  - dois robôs na mesma conversa;
  - trava que não casa nome com emoji;
  - conta nominal com espaço duro.
- 3 ALTOS.

Na nuvem: 33 + 20 + 8 ok, harness igual antes e depois.

**Com o OK do dono:** `./deploy/subir.sh --reiniciar`, fora do horário comercial.

**Conferir:** o 09 só protege se o dreno chamar `outbox.marcarEnviando(m)` antes do `sendMessage`.

**Decidir:**
- falhar fechado (R4);
- véspera de dia santo depois das 17h;
- Shabbat.
