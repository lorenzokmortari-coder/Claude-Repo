# Para a 00 · 26 · Nuvem · Ozav · esteira mensal de prospecção

**O que é:** `esteira.py`, um comando só: Receita → filtro de ICP (`icp.ini`) → site → nota → `top1000.csv`, `novidades.md`, `crm.jsonl`. Não escreve no CRM nem manda mensagem.
**Status:** completo, com 36 testes verdes (14 novos). Nada rodou com dado real.
**Comando (PC):**
```
pip install duckdb requests selectolax phonenumbers pandas pytest
python -m pytest -q
python esteira.py --mes 2026-10 --fonte-local <pasta dos zips>
```
**Dona:** 16 · Ozav · Hunting. **Prioridade:** 2.
**Só com dado real:** tempo da rodada, cobertura de site, falso positivo da exclusão por nome.

**MENSAGEM PRONTA**
Artifact "Nuvem · Ozav · esteira mensal de prospecção". Junta pipeline CNPJ v2, enriquecer site e vigia de concorrentes.
1. Copie esteira/ para uma pasta e rode `python -m pytest -q` (36 verdes, 2 pulados).
2. Rode `python esteira.py --mes 2026-10 --fonte-local <zips de 2026-10>`. A saída sai em saida/2026-10/esteira/. Se cair, rode o mesmo comando: ele retoma.
3. Confira três coisas: excluidos.csv (quem saiu como concorrente), o motivo das 20 primeiras do top1000.csv e o crm.jsonl antes de subir.
Para decidir: os pesos 0,7 CNPJ / 0,3 site; quantos candidatos vão ao site (1.500); se o ritmo de 1 pedido/s é por domínio (padrão) ou no total (workers = 1).
