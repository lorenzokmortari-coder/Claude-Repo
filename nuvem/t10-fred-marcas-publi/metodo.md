# Método: marcas que pagam publi (t10, Fred)

Pesquisa feita em 14/10/2026 para o Fred, perfil de sátira do mundo corporativo brasileiro. Objetivo: achar marcas que fizeram conteúdo pago com criadores de humor corporativo ou de negócios no Brasil em 2025–2026. Arquivos: `marcas.csv` (uma linha por marca), `top15.md` (ordem de prioridade) e este método.

## Números

- **116 buscas feitas** com o WebSearch (114 no modo "standard", 2 no "extended"). Outras 3 foram recusadas porque o limite de 200 buscas por turno, dividido entre todos os agentes do turno, acabou.
- **Cerca de 80 buscas** trouxeram ao menos um fato usado no CSV. As outras vieram vazias, antigas, de fora do Brasil ou repetidas.
- **42 marcas** viraram linha (uma por marca).
- Verificação: **31 "confirmado no trecho"** e **11 "só no resumo da busca"**.
- Data: **25 linhas com data de 2025 ou 2026** (mês ou dia); 16 com "não verificado" (em 3 delas o ano aparece no título: Elma Chips 2025, MadeiraMadeira 2025, Itaú 2026); 1 de out/2024 (Alura, marcada como fora do período).
- **9 linhas sem link** porque o único endereço achado tem nome de pessoa (ver "Regra de dado pessoal").
- A meta de 40 marcas foi batida em número de linhas, mas só 25 têm exemplo com data confirmada em 2025–2026. As demais estão marcadas.

## Regras seguidas

- Só fonte pública que apareceu num resultado de busca: imprensa de marketing e negócios (Meio & Mensagem, Propmark, Marcas pelo Mundo, Grandes Nomes da Propaganda, ABC da Comunicação, Nosso Meio, Acontecendo Aqui, Mundo do Marketing, Forbes Brasil, InfoMoney, Startups, Baguete, Canaltech, Revista Apólice, BPMoney, PRNewswire) e páginas oficiais das marcas.
- O WebFetch não funciona neste ambiente, então nenhuma página foi aberta. Tudo vem do título, do endereço e do resumo com trechos que a busca devolveu.
- Nenhuma conta criada, nenhuma mensagem enviada, nenhum login.
- Nenhum link foi escrito de memória: todos os endereços do CSV e deste arquivo apareceram num resultado.

## Regra de dado pessoal

- O CSV não tem nome de pessoa nem @ em nenhuma coluna, inclusive nos endereços e títulos. Criadores aparecem pelo tipo ("humor corporativo", "carreira, RH e CLT", "finanças pessoais") e pelo porte só quando a fonte disse.
- Nomes de pessoa em títulos viraram "[nome omitido]".
- Quando o único endereço achado tinha nome de pessoa (por exemplo, o nome de uma celebridade na URL da matéria), o link foi omitido e a coluna traz o veículo e o mês para achar a matéria: iFood Benefícios, Cambly, Vivo, MadeiraMadeira, Alura, Google (Gemini), C6 Bank, Banco do Brasil e Nubank. A entrevista do blog da Flash com uma criadora de humor corporativo (fonte do caso Cambly e da citação de Nestlé, Elma Chips e Buser) ficou fora pelo mesmo motivo, porque o endereço tem o nome da criadora.
- Esta lista de buscas também troca nomes de pessoa por marcadores.

## Como li cada resultado

- **confirmado no trecho:** o fato veio no resultado com referência clara àquele veículo ou link, em geral com frase citada da matéria.
- **só no resumo da busca:** o fato apareceu no resumo gerado pela ferramenta, sem frase citada ou sem dizer de qual link saiu.
- **não verificado** (na coluna de data): o trecho não mostrou mês e ano. Quando o ano estava no título, a observação diz.
- **Títulos:** copiados como vieram. Alguns vêm sem acento, no formato do endereço. Quando o resultado trouxe só um título genérico ("ABC da Comunicação", "bpmoney.com.br"), a coluna diz "título pelo endereço".
- **Aderência à sátira corporativa:** alta = público CLT, RH ou PJ de escritório e produto do mundo do trabalho (benefícios, RH, PJ, ferramenta de trabalho, escritório); média = público amplo com gancho de trabalho ou dinheiro; baixa = pouca ligação com escritório.
- **Publi:** a imprensa fala em "ações com influenciadores", "creators", "squad" ou "parceria". Não há valores nem confirmação da etiqueta #publi nos posts. Linhas sem criador (Flash, WeWork) ou só com celebridade (Caju, Pluxee, Bradesco) ficaram por terem humor de escritório ou público muito próximo do Fred, e isso está dito na coluna tipo_criador.

