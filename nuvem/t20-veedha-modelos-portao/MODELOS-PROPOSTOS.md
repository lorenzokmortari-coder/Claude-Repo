# 30 modelos à prova do portão (Veedha, 14/10/2026)

**São propostas:** nenhum modelo vale antes de o Lorenzo aprovar, versão a versão. O texto é sintético e não veio de nenhum cliente real.

**Estilo:**
- abertura "Bom dia {primeiroNome}! Tudo bem?" (pedido de 11/10/2026);
- a ação concreta já vem na mensagem;
- um empurrão para responder no fim;
- sem promessa de retorno, sem travessão e sem emoji.

`{primeiroNome}` é o campo do motor para a primeira palavra do nome do cadastro. Trocar "Bom dia" por "Boa tarde" ou "Boa noite" não muda o veredito.

**Como ler o veredito:**
- **Teste:** como sai quando o rodapé oficial existir; aqui roda com o rodapé de teste da bateria. Texto livre sai no máximo REVISAR (R38).
- **Hoje:** como sai com o config real, em que o rodapé oficial está vazio.
  - Conversa pura sai REVISAR, pela dispensa de 23/09/2026.
  - Com produto ou dinheiro sai BLOQUEADO só pela R08.
  - Por isso **nenhum modelo com produto sai antes do rodapé oficial**.
- **LIVRE:** o modelo entra em `config/modelos.json` como aprovado, numa cópia. O teste confere que a carga aceita o texto e que a instância exata sai LIVRE. Só os de conversa pura podem ser candidatos (C29).

## M01 documento_pendente · Documento pendente no cadastro da XP

```
Bom dia {primeiroNome}! Tudo bem? Passando pra lembrar que falta atualizar um documento do seu cadastro na XP. Quem atualiza e vc mesmo, direto no ambiente da XP. Se travar em alguma parte, me chama.
```
- **Quando usar:** A XP marcou documento pendente no cadastro do cliente.
- **Campos:** `{primeiroNome}` primeiro nome do cadastro
- **O que nunca trocar:** Quem atualiza e o cliente, no ambiente da XP. Nunca pedir que o cliente mande o documento para o assessor.
- **Regra que respeita:** Res. CVM 178, art. 3º, III (informacao sobre o servico do intermediario); LGPD art. 6º, III (minimizacao: o documento nao passa pelo assessor).
- **Veredito:** teste **REVISAR**; hoje **REVISAR**; como modelo aprovado: **LIVRE**.

## M02 endereco_no_cadastro · A XP pediu a atualizacao do endereco

```
Bom dia {primeiroNome}! Tudo bem? A XP pediu a atualizacao do seu cadastro, com o endereco. Quem atualiza e vc mesmo, direto no ambiente da XP. Se travar em alguma parte, me chama.
```
- **Quando usar:** Pedido de atualizacao de endereco no cadastro.
- **Campos:** `{primeiroNome}` primeiro nome do cadastro
- **O que nunca trocar:** O envio do comprovante e direto no ambiente da XP. O assessor nao recebe documento. A palavra "comprovante" tira o modelo da carga como LIVRE (o portao a le como assunto de dinheiro): fica "endereco".
- **Regra que respeita:** Res. CVM 178, art. 3º, III; LGPD art. 6º, III.
- **Veredito:** teste **REVISAR**; hoje **REVISAR**; como modelo aprovado: **LIVRE**.

## M03 perfil_de_investidor · Perfil de investidor (suitability) vencendo ou vencido

```
Bom dia {primeiroNome}! Tudo bem? Passando pra lembrar da atualizacao do seu perfil de investidor no cadastro da XP. Quem responde e vc mesmo, direto no ambiente da XP. Se travar em alguma parte, me chama.
```
- **Quando usar:** O Hub mostra o perfil perto da validade ou vencido. Antes disso, nenhuma recomendacao de produto sai para este cliente.
- **Campos:** `{primeiroNome}` primeiro nome do cadastro
- **O que nunca trocar:** Quem responde o questionario e o cliente, no ambiente da XP. Nao sugerir resposta.
- **Regra que respeita:** Res. CVM 30, art. 6º, III e art. 9º (perfil atualizado antes de recomendar).
- **Veredito:** teste **REVISAR**; hoje **REVISAR**; como modelo aprovado: **LIVRE**.

