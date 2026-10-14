# E-mail frio sem cair no spam: as regras de 2025–2026 (Ozav, 14/10/2026)

**Como foi verificado:** nenhuma página oficial abriu nesta rede (Google, Yahoo, Microsoft, gov.br, Planalto, RFC Editor, IETF). Tudo saiu do trecho que o buscador mostrou para a URL citada. Marcas:
- **[TB]:** trecho do buscador;
- **[NV]:** não verificado;
- **[CONFLITO]:** as fontes divergem.

URLs e detalhes em `pesquisa.md`.

## 1. O que os grandes provedores exigem

| Requisito | Gmail | Yahoo | Microsoft (Outlook.com de consumidor) |
|---|---|---|---|
| Quem é "remetente em volume" | perto de 5.000 por dia para contas pessoais Gmail, somando o domínio principal [TB] | sem limiar numérico nos trechos [NV] | 5.000 ou mais por dia, mesmo domínio no From [TB] |
| SPF | todos: SPF ou DKIM; volume: SPF e DKIM [TB] | idem [TB] | volume: SPF passa [TB] |
| DKIM | chave de 1024 bits ou mais, **2048 recomendada** [TB] | mínimo de 1024 bits [TB] | DKIM passa [TB] |
| DMARC | volume: publicado, p=none aceito [TB] | p=none ou mais; rua "fortemente recomendado" [TB] | p=none no mínimo; "p=reject is recommended" [TB] |
| Alinhamento | From alinhado com SPF ou DKIM [TB] | idem, relaxado aceito [TB] | ao menos um alinhado, "de preferência os dois" [TB] |
| PTR, rDNS, TLS | PTR que resolve de volta (FCrDNS); TLS [TB] | DNS direto e reverso válidos [TB]; TLS [NV] | rDNS válido [TB] |
| Cancelamento em um clique | volume, marketing: List-Unsubscribe + List-Unsubscribe-Post (RFC 8058), desde 01/06/2024; link mailto no corpo não basta [TB] | List-Unsubscribe funcional, POST "highly recommended", link no corpo [TB] | recomenda descadastro visível [TB] |
| Honrar descadastro | **48 h** [TB] | **2 dias** [TB] | [NV] |
| Taxa de spam | **abaixo de 0,10%, nunca 0,30%** (Postmaster) [TB] | abaixo de 0,3% [TB] | [NV] |
| Endurecimento | **desde nov/2025**, rejeição temporária e permanente para o que não cumpre; domínio novo em calendário acelerado [TB] | gradual em 2024 [TB] | desde 05/05/2025, Lixo Eletrônico; rejeição 550 5.7.515 documentada, mas a data de início não foi confirmada [CONFLITO] |

**Pontos de escopo:**
- As regras da Microsoft acima são do **Outlook.com de consumidor**. O público B2B da Ozav está mais no **Microsoft 365 corporativo**, cuja filtragem (EOP) não foi pesquisada [NV].
- A RFC 8058 exige assinatura DKIM cobrindo os dois cabeçalhos do List-Unsubscribe, e o clique é um HTTPS POST sem cookie nem redirecionamento [TB].

**Leitura para a Ozav:** o domínio separado não vai passar de 5.000 por dia, mas vale cumprir o pacote de volume desde o primeiro dia (SPF e DKIM de 2048 alinhados, DMARC com rua, um clique, 48 h). Domínio novo tem tolerância menor.

## 2. Conteúdo e link

| O que | Fonte oficial | Fornecedor e comunidade |
|---|---|---|
| Link | visível e compreensível; o destinatário sabe o que vai abrir (Google) [TB] | muitos links levantam suspeita [TB] |
| HTML e imagem | HTML dentro do padrão; nada de esconder conteúdo com CSS; nada de emoji imitando selo (Google) [TB] | imagem tende a piorar a entrega [TB] |
| Pixel de abertura | nada oficial [NV] | atrapalha, sobretudo em domínio de rastreamento compartilhado [TB] |
| Rastreamento de clique | o domínio do link não entra no alinhamento [TB] | desligar, ou usar domínio de rastreamento próprio [TB] |
| Anexo | nada oficial [NV] | anexo de desconhecido parece malware [TB] |
| Palavras-gatilho | nada oficial [NV] | **em grande parte mito**: pesam reputação, engajamento e autenticação [TB] |

**Prática para o frio:** texto simples, 0 ou 1 link do próprio domínio, sem anexo, sem imagem, sem pixel.

## 3. LGPD no e-mail frio B2B

| Dispositivo | O que diz | Verif. |
|---|---|---|
| Art. 7º, IX | legítimo interesse do controlador, salvo se prevalecerem direitos do titular | [TB] |
| Art. 10, caput e I | só para finalidade legítima, a partir de situação concreta; inclui "apoio e promoção de atividades do controlador" | [TB] |
| Art. 10, §1º | só os dados "estritamente necessários" | [TB] |
| Art. 10, §2º | medidas de transparência | [TB] |
| Art. 37 | registro das operações, "especialmente" no legítimo interesse | [TB parcial] |
| Art. 18, §2º | direito de oposição; a ANPD lê de forma ampla | [TB] |
| Guia de legítimo interesse da ANPD (fev/2024) | teste de balanceamento em 3 fases (finalidade, necessidade, balanceamento e salvaguardas), por finalidade; o modelo não é obrigatório | [TB]; [CONFLITO] sobre o dia (02 ou 15/02) |
| Prospecção B2B por e-mail | **nenhuma manifestação da ANPD encontrada** | [NV] |
| CAPEM (autorregulação de 2009, voluntária) | **proíbe "o primeiro envio para se obter a permissão"**, o que colide com o frio clássico; não é lei | [TB] |
| CDC, art. 43, §2º | cadastro não solicitado comunicado por escrito; o MPMG aplicou fora de crédito em 2024; para B2B o risco é baixo, mas existe (art. 29) | [TB] / leitura |

**Como cumprir (leitura, não orientação oficial):**
1. LIA escrita e datada para "prospecção de câmbio para empresas".
2. Só nome, cargo, empresa e e-mail corporativo. E-mail pessoal (gmail.com e outros) fica fora.
3. Origem de cada contato registrada (fonte, data, base legal).
4. Primeiro e-mail com quem é a Ozav, por que o contato, de onde veio o dado, link do aviso de privacidade e canal do encarregado.
5. Opção de sair em todo e-mail (um clique e link no corpo), supressão permanente honrada em até 48 h.
6. Revisar a LIA a cada trimestre.

**Decisão do dono que não se repropõe:** nada de raspar LinkedIn nem de prospectar pelo perfil pessoal do Lorenzo. A lista vem das bases que a Ozav já usa (por exemplo, a lista quente de CNPJ da tarefa 1).

## 4. BIMI (opcional)

- Gmail: DMARC em quarantine ou reject com **pct=100**; certificado VMC (marca registrada) ou CMC; logo SVG Tiny PS de 96 px ou mais e até 32 KB [TB].
- O padrão ainda é rascunho na IETF [TB].
- **Leitura:** para domínio de prospecção, o ganho é só visual. Deixar para depois que o domínio estiver estável. O `conferir_dominio.py --bimi` diz o que falta.
