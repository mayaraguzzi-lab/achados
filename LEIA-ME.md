# Achados do Dia — Shopee

Duas vezes por dia (7h e 16h), o sistema busca os produtos mais vendidos da Shopee, gera o **seu link de afiliado** e atualiza uma página com cada produto pronto para postar: imagem, texto e link.

Você só abre a página no celular ou computador, toca em **Copiar texto**, cola no grupo e marca **Já postei**.

Roda de graça no GitHub, sem precisar deixar o computador ligado.

---

## Passo 1 — Pegar suas chaves da Shopee

1. Entre em **affiliate.shopee.com.br** com sua conta de afiliada.
2. Procure o menu **Open API** (às vezes fica em "Ferramentas" ou no rodapé).
3. Copie o **App ID** e o **Secret**.
   - Se não aparecer, ou se der o erro **10035**, sua conta ainda não tem acesso: peça liberação pelo formulário de suporte de afiliados.
4. **Nunca** mande o Secret para ninguém nem cole em grupos. Ele funciona como uma senha.

## Passo 2 — Criar a conta e o repositório no GitHub

1. Crie uma conta grátis em **github.com**.
2. Clique em **New repository**, dê o nome `achados` e marque **Public**.
   - O GitHub Pages grátis exige repositório público. As chaves ficam guardadas em segredo (passo 3), então ninguém as vê.
3. Clique em **uploading an existing file** e envie todos os arquivos desta pasta, **incluindo a pasta `.github`**.

## Passo 3 — Guardar as chaves em segredo

No repositório: **Settings → Secrets and variables → Actions → New repository secret**. Crie dois:

| Nome | Valor |
|---|---|
| `SHOPEE_APP_ID` | seu App ID |
| `SHOPEE_SECRET` | seu Secret |

## Passo 4 — Ligar a página

1. **Settings → Pages → Source:** escolha **GitHub Actions**.
2. Vá em **Actions → Achados do dia → Run workflow** para gerar a primeira vez.
3. Quando ficar verde, o endereço aparece ali (algo como `seunome.github.io/achados`). Salve nos favoritos do celular.

A partir daí, a página se atualiza sozinha às 7h e às 16h.

---

## Ajustes (arquivo `config.json`)

| Campo | O que faz |
|---|---|
| `quantidade_produtos` | quantos produtos aparecem por dia |
| `palavras_chave` | nichos buscados (`""` = geral). Ex.: `"pet"`, `"fitness"` |
| `nota_minima` | só entra produto com avaliação a partir disso |
| `vendas_minimas` | descarta produtos com poucas vendas |
| `titulo_post` / `rodape_post` | primeira e última linha do texto |

Para mudar os horários, edite a linha `cron` em `.github/workflows/achados-diarios.yml`. O horário é em UTC, ou seja, 3 horas a mais que Brasília.

## Dicas de uso

- **Imagem:** o botão "Copiar imagem" funciona na maioria dos navegadores de computador. No celular, use "Abrir imagem", segure o dedo e salve.
- **Ritmo:** poste 2 ou 3 ofertas por vez em cada grupo, espaçadas, para não cansar o pessoal.
- **Página antiga:** a pasta `site/arquivo/` guarda a página e os dados de cada dia.

## Testar sem a API

```
python gerar_pagina.py --demo
```

Gera a página com 6 produtos fictícios em `site/index.html`.
