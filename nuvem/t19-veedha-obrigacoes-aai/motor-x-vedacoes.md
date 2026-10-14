# O que o motor da Veedha faz (ou poderia fazer) que bate numa vedação (14/10/2026)

**Fonte:** o LEIA-ME e a nota "O que o robô nunca pode fazer" do pacote "Veedha · portão". Os módulos de fila, coleta, carteira e ponte estão **fora do pacote**: o que digo sobre eles vem da descrição, não do código.

**Isto não é parecer jurídico.** Cada ponto separa a norma (com artigo e fonte) da interpretação.

**Gravidade:** é a mesma régua das tarefas da nuvem, aplicada ao que pode chegar a cliente ou regulador.

| # | Gravidade | Confiança | O que o motor faz | Norma que pode bater | Já coberto? |
|---|---|---|---|---|---|
| V01 | ALTO | alta | Não guarda log do que sai (5 anos) | Res. CVM 35 (guarda de 5 anos, fonte secundária); Res. CVM 178, arts. 29, §1º e 41 (segundo a nota do vault) | Não: lacuna L02 já conhecida |
| V02 | ALTO | média | Lê posição de cliente (MAPA, carteira) e pode gerar anexo, planilha ou PDF que o portão não lê | Res. CVM 178, art. 25, VII (extrato de posição) | Em parte: o portão só vê texto (L13) |
| V03 | MÉDIO | média | Conversa com cliente por WhatsApp pessoal, fora de sistema de gravação do intermediário; a ponte guarda as conversas localmente | Res. CVM 35, art. 14 (catálogo do motor); LGPD, arts. 7º, 15, 16 e 46 | Aviso R05 (decisão D02) e R07 (lista branca); retenção e base da ponte não documentadas |
| V04 | MÉDIO | baixa | Dado de cliente pode ir ao provedor do modelo de IA no `redigir` | LGPD, arts. 33 (transferência internacional) e 39 (operador); contrato com a XP (não lido) | Em parte: o contexto do portão só leva flags, datas e primeiro nome; o prompt do `redigir` não foi visto |
| V05 | MÉDIO | baixa | O coletor lê a tela do Hub da XP com a sessão do assessor | Política da XP para o Hub (não lida); LGPD, art. 46 | Fica de fora: guarda só perfil e validade em `veedha-dados`, fora do OneDrive |
| V06 | MÉDIO | média | Disparo em massa (régua, aniversário, relatório disponível) | Res. CVM 20, art. 1º (relatório de análise); Res. CVM 30, art. 6º (perfil de cada um); política da XP sobre massa (não lida) | Sim para os 5 modelos sem produto; produto em massa só sai REVISAR, com o perfil de cada destinatário (R15, R16); falta a tabela de classes por perfil (L10) |
| V07 | MÉDIO | alta | O rodapé oficial do art. 24 não existe; conversa pura sai sem rodapé por decisão do Lorenzo (23/09) | Res. CVM 178, art. 24 | R08 barra conteúdo financeiro; a leitura de que conversa não é "material" é do Lorenzo (registrada) |
| V08 | BAIXO | alta | Aviso de vencimento sem valor sai como REVISAR | Res. CVM 178, art. 25, VII | É calibragem (D03), a confirmar com o compliance da XP |
| V09 | BAIXO | média | Não confere a data do PEC nem o status do credenciamento | Regulamento do PEC (ANCORD, 5 anos); Lei 6.385, art. 16 | Não; é fácil de pôr no motor (aviso de prazo) |

---

## V01 · Sem log de 5 anos (ALTO, confiança alta)

**Norma:**
- Res. CVM 35 exige guardar documentos e informações por, no mínimo, 5 anos. A fonte é secundária: o texto oficial estava bloqueado.
- A nota do vault cita a Res. CVM 178, arts. 29, §1º e 41, e a Res. CVM 30, art. 14 (perfil no momento da recomendação).

**O que o motor faz:** o portão é função pura. Nada registra o que saiu, para quem, com que perfil e com que aprovação. É a lacuna L02 da própria nota, e dela dependem a L03 (perfil no instante do envio) e a L14 (registro LGPD por envio).

**Por que é ALTO:**
- Numa fiscalização da XP ou da CVM, o escritório não prova o que mandou nem que o perfil estava válido.
- É regra violada sem ninguém ver.

