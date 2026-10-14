# conferir_dominio.py: o DNS do domínio de prospecção

Confere SPF, DKIM, DMARC, MX e, se pedido, BIMI de um domínio, e diz o que falta. Só lê DNS público: não manda e-mail, não abre conexão SMTP e não usa conta nenhuma.

## Instalar e rodar (no PC)

```
pip install dnspython
python conferir_dominio.py dominio-de-prospeccao.com.br --seletor google
python conferir_dominio.py dominio-de-prospeccao.com.br --seletor s1 --seletor s2 --bimi
python conferir_dominio.py dominio-de-prospeccao.com.br --envelope bounce.dominio-de-prospeccao.com.br --json
```

- **Sem `--seletor`:** tenta os seletores DKIM mais comuns (google, selector1, selector2, default, k1, s1, s2 e outros). O seletor certo aparece no `s=` do cabeçalho DKIM-Signature de um e-mail enviado.
- **`--envelope`:** o domínio do Return-Path da ferramenta de envio. Confere se ele alinha com o From.
- **Código de saída:** 1 se houver FALTA ou ERRO; 0 se o DNS estiver completo.

## O que ele confere

| Item | FALTA quando | ATENÇÃO quando |
|---|---|---|
| SPF | não há registro, há mais de um, termina em `+all`, passa de 10 consultas de DNS ou de 2 consultas vazias (RFC 7208, 4.6.4) | termina em `?all` ou sem `all`; usa `ptr` |
| DKIM | não há chave no seletor pedido; `p=` vazio (revogada); chave RSA abaixo de 1024 bits; base64 quebrado | chave de 1024 bits (o recomendado é 2048); `t=y`; ed25519 sozinha |
| DMARC | não há registro; há mais de um; política inválida | `p=none`; `pct` abaixo de 100; sem `rua`. Subdomínio sem registro herda do domínio organizacional, e vale o `sp=` |
| MX | MX nulo (`0 .`, RFC 7505) | sem MX (respostas e devoluções não chegam) |
| BIMI (com `--bimi`) | — | DMARC fora de quarantine ou reject com pct=100; sem certificado (`a=`); logo fora de SVG em https |
| Alinhamento (com `--envelope`) | o Return-Path é de outro domínio organizacional | — |
| DNS da máquina | **ERRO** se o DNS não acha nem o MX de gmail.com. Rede que bloqueia DNS devolve "não existe" para tudo, e o relatório culparia o domínio | — |

O DNS não mostra o alinhamento do DKIM (`d=`). Para conferir de ponta a ponta, mande um e-mail de teste para uma caixa Gmail e abra "Mostrar original": SPF, DKIM e DMARC têm de dar PASS, e o DKIM tem de ter `d=` igual ao seu domínio.

## Testes

```
pip install dnspython pytest
python -m pytest -q test_conferir_dominio.py      # 33 testes, resolvedor falso, nenhuma consulta à rede
```

Os testes montam uma zona falsa e cobrem:
- domínio completo;
- DMARC ausente, duplicado, `p=none`, sem `rua`, `pct` parcial e herdado do domínio organizacional (.com.br);
- SPF ausente, duplicado, `+all`, `?all`, mais de 10 consultas, include inexistente e laço de include;
- chaves DKIM de 512, 1024, 2048 e 4096 bits (o tamanho é lido do DER da chave), revogada, `t=y`, seletor ausente e busca nos seletores comuns;
- MX ausente e nulo;
- timeout;
- BIMI;
- alinhamento do Return-Path;
- saída JSON e código de saída;
- a rede que desvia DNS.

**Limite desta nuvem:** aqui o DNS de saída devolve "não existe" para tudo (até gmail.com), então o script só rodou com o resolvedor falso. No PC ele consulta o DNS de verdade.
