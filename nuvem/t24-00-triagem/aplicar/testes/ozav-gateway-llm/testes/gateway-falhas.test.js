/**
 * Auditoria do gateway (llm.js), 14/10/2026, sessao da nuvem. Sem rede:
 *
 *   node --test testes/gateway-falhas.test.js        (Node 22+; ~1 min por causa das esperas reais do pedir())
 *
 * Um provedor falso em 127.0.0.1 faz o papel do OpenRouter. O que ele devolve depende do NOME do modelo pedido
 * (a parte depois da ultima "/"): m-ok, m-mudo (nunca responde), m-429, m-500, m-quebrado (JSON cortado),
 * m-vazio, m-erro200, m-cortado (finish_reason length), m-402, m-null, m-lista, m-semcampo, m-400pdf, m-400cache...
 * O prefixo (a01/, openai/...) so separa a contagem de pedidos de cada teste.
 *
 * Cada teste roda numa COPIA do llm.js e do lib/custos.js deste pacote, numa pasta temporaria, com um modelos.json de
 * teste apontando para o provedor falso. Nada toca o modelos.json real, o custos.jsonl real, o gasto-dia.json real,
 * o plano de verdade nem a DM do bot (o avisar.js e um falso que grava num arquivo). HOME aponta para uma pasta vazia.
 *
 * Os testes "Axx" falham no llm.js de 14/10/2026 e passam com o patch de mesmo numero (patches/NN-*.diff).
 * Os testes "Rxx" passam antes e depois: provam o que ja esta certo e seguram regressao.
 * O teste marcado "todo" documenta um achado sem patch (nao conta como falha).
 */
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const http = require('http');
const { spawn } = require('child_process');

const PACOTE = path.join(__dirname, '..');
const RAIZ = fs.mkdtempSync(path.join(os.tmpdir(), 'gw-auditoria-'));
process.env.HOME = RAIZ;
process.env.USERPROFILE = RAIZ;
process.env.OZAV_SEM_AVISO = '1';
process.env.OPENROUTER_API_KEY = 'k-openrouter-falsa-123';
for (const k of ['OZAV_WORKER', 'OZAV_ORCAMENTO_USD', 'OZAV_LOTE', 'OZAV_TETO_DIA_USD', 'OZAV_CLAUDE_GATEWAY', 'OZAV_GASTO_ARQ', 'OZAV_CUSTOS_ARQ', 'OZAV_PLANO_ESTADO', 'OZAV_PLANO_PASTA', 'OZAV_CLAUDE_ENV', 'OZAV_CLAUDE_BIN', 'ANTHROPIC_API_KEY']) {
  delete process.env[k];
}

// ------------------------------------------------------------------ o provedor falso

const recebidos = []; // { modelo, corpo, auth }
let BASE = '';
const contar = (modelo) => recebidos.filter((r) => r.modelo === modelo).length;