## Buscas feitas (em ordem)

1. publi humor corporativo marca 2025 influenciador
2. campanha influenciadores humor corporativo banco digital 2025
3. branded content criador humor escritório fintech
4. Meio & Mensagem campanhas da semana marcas usam humor para falar de finanças
5. Nubank campanha influenciadores humor 2025
6. Conta Azul influenciadores campanha empreendedores
7. Caju benefícios influenciador humor campanha
8. Flash benefícios campanha creators influenciadores
9. VR benefícios campanha humor influenciador CLT
10. Caju "Benefícios que dão vontade de ser CLT" influenciadores redes sociais
11. Alura campanha influenciadores 2025
12. C6 Bank creators campanha influenciadores 2025
13. Inter banco campanha humor influenciador 2025
14. XP Investimentos creators humor campanha influenciadores
15. Omie influenciador campanha empreendedor 2025
16. "XP lança iniciativa de conteúdo para fortalecer relacionamento com creators"
17. Gupy campanha influenciadores humor recrutamento
18. iFood Benefícios campanha influenciador CLT
19. criador de conteúdo humor corporativo parceria marca publi Instagram (extended)
20. "humor corporativo" influenciador marcas campanha
21. criadora conteúdo "absurdos do mundo corporativo" humor marcas
22. influenciadores humor CLT trabalho escritório marcas contratam 2025 (extended)
23. flashapp.com.br humor corporativo influencer CLTfluencers Nestlé Cambly Elma Chips Buser
24. napratica.org.br influencers CLT creators dia a dia na firma conteúdo pago marcas
25. "Bater cartão e gravar reels" nano influenciadores CLT marcas
26. Flash "Comédias da Vida Corporativa" campanha ISLA creators
27. PicPay creators campanha influenciadores 2025 humor
28. Mercado Pago influenciadores campanha 2025 creators
29. Wise influenciadores Brasil campanha creators
30. Wise "Quem converte se diverte" Live the Agency data lançamento
31. [cantora] Mercado Pago campanha influenciadores TikTok data
32. Cora banco PJ influenciador campanha empreendedores
33. Wise Cia Barbixas "Quem Sabe Não Improvisa" campanha
34. Cora "O Mundo é de Quem Faz" campanha influenciadores maio
35. Stone campanha humor influenciadores empreendedores 2025
36. Itaú campanha creators humor influenciadores 2025
37. Bradesco campanha influenciadores humoristas 2025
38. Santander Brasil campanha creators influenciadores 2025 humor
39. Bradesco campanha universitários influenciadores TikTok Publicis comédia geração Z
40. Itaú creators "Feito com Você" campanha influenciadores 2025 2026
41. Banco do Brasil influenciadores humor campanha 2026
42. LinkedIn Brasil campanha creators influenciadores 2025
43. Microsoft Copilot campanha influenciadores Brasil trabalho humor
44. Google Gemini campanha creators Brasil trabalho escritório influenciadores
45. Descomplica pós-graduação campanha influenciadores humor 2025
46. Cambly campanha influenciadores Brasil inglês trabalho
47. Hotmart campanha creators influenciadores 2025
48. Flash blog entrevista humor corporativo influencer LinkedIn Instagram 50 milhões visualizações sete meses
49. "CLTfluencers" marcas publicidade
50. Buser campanha influenciadores humor 2025
51. Elma Chips campanha creators influenciadores 2025
52. Nescafé campanha influenciadores escritório trabalho 2025
53. Buser "Não viajar custa caro" excesso de trabalho campanha
54. Buser Member Get Member Oscar criadores humor [criadora] indicação
55. RD Station campanha influenciadores creators marketing 2025
56. Pipefy campanha humor influenciadores
57. Sólides campanha influenciadores RH humor 2025
58. Black Friday da Sólides anos 90 "Você decide" influenciadores
59. "Passa lá no RH" bloco de carnaval Sólides influenciadores
60. Sólides influenciadora humor corporativo campanha Black Friday [criador]
61. Sólides "seu time joga fácil" Mineirão campanha ações com influenciadores março 2026
62. Faria Lima humor marca parceria influenciador campanha
63. campanha humor home office influenciadores marca 2025 trabalho remoto
64. campanha "segunda-feira" humor trabalho influenciadores marca 2025
65. Daki [personagem] "Chief Faria Lima Officer"
66. WeWork aposta no humor segurança escritórios compartilhados campanha
67. WeWork Brasil influenciador creators campanha 2025
68. influencer viraliza ao satirizar executivos do mercado financeiro Faria Lima parceria marcas publi
69. personagem farialimer humorista campanha marca 2025 2026
70. Alelo campanha influenciadores 2025
71. Ticket benefícios Edenred campanha influenciadores humor 2025
72. Pluxee Brasil campanha influenciadores creators
73. Alelo "Cria" escola de influenciadores nicho corporativo RH CLT
74. Pluxee "Benefício de Verdade" [humorista] R$ 10 milhões Oribá data
75. Alelo Sotaq marketing de influência RFP creators
76. Pluxee campanha [humorista] cinco personagens motoboy [personagem]
77. Inter "tirando leite de pedra" Meu Porquinho filme Talent O2 data
78. Swile Brasil campanha influenciadores humor trabalho
79. Wellhub campanha influenciadores Brasil 2025 bem-estar corporativo
80. TotalPass campanha influenciadores humor 2025
81. TotalPass "Não aceite nada menos que o Total" puxa-saco fofoqueiro escritório campanha data
82. Swile 2025 campanha influenciadores creators benefícios
83. Wellhub "Friends with corporate benefits" campanha
84. "Swile aposta na Creator Economy" influenciadores parceiros de negócio
85. Wellhub [apresentador] [criadora de finanças] embaixadores campanha Resoluções Euphoria data
86. TotalPass "faz total sentido" influenciadores março 2025 primeira campanha B2C
87. Neon banco campanha influenciadores 2025 humor
88. PagBank campanha influenciadores creators 2025
89. Nomad conta internacional campanha influenciadores humor 2025
90. Neon Viracrédito [humorista] esquetes humor Instagram TikTok On The Nose
91. "Neon se coloca como parceira financeira do brasileiro trabalhador"
92. Porto Seguro campanha influenciadores humor 2025
93. seguradora campanha humoristas influenciadores 2025 seguro de vida creators
94. Vivo campanha creators humor 2025 influenciadores trabalho
95. TIM campanha influenciadores humor 2025 creators
96. Claro campanha influenciadores humoristas 2025 2026
97. Claro empresas campanha pequenas empresas influenciadores empreendedores
98. TIM ativa 1.300 creators 14 praças TIM Controle BrandLovers data
99. "TIM converte creators em parceiros de longo prazo"
100. FGV Insper MBA campanha influenciadores 2025 educação executiva creators
101. G4 Educação influenciadores parceria campanha 2025
102. escola de inglês campanha humoristas influenciadores 2025 inglês para o trabalho
103. G4 Educação campanha "NaaaH" humor Liderança de Alta Performance influenciadores
104. Wise Up Fluency Open English campanha influenciadores 2025
105. Duolingo Brasil campanha creators humor 2025
106. Duolingo Brasil Jotacom Copa 2026 ofensivas influenciadores campanha junho
107. Duolingo exalta cultura do Norte ação influenciadores locais COP30
108. Contabilizei campanha influenciadores humor empreendedores 2025
109. TOTVS campanha influenciadores creators 2025
110. Bling ERP campanha influenciadores empreendedores e-commerce 2025
111. "Tem no Bling" campanha LWSA filmes maio outubro ano lançamento
112. Pipedrive HubSpot Brasil campanha influenciadores vendas humor
113. Notion Canva Brasil creators parceria campanha produtividade trabalho 2025
114. Notion chega ao Brasil comunidade criadores embaixadores presença digital data
115. Canva IA 2.0 campanha Brasil influenciadores maio 2026 empreendedor
116. Samsung Galaxy AI campanha influenciadores Brasil produtividade trabalho humor

