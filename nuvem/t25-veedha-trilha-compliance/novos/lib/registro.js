/**
 * REGISTRO DE SAÍDA — o que foi dito a cada cliente, guardado 5 anos. (tarefa 25 da nuvem, V01, 14/10/2026)
 *
 * POR QUE ISTO EXISTE
 * -------------------
 * O assessor tem de poder mostrar, anos depois, o que foi dito a cada cliente: a comunicação
 * com cliente é registro obrigatório, com guarda de 5 anos. O `estado.enviados` (lib/limites.js)
 * mede o silêncio de 72h: é histórico de DISPARO, não de CONTEÚDO. Este módulo guarda o
 * conteúdo: destino, canal, texto integral, veredito do portão, regras, quem aprovou e quando,
 * a hora da mensagem, a hora do servidor e o id da fila.
 *
 * AS GARANTIAS (o contrato de testes-pendentes/v01-log-de-saida.teste.js, mais a cadeia)
 *   1. Só acréscimo. Registro gravado não se reescreve: o mesmo id duas vezes lança "ja
 *      registrado". Não existe função de apagar, remover, limpar ou truncar.
 *   2. RETENCAO_ANOS = 5. `podeExpurgar(reg, agora)` só responde; quem expurga é gente, e
 *      nunca registro mais novo que isso.
 *   3. FORA DO ONEDRIVE. Pasta sincronizada (OneDrive, Dropbox, Google Drive, iCloud), inclusive
 *      por link ou junction, lança erro. O padrão é <VEEDHA_DADOS ou ~/veedha-dados>/registro-de-saida,
 *      a mesma pasta de dados que o conferir.js usa.
 *   4. FALHA FECHADA. Se não gravou (disco, pasta sincronizada, campo faltando, arquivo corrompido,
 *      cadeia quebrada), `registrar` lança, e a mensagem NÃO SAI: o registro é pré-condição do
 *      envio, não efeito dele (a fila chama antes de entregar ao canal; ver para-o-fila.md).
 *   5. CADEIA DE HASH. Cada linha leva o hash da anterior (`hashAnterior`) e o próprio (`hash` =
 *      sha256 da linha sem ele). Um arquivo por ano (registro-AAAA.jsonl, pelo ano UTC da hora do
 *      servidor); a cadeia atravessa a virada do ano. Linha mexida, apagada ou fora de ordem
 *      quebra a cadeia, e o `verificar` aponta a primeira.
 *
 * LINHA DE COMANDO
 *   node lib/registro.js verificar [--raiz PASTA]
 *       confere a cadeia inteira; sai 0 (íntegra) ou 1 (aponta arquivo:linha da 1ª adulterada)
 *   node lib/registro.js consultar --destino X --de AAAA-MM-DD --ate AAAA-MM-DD [--raiz PASTA]
 *       o que foi enviado a X no período (pela hora da mensagem, `em`), um JSON por linha
 *
 * DADO PESSOAL: este arquivo guarda dado de cliente por desenho. Por isso a pasta é fora da
 * sincronização, com permissão só do dono (pasta 700, arquivo 600).
 */

'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');

const RETENCAO_ANOS = 5;
const VEREDITOS_QUE_SAEM = Object.freeze(['LIVRE', 'REVISAR']);
const HASH_INICIAL = '0'.repeat(64);
const ARQUIVO_DO_ANO = /^registro-(\d{4})\.jsonl$/;
const SINCRONIZADA = /onedrive|dropbox|google ?drive|icloud/i;
const TRAVA_ESPERA_MS = 10000;
const TRAVA_VELHA_MS = 30000;
const LIMITE_TEXTO = 20000; // o mesmo teto do portão: o que passou por lá cabe aqui

const modoTeste = () => process.env.VEEDHA_MODO_TESTE === '1';
const sha256 = (s) => crypto.createHash('sha256').update(String(s), 'utf8').digest('hex');

/** A pasta padrão: a de dados da Veedha (a mesma do conferir.js), fora do OneDrive. */
function pastaPadrao() {
  return path.join(process.env.VEEDHA_DADOS || path.join(os.homedir(), 'veedha-dados'), 'registro-de-saida');
}

