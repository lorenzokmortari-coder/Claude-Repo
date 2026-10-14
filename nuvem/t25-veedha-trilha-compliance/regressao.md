# Regressão da tarefa 25 (antes × depois)

**Base:** pacote "Veedha · portão" + `veedha-portao.diff` da triagem 24 + `aplicar/testes/veedha-portao/` + os 2 testes de `testes-pendentes/`.

**Depois:** a mesma base com `patches/25-trilha.diff` e `patches/25-nota-do-vault.diff` aplicados por `patch -p1 --fuzz=0`. Com `git apply` o resultado é idêntico.

Linux, Node 22.22, `VEEDHA_VAULT=./vault`, 14/10/2026.

| Suíte | Antes | Depois |
|---|---|---|
| Bateria `testes/portao.teste.js` | 773 ok, "todos passaram" | 773 ok; saída idêntica, fora a linha que mede o tempo (44–98 ms nas duas, teto de 3.000 ms) |
| `testes/redteam.teste.js` | 8/8 | 8/8 |
| `testes/dispensa.teste.js` | 3/3 | 3/3 |
| `testes/modelos20.teste.js` | 1/1 | 1/1 |
| Corpus do redteam, 392 casos, caso a caso (config de teste) | 0 fuga para LIVRE; 9 fugas e 8 alarmes, todos marcados "aberto" | **idêntico**: o mesmo CSV, byte a byte |
| Corpus do redteam com o config real (rodapé vazio) | o retrato de hoje | **idêntico**, byte a byte |
| `modelos20/rodar.js`, 30 modelos nas 3 conferências | 30/30 | **idêntico**, byte a byte |
| `testes-pendentes/v02-anexo.teste.js` (dona) | 2/6 | **6/6** |
| `testes-pendentes/v01-log-de-saida.teste.js` (dona) | 0/6 | **5/6** no pacote; **6/6** com o `fila.js` de teste (o bloco do `para-o-fila.md`) |
| `testes/registro.teste.js` (novo) | 0/12 (o módulo não existia) | 12/12 |
| `testes/anexo-extra.teste.js` (novo) | 0/8 | 8/8 |
| `testes/conferir.teste.js` | falha: falta `./coletor/coletar` no pacote | falha igual (não é desta tarefa) |

Nenhum caso que passava piorou. Os casos do corpus não têm anexo, então o veredito deles não poderia mudar. A comparação byte a byte prova que não mudou.
