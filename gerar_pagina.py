#!/usr/bin/env python3
"""
Gera a página diária de achados da Shopee.

Busca os produtos mais vendidos pela Open API de Afiliados da Shopee Brasil,
gera o seu link de afiliado e monta uma página com imagem + texto + link
prontos para copiar e colar nos grupos.

Uso:
    python gerar_pagina.py          # usa a API (precisa de SHOPEE_APP_ID e SHOPEE_SECRET)
    python gerar_pagina.py --demo   # gera a página com produtos de exemplo
"""
import argparse
import datetime
import hashlib
import html
import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

ENDPOINT = "https://open-api.affiliate.shopee.com.br/graphql"
BASE = Path(__file__).resolve().parent
SITE = BASE / "site"
CONFIG = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
HOJE = datetime.datetime.now(ZoneInfo("America/Sao_Paulo"))


# ---------------------------------------------------------------- API Shopee
def chamar_api(query: str) -> dict:
    app_id = os.environ.get("SHOPEE_APP_ID")
    secret = os.environ.get("SHOPEE_SECRET")
    if not app_id or not secret:
        sys.exit("Faltam SHOPEE_APP_ID e SHOPEE_SECRET (veja o LEIA-ME).")
    payload = json.dumps({"query": query}, separators=(",", ":"))
    ts = str(int(time.time()))
    assinatura = hashlib.sha256((app_id + ts + payload + secret).encode()).hexdigest()
    req = urllib.request.Request(
        ENDPOINT,
        data=payload.encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"SHA256 Credential={app_id}, Timestamp={ts}, Signature={assinatura}",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        dados = json.load(resp)
    if dados.get("errors"):
        raise RuntimeError(json.dumps(dados["errors"], ensure_ascii=False))
    return dados["data"]


def buscar_produtos(palavra: str, limite: int = 50) -> list:
    filtro = f"keyword: {json.dumps(palavra)}, " if palavra else ""
    # sortType 2 = mais vendidos
    query = (
        "{ productOfferV2(" + filtro + f"sortType: 2, page: 1, limit: {limite}) "
        "{ nodes { itemId productName price priceMin priceMax priceDiscountRate "
        "sales ratingStar commissionRate imageUrl offerLink productLink shopName } } }"
    )
    return chamar_api(query)["productOfferV2"]["nodes"] or []


def link_curto(link: str) -> str:
    """Tenta encurtar (shopee.ee/...). Se falhar, usa o link de afiliado original."""
    sub = json.dumps(["achados", HOJE.strftime("%Y%m%d")])
    query = (
        "mutation { generateShortLink(input: {originUrl: "
        + json.dumps(link) + ", subIds: " + sub + "}) { shortLink } }"
    )
    try:
        return chamar_api(query)["generateShortLink"]["shortLink"] or link
    except Exception:
        return link


# ---------------------------------------------------------------- seleção
def num(v, padrao=0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return padrao


def selecionar(todos: list) -> list:
    vistos, bons = set(), []
    for p in todos:
        if p.get("itemId") in vistos:
            continue
        vistos.add(p.get("itemId"))
        if num(p.get("ratingStar")) < CONFIG["nota_minima"]:
            continue
        if num(p.get("sales")) < CONFIG["vendas_minimas"]:
            continue
        bons.append(p)
    bons.sort(key=lambda p: num(p.get("sales")), reverse=True)
    return bons[: CONFIG["quantidade_produtos"]]


# ---------------------------------------------------------------- texto do post
def reais(v: float) -> str:
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def vendidos(v: float) -> str:
    v = int(v)
    return f"{v/1000:.1f} mil".replace(".0 mil", " mil").replace(".", ",") if v >= 1000 else str(v)


def montar_texto(p: dict, link: str) -> str:
    preco = num(p.get("priceMin")) or num(p.get("price"))
    desconto = int(num(p.get("priceDiscountRate")))
    nome = p.get("productName", "").strip()
    if len(nome) > 90:
        nome = nome[:87].rstrip() + "..."
    linhas = [CONFIG["titulo_post"], "", nome, ""]
    if desconto > 0 and preco:
        original = preco / (1 - desconto / 100)
        linhas.append(f"💰 De ~{reais(original)}~ por *{reais(preco)}* ({desconto}% OFF)")
    elif preco:
        linhas.append(f"💰 Por *{reais(preco)}*")
    linhas.append(f"⭐ {num(p.get('ratingStar')):.1f} | {vendidos(num(p.get('sales')))} vendidos")
    linhas += ["", f"🛒 Compre aqui: {link}", "", CONFIG["rodape_post"]]
    return "\n".join(linhas)


# ---------------------------------------------------------------- página
def gerar_html(itens: list) -> str:
    data_txt = HOJE.strftime("%d/%m/%Y")
    hora_txt = HOJE.strftime("%H:%M")
    cards = []
    for i, it in enumerate(itens, 1):
        comissao = num(it.get("commissionRate")) * 100
        cards.append(f"""
    <article class="card" data-id="{html.escape(str(it['itemId']))}">
      <div class="img-wrap">
        <span class="rank">#{i}</span>
        <img src="{html.escape(it['imageUrl'])}" alt="" loading="lazy">
      </div>
      <div class="corpo">
        <div class="meta">
          <span>{vendidos(num(it.get('sales')))} vendidos</span>
          <span>Comissão {comissao:.1f}%</span>
        </div>
        <pre class="texto">{html.escape(it['texto'])}</pre>
        <div class="botoes">
          <button class="principal" data-acao="texto">Copiar texto</button>
          <button data-acao="imagem">Copiar imagem</button>
          <a class="btn" href="{html.escape(it['imageUrl'])}" target="_blank" rel="noopener">Abrir imagem</a>
          <button data-acao="link">Copiar link</button>
        </div>
        <label class="postado"><input type="checkbox"> Já postei</label>
      </div>
    </article>""")

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Achados do Dia</title>
<style>
:root {{
  --bg:#f6f4f1; --card:#fff; --tx:#1d1b19; --mut:#6b665f; --borda:#e6e1da;
  --acento:#ee4d2d; --acento-tx:#fff; --ok:#1f8a4c; --pre:#faf8f5;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --bg:#151413; --card:#1f1d1b; --tx:#f1ede8; --mut:#a39d95; --borda:#34312d;
    --acento:#ff6a45; --acento-tx:#1a0d08; --ok:#4cc583; --pre:#191816;
  }}
}}
:root[data-theme="dark"] {{
  --bg:#151413; --card:#1f1d1b; --tx:#f1ede8; --mut:#a39d95; --borda:#34312d;
  --acento:#ff6a45; --acento-tx:#1a0d08; --ok:#4cc583; --pre:#191816;
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--tx);
  font:15px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }}