## M04 termo_de_ciencia · Termo de ciencia (Anexo A) pendente

```
Bom dia {primeiroNome}! Tudo bem? Falta vc dar o ciente no termo da XP que explica como funciona a assessoria. Fica no ambiente da XP e leva poucos minutos. Se tiver qualquer duvida sobre o termo, me chama que a gente conversa.
```
- **Quando usar:** Cliente sem o termo de ciencia da assessoria. Sem ele a XP nao executa ordem direcionada pelo assessor.
- **Campos:** `{primeiroNome}` primeiro nome do cadastro
- **O que nunca trocar:** O cliente da o ciente no ambiente da XP. O assessor nao preenche por ele.
- **Regra que respeita:** Res. CVM 178, art. 37, §2º (termo antes da ordem) e art. 25, II (o assessor nao age pelo cliente).
- **Veredito:** teste **REVISAR**; hoje **REVISAR**.

## M05 boas_vindas · Conta aberta, primeiro contato

```
Bom dia {primeiroNome}! Tudo bem? Feliz de comecar esse trabalho com vc. Queria marcar uma conversa pra entender os seus objetivos. {diaDaSemana} as {hora} funciona? Se nao der, me fala outro horario.
```
- **Quando usar:** Cliente novo com conta aberta na XP pelo escritorio.
- **Campos:** `{primeiroNome}` primeiro nome do cadastro; `{diaDaSemana}` dia proposto; `{hora}` HH:MM
- **O que nunca trocar:** Sem produto e sem numero na primeira mensagem.
- **Regra que respeita:** Res. CVM 178, art. 3º, I e §1º (prospeccao identificando o intermediario: vem no rodape).
- **Veredito:** teste **REVISAR**; hoje **REVISAR**; como modelo aprovado: **LIVRE**.

## M06 reuniao_de_revisao · Reuniao de revisao periodica

```
Bom dia {primeiroNome}! Tudo bem? Queria marcar a nossa conversa de revisao. {diaDaSemana} as {hora} funciona pra vc? Se nao der, me fala outro horario.
```
- **Quando usar:** Revisao do semestre ou do ano, sem pauta de produto definida.
- **Campos:** `{primeiroNome}` primeiro nome do cadastro; `{diaDaSemana}` dia proposto; `{hora}` HH:MM
- **O que nunca trocar:** Nao antecipar recomendacao na mensagem de convite.
- **Regra que respeita:** Res. CVM 178, art. 3º, III.
- **Veredito:** teste **REVISAR**; hoje **REVISAR**; como modelo aprovado: **LIVRE**.

## M07 confirmar_reuniao · Lembrete no dia da reuniao

```
Bom dia {primeiroNome}! Tudo bem? Passando pra confirmar a nossa conversa de hoje as {hora}. Se nao der, me fala outro horario.
```
- **Quando usar:** Manha do dia de uma conversa marcada.
- **Campos:** `{primeiroNome}` primeiro nome do cadastro; `{hora}` HH:MM
- **O que nunca trocar:** So a hora muda.
- **Regra que respeita:** Res. CVM 178, art. 3º, III.
- **Veredito:** teste **REVISAR**; hoje **REVISAR**; como modelo aprovado: **LIVRE**.

## M08 remarcar_reuniao · Remarcar conversa

```
Bom dia {primeiroNome}! Tudo bem? Queria passar a nossa conversa pra {diaDaSemana} as {hora}. Se nao der, me fala outro horario.
```
- **Quando usar:** O assessor precisou mudar o horario combinado.
- **Campos:** `{primeiroNome}` primeiro nome do cadastro; `{diaDaSemana}` novo dia; `{hora}` HH:MM
- **O que nunca trocar:** Sem justificativa que cite mercado ou produto.
- **Regra que respeita:** Res. CVM 178, art. 3º, III.
- **Veredito:** teste **REVISAR**; hoje **REVISAR**; como modelo aprovado: **LIVRE**.

