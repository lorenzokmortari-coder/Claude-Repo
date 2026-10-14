/**
 * HOOKS DO CLAUDE CODE (tarefa 16 da nuvem, 14/10/2026): os patches 01 a 05, provados numa pasta temporária.
 *
 *   node --test testes/hooks.test.js      (da raiz do pacote "Setup · Claude Code"; node 18+ e bash; ~5 s)
 *
 * Cada teste Hxx monta um HOME, um APPDATA e um OneDrive\Claude de mentira e roda o hook como o Claude Code roda
 * (JSON na entrada padrão). H01–H05 falham no código de 14/10/2026 e passam com o patch de mesmo número.
 * H00 é a prova do que já está robusto (acento e espaço no caminho, config corrompido, 300 sessões no app).
 */
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const PACOTE = path.join(__dirname, '..');
const CONVERSA = path.join(PACOTE, 'hooks', 'automacao', 'estado', 'conversa.js');
const NONSTOP = path.join(PACOTE, 'hooks', 'claude-hooks', 'nonstop.sh');
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'hooks-'));
test.after(() => fs.rmSync(TMP, { recursive: true, force: true }));
let n = 0;
const escrever = (p, txt) => {
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, txt);
};

// ------------------------------------------------------------------ nonstop
function nonstop(home, entrada, extraPath) {
  const PATH = (extraPath ? extraPath + path.delimiter : '') + process.env.PATH;
  return spawnSync('bash', [NONSTOP], { input: JSON.stringify(entrada), env: { PATH, HOME: home }, encoding: 'utf8' });
}
const bloqueou = (r) => /"decision":"block"/.test(r.stdout);
// o "python" do PATH é o atalho da Microsoft Store: não roda, não imprime nada
function pythonDaStore() {
  const d = path.join(TMP, `store-${++n}`);
  for (const nome of ['python', 'python3']) escrever(path.join(d, nome), '#!/bin/bash\nexit 9009\n');
  for (const nome of ['python', 'python3']) fs.chmodSync(path.join(d, nome), 0o755);
  return d;
}

test('H01 nonstop ligado numa conversa nao segura a parada das outras, e a trava contra laco vale, mesmo sem python', () => {
  const home = path.join(TMP, `home-${++n}`);
  const estado = path.join(home, '.claude', 'hooks', 'state');
  fs.mkdirSync(estado, { recursive: true });
  const store = pythonDaStore();
  // a conversa A liga o modo (o handshake do plugin): a primeira parada dela e segurada
  fs.writeFileSync(path.join(estado, 'nonstop.activate'), '');
  const a = nonstop(home, { session_id: 'aaaa-1111', stop_hook_active: false }, store);
  assert.equal(a.status, 0, a.stderr);
  assert.ok(bloqueou(a), 'a conversa que ligou o modo tem de ser segurada');
  // a conversa A ja foi cutucada nesta volta: tem de poder parar (senao laco)
  const a2 = nonstop(home, { session_id: 'aaaa-1111', stop_hook_active: true }, store);
  assert.ok(!bloqueou(a2), 'stop_hook_active=true foi ignorado: a trava contra laco morreu (o python nao rodou)');
  // outra conversa fixa, que nunca ligou o modo
  const b = nonstop(home, { session_id: 'bbbb-2222', stop_hook_active: false }, store);
  assert.ok(!bloqueou(b), `a conversa B foi segurada pelo modo da A; estado: ${fs.readdirSync(estado).join(', ')}`);
});

