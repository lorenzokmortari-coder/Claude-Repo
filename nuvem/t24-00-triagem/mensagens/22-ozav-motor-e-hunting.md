Para 13 · Ozav · Motor e CRM (DNS e script) e 16 · Ozav · Hunting (aquecimento e conteúdo) · entrega 22 · prioridade 2

Artifact: "Nuvem · Ozav · e-mail frio sem cair no spam" https://claude.ai/artifact/5xoQBMR4sW79nBwktfVgKx

No PC:
```
pip install dnspython pytest
python -m pytest -q test_conferir_dominio.py   # 33 ok
python conferir_dominio.py <dominio-novo> --seletor <seletor> --bimi
```

**Antes do primeiro e-mail frio:**
- SPF;
- DKIM de 2048 bits;
- DMARC com `rua`;
- descadastro em um clique (RFC 8058), honrado em 48 h;
- spam abaixo de 0,1%.

O Gmail rejeita o que não cumpre desde nov/2025.

**Hunting:** 4 semanas de aquecimento (`plano-aquecimento.csv`). Depois, até 40 por dia por caixa; para crescer, mais caixas.

**Decidir:**
- quantas caixas;
- se usa ferramenta de aquecimento;
- a LIA e o aviso de privacidade.

**Só com dado real:**
- o DNS do domínio novo;
- o Postmaster depois da semana 2;
- quantos e-mails da lista são corporativos.

O Microsoft 365 corporativo não foi pesquisado.
