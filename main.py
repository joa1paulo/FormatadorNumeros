"""Etapa 6: interface web com dashboard (FastAPI). Rodar com: uvicorn main:app --reload"""
import base64

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse

from processador import previa_csv
from servico import executar

app = FastAPI(title="Formatador de Contatos")

PAGINA = r"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Formatador de Contatos</title>
<style>
  :root { --bg:#f6f7f9; --card:#fff; --texto:#1c1e21; --suave:#667085; --borda:#e4e7ec;
          --novos:#16a34a; --ja:#2563eb; --fixos:#d97706; --inv:#dc2626; --dup:#7c3aed; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#14161a; --card:#1d2025; --texto:#eceef1; --suave:#9aa1ac; --borda:#2c3037; }
  }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--texto); font-family: system-ui, sans-serif; }
  main { max-width: 860px; margin: 0 auto; padding: 24px 16px 64px; }
  h1 { font-size: 1.5rem; margin: 0 0 20px; }
  section { background:var(--card); border:1px solid var(--borda); border-radius:12px; padding:20px; margin-bottom:20px; }
  h2 { font-size:1.05rem; margin:0 0 14px; }
  label { display:block; margin-top:14px; font-weight:600; }
  small { font-weight:400; color:var(--suave); }
  input[type=file], select { display:block; margin-top:6px; max-width:100%; }
  button, .botao { margin-top:20px; padding:10px 20px; font-size:1rem; border:0; border-radius:8px;
          background:var(--ja); color:#fff; cursor:pointer; text-decoration:none; display:inline-block; }
  button:disabled { opacity:.6; cursor:wait; }
  .cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(130px,1fr)); gap:12px; }
  .card { border:1px solid var(--borda); border-radius:10px; padding:12px; border-left:5px solid var(--cor); }
  .card b { display:block; font-size:1.6rem; }
  .card span { color:var(--suave); font-size:.85rem; }
  .barra { display:flex; height:16px; border-radius:8px; overflow:hidden; background:var(--borda); margin:18px 0 8px; }
  .barra div { height:100%; transition: width .4s; }
  .legenda { display:flex; flex-wrap:wrap; gap:6px 16px; font-size:.85rem; color:var(--suave); }
  .legenda i { display:inline-block; width:10px; height:10px; border-radius:3px; margin-right:5px; }
  .erro { color:var(--inv); margin-top:12px; font-weight:600; }
  .oculto { display:none; }
  table { border-collapse:collapse; width:100%; font-size:.9rem; }
  td, th { text-align:left; padding:6px 8px; border-bottom:1px solid var(--borda); }
  .previa { margin-top:8px; overflow-x:auto; font-weight:400; }
  .previa small { display:block; margin-bottom:6px; }
  .previa .col { background:rgba(37,99,235,.14); font-weight:600; }
  .uploads { display:grid; grid-template-columns:1fr 1fr; gap:20px; align-items:start; }
  .uploads.so-um { grid-template-columns:1fr; }
  .upload { min-width:0; }
  @media (max-width:640px) { .uploads { grid-template-columns:1fr; } }
  .modo { display:flex; align-items:center; gap:10px; flex-wrap:wrap; font-weight:600; }
  .modo > span { color:var(--suave); }
  .modo > span.ativo { color:var(--texto); }
  .switch { position:relative; display:inline-block; width:46px; height:26px; margin:0; }
  .switch input { position:absolute; opacity:0; width:0; height:0; }
  .slider { position:absolute; inset:0; background:#98a2b3; border-radius:26px; cursor:pointer; transition:.2s; }
  .slider::before { content:""; position:absolute; width:20px; height:20px; left:3px; top:3px;
                    background:#fff; border-radius:50%; transition:.2s; }
  .switch input:checked + .slider { background:var(--ja); }
  .switch input:checked + .slider::before { transform:translateX(20px); }
  .switch input:focus-visible + .slider { outline:2px solid var(--ja); outline-offset:2px; }
</style>
</head>
<body>
<main>
  <h1>Formatador de Contatos</h1>

  <section>
    <h2>1. Enviar arquivos</h2>
    <form id="form">
      <div class="modo">
        <span id="txt-processar">Somente processar</span>
        <label class="switch" title="Alternar entre somente processar e mesclar">
          <input type="checkbox" id="modo-mesclar" checked>
          <span class="slider"></span>
        </label>
        <span id="txt-mesclar">Mesclar com já contatados</span>
      </div>
      <div class="uploads" id="uploads">
        <div class="upload">
          <label>Lista de números <small>(obrigatório, CSV)</small>
            <input type="file" name="talvez" accept=".csv" required>
          </label>
          <div class="previa" id="previa-talvez"></div>
        </div>
        <div class="upload" id="bloco-contatados">
          <label>Já contatados <small>(CSV; serão removidos da lista principal)</small>
            <input type="file" name="contatados" accept=".csv">
          </label>
          <div class="previa" id="previa-contatados"></div>
        </div>
      </div>
      <label>Formato de exportação
        <select name="formato">
          <option value="csv">CSV</option>
          <option value="txt">TXT (um número por linha)</option>
        </select>
      </label>
      <button type="submit" id="btn">Processar</button>
      <div id="erro" class="erro"></div>
    </form>
  </section>

  <section id="resultado" class="oculto">
    <h2>2. Resultado</h2>
    <div class="cards" id="cards"></div>
    <div class="barra" id="barra"></div>
    <div class="legenda" id="legenda"></div>
    <div id="contatados" class="oculto" style="margin-top:20px">
      <h2>Arquivo de já contatados</h2>
      <table id="tabela-contatados"></table>
    </div>
    <a class="botao" id="download" href="#">Baixar resultados (.zip)</a>
  </section>
</main>

<script>
const form = document.getElementById("form");
const btn = document.getElementById("btn");
const erro = document.getElementById("erro");
let urlAnterior = null;

const CAMPOS = [
  ["total", "Lidos", "#667085", false],
  ["novos", "Novos (prontos)", "var(--novos)", true],
  ["ja_contatados_removidos", "Já contatados removidos", "var(--ja)", true],
  ["fixos", "Fixos (separados)", "var(--fixos)", true],
  ["invalidos", "Inválidos", "var(--inv)", true],
  ["duplicados", "Duplicados removidos", "var(--dup)", true],
];

function renderizar(est) {
  const l = est.lista;
  const campos = est.contatados ? CAMPOS : CAMPOS.filter(c => c[0] !== "ja_contatados_removidos");
  const cartoes = est.contatados ? [...campos, ["mesclados", "Total mesclado (união)", "#0891b2", false]] : campos;
  document.getElementById("cards").innerHTML = cartoes.map(([k, nome, cor]) =>
    `<div class="card" style="--cor:${cor}"><b>${l[k].toLocaleString("pt-BR")}</b><span>${nome}</span></div>`
  ).join("");

  const total = l.total || 1;
  const partes = campos.filter(c => c[3]);
  document.getElementById("barra").innerHTML = partes.map(([k, nome, cor]) =>
    `<div title="${nome}: ${l[k]}" style="width:${(l[k] / total) * 100}%;background:${cor}"></div>`
  ).join("");
  document.getElementById("legenda").innerHTML = partes.map(([k, nome, cor]) =>
    `<span><i style="background:${cor}"></i>${nome}: ${((l[k] / total) * 100).toFixed(1)}%</span>`
  ).join("");

  const c = est.contatados;
  const blocoC = document.getElementById("contatados");
  if (c) {
    document.getElementById("tabela-contatados").innerHTML =
      `<tr><th>Lidos</th><th>Válidos</th><th>Fixos</th><th>Inválidos</th><th>Duplicados</th></tr>` +
      `<tr><td>${c.total}</td><td>${c.validos}</td><td>${c.fixos}</td><td>${c.invalidos}</td><td>${c.duplicados}</td></tr>`;
    blocoC.classList.remove("oculto");
  } else {
    blocoC.classList.add("oculto");
  }
}

// --- previa:inicio
const NOME_SEP = { ",": "vírgula", ";": "ponto e vírgula", "\t": "tabulação" };

function esc(s) {
  return String(s).replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function montarPrevia(d) {
  if (d.vazio) return "<small>Arquivo vazio.</small>";
  const cab = d.cabecalho, idx = d.idx_numero;
  const cabHtml = cab.map((c, i) => `<th class="${i === idx ? "col" : ""}">${esc(c)}</th>`).join("");
  const corpoHtml = d.linhas.map(r =>
    "<tr>" + cab.map((_, i) => `<td class="${i === idx ? "col" : ""}">${esc(r[i] ?? "")}</td>`).join("") + "</tr>"
  ).join("");
  const aviso = d.tem_cabecalho ? "" : " · <b>sem cabeçalho</b> (a 1ª linha também é dado)";
  return `<small>${d.total_linhas} linhas de dados · separador: ${NOME_SEP[d.delimitador] ?? esc(d.delimitador)}${aviso}` +
         ` · coluna lida como número: <b>${esc(cab[idx])}</b> · mostrando as primeiras ${d.linhas.length}</small>` +
         `<table><tr>${cabHtml}</tr>${corpoHtml}</table>`;
}

async function previa(input, alvoId) {
  const alvo = document.getElementById(alvoId);
  const arquivo = input.files[0];
  if (!arquivo) { alvo.innerHTML = ""; return; }
  try {
    const fd = new FormData();
    fd.append("arquivo", arquivo);
    const resp = await fetch("/previa", { method: "POST", body: fd });
    if (!resp.ok) throw new Error("falha");
    alvo.innerHTML = montarPrevia(await resp.json());
  } catch (ex) {
    alvo.innerHTML = "<small>Não foi possível gerar a pré-visualização.</small>";
  }
}
// --- previa:fim

document.querySelector('input[name="talvez"]')
  .addEventListener("change", e => previa(e.target, "previa-talvez"));
document.querySelector('input[name="contatados"]')
  .addEventListener("change", e => previa(e.target, "previa-contatados"));

// --- modo:inicio
const chkMesclar = document.getElementById("modo-mesclar");

function aplicarModo() {
  const mesclar = chkMesclar.checked;
  document.getElementById("bloco-contatados").classList.toggle("oculto", !mesclar);
  document.getElementById("uploads").classList.toggle("so-um", !mesclar);
  document.getElementById("txt-mesclar").classList.toggle("ativo", mesclar);
  document.getElementById("txt-processar").classList.toggle("ativo", !mesclar);
  if (!mesclar) {  // limpa o arquivo escolhido para que ele não seja enviado
    document.querySelector('input[name="contatados"]').value = "";
    document.getElementById("previa-contatados").innerHTML = "";
  }
}
// --- modo:fim
chkMesclar.addEventListener("change", aplicarModo);
aplicarModo();

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  erro.textContent = "";
  btn.disabled = true;
  btn.textContent = "Processando...";
  try {
    const fd = new FormData(form);
    if (!chkMesclar.checked) fd.delete("contatados");
    const resp = await fetch("/processar", { method: "POST", body: fd });
    const dados = await resp.json();
    if (!resp.ok) throw new Error(dados.detail || "Erro ao processar os arquivos.");

    renderizar(dados.estatisticas);

    const bytes = Uint8Array.from(atob(dados.zip_base64), ch => ch.charCodeAt(0));
    if (urlAnterior) URL.revokeObjectURL(urlAnterior);
    urlAnterior = URL.createObjectURL(new Blob([bytes], { type: "application/zip" }));
    const link = document.getElementById("download");
    link.href = urlAnterior;
    link.download = "contatos_formatados.zip";
    document.getElementById("resultado").classList.remove("oculto");
  } catch (ex) {
    erro.textContent = ex.message;
  } finally {
    btn.disabled = false;
    btn.textContent = "Processar";
  }
});
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def home():
    return PAGINA


@app.post("/previa")
async def previa(arquivo: UploadFile = File(...)):
    return previa_csv(await arquivo.read())


@app.post("/processar")
async def processar(
    talvez: UploadFile = File(...),
    contatados: UploadFile | None = File(None),
    formato: str = Form("csv"),
):
    if formato not in ("csv", "txt"):
        raise HTTPException(400, "Formato deve ser 'csv' ou 'txt'.")

    conteudo_talvez = await talvez.read()
    conteudo_contatados = await contatados.read() if contatados and contatados.filename else None

    try:
        zip_bytes, estatisticas = executar(conteudo_talvez, conteudo_contatados, formato)
    except UnicodeDecodeError:
        raise HTTPException(400, "Não foi possível ler o arquivo. Salve o CSV como UTF-8.")

    return {
        "estatisticas": estatisticas,
        "zip_base64": base64.b64encode(zip_bytes).decode("ascii"),
    }