// ------------------------------------------------------------------ conversa.js
function montar({ pasta = 'pc', titulo = '07 · Teste · Conversa', estado07, sessoes = 0, comHost = true } = {}) {
  const base = path.join(TMP, `${pasta}-${++n}`);
  const home = path.join(base, 'home');
  const appdata = path.join(home, 'AppData', 'Roaming');
  const raiz = path.join(base, 'OneDrive', 'Claude');
  const script = path.join(raiz, 'automacao', 'estado', 'conversa.js');
  escrever(script, fs.readFileSync(CONVERSA));
  fs.copyFileSync(path.join(path.dirname(CONVERSA), 'config.json'), path.join(raiz, 'automacao', 'estado', 'config.json'));
  escrever(path.join(raiz, 'ORQUESTRACAO.md'), '# mapa\n\n## 4 · papeis\n\n### 07 · Teste · Conversa\n```\nPAPEL-DA-07: cuida do teste.\n```\n');
  escrever(path.join(raiz, 'ESTADO.md'), '# Estado\n**Última atualização:** 14/10/2026\n\n## Agora\n- nada\n');
  if (estado07 !== undefined) escrever(path.join(raiz, 'conversas', '07.md'), estado07);
  const dir = path.join(appdata, 'Claude', 'claude-code-sessions', 'conta-1', 'org-1');
  fs.mkdirSync(dir, { recursive: true });
  for (let i = 0; i < sessoes; i++) {
    escrever(path.join(dir, `local_${String(i).padStart(4, '0')}.json`), JSON.stringify({ cliSessionId: `outra-${i}`, title: `${String(i % 50).padStart(2, '0')} · Outra` }));
  }
  const sessao = path.join(dir, comHost ? 'host-07.json' : 'local_zzzz.json');
  escrever(sessao, JSON.stringify({ cliSessionId: 'cli-07', title: titulo }));
  const env = { PATH: process.env.PATH, HOME: home, USERPROFILE: home, APPDATA: appdata, CLAUDE_CODE_SESSION_ATTENDED: '1' };
  if (comHost) env.CLAUDE_CODE_HOST_SESSION_ID = 'host-07';
  return { raiz, script, home, sessao, env };
}
function rodar(m, arg, entrada) {
  const r = spawnSync(process.execPath, [m.script, arg], { input: JSON.stringify({ cwd: m.raiz, session_id: 'cli-07', ...entrada }), env: m.env, encoding: 'utf8' });
  assert.equal(r.status, 0, r.stderr);
  if (!r.stdout.trim()) return '';
  return JSON.parse(r.stdout).hookSpecificOutput.additionalContext;
}

test('H02 o aviso dos 100 mil tokens sai mesmo com o usage do transcript em outra ordem de chaves', () => {
  const m = montar({ estado07: '# 07\n' });
  const linha = (u) => JSON.stringify({ type: 'assistant', isSidechain: false, message: { model: 'm', id: 'x', usage: u } });
  const transcript = path.join(TMP, `t-${++n}.jsonl`);
  // a ordem de hoje: funciona antes e depois
  fs.writeFileSync(transcript, [linha({ input_tokens: 5, cache_creation_input_tokens: 20000, cache_read_input_tokens: 90000, output_tokens: 9 })].join('\n') + '\n');
  assert.match(rodar(m, '--medir', { transcript_path: transcript }), /CONTEXTO EM ~110 MIL TOKENS/);
  // a mesma conta, chaves em outra ordem (outra versao do app, outro provedor)
  fs.writeFileSync(transcript, [linha({ cache_read_input_tokens: 90000, input_tokens: 5, output_tokens: 9, cache_creation_input_tokens: 20000 })].join('\n') + '\n');
  assert.match(rodar(m, '--medir', { transcript_path: transcript }), /CONTEXTO EM ~110 MIL TOKENS/, 'com outra ordem de chaves o hook leu 0 tokens e nao avisou');
  // abaixo do limite continua calado
  fs.writeFileSync(transcript, linha({ input_tokens: 5, cache_creation_input_tokens: 0, cache_read_input_tokens: 1000 }) + '\n');
  assert.equal(rodar(m, '--medir', { transcript_path: transcript }), '');
});

