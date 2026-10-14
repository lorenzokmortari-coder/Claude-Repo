# Olami SP: inscrição de eventos com Luma, Tally ou Sympla, e a LGPD

**Pesquisa feita em 14/10/2026.** Para quem: centro comunitário judaico jovem em São Paulo, público de 20 a 35 anos, eventos semanais gratuitos (jantar de Shabbat, aulas, festas). Hoje a inscrição é pelo Google Forms.
Arquivos: `pesquisa.md` (este) e `fontes.csv` (cada afirmação com fonte e grau de verificação).

## Como ler esta pesquisa

- O WebFetch não funciona neste ambiente, então **nenhuma página foi lida por inteiro**. Tudo vem dos trechos e do resumo que o WebSearch devolve.
- Selos usados em cada afirmação:
  - **[trecho]**: o texto da fonte aparece citado no resultado da busca.
  - **[resumo]**: a afirmação aparece só no resumo da busca, e o trecho literal não veio junto.
  - **[NV]**: não verificado. Não encontrei a informação, as fontes se contradizem, ou a conclusão é uma inferência minha.
- Todas as fontes foram vistas em **14/10/2026**.
- A cota de buscas acabou no fim do trabalho. Dois pontos da LGPD ficaram sem conferência literal no planalto.gov.br (veja a seção f).
- Isto não é parecer jurídico. O texto de consentimento precisa passar por um advogado antes de ir ao ar.

---

## (a) Luma: o que o plano grátis faz

### 1. Inscrição com aprovação: **SIM**

