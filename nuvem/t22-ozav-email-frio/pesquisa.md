# T22: e-mail frio B2B em domínio separado. Regras de entregabilidade e LGPD (2025-2026)

Pesquisa feita em 14/10/2026. Contexto: empresa B2B de câmbio (Brasil) vai prospectar por e-mail frio num domínio separado do principal.

## Nota de método (leia antes)

- **Nenhuma página pôde ser aberta.** O WebFetch falhou com `getaddrinfo ENOTFOUND` em todas as tentativas, e o proxy de saída recusou com 403 todos os domínios oficiais pedidos via curl. A lista completa está na seção (f).
- Tudo o que vem abaixo saiu de **trechos e resumos que o buscador (WebSearch) associou a cada URL**. Não li o texto integral de nenhuma página.
- Legenda de verificação:
  - **[TB]**: conferido em trecho do buscador atribuído àquela URL. A página não foi aberta.
  - **[NV]**: não verificado. Não apareceu em nenhum trecho, ou vem só de memória ou de análise própria.
  - **[CONFLITO]**: as fontes divergem.
- Legenda de natureza:
  - **OFICIAL**: Google, Yahoo, Microsoft, ANPD, planalto.gov.br, RFC/IETF.
  - **FORNECEDOR**: ferramentas de envio ou entregabilidade, que têm interesse comercial.
  - **COMUNIDADE**: fóruns, blogs, imprensa, escritórios de advocacia e doutrina.
- Antes de qualquer decisão, confira os números nas páginas oficiais vivas. Os trechos podem vir de cache antigo, e o próprio buscador avisou isso para as páginas do Gmail e do Yahoo.

---

## (a) Requisitos por provedor

Escopo de cada provedor:
- **Gmail:** o limiar de 5.000/dia conta mensagens para **contas pessoais do Gmail**. Se as regras também se aplicam a destinatários Google Workspace é [NV].
- **Microsoft:** as regras de alto volume valem para o **Outlook.com de consumidor** (outlook.com, hotmail.com, live.com). Os trechos não indicam que valham para tenants corporativos Microsoft 365, onde está a maior parte do público B2B. A filtragem do Microsoft 365 (EOP) **não foi pesquisada**.