**Interpretação (como cumprir):** um arquivo só de acréscimo (append-only), uma linha por envio, com:
- data e hora;
- canal;
- destinatário (id interno, nunca o telefone);
- hash do texto;
- veredito do portão e regras;
- quem aprovou;
- perfil e validade usados.

Retenção de 5 anos, fora do OneDrive, exportável para a XP.

**O motor confere sozinho:** sim. É código: a fila grava a linha antes de liberar o envio.

---

## V02 · Posição pode sair por anexo (ALTO, confiança média)

**Norma (catálogo do motor):** Res. CVM 178, art. 25, VII, que veda "confeccionar e enviar para os clientes extratos contendo informações sobre as operações realizadas ou posições em aberto".

**O que o motor faz:**
- `carteira.js` e `lib/mapa.js` leem posições (planilha MAPA) para montar a agenda: vencimentos, caixa e outros.
- O portão barra posição **no texto** (R14), a qualquer distância.
- O portão só recebe texto (L13). Uma planilha, um PDF ou uma imagem com posição anexada pela fila ou pelo e-mail passariam sem leitura.

**Cenário:** um robô de agenda anexa a planilha de vencimentos do cliente ("segue a lista do que vence em novembro"). O texto passa como REVISAR, e o anexo é um extrato de posição.

**Interpretação:** proibir anexo gerado pelo motor. Só link para a plataforma da XP, como o modelo `relatorio_disponivel_v1` já faz.

**O motor confere sozinho:** sim. A fila recusa qualquer item com anexo que não seja material da XP com id aprovado.

**Não confirmado:** não vi a fila nem o e-mail. Se nenhum deles aceitar anexo hoje, isto vira só trava preventiva.

---

## V03 · Conversa fora de sistema de gravação (MÉDIO, confiança média)

**Norma:**
- Catálogo do motor: Res. CVM 35, art. 14, que veda "manter diálogo com cliente, inclusive por preposto, fora de sistema de gravação". O dever de gravar é do intermediário.
- A nota do vault registra a lacuna `b3-bsm-gravacao`: não se sabe se WhatsApp é canal aceito por regulamento ou só pela política da XP.

**O que o motor faz:**
- Fala por `whatsapp_pessoal` e `whatsapp_business`.
- A ponte de leitura (Baileys 6.7.24) guarda as conversas num SQLite local.
- O portão avisa (R05) e não bloqueia: é a decisão D02 do Lorenzo ("bloquear hoje pararia a operação inteira").

**Interpretação:**
- A decisão D02 é dele e está registrada; não proponho mudar.
- O que falta é documentar a ponte, que guarda conversa de cliente: base legal (provável: execução de contrato e, para o que é registro regulatório, obrigação regulatória), retenção (5 anos para o que é registro; descarte do resto) e quem acessa.

**Nota técnica:** a ponte usa cliente não oficial do WhatsApp. Os Termos do WhatsApp Business App, em vigor desde 23/09/2026 segundo o trecho do buscador, proíbem acesso automatizado (ver a pesquisa da tarefa 18; nenhum dado da Ozav foi usado aqui).

**O motor confere sozinho:** parcialmente. A lista branca (R07) já impede gravar conversa fora do universo Veedha. A retenção pode virar uma rotina de descarte.

---

## V04 · Dado de cliente no modelo de IA (MÉDIO, confiança baixa)

**Norma:** LGPD, art. 39 (o operador segue as instruções do controlador) e art. 33 (transferência internacional), em paráfrase; o Planalto estava bloqueado. O contrato da XP pode proibir mandar dado de cliente a ferramenta de terceiro (não lido).

**O que o motor faz:**
- O contexto do portão leva só flags, datas e primeiro nome. O vault diz: "telefone e valores nunca entram no contexto".
- O `redigir.js` (fora do pacote) escreve rascunho com IA. Não vi o que vai no prompt.

**Interpretação:**
- Mandar ao modelo só o mínimo: primeiro nome, flags e o que o rascunho precisa. Nunca CPF, conta, posição ou telefone.
- Ter contrato ou termos do provedor que cubram o tratamento como operador.
- **A escolha do modelo está congelada desde 08/10/2026; isto não é proposta de troca.**

**O motor confere sozinho:** sim. Pode ter uma trava antes da chamada ao modelo que recusa prompt com CPF, número de conta ou valor junto de palavra de posição. É a mesma lógica do R14, aplicada ao prompt.

---

## V05 · Coletor lendo a tela do Hub (MÉDIO, confiança baixa)