- A opção "Require Approval" fica no **tipo de ingresso**: Manage Event > Registration > clicar no ingresso. **[trecho]**
- Quem se inscreve fica "Pending". O anfitrião aprova ou recusa pela lista de convidados (aba Guests na web; Manage > Guests no app), vendo as respostas de cada pessoa. **[resumo]**
- **Atenção:** convite enviado pelo anfitrião **pula a aprovação**. Quem se inscreve por convite entra aprovado. **[trecho]**
- Funciona com ingresso grátis, e a página de preços lista a aprovação entre os recursos do plano grátis. **[resumo]**
- Útil para a segurança da Olami: com "Restrict Location to Guests", quem não foi aprovado vê só a cidade e a área aproximada. O endereço completo aparece só para anfitriões e convidados aprovados. **[trecho]** A página não diz se o recurso é do grátis ou do Plus. **[NV]**
- A lista de espera funciona **só em eventos gratuitos**: você define a capacidade, liga "Over-Capacity Waitlist" e aprova ou recusa quem está na lista. **[resumo]**
- Fontes (vistas em 14/10/2026): [Setting Up Ticket Types](https://help.luma.com/p/setting-up-ticket-types) · [Managing Your Guest List](https://help.luma.com/p/managing-your-guest-list) · [Inviting and Adding Guests](https://help.luma.com/p/inviting-and-adding-guests-to-your-event) · [Payment + Require Approval](https://help.luma.com/p/payment-require-approval) · [Pricing · Luma](https://luma.com/pricing) · [Luma vs Eventbrite](https://help.luma.com/p/luma-vs-eventbrite) · [Hiding Your Event Location](https://help.luma.com/p/hiding-your-event-location) · [Waitlist](https://help.luma.com/p/waitlist)

### 2. Lembrete por WhatsApp para número do Brasil: **PROVÁVEL, mas não confirmado para o Brasil [NV]**

- **Regra da Luma.** O canal depende do país do número: "We use SMS for some countries and WhatsApp for other countries. You will see either SMS or WhatsApp based on your country." **[trecho]**
- **Lista de países com SMS** (segundo o resumo): EUA, Canadá, Austrália, Nova Zelândia, Japão, China e Ilhas Cayman. "A maioria dos outros países" recebe por WhatsApp, e a lista pode mudar. **[resumo]**
- **Brasil.** O país não aparece nominalmente em nenhum trecho. Pela regra acima, um número +55 receberia por **WhatsApp**, mas isso é inferência. **[NV]** Para ter certeza, inscreva o celular de alguém da equipe num evento de teste.
- **O convidado precisa ter telefone vinculado**: "If they've linked a phone number, they'll also get an SMS or WhatsApp message" (frase sobre convites). **[trecho]** Para blasts, o resumo diz o mesmo. **[resumo]** O resumo também diz que o anfitrião pode ativar a coleta de telefone na inscrição. **[resumo]**
- **Quem escolhe o canal é o convidado**, nas preferências da conta. O anfitrião não pode mudar essas preferências. **[resumo]**
- **Está no plano grátis: SIM.** A página de preços lista no grátis "Blasts and automated reminders via email, SMS, push notification and WhatsApp". **[trecho]**
- **Quando chegam.** Lembretes automáticos 1 dia e 1 hora antes, e o anfitrião não edita o texto (mensagens próprias saem como "Event Blast"). **[resumo]** A fonte é um post de 17/09/2024 que cita e-mail, SMS e push, mas não WhatsApp, então pode estar desatualizada.
- **Se o WhatsApp não chegar:** atualizar o app, aceitar os novos termos do WhatsApp e checar a configuração de remetentes desconhecidos. Quem respondeu STOP precisa reativar. **[resumo]**
- Fontes (vistas em 14/10/2026): [Notification Types](https://help.luma.com/p/notification-types) · [SMS / WhatsApp Messages](https://help.luma.com/p/sms-whatsapp-messages) · [Inviting and Adding Guests](https://help.luma.com/p/inviting-and-adding-guests-to-your-event) · [Disabling or Enabling Notifications and Reminders](https://help.luma.com/p/disabling-or-enabling-notifications-and-reminders) · [Sending or Scheduling Event Blasts](https://help.luma.com/p/sending-or-scheduling-event-blasts) · [Pricing · Luma](https://luma.com/pricing) · [Update to Reminders on Luma](https://help.luma.com/p/update-to-reminders-on-luma) · [Collect Registration Questions](https://help.luma.com/p/collect-registration-questions)

### 3. Check-in por QR code: **SIM**

- **Como funciona.** Cada inscrito recebe um QR por e-mail, na página do evento, no app e na carteira Apple/Google. O anfitrião abre o leitor da própria Luma; a câmera comum do celular não faz check-in. Ao ler o código, abre a ficha da pessoa e o anfitrião confirma com um toque. Também dá para buscar por nome ou e-mail. **[resumo]**
- **Onde funciona.** No app iOS e Android. Um resumo cita também a web, mas outra busca não achou página sobre leitor na web. **[resumo]**
- **Está no grátis?** Sim. Os comparativos da própria Luma marcam o check-in por QR como recurso da Luma, e a ajuda só aponta como pago o papel "só check-in" (abaixo). **[resumo]**
- **Quem faz check-in no grátis:** anfitriões com acesso de **Manager** ao evento. **[resumo]** Os admins do calendário (até 3 no grátis) provavelmente também podem, mas isso não foi confirmado. **[NV]**
- **Papel "só check-in" exige Luma Plus.** Esse papel lê QR e vê a lista, mas não baixa a lista nem edita o evento. Trecho: "Check-in staff requires Luma Plus." **[trecho]**
- **Quantas pessoas ou aparelhos ao mesmo tempo:** nenhum limite encontrado. **[NV]**
- **Ponto de LGPD:** quem faz check-in vê a lista completa, com contatos, e não há como esconder campos. **[resumo]**
- Fontes (vistas em 14/10/2026): [Check In Guests for In-Person Events](https://help.luma.com/p/check-in) · [Luma iOS App](https://help.luma.com/p/luma-ios-app) · [Adding Hosts and Managers to Your Event](https://help.luma.com/p/adding-hosts-and-managers-to-your-event) · [Luma Plus Overview](https://help.luma.com/p/luma-plus)

### 4. Exportação de quem se inscreveu e de quem veio: **SIM, CSV com status de check-in**

- **Como baixar.** Manage > Guests > Download CSV, com as opções "Download All Guests" e "Download Filtered Guests". **[resumo]**
- **O que vem no CSV.** Status de check-in (evento presencial) e a URL do QR. Quem tem vários ingressos aparece uma vez por ingresso. **[resumo]**
- **Não existe ligação automática com planilha no grátis.** Zapier e API são do Plus (preços da Luma e página da Metabase, que é terceiro). **[resumo]**
- Fontes (vistas em 14/10/2026): [Download Guest List as CSV](https://help.luma.com/p/download-guest-csv) · [Pricing · Luma](https://luma.com/pricing) · [Metabase × Luma (terceiro)](https://www.metabase.com/integrations/luma)

### 5. Limites do grátis e o que só o Luma Plus tem

| Item | Grátis | Luma Plus | Verificação |
|---|---|---|---|
| Eventos e convidados | ilimitados | ilimitados | [resumo] |
| Convites/newsletters para quem ainda não se inscreveu | 500 por semana **com o calendário verificado** (sem verificação: [NV]) | 5.000 por semana, com pacotes extras | [trecho] |
| Mensagens para quem já se inscreveu | ilimitadas | ilimitadas | [trecho] |
| Admins do calendário | até 3 | 5 incluídos (assento extra US$ 9/mês no plano anual) | [trecho]; os US$ 9 só no [resumo] |
| Taxa sobre ingresso **pago** (não se aplica a evento grátis) | 5% + taxa da Stripe | 0% + taxa da Stripe | 5%: [trecho]; 0%: [resumo] |
| Papel "só check-in" | não | sim | [trecho] |
| Perguntas personalizadas no formulário | sim, sem marcação de recurso pago | idem, mais a opção de separar "Nome" e "Sobrenome" | no grátis: [NV], é inferência porque a ajuda não as marca como pagas; nome e sobrenome no Plus: [trecho], com versões da página em conflito |
| Lógica condicional nas perguntas | não existe | não existe | [resumo] |
| Zapier, API, URL personalizada, cobrança de impostos, suporte prioritário | não | sim | [resumo] |
| **Preço** | US$ 0 | **US$ 59/mês no plano anual ou US$ 69/mês no mensal**, por calendário | [resumo] |

- **Detalhes das perguntas.** Tipos de pergunta: Texto, Opções, Perfil social, Empresa, Checkbox, Termos e Site. **[resumo]** O anfitrião escolhe se cada pergunta é obrigatória ("You can control the number of questions and if they are required or not"). **[trecho]** Nome e e-mail não podem ser desligados. **[resumo]**
- **Pergunta "Termos".** Aceita texto ou link e assinatura digital opcional, o que serve para o consentimento LGPD. **[resumo]**
- **Os envios.** O contador zera toda segunda às 00:00 UTC. **[trecho]** O Plus vale por calendário, não por conta. **[trecho]**
- Fontes (vistas em 14/10/2026): [Send Limits](https://help.luma.com/p/understanding-import-and-event-invite-limits) · [Luma Plus Overview](https://help.luma.com/p/luma-plus) · [Pricing · Luma](https://luma.com/pricing) · [Luma vs Meetup](https://help.luma.com/p/luma-vs-meetup) · [Collect Registration Questions](https://help.luma.com/p/collect-registration-questions) · [Collect Registration Questions (cópia help.lu.ma)](https://help.lu.ma/p/collect-registration-questions) · [Event Terms](https://help.luma.com/p/event-terms) · [Check In Guests](https://help.luma.com/p/check-in)

### 6. Onde ficam os dados e o que a Luma diz sobre privacidade

- **Segurança declarada.** A Luma usa a AWS ("global availability"). **[trecho]** Usa cláusulas contratuais padrão para transferências e diz "Data Processing Agreements: Available for enterprise customers at luma.com/dpa". **[trecho]** Criptografia AES-256 em repouso e TLS 1.2+. **[trecho]** Tem relatório SOC 2 Type II. **[resumo]**
- **Residência dos dados.** A Luma **não oferece escolha de onde os dados ficam**. **[resumo]** Em que país ficam: **[NV]**, não apareceu em nenhum trecho.
- **Política de privacidade.** Ao se inscrever, os dados do convidado vão para o anfitrião, e os dados de pagamento vão para a Stripe. **[resumo]**
- **Empresa responsável.** O resumo da busca cita "Luma Labs, Inc."; sede e país: **[NV]**. Também não sei se a Luma age só como operadora ou também como controladora dos dados da conta do convidado. **[NV]**
- **Idioma.** A Luma tem português do Brasil. **[resumo]**
- Fontes (vistas em 14/10/2026): [Enterprise Security](https://help.luma.com/p/enterprise-security) · [Security · Luma](https://luma.com/security) · [Data Processing Addendum · Luma](https://luma.com/dpa) · [Privacy Policy · Luma](https://luma.com/privacy-policy) · [Privacy Policy (luma.com/privacy)](https://luma.com/privacy) · [Languages](https://help.luma.com/p/languages)

---

## (b) Tally

### O que o plano grátis cobre (fontes vistas em 14/10/2026)

| Pergunta | Resposta | Verificação | Fonte |
|---|---|---|---|
| Formulários e respostas ilimitados? | **Sim**, "subject to our fair use guidelines" | [trecho] | [Tally vs Typeform](https://tally.so/help/tally-a-free-typeform-alternative), [Pricing](https://www.tally.so/pricing) |
| Lógica condicional? | **Sim**, grátis e sem limite de condições | [resumo] | [Conditional logic](https://tally.so/help/conditional-form-logic) |
| Campo obrigatório? Checkbox obrigatório? | Os blocos de entrada têm a opção "required" (atalho Cmd/Ctrl+Shift+R; o bloco de telefone tem o botão Required). Para o **checkbox** em si: não confirmado | [resumo]; checkbox: [NV] | [Keyboard shortcuts](https://tally.so/help/keyboard-shortcuts), [Phone number](https://tally.so/help/phone-number) |
| Como fazer o consentimento? | A Tally orienta caixa **desmarcada** e várias caixas quando há várias finalidades | [trecho] | [GDPR compliant form](https://tally.so/help/how-to-create-a-gdpr-compliant-form) |
| Integração com Google Sheets? | **Sim, grátis.** Cria uma linha por envio e, ao conectar, traz as respostas antigas | grátis: [resumo]; funcionamento: [trecho] | [Google Sheets Integration](https://tally.so/help/google-sheets-integration) |
| Campos ocultos (para saber o evento pelo link)? | **Sim**, grátis | [trecho] | [Hidden fields](https://tally.so/help/hidden-fields) |
| Fechar o formulário por limite de respostas ou por data? | **Sim**, grátis | [trecho] | [Pricing](https://www.tally.so/pricing) |
| Aviso por e-mail para a equipe? | **Sim**, grátis | [trecho] | [Self email notifications](https://tally.so/help/self-email-notifications) |
| E-mail de confirmação para quem se inscreve? | **Não. É recurso Pro** | [trecho] | [Respondent email notifications](https://tally.so/help/respondent-email-notifications) |
| Apagar respostas automaticamente depois de X dias? | Não. É recurso do plano Business. O que se apaga sai dos backups em até 90 dias | [resumo] | [GDPR](https://tally.so/help/gdpr) |
| **Onde ficam os dados (UE?)** | **Sim, na UE.** "stored in Europe" e "all form and user data is stored in Belgium, EU", **mas** "can be processed in countries outside of the EU by third parties" (política de 20/11/2023) | [trecho] | [GDPR](https://tally.so/help/gdpr), [Privacy](https://tally.so/privacy) |
| Papéis | Quem cria o formulário é o controlador; a Tally é a operadora. Há DPA | [trecho] | [GDPR](https://tally.so/help/gdpr), [DPA](https://tally.so/help/data-processing-agreement) |
| Preço do Pro, se um dia precisar | US$ 29/mês (páginas da Tally) contra US$ 24/mês (terceiro que cita a página de preços). As fontes se contradizem | [NV] | [Formbricks (terceiro)](https://formbricks.com/blog/tally-pricing) |
| Marca "Made with Tally" no grátis | Sim, segundo terceiros | [resumo] | [Jetadmin (terceiro)](https://www.jetadmin.io/blog/tally-review/) |

A Tally é um construtor de formulários. Não achei na documentação aprovação de inscritos, check-in por QR nem lembretes para quem se inscreveu **[NV]**. Ela serve para coletar dados, e as respostas vão para a planilha.

### Modelo de formulário de inscrição (Tally)

Princípio: pedir só o mínimo necessário (LGPD, art. 6º, III). Use **um formulário para todos os eventos**, com um campo oculto que vem no link (ex.: `?evento=shabbat-17-10`). Assim ninguém precisa escolher o evento.

| # | Campo (como aparece) | Tipo no Tally | Obrigatório | Por que existe |
|---|---|---|---|---|
| 1 | `evento` (não aparece) | Hidden fields | não (vem no link) | Saber o evento da inscrição sem perguntar |
| 2 | Nome e sobrenome | Short answer (resposta curta) | **Sim** | Achar a pessoa na lista e no check-in |
| 3 | E-mail | Email | **Sim** | Confirmar a inscrição e falar do evento |
| 4 | Celular com WhatsApp | Phone number (padrão +55) | **Sim** | Avisos do evento (endereço, horário, cancelamento). Só é usado para convites se a pessoa marcar o campo 9 |
| 5 | "Tenho 18 anos ou mais" | Checkbox | **Sim** | O público é adulto; evita pedir data de nascimento |
| 6 | "Quero informar uma restrição alimentar" | Checkbox | Não | Só em eventos com comida. Pela lógica condicional, abre o campo 7 |
| 7 | Restrição: Vegetariana / Vegana / Sem glúten / Sem lactose / Alergia / Outra, mais "Qual?" | Checkboxes + Short answer (aparece só se o 6 for marcado) | Não | Planejar a comida. Alergia é dado de saúde, que também é sensível. Apagar até 30 dias depois do evento. **Não ofereça "kosher" se a comida já é toda kosher**: seria coletar dado sensível sem necessidade |
| 8 | Aviso de privacidade + caixa de consentimento (texto abaixo) | Text (bloco de texto) + Checkbox | **Sim** | Consentimento específico e destacado para dado sensível (art. 11, I) |
| 9 | "Quero receber convites da Olami por:" WhatsApp / E-mail | Checkboxes (2 opções, ambas desmarcadas) | Não | Consentimento separado e opcional para divulgação (art. 8º, § 4º) |

**O que não perguntar, de propósito:** religião ou "você é judeu?", sinagoga ou movimento, CPF/RG, data de nascimento, endereço, gênero, Instagram, "como soube do evento". Nada disso é necessário para inscrever e fazer o check-in (art. 6º, III), e religião é dado sensível (art. 5º, II).

**Configuração:** feche o formulário pela capacidade ou pela data. Ligue a uma planilha Google com acesso só da equipe do evento. Lembre que o e-mail de confirmação ao inscrito é Pro: a confirmação sai manualmente pelo WhatsApp ou fica com a Luma. Os nomes dos blocos devem ser conferidos no editor **[NV]**.

**A mesma coisa na Luma** (se a inscrição for pela Luma): nome e e-mail já vêm por padrão; ligar a coleta de telefone **[resumo]**; perguntas "18+" (Checkbox, obrigatória), "Restrição alimentar" (Texto, opcional, sem lógica condicional), "Consentimento LGPD" (Termos, obrigatória) e "Convites por WhatsApp/e-mail" (Checkbox, opcional).

### Texto de consentimento LGPD (pronto para colar e completar)

Lei: [Lei nº 13.709/2018, texto compilado no planalto.gov.br](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm) · [texto original](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm). Os artigos estão conferidos na tabela logo abaixo do texto.

> **Aviso de privacidade: inscrição em eventos da Olami**
>
> **Quem cuida dos seus dados (controlador):** [nome da associação], CNPJ [00.000.000/0000-00], [endereço].
>
> **Por que pedimos um consentimento especial:** a Olami é um centro comunitário judaico. Por isso, o simples fato de você se inscrever pode indicar sua convicção religiosa ou sua ligação com uma organização de caráter religioso, e a lei trata isso como **dado pessoal sensível** (LGPD, art. 5º, II, e art. 11, § 1º). **Nós não perguntamos sua religião.** Só tratamos esses dados com o seu consentimento **específico e destacado** (art. 11, I).
>
> **Quais dados:** nome e sobrenome, e-mail, celular, o evento escolhido, sua presença (check-in) e, só se você quiser, uma restrição alimentar.
>
> **Para que usamos, e só para isso:**
> 1. registrar e confirmar sua inscrição e, quando as vagas forem limitadas, aprovar sua vaga;
> 2. mandar informações práticas do evento em que você se inscreveu (confirmação, endereço, horário, mudanças e lembretes);
> 3. controlar a entrada no dia (check-in), pela segurança de todos;
> 4. se você informar, preparar a comida levando em conta sua restrição alimentar;
> 5. contar a participação nos eventos em números gerais, sem identificar ninguém.
>
> Não vendemos seus dados e não os usamos para nenhuma outra finalidade (art. 6º, I e III; art. 8º, § 4º).
>
> **Base legal:** o seu consentimento (art. 7º, I, e art. 11, I). Você pode retirá-lo quando quiser, de graça e de forma simples (art. 8º, § 5º).
>
> **Por quanto tempo guardamos:** inscrição e presença, até [12] meses depois do evento; depois apagamos ou guardamos só números, sem nomes. Restrição alimentar, apagada até [30] dias depois do evento. Contato para convites (se você marcar a caixa opcional), até você pedir para sair (arts. 15 e 16).
>
> **Com quem compartilhamos:** só com as empresas que fazem a inscrição funcionar, em nosso nome e seguindo nossas instruções (operadores, art. 5º, VII): **Tally** (formulário; diz guardar os dados na União Europeia), **Luma** (plataforma de eventos, lembretes e check-in; empresa estrangeira, então seus dados podem ficar fora do Brasil, em [país a confirmar]) e [**Google**, se usarmos Planilhas Google]. Isso é uma **transferência internacional de dados** (art. 33). A ANPD reconheceu a União Europeia como tendo proteção adequada (Resolução CD/ANPD nº 32/2026). Para os outros países, a transferência se apoia no seu consentimento específico e em destaque (art. 33, VIII). A Luma também tem a própria política de privacidade para o uso da plataforma. A lista de inscritos só é vista pela equipe da Olami que organiza o evento.
>
> **Seus direitos (art. 18):** confirmar se tratamos seus dados; acessar seus dados; corrigir; pedir anonimização, bloqueio ou eliminação do que for desnecessário; portabilidade; eliminação dos dados tratados com seu consentimento; saber com quem compartilhamos; saber que você pode não consentir e o que acontece se não consentir; revogar o consentimento; e reclamar à ANPD (art. 18, § 1º). Se você não consentir, não conseguimos fazer a inscrição por este formulário. Fale com [contato] e vemos outra forma de você participar.
>
> **Encarregado (DPO) e canal de contato:** [nome do encarregado], [e-mail do encarregado] (art. 41). Pedido de acesso completo é respondido em até 15 dias (art. 19).
>
> **[ ] (obrigatória, em destaque) Li o aviso acima e autorizo a [nome da associação] a tratar meus dados de inscrição, sabendo que eles podem revelar minha ligação com uma organização judaica (dado sensível), somente para as finalidades 1 a 5 acima, inclusive a transferência internacional para Tally e Luma descrita no aviso.**

Caixa **separada, opcional e desmarcada** (campo 9):

> [ ] Quero receber convites e novidades da Olami por [ ] WhatsApp [ ] E-mail. Sei que isso também mostra minha ligação com a Olami e que posso sair quando quiser, respondendo "SAIR" ou escrevendo para [contato].

Guarde a prova do consentimento: a resposta do formulário, com data e hora, fica na Tally e na planilha. Quem tem de provar que o consentimento foi dado é a Olami (art. 8º, § 2º).

Adapte a lista de operadores ao que for usado de fato (só Luma, só Tally ou as duas, e o Google se houver planilha). Na Luma, cole o aviso numa pergunta "Termos" obrigatória e a caixa de convites numa pergunta Checkbox opcional.

**Artigos citados e o que foi conferido** (links acima; fontes vistas em 14/10/2026)

| Dispositivo | O que diz | Verificação |
|---|---|---|
| Art. 5º, II | Dado sensível inclui "convicção religiosa" e "filiação a [...] organização de caráter religioso" | [trecho] (planalto) |
| Art. 5º, VI e VII | Controlador decide; operador trata em nome do controlador | [trecho] (planalto) |
| Art. 5º, VIII | Encarregado. Nova redação dada pela Lei 15.352/2026: "indicada pelo controlador e operador" | [trecho] ([Lei 15.352/2026, planalto](https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2026/lei/l15352.htm) · [Câmara](https://www2.camara.leg.br/legin/fed/lei/2026/lei-15352-25-fevereiro-2026-798731-publicacaooriginal-178208-pl.html)) |
| Art. 5º, XII | Consentimento é "livre, informada e inequívoca [...] para uma finalidade determinada" | [trecho] (planalto) |
| Art. 6º, III | Necessidade: só o mínimo necessário | [resumo] (planalto) |
| Art. 7º, I | Consentimento como base legal | [trecho] (planalto) |
| Art. 8º, § 1º | Consentimento escrito em cláusula destacada | [resumo], **só em fontes de terceiros** ([Gran Cursos](https://blog.grancursosonline.com.br/lei-13-709-2018-lgpd-consentimento-e-requisitos-de-validade-art-8/amp/)); não conferido no planalto |
| Art. 8º, §§ 2º, 4º e 5º | Ônus da prova é do controlador; autorizações genéricas são nulas; revogação a qualquer momento, gratuita e facilitada | [trecho] (planalto) |
| Art. 9º | O que informar ao titular: finalidade, forma e duração, identificação e contato do controlador, uso compartilhado | [resumo] (planalto) |
| Art. 11, I | "consentir, de forma específica e destacada, para finalidades específicas" | [trecho] (planalto) |
| Art. 11, § 1º | Também vale para tratamento que **revele** dado sensível e possa causar dano | [resumo] (planalto) |
| Arts. 15 e 16 | Fim do tratamento e eliminação, com exceções para guardar | art. 15: [NV] (veio só o título); art. 16: [resumo] |
| Art. 18 e § 1º | Direitos do titular; reclamar à autoridade nacional | [resumo] (planalto) |
| Art. 19 | Acesso simplificado imediato, ou declaração completa em até 15 dias | [resumo] (planalto) |
| Art. 33, I, II "b" e VIII | País adequado; cláusulas-padrão; consentimento específico e em destaque | [resumo] (planalto) |
| Art. 41 | Indicar encarregado e divulgar o contato (de preferência no site) | caput: [trecho]; § 1º: [resumo] |
| Lei 15.352/2026 | Cria a "Agência Nacional de Proteção de Dados (ANPD), autarquia de natureza especial" | [trecho] |
| [Res. CD/ANPD nº 2/2022](https://www.gov.br/anpd/pt-br/acesso-a-informacao/institucional/atos-normativos/regulamentacoes_anpd/resolucao-cd-anpd-no-2-de-27-de-janeiro-de-2022) | Agente de pequeno porte não precisa indicar encarregado, mas deve ter um canal de comunicação | [trecho] |
| [Guia ANPD do encarregado](https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/copy_of_guia_da_atuacao_do_encarregado_anpd.pdf/@@display-file/file) | Pequeno porte com tratamento de **alto risco** deve indicar encarregado | [trecho]. A [minuta](https://www.gov.br/anpd/pt-br/assuntos/noticias/inclusao-de-arquivos-para-link-nas-noticias/minuta_de_resolucao___aplicacao_da_lgpd_para_agentes_de_tratamento_de_pequeno_porte.pdf/@@display-file/file) punha dado sensível como critério de alto risco; texto final: [NV] |
| [Res. CD/ANPD nº 19/2024](https://www.gov.br/anpd/pt-br/acesso-a-informacao/institucional/atos-normativos/regulamentacoes_anpd/resolucao-cd-anpd-no-19-de-23-de-agosto-de-2024) | Regulamento de transferência internacional e cláusulas-padrão | [resumo] |
| [Res. CD/ANPD nº 32/2026](https://www.gov.br/anpd/pt-br/centrais-de-conteudo/outros-documentos-e-publicacoes-institucionais/resolucao-no-32-decisao-de-adequacao-uniao-europeia-em-lingua-inglesa.pdf) | UE reconhecida como adequada (art. 33, I) | [resumo] (versão oficial em inglês e [lista de regulamentações da ANPD](https://www.gov.br/anpd/pt-br/acesso-a-informacao/institucional/atos-normativos/regulamentacoes_anpd)) |

**Encarregado na prática:** a Olami talvez se enquadre como agente de pequeno porte, que pela regra geral só precisa de um canal de contato. Mas a inscrição trata dado sensível, e o guia da ANPD tira a dispensa de quem faz tratamento de alto risco. O caminho prudente é **indicar um encarregado** e publicar o contato.

---

## (c) Migração do Google Forms em 5 passos

1. **Exportar e trancar o histórico (dia 1).** No Google Forms, vá em Respostas, abra o menu e baixe o CSV ou use "Ver no Planilhas". **[resumo]** ([ajuda do Google](https://support.google.com/docs/answer/139706?hl=en)) Guarde numa pasta do Drive com acesso só da coordenação e tire colaboradores antigos: quem tem acesso ao formulário pode ter acesso à planilha ligada. **[resumo]** Separe o que vale guardar (contagem por evento) do que pode ser apagado.
2. **Recriar o formulário (dias 1 e 2).** A Tally **não tem importador do Google Forms** (não encontrei: **[NV]**). Ela importa do Typeform em um clique e, com a Tally AI (beta, grátis), recria um formulário a partir de PDF, imagem, print, JSON, CSV ou Markdown. **[trecho]** ([Import](https://tally.so/help/import)) Como o formulário novo muda por causa da LGPD, o mais rápido é montar à mão o modelo da seção (b). **Não use conversores de terceiros que pedem a chave de API da Tally**, como o Form Mate. **[resumo]** Na Luma: crie o calendário da Olami e um ingresso grátis com Require Approval, capacidade e lista de espera, "Restrict Location to Guests", as perguntas mínimas e a pergunta "Termos" com o consentimento.
3. **Ligar à planilha (dia 2).** Na Tally: Integrations > Connect to Google Sheets. É grátis, cria uma linha por inscrição e traz as respostas antigas. **[trecho]** ([Google Sheets Integration](https://tally.so/help/google-sheets-integration)) Use uma planilha nova, compartilhada só com a equipe. Na Luma grátis não há integração automática (Zapier e API são Plus), então baixe o CSV com o check-in depois de cada evento. **[resumo]**
4. **Trocar os links e rodar 2 semanas em paralelo (semanas 1 e 2).** Troque o link na bio do Instagram, nos grupos e na comunidade do WhatsApp, no site e no Linktree. No Google Forms antigo, deixe só um aviso "inscrições agora em [link novo]" (ou feche para novas respostas; essa opção não foi conferida nesta pesquisa: **[NV]**). Toda semana, compare inscritos no novo, no antigo e presentes.
5. **Encerrar e apagar (fim da semana 2).** Feche o Google Forms. Depois de exportar o que precisa, use "Delete all responses" (Respostas > Resumo > menu) e desvincule a planilha; desvincular interrompe o envio de respostas novas, mas mantém os dados. **[resumo]** ([ajuda do Google](https://support.google.com/docs/answer/2917686?hl=en)) Apague as planilhas antigas que passaram do prazo de guarda. Na Tally o apagamento automático é do plano Business, então marque um lembrete mensal para apagar as restrições alimentares (30 dias) e as inscrições antigas (12 meses). O que se apaga sai dos backups em até 90 dias. **[resumo]**

---

## (d) Comparação com a Sympla grátis

**O que a Sympla oferece para evento gratuito** (fontes vistas em 14/10/2026):

- **Taxa:** nenhuma. Ingresso gratuito não tem taxa de serviço. **[resumo]** ([Quanto custa](https://produtores.sympla.com.br/quanto-custa/) · [Qual o custo para utilizar a Sympla](https://ajuda.sympla.com.br/hc/pt-br/articles/204767415-Qual-o-custo-para-utilizar-a-Sympla)) Em evento pago a taxa é de cerca de 10%, mas as fontes divergem.
- **Aprovação de inscritos:** **não encontrei recurso de aprovação manual [NV].** Só apareceu "compras pendentes de aprovação", que é sobre pagamento.
- **Check-in:**
  - App Sympla Organizador lê o QR Code ou usa a "lista de confirmados". **[trecho]** ([App Store](https://apps.apple.com/app/1140266871) · [App Organizador](https://www.sympla.com.br/app-organizador))
  - Funciona **sem internet** depois de baixar a lista; também dá para fazer pelo computador ou com leitor de código. **[trecho]** ([Controle de entrada](https://ajuda.sympla.com.br/hc/pt-br/articles/204767355-Como-controlar-a-entrada-de-participantes-no-dia-do-evento))
  - A equipe entra como colaboradora, com conta Sympla própria. **[trecho]** Há níveis de acesso como "Check-in" e "Coordenador de check-in". **[resumo]** ([Pessoas que trabalham no evento](https://ajuda.produtor.sympla.com.br/hc/pt-br/articles/15444664286221-Como-adiciono-pessoas-que-ir%C3%A3o-trabalhar-no-meu-evento))
- **Lembretes:**
  - E-mail de confirmação com QR automático; a página de produtores fala em "lembrete automático", mas não diz quando. **[resumo]** ([Eventos corporativos](https://produtores.sympla.com.br/eventos-corporativos-e-negocios/))
  - O organizador pode mandar e-mail aos participantes filtrando por ingresso e por check-in. **[resumo]** ([Enviar mensagem](https://ajuda.sympla.com.br/hc/pt-br/articles/204767365-Como-enviar-uma-mensagem-para-os-participantes-do-meu-evento))
  - **WhatsApp só por integração de terceiros**, como a Pluga. **[resumo]** ([Pluga, terceiro](https://blog.pluga.co/sympla-whatsapp-integrados/))
- **Exportação:** a aba Participantes tem "Exportar Participantes" (Excel), com as respostas do formulário e se a pessoa fez check-in. **[trecho]**
- **Formulário personalizado:**
  - Nome, sobrenome e e-mail por padrão. **[trecho]** Campos prontos (Endereço, Telefone, CPF/CNPJ, RG, Termo de responsabilidade) e campos livres (Texto, Parágrafo, Lista, Múltipla escolha, Vários valores). **[resumo]** Dá para mostrar uma pergunta só para certos tipos de ingresso. **[trecho]** ([Formulário personalizado](https://ajuda.sympla.com.br/hc/pt-br/articles/204767225-Posso-criar-um-formul%C3%A1rio-de-inscri%C3%A7%C3%A3o-compra-personalizado-e-por-onde-encontro-as-respostas-dele))
  - Para dado sensível, a Sympla orienta usar campo opcional, com consentimento expresso. **[resumo]** ([Dados sensíveis](https://ajuda.produtor.sympla.com.br/hc/pt-br/articles/15444516393741-Como-posso-coletar-dados-sens%C3%ADveis-no-formul%C3%A1rio-de-inscri%C3%A7%C3%A3o-personalizado))
- **Dados:** a Sympla é operadora dos dados do formulário, e o organizador é o controlador. Guarda em nuvem de parceiros no Brasil ou em outros países (EUA, UE). **[resumo]** ([Tratamento de dados](https://termos-e-politicas.sympla.com.br/hc/pt-br/articles/360031012191-2-Do-tratamento-de-dados-pessoais) · [Armazenamento](https://termos-e-politicas.sympla.com.br/hc/pt-br/articles/360030734152-6-Armazenamento-de-informa%C3%A7%C3%B5es-pessoais))

**Luma × Sympla × Google Forms + Tally** (planos grátis, para evento gratuito)

| Critério | Luma | Sympla | Google Forms + Tally |
|---|---|---|---|
| Custo para evento gratuito | US$ 0 [resumo] | R$ 0 [resumo] | R$ 0; Tally ilimitada com "fair use" [trecho] |
| Aprovação de inscritos | **Sim**, por ingresso [trecho] | [NV] (não encontrei) | Não tem: aprovação manual pela planilha [NV] |
| Esconder o endereço até aprovar | **Sim** [trecho] | [NV] | Não se aplica: o endereço vai à mão |
| Check-in | QR pelo app; o papel "só check-in" é Plus [trecho] | QR ou lista, **offline**, com nível "Check-in" para a equipe [trecho] | Não tem: lista impressa ou planilha [NV] |
| Lembretes | Automáticos, 1 dia e 1 hora antes, por e-mail/push/SMS/WhatsApp [trecho/resumo] | Confirmação por e-mail; "lembrete automático" sem detalhes; e-mail manual [resumo] | Não tem; o e-mail ao inscrito na Tally é Pro [trecho] |
| WhatsApp | Sim, conforme o país; Brasil [NV] | Só com terceiros [resumo] | Manual, fora da ferramenta |
| Exportação | CSV com check-in [resumo] | Excel com check-in [trecho] | Planilha Google automática (Tally) [trecho]; CSV (Google Forms) [resumo] |
| Formulário personalizado | Sim, 7 tipos, sem lógica condicional [resumo] | Sim, pergunta por tipo de ingresso [trecho] | Sim; a Tally tem lógica condicional grátis [resumo] |
| Caixa de consentimento | Pergunta "Termos" e Checkbox, obrigatórias se quiser [trecho/resumo] | "Termo de responsabilidade" e campos opcionais [resumo] | Checkbox; a Tally orienta caixas separadas [trecho] |
| Onde ficam os dados | AWS, sem escolha de região; país [NV] | Brasil ou exterior (EUA/UE) [resumo] | Tally: Bélgica/UE [trecho]; Google: [NV] |
| Português | Tem pt-BR [resumo] | Site e ajuda em português | [NV] (não pesquisado) |

---

## (e) Recomendação (5 linhas)

1. Use a **Luma grátis** como ferramenta principal: aprovação por ingresso, check-in por QR, lembretes automáticos e CSV com presença, sem custo para evento gratuito; ligue também "Restrict Location to Guests" (o plano desse recurso não foi confirmado).
2. Antes de prometer lembrete por WhatsApp, teste com um número +55. A regra da Luma aponta WhatsApp para o Brasil, mas isso não está escrito com todas as letras; o e-mail é o canal garantido.
3. Formulário mínimo (nome, e-mail, celular, 18+, restrição alimentar opcional) e consentimento destacado (pergunta "Termos" na Luma, ou o modelo Tally acima). Nunca pergunte religião.
4. Use a **Tally grátis** onde a Luma é fraca: formulários com lógica condicional (jantar grande com restrições), lista de interesse e pesquisas, com dados na UE e planilha automática.
5. A Sympla fica como plano B: boa em check-in offline e Excel, mas sem aprovação confirmada e sem WhatsApp nativo. Aposente o Google Forms depois de 2 semanas em paralelo e valide o texto LGPD com um advogado.

---

## (f) Limitações e não verificado

**Método**
- Nenhuma página foi lida por inteiro (sem WebFetch); tudo veio de trechos e resumos de busca.
- A cota de buscas acabou antes de conferir no planalto.gov.br o **art. 8º, § 1º** (cláusula destacada; só em fontes de terceiros) e o **art. 9º, § 3º** (o que informar quando o tratamento é condição para o serviço). Por isso o § 3º não foi citado.

**Luma**
- Se o **Brasil recebe por WhatsApp** (inferência pela regra "a maioria dos outros países").
- Se o anfitrião pode **exigir** telefone na inscrição (só no resumo).
- Se os lembretes de 1 dia e 1 hora ainda valem e saem por WhatsApp (a fonte é de 2024).
- Quantas pessoas ou aparelhos podem fazer check-in ao mesmo tempo, e se o leitor funciona na web.
- Se as perguntas personalizadas são do grátis (inferência); há versões em conflito sobre "nome e sobrenome separados só no Plus".
- O limite semanal de envio de um calendário que ainda não passou pela verificação da Luma (só achei os 500 do calendário verificado); o limite de importação de contatos (sem número).
- Preço do Plus (US$ 59 ou 69) visto só no resumo; valor em reais e impostos não pesquisados.
- Se "Restrict Location to Guests" e a lista de espera são do grátis.
- País onde os dados ficam, entidade legal e sede, e se a Luma é só operadora ou também controladora da conta do convidado. O DPA da Luma é "para clientes enterprise".

**Tally**
- Se o **checkbox único** pode ser obrigatório (só achei o "required" geral).
- Nomes exatos dos blocos (Short answer, Email, Phone number, Checkbox, Checkboxes, Text, Hidden fields): conferir no editor.
- Preços de Pro e Business (fontes em conflito).
- Lista de suboperadores fora da UE. A política de privacidade vista é de 20/11/2023.
- Importador do Google Forms: não encontrei, o que não prova que não exista.
- Aprovação, check-in e lembretes: não encontrados na documentação.

**Sympla**
- Aprovação manual de inscritos.
- Quando sai o lembrete automático de evento presencial e por qual canal.
- Taxa de evento pago (fontes divergem; não afeta a Olami).
- Em que país ficam os dados.

**Google**
- Onde o Google guarda respostas e planilhas (não pesquisado; afeta a transferência internacional).
- Opção de parar de aceitar respostas com mensagem.
- Menus que podem ter mudado (um dos artigos é antigo).

**LGPD**
- Art. 15 (veio só o título).
- Texto final da Res. CD/ANPD nº 2/2022 sobre "dado sensível = alto risco" (visto só na minuta) e o que a Res. CD/ANPD nº 15/2024 alterou nela.
- A Res. CD/ANPD nº 32/2026 foi conferida só pelo resumo e pela versão em inglês.
- Tratar a própria inscrição como dado sensível (art. 11, § 1º) é uma leitura cautelosa, que um advogado deve confirmar.
- Os prazos de guarda (12 meses e 30 dias) são sugestões, não exigência da lei.
