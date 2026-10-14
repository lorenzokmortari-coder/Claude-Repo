#!/usr/bin/env node
/**
 * RED TEAM DO PORTÃO — executor do corpus sintético (tarefa 14 da nuvem, 14/10/2026).
 *
 *   node redteam/executor.js                                   (da raiz do pacote; lê redteam/corpus.jsonl)
 *   node redteam/executor.js outro.jsonl --csv resultados.csv  (tabela caso a caso)
 *   node redteam/executor.js --json resumo.json                (números por categoria, para comparar rodadas)
 *   node redteam/executor.js --config-real                     (o config de hoje: rodapé oficial vazio, modelos do arquivo)
 *
 * O portão é o do pacote, numa CÓPIA em pasta temporária: o rodapé de teste da bateria (o oficial
 * ainda é lacuna), os modelos aprovados como na bateria e a dispensa em conversa pura do config
 * real. O config real não é tocado. Datas fixas (agora = 2026-09-10), em modo teste.
 *
 * Medida por categoria: FUGA = devia BLOQUEADO e saiu REVISAR ou LIVRE (LIVRE é sempre CRÍTICO);
 * ALARME = devia passar (REVISAR/LIVRE) e saiu BLOQUEADO. Caso com `aberto` (fuga ou alarme conhecido,
 * sem patch) entra na conta mas não reprova. Sai com código 1 se algum caso sem `aberto` errar.
 *
 * DADO PESSOAL: nenhum. Todo texto do corpus é sintético; "Cliente" é o primeiro nome de cadastro de teste.
 */
'use strict';

process.env.VEEDHA_MODO_TESTE = '1';
const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');

const RAIZ = path.resolve(__dirname, '..');
const args = process.argv.slice(2);
const opcao = (nome) => {
  const i = args.indexOf(nome);
  return i >= 0 ? args[i + 1] : null;
};
const CORPUS = args.find((a, i) => !a.startsWith('--') && !['--csv', '--json'].includes(args[i - 1])) || path.join(__dirname, 'corpus.jsonl');

const sha256 = (s) => crypto.createHash('sha256').update(String(s), 'utf8').digest('hex');
const { RODAPE_DE_TESTE, leituraDeTeste } = require(path.join(RAIZ, 'testes', 'portao.teste.js'));

/** A cópia do motor com rodapé de teste, modelos aprovados e a dispensa do config real (ou o config real intacto). */
function montarMotor({ real = false } = {}) {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'veedha-redteam-'));
  if (/onedrive/i.test(tmp)) throw new Error(`pasta temporaria dentro do OneDrive: ${tmp}`);
  fs.cpSync(RAIZ, tmp, { recursive: true, filter: (src) => !['testes', 'redteam', 'dados', 'node_modules', '.git'].includes(path.relative(RAIZ, src).split(path.sep)[0]) });
  if (real) return { raiz: tmp, portao: require(path.join(tmp, 'lib', 'portao.js')) };
  const arqRodape = path.join(tmp, 'config', 'rodape.json');
  const rodape = JSON.parse(fs.readFileSync(arqRodape, 'utf8'));
  Object.assign(rodape, { texto: RODAPE_DE_TESTE, sha256: sha256(RODAPE_DE_TESTE), aprovado: true, aprovadoPor: 'Bateria automatizada (so na copia)', aprovadoEm: '2026-09-01', fonte: 'teste' });
  fs.writeFileSync(arqRodape, JSON.stringify(rodape, null, 2));
  const arqModelos = path.join(tmp, 'config', 'modelos.json');
  const cfg = JSON.parse(fs.readFileSync(arqModelos, 'utf8'));
  for (const m of cfg.modelos) {
    Object.assign(m, { aprovado: true, aprovadoPor: cfg.aprovadores[0], aprovadoEm: '2026-09-01', corpoSha256: sha256(m.corpo), leituraDeSentido: leituraDeTeste(m.corpo) });
  }
  fs.writeFileSync(arqModelos, JSON.stringify(cfg, null, 2));
  return { raiz: tmp, portao: require(path.join(tmp, 'lib', 'portao.js')) };
}