## M09 depois_da_reuniao · Agradecimento depois da conversa

```
Bom dia {primeiroNome}! Tudo bem? Obrigado pela conversa. Se ficou alguma duvida, me responde aqui que a gente conversa.
```
- **Quando usar:** Mesmo dia ou dia seguinte a uma reuniao.
- **Campos:** `{primeiroNome}` primeiro nome do cadastro
- **O que nunca trocar:** Nao resumir por escrito a carteira nem o que foi recomendado: resumo da carteira e extrato (art. 25, VII).
- **Regra que respeita:** Res. CVM 178, art. 25, VII.
- **Veredito:** teste **REVISAR**; hoje **REVISAR**; como modelo aprovado: **LIVRE**.

## M10 cliente_sumido · Cliente sem contato ha meses

```
Bom dia {primeiroNome}! Tudo bem? Faz um tempo que a gente nao conversa. Queria saber se mudou alguma coisa nos seus planos. Me fala um horario bom pra gente conversar?
```
- **Quando usar:** Regua de relacionamento: sem conversa ha mais de um trimestre.
- **Campos:** `{primeiroNome}` primeiro nome do cadastro
- **O que nunca trocar:** Pergunta sobre planos, nunca sobre a carteira.
- **Regra que respeita:** Res. CVM 178, art. 3º, I e III.
- **Veredito:** teste **REVISAR**; hoje **REVISAR**; como modelo aprovado: **LIVRE**.

## M11 retorno_de_ligacao · Ligacao perdida do cliente

```
Bom dia {primeiroNome}! Tudo bem? Vi a sua ligacao e nao consegui atender. Me fala um horario bom que eu te ligo.
```
- **Quando usar:** O cliente ligou e o assessor nao atendeu.
- **Campos:** `{primeiroNome}` primeiro nome do cadastro
- **O que nunca trocar:** Ordem por ligacao so no canal gravado da XP. Fica fora da carga LIVRE: a lista fechada de pedidos le "vi a sua ligacao" como pedido (testadas 5 redacoes).
- **Regra que respeita:** Res. CVM 35, art. 14 (dialogo em sistema de gravacao).
- **Veredito:** teste **REVISAR**; hoje **REVISAR**.

## M12 informe_de_rendimentos · Informe para o imposto de renda disponivel

```
Bom dia {primeiroNome}! Tudo bem? O seu relatorio para o imposto de renda ja esta disponivel na plataforma da XP. Se travar em alguma parte, me chama.
```
- **Quando usar:** Fevereiro e marco, quando a XP libera o informe.
- **Campos:** `{primeiroNome}` primeiro nome do cadastro
- **O que nunca trocar:** Nao mandar o informe nem os valores: o informe e da XP.
- **Regra que respeita:** Res. CVM 178, art. 25, VII (o assessor nao envia extrato; aponta o canal da XP).
- **Veredito:** teste **REVISAR**; hoje **REVISAR**; como modelo aprovado: **LIVRE**.

## M13 ausencia_do_assessor · Assessor fora (ferias, viagem)

```
Bom dia {primeiroNome}! Tudo bem? Vou ficar fora ate {data}. Nesse periodo, qualquer coisa urgente da sua conta e direto com a central da XP. Na volta te procuro.
```
- **Quando usar:** Antes de um periodo fora.
- **Campos:** `{primeiroNome}` primeiro nome do cadastro; `{data}` DD/MM da volta
- **O que nunca trocar:** O canal no periodo e a central da XP, nunca outra pessoa sem credenciamento.
- **Regra que respeita:** Res. CVM 178, art. 25, IV e V (nao delegar a quem nao e assessor contratado).
- **Veredito:** teste **REVISAR**; hoje **REVISAR**.

## M14 vencimento_reaplicar · Vencimento de titulo, com recomendacao de onde aplicar

