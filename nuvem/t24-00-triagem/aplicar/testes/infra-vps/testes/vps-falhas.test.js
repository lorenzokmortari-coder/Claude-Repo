/**
 * MODOS DE FALHA DA VPS (tarefa 15 da nuvem, 14/10/2026): os patches 01 a 07, provados numa pasta temporária.
 *
 *   node --test testes/vps-falhas.test.js      (da raiz do pacote "Infra · VPS"; Linux com bash, flock e tar; ~20 s)
 *
 * Cada teste Vxx copia o script do pacote para um HOME de mentira e simula a falha: falha no código de 14/10/2026
 * e passa com o patch de mesmo número. Nada toca o servidor; nenhum segredo de verdade (os .env são de mentira).
 */
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const http = require('http');
const { spawn, spawnSync } = require('child_process');
const { DatabaseSync } = require('node:sqlite');

const PACOTE = path.join(__dirname, '..');
const RAIZ_TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'vps-falhas-'));
test.after(() => fs.rmSync(RAIZ_TMP, { recursive: true, force: true }));
let n = 0;
const novoHome = () => {
  const h = path.join(RAIZ_TMP, `home-${++n}`);
  fs.mkdirSync(h, { recursive: true });
  return h;
};
const escrever = (p, txt, modo) => {
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, txt);
  if (modo) fs.chmodSync(p, modo);
};
const bash = (args, env, opts = {}) => spawnSync('bash', args, { env: { PATH: process.env.PATH, ...env }, encoding: 'utf8', timeout: 60000, ...opts });
const esperar = (ms) => new Promise((r) => setTimeout(r, ms));

test('V01 tarefa da Ozav com a trava presa ha 5 h deixa de "pular" calada: vira status 75 no log (o fiscal ve)', async () => {
  const h = novoHome();
  const raiz = path.join(h, 'ozav-crm');
  fs.mkdirSync(path.join(raiz, 'deploy'), { recursive: true });
  fs.copyFileSync(path.join(PACOTE, 'ozav', 'deploy', 'rodar.sh'), path.join(raiz, 'deploy', 'rodar.sh'));
  escrever(path.join(raiz, 'varrer-sla.js'), '// de mentira\n');
  escrever(path.join(h, '.ozav', 'crm.env'), 'X=1\n');
  escrever(path.join(h, '.local', 'node', 'bin', 'node'), '#!/bin/bash\nsleep 30\n', 0o755); // o worker que trava
  const env = { HOME: h };
  const a = spawn('bash', [path.join(raiz, 'deploy', 'rodar.sh'), 'sla'], { env: { PATH: process.env.PATH, ...env }, stdio: 'ignore', detached: true });
  try {
    await esperar(1500);
    const desde = path.join(raiz, '.travas', 'sla.lock.desde');
    // a rodada A pegou a trava ha pouco: a B pula como sempre (sem alarme falso)
    let b = bash([path.join(raiz, 'deploy', 'rodar.sh'), 'sla'], env);
    assert.equal(b.status, 0, b.stderr);
    // a rodada A esta pendurada ha 5 h
    escrever(desde, String(Math.floor(Date.now() / 1000) - 5 * 3600));
    b = bash([path.join(raiz, 'deploy', 'rodar.sh'), 'sla'], env);
    const log = fs.readFileSync(path.join(raiz, 'logs', 'sla.log'), 'utf8');
    assert.equal(b.status, 75, `a rodada com a trava presa ha 5 h saiu com ${b.status} (pulou calada); log:\n${log.slice(-300)}`);
    assert.match(log, /sla terminou com status 75/);
  } finally {
    try {
      process.kill(-a.pid, 'SIGKILL');
    } catch {
      /* ja saiu */
    }
  }
});