/** O caminho real, resolvendo link e junction até a parte que existe (como o conferir.js). */
function caminhoReal(caminho) {
  const resolvido = path.resolve(caminho);
  let atual = resolvido;
  const resto = [];
  for (;;) {
    try {
      const real = fs.realpathSync.native(atual);
      return resto.length ? path.join(real, ...resto.reverse()) : real;
    } catch (e) {
      const pai = path.dirname(atual);
      if (pai === atual) return resolvido;
      resto.push(path.basename(atual));
      atual = pai;
    }
  }
}

function pastaDoRegistro(opcoes) {
  const raiz = path.resolve((opcoes && opcoes.raiz) || pastaPadrao());
  const real = caminhoReal(raiz);
  if (SINCRONIZADA.test(raiz) || SINCRONIZADA.test(real)) {
    throw new Error(
      `registro de saida dentro de pasta sincronizada (OneDrive ou parecida): ${real}${real !== raiz ? ` (via ${raiz})` : ''}. ` +
        'Dado de cliente mora fora da sincronizacao; a mensagem nao sai.'
    );
  }
  return raiz;
}

// ---------------------------------------------------------------------------
// A linha e a cadeia
// ---------------------------------------------------------------------------

const ORDEM = ['seq', 'id', 'destino', 'canal', 'texto', 'veredito', 'regras', 'aprovadoPor', 'aprovadoEm', 'em', 'registradoEm', 'anexos', 'hashAnterior'];

/** A linha sem o hash, sempre na mesma ordem de chaves: é o que o hash cobre. */
function corpoDaLinha(r) {
  const o = {};
  for (const k of ORDEM) o[k] = r[k] === undefined ? null : r[k];
  return JSON.stringify(o);
}

const textoObrigatorio = (v) => typeof v === 'string' && v.trim().length > 0;
const dataValida = (v) => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}/.test(v) && !Number.isNaN(Date.parse(v));

/** Confere a saída e monta o registro (sem seq, cadeia e hora do servidor). Lança se faltar algo. */
function montarRegistro(saida) {
  if (!saida || typeof saida !== 'object' || Array.isArray(saida)) throw new Error('saida ausente ou malformada');
  const falta = ['id', 'destino', 'canal', 'texto'].filter((k) => !textoObrigatorio(saida[k]));
  if (falta.length) throw new Error(`saida sem ${falta.join(', ')}`);
  if (saida.id.length > 200) throw new Error('id da fila com mais de 200 caracteres');
  if (saida.texto.length > LIMITE_TEXTO) throw new Error(`texto com mais de ${LIMITE_TEXTO} caracteres`);
  if (!VEREDITOS_QUE_SAEM.includes(saida.veredito)) {
    throw new Error(`veredito "${saida.veredito}" nao sai: so ${VEREDITOS_QUE_SAEM.join(' ou ')} (o que o portao barrou nao e enviado)`);
  }
  const aprovadoPor = textoObrigatorio(saida.aprovadoPor) ? saida.aprovadoPor.trim() : null;
  const aprovadoEm = saida.aprovadoEm === undefined || saida.aprovadoEm === null || saida.aprovadoEm === '' ? null : saida.aprovadoEm;
  if (aprovadoEm !== null && !dataValida(aprovadoEm)) throw new Error('aprovadoEm nao e data valida');
  if (saida.veredito === 'REVISAR' && (!aprovadoPor || !aprovadoEm)) {
    throw new Error('veredito REVISAR sem aprovadoPor e aprovadoEm: texto livre so sai com aprovacao humana registrada');
  }
  if (saida.em !== undefined && saida.em !== null && !dataValida(saida.em)) throw new Error('em nao e data valida');
  const regras = saida.regras === undefined || saida.regras === null ? [] : saida.regras;
  if (!Array.isArray(regras) || regras.some((x) => typeof x !== 'string')) throw new Error('regras tem de ser lista de texto (R-xx)');
  let anexos = [];
  if (saida.anexos !== undefined && saida.anexos !== null) {
    if (!Array.isArray(saida.anexos)) throw new Error('anexos tem de ser lista');
    anexos = saida.anexos.map((a, i) => {
      if (!a || typeof a !== 'object' || !textoObrigatorio(a.nome)) throw new Error(`anexos[${i}] sem nome`);
      return { nome: a.nome.trim(), sha256: typeof a.sha256 === 'string' ? a.sha256.trim().toLowerCase() : null };
    });
  }
  return {
    id: saida.id,
    destino: saida.destino,
    canal: saida.canal,
    texto: saida.texto,
    veredito: saida.veredito,
    regras: [...regras],
    aprovadoPor,
    aprovadoEm,
    em: saida.em || null,
    anexos,
  };
}

