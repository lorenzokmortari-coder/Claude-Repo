# Risco de banimento no WhatsApp: achados (Ozav · envio, 14/10/2026)

**Escopo:** o que protege o número do WhatsApp Business da Ozav (sessão Baileys no servidor) contra restrição e banimento: `whatsapp-governador.js`, `whatsapp-convivencia.js`, `catraca.js` e `whatsapp/lib/outbox.js`, do pacote "Ozav · envio". As linhas são do código original, sem patch.

**Como foi testado:** offline, com `node --test testes/banimento.test.js` (Node 22.22). O estado e o livro do governador ficam numa pasta temporária, e o banco da captura fica em memória (`node:sqlite`, mesma tabela `mensagens`).

**Resultado:**
- Antes dos patches, 6 dos 8 testes falham. Com os dois patches, os 8 passam.
- Os 33 testes do pacote e o `governador --testar` passam antes e depois. O `convivencia --harness` também passa depois.
- O `catraca --harness` dá 148 de 158 antes e depois. As 10 falhas vêm da limpeza do pacote.
- Os dois patches aplicam limpos por cima do `todos.diff` da tarefa 12, só com deslocamento de linhas, e as suítes das duas tarefas passam juntas: 28 testes e 1 pendente da 12, mais os 33 do pacote.

**Fontes:** a pesquisa está em `pesquisa.md`, com a natureza de cada fonte: OFICIAL, IMPRENSA ou COMUNIDADE. Nenhuma página oficial abriu nesta rede: tudo o que é oficial veio do trecho mostrado pelo buscador e está marcado "não verificado".

| # | Gravidade | Confiança | Em uma linha | Patch |
|---|---|---|---|---|
| W01 | ALTO | média | Erro 463 ("reach-out timelock") e os outros sinais de restrição não armam o disjuntor | 01 |
| W02 | MÉDIO | baixa | Ninguém mede as mensagens mandadas a quem não responde, e o WhatsApp testa um teto mensal disso | 02 |
| W03 | MÉDIO | baixa | Baileys `^6.7.9`: a comunidade diz que o 463 só é tratado a partir do 7.0.0-rc13 | sem patch (teste num número de laboratório) |
| W04 | MÉDIO | média | Celular principal 14 dias sem abrir o app desconecta os aparelhos vinculados (o servidor cai) | sem patch (rotina) |
| W05 | BAIXO | baixa | Sessão num IP de datacenter aparece em relatos como agravante | sem patch (registro) |
| W06 | — | — | Os Termos do WhatsApp Business App (em vigor desde 23/09/2026, segundo o trecho do buscador) proíbem acesso automatizado | decisão do dono |

---

## W01 · Sinal de restrição não arma o disjuntor (ALTO, confiança média)

**Onde:** `whatsapp-governador.js:106`. É a expressão `SINAL`, usada por `sinal()` (linha 365) para armar o disjuntor e avisar o Lorenzo.

**Cenário**
- **Entrada:** o número leva uma restrição. Pela página oficial (via trecho do buscador), uma conta restrita continua falando com quem já conversou, mas não inicia conversa nova, não cria grupo, não adiciona ninguém e perde os aparelhos vinculados. No Baileys, segundo a comunidade, isso chega como:
  - o erro `463` (`NackCallerReachoutTimelocked`, a trava de reach-out);
  - `RESTRICT_ALL_COMPANIONS`;
  - `device_removed`;
  - o aviso "not allowed to use WhatsApp" ou "subject to restrictions".
- **O que acontece:**
  - Nenhum desses textos casa com a `SINAL`. O disjuntor não arma, e ninguém é avisado no Slack.
  - O dreno trata o erro como falha comum.
  - Pela R38–R39, interação nova volta a ser tentada no dia seguinte, e grupo novo também, ainda durante a restrição.
  - Os relatos da comunidade mostram a escalada que se segue: restrição de 24 h, depois 48 h, depois ban permanente (issue 1983 do Baileys).
