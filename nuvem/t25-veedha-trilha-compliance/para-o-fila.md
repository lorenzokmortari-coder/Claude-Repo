# Para o `fila.js`: o registro de saída como pré-condição do envio (V01.6)

O `fila.js` não está no pacote, então este trecho é para colar no PC.

A lógica toda está no `lib/registro.js` (`registrarSaida`), que tem teste aqui. No `fila.js` entram só a função abaixo e uma chamada.

## 1. A função, perto dos outros `require` do `fila.js`

```js
// V01 (tarefa 25 da nuvem, 14/10/2026): registro de 5 anos do que sai, ANTES do envio.
// Se nao gravou, lanca (code SEM_REGISTRO) e a mensagem nao sai: registro e pre-condicao, nao efeito.
const registroDeSaida = require('./lib/registro');
function exigeRegistroDeSaida(item, julgamento, opcoes) {
  // item: { id, destino, canal, texto, aprovadoPor, aprovadoEm, anexos }
  // julgamento: o resultado de portao.verificar(texto, contexto) na hora da saida
  return registroDeSaida.registrarSaida(item, julgamento, opcoes);
}
```

E no `module.exports` do `fila.js`, acrescente `exigeRegistroDeSaida`.

## 2. Onde chamar

A chamada vai no ponto em que a fila libera a mensagem para o canal: o `proximo()`, ou o que entrega ao dreno. Ela entra:
- **depois** do novo julgamento do portão na hora da saída (R46);
- **antes** de entregar ao canal (`sendMessage`, e-mail).

```js
let gravado;
try {
  gravado = exigeRegistroDeSaida(item, julgamento);
} catch (e) {
  // nao sai: o item fica na fila, retido, com o motivo visivel para o dono
  item.retido = true;
  item.motivo = e.message; // "registro de saida nao gravado (...): a mensagem NAO sai"
  return null;             // ou o "nada a enviar" que o proximo() ja usa
}
// so daqui para baixo a mensagem vai ao canal
```

## 3. Como conferir

1. Mova `testes-pendentes/v01-log-de-saida.teste.js` para `testes/` e rode:
   ```
   node --test testes/v01-log-de-saida.teste.js
   ```
   Tem de dar 6/6. O V01.6 procura `exigeRegistroDeSaida` no `fila.js`.
2. **Prova de falha fechada, uma vez:** aponte `VEEDHA_DADOS` para uma pasta dentro do OneDrive e mande uma mensagem de teste. Ela tem de ficar retida, com o motivo "pasta sincronizada". Depois, volte o `VEEDHA_DADOS`.
3. Depois da primeira mensagem real:
   ```
   node lib/registro.js verificar
   ```
   Tem de mostrar "registro integro: 1 registro(s)".

## O que conferir no `fila.js` real

- **Os nomes dos campos do item.** Se a fila usa outros nomes (por exemplo `para` em vez de `destino`), mapeie na chamada: `exigeRegistroDeSaida({ ...item, destino: item.para }, julgamento)`.
- **O `id` é único por mensagem.** Se o mesmo item volta para nova tentativa depois de falha no canal, o 2º registro lança "ja registrado", e isso é o certo: o registro diz o que saiu uma vez.

  Se o canal falhou e a mensagem vai de novo, registre a nova tentativa com id próprio (`<id>#2`). Registrar só depois que o canal confirmar não serve: aí a mensagem sairia antes do registro, e o contrato do V01 pede o contrário.