function responder(req, res, bruto) {
  let corpo = {};
  try {
    corpo = JSON.parse(bruto);
  } catch {
    /* corpo estranho: responde 400 abaixo */
  }
  const modelo = String(corpo.model || '');
  const nome = modelo.slice(modelo.lastIndexOf('/') + 1);
  const n = contar(modelo); // quantos pedidos deste modelo ja chegaram antes deste
  recebidos.push({ modelo, corpo, auth: req.headers.authorization });
  const json = (status, obj, atraso = 0) =>
    setTimeout(() => {
      res.writeHead(status, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(obj));
    }, atraso);
  const texto = (conteudo, { fim = 'stop', custo = 0.001, entrada = 100, saida = 20, atraso = 0 } = {}) =>
    json(200, { choices: [{ message: { role: 'assistant', content: conteudo }, finish_reason: fim }], usage: { prompt_tokens: entrada, completion_tokens: saida, ...(custo == null ? {} : { cost: custo }) } }, atraso);

  switch (nome) {
    case 'm-ok':
      return texto('resposta boa');
    case 'm-json':
      return texto('{"ok": true}');
    case 'm-caro':
      return texto('resposta cara', { custo: 0.6 });
    case 'm-10c':
      return texto('dez centavos', { custo: 0.1, atraso: 300 });
    case 'm-mudo':
      return; // nunca responde: quem chamou estoura o tempo
    case 'm-sem-corpo':
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.write('{"choices": ');
      return; // cabecalho e meio corpo, depois silencio
    case 'm-429':
      return json(429, { error: { code: 429, message: 'Rate limit exceeded' } });
    case 'm-500':
      return json(500, { error: { code: 500, message: 'Internal Server Error' } });
    case 'm-quebrado':
      res.writeHead(200, { 'Content-Type': 'application/json' });
      return res.end('{"choices": [{"message": {"content": "meia res');
    case 'm-vazio':
      return texto('');
    case 'm-erro200':
      return json(200, { error: { code: 502, message: 'Provider returned error' } });
    case 'm-cortado':
      return texto('Bom dia! Sobre a proposta que voce pediu ontem, o valor do', { fim: 'length', custo: 0.002 });
    case 'm-402':
      return json(402, { error: { code: 402, message: 'Insufficient credits. Add more using https://openrouter.ai/settings/credits' } });
    case 'm-401eco':
      return json(401, { error: { code: 401, message: `No auth credentials found (recebi: ${req.headers.authorization})` } });
    case 'm-null':
      return texto('null');
    case 'm-lista':
      return texto('[]');
    case 'm-semcampo':
      return texto('{"outro": 1}');
    case 'm-400pdf':
      return n === 0 ? json(400, { error: { code: 400, message: 'Invalid file-parser engine "native" for this model' } }) : texto('lido sem o leitor nativo');
    case 'm-400cache':
      return n === 0 ? json(400, { error: { code: 400, message: 'cache_control is not supported by this provider' } }) : texto('ok sem cache');
    case 'gemini-3.5-flash-lite':
      // modelo de verdade da tabela de reserva, mas SEM usage.cost: 1 milhao de tokens de entrada = US$ 0,30 pela tabela
      return texto('sem custo informado', { custo: null, entrada: 1000000, saida: 0 });
    default:
      return json(400, { error: { code: 400, message: 'modelo desconhecido no provedor falso: ' + modelo } });
  }
}

const servidor = http.createServer((req, res) => {
  let bruto = '';
  req.on('data', (d) => (bruto += d));
  req.on('end', () => responder(req, res, bruto));
});

test.before(async () => {
  await new Promise((r) => servidor.listen(0, '127.0.0.1', r));
  BASE = `http://127.0.0.1:${servidor.address().port}`;
});

test.after(async () => {
  servidor.closeAllConnections();
  await new Promise((r) => servidor.close(r));
  fs.rmSync(RAIZ, { recursive: true, force: true });
});

// ------------------------------------------------------------------ as copias do gateway

let _n = 0;
/** Uma copia do gateway deste pacote com um modelos.json de teste. Cada copia e um "processo" novo (modulo novo). */
function copia(funcoes, { avisar = false } = {}) {
  const dir = path.join(RAIZ, `copia-${++_n}`);
  fs.mkdirSync(path.join(dir, 'lib'), { recursive: true });
  fs.copyFileSync(path.join(PACOTE, 'llm.js'), path.join(dir, 'llm.js'));
  fs.copyFileSync(path.join(PACOTE, 'lib', 'custos.js'), path.join(dir, 'lib', 'custos.js'));
  fs.writeFileSync(
    path.join(dir, 'modelos.json'),
    JSON.stringify({ provedores: { openrouter: { chave: 'OPENROUTER_API_KEY', base: BASE, so_primeira_mao: [] }, plano: { tipo: 'claude-cli' } }, funcoes })
  );
  const log = path.join(dir, 'avisos.log');
  if (avisar) {
    fs.mkdirSync(path.join(dir, 'claude'));
    fs.writeFileSync(path.join(dir, 'claude', 'avisar.js'), `require('fs').appendFileSync(${JSON.stringify(log)}, JSON.stringify(process.argv.slice(2)) + '\\n');`);
  }
  return {
    dir,
    llm: require(path.join(dir, 'llm.js')),
    livro: () => {
      const arq = path.join(dir, 'custos.jsonl');
      return fs.existsSync(arq) ? fs.readFileSync(arq, 'utf8').trim().split('\n').filter(Boolean).map((l) => JSON.parse(l)) : [];
    },
    gasto: (arq = path.join(dir, 'gasto-dia.json')) => (fs.existsSync(arq) ? JSON.parse(fs.readFileSync(arq, 'utf8')) : { usd: 0, chamadas: 0, funcoes: {}, lotes: {} }),
    /** Os avisos que o avisar.js falso recebeu (o gateway chama por execFile, sem esperar): espera ate `ms`. */
    avisos: async (ms = 3000) => {
      const ate = Date.now() + ms;
      while (Date.now() < ate && !fs.existsSync(log)) await new Promise((r) => setTimeout(r, 50));
      await new Promise((r) => setTimeout(r, 300));
      return fs.existsSync(log) ? fs.readFileSync(log, 'utf8').trim().split('\n').filter(Boolean).map((l) => JSON.parse(l)) : [];
    },
  };
}

