# T18 — Risco de banimento/restrição de número WhatsApp Business app usado via cliente não oficial (Baileys / whatsapp-web.js), 2025–2026

Pesquisa feita em 14/10/2026. Contexto do caso: empresa B2B de câmbio com um número do **WhatsApp Business app** (não a Cloud API) conectado via **Baileys** num servidor, atendendo clientes em grupos e no privado.

## Como ler este documento (método e limites)

- **Natureza da fonte**: OFICIAL (faq.whatsapp.com, whatsapp.com/legal, business.whatsapp.com, blog/newsroom Meta), IMPRENSA, COMUNIDADE (issue do GitHub, fórum, blog de vendedor de ferramenta).
- **Status de verificação**:
  - **[lido]** = página aberta e lida por mim nesta pesquisa (só foi possível no github.com e no raw.githubusercontent.com).
  - **[não verificado — snippet]** = conteúdo obtido apenas pelo resumo/trecho do mecanismo de busca, porque o domínio estava bloqueado na rede desta sessão (ver seção e). **Todas as páginas OFICIAIS caíram nesta categoria**: faq.whatsapp.com, whatsapp.com e business.whatsapp.com não abriram. Antes de usar qualquer frase "oficial" como citação, abra a URL e confira.
- Citações entre aspas vindas do GitHub vêm da leitura da página pela ferramenta de leitura (que resume o conteúdo); são fiéis ao que ela devolveu, mas convém reabrir a issue antes de citar literalmente em documento externo.
- Nenhum nome de pessoa física é citado. Relatos de issues aparecem como "relator", "comentarista" ou "mantenedor".
- Datas de issue = data de abertura/comentário mostrada no GitHub.

---

## (a) Tabela de gatilhos