test('V02 duas rodadas do vigia do personagem ao mesmo tempo nao se sobrepoem (nem o vigia e o vigia-conferir das 12h45)', async () => {
  const h = novoHome();
  const raiz = path.join(h, 'fred-motor');
  fs.mkdirSync(raiz, { recursive: true });
  fs.copyFileSync(path.join(PACOTE, 'fred', 'fred-motor', 'rodar.sh'), path.join(raiz, 'rodar.sh'));
  const marcas = path.join(h, 'marcas.txt');
  // o python3 de mentira: anota inicio e fim de cada rodada e demora 2 s (como um video grande)
  escrever(path.join(h, 'bin', 'python3'), `#!/bin/bash\necho "inicio $(date +%s%N) $*" >> ${marcas}\nsleep 2\necho "fim $(date +%s%N) $*" >> ${marcas}\n`, 0o755);
  const roda = (tarefa) => new Promise((r) => spawn('bash', [path.join(raiz, 'rodar.sh'), tarefa], { env: { PATH: process.env.PATH, HOME: h }, stdio: 'ignore' }).on('close', r));
  await Promise.all([roda('vigia'), roda('vigia'), roda('vigia-conferir')]);
  const ev = fs.readFileSync(marcas, 'utf8').trim().split('\n').map((l) => l.split(' ')).map(([t, ns]) => ({ t, ns: BigInt(ns) }));
  let abertas = 0;
  let pico = 0;
  for (const e of ev.sort((x, y) => (x.ns < y.ns ? -1 : 1))) {
    abertas += e.t === 'inicio' ? 1 : -1;
    pico = Math.max(pico, abertas);
  }
  assert.equal(ev.filter((e) => e.t === 'inicio').length, 3, 'as tres rodadas tem de rodar (uma espera a outra)');
  assert.equal(pico, 1, `${pico} rodadas da familia vigia ao mesmo tempo: duas leem "ainda nao agendei" e agendam o mesmo post`);
});

test('V03 o backup da Ozav leva o que esta no WAL do mensagens.db e prova a restauracao todo dia', async () => {
  const h = novoHome();
  const raiz = path.join(h, 'ozav-crm');
  fs.mkdirSync(path.join(raiz, 'deploy'), { recursive: true });
  fs.mkdirSync(path.join(raiz, 'logs'), { recursive: true });
  fs.mkdirSync(path.join(h, 'ozav-marketing', 'estado'), { recursive: true });
  fs.copyFileSync(path.join(PACOTE, 'ozav', 'deploy', 'backup.sh'), path.join(raiz, 'deploy', 'backup.sh'));
  escrever(path.join(h, '.ozav', '.env'), Array.from({ length: 22 }, (_, i) => `CHAVE_${i}=x`).join('\n') + '\n');
  fs.mkdirSync(path.join(h, '.local', 'node', 'bin'), { recursive: true });
  fs.symlinkSync(process.execPath, path.join(h, '.local', 'node', 'bin', 'node'));
  const dbArq = path.join(raiz, 'whatsapp', 'dados', 'mensagens.db');
  fs.mkdirSync(path.dirname(dbArq), { recursive: true });
  // a captura: WAL, 500 mensagens gravadas que ainda nao foram para o arquivo principal (sem checkpoint), processo vivo
  const escritor = spawn(process.execPath, ['-e', `
    const {DatabaseSync}=require('node:sqlite');
    const d=new DatabaseSync(${JSON.stringify(dbArq)});
    d.exec('PRAGMA journal_mode=WAL; PRAGMA wal_autocheckpoint=0; CREATE TABLE mensagens (jid TEXT, ts INTEGER, texto TEXT)');
    const ins=d.prepare('INSERT INTO mensagens VALUES (?,?,?)');
    for (let i=0;i<500;i++) ins.run('g'+(i%7), i, 'mensagem '+i);
    console.log('pronto'); setInterval(()=>{}, 1000);`], { stdio: ['ignore', 'pipe', 'inherit'] });
  try {
    await new Promise((r) => escritor.stdout.once('data', r));
    const b = bash([path.join(raiz, 'deploy', 'backup.sh')], { HOME: h });
    assert.equal(b.status, 0, b.stdout + b.stderr);
    const pacote = fs.readdirSync(path.join(h, 'backups')).find((f) => /^estado-\d+\.tgz$/.test(f));
    const prova = path.join(RAIZ_TMP, `prova-${n}`);
    fs.mkdirSync(prova);
    spawnSync('tar', ['xzf', path.join(h, 'backups', pacote), '-C', prova]);
    const dbv = new DatabaseSync(path.join(prova, 'whatsapp', 'dados', 'mensagens.db'), { readOnly: true });
    let total = 0;
    try {
      total = dbv.prepare('SELECT count(*) c FROM mensagens').get().c;
    } catch {
      total = 0; // o arquivo principal ainda nem tem a tabela: tudo estava no WAL
    }
    assert.equal(total, 500, `o pacote restaurado tem ${total} de 500 mensagens: o que estava no WAL ficou de fora`);
    const ultima = path.join(h, 'backups', '.prova-ultima.txt');
    assert.ok(fs.existsSync(ultima) && /RESTAURACAO VALIDA/.test(fs.readFileSync(ultima, 'utf8')), 'a prova de restauracao nao rodou no backup do dia');
  } finally {
    escritor.kill('SIGKILL');
  }
});

