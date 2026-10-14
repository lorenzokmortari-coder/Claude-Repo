# Para a 00 · tarefa 25 · trilha de compliance

**O que é:**
- V01: o registro de 5 anos do que sai, em `lib/registro.js`;
- V02: o anexo no portão, regra R55.

**Status:** completo.
- Os 2 testes da dona estão verdes. O V01.6 depende do `fila.js`.
- Nenhuma piora: 773 ok, 12/12, e os 392 casos e os 30 modelos idênticos.

**Dona:** 23 · Veedha · Motor. **Prioridade:** 1.

**Só com a XP ou dado real:**
- o prazo e o formato da guarda;
- se a agenda de vencimento conta como extrato;
- se o texto extraído do anexo basta;
- a cópia do registro.

## Mensagem para a 23

Artifact "Nuvem · Veedha · trilha de compliance" https://claude.ai/artifact/Ub1dR6f6dakHS6GEXncJ2X

Por cima do `veedha-portao.diff` da triagem:
1. Na raiz do motor: `patch -p1 < patches/25-trilha.diff`
2. Na raiz do vault: `patch -p1 -d <vault> < patches/25-nota-do-vault.diff`. Se recusar, cole a linha da R55 à mão.
3. Mova os 2 testes de `testes-pendentes/` para `testes/`.
4. Cole o trecho do `para-o-fila.md` no `fila.js`.

**Testar:** `node --test` nos 4 testes (v01, v02, `registro`, `anexo-extra`): 32 ok. O harness de sempre: 12/12, com a bateria igual.

**O que muda:**
- anexo sem texto extraído sai BLOQUEADO;
- com anexo, nunca LIVRE;
- sem registro gravado, a mensagem não sai.

**Decidir:**
- a cópia do registro, fora do OneDrive;
- quem aprova anexo pelo hash;
- as perguntas à XP, em `conferir-com-a-XP.md`.