- **O que devia acontecer:** a R42 diz que o sinal do WhatsApp arma o disjuntor (nada sai por 3 h, nenhuma interação nova por 48 h) e avisa o Lorenzo uma vez.

**Evidência:**
- B01 falha antes e passa depois.
- B02 é o controle: queda comum ("Connection Closed", "conflict", "restart required", "ECONNRESET") não arma.
- B03 garante que os sinais antigos continuam armando.

**Patch (01):** acrescenta `463`, `reach-out`, `timelock`, `restrict`, `device_removed` e `not allowed to use whatsapp` à `SINAL`. É uma linha, mais o comentário.

**Por que a confiança é média:**
- O texto exato do erro depende do dreno (`whatsapp/conectar.js`), que não está no pacote. Se ele passar só o número do status, sem texto, o `\b463\b` cobre. Se passar um objeto sem `toString` útil, não cobre.
- A ligação entre o 463 e a restrição é leitura da comunidade (issue 2441 do Baileys), não documento oficial.

**Lado ruim:** a palavra `restrict` pode armar o disjuntor num erro que não é de restrição de conta, como um grupo onde só admin fala. O efeito é parar 3 h e segurar interação nova por 48 h. Isso erra para o lado do número, que é a regra do dono.

---

## W02 · Ninguém mede mensagem sem resposta (MÉDIO, confiança baixa)

**Onde:** `whatsapp-governador.js:287-351` (`motivo`). O governador conta envios por hora, por dia e interação nova. Não conta quantas das nossas mensagens ficaram sem resposta.

**Cenário**
- **Entrada:** em 17/10/2025, segundo a imprensa (via trecho do buscador), o WhatsApp anunciou o teste de um teto mensal de mensagens mandadas a quem não responde, para pessoas e empresas. O número não foi divulgado, e a resposta da pessoa tira da conta as mensagens mandadas a ela.
  - A régua e a leva mandam até 60 follow-ups por dia (R47) a contatos antigos que muitas vezes não respondem.
  - Os vendedores de API citam a taxa de resposta baixa como fator de risco (COMUNIDADE).
- **O que acontece:** o número pode bater num teto que ninguém vê chegando, e o primeiro sinal é o próprio bloqueio.
- **O que devia acontecer:** saber quantas mensagens de iniciativa estão sem resposta no mês e, se o dono quiser, pôr um teto da casa.

**Patch (02):**
- O `registrar` grava o `jid` no livro.
- `semResposta(agora, db)` conta, nos últimos 30 dias e só no privado, as nossas mensagens que não são resposta e depois das quais a pessoa não escreveu.
- O `status(agora, db)` mostra o número, e `node whatsapp-governador.js --sem-resposta` imprime a conta.
- Só segura com `OZAV_WPP_SEM_RESPOSTA_30D` maior que 0. O padrão é 0, que só mede.
- Com o teto ligado e sem o banco, segura ("na dúvida, não").
- Grupo fica fora da conta: o time escreve nos grupos e contaria como resposta, e o teste do WhatsApp fala em pessoas.

**Evidência:**
- B04 a B08 falham antes e passam depois.
- O cenário tem 4 mensagens sem resposta em 2 contatos, e a conta exclui:
  - quem respondeu depois;
  - a nossa resposta;
  - o envio de 40 dias atrás;
  - o grupo;
  - a linha velha sem `jid`.

**Por que a confiança é baixa:**
- O WhatsApp não publicou o número nem confirmou o lançamento global (nada encontrado em 2026).
- O teto da casa é decisão do dono, depois de ver o número real. O comando para isso está no `para-a-00.md`.

**Limite:** as linhas do livro anteriores ao patch não têm `jid`, então a conta só fica completa 30 dias depois de aplicar.

---

## W03 · Baileys `^6.7.9` e o 463 (MÉDIO, confiança baixa, sem patch)