/** Lê todos os arquivos do ano, em ordem, conferindo a cadeia. Nunca lança por conteúdo: devolve o problema. */
function lerCadeia(raiz) {
  let nomes;
  try {
    nomes = fs.readdirSync(raiz);
  } catch (e) {
    if (e && e.code === 'ENOENT') return { registros: [], arquivos: [], problema: null };
    throw e;
  }
  const arquivos = nomes.filter((n) => ARQUIVO_DO_ANO.test(n)).sort();
  const registros = [];
  let anterior = HASH_INICIAL;
  for (const nome of arquivos) {
    const linhas = fs.readFileSync(path.join(raiz, nome), 'utf8').split('\n');
    if (linhas[linhas.length - 1] === '') linhas.pop();
    for (let i = 0; i < linhas.length; i++) {
      const onde = { arquivo: nome, linha: i + 1 };
      let r;
      try {
        r = JSON.parse(linhas[i]);
      } catch (e) {
        return { registros, arquivos, problema: { ...onde, motivo: 'linha que nao e JSON (corrompida ou cortada)' } };
      }
      if (!r || typeof r !== 'object') return { registros, arquivos, problema: { ...onde, motivo: 'linha que nao e registro' } };
      if (r.seq !== registros.length + 1) return { registros, arquivos, problema: { ...onde, motivo: `seq ${r.seq}, esperado ${registros.length + 1} (linha apagada, repetida ou fora de ordem)` } };
      if (r.hashAnterior !== anterior) return { registros, arquivos, problema: { ...onde, motivo: 'hashAnterior nao bate com o hash da linha anterior (linha apagada ou trocada antes desta)' } };
      if (r.hash !== sha256(corpoDaLinha(r))) return { registros, arquivos, problema: { ...onde, motivo: 'hash nao bate com o conteudo (esta linha foi alterada)' } };
      registros.push(r);
      anterior = r.hash;
    }
  }
  return { registros, arquivos, problema: null };
}

const descrever = (p) => `${p.arquivo}:${p.linha}: ${p.motivo}`;

// ---------------------------------------------------------------------------
// A trava entre processos (dois robôs gravando ao mesmo tempo quebrariam a cadeia)
// ---------------------------------------------------------------------------

function dormir(ms) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
}

function comTrava(raiz, fn) {
  const trava = path.join(raiz, '.trava');
  const inicio = Date.now();
  for (;;) {
    try {
      fs.mkdirSync(trava);
      break;
    } catch (e) {
      if (!e || e.code !== 'EEXIST') throw e;
      let idade = 0;
      try {
        idade = Date.now() - fs.statSync(trava).mtimeMs;
      } catch (_) {
        continue; // soltou entre o mkdir e o stat: tenta de novo
      }
      if (idade > TRAVA_VELHA_MS) {
        fs.rmSync(trava, { recursive: true, force: true }); // trava de processo que morreu no meio
        continue;
      }
      if (Date.now() - inicio > TRAVA_ESPERA_MS) throw new Error(`registro ocupado por outro processo ha mais de ${TRAVA_ESPERA_MS / 1000} s`);
      dormir(50);
    }
  }
  try {
    return fn();
  } finally {
    fs.rmSync(trava, { recursive: true, force: true });
  }
}

// ---------------------------------------------------------------------------
// A API
// ---------------------------------------------------------------------------

