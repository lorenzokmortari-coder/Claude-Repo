# Trilha de compliance da Veedha (tarefa 25, 14/10/2026)

Fecha os dois ALTOS da tarefa 19:
- **V01:** o registro de 5 anos do que sai.
- **V02:** o anexo que o portão não lia.

O alvo são os 2 testes que a conversa dona escreveu em `testes-pendentes/`.

## Ordem de aplicação

1. **Base.** É o pacote "Veedha · portão" com o `aplicar/veedha-portao.diff` da triagem 24 e a pasta `aplicar/testes/veedha-portao/`. É o que o PC já tem.
2. **Código, na raiz do motor:**
   ```
   patch -p1 --dry-run < patches/25-trilha.diff && patch -p1 < patches/25-trilha.diff
   ```
   O que muda:
   - muda `lib/portao.js`;
   - cria `lib/registro.js`, `config/anexos-aprovados.json`, `testes/registro.teste.js` e `testes/anexo-extra.teste.js`.
3. **Nota do vault, na raiz do vault** (a pasta `cerebro-veedha`, a mesma que o `lib/vault.js` acha):
   ```
   patch -p1 -d "<pasta do vault>" < patches/25-nota-do-vault.diff
   ```
   Ele acrescenta só a linha da R55 depois da linha da R51 em `08-Regulatorio/O que o robo nunca pode fazer.md`. O arquivo é CRLF.

   Se a nota do PC estiver diferente do recorte do pacote e o patch recusar, cole à mão a linha `| R55 | ...` que está no diff. A bateria confere nota × código e acusa se faltar.
4. **Testes pendentes viram testes:** mova `testes-pendentes/v01-log-de-saida.teste.js` e `testes-pendentes/v02-anexo.teste.js` para `testes/`.
5. **`fila.js`:** cole o trecho de `para-o-fila.md` (V01.6).

## Testar

```
node --test testes/v01-log-de-saida.teste.js testes/v02-anexo.teste.js testes/registro.teste.js testes/anexo-extra.teste.js
node --test testes/redteam.teste.js testes/dispensa.teste.js testes/modelos20.teste.js
node testes/portao.teste.js
node lib/portao.js
```
O que esperar:
- **1º comando:** 32 ok (6 + 6 + 12 + 8).
- **2º comando:** 12 ok.
- **Bateria:** a mesma contagem de antes. No pacote, com `VEEDHA_VAULT=./vault`, são 773.
- **`node lib/portao.js`:** mostra "anexos aprovados ... NENHUM".

Na nuvem, sem o `fila.js`, o V01.6 falha. Montei um `fila.js` de teste com o bloco do `para-o-fila.md`, tal como está, e com ele o V01 deu 6/6.

## V02: o anexo no portão (regra R55)

**O formato.** `verificar(texto, contexto)` aceita `contexto.anexos = [{ nome, texto?, sha256? }]`.

**O que acontece com cada anexo:**

| Anexo | Veredito |
|---|---|
| Sem `texto` extraído (ou com texto vazio) e sem `sha256` aprovado | **BLOQUEADO R55**, norma `res178-art25-VII`. Nunca REVISAR |
| Com `texto` | O texto passa pelos mesmos detectores do corpo: extrato, posição, rentabilidade, promessa, senha, ofuscação e os demais. O motivo diz qual anexo barrou. Produto no anexo aciona o suitability, como no corpo |
| Legível e inofensivo | Não barra |

**Em qualquer caso com anexo:**
- nunca LIVRE, nem com instância de modelo aprovado;
- não há dispensa de rodapé, porque anexo é material.

**Lista malformada:** `anexos` que não é lista, item sem `nome`, `texto` que não é texto ou acima de 400 mil caracteres → BLOQUEADO R35.

**Sem `anexos`, ou com lista vazia:** nada muda.

**Aprovar um arquivo pelo hash.** Fica em `config/anexos-aprovados.json`, **vazio por padrão**. Cada entrada precisa de:
- o `sha256` do arquivo;
- `aprovadoPor` da lista fechada de aprovadores do `config/modelos.json`;
- `aprovadoEm` com data passada.

Entrada fora disso não aprova nada. Para tirar o hash:
```
node -e "console.log(require('crypto').createHash('sha256').update(require('fs').readFileSync(process.argv[1])).digest('hex'))" arquivo.pdf
```

**O que fica de fora do anexo.** O número sem lastro (R33) e a citação (R34) continuam olhando só o corpo. Um PDF institucional tem CNPJ, endereço e telefone, que o R33 barraria. No anexo, valor de posição e taxa já barram pelos R14, R25 e R26.

## V01: o registro de saída (`lib/registro.js`)

**API:**
- `registrar(saida, { raiz })`, `ler({ raiz })`, `consultar(...)`, `verificarCadeia(...)`, `podeExpurgar(reg, agora)`, `registrarSaida(item, julgamento)` (a que a fila usa);
- `RETENCAO_ANOS = 5`;
- nenhuma função de apagar.

**Onde mora:** `%VEEDHA_DADOS%\registro-de-saida`. Sem a variável, `%USERPROFILE%\veedha-dados\registro-de-saida`, a mesma pasta de dados do `conferir.js`. Se o caminho cair no OneDrive, Dropbox, Google Drive ou iCloud (inclusive por link ou junction), ele recusa, e a mensagem não sai.

**O que cada linha guarda:**
- destino, canal e texto integral;
- veredito do portão e regras;
- aprovadoPor e aprovadoEm;
- a hora da mensagem e a hora do servidor;
- o id da fila;
- os anexos (nome e sha256).

**Como grava:**
- só acréscimo, um arquivo por ano (`registro-AAAA.jsonl`);
- cada linha leva o hash da anterior, e a cadeia atravessa a virada do ano;
- trava entre processos, `fsync`, arquivo 600.

**O que recusa (falha fechada):**
- veredito BLOQUEADO;
- REVISAR sem aprovação;
- id repetido;
- campo faltando;
- arquivo corrompido ou cadeia quebrada.

**Comandos:**
```
node lib/registro.js verificar                 # integro, ou a 1a linha adulterada (arquivo:linha), saindo com 1
node lib/registro.js consultar --destino 5511900000001 --de 2026-03-01 --ate 2026-03-31
```

**Expurgo.** `podeExpurgar(reg, agora)` só responde. Quem expurga é gente, depois dos 5 anos.

**Desempenho.** Cada `registrar` relê e confere a cadeia inteira. Para o volume de um escritório (milhares de mensagens por ano) é instantâneo. Se passar de centenas de milhares de linhas, vale guardar um índice.

## O que não está aqui

- **A cópia de segurança do registro.** São 5 anos de guarda, e o disco do PC sozinho não é guarda. O OneDrive não pode: é decisão do dono. Ver `conferir-com-a-XP.md`.
- **O extrator de texto de PDF ou imagem.** É quem chama o portão que extrai e manda em `anexos[].texto`. O portão julga o texto que recebe.