```
Bom dia {primeiroNome}! Tudo bem? O seu {produto_vencendo} vence dia {data}. Minha recomendacao e aplicar esse valor em {produto_destino}, que esta na prateleira da XP. Me responde aqui se faz sentido pra vc que eu te ligo e explico os detalhes.
```
- **Quando usar:** Titulo do cliente vence nos proximos dias e o perfil esta valido.
- **Campos:** `{primeiroNome}` primeiro nome do cadastro; `{produto_vencendo}` nome do produto que vence (sem valor); `{data}` DD/MM do vencimento; `{produto_destino}` produto da prateleira da XP adequado ao perfil
- **O que nunca trocar:** Sem valor, sem taxa, sem rentabilidade passada e sem adjetivo sobre o produto destino. O produto destino tem de ser da classe permitida para o perfil.
- **Regra que respeita:** Res. CVM 30, art. 6º (perfil valido); Res. CVM 178, art. 25, III (recomendar sim, analisar nao) e VII (sem valor da posicao).
- **Veredito:** teste **REVISAR**; hoje **BLOQUEADO** (R08).

## M15 vencimento_usar_ou_aplicar · Vencimento, cliente pode precisar do dinheiro

```
Bom dia {primeiroNome}! Tudo bem? O seu {produto_vencendo} vence dia {data}. Se vc for usar esse dinheiro, nao precisa fazer nada: o valor fica na sua conta da XP. Se nao for usar, minha recomendacao e aplicar em {produto_destino}. Me responde aqui qual dos dois.
```
- **Quando usar:** Titulo vence e nao se sabe se o cliente vai usar o dinheiro.
- **Campos:** `{primeiroNome}` primeiro nome do cadastro; `{produto_vencendo}` produto que vence; `{data}` DD/MM; `{produto_destino}` produto da prateleira da XP adequado ao perfil
- **O que nunca trocar:** As duas opcoes ficam lado a lado; nenhuma pressao.
- **Regra que respeita:** Res. CVM 30, art. 6º; Res. CVM 178, art. 25, VII.
- **Veredito:** teste **REVISAR**; hoje **BLOQUEADO** (R08).

## M16 troca_com_custo · Vender X e aplicar em Y (troca)

```
Bom dia {primeiroNome}! Tudo bem? Minha recomendacao e vender {produto_origem} e aplicar em {produto_destino}. Custo total da troca, ja com IR, corretagem e taxa de saida: {custo_total}. Me responde aqui se quer seguir que eu te ligo pra explicar.
```
- **Quando usar:** Recomendacao de troca de produto, com o custo total ja levantado na simulacao da XP.
- **Campos:** `{primeiroNome}` primeiro nome do cadastro; `{produto_origem}` o que vender; `{produto_destino}` onde aplicar; `{custo_total}` custo total da troca, da simulacao da XP (vai em fonteDeNumeros)
- **O que nunca trocar:** A frase do custo total, com IR, corretagem e taxa de saida, e obrigatoria e o numero tem de sair da simulacao da XP (fonte declarada). Sem ela a troca barra (R20).
- **Regra que respeita:** Res. CVM 30, art. 3º, §5º (custo total da troca); Res. CVM 35, art. 26-D, I (conflito da remuneracao).
- **Veredito:** teste **REVISAR**; hoje **BLOQUEADO** (R08).
- **Contexto que o motor precisa declarar:** `{"temCustoTotal": true, "fonteDeNumeros": "Simulacao da XP: custo total da troca R$ 87,40"}`

## M17 fim_de_carencia_manter · Fim de carencia, recomendacao de manter

```
Bom dia {primeiroNome}! Tudo bem? A carencia do seu {produto} termina dia {data}. A partir dai o resgate fica livre. Minha recomendacao e manter onde esta. Se vc estiver pensando em resgatar, me responde aqui antes que a gente conversa.
```
- **Quando usar:** Carencia do produto termina e a recomendacao e nao mexer.
- **Campos:** `{primeiroNome}` primeiro nome do cadastro; `{produto}` produto com carencia; `{data}` DD/MM
- **O que nunca trocar:** Nao justificar com rentabilidade nem comparar com outro produto.
- **Regra que respeita:** Res. CVM 30, art. 6º; Res. CVM 178, art. 25, III.
- **Veredito:** teste **REVISAR**; hoje **BLOQUEADO** (R08).

## M18 fim_de_carencia_trocar · Fim de carencia, recomendacao de resgatar e aplicar em outro