test('H03 estado acima do teto: a "Ultima entrega" entra inteira (no 00.md real sobravam 92 de 245 caracteres)', () => {
  // como o 00.md de 14/10: 3.908 caracteres de secoes e a "Ultima entrega" por ultimo
  const corpo = '# 07 · Teste — estado da conversa\n\n## Foco\n' + 'x'.repeat(3850) + '\n\n';
  const entrega = '## Última entrega\n- 14/10 manhã: ' + 'e'.repeat(190) + ' FIM-DA-ENTREGA\n';
  let m = montar({ estado07: corpo + entrega });
  let out = rodar(m, '--abrir', {});
  assert.match(out, /PAPEL-DA-07/);
  assert.match(out, /FIM-DA-ENTREGA/, 'o corte levou o fim da "Ultima entrega"');
  assert.match(out, /\[cortado: o arquivo passou do teto/);
  // na ordem do molde da /limpa (a entrega no meio, "Cuidado" e "Onde esta o resto" depois)
  m = montar({ estado07: '# 07\n\n## Foco\n' + 'f'.repeat(2500) + '\n\n' + entrega + '\n## Cuidado\n' + 'c'.repeat(1500) + '\n\n## Onde está o resto\n- caminhos\n' });
  out = rodar(m, '--abrir', {});
  assert.match(out, /FIM-DA-ENTREGA/);
  // abaixo do teto nada muda
  m = montar({ estado07: '# 07\n\n## Foco\ncurto\n\n' + entrega });
  out = rodar(m, '--abrir', {});
  assert.ok(out.includes('## Foco\ncurto\n\n## Última entrega') && !/cortado/.test(out));
});

test('H04 o app gravando o json da sessao na hora da abertura nao faz a conversa perder o estado', () => {
  const m = montar({ estado07: '# 07\n\n## Foco\nESTADO-DA-07\n' });
  assert.match(rodar(m, '--abrir', {}), /ESTADO-DA-07/, 'leitura normal');
  // o app esta regravando o arquivo: meio JSON
  fs.writeFileSync(m.sessao, '{"cliSessionId":"cli-07","title":"07 · Te');
  const out = rodar(m, '--abrir', {});
  assert.match(out, /ESTADO-DA-07/, `sem titulo o estado nao entrou; o hook injetou:\n${out.slice(0, 400)}`);
  assert.match(out, /PAPEL-DA-07/);
});

test('H00 (ja robusto) acento e espaco no caminho, config corrompido, conversa sem estado e 300 sessoes no app', () => {
  const m = montar({ pasta: 'Área de Trabalho/One Drive', sessoes: 300, comHost: false });
  fs.writeFileSync(path.join(path.dirname(m.script), 'config.json'), '{ "limite_tokens": 100');
  const t0 = Date.now();
  const out = rodar(m, '--abrir', {});
  const ms = Date.now() - t0;
  assert.match(out, /PAPEL-DA-07/);
  assert.match(out, /Ainda sem estado proprio/);
  assert.ok(out.includes(path.join(m.raiz, 'conversas', '07.md')), 'o caminho com acento e espaco tem de sair inteiro');
  assert.ok(ms < 3000, `abrir levou ${ms} ms (o timeout do hook e 10 s)`);
  // fora de sessao atendida (tarefa agendada) nao injeta nada
  m.env.CLAUDE_CODE_SESSION_ATTENDED = '0';
  assert.equal(rodar(m, '--abrir', {}), '');
});

test('H05 o Bash nao le as pastas que o settings.json nega para o Read (chaves, cliente da Veedha, financas)', () => {
  const guarda = path.join(PACOTE, 'hooks', 'automacao', 'guarda', 'guarda.js');
  assert.ok(fs.existsSync(guarda), 'nao ha guarda: o deny so vale para o Read, e o Bash(cat:*) esta liberado');
  const roda = (command) => spawnSync(process.execPath, [guarda], { input: JSON.stringify({ tool_name: 'Bash', tool_input: { command } }), encoding: 'utf8' });
  for (const c of [
    'cat C:/Users/x/veedha-dados/clientes.csv',
    'type C:\\Users\\x\\.ozav\\.env',
    'ssh -i k claude-motor@<IP_VPS> "grep -c = ~/.ozav/.env"',
    'head ~/financas/originais/extrato.ofx',
    'powershell Get-Content "C:\\Users\\x\\financas\\originais\\fatura.pdf"',
  ]) {
    const r = roda(c);
    assert.equal(r.status, 2, `passou: ${c}`);
    assert.match(r.stderr, /Bloqueado pela guarda/);
  }
  for (const c of ['node coletar.js --dia', 'cat ozav-crm/README.md', 'ls ~/ozav-marketing/estado', 'grep -rn ozav projetos/ozav/crm']) {
    assert.equal(roda(c).status, 0, `barrou sem motivo: ${c}`);
  }
  assert.equal(spawnSync(process.execPath, [guarda], { input: 'nao e json', encoding: 'utf8' }).status, 0, 'entrada ilegivel deixa passar');
});