**Onde:** `whatsapp/package.json:12`.

**Cenário:** segundo a comunidade (issue 2441), a única correção relatada para o 463 é o Baileys 7.0.0-rc13 ou posterior, com o "tctoken". Os resultados variam, e há logout forçado sem solução no rc14. Também é comunidade o relato de mensagem 1:1 que deixou de chegar depois de uma conta restaurada e que só voltou ao atualizar o Baileys (issue 2699).

**Por que sem patch:**
- Trocar a versão principal do Baileys muda a API e não é correção mínima.
- Fazer isso no número de produção é somar dois riscos no mesmo dia, o que é contra a regra da casa.

**Proposta:** testar o 7.x num número de laboratório (um chip que não é o da Ozav) por uma semana antes de decidir.

---

## W04 · 14 dias sem abrir o app no celular derrubam o servidor (MÉDIO, confiança média, sem patch)

**Fonte:** FAQ do multi-agent no Business app, OFICIAL via trecho do buscador. Se o aparelho principal não for usado por mais de 14 dias, os aparelhos vinculados são desconectados.

**Cenário:** o celular com o número da Ozav fica guardado. No 15º dia, a captura cai, e o porteiro da captura (R46) segura a régua por buraco de mais de 26 h. O comercial para.

**Proposta:** pôr na rotina abrir o WhatsApp Business no celular do número a cada 10 dias, no máximo.
- Não conferi se o `pulso.js` avisa quando a sessão cai por isso, porque o dreno não está no pacote.
- Conferir com dado real: quando o celular foi aberto pela última vez.

---

## W05 · IP de datacenter (BAIXO, confiança baixa, sem patch)

**Fontes (COMUNIDADE):**
- Uma conta Business verificada foi restrita logo ao ler o QR num servidor de nuvem com várias conexões Baileys (issue 2805).
- Um comentário diz que IP de servidor é marcado com mais rigor (issue 2309).
- Os dois relatos são hipóteses, não medição.

**Leitura para a Ozav:** já há só um socket (R1), e o número voltou e opera desde 27/09. Registro o risco para o plano B. Se o número cair de novo logo depois de um repareamento, essa hipótese entra na forense.

---

## W06 · Termos do WhatsApp Business App (sem gravidade: decisão do dono)

Segundo o trecho do buscador, os novos "WhatsApp Terms for WhatsApp Business App" estão em vigor desde 23/09/2026 e proíbem interagir com o serviço "through automated or other means" sem consentimento por escrito. As Messaging Guidelines tratam o cliente não oficial como comportamento adverso, e o próprio README do Baileys avisa do risco.

Nenhum ajuste do governador zera esse risco. A saída definitiva seria a API oficial, que tem custo por conversa e outra operação. Isso não está na lista de decisões congeladas, mas é decisão do dono, então fica só registrado no plano B como rota de saída.

---

## O que não consegui testar

- **O dreno** (`whatsapp/conectar.js`) não está no pacote. Ficaram sem teste:
  - como o erro do Baileys chega ao `sinal()`: texto, número ou objeto;
  - se o dreno chama `governador.registrar(m, db)` com o `m.jid`;
  - presença ("digitando"), confirmação de leitura e reconexão.
- **O `hunting.js` e o `primeiro-contato.js`** (fora do pacote): não sei se usam `onWhatsApp`, `isRegisteredUser` ou `getNumberId` para conferir número antes do toque frio. A comunidade associa essas consultas repetidas a restrição (issue 3948 do whatsapp-web.js). Vale um `grep` no PC.
- **Texto oficial:** nenhuma página oficial do WhatsApp ou da Meta abriu nesta rede. Tudo marcado OFICIAL saiu do trecho do buscador; abra a URL antes de citar.
- **Números de comunidade** (15 a 40 contatos novos por dia, intervalos): são relatos isolados e se contradizem. Nenhum é limite oficial.