```
Bom dia {primeiroNome}! Tudo bem? A carencia da {produto} termina dia {data}. Minha recomendacao e resgatar e aplicar em {produto_destino}. Custo total da troca, ja com IR e taxas: {custo_total}. Me responde aqui se quer seguir que eu te ligo pra explicar.
```
- **Quando usar:** Carencia termina e a recomendacao e trocar, com custo levantado.
- **Campos:** `{primeiroNome}` primeiro nome do cadastro; `{produto}` produto com carencia; `{data}` DD/MM; `{produto_destino}` produto da prateleira; `{custo_total}` custo total da simulacao da XP
- **O que nunca trocar:** Custo total obrigatorio, da simulacao da XP. Sem "seu"/"sua" na mensagem: posse junto de qualquer valor barra como extrato (R14), e o custo total e um valor.
- **Regra que respeita:** Res. CVM 30, art. 3º, §5º e art. 6º.
- **Veredito:** teste **REVISAR**; hoje **BLOQUEADO** (R08).
- **Contexto que o motor precisa declarar:** `{"temCustoTotal": true, "fonteDeNumeros": "Simulacao da XP: custo total da troca R$ 41,10"}`

## M19 aporte_recebido · Aporte caiu na conta da XP

```
Bom dia {primeiroNome}! Tudo bem? O seu aporte ja aparece na sua conta da XP. Minha recomendacao e aplicar em {produto_destino}. Me responde aqui se faz sentido que eu te explico como fazer pelo ambiente da XP.
```
- **Quando usar:** O dinheiro novo do cliente aparece na conta da XP.
- **Campos:** `{primeiroNome}` primeiro nome do cadastro; `{produto_destino}` produto da prateleira adequado ao perfil
- **O que nunca trocar:** Nunca dizer que o assessor recebeu o dinheiro: ele esta na conta do cliente na XP. Sem o valor.
- **Regra que respeita:** Res. CVM 178, art. 25, I (o assessor nao recebe recurso) e VII (sem valor); Res. CVM 30, art. 6º.
- **Veredito:** teste **REVISAR**; hoje **BLOQUEADO** (R08).

## M20 saldo_parado · Saldo em conta sem aplicacao

```
Bom dia {primeiroNome}! Tudo bem? Tem um saldo sem aplicacao na sua conta da XP. Minha recomendacao e aplicar em {produto_destino}. Me responde aqui se faz sentido que eu te ligo e explico os detalhes.
```
- **Quando usar:** Ha saldo livre na conta da XP ha alguns dias.
- **Campos:** `{primeiroNome}` primeiro nome do cadastro; `{produto_destino}` produto da prateleira adequado ao perfil
- **O que nunca trocar:** Nunca escrever o valor do saldo (art. 25, VII). Sem pressa nem 'esta perdendo dinheiro'.
- **Regra que respeita:** Res. CVM 178, art. 25, VII; Res. CVM 30, art. 6º; ANBIMA art. 64, IV.
- **Veredito:** teste **REVISAR**; hoje **BLOQUEADO** (R08).

## M21 resgate_pedido · Cliente pediu resgate

```
Bom dia {primeiroNome}! Tudo bem? Vi que vc pediu o resgate do {produto}. O valor cai na sua conta da XP no prazo do produto. Se a ideia for usar o dinheiro em outro investimento, me responde aqui antes que a gente conversa.
```
- **Quando usar:** O resgate aparece no Hub.
- **Campos:** `{primeiroNome}` primeiro nome do cadastro; `{produto}` produto resgatado
- **O que nunca trocar:** O dinheiro fica na conta do cliente na XP. Sem valor e sem prazo inventado.
- **Regra que respeita:** Res. CVM 178, art. 25, I e VII.
- **Veredito:** teste **REVISAR**; hoje **BLOQUEADO** (R08).

## M22 cupom_pago · Cupom ou juros pagos

