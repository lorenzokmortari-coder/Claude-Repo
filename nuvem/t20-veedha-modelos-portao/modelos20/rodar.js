#!/usr/bin/env node
/**
 * MODELOS À PROVA DO PORTÃO (tarefa 20 da nuvem, 14/10/2026): roda as 30 propostas de modelos20/modelos.json no
 * portão real, com o executor da tarefa 14 (redteam/executor.js), e confere o veredito esperado.
 *
 *   node modelos20/rodar.js                       (da raiz do motor; precisa de redteam/ da tarefa 14)
 *   node modelos20/rodar.js --csv resultados.csv  (tabela modelo a modelo)
 *
 * Três conferências por modelo:
 *   1. config de TESTE (rodapé de teste da bateria, como será com o rodapé oficial): o veredito tem de ser o `esperado`
 *      (todos REVISAR: texto livre nunca sai LIVRE, R38) e nenhum bloqueio;
 *   2. config REAL de hoje (rodapé oficial vazio): o veredito tem de ser o `esperado_real`. Conversa pura sai REVISAR
 *      (dispensa de 23/09/2026); com produto sai BLOQUEADO, e o ÚNICO bloqueio tem de ser o R08 (falta o rodapé);
 *   3. `candidato_livre`: numa cópia, o modelo entra em config/modelos.json como aprovado. A carga tem de aceitar o
 *      texto (lista fechada de pedidos e de caracteres) e a instância exata tem de sair LIVRE.
 * Sai com código 1 se algum modelo der diferente do esperado.
 *
 * DADO PESSOAL: nenhum. Os exemplos são sintéticos ("Cliente", "Banco Exemplo", "Banco Modelo").
 */
'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const RAIZ = path.resolve(__dirname, '..');
const { montarMotor, PRESETS } = require(path.join(RAIZ, 'redteam', 'executor.js'));
const { RODAPE_DE_TESTE, leituraDeTeste } = require(path.join(RAIZ, 'testes', 'portao.teste.js'));

const args = process.argv.slice(2);
const opcao = (n) => (args.includes(n) ? args[args.indexOf(n) + 1] : null);
const ARQ = path.join(__dirname, 'modelos.json');
const sha256 = (s) => crypto.createHash('sha256').update(String(s), 'utf8').digest('hex');

function render(corpo, campos) {
  return corpo.replace(/\{(\w+)\}/g, (m, k) => {
    if (!(k in campos)) throw new Error(`campo sem exemplo: ${k}`);
    return campos[k];
  });
}

function contexto(m, extra = {}) {
  const c = PRESETS[m.contexto]();
  for (const [k, v] of Object.entries({ ...(m.extra || {}), ...extra })) {
    if (k === 'destinatario') Object.assign(c.destinatario, v);
    else c[k] = v;
  }
  return c;
}

/** O portão de uma cópia de teste com os candidatos a LIVRE aprovados em config/modelos.json. */
function motorComCandidatos(candidatos) {
  const { raiz } = montarMotor();
  const arq = path.join(raiz, 'config', 'modelos.json');
  const cfg = JSON.parse(fs.readFileSync(arq, 'utf8'));
  for (const m of candidatos) {
    cfg.modelos.push({ id: m.id.toLowerCase(), gatilho: m.situacao, corpo: m.corpo, aprovado: true, aprovadoPor: cfg.aprovadores[0], aprovadoEm: '2026-09-01', corpoSha256: sha256(m.corpo), leituraDeSentido: leituraDeTeste(m.corpo) });
  }
  fs.writeFileSync(arq, JSON.stringify(cfg, null, 2));
  for (const k of Object.keys(require.cache)) if (k.startsWith(raiz)) delete require.cache[k];
  return require(path.join(raiz, 'lib', 'portao.js'));
}

function main() {
  const { modelos } = JSON.parse(fs.readFileSync(ARQ, 'utf8'));
  const teste = montarMotor().portao;
  const real = montarMotor({ real: true }).portao;
  const candidatos = modelos.filter((m) => m.candidato_livre);
  const comCand = motorComCandidatos(candidatos);
  const res = [];
  for (const m of modelos) {
    const texto = render(m.corpo, m.exemplo);
    const rt = teste.verificar(`${texto}\n\n${RODAPE_DE_TESTE}`, contexto(m));
    const rr = real.verificar(texto, contexto(m));
    const regrasReal = [...new Set(rr.bloqueios.map((b) => b.regra))];
    const okTeste = rt.veredito === m.esperado && rt.bloqueios.length === 0;
    const okReal = rr.veredito === m.esperado_real && (m.esperado_real !== 'BLOQUEADO' || (regrasReal.length === 1 && regrasReal[0] === 'R08'));
    let livre = '';
    let okLivre = true;
    if (m.candidato_livre) {
      const id = m.id.toLowerCase();
      const carregado = comCand.MODELOS.find((x) => x.id === id);
      const campos = Object.fromEntries(Object.entries(m.exemplo).filter(([k]) => k !== 'primeiroNome'));
      const ri = comCand.verificar(`${texto}\n\n${RODAPE_DE_TESTE}`, contexto(m, { modeloId: id, camposDoModelo: { primeiroNome: m.exemplo.primeiroNome, ...campos } }));
      livre = carregado && carregado.valido ? ri.veredito : `RECUSADO NA CARGA: ${carregado ? carregado.motivo : 'ausente'}`;
      okLivre = livre === 'LIVRE';
    }
    res.push({ id: m.id, situacao: m.situacao, teste: rt.veredito, bloqueiosTeste: rt.bloqueios.map((b) => `${b.regra}:${b.id}`).join(' '), real: rr.veredito, regrasReal: regrasReal.join(' '), livre, ok: okTeste && okReal && okLivre, texto });
  }
  console.log('modelo'.padEnd(32), 'teste'.padEnd(9), 'real (hoje)'.padEnd(22), 'como modelo aprovado');
  for (const r of res) {
    console.log(`${r.ok ? ' ' : '!'} ${r.id.padEnd(30)} ${r.teste.padEnd(9)} ${(r.real + (r.regrasReal ? ` (${r.regrasReal})` : '')).padEnd(22)} ${r.livre}`);
    if (r.bloqueiosTeste) console.log(`     bloqueios no teste: ${r.bloqueiosTeste}`);
  }
  const ruins = res.filter((r) => !r.ok);
  console.log(`\n${res.length} modelos; ${res.length - ruins.length} com o veredito esperado nas ${candidatos.length ? 'tres' : 'duas'} conferencias; ${candidatos.length} candidatos a LIVRE`);
  const arqCsv = opcao('--csv');
  if (arqCsv) {
    const q = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`;
    const cab = ['id', 'situacao', 'veredito_teste', 'bloqueios_teste', 'veredito_real_hoje', 'regras_real', 'como_modelo_aprovado', 'ok', 'texto_exemplo'];
    fs.writeFileSync(arqCsv, [cab.join(','), ...res.map((r) => [r.id, r.situacao, r.teste, r.bloqueiosTeste, r.real, r.regrasReal, r.livre, r.ok ? 'sim' : 'NAO', r.texto].map(q).join(','))].join('\n') + '\n');
  }
  process.exitCode = ruins.length ? 1 : 0;
  return res;
}

if (require.main === module) main();
module.exports = { main, render };