async function comEnv(vars, fn) {
  const antes = {};
  for (const [k, v] of Object.entries(vars)) {
    antes[k] = process.env[k];
    if (v === undefined) delete process.env[k];
    else process.env[k] = v;
  }
  try {
    return await fn();
  } finally {
    for (const [k, v] of Object.entries(antes)) {
      if (v === undefined) delete process.env[k];
      else process.env[k] = v;
    }
  }
}
const comAviso = (fn) => comEnv({ OZAV_SEM_AVISO: undefined }, fn);
const textoDoAviso = (a) => a[a.indexOf('--texto') + 1] || '';

/** Roda um script Node num processo separado (outro "robo"), com o ambiente dado. */
function rodarFilho(codigo, env) {
  return new Promise((resolve) => {
    const f = spawn(process.execPath, ['-e', codigo], { env: { ...process.env, ...env }, stdio: ['ignore', 'pipe', 'pipe'] });
    let saida = '';
    f.stdout.on('data', (d) => (saida += d));
    f.stderr.on('data', (d) => (saida += d));
    f.on('close', (c) => resolve({ codigo: c, saida }));
  });
}

// ====================================================================== achados (falham antes do patch)

test('A01 estouro de tempo nao se repete: um pedido so ao elo lento, e a vez passa logo ao proximo (G3)', async () => {
  const c = copia({ _f: { cadeia: ['openrouter:a01/m-mudo', 'openrouter:a01/m-ok'], max_saida: 100 } });
  const t0 = Date.now();
  const r = await c.llm.gerarDetalhado({ funcao: '_f', prompt: 'x', timeoutMs: 400 });
  const dt = Date.now() - t0;
  assert.equal(r.modelo, 'a01/m-ok');
  assert.equal(contar('a01/m-mudo'), 1, `o elo que estourou o tempo recebeu ${contar('a01/m-mudo')} pedidos (cada um pode estar sendo cobrado do outro lado)`);
  assert.ok(dt < 3000, `a chamada levou ${dt} ms com timeout de 400 ms`);
});

test('A02 resposta vazia, sem "choices" ou cortada no max_tokens nao e sucesso: a cadeia passa a vez e o custo fica no livro', async () => {
  const c = copia({
    _vazio: { cadeia: ['openrouter:a02/m-vazio', 'openrouter:a02/m-ok'] },
    _erro200: { cadeia: ['openrouter:a02/m-erro200', 'openrouter:a02/m-ok'] },
    _cortado: { cadeia: ['openrouter:a02/m-cortado', 'openrouter:a02/m-ok'] },
  });
  for (const f of ['_vazio', '_erro200', '_cortado']) {
    const r = await c.llm.gerarDetalhado({ funcao: f, prompt: 'x' });
    assert.equal(r.modelo, 'a02/m-ok', `${f}: o gateway devolveu ${JSON.stringify(r.conteudo)} (por ${r.modelo}) como se fosse resposta`);
  }
  assert.ok(c.livro().some((l) => l.modelo === 'a02/m-cortado' && l.custo === 0.002), 'a chamada cortada foi cobrada e tem de estar no livro');
});