header {{ max-width:1200px; margin:0 auto; padding:28px 16px 8px; }}
h1 {{ margin:0; font-size:26px; letter-spacing:-.01em; }}
.sub {{ color:var(--mut); margin-top:4px; }}
.progresso {{ margin-top:10px; font-weight:600; }}
main {{ max-width:1200px; margin:0 auto; padding:16px;
  display:grid; gap:16px; grid-template-columns:repeat(auto-fill,minmax(290px,1fr)); }}
.card {{ background:var(--card); border:1px solid var(--borda); border-radius:14px;
  overflow:hidden; display:flex; flex-direction:column; transition:opacity .2s; }}
.card.feito {{ opacity:.45; }}
.img-wrap {{ position:relative; aspect-ratio:1; background:var(--pre); }}
.img-wrap img {{ width:100%; height:100%; object-fit:cover; display:block; }}
.rank {{ position:absolute; top:10px; left:10px; background:var(--acento); color:var(--acento-tx);
  font-weight:700; padding:2px 9px; border-radius:20px; font-size:13px; }}
.corpo {{ padding:12px; display:flex; flex-direction:column; gap:10px; flex:1; }}
.meta {{ display:flex; justify-content:space-between; color:var(--mut); font-size:13px; }}
.texto {{ margin:0; white-space:pre-wrap; word-break:break-word; font:inherit; font-size:14px;
  background:var(--pre); border:1px solid var(--borda); border-radius:10px; padding:10px; flex:1; }}