test('V04 backup do personagem que nao fecha (pasta sumida, disco cheio) sai com erro e escreve FALHOU, nao "backup ok"', () => {
  const h = novoHome();
  const raiz = path.join(h, 'fred-motor');
  fs.mkdirSync(path.join(raiz, 'dados', 'logs'), { recursive: true });
  escrever(path.join(raiz, '.env'), 'X=1\n');
  // fred-motor/segredos nao existe: o tar falha
  fs.copyFileSync(path.join(PACOTE, 'fred', 'fred-motor', 'backup.sh'), path.join(h, 'backup.sh'));
  const b = bash([path.join(h, 'backup.sh')], { HOME: h });
  const log = fs.readFileSync(path.join(raiz, 'dados', 'logs', 'backup.log'), 'utf8');
  assert.notEqual(b.status, 0, `o backup que falhou saiu com status 0; o log diz: ${log.trim()}`);
  assert.match(log, /FALHOU/);
  // e com tudo no lugar o backup sai
  fs.mkdirSync(path.join(raiz, 'segredos'));
  const ok = bash([path.join(h, 'backup.sh')], { HOME: h });
  assert.equal(ok.status, 0, ok.stderr);
  assert.ok(fs.readdirSync(path.join(h, 'backups')).some((f) => /^fred-\d+\.tgz$/.test(f)));
});

test('V05 vigia de fora (no PC): painel fresco = ok; parado ou fora do ar avisa na segunda leitura ruim seguida', async () => {
  const vigia = require(path.join(PACOTE, 'pc', 'vigiar-vps.js'));
  let idadeMin = 10;
  const srv = http.createServer((req, res) => {
    res.writeHead(200, { 'Last-Modified': new Date(Date.now() - idadeMin * 60000).toUTCString() });
    res.end('ok');
  });
  await new Promise((r) => srv.listen(0, '127.0.0.1', r));
  const url = `http://127.0.0.1:${srv.address().port}/`;
  const estado = path.join(RAIZ_TMP, 'vigia.json');
  // assincrono de proposito: o servidor de mentira mora neste processo (spawnSync travaria o laco e ele nao responderia)
  const rodar = () => new Promise((r) => spawn(process.execPath, [path.join(PACOTE, 'pc', 'vigiar-vps.js'), '--url', url, '--estado', estado, '--sem-aviso', '--timeout-ms', '2000'], { stdio: 'ignore' }).on('close', r));
  try {
    assert.equal((await vigia.ler(url, 90, 2000)).ok, true);
    assert.equal(await rodar(), 0, 'painel fresco');
    idadeMin = 180;
    assert.equal(await rodar(), 1, 'primeira leitura ruim so registra');
    assert.equal(await rodar(), 2, 'segunda leitura ruim seguida avisa');
    idadeMin = 5;
    assert.equal(await rodar(), 0, 'voltou');
  } finally {
    srv.close();
  }
  // fora do ar
  const fora = spawnSync(process.execPath, [path.join(PACOTE, 'pc', 'vigiar-vps.js'), '--url', url, '--estado', estado, '--sem-aviso', '--timeout-ms', '1000'], { encoding: 'utf8' });
  assert.equal(fora.status, 1);
  assert.match(fora.stdout, /sem resposta/);
});

// o HOME de mentira da Ozav com o estado de um dia normal (V06 e V07)
function homeOzav() {
  const h = novoHome();
  const raiz = path.join(h, 'ozav-crm');
  fs.mkdirSync(path.join(raiz, 'deploy'), { recursive: true });
  fs.copyFileSync(path.join(PACOTE, 'ozav', 'deploy', 'backup.sh'), path.join(raiz, 'deploy', 'backup.sh'));
  const restaurar = path.join(PACOTE, 'ozav', 'deploy', 'restaurar-estado.sh');
  if (fs.existsSync(restaurar)) fs.copyFileSync(restaurar, path.join(raiz, 'deploy', 'restaurar-estado.sh'));
  escrever(path.join(h, '.ozav', '.env'), Array.from({ length: 22 }, (_, i) => `CHAVE_${i}=x`).join('\n') + '\n');
  fs.mkdirSync(path.join(h, '.local', 'node', 'bin'), { recursive: true });
  fs.symlinkSync(process.execPath, path.join(h, '.local', 'node', 'bin', 'node'));
  const dbArq = path.join(raiz, 'whatsapp', 'dados', 'mensagens.db');
  fs.mkdirSync(path.dirname(dbArq), { recursive: true });
  const d = new DatabaseSync(dbArq);
  d.exec('CREATE TABLE mensagens (jid TEXT, ts INTEGER, texto TEXT)');
  const ins = d.prepare('INSERT INTO mensagens VALUES (?,?,?)');
  for (let i = 0; i < 40; i++) ins.run('g' + (i % 3), i, 'mensagem ' + i);
  d.close();
  escrever(path.join(raiz, 'telegram', 'sessao.txt'), 'sessao-de-mentira\n');
  escrever(path.join(raiz, 'avisados.jsonl'), '{"jid":"g1","ts":1}\n');
  escrever(path.join(raiz, 'conduzir-config.json'), JSON.stringify({ travadas: ['<JID_1>', '<JID_2>'] }));
  escrever(path.join(raiz, 'hunting-bc-estado.json'), JSON.stringify({ fila: [] }));
  escrever(path.join(h, 'ozav-marketing', 'estado', 'publicados.json'), '["post-1"]');
  return { h, raiz, dbArq };
}
// o cron chama o backup pelo rodar.sh, que faz cd na raiz antes
const backupDoDia = ({ h, raiz }, cwd = raiz) => {
  const b = bash([path.join(raiz, 'deploy', 'backup.sh')], { HOME: h }, { cwd });
  assert.equal(b.status, 0, b.stdout + b.stderr);
  return path.join(h, 'backups', fs.readdirSync(path.join(h, 'backups')).find((f) => /^estado-\d+\.tgz$/.test(f)));
};