test('A03 sem credito no OpenRouter (402): o dono e avisado na hora (o 17/09 de novo)', async () => {
  const c = copia({ _f: { cadeia: ['openrouter:a03/m-402'] } }, { avisar: true });
  await comAviso(() => assert.rejects(c.llm.gerar({ funcao: '_f', prompt: 'x' }), /402/));
  const av = await c.avisos();
  assert.ok(av.some((a) => /402|cr[eé]dito/i.test(textoDoAviso(a))), 'nenhum aviso de credito: ' + JSON.stringify(av));
});

test('A04 gasto de teste com lote declarado nao come o orcamento do dia da funcao da operacao (G9/G10)', async () => {
  const funcoes = { _transc: { cadeia: ['openrouter:a04/m-caro'], teto_dia_usd: 1, ao_estourar: 'so_plano' } };
  const teste = copia(funcoes);
  await comEnv({ OZAV_ORCAMENTO_USD: '5', OZAV_LOTE: 'eval-audio' }, async () => {
    await teste.llm.gerar({ funcao: '_transc', prompt: 'x', forcarElo: 'openrouter:a04/m-caro' });
    await teste.llm.gerar({ funcao: '_transc', prompt: 'x', forcarElo: 'openrouter:a04/m-caro' });
  });
  const op = copia(funcoes); // a operacao: outro processo, mesmo contador do dia
  await comEnv({ OZAV_GASTO_ARQ: path.join(teste.dir, 'gasto-dia.json') }, async () => {
    const r = await op.llm.gerarDetalhado({ funcao: '_transc', prompt: 'x' });
    assert.equal(r.modelo, 'a04/m-caro');
  });
});

test('A05 o aviso de orcamento estourado nao diz "nada parou" quando a funcao nao tem elo do plano', async () => {
  const c = copia({ _leitura: { cadeia: ['openrouter:a05/m-caro'], teto_dia_usd: 0.5, ao_estourar: 'so_plano' } }, { avisar: true });
  await c.llm.gerar({ funcao: '_leitura', prompt: 'x' }); // US$ 0,60 > teto de 0,50
  await comAviso(() => assert.rejects(c.llm.gerar({ funcao: '_leitura', prompt: 'x' }), /esgotad/));
  const textos = (await c.avisos()).map(textoDoAviso).join('\n');
  assert.match(textos, /or[cç]amento/i, 'o aviso de orcamento nao saiu');
  assert.doesNotMatch(textos, /nada parou/, 'o aviso diz "nada parou", mas a funcao parou');
});

test('A06 o teto do PROCESSO vale por dia: processo de longa duracao (bot) nao fica mudo para sempre depois de US$ 1 (G8)', async (t) => {
  t.mock.timers.enable({ apis: ['Date'], now: Date.parse('2026-10-14T15:00:00Z') });
  const c = copia({ _cli: { cadeia: ['openrouter:a06/m-caro'] } });
  await c.llm.gerar({ funcao: '_cli', prompt: 'x' });
  await c.llm.gerar({ funcao: '_cli', prompt: 'x' }); // US$ 1,20 neste processo hoje
  await assert.rejects(c.llm.gerar({ funcao: '_cli', prompt: 'x' }), /DISJUNTOR: este processo/);
  t.mock.timers.setTime(Date.parse('2026-10-15T15:00:00Z')); // dia seguinte, mesmo processo
  const r = await c.llm.gerarDetalhado({ funcao: '_cli', prompt: 'x' });
  assert.equal(r.modelo, 'a06/m-caro');
});

