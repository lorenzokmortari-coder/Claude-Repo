# Para a 00 · tarefa 20 · Nuvem · Veedha · modelos à prova do portão

**O que é:** 30 modelos de mensagem a cliente (vencimento, carência, aporte, resgate, cupom, Copom, documento, reunião, cliente sumido e outros) no estilo de 11/10, rodados no portão real.
- 10 deles passam na carga como candidatos a LIVRE.
- Todos são propostas: nada vale sem a aprovação do Lorenzo, um por um.

**Status:** completo. Achei um furo no portão (F01, ALTO): a dispensa de rodapé deixa sair "renda fixa", "bitcoin", "título público", "multimercado", "depósito", "pix" e "TED" sem rodapé. O patch 01 corrige, com teste.

**Comandos (na pasta do motor, já com o `redteam/` da tarefa 14):**
```
cp -r <entrega>/modelos20 . && cp <entrega>/testes/*.js testes/
node --test testes/dispensa.teste.js testes/modelos20.teste.js   # 2 falham hoje
patch -p1 < <entrega>/patches/01-dispensa-de-rodape-respeita-produto-e-dinheiro.diff
node --test testes/dispensa.teste.js testes/modelos20.teste.js && VEEDHA_VAULT=./vault node testes/portao.teste.js
```
Aplica junto com o `todos.diff` da tarefa 14.

**Donas:** 23 · Veedha · Motor (patch) e 20 · Veedha · Orquestrador (aprovar modelos).

**Prioridade:** 1 para o patch (ALTO com teste); 2 para os modelos.

**Decidir:**
- quais modelos aprovar;
- se amplia as aberturas neutras da carga ("bem vindo", "vi a sua ligação").

**Só com dado real:** rodar o `modelos20/rodar.js` com os nomes de produto de verdade antes de aprovar.
