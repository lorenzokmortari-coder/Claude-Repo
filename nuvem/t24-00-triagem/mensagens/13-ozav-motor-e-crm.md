Para 13 · Ozav · Motor e CRM · entrega 13 · prioridade 1

Artifact: "Nuvem · Ozav · auditoria do gateway LLM" https://claude.ai/artifact/Dx7sA5hvyaCuV8ydxzTrxz
Consolidado em aplicar/ozav-gateway-llm.diff na triagem https://claude.ai/artifact/QiqEBkSYXwY2PX5pMQEMaT. É o todos.diff da 13. Aplicados em sequência, o 09 e o 11 batem no 03.

Na pasta do CRM (o patch 05 tem o marcador <IP_VPS>, lido do próprio llm.js):
```
cp -r <t24>/aplicar/testes/ozav-gateway-llm/. .
IP=$(grep -oE 'http://[0-9.]+:8778' llm.js | head -1 | cut -d/ -f3 | cut -d: -f1); echo $IP
sed "s/<IP_VPS>/$IP/g" <t24>/aplicar/ozav-gateway-llm.diff | patch -p1
node --test testes/gateway-falhas.test.js && node llm.js --testar-plano
```

**7 ALTOS:**
- timeout repetido 4x;
- resposta vazia ou cortada passa como sucesso;
- 402 sem aviso;
- teste de lote come o orçamento da função;
- teto do processo nunca zera;
- 6 `claude` numa VPS de 1 vCPU;
- segunda leitura no mesmo fornecedor.

Na nuvem: 17/17 + 1 todo, e os harnesses passam. Aplica junto com o ozav-envio.diff.

**Decidir:** passar `evitarFornecedor` na segunda leitura, porque sem isso o 09 não age.