test('A07 no maximo 2 "claude" ao mesmo tempo na MAQUINA, nao 2 por processo (G7)', async () => {
  const dir = fs.mkdtempSync(path.join(RAIZ, 'plano-'));
  const log = path.join(dir, 'claude.log');
  const falso = path.join(dir, 'claude-falso.js');
  fs.writeFileSync(
    falso,
    `const fs=require('fs');fs.appendFileSync(process.env.LOG_CLAUDE,'ini '+Date.now()+'\\n');let e='';process.stdin.on('data',d=>e+=d).on('end',()=>setTimeout(()=>{fs.appendFileSync(process.env.LOG_CLAUDE,'fim '+Date.now()+'\\n');console.log(JSON.stringify({is_error:false,result:'ok '+e.slice(0,5),usage:{input_tokens:1,output_tokens:1},total_cost_usd:0.001}))},600));`
  );
  fs.writeFileSync(path.join(dir, 'claude.env'), 'CLAUDE_CODE_OAUTH_TOKEN=tok-de-teste\nOZAV_CLAUDE_GATEWAY=valer\n');
  const c = copia({ _p: { cadeia: ['plano:claude-x'] } });
  const env = { LOG_CLAUDE: log, OZAV_CLAUDE_ENV: path.join(dir, 'claude.env'), OZAV_CLAUDE_BIN: falso, OZAV_PLANO_PASTA: path.join(dir, 'pasta'), OZAV_PLANO_ESTADO: path.join(dir, 'estado.json') };
  const codigo = `const llm=require(${JSON.stringify(path.join(c.dir, 'llm.js'))});Promise.all([llm.gerar({funcao:'_p',prompt:'a'}),llm.gerar({funcao:'_p',prompt:'b'})]).then(()=>process.exit(0),(e)=>{console.error(e.message);process.exit(1)});`;
  const filhos = await Promise.all([1, 2, 3].map(() => rodarFilho(codigo, env)));
  for (const f of filhos) assert.equal(f.codigo, 0, f.saida);
  const ev = fs.readFileSync(log, 'utf8').trim().split('\n').map((l) => l.split(' ')).map(([k, t]) => ({ k, t: Number(t) }));
  ev.sort((a, b) => a.t - b.t || (a.k === 'fim' ? -1 : 1));
  let agora = 0;
  let max = 0;
  for (const e of ev) max = Math.max(max, (agora += e.k === 'ini' ? 1 : -1));
  assert.equal(ev.filter((e) => e.k === 'ini').length, 6);
  assert.ok(max <= 2, `chegaram a rodar ${max} "claude" ao mesmo tempo (3 robos x 2 chamadas)`);
});

test('A08 o reenvio depois de um 400 nao tira o leitor nativo do PDF (G16) nem o raciocinio declarado (G15)', async () => {
  const c = copia({
    _pdf: { cadeia: ['openrouter:a08/m-400pdf', 'openrouter:a08b/m-ok'], raciocinio: { effort: 'low' } },
    _cache: { cadeia: ['openrouter:a08/m-400cache'], raciocinio: { effort: 'low' } },
  });
  await c.llm.gerarDetalhado({ funcao: '_pdf', prompt: 'Descreva.', anexos: [{ tipo: 'pdf', base64: 'JVBERi0xLjQ=' }] }).catch(() => {});
  const pdfs = recebidos.filter((r) => r.modelo === 'a08/m-400pdf');
  assert.ok(pdfs.length >= 1);
  assert.ok(pdfs.every((r) => r.corpo.plugins), `${pdfs.length} pedidos com PDF; algum saiu SEM o leitor nativo (o OpenRouter cai no OCR cobrado a parte)`);
  await c.llm.gerarDetalhado({ funcao: '_cache', prompt: 'x', sistemaFixo: 'VOZ FIXA. ', sistema: 'resto do sistema' }).catch(() => {});
  const caches = recebidos.filter((r) => r.modelo === 'a08/m-400cache');
  assert.ok(caches.length >= 2, 'o 400 de cache_control tem de ser reenviado com o sistema em texto corrido');
  assert.ok(caches.every((r) => r.corpo.reasoning && r.corpo.reasoning.effort === 'low'), 'o reenvio tirou o raciocinio declarado (o provedor volta ao padrao dele)');
});