test('V06 o backup da Ozav leva o painel de travas da catraca e os .jsonl, mesmo rodado a mao de fora da raiz', () => {
  const o = homeOzav();
  // "RODAR: bash ~/ozav-crm/deploy/backup.sh" (cabecalho do script), da home: o caso de quem tira um pacote antes de desligar a VPS
  const lista = spawnSync('tar', ['tzf', backupDoDia(o, o.h)], { encoding: 'utf8' }).stdout.split('\n');
  for (const f of ['conduzir-config.json', 'hunting-bc-estado.json', 'avisados.jsonl']) {
    assert.ok(lista.includes(f), `${f} ficou fora do pacote: perdida a VPS, some junto. O pacote leva: ${lista.filter(Boolean).join(', ')}`);
  }
});

test('V07 restaurar o pacote poe cada parte na sua raiz (o "tar xzf -C ~" do documento deixa tudo na home)', () => {
  const o = homeOzav();
  const pacote = backupDoDia(o);
  const script = path.join(o.raiz, 'deploy', 'restaurar-estado.sh');
  assert.ok(fs.existsSync(script), 'nao ha script de restauracao: so o "tar xzf <pacote> -C ~" do INFRAESTRUTURA.md');

  // o comando do documento, numa home de prova: mensagens.db e sessao do Telegram vao parar na raiz da home
  const doc = novoHome();
  spawnSync('tar', ['xzf', pacote, '-C', doc]);
  assert.ok(fs.existsSync(path.join(doc, 'whatsapp', 'dados', 'mensagens.db')) && !fs.existsSync(path.join(doc, 'ozav-crm')), 'o comando do documento mudou de comportamento');

  // o desastre: VPS nova com o deploy feito e o estado vazio
  fs.rmSync(path.join(o.h, '.ozav'), { recursive: true });
  fs.rmSync(path.join(o.h, 'ozav-marketing', 'estado'), { recursive: true });
  fs.rmSync(path.join(o.raiz, 'telegram'), { recursive: true });
  fs.rmSync(path.join(o.raiz, 'avisados.jsonl'));
  fs.writeFileSync(o.dbArq, ''); // banco vazio criado pelo primeiro boot

  // --seco nao mexe em nada
  const seco = bash([script, pacote, '--seco'], { HOME: o.h });
  assert.equal(seco.status, 0, seco.stdout + seco.stderr);
  assert.ok(!fs.existsSync(path.join(o.h, '.ozav')), '--seco restaurou');

  const r = bash([script, pacote], { HOME: o.h });
  assert.equal(r.status, 0, r.stdout + r.stderr);
  const dbv = new DatabaseSync(o.dbArq, { readOnly: true });
  assert.equal(dbv.prepare('SELECT count(*) c FROM mensagens').get().c, 40);
  dbv.close();
  assert.ok(fs.existsSync(o.dbArq + '.antes-restaurar'), 'o banco que estava no lugar tem de ficar guardado ao lado');
  assert.equal(fs.readFileSync(path.join(o.raiz, 'telegram', 'sessao.txt'), 'utf8'), 'sessao-de-mentira\n');
  assert.ok(fs.existsSync(path.join(o.raiz, 'avisados.jsonl')));
  assert.equal(fs.readFileSync(path.join(o.h, 'ozav-marketing', 'estado', 'publicados.json'), 'utf8'), '["post-1"]');
  assert.equal(fs.statSync(path.join(o.h, '.ozav', '.env')).mode & 0o777, 0o600);
  assert.ok(!fs.existsSync(path.join(o.h, 'whatsapp')) && !fs.existsSync(path.join(o.h, 'estado')), 'sobrou estado na raiz da home');
});
