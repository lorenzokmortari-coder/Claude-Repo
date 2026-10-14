Para 01 · Infra e robôs · entrega 15 · prioridade 1

Artifact: "Nuvem · Infra · modos de falha da VPS" https://claude.ai/artifact/BHrM2sja7RRUZFGALma6c9
Consolidado em aplicar/infra-vps.diff na triagem https://claude.ai/artifact/QiqEBkSYXwY2PX5pMQEMaT: o todos.diff da 15 mais o X01.

**Antes de tudo:** renovar o contrato da VPS até 17/10 (vence em 18/10) e tirar um snapshot novo.

Na raiz do pacote "Infra · VPS":
```
cp -r <t24>/aplicar/testes/infra-vps/. .
node --test testes/vps-falhas.test.js testes/estado-do-governador.test.js   # 8 falham
patch -p1 < <t24>/aplicar/infra-vps.diff
node --test testes/vps-falhas.test.js testes/estado-do-governador.test.js   # 8 ok
```

Depois, cada arquivo vai para o seu lugar:
- `ozav/deploy`: pelo `subir.sh`;
- `fred/fred-motor`: pelo caminho do personagem;
- `pc/vigiar-vps.js`: no Agendador, de 30 em 30 min.

**X01 (ALTO, novo):** o backup e a restauração não levavam o `whatsapp-governador.json` (disjuntor, pausa e aquecimento) nem o `catraca-regras.json`. Perdida a VPS, o disjuntor sumia no meio de uma restrição.

**Decidir:**
- `restaurar-estado.sh --seco` num pacote real;
- desligar a expiração da chave do Tailscale.