test('A09 a segunda leitura nunca sai pelo fornecedor de quem redigiu, nem quando a redacao caiu na reserva (G17)', async () => {
  const c = copia({
    _redacao: { cadeia: ['openrouter:anthropic/m-quebrado', 'openrouter:openai/m-ok'] },
    _adversarial: { cadeia: ['openrouter:openai/m-json', 'openrouter:moonshotai/m-json'] },
  });
  const red = await c.llm.gerarDetalhado({ funcao: '_redacao', prompt: 'escreva' });
  assert.equal(red.modelo, 'openai/m-ok', 'a redacao caiu na reserva da OpenAI (cenario do teste)');
  assert.equal(red.fornecedor, 'openai', 'o resultado tem de dizer o fornecedor de quem redigiu');
  const adv = await c.llm.gerarDetalhado({ funcao: '_adversarial', prompt: 'revise', esquema: { type: 'object' }, evitarFornecedor: red.fornecedor });
  assert.notEqual(adv.modelo.split('/')[0], 'openai', 'a segunda leitura saiu pelo mesmo fornecedor que redigiu');
});

test('A10 JSON valido do tipo errado (null, lista) ou sem campo obrigatorio nao e sucesso', async () => {
  const esquema = { type: 'object', properties: { ok: { type: 'boolean' } }, required: ['ok'] };
  const c = copia({
    _null: { cadeia: ['openrouter:a10/m-null', 'openrouter:a10/m-json'] },
    _lista: { cadeia: ['openrouter:a10/m-lista', 'openrouter:a10/m-json'] },
    _semcampo: { cadeia: ['openrouter:a10/m-semcampo', 'openrouter:a10/m-json'] },
  });
  for (const f of ['_null', '_lista', '_semcampo']) {
    const r = await c.llm.gerarDetalhado({ funcao: f, prompt: 'x', esquema });
    assert.deepEqual(r.conteudo, { ok: true }, `${f}: o gateway devolveu ${JSON.stringify(r.conteudo)} como resposta valida`);
  }
});

test('A11 a cabeca da cadeia falhou e a reserva respondeu: o dono fica sabendo (uma vez por dia pela chave do avisar.js)', async () => {
  const c = copia({ _tri: { cadeia: ['openrouter:a11/m-quebrado', 'openrouter:a11/m-ok'] } }, { avisar: true });
  await comAviso(async () => {
    const r = await c.llm.gerarDetalhado({ funcao: '_tri', prompt: 'x' });
    assert.equal(r.modelo, 'a11/m-ok');
  });
  const av = await c.avisos();
  assert.ok(av.some((a) => a.includes('reserva-_tri')), 'nenhum aviso de reserva: ' + JSON.stringify(av));
});

test('A12 sem custo informado, a tabela de reserva casa o ID do OpenRouter ("google/...") e o disjuntor soma', async () => {
  const c = copia({ _d: { cadeia: ['openrouter:google/gemini-3.5-flash-lite'] } });
  await c.llm.gerar({ funcao: '_d', prompt: 'x' });
  const linha = c.livro().pop();
  assert.equal(linha.custo, 0.3, 'livro: ' + JSON.stringify(linha));
  assert.equal(c.gasto().usd, 0.3, 'o disjuntor somou ' + c.gasto().usd);
});

test('A13 o relogio do plano vale mesmo quando o "claude" deixa um subprocesso com a saida aberta', async () => {
  const dir = fs.mkdtempSync(path.join(RAIZ, 'neto-'));
  const falso = path.join(dir, 'claude-falso.js');
  fs.writeFileSync(falso, `require('child_process').spawn('sleep', ['8'], { stdio: 'inherit' }); setTimeout(() => {}, 60000);`);
  fs.writeFileSync(path.join(dir, 'claude.env'), 'CLAUDE_CODE_OAUTH_TOKEN=tok-de-teste\nOZAV_CLAUDE_GATEWAY=valer\n');
  const c = copia({ _p: { cadeia: ['plano:claude-x'] } });
  const env = { OZAV_CLAUDE_ENV: path.join(dir, 'claude.env'), OZAV_CLAUDE_BIN: falso, OZAV_PLANO_PASTA: path.join(dir, 'pasta'), OZAV_PLANO_ESTADO: path.join(dir, 'estado.json') };
  const t0 = Date.now();
  await comEnv(env, () => assert.rejects(c.llm.gerar({ funcao: '_p', prompt: 'x', timeoutMs: 500 }), /nao respondeu/));
  const dt = Date.now() - t0;
  assert.ok(dt < 4000, `com timeout de 0,5 s a chamada so voltou em ${dt} ms (presa no subprocesso)`);
});

