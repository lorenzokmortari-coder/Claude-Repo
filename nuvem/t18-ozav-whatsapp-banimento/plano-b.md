# Plano B: se o número da Ozav cair (14/10/2026)

O que deixar pronto antes e o que fazer na primeira hora. Os passos não mandam nada a ninguém sozinhos: todo aviso a cliente é rascunho para o Lorenzo aprovar.

## Os três estados (saber qual é em 2 minutos)

| O que aparece no celular do número | O que é | Dura | O que dá para fazer | Fonte |
|---|---|---|---|---|
| "Sua conta está restrita" (ou o servidor perdeu a sessão e no app aparece o aviso) | Restrição | "tempo alocado"; os relatos falam em 24 h. Para ver quanto falta: Nova conversa → um contato com quem nunca falou → o aviso mostra o tempo | Continua falando com quem já conversou. Não inicia conversa nova, não cria grupo, não adiciona ninguém. **Perde os aparelhos vinculados**, então o servidor cai | OFICIAL via trecho do buscador: faq.whatsapp.com/717472490411581; relatos: issues 2800 e 2441 do Baileys |
| "Banida temporariamente", com contagem | Ban temporário | Contagem na tela; nos relatos, 24 h a 48 h, com escalada | Esperar. A orientação oficial fala em deixar o cliente não oficial, e insistir pode virar ban permanente | OFICIAL via trecho do buscador: faq.whatsapp.com/1848531392146538; relato: issue 1983 do Baileys |
| "Este número não pode usar o WhatsApp", com botão "Solicitar análise" | Ban | Permanente, salvo revisão | Pedir a revisão **uma vez**, no próprio app; a maioria sai em até 24 h. **Sem o botão, o ban é final** | OFICIAL via trecho do buscador: faq.whatsapp.com/465883178708358 |

## Antes (deixar pronto agora)

1. **Rotina do celular:** abrir o WhatsApp Business no celular do número a cada 10 dias, no máximo. Com 14 dias sem uso, os aparelhos vinculados caem (W04).
2. **Lista de contato fora do WhatsApp:** para cada cliente ativo, a empresa e um e-mail de contato, tirados do CRM, o Twenty.
   - O `correio`/e-mail já é o segundo canal da R37.
   - Conferir com dado real: quantos clientes ativos não têm e-mail no CRM.
3. **Rascunho do aviso a cliente**, para o Lorenzo aprovar antes de qualquer envio. É curto e sem pedir desculpa demais: "O WhatsApp da Ozav está fora do ar por algumas horas. Qualquer coisa urgente, responda este e-mail ou fale com [canal]. Voltamos a falar por lá assim que normalizar."
4. **Comando de parada à mão**, já documentado: `node whatsapp-governador.js --pausar 1440 numero caiu`. O disjuntor arma sozinho com o sinal (patch 01), mas a pausa garante que nenhuma fila sai na volta antes de alguém olhar.
5. **Forense pronta:** o que guardar no minuto zero.
   - O `whatsapp-governador.jsonl` das últimas 48 h.
   - O `catraca.jsonl`.
   - As últimas linhas do log do dreno.
   - O `ultimo_sinal` do estado.
   - É o mesmo material da análise de 23/09.
6. **Número de laboratório (opcional, decisão do dono):** um chip que não é o da Ozav, para testar o Baileys 7.x (W03) e qualquer mudança no dreno. Não é número reserva para fugir de ban: usar outro número para continuar o mesmo envio que levou ao ban viola os termos.
7. **Rota de saída (decisão do dono):** a API oficial do WhatsApp (Cloud API) tira o risco de cliente não oficial, mas cobra por conversa e muda a operação. Vale ter o custo levantado para não decidir no susto.

## Primeira hora (em ordem)

1. **Minuto 0:** `node whatsapp-governador.js --pausar 1440 numero caiu` e `node whatsapp-governador.js --status`. Nada mais sai.
2. **Minuto 5:** não reconectar o Baileys em laço nem ler o QR de novo. Cada tentativa num número restrito pode piorar. Se o dreno reconecta sozinho, parar o serviço da captura.
3. **Minuto 10:** abrir o app no celular do número e ver qual dos três estados é.
4. **Minuto 15, se for restrição:** responder os clientes que estão esperando pelo próprio celular. As conversas existentes continuam funcionando. Não criar grupo e não adicionar ninguém. Religar o servidor só depois que a restrição acabar, e com o aquecimento (`--aquecer`).
5. **Minuto 15, se for ban com o botão:** pedir a análise uma única vez. O texto é curto e verdadeiro: empresa de câmbio B2B que fala com clientes que pediram contato. Contatar o suporte fora do fluxo não acelera.
6. **Minuto 20:** o Lorenzo decide se manda o aviso aos clientes ativos por e-mail, com o rascunho pronto. Nenhum robô manda isso sozinho.
7. **Minuto 30:** guardar a forense e anotar o que saiu nas 24 h anteriores:
   - quantas interações novas;
   - quantas mensagens sem resposta (patch 02);
   - qual robô, que erro.
8. **Na volta:** reparear com o aquecimento de 5 dias e `--novas-desde` no dia seguinte. Se o número for novo, aquecer mais: os relatos falam em 7 a 30 dias, e o teto de 5 dias é para o mesmo número.

## O que não fazer

- Não trocar para outro número às pressas para continuar o mesmo envio.
- Não instalar outra biblioteca de WhatsApp no meio da crise.
- Não pedir revisão mais de uma vez.
- Não pôr o número de alguém do time no lugar.