.botoes {{ display:grid; grid-template-columns:1fr 1fr; gap:8px; }}
button, .btn {{ font:inherit; font-size:14px; padding:9px 8px; border-radius:9px; cursor:pointer;
  border:1px solid var(--borda); background:var(--card); color:var(--tx); text-align:center;
  text-decoration:none; }}
button.principal {{ background:var(--acento); color:var(--acento-tx); border-color:var(--acento);
  font-weight:600; }}
button.ok {{ background:var(--ok); border-color:var(--ok); color:#fff; }}
.postado {{ color:var(--mut); font-size:14px; display:flex; gap:6px; align-items:center; }}
.aviso {{ position:fixed; left:50%; bottom:20px; transform:translateX(-50%); background:var(--tx);
  color:var(--bg); padding:10px 16px; border-radius:10px; font-size:14px; opacity:0;
  transition:opacity .2s; pointer-events:none; max-width:calc(100% - 32px); }}
.aviso.on {{ opacity:1; }}
</style>
</head>
<body>
<header>
  <h1>Achados do Dia</h1>
  <div class="sub">Shopee • mais vendidos de {data_txt} • atualizado às {hora_txt}</div>
  <div class="progresso" id="progresso"></div>
</header>
<main>{''.join(cards)}
</main>
<div class="aviso" id="aviso"></div>
<script>
const DIA = "{HOJE.strftime('%Y-%m-%d')}";
const chave = id => "postado-" + DIA + "-" + id;
const aviso = document.getElementById("aviso");
function avisar(msg) {{
  aviso.textContent = msg; aviso.classList.add("on");
  clearTimeout(avisar.t); avisar.t = setTimeout(() => aviso.classList.remove("on"), 2200);
}}
function lerMarca(id) {{ try {{ return localStorage.getItem(chave(id)) === "1"; }} catch (e) {{ return false; }} }}
function gravarMarca(id, v) {{ try {{ v ? localStorage.setItem(chave(id), "1") : localStorage.removeItem(chave(id)); }} catch (e) {{}} }}
function atualizarProgresso() {{
  const total = document.querySelectorAll(".card").length;
  const feitos = document.querySelectorAll(".card.feito").length;
  document.getElementById("progresso").textContent = feitos + " de " + total + " postados hoje";
}}
async function copiarTexto(t) {{
  try {{ await navigator.clipboard.writeText(t); return true; }}
  catch (e) {{
    const a = document.createElement("textarea"); a.value = t; document.body.appendChild(a);
    a.select(); const ok = document.execCommand("copy"); a.remove(); return ok;
  }}
}}
async function copiarImagem(url) {{
  const img = new Image(); img.crossOrigin = "anonymous"; img.src = url;
  await img.decode();
  const c = document.createElement("canvas"); c.width = img.naturalWidth; c.height = img.naturalHeight;
  c.getContext("2d").drawImage(img, 0, 0);
  const blob = await new Promise(r => c.toBlob(r, "image/png"));
  await navigator.clipboard.write([new ClipboardItem({{ "image/png": blob }})]);
}}
document.querySelectorAll(".card").forEach(card => {{
  const id = card.dataset.id;
  const caixa = card.querySelector(".postado input");
  const texto = card.querySelector(".texto").textContent;
  const link = (texto.match(/https?:\\/\\/\\S+/) || [""])[0];
  const imagem = card.querySelector("img").src;
  caixa.checked = lerMarca(id); card.classList.toggle("feito", caixa.checked);
  caixa.addEventListener("change", () => {{
    gravarMarca(id, caixa.checked); card.classList.toggle("feito", caixa.checked); atualizarProgresso();
  }});
  card.querySelectorAll("button").forEach(b => b.addEventListener("click", async () => {{
    const acao = b.dataset.acao, rotulo = b.textContent;
    try {{
      if (acao === "texto") await copiarTexto(texto);
      if (acao === "link") await copiarTexto(link);
      if (acao === "imagem") await copiarImagem(imagem);
      b.classList.add("ok"); b.textContent = "Copiado!";
      setTimeout(() => {{ b.classList.remove("ok"); b.textContent = rotulo; }}, 1500);
    }} catch (e) {{
      avisar(acao === "imagem" ? "Não deu para copiar a imagem aqui. Use “Abrir imagem” e salve." : "Não consegui copiar. Selecione o texto e copie.");
    }}
  }}));
}});
atualizarProgresso();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------- demo
def produtos_demo() -> list:
    cores = ["#ee4d2d", "#2d7fee", "#1f8a4c", "#a03fd6", "#e0a100", "#d6336c"]
    nomes = [
        ("Mini Processador Elétrico de Alimentos USB Recarregável 250ml", 39.9, 45, 18200, 4.9),
        ("Kit 10 Potes Herméticos de Vidro com Tampa Bambu", 89.9, 38, 9400, 4.8),
        ("Escova Secadora Rotativa 3 em 1 Íons Negativos", 119.0, 52, 7300, 4.7),
        ("Fone Bluetooth TWS Cancelamento de Ruído Estojo LED", 49.9, 60, 25100, 4.6),
        ("Organizador de Maquiagem Giratório 360° Acrílico", 34.9, 30, 5200, 4.8),
        ("Garrafa Térmica Inox 1L com Indicador de Temperatura", 42.5, 25, 11800, 4.9),
    ]
    prods = []
    for i, (n, preco, desc, vend, nota) in enumerate(nomes):
        svg = (f"<svg xmlns='http://www.w3.org/2000/svg' width='600' height='600'>"
               f"<rect width='600' height='600' fill='{cores[i]}'/>"
               f"<text x='300' y='320' font-size='44' font-family='sans-serif' fill='white' "
               f"text-anchor='middle'>Produto {i+1}</text></svg>")
        prods.append({
            "itemId": 1000 + i, "productName": n, "priceMin": preco, "priceDiscountRate": desc,
            "sales": vend, "ratingStar": nota, "commissionRate": 0.08 + i * 0.01,
            "imageUrl": "data:image/svg+xml;utf8," + urllib.request.quote(svg),
            "offerLink": f"https://s.shopee.com.br/exemplo{i+1}",
        })
    return prods


# ---------------------------------------------------------------- principal
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="usa produtos de exemplo, sem API")
    args = ap.parse_args()

    if args.demo:
        escolhidos = produtos_demo()
    else:
        todos = []
        for palavra in CONFIG["palavras_chave"]:
            try:
                todos += buscar_produtos(palavra)
            except Exception as e:
                print(f"Aviso: busca '{palavra}' falhou: {e}", file=sys.stderr)
        escolhidos = selecionar(todos)
        if not escolhidos:
            sys.exit("Nenhum produto encontrado. Confira as credenciais e o config.json.")

    itens = []
    for p in escolhidos:
        link = p.get("offerLink") if args.demo else link_curto(p.get("offerLink") or p.get("productLink"))
        itens.append({**p, "link": link, "texto": montar_texto(p, link)})

    SITE.mkdir(exist_ok=True)
    (SITE / "arquivo").mkdir(exist_ok=True)
    pagina = gerar_html(itens)
    (SITE / "index.html").write_text(pagina, encoding="utf-8")
    (SITE / "arquivo" / f"{HOJE:%Y-%m-%d}.html").write_text(pagina, encoding="utf-8")
    (SITE / "arquivo" / f"{HOJE:%Y-%m-%d}.json").write_text(
        json.dumps(itens, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Página gerada com {len(itens)} produtos: {SITE / 'index.html'}")


if __name__ == "__main__":
    main()
