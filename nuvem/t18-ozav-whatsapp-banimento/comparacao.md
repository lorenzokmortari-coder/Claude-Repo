# O que o nosso código já faz × o que derruba número (14/10/2026)

Esta tabela cruza os gatilhos citados em 2025–2026 (`pesquisa.md`) com as regras do pacote "Ozav · envio" (R1–R60 do LEIA-ME).

**Como ler:**
- **Natureza** é a da fonte: OFICIAL, IMPRENSA ou COMUNIDADE. Toda fonte OFICIAL veio só do trecho do buscador, porque as páginas do WhatsApp não abriram nesta rede.
- **Veredito:**
  - **ok:** o código cobre;
  - **falta:** não há regra;
  - **folgado:** a regra existe, mas deixa passar mais do que os relatos sugerem;
  - **apertado:** a regra segura mais do que o risco pede.

| Gatilho citado | Natureza | O que o código faz hoje | Veredito |
|---|---|---|---|
| Iniciar conversa com quem nunca falou com o número (o padrão mais repetido nos relatos de restrição) | OFICIAL (spam, envio em massa) + COMUNIDADE (15 a 40 contatos novos por dia → restrição de 24 h) | Interação nova: no máximo 2 por 24 h, 180 min entre elas, só depois de `novas_desde`, disjuntor de 48 h (R38–R39); `podeTocarNova` exige número quieto (R45) | **ok.** Fica muito abaixo dos relatos. O teto de 2 é decisão do dono (02/10). |
| Criar grupo e adicionar gente | OFICIAL (conta restrita não cria grupo nem adiciona) + COMUNIDADE | `criar_grupo`, `adicionar_time`, `convidar` e `remover_participante` contam como interação nova; o "oi" de grupo novo só sai em dia útil, das 8h às 20h | **ok.** O "oi" em feriado foi achado A08 da tarefa 12. |
| Mesma mensagem para muitos | OFICIAL (envio em massa) + COMUNIDADE (respostas idênticas a ~100 pessoas → restrição) | Interação nova com o mesmo começo em outra conversa: segura 24 h (R39). Follow-up: não começa com as 3 mesmas palavras de outro toque do dia (R26) nem repete o começo na conversa em 7 dias (R21) | **ok.** O texto vem de quem escreve, conta a conta. |
| Intervalo fixo ou curto entre mensagens | COMUNIDADE (7 s fixos → ban; 20 a 120 s não bastaram em vários relatos) | 2 a 4 min sorteados pela chave da última mensagem, entre robôs, e que sobrevivem a reinício; resposta só 75 s depois de qualquer mensagem (R40) | **ok.** Os relatos dizem que intervalo sozinho não salva; o que pesa é o contato novo. |
| Volume por dia | COMUNIDADE (números contraditórios: 50 a 110 por dia em número novo → restrição) | Follow-up: 25 por hora e 120 em 24 h. Resposta: 20 por hora e 80 em 24 h. Teto do disparo: 60 follow-ups por dia (R40, R47) | **folgado no papel.** O teto que vale na prática é o de 60/dia do disparo. O de 120 do governador nunca é testado pelos robôs de lista. |
| Mensagens sem resposta | IMPRENSA (teste de teto mensal, 17/10/2025, número não divulgado) + COMUNIDADE (taxa de resposta baixa) | Nada mede | **falta.** Patch 02: mede e, se o dono quiser, segura. |
| Sinal do WhatsApp (limite, ban, restrição) | OFICIAL (restrição) + COMUNIDADE (463 "reach-out timelock") | O disjuntor arma com rate-overlimit, forbidden, 401/403, logged out, spam, blocked e banned (R42) | **falta** o 463 e os textos de restrição. Patch 01. |
| Número ou aparelho novo sem aquecimento | COMUNIDADE (restrição logo nas 3 primeiras mensagens de um número novo; aquecimento de 7 a 30 dias) | Aquecimento de 5 dias depois de todo pareamento; no dia 0, nenhuma interação nova (R41) | **ok** para reparear o mesmo número. **Folgado** para um número NOVO; ver o plano B. |
| Robô 24 h sem pausa | COMUNIDADE | Follow-up só em dia útil, das 8h às 20h (R47); nos feriados, a régua e o hunting param (R12); resposta só quando o cliente escreve | **ok** |
| Dois sockets ou reconexão em laço | COMUNIDADE (suspeita de conflito → ban) | Uma fila e um socket (R1); a convivência não toca ninguém novo até 30 min depois de reconectar (R45) | **ok** pelo desenho. O laço de reconexão do dreno não foi visto. |
| Conferir número repetidas vezes (`onWhatsApp`, `isRegisteredUser`) | COMUNIDADE (~80 por hora → restrição) | Nada no pacote chama essas funções | **conferir no PC:** o `hunting.js` está fora do pacote. |
| Celular principal 14 dias sem uso | OFICIAL (aparelhos vinculados desconectados) | Nada | **falta** como rotina (W04); não é código. |
| Versão do cliente | COMUNIDADE ("use a última"; o 463 só é tratado no 7.0.0-rc13+) | Baileys `^6.7.9` | **conferir:** testar o 7.x num número de laboratório (W03). |
| IP de datacenter | COMUNIDADE (hipótese) | Sessão no servidor | registro (W05) |
| Link na primeira mensagem | nenhuma fonte encontrada | Nada | **sem base pública:** não mexi. |
| Marcar ou não como lido, "digitando" | nenhuma fonte ligando isso a ban; "digitando" só como sugestão de comunidade | Fica no dreno, fora do pacote | sem base: não mexi |

## Apertado demais?

Nada que eu mudaria. Dois pontos seguram mais do que os relatos pedem, e os dois são escolha deliberada do dono depois do banimento de 24/09:
- **2 interações novas por dia:** os relatos de restrição começam em 15 por dia.
- **48 h sem interação nova depois de qualquer sinal.**

Por isso não proponho afrouxar nenhum dos dois.

O patch 01 aperta um pouco mais: a palavra `restrict` pode armar o disjuntor num erro que não é de conta.

## O que pesa de verdade

O maior risco que sobra não está no volume: são os Termos do Business App em vigor desde 23/09/2026 (W06) e a detecção de cliente não oficial, que o WhatsApp testa desde setembro de 2026 segundo a imprensa. Nenhum teto zera isso. Por isso o plano B importa mais que mais um ajuste fino.
