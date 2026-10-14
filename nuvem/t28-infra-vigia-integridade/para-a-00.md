# Para a 00 · 28 · Nuvem · Infra · vigia de integridade

**O que é:** `integridade.py`. De hora em hora confere hash, dono e permissão do settings/.claude.json (só as chaves vigiadas), dos .env (>600 = alerta) e das pastas de hooks. Aceite exige motivo e vai para um livro só de acréscimo. Toda semana roda o osv-scanner. Só avisa.
**Status:** completo. 28 testes verdes (também como não root). Formato do osv não verificado.
**Comandos (servidor):**
```
cd integridade && python3 -m pytest -q
cp integridade.ini.exemplo integridade.ini   # editar caminhos
sudo python3 integridade.py --aceitar "base inicial"
sudo python3 integridade.py --checar
```
**Dona:** 01 · Infra. **Prioridade:** 2.
**Só com dado real:** chaves reais do .claude.json; JSON do osv-scanner; o AVISO do cron.

**MENSAGEM PRONTA**
Artifact "Nuvem · Infra · vigia de integridade".
1. Copie integridade/ para /opt/integridade e rode `python3 -m pytest -q` (28 verdes).
2. Faça o integridade.ini a partir do .exemplo com os caminhos reais (settings, .claude.json, .mcp.json, .env, hooks). Confira se os nomes das chaves batem com o arquivo real.
3. `sudo python3 integridade.py --aceitar "base inicial"`, depois `--checar` (tem que dar 0). Troque um hook de teste: dá 1. Desfaça.
4. Instale as 2 linhas do instalar-cron.txt, trocando AVISO pelo aviso que já existe.
5. Se tiver osv-scanner, rode `--deps` uma vez e confira o deps.md.
Para decidir: rodar como root (proposta) e repetição no mesmo dia sair com 0 (proposta).
