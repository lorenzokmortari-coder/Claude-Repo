/**
 * TRIAGEM 00 (tarefa 24 da nuvem, 14/10/2026): o cruzamento das tarefas 15 e 18.
 *
 *   node --test testes/estado-do-governador.test.js     (da raiz do pacote "Infra · VPS", DEPOIS do aplicar/infra-vps.diff)
 *
 * O backup (patch 06 da 15) e a restauracao (patch 07 da 15) levam uma lista fechada do estado que so mora no servidor.
 * Ficaram fora dois arquivos que o codigo do envio chama de "estado do servidor, fora do deploy":
 *   - whatsapp-governador.json: o disjuntor (que o patch 01 da 18 arma no 463/restricao), a pausa e o aquecimento;
 *   - catraca-regras.json: as regras vivas da catraca, editadas no servidor.
 * Perdida a VPS, o governador volta ao PADRAO (lerEstado com ENOENT): disjuntor e aquecimento somem e o volume volta ao
 * normal no meio de uma restricao. Falha sem o patch extra e passa com ele.
 */
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');
const { DatabaseSync } = require('node:sqlite');

const PACOTE = path.join(__dirname, '..');
const RAIZ_TMP = fs.mkdtempSync(path.join(os.tmpdir(), 't24-governador-'));
test.after(() => fs.rmSync(RAIZ_TMP, { recursive: true, force: true }));
const escrever = (p, txt) => {
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, txt);
};
const bash = (args, env, opts = {}) => spawnSync('bash', args, { env: { PATH: process.env.PATH, ...env }, encoding: 'utf8', timeout: 60000, ...opts });

test('X01 o backup e a restauracao levam o estado do governador (disjuntor, pausa, aquecimento) e as regras vivas da catraca', () => {
  const h = path.join(RAIZ_TMP, 'home');
  const raiz = path.join(h, 'ozav-crm');
  fs.mkdirSync(path.join(raiz, 'deploy'), { recursive: true });
  for (const s of ['backup.sh', 'restaurar-estado.sh']) {
    const o = path.join(PACOTE, 'ozav', 'deploy', s);
    assert.ok(fs.existsSync(o), `falta ozav/deploy/${s}: aplique antes o aplicar/infra-vps.diff`);
    fs.copyFileSync(o, path.join(raiz, 'deploy', s));
  }
  escrever(path.join(h, '.ozav', '.env'), Array.from({ length: 22 }, (_, i) => `CHAVE_${i}=x`).join('\n') + '\n');
  fs.mkdirSync(path.join(h, '.local', 'node', 'bin'), { recursive: true });
  fs.symlinkSync(process.execPath, path.join(h, '.local', 'node', 'bin', 'node'));
  const db = path.join(raiz, 'whatsapp', 'dados', 'mensagens.db');
  fs.mkdirSync(path.dirname(db), { recursive: true });
  const d = new DatabaseSync(db);
  d.exec('CREATE TABLE mensagens (jid TEXT, ts INTEGER, texto TEXT)');
  d.prepare('INSERT INTO mensagens VALUES (?,?,?)').run('g1', 1, 'oi');
  d.close();
  const governador = JSON.stringify({ disjuntor_tudo_ate: '2026-10-16T12:00:00.000Z', aquecimento_desde: '2026-10-14T11:00:00.000Z', pausa_ate: null });
  const regras = JSON.stringify({ mao_espera_min: 15 });
  escrever(path.join(raiz, 'whatsapp-governador.json'), governador);
  escrever(path.join(raiz, 'catraca-regras.json'), regras);
  escrever(path.join(h, 'ozav-marketing', 'estado', 'publicados.json'), '["post-1"]'); // o backup abre esta pasta sempre

  const b = bash([path.join(raiz, 'deploy', 'backup.sh')], { HOME: h }, { cwd: raiz });
  assert.equal(b.status, 0, b.stdout + b.stderr);
  const pacote = path.join(h, 'backups', fs.readdirSync(path.join(h, 'backups')).find((f) => /^estado-\d+\.tgz$/.test(f)));
  const lista = spawnSync('tar', ['tzf', pacote], { encoding: 'utf8' }).stdout.split('\n');
  for (const f of ['whatsapp-governador.json', 'catraca-regras.json']) {
    assert.ok(lista.includes(f), `${f} ficou fora do pacote: perdida a VPS, o disjuntor e as regras vivas somem. O pacote leva: ${lista.filter(Boolean).join(', ')}`);
  }

  // o desastre: VPS nova, deploy feito, estado vazio
  fs.rmSync(path.join(raiz, 'whatsapp-governador.json'));
  fs.rmSync(path.join(raiz, 'catraca-regras.json'));
  const r = bash([path.join(raiz, 'deploy', 'restaurar-estado.sh'), pacote], { HOME: h });
  assert.equal(r.status, 0, r.stdout + r.stderr);
  assert.equal(fs.readFileSync(path.join(raiz, 'whatsapp-governador.json'), 'utf8'), governador, 'o disjuntor do governador nao voltou ao lugar');
  assert.equal(fs.readFileSync(path.join(raiz, 'catraca-regras.json'), 'utf8'), regras, 'as regras vivas da catraca nao voltaram ao lugar');
});