```
Bom dia {primeiroNome}! Tudo bem? Os juros do seu {produto} foram pagos hoje na sua conta da XP. Minha recomendacao e aplicar esse valor em {produto_destino}. Me responde aqui se quer seguir que eu te ligo.
```
- **Quando usar:** Pagamento de cupom de titulo ou juros na conta.
- **Campos:** `{primeiroNome}` primeiro nome do cadastro; `{produto}` titulo que pagou; `{produto_destino}` produto da prateleira adequado ao perfil
- **O que nunca trocar:** Sem o valor do cupom. Nao usar 'reinvestir': o portao le como troca e exige custo total.
- **Regra que respeita:** Res. CVM 178, art. 25, VII; Res. CVM 30, art. 6º.
- **Veredito:** teste **REVISAR**; hoje **BLOQUEADO** (R08).

## M23 dividendos · Dividendos ou rendimentos de FII pagos

```
Bom dia {primeiroNome}! Tudo bem? Caiu hoje um pagamento de dividendos na sua conta da XP. Minha recomendacao e aplicar esse valor em {produto_destino}. Me responde aqui se faz sentido que eu te ligo.
```
- **Quando usar:** Pagamento de proventos na conta.
- **Campos:** `{primeiroNome}` primeiro nome do cadastro; `{produto_destino}` produto da prateleira adequado ao perfil
- **O que nunca trocar:** Sem valor, sem nome de acao e sem comentario sobre a empresa.
- **Regra que respeita:** Res. CVM 178, art. 25, III e VII; Res. CVM 20, art. 2º.
- **Veredito:** teste **REVISAR**; hoje **BLOQUEADO** (R08).

## M24 aniversario_de_aplicacao · Aniversario de aplicacao

```
Bom dia {primeiroNome}! Tudo bem? O seu {produto} faz aniversario de aplicacao dia {data}. Minha recomendacao e nao resgatar antes dessa data. Se vc estiver precisando do dinheiro, me responde aqui que a gente conversa.
```
- **Quando usar:** Produto com data de aniversario que muda liquidez ou rendimento (previdencia, poupanca, LCI com carencia).
- **Campos:** `{primeiroNome}` primeiro nome do cadastro; `{produto}` produto; `{data}` DD/MM
- **O que nunca trocar:** Sem dizer quanto rendeu nem quanto 'perde' resgatando antes.
- **Regra que respeita:** Res. CVM 178, art. 25, III e VII.
- **Veredito:** teste **REVISAR**; hoje **BLOQUEADO** (R08).

## M25 copom · Mudanca na Selic

```
Bom dia {primeiroNome}! Tudo bem? O Copom divulgou ontem a decisao sobre a Selic. A XP publicou a leitura dela neste link: {link_xp}. Queria marcar uma conversa rapida pra ver se muda alguma coisa nos seus planos. {diaDaSemana} as {hora} funciona?
```
- **Quando usar:** Dia seguinte a uma decisao do Copom.
- **Campos:** `{primeiroNome}` primeiro nome do cadastro; `{link_xp}` link da analise publicada pela XP; `{diaDaSemana}` dia; `{hora}` HH:MM
- **O que nunca trocar:** Nada de previsao nem leitura propria do efeito na carteira (analise, art. 25, III). So o link da XP e o convite.
- **Regra que respeita:** Res. CVM 178, art. 25, III; Res. CVM 20, arts. 1º e 2º.
- **Veredito:** teste **REVISAR**; hoje **BLOQUEADO** (R08).

## M26 come_cotas · Come-cotas de maio e novembro

```
Bom dia {primeiroNome}! Tudo bem? No fim do mes tem o come-cotas dos fundos. E automatico e vc nao precisa fazer nada. Se quiser entender como funciona nos seus fundos, me responde aqui que a gente marca uma conversa.
```
- **Quando usar:** Ultima semana de maio e de novembro, para quem tem fundo.
- **Campos:** `{primeiroNome}` primeiro nome do cadastro
- **O que nunca trocar:** Sem valor do imposto e sem dizer quanto o cliente vai pagar.
- **Regra que respeita:** Res. CVM 178, art. 25, VII; Res. CVM 30, art. 6º.
- **Veredito:** teste **REVISAR**; hoje **BLOQUEADO** (R08).

## M27 objetivo_com_data · Cliente vai precisar do dinheiro numa data