const CLIENTE = { temOptIn: true, temOptOut: false, suitabilityPerfil: 'moderado', suitabilityData: '2025-11-20', suitabilityValidoAte: '2027-11-20', termoCienciaAssinado: true, ehClienteAtivo: true, baseLegal: 'execucao_contrato', categoriaInvestidor: 'varejo', primeiroNome: 'Cliente' };
const PROSPECT = { temOptIn: true, temOptOut: false, suitabilityPerfil: null, suitabilityData: null, termoCienciaAssinado: false, ehClienteAtivo: false, baseLegal: 'legitimo_interesse', categoriaInvestidor: 'varejo', primeiroNome: 'Contato' };
const BASE = { canal: 'whatsapp_pessoal', agora: '2026-09-10', canalGravado: false, intermediario: 'XP Investimentos', citaProduto: false, temCustoTotal: false, origemDoConteudo: 'proprio' };
const PRESETS = {
  cliente: () => ({ ...BASE, destinatario: { ...CLIENTE } }),
  prospect: () => ({ ...BASE, destinatario: { ...PROSPECT } }),
  vencido: () => ({ ...BASE, destinatario: { ...CLIENTE, suitabilityValidoAte: '2026-08-01' } }),
  optout: () => ({ ...BASE, destinatario: { ...CLIENTE, temOptOut: true } }),
  semoptin: () => ({ ...BASE, destinatario: { ...CLIENTE, temOptIn: false } }),
  sembase: () => ({ ...BASE, destinatario: { ...CLIENTE, baseLegal: null } }),
  exclient: () => ({ ...BASE, destinatario: { ...CLIENTE, ehClienteAtivo: false } }),
  business: () => ({ ...BASE, canal: 'whatsapp_business', dentroJanela24h: false, destinatario: { ...CLIENTE } }),
  whats: () => ({ ...BASE, canal: 'whatsapp', destinatario: { ...CLIENTE } }),
  semtermo: () => ({ ...BASE, destinatario: { ...CLIENTE, termoCienciaAssinado: false } }),
  material: () => ({ ...BASE, citaProduto: true, destinatario: { ...CLIENTE } }),
};

function contexto(caso) {
  const preset = PRESETS[caso.contexto];
  if (!preset) throw new Error(`${caso.id}: contexto desconhecido "${caso.contexto}"`);
  const c = preset();
  for (const [k, v] of Object.entries(caso.extra || {})) {
    if (k === 'destinatario') Object.assign(c.destinatario, v);
    else c[k] = v;
  }
  return c;
}

function classificar(esperado, obtido) {
  if (obtido === esperado) return 'ok';
  if (esperado === 'BLOQUEADO') return obtido === 'LIVRE' ? 'fuga-livre' : 'fuga';
  if (obtido === 'BLOQUEADO') return 'alarme';
  if (obtido === 'LIVRE') return 'livre-indevido';
  return 'diferente';
}

function rodar(casos, P, { semRodape = false } = {}) {
  return casos.map((caso) => {
    // No config real nao ha rodape oficial para acrescentar: o texto vai como esta.
    const texto = caso.rodape === false || semRodape ? caso.texto : `${caso.texto}\n\n${RODAPE_DE_TESTE}`;
    const r = P.verificar(texto, contexto(caso));
    const regras = [...new Set(r.bloqueios.map((b) => `${b.regra}:${b.id}`))];
    return { ...caso, obtido: r.veredito, resultado: classificar(caso.esperado, r.veredito), regrasDisparadas: regras };
  });
}