**O que o motor faz:** `coletor/coletar.js` e `ler-tela.js` leem o perfil de suitability no Hub da XP, com a sessão do próprio assessor, e guardam perfil e validade em `veedha-dados/hub/indice.json`, fora do OneDrive.

**Norma:** não há vedação da CVM a que o assessor consulte o Hub. O risco está em dois lugares:
- na política da XP sobre automação no Hub (não lida: lacuna `xp-manuais`);
- na segurança do arquivo (LGPD, art. 46, em paráfrase).

**Interpretação:** perguntar ao compliance da XP se a leitura automatizada da tela é permitida. Guardar só perfil e validade, como já se faz, com permissão de arquivo restrita.

**O motor confere sozinho:** não. É pergunta para a XP.

---

## V06 · Disparo em massa (MÉDIO, confiança média)

**Norma:**
- Nenhuma norma específica da CVM, da ANCORD ou da ANBIMA sobre envio em massa foi encontrada.
- A Res. CVM 20, art. 1º, §1º (trecho do buscador) chama de relatório de análise "quaisquer textos [...] sobre valores mobiliários específicos [...] que possam auxiliar ou influenciar investidores", "ainda que restrita a clientes".
- A Res. CVM 30, art. 6º, pede a adequação ao perfil de cada um.

**O que o motor faz:**
- Os 5 modelos aprovados não falam de produto. Massa com eles não bate na Res. 20 nem na Res. 30.
- Texto livre com produto sai no máximo REVISAR e é conferido por destinatário (R15, R16).
- Falta a tabela de classes permitidas por perfil (L10): sem ela, produto fora do perfil vira só aviso (R17).

**Interpretação:**
- Produto em massa só com material da XP íntegro (R28 a R30) e segmentado por perfil.
- A política da XP sobre massa é a lacuna que decide (`xp-manuais`).

**O motor confere sozinho:** sim, se a tabela de classes por perfil existir (L10).

---

## V07 · Rodapé do art. 24 (MÉDIO, confiança alta)

**Norma (catálogo do motor):** Res. CVM 178, art. 24, que veda usar material que não faça "referência expressa ao intermediário contratante, que não identifique o assessor como contratado e que não apresente os dados de contato da ouvidoria".

**O que o motor faz:**
- `config/rodape.json` está vazio e com `aprovado: false` (L26).
- Conteúdo financeiro barra pela R08.
- A conversa pura dispensa o rodapé por decisão do Lorenzo, de 23/09/2026. A leitura dele é que mensagem de conversa não é "material" (art. 24, §2º, que fala de apostila, curso, palestra e página na internet).

**Interpretação:** a decisão está registrada e é dele. O que eu apontaria é prático: **sem o texto oficial do rodapé, nenhuma mensagem com produto sai do motor**, e isso inclui os modelos da tarefa 20. Conseguir o texto com a XP destrava mais coisa do que qualquer outra lacuna.

---

## V08 · Agenda de vencimento (BAIXO, confiança alta)

É a calibragem D03 da nota: aviso de vencimento sem valor sai como REVISAR. A nota já diz que é "a fronteira mais fina do portão" e que falta confirmar com o compliance da XP. Não há nada novo a acrescentar, só a pergunta pendente.

---

## V09 · PEC e credenciamento (BAIXO, confiança média)

**Norma:**
- Regulamento do PEC da ANCORD (trecho do buscador): renovação "5 (cinco) anos após o credenciamento ou após a sua última renovação".
- Lei 6.385, art. 16: só atua quem tem registro.

**O motor confere sozinho:** sim, e é barato. Guardar a data do último credenciamento ou da última renovação e avisar 12, 6 e 3 meses antes.

---

## O que não deu para verificar

- **Nenhum texto oficial abriu nesta rede.** Ficaram bloqueados CVM, Planalto, ANBIMA, ANCORD, XP e BSM. O texto da Res. 178 nesta entrega vem de duas fontes:
  - do catálogo do próprio motor (levantamento de 10/09/2026);
  - de trechos do buscador.
- **O art. 25 completo** (incisos IV e V) e o prazo de comunicação cadastral não foram vistos.
- **O código da fila, do coletor, da carteira, da ponte e do redigir** não está no pacote: os pontos V02 a V06 vêm da descrição.
- **Os manuais da XP** (compliance do assessor, materiais publicitários, canais) não foram lidos. São a lacuna que mais muda as respostas.
