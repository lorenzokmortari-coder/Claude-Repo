# Modelos à prova do portão: achados (Veedha, 14/10/2026)

**Como foi testado:**
- As 30 propostas de `modelos20/modelos.json` rodaram no `lib/portao.js` real, pelo executor da tarefa 14 (`redteam/executor.js`), em três cópias:
  1. o portão de hoje;
  2. o de hoje com o patch 01 desta tarefa;
  3. o de hoje com os 7 patches da tarefa 14 e mais o patch 01.
- O runner é o `modelos20/rodar.js`, e os testes são `node --test testes/modelos20.teste.js testes/dispensa.teste.js`.

**Resultado:**

| Portão | Modelos com o veredito esperado | Testes desta tarefa | Bateria antiga | Red team da 14 |
|---|---|---|---|---|
| de hoje | 28 de 30 (M29 e M30 saem sem rodapé no config real) | 2 de 4 | 773 ok | (8 falham, como hoje) |
| hoje + patch 01 | 30 de 30 | 4 de 4 | 773 ok | (8 falham, como hoje) |
| hoje + patches da 14 + patch 01 | 30 de 30 | 4 de 4 | 773 ok | 8 de 8 |

O corpus de 392 mensagens da tarefa 14, no config real, dá o mesmo veredito caso a caso com e sem o patch 01: o patch não muda nenhum resultado já medido.

## F01 · A dispensa de rodapé deixa sair produto e movimentação de dinheiro (ALTO, confiança alta)

**Onde:**
- `lib/portao.js:2213` (`SINAL_DE_DINHEIRO`);
- `lib/portao.js:2243-2253` (`ehConversaPura`).

**Regra:**
- C7 do LEIA-ME: a decisão do Lorenzo, de 23/09/2026, é que "achou produto, número, valor, prazo [...], o rodapé volta a ser obrigatório".
- Res. CVM 178, art. 24 (o rodapé identifica o intermediário, o assessor contratado e a ouvidoria).

**Cenário:**
- **Entrada:** o config real tem o rodapé oficial vazio. Seguem mensagens que o próprio portão marca como "termo financeiro (produto)" ou que falam de mover dinheiro:
  - "A XP publicou um relatório novo sobre renda fixa...";
  - "Queria te mostrar uma ideia de bitcoin";
  - "Tem um título público...";
  - "Queria falar do multimercado...";
  - "Que tal a gente olhar renda variável...";
  - "Os dados pra depositar na sua conta da XP...";
  - "Faz o pix pra sua conta da XP";
  - "A TED pra sua conta da XP...";
  - "A transferência pra sua conta da XP...".
- **O que acontece:** saem REVISAR, sem rodapé. A dispensa usa uma lista própria (`SINAL_DE_DINHEIRO`) que não conhece esses produtos nem esses meios de pagamento.
- **O que devia acontecer:** BLOQUEADO pela R08 enquanto o rodapé oficial não existir.

**Por que é ALTO:** é fuga para REVISAR, não para LIVRE. Mas a mensagem com produto chega ao cliente sem a identificação do art. 24 se o Lorenzo aprovar sem notar, e o portão mostra "rodapé dispensado: conversa pura".

**Patch 01** (`patches/01-dispensa-de-rodape-respeita-produto-e-dinheiro.diff`), com duas linhas:
- a dispensa cai quando o próprio portão achou "termo financeiro (produto)";
- `SINAL_DE_DINHEIRO` ganha depósito, pix, TED, transferência e boleto.

Os 5 modelos aprovados e a conversa pura continuam dispensando o rodapé (D02 e D03).

**Evidência:** D01 falha antes e passa depois, e o M29 e o M30 do `modelos20.teste.js` também.

**Ponto escolhido de propósito:** "relatório", sozinho, não desfaz a dispensa. O modelo aprovado `relatorio_disponivel_v1` depende disso, e a bateria antiga confere.

## O que a carga dos modelos LIVRE recusa (observações, sem patch)

O portão aceita como modelo LIVRE só o que passa pela lista fechada de pedidos (C29). Na prática, ao escrever, quatro coisas apareceram:

| Frase | O que a carga diz | O que fiz |
|---|---|---|
| "Vi a sua ligação e não consegui atender" (5 redações) | lê a frase sobre o que o cliente fez como pedido fora da lista | M11 fica como proposta REVISAR (`candidato_livre: false`) |
| "Seja bem vindo", "bem vindo!" | idem | M05 reescrito: "Feliz de começar esse trabalho com vc" |
| "comprovante de residência" | "comprovante" é assunto de dinheiro para a carga | M02 reescrito com "endereço" |
| "Tá na hora da nossa conversa", "Segue de pé?", "precisei mexer na agenda" | pedido fora da lista | reescritos com "queria marcar" ou "me fala outro horário" |

Isso não é furo de segurança: a carga erra para o lado de recusar, que é o desenho. Se o Lorenzo quiser essas frases, o caminho é ampliar a lista de aberturas neutras (`ABERTURA_NEUTRA`), e é decisão dele.

## O que o portão pede nos modelos com produto

- **Troca** (vender X e aplicar em Y; resgatar e aplicar):
  - o custo total vai escrito no texto, e o número sai da simulação da XP, declarado em `fonteDeNumeros` com `temCustoTotal: true`, senão barra pela R20;
  - "reinvestir" também é lido como troca: os modelos usam "aplicar esse valor".
- **Posse com valor:** "seu" ou "sua" em qualquer lugar da mensagem, junto de qualquer valor (o custo total é um valor), barra como extrato (R14, falso positivo aceito D16). Por isso o M18 fala "a carência da LCI", e não "do seu".
- **Perfil:** produto só com perfil válido (R15 e R16). O contexto de teste é cliente com perfil moderado válido. Para quem não tem perfil, todo modelo com produto barra, como deve.

## O que não consegui testar

- **A voz do `conferir.js`** (travessão, fórmula de IA, emoji): ela depende do `redigir.js`, que não está no pacote.
- **A segunda leitura de sentido (C31) e a aprovação nominal do Lorenzo:** ficam fora do código.
- **Mensagem real:** os exemplos são sintéticos. Com nomes reais de produto, o detector pode reagir diferente; vale rodar o `modelos20/rodar.js` com os produtos de verdade antes de aprovar.