function resumir(res) {
  const por = new Map();
  for (const x of res) {
    if (!por.has(x.categoria)) por.set(x.categoria, { categoria: x.categoria, casos: 0, devemBarrar: 0, fugas: 0, fugasLivre: 0, devemPassar: 0, alarmes: 0, livreIndevido: 0, abertos: 0 });
    const s = por.get(x.categoria);
    s.casos++;
    if (x.esperado === 'BLOQUEADO') s.devemBarrar++;
    else s.devemPassar++;
    if (x.resultado === 'fuga' || x.resultado === 'fuga-livre') s.fugas++;
    if (x.resultado === 'fuga-livre') s.fugasLivre++;
    if (x.resultado === 'alarme') s.alarmes++;
    if (x.resultado === 'livre-indevido') s.livreIndevido++;
    if (x.resultado !== 'ok' && x.aberto) s.abertos++;
  }
  return [...por.values()];
}

function csv(res) {
  const q = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`;
  const cab = ['id', 'categoria', 'subtipo', 'contexto', 'esperado', 'obtido', 'resultado', 'regra', 'regras_disparadas', 'aberto', 'interpretacao', 'texto'];
  return [cab.join(','), ...res.map((x) => [x.id, x.categoria, x.subtipo, x.contexto, x.esperado, x.obtido, x.resultado, x.regra, x.regrasDisparadas.join(' '), x.aberto || '', x.interpretacao ? 'sim' : '', x.texto].map(q).join(','))].join('\n') + '\n';
}

function main() {
  const casos = fs.readFileSync(CORPUS, 'utf8').split('\n').filter((l) => l.trim()).map((l) => JSON.parse(l));
  const real = args.includes('--config-real');
  const { portao } = montarMotor({ real });
  const res = rodar(casos, portao, { semRodape: real });
  if (real) console.log('CONFIG REAL: rodape oficial vazio; o que tem conteudo financeiro sai BLOQUEADO pela R08 antes de qualquer detector\n');
  const resumo = resumir(res);
  const pct = (a, b) => (b ? `${Math.round((100 * a) / b)}%` : '-');
  console.log(`corpus: ${casos.length} mensagens (${path.basename(CORPUS)})\n`);
  console.log('categoria'.padEnd(20), 'casos  barrar  fugas   passar  alarmes  abertos');
  const tot = { casos: 0, devemBarrar: 0, fugas: 0, fugasLivre: 0, devemPassar: 0, alarmes: 0, livreIndevido: 0, abertos: 0 };
  for (const s of resumo) {
    for (const k of Object.keys(tot)) tot[k] += s[k];
    console.log(s.categoria.padEnd(20), String(s.casos).padStart(5), String(s.devemBarrar).padStart(7), `${s.fugas} (${pct(s.fugas, s.devemBarrar)})`.padStart(9), String(s.devemPassar).padStart(7), String(s.alarmes).padStart(8), String(s.abertos).padStart(8));
  }
  console.log('TOTAL'.padEnd(20), String(tot.casos).padStart(5), String(tot.devemBarrar).padStart(7), `${tot.fugas} (${pct(tot.fugas, tot.devemBarrar)})`.padStart(9), String(tot.devemPassar).padStart(7), String(tot.alarmes).padStart(8), String(tot.abertos).padStart(8));
  console.log(`\nfugas para LIVRE (CRITICO): ${tot.fugasLivre}; LIVRE fora de modelo: ${tot.livreIndevido}`);
  const novos = res.filter((x) => x.resultado !== 'ok' && !x.aberto);
  for (const x of novos) console.log(`  ${x.resultado.toUpperCase().padEnd(10)} ${x.id} ${x.esperado}->${x.obtido} ${JSON.stringify(x.texto).slice(0, 110)}`);
  const csvArq = opcao('--csv');
  if (csvArq) fs.writeFileSync(csvArq, csv(res));
  const jsonArq = opcao('--json');
  if (jsonArq) fs.writeFileSync(jsonArq, JSON.stringify({ corpus: path.basename(CORPUS), total: tot, porCategoria: resumo }, null, 2));
  console.log(novos.length ? `\n${novos.length} caso(s) fora do esperado sem marca de "aberto": FALHA` : '\ntodos os casos sem "aberto" deram o veredito esperado');
  process.exitCode = novos.length ? 1 : 0;
}

if (require.main === module) main();
module.exports = { montarMotor, rodar, resumir, PRESETS };