test(
  'A14 chamadas em paralelo passam juntas pelo teto do processo (sem patch: ver achados.md)',
  { todo: 'sem patch: o teto e conferido antes e somado depois; exige reservar uma estimativa por chamada' },
  async () => {
    const c = copia({ _par: { cadeia: ['openrouter:a14/m-10c'] } });
    const rs = await Promise.allSettled(Array.from({ length: 15 }, () => c.llm.gerar({ funcao: '_par', prompt: 'x' })));
    const pagas = rs.filter((r) => r.status === 'fulfilled').length;
    assert.ok(pagas * 0.1 <= 1.1, `${pagas} chamadas pagas (US$ ${(pagas * 0.1).toFixed(2)}) num processo com teto de US$ 1`);
  }
);

// ====================================================================== o que ja esta certo (passa antes e depois)

test('R01 429 e 500 tem teto: 4 pedidos no mesmo elo e a vez passa (nao e tempestade sem fim)', async () => {
  const c = copia({ _r: { cadeia: ['openrouter:r01/m-429', 'openrouter:r01b/m-500', 'openrouter:r01/m-ok'] } });
  const r = await c.llm.gerarDetalhado({ funcao: '_r', prompt: 'x' });
  assert.equal(r.modelo, 'r01/m-ok');
  assert.equal(contar('r01/m-429'), 4);
  assert.equal(contar('r01b/m-500'), 4);
});

test('R02 corpo JSON quebrado e cabecalho sem corpo: o elo falha (sem repetir) e a cadeia segue', async () => {
  const c = copia({ _q: { cadeia: ['openrouter:r02/m-quebrado', 'openrouter:r02/m-sem-corpo', 'openrouter:r02/m-ok'] } });
  const t0 = Date.now();
  const r = await c.llm.gerarDetalhado({ funcao: '_q', prompt: 'x', timeoutMs: 600 });
  assert.equal(r.modelo, 'r02/m-ok');
  assert.equal(contar('r02/m-quebrado'), 1);
  assert.equal(contar('r02/m-sem-corpo'), 1);
  assert.ok(Date.now() - t0 < 3000);
});

test('R03 a chave nunca aparece no erro, nem quando o provedor a devolve no corpo (G13)', async () => {
  const c = copia({ _k: { cadeia: ['openrouter:r03/m-401eco'] } });
  const e = await c.llm.gerar({ funcao: '_k', prompt: 'x' }).catch((x) => x);
  assert.match(e.message, /401/);
  assert.doesNotMatch(e.message, /k-openrouter-falsa-123/);
});

test('R04 seis robos gravando ao mesmo tempo: o livro e o contador do dia nao perdem linha nem soma (G11/G12)', async () => {
  const c = copia({ _v: { cadeia: ['openrouter:r04/m-ok'] } });
  const codigo = `const llm=require(${JSON.stringify(path.join(c.dir, 'llm.js'))});(async()=>{for(let i=0;i<30;i++)await llm.gerar({funcao:'_v',prompt:'x'+i})})().then(()=>process.exit(0),(e)=>{console.error(e.message);process.exit(1)});`;
  const filhos = await Promise.all([1, 2, 3, 4, 5, 6].map(() => rodarFilho(codigo, { OZAV_WORKER: '1' })));
  for (const f of filhos) assert.equal(f.codigo, 0, f.saida);
  const livro = c.livro();
  assert.equal(livro.length, 180);
  const g = c.gasto();
  assert.equal(g.chamadas, 180);
  assert.equal(Number(g.usd.toFixed(6)), 0.18);
});