```
Bom dia {primeiroNome}! Tudo bem? Vc comentou que vai precisar de parte do dinheiro em {data}. Minha recomendacao e deixar essa parte em {produto_liquidez}, que tem resgate diario. Me responde aqui se faz sentido que eu te ligo e explico.
```
- **Quando usar:** O cliente avisou que vai usar parte do dinheiro (viagem, imovel).
- **Campos:** `{primeiroNome}` primeiro nome do cadastro; `{data}` DD/MM; `{produto_liquidez}` produto de liquidez diaria da prateleira
- **O que nunca trocar:** Sem valor e sem prometer que o dinheiro estara disponivel: falar do resgate, nao do resultado.
- **Regra que respeita:** Res. CVM 30, art. 6º; ANBIMA art. 64, IV.
- **Veredito:** teste **REVISAR**; hoje **BLOQUEADO** (R08).

## M28 produto_novo_na_xp · Produto novo na prateleira da XP

```
Bom dia {primeiroNome}! Tudo bem? A XP abriu {produto}. O material completo da XP esta aqui: {link_material}. Minha recomendacao e olhar com calma e, se fizer sentido, a gente conversa. Me responde aqui que eu te ligo.
```
- **Quando usar:** Campanha de produto, so para clientes com perfil compativel e valido.
- **Campos:** `{primeiroNome}` primeiro nome do cadastro; `{produto}` produto novo; `{link_material}` link do material tecnico da XP
- **O que nunca trocar:** Sem taxa no texto (taxa exige os avisos do art. 78 e o link) e sem adjetivo. O link do material da XP fica.
- **Regra que respeita:** Res. CVM 30, art. 6º; ANBIMA arts. 64, IV e 67.
- **Veredito:** teste **REVISAR**; hoje **BLOQUEADO** (R08).
- **Contexto que o motor precisa declarar:** `{"urlMaterialTecnico": "https://conteudo.xpi.com.br/exemplo-material"}`

## M29 como_transferir · Cliente pergunta como mandar dinheiro para a XP

```
Bom dia {primeiroNome}! Tudo bem? Os dados pra depositar na sua conta da XP ficam no ambiente da XP, no seu nome. O deposito sai do seu banco direto pra la. Se travar em alguma parte, me chama.
```
- **Quando usar:** Resposta a pergunta do cliente sobre deposito.
- **Campos:** `{primeiroNome}` primeiro nome do cadastro
- **O que nunca trocar:** O dinheiro vai do banco do cliente para a conta dele na XP, no nome dele. Nunca conta ou chave do assessor, do escritorio ou de terceiro. "Pra colocar dinheiro na XP ... para a conta" foi lido como troca (R20): nao usar. No config de hoje saia REVISAR sem rodape: a dispensa de conversa pura nao conhecia deposito, pix, TED, transferencia nem boleto (patch 01).
- **Regra que respeita:** Res. CVM 178, art. 25, I.
- **Veredito:** teste **REVISAR**; hoje **BLOQUEADO** (R08) (no portão de hoje, sem o patch 01: REVISAR ).

## M30 relatorio_da_xp · Relatorio de research da XP sobre tema da carteira

```
Bom dia {primeiroNome}! Tudo bem? A XP publicou um relatorio novo sobre renda fixa, segue o link: {link_relatorio}. Depois de ler, se quiser, me responde aqui que a gente conversa.
```
- **Quando usar:** A XP publicou um relatorio que interessa ao cliente. Repasse integro, so o link.
- **Campos:** `{primeiroNome}` primeiro nome do cadastro; `{link_relatorio}` link do relatorio da XP
- **O que nunca trocar:** So o link, sem resumir nem comentar o relatorio (resumo com juizo e analise propria, art. 25, III; ANBIMA art. 71, II). No config de hoje sai REVISAR sem rodape por um furo da dispensa de conversa pura ("renda fixa" nao esta na lista dela): patch 01.
- **Regra que respeita:** Res. CVM 20, arts. 2º e 20; ANBIMA art. 71, II.
- **Veredito:** teste **REVISAR**; hoje **BLOQUEADO** (R08) (no portão de hoje, sem o patch 01: REVISAR ).