/**
 * Grava UMA mensagem que vai sair. Lança se não gravou: quem chama não envia.
 * @param {object} saida   { id, destino, canal, texto, veredito, regras?, aprovadoPor?, aprovadoEm?, em?, anexos? }
 * @param {object} opcoes  { raiz? } (e `agora`, só em modo teste, para a virada do ano)
 * @returns {object} o registro gravado, com seq e hash
 */
function registrar(saida, opcoes = {}) {
  const raiz = pastaDoRegistro(opcoes);
  const base = montarRegistro(saida);
  const agora = modoTeste() && opcoes.agora ? new Date(opcoes.agora) : new Date();
  if (Number.isNaN(agora.getTime())) throw new Error('agora invalido');
  fs.mkdirSync(raiz, { recursive: true, mode: 0o700 });
  return comTrava(raiz, () => {
    const { registros, arquivos, problema } = lerCadeia(raiz);
    if (problema) throw new Error(`registro de saida com a cadeia quebrada em ${descrever(problema)}; nada sai ate alguem conferir (node lib/registro.js verificar)`);
    if (registros.some((r) => r.id === base.id)) throw new Error(`id "${base.id}" ja registrado (duplicado): registro de saida nao se reescreve`);
    const ultimo = registros[registros.length - 1] || null;
    const registradoEm = agora.toISOString();
    // Relógio que voltou não volta o arquivo: a linha vai para o ano mais novo já aberto, e a cadeia segue em ordem.
    const anoUltimo = arquivos.length ? Number(arquivos[arquivos.length - 1].match(ARQUIVO_DO_ANO)[1]) : 0;
    const ano = Math.max(agora.getUTCFullYear(), anoUltimo);
    const registro = Object.assign({ seq: registros.length + 1 }, base, {
      em: base.em || registradoEm,
      registradoEm,
      hashAnterior: ultimo ? ultimo.hash : HASH_INICIAL,
    });
    registro.hash = sha256(corpoDaLinha(registro));
    const arquivo = path.join(raiz, `registro-${ano}.jsonl`);
    const fd = fs.openSync(arquivo, 'a', 0o600);
    try {
      fs.writeSync(fd, JSON.stringify(registro) + '\n');
      fs.fsyncSync(fd);
    } finally {
      fs.closeSync(fd);
    }
    return JSON.parse(JSON.stringify(registro));
  });
}

/** Todos os registros, em ordem. Lança se a cadeia estiver quebrada: histórico adulterado não se lê calado. */
function ler(opcoes = {}) {
  const raiz = path.resolve((opcoes && opcoes.raiz) || pastaPadrao());
  const { registros, problema } = lerCadeia(raiz);
  if (problema) throw new Error(`registro de saida com a cadeia quebrada em ${descrever(problema)} (node lib/registro.js verificar)`);
  return registros;
}

/** A cadeia inteira confere? { ok, total, arquivos, problema } */
function verificarCadeia(opcoes = {}) {
  const raiz = path.resolve((opcoes && opcoes.raiz) || pastaPadrao());
  const { registros, arquivos, problema } = lerCadeia(raiz);
  return { ok: !problema, total: registros.length, arquivos, problema, raiz };
}

/** O que foi enviado a um destino num período (datas AAAA-MM-DD, inclusivas, pela hora da mensagem). */
function consultar({ destino, de, ate, raiz } = {}) {
  const dia = (v, nome) => {
    if (v === undefined || v === null || v === '') return null;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(v) || Number.isNaN(Date.parse(v))) throw new Error(`${nome} nao e data AAAA-MM-DD`);
    return v;
  };
  const d0 = dia(de, '--de');
  const d1 = dia(ate, '--ate');
  return ler({ raiz }).filter((r) => {
    if (destino && r.destino !== destino) return false;
    const d = String(r.em || r.registradoEm).slice(0, 10);
    return (!d0 || d >= d0) && (!d1 || d <= d1);
  });
}

