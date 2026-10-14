# Só dá para conferir com a XP ou com dado real (tarefa 25)

Nenhuma página oficial foi aberta nesta tarefa, por decisão de saldo. O que segue é pergunta, não resposta.

## Para a XP (ou o compliance dela)

1. **Prazo e formato da guarda.**
   - Os 5 anos contam do envio?
   - O registro do próprio escritório (JSONL com hash encadeado, fora da nuvem pública) atende? Ou a guarda tem de ser pelo canal gravado do intermediário?
   - Qual formato de entrega, se pedirem?
2. **Agenda de vencimento conta como extrato** (art. 25, VII)? É o D03 da tarefa 19. Muda o padrão de `bloquearAgendaDeVencimento`.
3. **Anexo:**
   - O que pode ir? Por exemplo, convite, lâmina pública, material institucional da XP.
   - Basta o texto extraído pelo próprio escritório para julgar, ou anexo com dado de cliente é vedado sempre?
4. **Mensagem recebida.** A obrigação de guarda cobre também o que o cliente manda, ou só o que sai? Hoje o registro guarda só o que sai.
5. **WhatsApp pessoal.** Mensagem pelo WhatsApp pessoal registrada só pelo motor basta? Hoje sai com o aviso R05, de canal não gravado.

## Para o dono (decisão)

- **Onde fica a cópia de segurança do registro.** São 5 anos, fora do OneDrive (decisão já tomada). O registro é append-only e verificável, então dá para copiar inteiro e conferir com `verificar`. Opções a decidir: a VPS, o R2, um disco externo.
- **Quem aprova anexo pelo hash** e se a lista começa vazia (padrão) ou com algum material institucional.
- **Nova tentativa depois de falha do canal.** A recomendação é um id por tentativa (`<id>#2`). Ver `para-o-fila.md`.

## Só com dado real

- Os nomes de campo do item no `fila.js` real (destino, canal, aprovação).
- O extrator de texto de PDF e imagem que vai alimentar `anexos[].texto`, e o que ele devolve num print de carteira. Se vier vazio, o anexo barra, que é o certo.
- O volume de mensagens por ano, para saber quando um índice passa a valer a pena.