| Gatilho | O que a fonte diz (citação curta ou paráfrase fiel) | Natureza | URL | Data da fonte | Verificação |
|---|---|---|---|---|---|
| Atividade que parece spam, automação ou envio em massa (gatilho geral da restrição) | Página "About restricted accounts": a restrição ocorre porque a atividade recente da conta "may look like spam, automated, or bulk messaging", o que viola os Termos; quem fizer spam, automação ou envio em massa pode ter a conta banida. | OFICIAL | https://faq.whatsapp.com/717472490411581/?cms_platform=web&lang=en | s/d | não verificado — snippet |
| Envio em massa / auto-mensagem (termos) | Termos de Serviço listam como uso proibido enviar "illegal or impermissible communications such as bulk messaging, auto-messaging, auto-dialing, and the like". | OFICIAL | https://www.whatsapp.com/legal/terms-of-service | s/d | não verificado — snippet |
| Cliente não oficial / automação (diretrizes) | Messaging Guidelines tratam como comportamento adverso usar "unofficial clients, bulk messaging, auto-messaging, auto-dialing, or automation to harm WhatsApp or our users". | OFICIAL | https://www.whatsapp.com/legal/messaging-guidelines | s/d (buscador indicou atualização recente) | não verificado — snippet |
| Cliente não oficial (termos do Business app) | Termos do WhatsApp Business App: a empresa não pode, "directly, indirectly, or through automated or other means", fazer scraping nem criar/usar apps que interajam com o serviço sem consentimento por escrito. | OFICIAL | https://www.whatsapp.com/legal/WhatsApp-Terms-for-WhatsApp-Business-App | vigência 23/09/2026 (segundo o snippet) | não verificado — snippet |
| Cliente não oficial (FAQ) | "About unofficial apps": usar apps não oficiais ou vincular a conta a versões não oficiais viola os Termos; contas podem ser banidas temporária ou permanentemente, ou sofrer restrições, "including the ability to link devices". | OFICIAL | https://faq.whatsapp.com/1217634902127718 | s/d | não verificado — snippet |
| Cliente não oficial (ban temporário) | "About temporarily banned accounts": a mensagem "Temporarily banned" pode significar uso de versão não oficial ou scraping; se não migrar para o app oficial, a conta "might be permanently banned". | OFICIAL | https://faq.whatsapp.com/1848531392146538/ | s/d | não verificado — snippet |
| Cliente não oficial (aviso do próprio projeto) | README do Baileys: não é afiliado ao WhatsApp; "Do not spam people with this. We discourage any stalkerware, bulk or automated messaging usage." / "Use at your own discretion." | COMUNIDADE (README do projeto) | https://github.com/WhiskeySockets/Baileys | consultado 14/10/2026 | lido |
| Cliente não oficial (aviso do próprio projeto) | README do whatsapp-web.js: "it is not guaranteed you will not be blocked by using this method. WhatsApp does not allow bots or unofficial clients on their platform, so this shouldn't be considered totally safe." | COMUNIDADE (README do projeto) | https://github.com/wwebjs/whatsapp-web.js | consultado 14/10/2026 | lido |
| Cliente não oficial (aviso no app) | Relato: app mostrou alerta "Your account may soon be subject to restrictions" dizendo que a conta usava ferramentas "unauthorized"; 2 alertas em 700 instâncias, 1 em ~20 instalações. | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/2658 | 24/06/2026 | lido |
| Cliente não oficial (aviso de desativação) | Relato com texto do aviso (com erros de digitação no original): "Your account has beed disabled because we detected you are using an unofficiabl whatsapp". | COMUNIDADE | https://github.com/wwebjs/whatsapp-web.js/issues/3594 | jun/2025 | lido |
| Cliente não oficial (detecção em teste) | WhatsApp testa aviso na tela "Aparelhos conectados" para quem vincula a conta via cliente web não oficial; o aviso volta até o usuário migrar ao WhatsApp Web oficial (beta Android 2.26.35.1). | IMPRENSA (site de acompanhamento de betas) | https://wabetainfo.com/whatsapp-is-testing-a-safety-warning-for-unofficial-web-clients/ ; https://www.tuttoandroid.net/news/2026/09/01/whatsapp-avviso-client-web-non-ufficiali-android-1170360/ | ~01/09/2026 | não verificado — snippet |
| Contatos novos (primeiro contato) / "reach-out" | Investigação do Baileys: erro 463 "NackCallerReachoutTimelocked" = trava temporal que impede mandar mensagens/ligar para desconhecidos; o mantenedor conclui que "the 463 is in fact a result of an account restriction". Com a trava, só é possível enviar a chats que já têm "tctoken". | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/2441 | 25/03/2026 (comentários até set/2026) | lido |
| Contatos novos por dia | Relato: restrição de 24 h depois de enviar 30–40 mensagens a usuários novos; outro: restrição após responder ~100 usuários. | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/2800 | 05/09/2026 e 27/09/2026 | lido |
| Contatos novos por dia (número Business) | Relato: mensagens-modelo para contatos não salvos e sem histórico, ~15–20/dia → 2 restrições de 24 h → 2 bans de 48 h → ban vitalício que tirou o acesso ao WhatsApp Business. | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/1983 | 28/10/2025 | lido |
| Contatos novos (blog de vendedor) | Guia de vendedor: "cooldown" costuma ocorrer após mensagens a 20–30 contatos novos em janela curta; ainda dá para responder clientes existentes. | COMUNIDADE (blog de vendedor) | https://chakrahq.com/article/whatsapp-business-account-restricted-fix/ | 2026 (título) | não verificado — snippet |
| Mensagens sem resposta | WhatsApp testa limite mensal de mensagens enviadas a quem não responde (pessoas e empresas); número não divulgado; pop-up de aviso perto do limite; resposta do destinatário "zera" a contagem daquele envio. | IMPRENSA | https://techcrunch.com/2025/10/17/whatsapp-will-curb-the-number-of-messages-people-and-businesses-can-send-without-a-response | 17/10/2025 | não verificado — snippet |
| Mensagens sem resposta (baixa taxa de resposta) | Vendedores citam como fator de risco a baixa razão respostas/mensagens enviadas (o resumo de busca atribuiu isso ao conjunto das páginas, sem indicar uma só). | COMUNIDADE (blog de vendedor) | https://support.whapi.cloud/help-desk/blocking/how-to-not-get-banned ; https://green-api.com/en/docs/faq/how-to-protect-number-from-ban/ | s/d | não verificado — snippet |
| Denúncias / bloqueios pelos destinatários | Business Messaging Policy: só contatar quem deu o número e deu opt-in; os sistemas podem limitar quantas mensagens/ligações a empresa inicia com base no feedback dos usuários (bloqueios e denúncias). | OFICIAL | https://business.whatsapp.com/policy | s/d | não verificado — snippet |
| Denúncias / bloqueios | Mantenedor do whatsapp-web.js (2021): envio em massa é detectado por "consistent intervals, message rates, the amount of contacts, and possible reports from end users". | COMUNIDADE | https://github.com/wwebjs/whatsapp-web.js/issues/532 | 09/02/2021 (tópico trancado em jul/2024) | lido |
| Detecção sem denúncia | Reportagem de 2019: WhatsApp removia ≥2 milhões de contas/mês por comportamento automatizado/em massa, mais de 75% banidas sem denúncia recente de usuário (detecção proativa). | IMPRENSA | https://gulfnews.com/world/asia/india/whatsapp-removing-2-million-suspicious-accounts-a-month-in-india-1.1549520714416 | fev/2019 | não verificado — snippet |
| Mesma mensagem para muitos | Relato: número restrito após ~100 usuários; o relator atribui a respostas idênticas a mensagens idênticas (mesma saudação, mesmo comando). | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/2800 | 27/09/2026 | lido |
| Criação de grupo / adicionar gente em grupo | Conta restrita não pode "create groups" nem "add members to groups", nem iniciar chat/ligação com contato novo nem usar aparelhos conectados. | OFICIAL | https://faq.whatsapp.com/717472490411581/?cms_platform=web&lang=en | s/d | não verificado — snippet |
| Adicionar gente em grupo (proteção do destinatário) | Desde ago/2025, quem é adicionado a grupo por alguém fora dos contatos vê "safety overview" (dados do grupo, opção de sair sem abrir o chat, notificações silenciadas). | IMPRENSA | https://www.tribuneindia.com/news/business/whatsapp-launches-safety-overview-tool-bans-6-8-mn-accounts-linked-to-scam-centres | ago/2025 | não verificado — snippet |
| Criação/adição em massa em grupos | FAQ de vendedor: criação repetida de grupos em massa ou adição em massa de usuários pode disparar restrição. | COMUNIDADE (blog de vendedor) | https://greenapi.com/en/docs/faq/what-types-of-blocks-can-whatsapp-impose | s/d | não verificado — snippet |
| Bots em grupos | Relato: 5 bans em uma semana em bots que estavam em ~9 grupos cada; suspeita (não confirmada) de que misturar grupo e privado dispara ban; ban "within 2 mins" após reconectar. | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/1869 | 05/10/2025 | lido |
| Link na primeira mensagem | **Nenhuma fonte encontrada/conferida** dentro do teto de buscas. Não há base pública verificada nesta pesquisa para afirmar que link na 1ª mensagem é gatilho. | — | — | — | não encontrado |
| Versão do cliente desatualizada | Comunidade: "always use latest version to avoid getting banned" (comentário); conta restaurada com mensagens privadas não entregues resolvida ao atualizar o Baileys para a versão atual do GitHub. | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/1983 ; https://github.com/WhiskeySockets/Baileys/issues/2699 | out/2025; jul/2026 | lido |
| Versão do cliente desatualizada (463) | Única correção relatada para o erro 463: subir para Baileys 7.0.0-rc13 ou posterior (suporte a tctoken); resultados variam e há logout forçado não resolvido no rc14. | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/2441 | jul–ago/2026 | lido |
| Sessões múltiplas / reconexão | Comentários suspeitam que lógica de reconexão que deixa dois sockets vivos na mesma sessão leva a conflito e ban (não confirmado). | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/2707 ; https://github.com/WhiskeySockets/Baileys/issues/2699 | jul/2026 | lido |
| Sessões múltiplas + IP de datacenter | Conta Business verificada (selo azul) restrita "instantaneamente" ao escanear QR num servidor GCP com várias conexões Baileys simultâneas; aviso: "This account is not allowed to use WhatsApp due to spam". Relator suspeita de IP de datacenter, densidade de conexões e impressão digital TLS (hipóteses). | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/2805 | 07/09/2026 | lido |
| IP de servidor | Comentário: "Server IPs are flagged more aggressively by WhatsApp" (opinião; o autor promovia biblioteca própria). | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/2309 | 24/03/2026 | lido |
| Aparelhos conectados (limite/inatividade do celular) | FAQ multi-agent (Business app): limite de aparelhos depende de assinatura Meta Verified/Meta One; se o aparelho principal não for usado por mais de 14 dias, os aparelhos conectados são desconectados. | OFICIAL | https://faq.whatsapp.com/395911122612120/?cms_platform=android | s/d | não verificado — snippet |
| Número novo sem aquecimento | Relato com WhatsApp Business, número recém-criado: ~110 msg/dia, intervalos aleatórios de 20–35 s, pausa de 2–3 min a cada 25 → restrição de 24 h logo após as 3 primeiras mensagens. | COMUNIDADE | https://github.com/wwebjs/whatsapp-web.js/issues/4008 | 08/12/2025 | lido |
| Número novo sem aquecimento | Sugestão de comunidade: deixar o número sem conectar ~2 dias e conversar devagar a partir de outro número antes de ligar o bot. | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/2131 | 07/12/2025 | lido |
| Envio 24 h sem pausa | Comentário: o problema vem de o WhatsApp detectar bots que rodam 24/7; recomenda não rodar sem parar, não mandar rajadas, usar atrasos aleatórios. | COMUNIDADE | https://github.com/wwebjs/whatsapp-web.js/issues/3594 | 09/06/2025 | lido |
| Envio 24 h sem pausa (número novo) | Regra de vendedor (Whapi) para números novos: não passar de 2 msg/min, nem de 6 h de atividade/dia, nem de 3 dias seguidos. | COMUNIDADE (blog de vendedor) | https://support.whapi.cloud/help-desk/blocking/how-to-not-get-banned ; https://support.whapi.cloud/help-desk/blocking/warming-up-new-phone-numbers-for-whatsapp-api | s/d | não verificado — snippet |
| Checagem repetida de número (isRegisteredUser / getNumberId) | Relatos: restrição de 24 h ao escanear QR; chamadas repetidas a `isRegisteredUser()` (~80/h) e `getNumberId()` associadas a restrição/ban; conselho: "Avoid use client.isRegisteredUser()". | COMUNIDADE | https://github.com/wwebjs/whatsapp-web.js/issues/3948 | nov/2025 | lido |
| Envio a número não registrado | Observação (não confirmada) de que enviar a número fora do WhatsApp pode disparar restrição `RESTRICT_ALL_COMPANIONS`. | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/2441 | ago/2026 | lido |
| Publicação de status em massa | Relato: status para 2–3 mil contatos em lotes de 100, num servidor → 2 bans temporários e depois permanente. | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/2309 | 30/01/2026 | lido |
| "Não marcar como lido" / presença | **Nenhuma fonte pública encontrada** ligando marcar/não marcar como lido a ban. Presença "digitando" aparece só como sugestão de comunidade (ver seção d). | — | — | — | não encontrado |