| Requisito | Gmail | Yahoo | Microsoft (Outlook.com consumidor) | URL (todas OFICIAL salvo indicação) | Vigência |
|---|---|---|---|---|---|
| Quem é "remetente em volume" | "close to 5,000 messages or more to personal Gmail accounts within a 24-hour period". Mensagens do mesmo domínio primário somam no limite [TB]. "Uma vez em volume, sempre em volume" [NV] | Exige requisitos de "bulk sender", mas nenhum trecho trouxe um limiar numérico [NV] | "5,000 or more email messages", todas com o mesmo domínio no 5322.From [TB] | G2 https://support.google.com/mail/answer/14229414?hl=en · Y1 https://senders.yahooinc.com/best-practices/ · M2 https://support.microsoft.com/en-us/outlook/fix-ndr-error-550-5-7-515-in-outlook-com | Gmail e Yahoo: fev/2024. Microsoft: 05/05/2025 |
| Domínio novo | "New domain" é o que não enviou mais de 5.000/dia a contas pessoais Gmail desde 01/01/2024. A progressão de enforcement para domínios novos é "on an accelerated timetable" [TB] | n/d [NV] | n/d [NV] | G2 | Em vigor (o FAQ cita a escalada de nov/2025) |
| SPF | Todos: SPF **ou** DKIM. Volume: SPF **e** DKIM [TB] | Todos: SPF ou DKIM. Volume: SPF e DKIM [TB] | Volume: SPF deve passar [TB] | G1 https://support.google.com/mail/answer/81126?hl=en · Y1 · M1 (ver nota 1) | Gmail e Yahoo: 01/02/2024. Microsoft: 05/05/2025 |
| DKIM e tamanho de chave | Chave de **1024 bits ou mais**, **2048 recomendada** [TB] | "minimum 1024-bit key length" [TB]. 2048 não aparece nos trechos | DKIM deve passar [TB]. Tamanho de chave não encontrado [NV] | G1 · Y1 · M1 | Idem |
| DMARC: política mínima | Volume: registro DMARC publicado. "Your DMARC enforcement policy can be set to none" [TB] | Volume: "p=none" ou mais restrita, e o DMARC precisa passar. Tag `rua` "strongly recommended" [TB] | Volume: no mínimo **p=none**. Trecho de política do Outlook: "p=reject is recommended" [TB] | G2 · Y1 · M1 · M3 https://learn.microsoft.com/en-us/defender-office-365/external-senders-policies-practices-guidelines | Idem |
| DMARC: alinhamento | O domínio do From: alinhado ao domínio do SPF **ou** do DKIM [TB] | From alinhado a SPF ou DKIM. Alinhamento relaxado é aceito [TB] | SPF e/ou DKIM (ao menos um) alinhado ao 5322.From, "preferably both" [TB] | G1 · Y1 · M1 · M2 | Idem |
| PTR / rDNS | Todos: PTR para o IP de envio, com o hostname resolvendo de volta ao mesmo IP (FCrDNS) [TB] | Todos: "valid forward and reverse DNS" [TB]. Sem rDNS, a reputação do IP tende a cair [TB] | Política do Outlook.com: rDNS válido. IP dinâmico pode ser recusado. Até 500 conexões simultâneas sem acordo prévio [TB] | G1 · Y1 · Y2 https://senders.yahooinc.com/faqs/ · M3 / M4 https://sendersupport.olc.protection.outlook.com/pm/policies.aspx | Gmail e Yahoo: fev/2024. Microsoft: política permanente |
| TLS | Todos: conexão TLS para transmitir [TB]. O buscador indicou que o item entrou em dez/2023 [NV] | Nenhum trecho menciona TLS [NV] | Não encontrado [NV] | G1 | Gmail: fev/2024 |
| Formato RFC 5322 | Todos: seguir a RFC 5322 e ter Message-ID válido. HTML conforme os padrões HTML [TB] | Todos: RFC 5321 e 5322 [TB] | Não encontrado [NV] | G1 · Y1 | fev/2024 |
| Cancelamento em um clique (RFC 8058) | Volume, só para mensagens de marketing e promoção (transacionais isentas). Exige os cabeçalhos List-Unsubscribe e List-Unsubscribe-Post. "Including a mailto link in the body … doesn't meet our one-click unsubscribe requirement" [TB] | Exige List-Unsubscribe funcional. Método POST (RFC 8058) "highly recommended", mailto "acceptable". Também pede link de descadastro visível no corpo [TB] | Recomenda (não exige) "functional/visible unsubscribe links" [TB, via COMUNIDADE]. RFC 8058 não citada nos trechos [NV] | G1 · G2 · Y1 · Y3 https://blog.postmaster.yahooinc.com/post/730172167494483968/more-secure-less-spam · M1 | Gmail: **01/06/2024** para quem já tinha link de descadastro [TB]. Yahoo: "starting June 2024" [TB] |
| Prazo para honrar descadastro | **48 horas** ("fulfill unsubscribe requests within 48 hours"). Não cumprir tira o remetente da elegibilidade a suporte e mitigação [TB] | **2 dias** ("honor our users requests within two days") [TB] | Prazo não encontrado [NV] | G2 · Y1 · Y3 | 2024 |
| Taxa de spam | Manter **< 0,10%** no Postmaster Tools e nunca chegar a **0,30%**. Acima de 0,3%, o remetente fica inelegível a mitigação (desde jun/2024) [TB] | **< 0,3%**, calculada só sobre mensagens entregues na caixa de entrada [TB] | Limiar numérico não encontrado [NV] | G1 · G2 · G3 https://support.google.com/mail/answer/14668346?hl=en · Y1 | Gmail: jun/2024 (0,3% para mitigação) |
| Painel de conformidade | Postmaster Tools tem painel "Compliance status" para volume (DMARC, um clique, honrar descadastro). Domínio com pouco tráfego pode ficar sem dados [TB] | Sender Hub com taxa de reclamação [TB] | SNDS e Postmaster do Outlook.com (abrir chamado em caso de rate limit) [TB] | G3 · Y1 · M4 | n/d |
| Consequência / enforcement | **A partir de nov/2025** o Gmail "ramping up enforcement on non-compliant traffic", com **rejeições temporárias e permanentes** [TB]. Códigos: 4.7.x são throttling, com recuo exponencial. 5.7.26 (não autenticado), 5.7.27 (SPF) e 5.7.30 (DKIM) são bloqueios [TB]. [CONFLITO] O código temporário de DMARC ausente aparece como 4.7.31 no FAQ e 4.7.40 na página de erros SMTP | Enforcement gradual no 1º semestre de 2024 [TB] | O anúncio (abr/2025) diz que, **após 05/05/2025**, mensagens não conformes iriam para o **Lixo Eletrônico**, com **rejeição depois** e data não anunciada no trecho [TB]. O NDR **550 5.7.515** "Access denied, sending domain … does not meet the required authentication level" está documentado em página oficial de suporte, e há relatos de 2026 (COMUNIDADE) com esse código [TB]. [CONFLITO] Sobre quando a rejeição começou (ver nota 1) | G2 · G4 https://support.google.com/a/answer/3726730?hl=en · Y4 https://blog.postmaster.yahooinc.com/post/737268108173230080/an-update-on-enforcing-email-standards · M1 · M2 · M5 (COMUNIDADE) https://techcommunity.microsoft.com/discussions/outlookgeneral/failed-to-send-emails-to-outlookhotmail-recipients-returns-error-550-5-7-515/4498481 | Gmail: nov/2025. Microsoft: 05/05/2025 (Lixo Eletrônico), rejeição depois |
| Práticas recomendadas extras | Não usar HTML/CSS para esconder conteúdo. Links visíveis e compreensíveis. Não usar emojis que imitem elementos gráficos ou selos de verificação [TB] | n/d | From e Reply-To válidos, descadastro visível, higiene de lista, assunto fiel ao conteúdo, consentimento prévio. São **recomendações**, não exigências [TB, via COMUNIDADE]. O item "compliant P2 sender address" do anúncio não aparece em nenhum trecho [NV] | G1 · M1 | n/d |
| Limite de envio da caixa (Google Workspace) | **2.000 mensagens/dia por usuário** (janela móvel de 24 h), 1.500 via mala direta e 500 em conta de teste. Os limites podem mudar sem aviso [TB] | n/a | n/a | G6 https://support.google.com/a/answer/166852?hl=en · https://knowledge.workspace.google.com/admin/gmail/gmail-sending-limits-in-google-workspace | Vigente |

