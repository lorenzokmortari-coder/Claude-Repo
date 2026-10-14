#!/usr/bin/env node
// Barra de status do Claude Code com a cota real do plano (janela de 5 h e de 7 dias) e um
// registro de no máximo 1 linha por minuto em ~/.claude/cota.jsonl.
//
// Campos lidos (documentação oficial, code.claude.com/docs/en/statusline, conferida em 14/10/2026):
//   rate_limits.five_hour.used_percentage / .resets_at   (0 a 100; Unix epoch em segundos)
//   rate_limits.seven_day.used_percentage / .resets_at
//   model.id, model.display_name, session_id, workspace.current_dir, context_window.used_percentage
// rate_limits só vem para assinante Pro/Max (ou atrás de um gateway com limite de gasto), só depois
// da primeira resposta da API na sessão, e cada janela pode faltar. Sem janela, não grava linha.
//
// Sem dependência: só Node (fs, os, path, child_process). Settings (~/.claude/settings.json):
//   "statusLine": { "type": "command", "command": "node ~/.claude/statusline-cota.mjs", "refreshInterval": 60 }
// O refreshInterval de 60 s faz a barra rodar (e gravar) também com a sessão parada.
//
// Opcional: ~/.claude/cota-base.txt com o comando da barra que você já usava. Ela recebe o mesmo
// JSON e a saída dela aparece antes do trecho da cota.
// Só para teste: COTA_DIR (pasta no lugar de ~/.claude) e COTA_AGORA_MS (relógio fixo).
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";

const DIR = process.env.COTA_DIR || path.join(os.homedir(), ".claude");
const ARQUIVO = path.join(DIR, "cota.jsonl");
const ESTADO = path.join(DIR, "cota.ultimo");
const BASE = path.join(DIR, "cota-base.txt");
const DIAS = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"];
const COR = { verde: "\x1b[32m", amarelo: "\x1b[33m", vermelho: "\x1b[31m", fim: "\x1b[0m", cinza: "\x1b[2m" };

function lerStdin() {
  try {
    return fs.readFileSync(0, "utf8");
  } catch {
    return "";
  }
}

const num = (x) => (typeof x === "number" && Number.isFinite(x) ? x : null);
const dois = (n) => String(Math.trunc(Math.abs(n))).padStart(2, "0");

function horaLocal(d) {
  const off = -d.getTimezoneOffset();
  const sinal = off >= 0 ? "+" : "-";
  return `${d.getFullYear()}-${dois(d.getMonth() + 1)}-${dois(d.getDate())}T${dois(d.getHours())}:` +
    `${dois(d.getMinutes())}:${dois(d.getSeconds())}${sinal}${dois(off / 60)}:${dois(off % 60)}`;
}

// As cores e os blocos usam o percentual já arredondado, igual ao statusline-cota.sh.
function cor(pct) {
  const p = Math.round(pct);
  return p >= 80 ? COR.vermelho : p >= 50 ? COR.amarelo : COR.verde;
}

function barra(pct) {
  const cheios = Math.max(0, Math.min(10, Math.round(Math.round(pct) / 10)));
  return "▓".repeat(cheios) + "░".repeat(10 - cheios);
}

function quando(epoch, agora, comDia) {
  if (epoch === null) return "";
  const d = new Date(epoch * 1000);
  const hm = `${dois(d.getHours())}:${dois(d.getMinutes())}`;
  const mesmoDia = d.toDateString() === agora.toDateString();
  return comDia && !mesmoDia ? `${DIAS[d.getDay()]} ${hm}` : hm;
}

function trechoCota(j5, j7, agora) {
  const partes = [];
  if (j5 && j5.pct !== null) {
    partes.push(`5h ${cor(j5.pct)}${barra(j5.pct)} ${Math.round(j5.pct)}%${COR.fim}` +
      (j5.reset !== null ? ` ${COR.cinza}↻${quando(j5.reset, agora, true)}${COR.fim}` : ""));
  }
  if (j7 && j7.pct !== null) {
    partes.push(`7d ${cor(j7.pct)}${Math.round(j7.pct)}%${COR.fim}` +
      (j7.reset !== null ? ` ${COR.cinza}↻${quando(j7.reset, agora, true)}${COR.fim}` : ""));
  }
  return partes.join(" · ");
}

function barraPadrao(d) {
  const modelo = d.model?.display_name || d.model?.id || "?";
  const pasta = String(d.workspace?.current_dir || d.cwd || "").split(/[\\/]/).filter(Boolean).pop() || "";
  const ctx = num(d.context_window?.used_percentage);
  return `[${modelo}]` + (pasta ? ` ${pasta}` : "") + ` | ctx ${ctx === null ? "--" : Math.round(ctx) + "%"}`;
}

function barraBase(bruto) {
  let cmd = "";
  try {
    cmd = fs.readFileSync(BASE, "utf8").split(/\r?\n/)[0].trim();
  } catch {
    return "";
  }
  if (!cmd) return "";
  const r = spawnSync(cmd, { input: bruto, shell: true, encoding: "utf8", timeout: 2500 });
  return (r.stdout || "").replace(/\s+$/, "");
}

function registrar(d, j5, j7, agora) {
  if ((!j5 || j5.pct === null) && (!j7 || j7.pct === null)) return;
  const hora = horaLocal(agora);
  const minuto = hora.slice(0, 16);
  let ultimo = "";
  try {
    ultimo = fs.readFileSync(ESTADO, "utf8").trim();
  } catch {
    // primeira vez
  }
  if (ultimo === minuto) return;
  try {
    fs.mkdirSync(DIR, { recursive: true });
    const linha = {
      hora,
      pct_5h: j5 ? j5.pct : null, reset_5h: j5 ? j5.reset : null,
      pct_7d: j7 ? j7.pct : null, reset_7d: j7 ? j7.reset : null,
      modelo: d.model?.id ?? null, modelo_nome: d.model?.display_name ?? null, sessao: d.session_id ?? null,
    };
    fs.appendFileSync(ARQUIVO, JSON.stringify(linha) + "\n");
    fs.writeFileSync(ESTADO, minuto);
  } catch {
    // a barra continua aparecendo mesmo se o disco falhar
  }
}

function janela(obj) {
  if (!obj || typeof obj !== "object") return null;
  return { pct: num(obj.used_percentage), reset: num(obj.resets_at) };
}

const bruto = lerStdin();
let dados = {};
try {
  dados = JSON.parse(bruto) || {};
} catch {
  dados = {};
}
const agora = new Date(Number(process.env.COTA_AGORA_MS) || Date.now());
const j5 = janela(dados.rate_limits?.five_hour);
const j7 = janela(dados.rate_limits?.seven_day);
registrar(dados, j5, j7, agora);

const principal = barraBase(bruto) || barraPadrao(dados);
const cota = trechoCota(j5, j7, agora);
process.stdout.write(cota ? (principal.includes("\n") ? `${principal}\n${cota}\n` : `${principal} | ${cota}\n`) : `${principal}\n`);
