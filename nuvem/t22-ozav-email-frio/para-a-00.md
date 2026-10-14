# Para a 00 · tarefa 22 · Nuvem · Ozav · e-mail frio sem cair no spam

**O que é:**
- as regras de 2025–2026 do Gmail, do Yahoo e da Microsoft: SPF, DKIM de 2048, DMARC, um clique, 48 h, spam abaixo de 0,1%; o Gmail rejeita o que não cumpre desde nov/2025;
- conteúdo e LGPD (legítimo interesse, LIA, opção de sair);
- `conferir_dominio.py`, com 33 testes;
- o plano de aquecimento de 4 semanas.

**Status:** completo no código. A pesquisa veio de trecho do buscador, porque as páginas oficiais estavam bloqueadas. A filtragem do Microsoft 365 corporativo, que é onde está o público B2B, não foi pesquisada.

**Comandos (no PC):**
```
pip install dnspython pytest
python -m pytest -q test_conferir_dominio.py
python conferir_dominio.py <dominio-novo> --seletor <seletor> --bimi
```

**Donas:**
- 13 · Ozav · Motor e CRM (DNS e script);
- 16 · Ozav · Hunting (aquecimento e regras de conteúdo).

**Prioridade:** 2. Fazer antes do primeiro e-mail frio do domínio novo.

**Decidir:**
- quantas caixas (25 a 30 frios por dia em cada uma, depois do aquecimento);
- se usa ferramenta de aquecimento;
- a LIA e o aviso de privacidade.

**Só com dado real:**
- o DNS do domínio novo (rodar o script);
- o Postmaster Tools depois da semana 2;
- quantos e-mails da lista são corporativos e verificados.
