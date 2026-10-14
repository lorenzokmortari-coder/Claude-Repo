# Plano de aquecimento: 4 semanas, por caixa (Ozav, domínio separado, 14/10/2026)

**Importante:**
- **Nenhuma fonte oficial publica uma tabela semanal.** O Google diz para começar baixo com destinatários engajados, subir devagar (de 25% a 100% ao dia depois de um adiamento) e nunca dobrar de uma vez.
- Os números por dia abaixo são **faixa de fornecedor** (Instantly, Smartlead, lemlist e outros), marcados na última coluna.
- Os limites de parada (spam abaixo de 0,1%, nunca 0,3%; descadastro em 48 h) são do Gmail (oficial, via trecho do buscador).

| Semana | Dias | Aquecimento/dia | Frios/dia | Teto/dia | O que fazer | Pare se | Fonte dos números |
|---|---|---|---|---|---|---|---|
| 0 | antes do dia 1 | 0 | 0 | 0 | Registrar o domínio separado. Publicar SPF, DKIM de 2048 bits, DMARC p=none com rua e MX para a caixa que lê as respostas. Rodar o conferir_dominio.py até não faltar nada. Escrever a LIA (LGPD) e o aviso de privacidade. Montar a lista de supressão. | qualquer FALTA no conferir_dominio.py | OFICIAL (Gmail, Yahoo, Microsoft) para o DNS; nossa para o resto |
| 1 | 1 a 7 | 5 subindo até 15 | 0 | 15 | Só conversa que gera resposta: o time, parceiros e contatos que já conhecem a Ozav (ou ferramenta de aquecimento). Nenhum e-mail frio. Assinatura completa. | devolução por autenticação (5.7.26, 5.7.27, 5.7.30) ou bounce acima de 2% | FORNECEDOR (Instantly, Smartlead, lemlist e outros: faixa de mercado) |
| 2 | 8 a 14 | 15 subindo até 25 | 0 | 25 | Continua só aquecimento. Abrir o Postmaster Tools e ler os relatórios DMARC (rua) todo dia. | spam no Postmaster acima de 0,1% ou fonte desconhecida mandando pelo domínio no relatório DMARC | FORNECEDOR; o 0,1% é OFICIAL (Gmail) |
| 3 | 15 a 21 | cerca de 20 | 5 subindo até 10 | 30 | Primeiros frios só para lista verificada (e-mail corporativo validado, origem registrada). Texto simples, 0 ou 1 link, sem anexo, sem pixel de abertura. Descadastro em um clique e no corpo. | bounce acima de 2%; qualquer reclamação; adiamento 4.7.x (pausar 15 min, mandar 1 teste e ficar 24 h abaixo do nível) | FORNECEDOR; a regra do adiamento é OFICIAL (Gmail) |
| 4 | 22 a 28 | 15 a 20 | 15 subindo até 25 | 40 | Subir os frios de 2 a 3 por dia, nunca dobrar de um dia para o outro. Responder toda resposta no mesmo dia. Honrar descadastro em até 48 h. | bounce acima de 2%; spam a partir de 0,1%; parar tudo em 0,3% | FORNECEDOR (teto de 40 por caixa e 120 por domínio: lemlist); 48 h e 0,3% são OFICIAL (Gmail) |
| 5 em diante | 29 em diante | 10 a 15 (manter) | até 25 a 30 | 40 | Escalar com mais caixas aquecidas no mesmo domínio (até 120 por dia no domínio, somando tudo), não com mais volume por caixa. Depois de 2 a 4 semanas de relatório rua limpo, subir o DMARC para p=quarantine. | os mesmos limites | FORNECEDOR; o prazo do DMARC é prática de mercado (não verificado) |

**Escalar:** a Ozav vai querer mais do que 25 a 30 frios por dia. O caminho de mercado é mais caixas no domínio separado (até cerca de 120 por dia no domínio, somando aquecimento e frio), cada uma aquecida do zero. Não é mais volume por caixa.

**O teto físico do Google Workspace** é de 2.000 mensagens por dia por usuário (oficial), muito acima do que o aquecimento permite.