---

## (b) Restrição × ban temporário × ban permanente × recurso

| Situação | O que acontece (segundo a fonte) | Duração | Recurso | Natureza | URL | Verificação |
|---|---|---|---|---|---|---|
| **Conta restrita** ("Your account is restricted right now") | Continua falando com pessoas e grupos com quem já conversou. Não pode iniciar chat/ligação com contato novo, criar grupo, adicionar membros a grupo nem usar aparelhos conectados; alguns aparelhos conectados podem ser deslogados. | "allocated time"; termina sozinha e o app notifica. Para ver o tempo restante: Nova conversa → contato com quem nunca falou → pop-up mostra o tempo. | Não há ação: a restrição acaba sozinha. | OFICIAL | https://faq.whatsapp.com/717472490411581/?cms_platform=web&lang=en | não verificado — snippet |
| Conta restrita — duração observada | Relatos de 24 h são os mais comuns (Baileys #2800, #2260; wwebjs #4008, #3948). | 24 h (relatos) | — | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/2800 ; https://github.com/wwebjs/whatsapp-web.js/issues/4008 | lido |
| Conta restrita — ponto crítico para quem usa Baileys | Como a restrição corta "linked devices", e o Baileys é um aparelho conectado, **a restrição derruba o canal do servidor** mesmo antes de um ban. Relato no Baileys: notificação de trava seguida de logout 401 `device_removed`. | — | — | OFICIAL (corte de linked devices) + COMUNIDADE (logout) | https://faq.whatsapp.com/717472490411581/?cms_platform=web&lang=en ; https://github.com/WhiskeySockets/Baileys/issues/2441 | snippet / lido |
| **Ban temporário** ("Temporarily banned") | Pode indicar uso de versão não oficial ou scraping; a orientação é migrar para o app oficial ou parar o scraping. | Duração não informada nos trechos obtidos (não verificado). | Migrar para o app oficial; se não migrar, pode virar permanente. | OFICIAL | https://faq.whatsapp.com/1848531392146538/ | não verificado — snippet |
| Ban temporário — escalada observada | Relato de número Business: 2× restrição de 24 h → 2× ban de 48 h → ban vitalício que tirou o acesso ao WhatsApp Business. Outro: "multiple bans in a row and then a permanent ban". | 24 h / 48 h (relatos) | — | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/1983 ; https://github.com/WhiskeySockets/Baileys/issues/1869 | lido |
| **Ban (permanente)** | Tela: "This phone number can't use WhatsApp: [número]. You can request a review of this number." Bane quando entende que a atividade viola os Termos (ex.: spam, golpes, risco à segurança). | Permanente, salvo revisão favorável. | **No app**: tocar "Request review"; o app notifica a decisão. A maioria das revisões é concluída em até 24 h. Uma revisão por número. **Se não aparecer opção de revisão, o ban é final e sem recurso.** Contatar fora do fluxo não acelera; terceiros não removem ban. | OFICIAL | https://faq.whatsapp.com/465883178708358/ | não verificado — snippet |
| Ban — Business app, mensagem "Your phone number is banned from using WhatsApp. Contact support for help." | Aponta a seção "Acceptable Use of our Business Services" dos Termos; pode não haver aviso prévio. | — | "if you think your account was banned by mistake, please email us and we'll look into your case" (endereço de e-mail não conferido). | OFICIAL | https://faq.whatsapp.com/560862344471551/?locale=en_US | não verificado — snippet |
| Canal de contato | Página "Contact WhatsApp" reúne formulários de suporte (não há formulário específico de recurso conferido). | — | Formulários de contato | OFICIAL | https://www.whatsapp.com/contact | não verificado — snippet |
| Ban por cliente não oficial — relato de recuperação | Relator contatou o suporte do WhatsApp e, "after several attempts", conseguiu reconectar; suspeitou que era um aviso. | — | Suporte (relato) | COMUNIDADE | https://github.com/wwebjs/whatsapp-web.js/issues/3594 | lido |
| Conta restaurada após ban | Relato: depois de restaurada, mensagens 1:1 enviadas pelo Baileys não chegavam (grupos funcionavam); resolveu ao atualizar o Baileys. | — | — | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/2699 | lido |
| Prazo de revisão (outro produto) | Para restrição "Sending spam" de conta da **API** (não do app), um vendedor fala em revisão pelo Meta Business Suite em 24–48 h, às vezes até 1 semana. **Não se aplica diretamente ao Business app.** | 24–48 h, até 1 semana | Meta Business Suite | COMUNIDADE (blog de vendedor) | https://support.wati.io/en/articles/15846639-how-to-appeal-a-sending-spam-restriction-for-your-whatsapp-business-account | não verificado — snippet |

Notas:
- "Request review" e "até 24 h" vêm da página oficial "About account bans" (via snippet). Não achei prazo oficial para ban temporário nem para a restrição.
- Política oficial de Business: o WhatsApp pode "limit or remove your access to WhatsApp for Business" de quem usa ou opera serviço que viola termos, "such as messaging people at scale in an unauthorized manner" (https://business.whatsapp.com/policy — não verificado, snippet).

---

## (c) Mudanças 2024–2026 (com datas)

| Data | Mudança | Natureza | URL | Verificação |
|---|---|---|---|---|
| mai/2024 | Beta do WhatsApp com recurso de **restrição de conta**: impede iniciar chats novos por um tempo como punição temporária, em vez de banir; detecção automática de comportamento tipo spam (muitas mensagens para desconhecidos). | IMPRENSA | https://www.medianama.com/2024/05/223-whatsapp-beta-tests-new-temporary-chat-restrictions/ ; https://www.phonearena.com/news/whatsapp-working-on-automated-restrictions-that-could-reduce-spam_id157919 | não verificado — snippet |
| s/d (página vigente) | Página oficial "About restricted accounts" descreve a restrição já em produção (o que fica bloqueado, como ver o tempo restante). | OFICIAL | https://faq.whatsapp.com/717472490411581/?cms_platform=web&lang=en | não verificado — snippet |
| 18/03/2025 | Meta anuncia testes de **limite mensal de mensagens de transmissão (broadcast)** para pessoas e empresas; exemplo citado pela Meta: 30/mês (pode mudar no teste). No **Business app**, broadcast era grátis e ilimitado; no piloto, 250 mensagens personalizadas grátis e cobrança acima disso (preço não definido). | IMPRENSA | https://techcrunch.com/2025/03/18/whatsapp-will-soon-limit-number-of-broadcast-messages-users-and-businesses-can-send/ | não verificado — snippet |
| 2026 | **Não achei anúncio oficial** de lançamento definitivo, preço ou limite final de broadcast no Business app. Blogs de vendedor trazem números conflitantes, sem fonte Meta (não atribuo número a URL específica porque o resumo de busca não deixou claro de qual página vinha cada número). | — | — | não verificado |
| ago/2025 | "Safety overview" ao ser adicionado a grupo por quem não é contato; Meta informa 6,8 milhões de contas ligadas a centrais de golpe banidas no 1º semestre de 2025. | IMPRENSA | https://www.tribuneindia.com/news/business/whatsapp-launches-safety-overview-tool-bans-6-8-mn-accounts-linked-to-scam-centres ; https://dailynews.co.za/technology/mobile-apps/2025-08-06-whatsapp-ramps-up-fight-against-messaging-scams-with-new-tools-and-account-bans/ | não verificado — snippet |
| out/2025 (anúncio) → 15/01/2026 (vigência para clientes existentes) | Business Solution Terms (API) ganham seção "AI Providers": proíbe provedores de IA de uso geral cuja funcionalidade principal é a IA; IA embutida em atendimento continua permitida. Novos clientes da API sob os termos desde 15/10/2025. Página oficial mostra "Last Modified: January 15, 2026". **Vale para a API, não para o Business app.** | OFICIAL + IMPRENSA + COMUNIDADE | https://www.whatsapp.com/legal/business-solution-terms ; https://www.business-standard.com/technology/tech-news/meta-bans-ai-chatbots-from-whatsapp-business-api-chatgpt-to-shut-down-jan-2026-125102200335_1.html ; https://respond.io/blog/whatsapp-general-purpose-chatbots-ban | não verificado — snippet |
| 17/10/2025 | Teste de **limite mensal de mensagens sem resposta** (pessoas e empresas, para quem não respondeu); número não divulgado ("testing different limits"); pop-up quando se aproxima do limite; teste em vários países "in the coming weeks". Beta Android 2.25.31.5 citado. | IMPRENSA | https://techcrunch.com/2025/10/17/whatsapp-will-curb-the-number-of-messages-people-and-businesses-can-send-without-a-response ; https://www.digit.in/news/apps/whatsapp-to-limit-how-many-messages-you-can-send-in-new-chats-to-fight-spam-and-unwanted-texts.html | não verificado — snippet |
| após out/2025 | **Não achei confirmação de lançamento global em 2026** do limite de mensagens sem resposta, nem número oficial. Um veículo cita "Messaging Limit Framework" em 07/10/2025; não corroborado, possivelmente ligado aos limites da API. | IMPRENSA | https://techeconomy.ng/whatsapp-sets-messaging-limits-curb-spam | não verificado — snippet |
| out–nov/2025 | Onda de relatos de ban/restrição com Baileys (v6.7.x e 7.0.0-rc) e com whatsapp-web.js 1.34.2. | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/1869 ; https://github.com/WhiskeySockets/Baileys/issues/1983 ; https://github.com/WhiskeySockets/Baileys/issues/2131 ; https://github.com/wwebjs/whatsapp-web.js/issues/4008 | lido |
| 04/12/2025 | Comissão Europeia abre investigação sobre a exclusão de IAs rivais. | IMPRENSA | https://www.theregister.com/2025/12/04/eu_probes_meta_whatsapp_ai/ | não verificado — snippet |
| 24/12/2025 | Autoridade antitruste italiana (AGCM) manda a Meta suspender a política contra chatbots rivais. | IMPRENSA | https://techcrunch.com/2025/12/24/italy-tells-meta-to-suspend-its-policy-that-bans-rival-ai-chatbots-from-whatsapp/ | não verificado — snippet |
| jan–mar/2026 (Brasil) | CADE impõe medida preventiva contra a regra de chatbots; em 04/03/2026 o plenário nega recurso da Meta e mantém a medida (provedores de IA podem continuar na plataforma). | IMPRENSA | https://www.cnnbrasil.com.br/economia/negocios/cade-mantem-medida-preventiva-que-obriga-meta-a-permitir-chatbots-de-ia-no-whatsapp/ ; https://mercadoeconsumo.com.br/04/03/2026/noticias/cade-mantem-medida-preventiva-que-obriga-meta-a-permitir-chatbots-de-ia-no-whatsapp/ | não verificado — snippet |
| fev/2026 | Comissão Europeia envia objeções formais (statement of objections). | IMPRENSA | https://alternativeto.net/news/2026/2/eu-warns-meta-it-has-to-open-whatsapp-to-rival-ai-chatbots-citing-antitrust-concerns | não verificado — snippet |
| 09/06/2026 | Comissão Europeia emite medida cautelar: Meta deve reabrir a Business API a assistentes de IA de terceiros nos termos anteriores a 15/10/2025, até o fim do processo. | IMPRENSA | https://www.morningstar.com/news/dow-jones/202606095919/meta-gets-eu-antitrust-order-to-open-whatsapp-to-rival-ai-chatbots-update | não verificado — snippet |
| 25/03/2026 → set/2026 | Comunidade Baileys documenta o erro **463 "reach-out timelock"** (restrição para iniciar conversa com desconhecidos) como ligado a restrição de conta; correção parcial via tctoken (7.0.0-rc13+), sem solução oficial. | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/2441 ; https://github.com/WhiskeySockets/Baileys/issues/2707 | lido |
| jun/2026 | Aparecem relatos de aviso no app "Your account may soon be subject to restrictions", citando ferramentas não autorizadas. | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/2658 | lido |
| ~01/09/2026 | WhatsApp testa aviso persistente em "Aparelhos conectados" para clientes web não oficiais (beta Android 2.26.35.1). Indica que o WhatsApp já distingue esses clientes. | IMPRENSA | https://wabetainfo.com/whatsapp-is-testing-a-safety-warning-for-unofficial-web-clients/ ; https://www.tuttoandroid.net/news/2026/09/01/whatsapp-avviso-client-web-non-ufficiali-android-1170360/ | não verificado — snippet |
| 23/09/2026 | Entram em vigor os novos **"WhatsApp Terms for WhatsApp Business App"** (segundo o snippet: "These new terms will go into effect on September 23, 2026"); incluem proibição de acesso por meios automatizados e de apps que interajam com o serviço sem consentimento. | OFICIAL | https://www.whatsapp.com/legal/WhatsApp-Terms-for-WhatsApp-Business-App | não verificado — snippet |

---

## (d) Números concretos citados — TODOS COMUNIDADE (não são limites oficiais)

O WhatsApp **não publica** limite diário seguro para o Business app. Os números abaixo são relatos isolados ou regras de vendedor e se contradizem. Servem como indício, não como garantia.

| Número citado | Contexto / resultado | Natureza | URL | Data | Verificação |
|---|---|---|---|---|---|
| 30–40 mensagens a usuários novos | → restrição de 24 h | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/2800 | 05/09/2026 | lido |
| ~100 usuários com respostas idênticas | → número restrito | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/2800 | 27/09/2026 | lido |
| 15–20 mensagens/dia a contatos não salvos (número Business) | → 24 h, 24 h, 48 h, 48 h, ban vitalício | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/1983 | 28/10/2025 | lido |
| ~50 mensagens num dia + 10 no mesmo dia, sem atraso | → ban temporário de 24 h; depois de expirar, bloqueado de novo após ~9 mensagens | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/2850 | 07/10/2026 | lido |
| Atraso aleatório 3–10 s (curto) e 13–23 s (longo), pausa de 40 s entre lotes, presença "digitando" antes de cada mensagem | Sugestão de comentarista ("u need to implement random delay between messages"); sem medição | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/2850 | 14/10/2026 | lido |
| Intervalo fixo de 7 s | → ban relatado | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/2131 | 29/11/2025 | lido |
| Atraso aleatório 11–27 s | → ainda problemático | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/2131 | 30/11/2025 | lido |
| Deixar número novo ~2 dias sem conectar e conversar devagar antes de ligar o bot | Sugestão de aquecimento | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/2131 | 07/12/2025 | lido |
| ≤ 8 mensagens/min e ≤ 200/h; aquecimento de 7+ dias para número e IP novos; atrasos com distribuição gaussiana | Sugestão (o autor promovia biblioteca própria) | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/2309 | 24/03/2026 | lido |
| 2–5 s de jitter entre lotes de status | Sugestão | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/2309 | 25/04/2026 | lido |
| Aquecimento de 7 dias + jitter gaussiano | Sugestão (comentário de ferramenta de terceiro) | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/2075 | 25/04/2026 | lido |
| ~400 conversas em 2 h (~100 pessoas), respostas em 2–4 s | → restrição em ~2 h numa conta de 7 meses | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/1850 | 01/10/2025 | lido |
| Atrasos de 30–120 s por mensagem | → também restrito (outro relato) | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/1850 | out/2025 | lido |
| Bots duravam ~1 semana no privado e ~1 semana por grupo | Relato | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/1869 | out/2025 | lido |
| Trava 463 padrão de 60 s quando o servidor não informa expiração | Leitura de código pela comunidade | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/2441 | 25/03/2026 | lido |
| tctoken dura ~28 dias | Relato | COMUNIDADE | https://github.com/WhiskeySockets/Baileys/issues/2707 | jul/2026 | lido |
| ~110 msg/dia em ~60 min, 20–35 s aleatório, pausa de 2–3 min a cada 25, até 3 mensagens para quem nunca falou (WhatsApp Business, número novo) | → restrição de 24 h depois das 3 primeiras | COMUNIDADE | https://github.com/wwebjs/whatsapp-web.js/issues/4008 | 08/12/2025 | lido |
| 60–75 s de atraso | "still not enough" desde whatsapp-web.js 1.34.2 | COMUNIDADE | https://github.com/wwebjs/whatsapp-web.js/issues/4008 | 10/12/2025 | lido |
| Lotes de 10–15 números, 40–60 s de atraso, 35–45 min entre lotes | → ~160 mensagens e ban após mais 3 | COMUNIDADE | https://github.com/wwebjs/whatsapp-web.js/issues/4008 | 16/12/2025 | lido |
| Hipótese de limite real de 50–75/dia (número novo) | Hipótese do relator, não medida | COMUNIDADE | https://github.com/wwebjs/whatsapp-web.js/issues/4008 | 08/12/2025 | lido |
| Intervalo de 15 s, ~250 mensagens | → restrição | COMUNIDADE | https://github.com/wwebjs/whatsapp-web.js/issues/3966 | 20/11/2025 | lido |
| 3–7 s proporcionais ao tamanho do texto + estado "digitando"; não escrever para quem nunca interagiu | Sugestão de comentarista | COMUNIDADE | https://github.com/wwebjs/whatsapp-web.js/issues/3966 | nov/2025 | lido |
| 7–13 s e depois 8–15 s; `isRegisteredUser()` ~80×/h | → restrição de 24 h ao escanear QR | COMUNIDADE | https://github.com/wwebjs/whatsapp-web.js/issues/3948 | nov/2025 | lido |
| ~200 mensagens (às vezes 10) a ~1.500 contatos salvos | → ban (2021); usuário seguro relata 3–4 pessoas/dia, sempre iniciadas pelo cliente | COMUNIDADE | https://github.com/wwebjs/whatsapp-web.js/issues/532 | 2021–2024 | lido |
| 20 destinatários novos/dia para número novo; até 200 clientes/dia no total; 25–30 dias para deixar de ser "suspeito" | Regra de vendedor (Green-API; o resumo de busca não indicou qual das duas páginas) | COMUNIDADE (blog de vendedor) | https://green-api.com/en/docs/faq/warming-up-whatsapp-number/ ; https://green-api.com/en/docs/faq/how-to-protect-number-from-ban/ | s/d | não verificado — snippet |
| ≤ 2 msg/min, ≤ 6 h de atividade/dia, ≤ 3 dias seguidos (número novo) | Regra de vendedor (Whapi; o resumo de busca não indicou qual das duas páginas) | COMUNIDADE (blog de vendedor) | https://support.whapi.cloud/help-desk/blocking/how-to-not-get-banned ; https://support.whapi.cloud/help-desk/blocking/warming-up-new-phone-numbers-for-whatsapp-api | s/d | não verificado — snippet |
| Aquecer 10–30 dias antes de tráfego automatizado alto | Regra de vendedor | COMUNIDADE (blog de vendedor) | https://whapi.cloud/blog/pt/how-to-warm-up-whatsapp-number-real-inbound-conversations | s/d | não verificado — snippet |
| 20–30 contatos novos em janela curta → "cooldown" | Regra de vendedor | COMUNIDADE (blog de vendedor) | https://chakrahq.com/article/whatsapp-business-account-restricted-fix/ | 2026 | não verificado — snippet |

Padrão que se repete nos relatos (COMUNIDADE): o maior risco aparece ao **iniciar conversa com quem nunca falou com o número** (número não salvo, sem histórico). Responder a quem escreveu primeiro aparece bem menos nos relatos. Mesmo intervalos longos (20–120 s) não evitaram restrição em vários casos, e atrasos sozinhos não parecem resolver.

---

## Leitura para o caso (síntese, não é fonte)

1. O uso descrito (Business app + Baileys num servidor) viola, pelo texto oficial via snippet, os Termos de Serviço e os novos Termos do Business App (vigência 23/09/2026), que proíbem acesso por meios automatizados ou apps não autorizados. O risco não é zero mesmo com volume baixo.
2. A **restrição** (não só o ban) já derruba o Baileys, porque corta "linked devices". Para o comercial, uma restrição de 24 h pode ter o mesmo efeito de uma queda.
3. O ban permanente pode ser final, sem botão de revisão. Quando há revisão, o oficial diz que a maioria sai em até 24 h.
4. O WhatsApp está testando avisos específicos para clientes web não oficiais (set/2026) e limites para mensagens sem resposta (out/2025). A tendência é de mais detecção, não menos.
5. A regra de IA de uso geral (jan/2026) vale para a API, não para o Business app. No Brasil, foi suspensa por medida do CADE (mar/2026).

---

## (e) Domínios bloqueados nesta sessão

Testados em 14/10/2026.

**WebFetch, falha de DNS (`getaddrinfo ENOTFOUND`):**
- faq.whatsapp.com
- www.whatsapp.com
- business.whatsapp.com
- blog.whatsapp.com
- developers.facebook.com
- techcrunch.com
- wabetainfo.com
- green-api.com
- support.whapi.cloud
- www.apfelpatient.de
- www.storyboard18.com
- en.wikipedia.org
- wwebjs.dev

**curl via proxy da sessão:**
- faq.whatsapp.com: `CONNECT tunnel failed, response 403` (o proxy registra "policy denial or upstream failure").
- Sem resposta (HTTP 000): www.whatsapp.com, business.whatsapp.com, developers.facebook.com, blog.whatsapp.com, about.fb.com, www.facebook.com, transparency.meta.com, wwebjs.dev, www.reddit.com, web.archive.org, archive.ph, r.jina.ai, www.google.com, techcrunch.com, www.theverge.com, wabetainfo.com.
- github.com e api.github.com: 403 via curl, mas **github.com abriu normalmente via WebFetch**.

**Acessíveis:**
- github.com (via WebFetch)
- raw.githubusercontent.com (via curl, HTTP 200)

Consequência: nenhuma página OFICIAL nem de IMPRENSA pôde ser aberta. Tudo dessas categorias está marcado "não verificado — snippet".

---

## (f) Buscas usadas

- **30 de 30** buscas web (WebSearch, modo "standard").
- Leituras de página (WebFetch) e downloads de README via raw.githubusercontent.com não contam como busca.
- Nenhuma conta foi criada, nenhuma mensagem foi enviada, nada atrás de login foi acessado.