/**
 * Já passou do prazo de guarda? Só responde; não apaga nada. Data ilegível = não (não dá para provar a idade).
 * @param {{em?: string, registradoEm?: string}} reg
 * @param {string|Date} [agora]
 */
function podeExpurgar(reg, agora) {
  const quando = Date.parse((reg && (reg.registradoEm || reg.em)) || '');
  const hoje = agora === undefined ? Date.now() : new Date(agora).getTime();
  if (Number.isNaN(quando) || Number.isNaN(hoje)) return false;
  const limite = new Date(quando);
  limite.setUTCFullYear(limite.getUTCFullYear() + RETENCAO_ANOS);
  return hoje >= limite.getTime();
}

/**
 * Para a fila: registra a saída a partir do item e do julgamento do portão, ou lança com
 * code SEM_REGISTRO. Portão que não liberou também lança: não se registra o que não sai.
 * @param {object} item        { id, destino, canal, texto, aprovadoPor?, aprovadoEm?, em?, anexos? }
 * @param {object} julgamento  o resultado de portao.verificar(texto, contexto)
 */
function registrarSaida(item, julgamento, opcoes = {}) {
  const semRegistro = (motivo) => Object.assign(new Error(`registro de saida nao gravado (${motivo}): a mensagem NAO sai`), { code: 'SEM_REGISTRO' });
  if (!julgamento || typeof julgamento !== 'object' || julgamento.passou !== true || !VEREDITOS_QUE_SAEM.includes(julgamento.veredito)) {
    throw semRegistro(`o portao nao liberou esta mensagem (veredito ${julgamento && julgamento.veredito})`);
  }
  const it = item && typeof item === 'object' ? item : {};
  const achados = [].concat(julgamento.revisar || [], julgamento.avisos || []);
  const regras = [...new Set(achados.map((x) => x && x.regra).filter((x) => typeof x === 'string'))].sort();
  try {
    return registrar(
      {
        id: it.id,
        destino: it.destino,
        canal: it.canal,
        texto: it.texto,
        veredito: julgamento.veredito,
        regras,
        aprovadoPor: it.aprovadoPor,
        aprovadoEm: it.aprovadoEm,
        em: it.em,
        anexos: it.anexos,
      },
      opcoes
    );
  } catch (e) {
    throw semRegistro(e && e.message);
  }
}

module.exports = Object.freeze({ registrar, ler, consultar, verificarCadeia, podeExpurgar, registrarSaida, pastaPadrao, RETENCAO_ANOS });

// ---------------------------------------------------------------------------
// Linha de comando
// ---------------------------------------------------------------------------

if (require.main === module) {
  const args = process.argv.slice(2);
  const opcao = (nome) => {
    const i = args.indexOf(nome);
    return i >= 0 ? args[i + 1] : undefined;
  };
  const raiz = opcao('--raiz');
  try {
    if (args[0] === 'verificar') {
      const v = verificarCadeia({ raiz });
      if (v.ok) {
        console.log(v.total ? `registro integro: ${v.total} registro(s) em ${v.arquivos.join(', ')} (${v.raiz})` : `nenhum registro ainda em ${v.raiz}`);
        process.exit(0);
      }
      console.log(`ADULTERADO a partir de ${descrever(v.problema)} (${v.raiz}); ${v.total} registro(s) integro(s) antes dele`);
      process.exit(1);
    } else if (args[0] === 'consultar') {
      const achados = consultar({ destino: opcao('--destino'), de: opcao('--de'), ate: opcao('--ate'), raiz });
      for (const r of achados) console.log(JSON.stringify(r));
      console.error(`${achados.length} registro(s)`);
      process.exit(0);
    } else {
      console.log('uso: node lib/registro.js verificar [--raiz PASTA]');
      console.log('     node lib/registro.js consultar --destino X --de AAAA-MM-DD --ate AAAA-MM-DD [--raiz PASTA]');
      console.log(`pasta padrao: ${pastaPadrao()} · guarda: ${RETENCAO_ANOS} anos`);
      process.exit(args.length ? 2 : 0);
    }
  } catch (e) {
    console.error(`erro: ${e.message}`);
    process.exit(1);
  }
}
