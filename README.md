# Censo Anki Brasil

Addon para Anki Desktop + API Cloudflare Worker/D1 para coletar, duas vezes por ano, estatísticas agregadas sobre uso do Anki e addons na comunidade Anki Brasil.

Autor: **Danyel Barboza - Comunidade Anki Brasil**

## O que o projeto contém

```text
addon/      Addon modular do Anki Desktop
worker/     API Cloudflare Worker + banco D1
scripts/    Script de empacotamento do addon
privacy.md  Texto de privacidade para GitHub/AnkiWeb
```

## Requisito de versão

- Anki Desktop **24.06+**
- Windows, macOS e Linux

O addon não roda no AnkiWeb, AnkiDroid ou AnkiMobile. Ele coleta quando a pessoa abre o **Anki Desktop**.

## Janelas de coleta

- 01/06 a 10/06
- 10/12 a 20/12

IDs gerados:

```text
censo-anki-brasil-2026-1
censo-anki-brasil-2026-2
```

## Comportamento

- Primeira abertura: mostra explicação e abre o perfil.
- 10 dias antes do censo: mostra lembrete gentil para atualizar o perfil.
- No início da coleta: mostra novo lembrete gentil para manter o perfil atualizado.
- Durante a janela: envia automaticamente, sem perguntar.
- Uma resposta por usuário/censo.
- Se falhar, tenta de novo silenciosamente na próxima abertura durante a janela.
- O usuário pode pausar a participação nas configurações.

## Dados enviados

Não envia conteúdo de cards, notas, decks, campos, tags ou mídia. Envia agregados em faixas, perfil opcional e lista de addons instalados.

Veja `privacy.md` para texto detalhado.

# Deploy do backend Cloudflare

## 1. Revogue tokens expostos

Se algum token da Cloudflare foi colado em chat, GitHub, print ou qualquer lugar público, revogue-o antes de continuar.

## 2. Instale Node.js

Instale Node.js LTS. Depois, no terminal:

```bash
cd worker
npm install
npx wrangler login
```

## 3. Crie o banco D1

```bash
npm run db:create
```

A Cloudflare vai mostrar algo parecido com:

```toml
[[d1_databases]]
binding = "DB"
database_name = "censo-anki-brasil-db"
database_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

Copie apenas o `database_id` e substitua em `worker/wrangler.toml` no campo:

```toml
database_id = "REPLACE_WITH_D1_DATABASE_ID_AFTER_CREATE"
```

Isso é configuração de deploy, não código do addon.

## 4. Crie as tabelas

```bash
npm run db:init
```

## 5. Publique o Worker

```bash
npm run deploy
```

O Wrangler vai mostrar a URL pública, por exemplo:

```text
https://censo-anki-brasil-api.SEUSUBDOMINIO.workers.dev
```

Você não precisa ter domínio próprio. O domínio padrão `workers.dev` é suficiente.

# Configurando a URL no addon sem mexer no código

O pacote vem com uma URL padrão:

```text
https://censo-anki-brasil-api.danyelbarboza.workers.dev
```

Se a sua URL real for diferente, há duas opções sem alterar código Python:

## Opção A: configurar pela interface do addon

No Anki Desktop:

```text
Ferramentas → Censo Anki Brasil → Configurações → URL da API
```

Cole a URL do Worker e salve.

## Opção B: gerar um pacote já com a URL certa

Na raiz do projeto:

```bash
python scripts/build_addon.py --api-url "https://censo-anki-brasil-api.SEUSUBDOMINIO.workers.dev"
```

O arquivo `.ankiaddon` será criado em `dist/`. Isso altera apenas o `config.json` empacotado, não o código.

# Empacotando para AnkiWeb

```bash
python scripts/build_addon.py --api-url "https://censo-anki-brasil-api.SEUSUBDOMINIO.workers.dev"
```

Envie o arquivo `.ankiaddon` da pasta `dist/` para o AnkiWeb Add-ons.

# Endpoints públicos

- `GET /config` configuração atual do censo
- `POST /submit` envio real do addon
- `POST /debug-submit` envio de teste da área de desenvolvedor
- `GET /results` resultados agregados em JSON
- `GET /results.html` página HTML simples com resultados públicos

# Área de desenvolvedor

Senha: `4599`

Funções:

- Ver JSON final
- Copiar JSON
- Salvar JSON
- Enviar JSON para `/debug-submit`
- Resetar status local de envio

O endpoint de teste salva em tabela separada e não entra nos resultados públicos.

# Observações técnicas

O backend usa Cloudflare D1. A documentação da Cloudflare descreve o D1 como banco SQL serverless compatível com convenções do SQLite e acessível via bindings do Worker. O Worker usa prepared statements para inserções e consultas.