Recusadas pelo limite de buscas (não rodaram): "Uber campanha influenciadores humor Brasil 2025 creators", "99 app campanha influenciadores humor 2025 99Pop", "Sem Parar Veloe ConectCar campanha influenciadores humor 2025".

## O que foi descartado e por quê

- **Fora do Brasil:** ActivoBank e Worten (Portugal), Nescafé na Espanha (ação no TikTok com quem trabalha de madrugada), Microsoft Copilot (influenciadores nos EUA), Coors Light (EUA), programa de criadores da HubSpot no LinkedIn (global).
- **Só exemplos antigos, sem nada de 2025–2026:** Santander (2021–2022), Claro (2020–2022), Porto Seguro (2021–2022), Neon (esquetes de humor em nov/2023), Caixa (2023), English Live (2017), EF (sem data), Open English (2024, sem influenciador), Red Bull "Dia do Meio Período" (2021), Americanas Empresas (2021), MetLife e Liberty Seguros (2022 ou sem data), Will Bank e Itaipava (sem data).
- **Sem criador nem influenciador achado:** Conta Azul (novo posicionamento em jul/2025, sem criador), Omie, TOTVS, Contabilizei, Pipefy, Pipedrive, Notion (chegada ao Brasil sem campanha com criadores), Nomad (humor sem criador), PagBank (2026, com apresentador de TV), VR, Ticket, Wise Up (2025, sem influenciador), FGV e Insper, Samsung (oficinas do programa de creators, sem data), LinkedIn (#JuntosNessa, sem ano), Gupy (crise de reputação em 2024, sem campanha).
- **Dado conflitante ou fraco:** Black Friday da Sólides com criadores de humor (uma busca disse 2025; outra mostrou matéria de nov/2023 sem influenciador; ficou de fora), Buscopan com humorista (link e data incertos), LATAM Pass com sátira de dublagem (sem link e sem data).
- **Fora do foco do Fred:** moda e varejo (Lupo, Usaflex, Amaro, Morana), limpeza (Cif no BBB 26), construção (Vedacit), Shell Select e Kasinski (humorista, sem data), Copel Telecom (sem data), ARQ/DolarApp (vaga para criador interno, não é publi), QuintoAndar e Globoplay (citadas numa matéria sobre criadora que voltou à CLT, sem nicho e sem data).
- **Não é marca:** a matéria do Jornal Opção sobre um perfil anônimo que satiriza executivos do mercado financeiro (talvez o próprio Fred) não cita nenhuma marca: https://www.jornalopcao.com.br/ultimas-noticias/saiba-quem-e-o-influencer-que-viraliza-ao-satirizar-executivos-do-mercado-financeiro-770931/

## Limitações

- Nenhuma página foi aberta (WebFetch bloqueado). O resumo da ferramenta de busca às vezes mistura matérias, então datas e detalhes podem ter erro, e as linhas "só no resumo da busca" pedem conferência antes de virar argumento comercial.
- O limite de buscas acabou antes de cobrir alguns setores: mobilidade corporativa (Uber, 99, locadoras, tags de pedágio), coworking além do WeWork (IWG/Regus), cartões corporativos (Clara, Conta Simples), cafés e energéticos (3 Corações, Pilão, Nespresso, Red Bull, Monster), saúde corporativa (Alice, SulAmérica, Amil) e mais marcas de RH (Convenia, Factorial, Feedz).
- Viés de imprensa: só aparece o que virou notícia. Publis pequenas, fechadas direto com perfis de humor corporativo, quase nunca viram matéria, então a lista subestima marcas médias que pagam publi direto ao criador.
- A única fonte sobre marcas que procuraram uma criadora de humor corporativo (Nestlé, Cambly, Elma Chips, Buser) é uma entrevista sem data no blog da Flash; trata-se de propostas recebidas, não de publis confirmadas.
- "Confirmado no trecho" quer dizer que o fato veio no resultado da busca, não que a página foi lida inteira.

## Próximos passos sugeridos (nova rodada de buscas)

- Cobrir os setores que ficaram de fora (lista acima).
- Conferir a data das linhas "não verificado" com mais peso no top 15: Buser, Swile, Pluxee, Cambly, Nescafé.
- Abrir as matérias quando houver acesso (WebFetch ou navegador) para confirmar formato, criadores e datas das linhas "só no resumo da busca", começando por iFood Benefícios e Stone.