**Nota 1: cronologia da Microsoft [CONFLITO].**
- URL M1: https://techcommunity.microsoft.com/blog/microsoftdefenderforoffice365blog/strengthening-email-ecosystem-outlook%E2%80%99s-new-requirements-for-high%E2%80%90volume-senders/4399730
- O que os trechos oficiais confirmam:
  - Lixo Eletrônico a partir de 05/05/2025 e rejeição "eventually".
  - Uma atualização de 29/04 citando a resposta 550 5.7.515.
- O que dizem fornecedores e comunidade:
  - dmarcian (https://dmarcian.com/microsoft-enforces-spf-dkim-dmarc/) e outros dizem que a ideia inicial era rejeitar direto e que depois a Microsoft suavizou para "Lixo primeiro".
  - Um "tracker" de fornecedor diz que as rejeições graduais começaram em set/2025, com efeito pleno no início de 2026. Não identifiquei qual URL [NV].
- **Resposta à pergunta "a Microsoft rejeita desde maio/2025?":** não confirmado. O que está confirmado por fonte oficial é o Lixo Eletrônico desde 05/05/2025. A rejeição com 5.7.515 existe e está documentada, mas a data de início não foi verificada.

**Resposta à pergunta "o Gmail começou a rejeitar em nov/2025?":** sim, segundo o trecho do FAQ oficial (G2) [TB]. Desde nov/2025 há escalada de enforcement com rejeições temporárias e permanentes, aplicada de forma gradual e mais rápida para domínios novos.

**Implicação para o domínio separado (análise, não fonte):**
- O Gmail soma o volume por domínio primário (G2 [TB]). Um domínio registrável separado (não subdomínio do principal) tem contagem e reputação próprias.
- Mesmo abaixo de 5.000/dia, vale cumprir o pacote "volume" desde o início:
  - SPF e DKIM com chave de 2048 bits, ambos alinhados.
  - DMARC publicado com `rua`.
  - PTR e TLS (já cobertos se usar Google Workspace ou Microsoft 365 como servidor de envio [NV]).
  - List-Unsubscribe com One-Click.
  - Descadastro honrado em até 48 h.
- Motivo: o enforcement de domínio novo é acelerado, e um descuido custa mais caro a um domínio sem histórico.

**RFC 8058 (OFICIAL), https://rfc-editor.org/rfc/rfc8058 [TB]:**
- A mensagem "MUST have a valid DomainKeys Identified Mail (DKIM) signature that covers at least the List-Unsubscribe and List-Unsubscribe-Post headers", e os dois devem constar na tag `h=`.
- O receptor faz HTTPS POST na URI do List-Unsubscribe, com o corpo `List-Unsubscribe=One-Click`.
- Sem cookies nem autenticação HTTP. O remetente não deve responder com redirect.
- Sem assinatura DKIM, o receptor não deve oferecer o um clique.
- Erratum 5559 é editorial.

---

## (b) Aquecimento de domínio novo e de caixa

### OFICIAL

**Google** (G1 https://support.google.com/mail/answer/81126?hl=en; G5 https://support.google.com/mail/answer/15256272?hl=en; G2). O buscador não separou qual frase vem de qual página entre G1, G2 e G5 [TB]:
- Começar com volume baixo para usuários engajados e aumentar devagar. Enviar com consistência, sem rajadas.
- Quanto maior o volume, mais lento deve ser o aumento. Envio diário permite subir mais rápido que envio semanal.
- Depois de um adiamento (deferral): pausar cerca de 15 min, mandar 1 mensagem de teste e ficar 24 h abaixo do nível que causou o adiamento. Daí em diante, aumento diário típico de **25% a 100%**, conforme fatores.
- "Immediately doubling previously sent volumes suddenly could result in rate limiting or reputation drops."
- Cotas por domínio **e** por IP. Quando o IP atinge a cota, todos os domínios naquele IP param.
- Volume consistente é "particularly important for new domains".
- O Postmaster Tools pode não mostrar dados para domínio com pouco tráfego (G3) [TB].
- **Teto físico:** 2.000 mensagens/dia por usuário Workspace e 500 em conta de teste (G6) [TB].

**Microsoft** (M3 https://learn.microsoft.com/en-us/defender-office-365/external-senders-policies-practices-guidelines e/ou M4 https://sendersupport.olc.protection.outlook.com/pm/policies.aspx; URL exata do trecho não determinada) [TB]:
- Um IP novo "can expect to be fully ramped within a couple of weeks or sooner depending on volume, list accuracy" e com reclamações mínimas.
- IP novo em domínio com SPF e boa reputação pode herdar parte dela.
- Material Dynamics 365, que é OFICIAL mas genérico de marketing e não específico do Outlook.com (https://learn.microsoft.com/en-us/dynamics365/customer-insights/journeys/warmup-process-email-marketing) [TB]: nas semanas 1 e 2, enviar aos mais ativos (abriram ou clicaram nos últimos 30 dias) e começar com volume baixo a moderado.

**Yahoo** (Y2 https://senders.yahooinc.com/faqs/) [TB]:
- Não há cronograma publicado.
- Remetente novo ou IP novo com dificuldade deve abrir "Sender Support Request".
- Ausência de rDNS aumenta a chance de rebaixar a reputação do IP.

**Observação:** nenhuma fonte oficial publica uma tabela de "X e-mails/dia na semana N" para domínio novo. Os números semanais abaixo são todos de fornecedores.

### FORNECEDOR / COMUNIDADE

| Fonte (natureza) | Duração do aquecimento | Início | Teto por caixa | URL |
|---|---|---|---|---|
| Instantly (FORNECEDOR) | ≥ 2 semanas para caixa nova. 4 semanas "safer" para domínio novo | 10-15/dia por caixa na semana 1. Na produção, a ferramenta sobe o limite em +2/dia (10, 12, 15, 18…) | ≤ 30 e-mails frios/caixa/dia | https://instantly.ai/blog/slow-ramp-plan-for-new-cold-email-domains-deliverability/ · https://instantly.ai/blog/what-is-slow-ramp-warmup/ |
| Smartlead (FORNECEDOR) | 3-4 semanas para domínio novo. 6-8 semanas para domínio com histórico ruim ou saindo de blocklist | 5-10/dia, subindo para 25, 50 e 100 ao longo das semanas | n/d | https://www.smartlead.ai/blog/email-warm-up-guide · https://www.smartlead.ai/blog/how-many-cold-emails-per-day |
| lemlist (FORNECEDOR) | 3-5 semanas (título do guia de 2026) | +1 e-mail de aquecimento/dia até cerca de 20/dia | ≤ 40/dia por caixa e ≤ 120/dia por domínio, **somando aquecimento e prospecção** | https://www.lemlist.com/blog/warm-up-email-account |
| Diversos (FORNECEDOR/COMUNIDADE: InboxAlly, NameSilo, LeadHaste, SyncGTM) | 2-3 semanas (caixa nova em domínio antigo) a 4-8 semanas (domínio novo). Um guia recomenda nada de e-mail frio nos primeiros 14 dias | Semana 1: 5-10 ou 10-20/dia. Semana 2: 10-15 (há quem fale em 30-50). Semana 3: 15-25. Semana 4: 25-30 | 30-50/caixa/dia. Para escalar, mais caixas e domínios, não mais volume por caixa | https://inboxally.helpjuice.com/en_US/faqs/how-long-does-it-take-to-warm-up-a-domain · https://www.namesilo.com/blog/en/email/how-to-warm-up-a-new-domain-for-cold-email-outreach · https://leadhaste.com/blog/email-warmup-timeline-and-schedule · https://syncgtm.com/blog/how-long-to-warm-up-email |
| Limites de saúde (FORNECEDOR) | n/a | n/a | Bounce abaixo de 1% a 3%, conforme a fonte. Reclamações bem abaixo de 0,3% | Mesmas URLs acima |

O buscador não mapeou cada número a uma URL individual nos fornecedores "diversos". Trate a linha como faixa de mercado [TB, atribuição individual NV].

**Síntese prática** (nossa, montada a partir de fornecedores; **não é regra oficial**):
- Semanas 1 e 2: só aquecimento.
- Semana 3: 5-10 e-mails frios/dia por caixa.
- Semana 4: 15-25/dia.
- Depois: até 25-30/dia por caixa, com bounce abaixo de 2% e spam bem abaixo de 0,1% no Postmaster.
- Para escalar, adicionar caixas aquecidas, não subir o volume por caixa.

---

## (c) Conteúdo e links que derrubam a entrega

| Item | OFICIAL | FORNECEDOR / COMUNIDADE | URL |
|---|---|---|---|
| Encurtadores de URL | Nenhum trecho oficial do Google menciona encurtadores [NV] | Domínios em blocklist, seja no remetente, no domínio de rastreamento ou nos links, prejudicam a entrega. Encurtadores compartilhados herdam reputação alheia (inferência a partir disso) [NV] | G1 · https://www.warmy.io/blog/impact-of-tracking-links-deliverability/ |
| Muitos links | Google: links no corpo "visible and easy to understand", e o destinatário deve saber o que esperar ao clicar [TB] | "too many links … may be considered suspicious" [TB] | G1 · https://www.warmy.io/blog/impact-of-tracking-links-deliverability/ |
| Imagens / HTML pesado | Google: HTML deve seguir os padrões HTML. Não usar HTML/CSS para esconder conteúdo, sob risco de spam. Não usar emojis que imitem elementos gráficos [TB] | Imagens "might cause more of your emails go into spam" [TB] | G1 · https://www.warmy.io/blog/impact-of-tracking-links-deliverability/ |
| Pixel de rastreamento de abertura | Nada oficial encontrado [NV] | Pixel pode prejudicar, sobretudo em domínio de rastreamento compartilhado com má reputação. Taxa de abertura já é distorcida pela privacidade da Apple ("40-50%") [TB] | https://instantly.ai/blog/email-tracking-and-deliverability-why-tracking-pixels-can-hurt-your-inbox-placement/ |
| Rastreamento de clique / domínio de link diferente do remetente | Google exige alinhamento só do From com SPF/DKIM. Domínio de link não faz parte da regra de alinhamento (G1) [TB] | lemlist: links não rastreados entregam melhor. Alternativas: desligar o rastreamento de clique ou usar **domínio de rastreamento próprio (custom tracking domain)**, que isola a reputação [TB]. É afirmação de fornecedor sem dados publicados | https://help.lemlist.com/en/articles/13941647-lemcoach-should-you-track-clicks-and-opens-in-cold-email-campaigns |
| Anexos | Nada oficial encontrado [NV] | Anexo de remetente desconhecido levanta suspeita de malware (Wikipedia, COMUNIDADE) [TB] | https://en.wikipedia.org/wiki/Cold_email |
| Palavras-gatilho | Nada oficial encontrado [NV] | **Em grande parte mito.** Filtros modernos ignoram listas estáticas e pesam reputação, engajamento, autenticação e contexto. Ressalva: palavras "spammy" podem elevar reclamações e afetar a reputação de forma indireta [TB] | https://www.litmus.com/blog/why-spam-trigger-words-are-a-thing-of-the-past · https://www.suped.com/knowledge/email-deliverability/technical/are-spam-trigger-word-lists-accurate-and-should-i-be-concerned-about-them · https://www.marketingprofs.com/articles/2018/33734/do-you-still-believe-these-three-urban-myths-of-email-marketing · https://mailmodo.com/guides/spam-words |

**Leitura combinada:**
- O que derruba a entrega, pelas fontes oficiais, é autenticação, reputação e taxa de spam, não o texto em si.
- Em e-mail frio, a prática de mercado (FORNECEDOR) é:
  - texto simples ou HTML mínimo, com 0 a 1 link;
  - sem anexo e sem imagem;
  - rastreamento de abertura desligado;
  - rastreamento de clique desligado, ou com domínio próprio.

---

## (d) LGPD no e-mail frio B2B

### Lei 13.709/2018 (OFICIAL)

URLs: https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm (texto compilado: https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm). O planalto.gov.br estava bloqueado; os trechos vêm do buscador.

| Dispositivo | Citação curta / conteúdo | Verificação |
|---|---|---|
| Art. 7º, IX | Tratamento "quando necessário para atender aos interesses legítimos do controlador ou de terceiro, exceto no caso de prevalecerem direitos e liberdades fundamentais do titular que exijam a proteção dos dados (…)" | [TB] |
| Art. 10, caput | "O legítimo interesse do controlador somente poderá fundamentar tratamento de dados pessoais para finalidades legítimas, consideradas a partir de situações concretas". O rol exemplificativo inclui (I) "apoio e promoção de atividades do controlador" e (II) proteção do exercício regular de direitos do titular ou prestação de serviços que o beneficiem | [TB] |
| Art. 10, §1º | Somente "os dados pessoais estritamente necessários para a finalidade pretendida poderão ser tratados" | [TB] |
| Art. 10, §2º | O controlador "deverá adotar medidas para garantir a transparência do tratamento" baseado em legítimo interesse | [TB] |
| Art. 10, §3º | A ANPD pode pedir relatório de impacto (RIPD), respeitados os segredos comercial e industrial | [TB] |
| Art. 37 | Dever de controlador e operador de manter registro das operações de tratamento, com ênfase em legítimo interesse ("especialmente quando baseado no legítimo interesse") | [TB parcial: ênfase confirmada, frase literal NV] |
| Art. 18, §2º | Direito de oposição a tratamento feito com base em hipótese que dispensa consentimento, em caso de descumprimento da LGPD. O Guia da ANPD lê de forma ampla: o titular pode se opor se discordar da avaliação do controlador ou se o tratamento violar suas legítimas expectativas | [TB]. [CONFLITO] Uma contribuição em nota técnica de consulta pública defendia leitura mais restritiva |
| Art. 6º, X | Responsabilização e prestação de contas. O Guia liga o teste de balanceamento a esse princípio e ao art. 37 | [TB] |
| Art. 5º, I | Definição de dado pessoal: informação de pessoa natural identificada ou identificável | [NV]. Implica que e-mail nominal corporativo (nome.sobrenome@empresa) é dado pessoal; nenhuma fonte oficial nos trechos tratou do "dado de contato corporativo" |
| Art. 19, II / art. 9º (origem do dado e transparência) | A declaração "que indique a origem dos dados" e o dever de informar não apareceram em nenhum trecho | [NV] |
| Sanções (art. 52) | Blog cita 2% do faturamento, limitado a R$ 50 milhões por infração | [NV], fonte secundária |

### Guia Orientativo ANPD "Hipóteses legais de tratamento de dados pessoais: Legítimo Interesse" (OFICIAL)

URLs:
- PDF: https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/guia_legitimo_interesse.pdf/@@display-file/file
- Notícia: https://www.gov.br/anpd/pt-br/assuntos/noticias/anpd-lanca-guia-orientativo-sobre-legitimo-interesse

**Data: fevereiro/2024, confirmado [TB].** [CONFLITO] sobre o dia:
- 02/02/2024 segundo escritórios (COMUNIDADE): https://www.mattosfilho.com.br/unico/anpd-legitimo-interesse-lgpd/ e https://confidata.com.br/blog/legitimo-interesse-lgpd-lia-exemplos-limites
- 15/02/2024 segundo listagem de governo estadual: https://sedu.es.gov.br/GrupodeArquivos/materiais-e-publicacoes-da-anpd
- Nota técnica da ANPD: "Em fevereiro de 2024 a ANPD publicou o guia".

**Teste de balanceamento** em três fases: "i) finalidade; ii) necessidade; e iii) balanceamento e salvaguardas" [TB].
- Deve ser aplicado "para cada finalidade específica" [TB].
- "O modelo proposto pela ANPD não é de uso obrigatório". O controlador pode usar outro método conforme a LGPD [TB].
- Modelo simplificado no Anexo II (COMUNIDADE: confidata) [TB].
- É "ferramenta essencial para demonstrar a conformidade (…) nos termos do art. 6º, X (…) e do art. 37" [TB].
- [CONFLITO]: na consulta pública houve quem defendesse que o teste fosse obrigatório. O guia final o trata como boa prática e medida recomendada. Fonte: https://www.gov.br/anpd/pt-br/acesso-a-informacao_antigo/audiencias-e-consultas-publicas/documentos-1/nt-ts-1_2023_0046035.pdf/@@display-file/file

**Outros pontos do guia:**
- O controlador deve conseguir demonstrar que o tratamento é razoavelmente esperado pelo titular naquele contexto, e deve oferecer canal de fácil acesso para o exercício de direitos (COMUNIDADE: Mattos Filho, resumindo o guia) [TB].
- Marketing direto citado como operação típica e de baixo risco sob legítimo interesse: só por escritório (COMUNIDADE: https://www.bmalaw.com.br/conteudo/direito-digital-protecao-de-dados-e-cybersecurity/artigos-e-noticias/o-legitimo-interesse-na-visao-da-anpd/pdf). Exemplo literal no guia [NV].
- Legítimo interesse não serve para dado sensível (COMUNIDADE) [TB].

**Prospecção B2B especificamente:**
- Nenhuma manifestação da ANPD foi encontrada [NV].
- COMUNIDADE e FORNECEDOR:
  - Escritório: "ainda seja cedo para afirmar como as campanhas de e-mail marketing serão interpretadas pela ANPD ou mesmo pelo Poder Judiciário". URL: https://www.bmalaw.com.br/conteudo/direito-digital-protecao-de-dados-e-cybersecurity/artigos-e-noticias/lgpd-e-oito-dicas-juridicas-para-campanhas-de-e-mail-marketing/pdf
  - Snov.io (FORNECEDOR) declara usar legítimo interesse para prospects: https://snov.io/knowledgebase/br/perguntas-frequentes-sobre-lgpd-para-usuarios-e-clientes-snov-io/
  - Blog de CRM (FORNECEDOR) afirma, sem base normativa, que não se pode abordar lead "que não liberou seus dados": https://www.agendor.com.br/blog/mailing-b2b/

**Checklist operacional** (síntese nossa a partir dos dispositivos acima; não é orientação oficial):
1. LIA escrita e datada para a finalidade "prospecção comercial de câmbio para empresas", nas três fases do guia.
2. Dados mínimos: nome, cargo, empresa e e-mail corporativo (art. 10, §1º). Evitar e-mails pessoais (gmail.com etc.), onde a expectativa do titular é menor.
3. Origem de cada contato registrada (fonte, data, base legal), dentro do registro de operações do art. 37.
4. Transparência já no 1º e-mail (art. 10, §2º): quem é a empresa, por que o contato e de onde veio o dado (art. 19 [NV]), link para o aviso de privacidade e canal do encarregado.
5. Opção de sair em todo e-mail: cabeçalho one-click e link no corpo. Lista de supressão permanente, honrada em ≤ 48 h, o prazo do Gmail, mais rígido que o do Yahoo. É o caminho operacional para o direito de oposição (art. 18, §2º).
6. Revisão periódica da LIA. A ANPD pode pedir RIPD (art. 10, §3º).

### CAPEM: Código de Autorregulamentação para a Prática de E-mail Marketing (COMUNIDADE, autorregulação)

**Status e fontes:**
- Em vigor desde 13/08/2009, segundo a imprensa da época. Iniciativa de 14 entidades, entre elas a ABEMD.
- **Voluntário e não vinculante** (EmailOctopus).
- Previa Conselho de Ética com medidas educativas e, em último caso, punitivas.
- capem.org.br estava bloqueado, então a situação atual do código é [NV].
- URLs:
  - https://www.contadores.cnt.br/projetos/50/noticias/tecnicas/2009/08/12/autorregulamentacao-de-e-mail-marketing-entra-em-vigor.html
  - https://www.baguete.com.br/noticias/e-mail-marketing-regulamentacao-e-oficial
  - https://emailoctopus.com/blog/email-marketing-regulations-brazil

**Regras relevantes [TB]:**
- Opt-in ou soft opt-in. Sem permissão, só com relacionamento prévio e opção de descadastro.
- **Proíbe "o primeiro envio para se obter a permissão do destinatário para envios posteriores"**, o que colide frontalmente com o e-mail frio clássico.
- Remetente com endereço no **próprio domínio**. Serviços de e-mail gratuitos não são permitidos.
- Descadastro: [CONFLITO] uma fonte diz 2 dias via link e 5 dias úteis por outros meios; outra diz "até dois dias úteis".

**Relevância:** baixa do ponto de vista jurídico, porque não é lei. Ainda assim é referência ética que pode ser citada contra a empresa. O prazo de 2 dias coincide com Yahoo e Gmail.

### CDC: art. 43 (Lei 8.078/1990)

**Texto do §2º** [TB, via fontes secundárias, porque planalto.gov.br estava bloqueado]: "A abertura de cadastro, ficha, registro e dados pessoais e de consumo deverá ser comunicada por escrito ao consumidor, quando não solicitada por ele."
- https://www.dizerodireito.com.br/2023/06/antes-do-consumidor-ser-inscrito-nos.html
- https://modeloinicial.com.br/lei/CDC/codigo-defesa-consumidor/art-43

**Aplicação além de cadastro de crédito:**
- O MPMG (2024) aplicou o art. 43, §2º, junto com o Decreto 2.181/97, art. 13, XIII, a uma empresa de varejo que abriu cadastro de clientes sem comunicação prévia [TB]. URL: https://mpmg.mp.br/data/files/8F/23/8A/1C/C457091017A50CF8760849A8/Dec%20Adm_CDC_Abertura%20de%20cadastro%20de%20dados%20pessoais%20e%20de%20consumo_%20sem%20previa%20informacao%20ao%20consumidor_Track%20_%20Field%20Co%20S.A_14%20PJ%20BH_20mai2024.pdf
- [CONFLITO] Sobre a forma da comunicação (carta ou meio eletrônico): o buscador não trouxe o desfecho do repetitivo do STJ.

**Se aplica a e-mail frio B2B? Não confirmado [NV]. Análise:**
- O CDC protege o "consumidor". Pela jurisprudência, pessoa jurídica é consumidora quando é destinatária final ou vulnerável, num finalismo mitigado. O STJ, no REsp 476.428/SC, admite abrandar o critério (COMUNIDADE: https://www.aurum.com.br/blog/cdc-comentado/art-29-cdc/) [TB].
- O art. 29 equipara a consumidor "todas as pessoas determináveis ou não, expostas às práticas" dos Capítulos V e VI [TB].
- O art. 43 fica no Capítulo V (Das Práticas Comerciais). A localização é [NV] nesta pesquisa: a página da legjur sobre o Capítulo V apareceu nos resultados, mas sem conteúdo.
- Conclusão: para câmbio a empresas que usam o serviço como insumo, o CDC tende a não se aplicar. O risco não é zero (equiparação do art. 29, PJ vulnerável). A mitigação é a mesma da LGPD: informar no 1º contato que o dado foi registrado e de onde veio. Isso atende a LGPD (transparência) e reduz o risco no art. 43, §2º.

---

## (e) BIMI

| Requisito | Conteúdo | Natureza / Verificação | URL |
|---|---|---|---|
| DMARC em enforcement | Google: "p" deve ser **quarantine ou reject**. "BIMI doesn't support DMARC policies that have the p option set to none". **pct=100** | OFICIAL [TB] | https://support.google.com/a/answer/10911320?hl=en |
| DMARC (padrão) | Rascunho IETF: quarantine com percentual efetivo de 100%, ou reject com qualquer pct. A política precisa estar em enforcement também nos subdomínios. Ainda é **rascunho** (draft-14) | OFICIAL, IETF draft [TB] | https://datatracker.ietf.org/doc/html/draft-brand-indicators-for-message-identification-14 |
| Certificado | Gmail exige **VMC** (Verified Mark Certificate, para marca registrada) ou **CMC** (Common Mark Certificate, para marca de uso anterior ou modificação de marca registrada). Logo sem registro pode usar CMC | OFICIAL [TB] | https://support.google.com/a/answer/10911320?hl=en · https://bimigroup.org/verified-mark-certificates-vmc-and-bimi/ |
| Logo | SVG Tiny PS, no mínimo 96×96 px em pixels absolutos, ≤ 32 KB. O Gmail não aceita SVG avulso, só o PEM do certificado | OFICIAL [TB] | https://support.google.com/a/answer/10911320?hl=en |
| Yahoo / outros | Página antiga do BIMI Group diz que Yahoo e AOL aceitam BIMI autodeclarado (sem certificado). Pode estar desatualizado | COMUNIDADE (grupo do padrão) [TB, possivelmente desatualizado] | https://bimigroup.org/implementation-guide/ |
| Apple Mail | Não verificado | [NV] | n/a |
| Custo do VMC/CMC | Não verificado | [NV] | n/a |

**Implicação (análise):**
- BIMI exige subir o DMARC do domínio frio para quarantine/reject com pct=100 e obter certificado, o que pede marca registrada ou uso anterior.
- Não é requisito de entrega. Para domínio de prospecção, o ganho é cosmético. Avaliar só depois que o domínio estiver estável.
- Subir o DMARC do domínio frio para quarantine ou reject é recomendável por si só, depois de 2 a 4 semanas de relatórios `rua` limpos [NV como prazo; prática de mercado].

---

## (f) Domínios bloqueados pela rede

1. **WebFetch:** falhou com `getaddrinfo ENOTFOUND` (o DNS não resolve dentro da ferramenta) em `support.google.com`, `senders.yahooinc.com` e `www.planalto.gov.br`. Como falhou em todos, parei de tentar.
2. **curl via proxy:** `CONNECT tunnel failed, response 403` (`connect_rejected` por política) em:
   - `support.google.com`
   - `senders.yahooinc.com`
   - `techcommunity.microsoft.com`
   - `learn.microsoft.com`
   - `www.gov.br`
   - `www.planalto.gov.br`
   - `www.rfc-editor.org`
   - `datatracker.ietf.org`
   - `www.ietf.org`
   - `bimigroup.org`
   - `blog.google`
   - `workspaceupdates.googleblog.com`
   - `postmaster.google.com`
   - `developers.google.com`
   - `knowledge.workspace.google.com`
   - `sendersupport.olc.protection.outlook.com`
   - `www.capem.org.br`
   - `web.archive.org`
   - `www.google.com`
   - `en.wikipedia.org`
3. **Acessíveis:** só `api.github.com` (200) e `github.com` (400 na raiz), que são irrelevantes aqui.

---

## (g) Buscas usadas (WebSearch, modo "standard")

**Teto estourado:** fiz **27 buscas**, uma acima do teto de 26, por erro de contagem.

1. Gmail email sender guidelines requirements all senders 5,000 messages SPF DKIM DMARC one-click unsubscribe spam rate 0.3% (support.google.com)
2. Gmail November 2025 non-compliant traffic rejections enforcement bulk senders temporary permanent errors (domínios Google)
3. Yahoo sender requirements best practices bulk senders DMARC one-click unsubscribe honor 2 days spam rate 0.3% (yahooinc.com)
4. Outlook.com new requirements high-volume senders 5,000 emails per day SPF DKIM DMARC May 5 2025 550 5.7.515 rejection (microsoft.com)
5. Microsoft Outlook high-volume senders update "reject" instead of junk May 2025 compliant P2 sender address functional unsubscribe list hygiene
6. "Strengthening Email Ecosystem" Outlook high-volume senders update junk folder rejected "5.7.515" techcommunity (microsoft.com)
7. Gmail sender guidelines "valid forward and reverse DNS" PTR TLS "RFC 5322" "0.10%" spam rate "within 48 hours" unsubscribe (support.google.com)
8. Gmail sender guidelines increase sending volume slowly new domain "ramp up" warm up IP domain Postmaster (Google)
9. Gmail email sender guidelines content "URL shorteners" links hidden content "mix" personal and promotional same domain HTML formatting standards (support.google.com)
10. cold email deliverability disable open tracking pixel link tracking custom tracking domain URL shorteners attachments images plain text spam trigger words myth
11. "spam trigger words" myth deliverability filters reputation engagement not words
12. new domain mailbox warm-up schedule cold email emails per day week 1 week 2 week 3 week 4 max 30-50 per inbox
13. Yahoo sender best practices new IP new domain ramp up volume gradually warm Microsoft Outlook.com postmaster policies practices guidelines (Yahoo/Microsoft)
14. ANPD Guia Orientativo Hipóteses legais de tratamento de dados pessoais Legítimo Interesse fevereiro 2024 teste de balanceamento (gov.br)
15. Lei 13.709 art. 10 "O legítimo interesse do controlador somente poderá fundamentar…" art. 7º IX (planalto.gov.br)
16. LGPD art. 37 "especialmente quando baseado no legítimo interesse" art. 18 § 2º "opor-se a tratamento" art. 19 "indique a origem dos dados" art. 7º § 3º § 4º manifestamente públicos (gov.br)
17. guia legítimo interesse ANPD exemplo marketing direto envio de e-mail publicidade legítimas expectativas titular opt-out prospecção B2B
18. CAPEM Código de Autorregulamentação para Prática de E-mail Marketing opt-in opt-out regras Abemd
19. CDC Lei 8.078 art. 43 § 2º "abertura de cadastro, ficha, registro e dados pessoais e de consumo deverá ser comunicada por escrito ao consumidor"
20. BIMI requirements DMARC p=quarantine or p=reject pct=100 Verified Mark Certificate Common Mark Certificate Gmail Yahoo Apple Mail SVG Tiny PS
21. RFC 8058 "List-Unsubscribe-Post: List-Unsubscribe=One-Click" HTTPS POST DKIM signature must cover headers (rfc-editor/ietf)
22. Gmail sender guidelines FAQ "June 1, 2024" one-click unsubscribe bulk senders deadline timeline April 2024 DMARC (Google)
23. Gmail sending limits in Google Workspace messages per day 2,000 trial accounts 500 recipients per message (Google)
24. Instantly OR Smartlead OR lemlist warmup new mailbox "per day" increase daily limit 2 weeks before cold campaign recommended sending limit per inbox
25. Yahoo sender requirements DKIM key length 1024 2048 TLS bulk senders February 2024 one-click unsubscribe June 2024 senders.yahooinc.com FAQ
26. e-mail corporativo nominal é dado pessoal LGPD prospecção B2B legítimo interesse dado de contato profissional pessoa jurídica ANPD
27. CDC art. 29 "equiparam-se aos consumidores todas as pessoas determináveis ou não, expostas às práticas" bancos de dados cadastros art. 43 pessoa jurídica B2B

**Lacunas para uma próxima rodada**, com a rede liberada para support.google.com, senders.yahooinc.com, techcommunity.microsoft.com, gov.br e planalto.gov.br:
- Ler as páginas integrais.
- Confirmar a data de início das rejeições da Microsoft.
- Confirmar TLS e limiar de volume no Yahoo.
- Confirmar os arts. 5º, 9º e 19 da LGPD.
- Achar exemplos de marketing no Guia da ANPD.
- Saber a situação atual do CAPEM.
- Levantar as regras de filtragem do Microsoft 365 corporativo (EOP), que são as mais relevantes para destinatários B2B.
