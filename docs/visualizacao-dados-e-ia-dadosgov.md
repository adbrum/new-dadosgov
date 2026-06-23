# Soluções de Visualização de Dados e IA para o Portal dados.gov.pt

> **Documento técnico de análise e recomendação**
> Portal: dados.gov.pt (assente em udata — Flask/MongoDB + Next.js)
> Data: 2026-06-16
> Âmbito: visualização de dados, papel do Hydra (rastreador/data lake), sincronismo, MCP e aplicação de IA aos dados abertos (incl. PoC de validação de HVDs).

---

## Convenção de rigor

Ao longo do documento as afirmações são marcadas como:

- **[FACTO]** — confirmado no código do dadosgov ou em documentação pública das fontes.
- **[INFERÊNCIA]** — conclusão fundamentada mas não citada explicitamente; deve ser validada empiricamente.
- **[A CONFIRMAR]** — não confirmado pelas fontes públicas; requer verificação no ambiente da AMA.

---

## 1. Sumário executivo

1. **O dados.gov.pt armazena recursos de duas formas** [FACTO]: ficheiros **carregados** para a infraestrutura (armazenamento local ou S3/MinIO) e **ligações remotas** apontando a fontes de terceiros. A distinção é o campo `filetype` (`file` vs `remote`) no modelo `Resource`. A recolha automática (*harvesting*) (DCAT, CSW, CKAN, OGC, INE, etc.) **apenas referencia URLs remotos — não copia os dados** para a infraestrutura.

2. **O Hydra (`hydra-pt`) é um rastreador (crawler) de metadados** [FACTO], derivado (fork) do `datagouv/hydra` (udata-hydra). **Não guarda os ficheiros originais como blocos binários (blobs)**; em vez disso: (a) guarda **metadados + somas de verificação (checksums) de todos os recursos** rastreados por URL, e (b) **descarrega e converte** o conteúdo dos recursos tabulares para **tabelas PostgreSQL + Parquet** e os geoespaciais (GeoJSON) para **PMTiles**. Quanto à pergunta direta: o Hydra **trata recursos locais e remotos da mesma forma — para ele ambos são apenas URLs no catálogo** [INFERÊNCIA forte], pelo que cobre tanto os dados na nossa infraestrutura como os remotos.

3. **Sim, o Hydra pode funcionar como camada de "data lake" tabular com sincronismo** [FACTO para o mecanismo; INFERÊNCIA para a designação "data lake"]: tem deteção incremental de alterações (data de colheita + cabeçalhos HTTP + soma de verificação), rastreio periódico (`CHECK_DELAYS`) e atualização através de notificação (webhook) do udata. O resultado (PostgreSQL + Parquet) é uma base consultável e exponível por API.

4. **A integração de visualização tabular já está parcialmente ligada no dados.gov.pt** [FACTO]: `backend/udata/core/dataset/preview.py` (`TabularAPIPreview`) gera `preview_url` quando o recurso tem o extra `analysis:parsing:parsing_table` — que é precisamente o resultado produzido pelo Hydra — e quando `TABULAR_EXPLORE_URL` está configurado. Falta confirmar/ativar a cadeia completa de serviços (Hydra + api-tabular + explorador) em produção.

5. **Habilitar MCP é viável e é uma oportunidade diferenciadora** [FACTO/INFERÊNCIA]: existem servidores MCP para CKAN mas **não existe publicamente um MCP nativo para udata**. Construir um MCP sobre a API udata (`/api/1`, `/api/2`) + o tabular-api do Hydra exporia o catálogo e os dados tabulares a assistentes de IA (Claude, etc.).

6. **A IA acelera o ciclo de vida dos dados abertos** em metadados automáticos, deteção de schema/tipos/PII, "chat with data" (text-to-SQL/RAG), geração de visualizações por linguagem natural e **validação de conformidade HVD** — esta última é o candidato ideal a PoC (secção 7).

---

## 2. Arquitetura atual do dados.gov.pt — onde estão os dados

### 2.1 Modelo de recurso: local vs remoto [FACTO]

`backend/udata/core/dataset/models.py` (classe `ResourceMixin`) e `constants.py`:

```python
RESOURCE_FILETYPES = OrderedDict([
    ("file",   "Uploaded file"),   # armazenado na nossa infra
    ("remote", "Remote file"),     # URL externa (terceiros)
])
```

| Aspeto | `filetype = "file"` (local) | `filetype = "remote"` (remoto) |
| --- | --- | --- |
| `fs_filename` | preenchido (ex.: `2026-06-16/abc...csv`) | `NULL` |
| `url` | aponta a `/api/1/datasets/r/<id>` (permalink) | URL externa da fonte |
| Armazenamento | storage backend (FS local ou S3/MinIO) | não copiado — só referência |
| Download | `_serve_hosted_resource()` (bytes do storage) | `_proxy_remote_resource()` (proxy com SSRF guard) |

Campos relevantes do recurso: `url`, `urlhash`, `checksum`, `format`, `mime`, `filesize`, `fs_filename`, `extras`, `harvest` (`HarvestResourceMetadata`), `schema`.

### 2.2 Armazenamento de ficheiros [FACTO]

- **Flask-Storage** com storages dedicados (`resources`, `avatars`, `logos`, `images`, `chunks`, `tmp`, `references`) — `backend/udata/core/storages/__init__.py`.
- **Suporte a S3/MinIO** via boto3 — `backend/udata/storage/s3.py`; config `S3_URL`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `BUCKETS_PREFIX` em `settings.py`.
- **Upload chunked** com validação de extensão *e* de conteúdo (magic bytes, scanning anti-payload) — `backend/udata/core/storages/api.py`, `validation.py`.

### 2.3 Harvesting — referência, não cópia [FACTO]

`backend/udata/harvest/`. Backends: `dcat`, `csw-dcat`, `csw-iso-19139`, `ckan`, `ogc` (WMS/WFS), `apambiente`, `dgt`, `ine`, `maaf`, `odspt`. Frequências: manual, diária, semanal, mensal.

> A recolha automática (*harvesting*) extrai **metadados** das fontes e cria conjuntos de dados locais cujos recursos ficam com `filetype="remote"` e `url` a apontar à origem. **Não há cópia de conteúdo para a infraestrutura.** A `HarvestResourceMetadata` (`remote_id`, `uri`, `modified_at`) suporta atualização incremental.

### 2.4 Visualização/pré-visualização já existente [FACTO]

`backend/udata/core/dataset/preview.py`:

```python
class TabularAPIPreview(Preview):
    def preview_url(self, resource):
        base = current_app.config["TABULAR_EXPLORE_URL"]
        if not base: return None
        if "analysis:parsing:parsing_table" not in resource.extras: return None
        if resource.filetype == "remote" and not current_app.config["TABULAR_ALLOW_REMOTE"]:
            return None
        return f"{base}/resources/{resource.id}"
```

Config em `settings.py`: `TABULAR_API_DATASERVICE_ID`, `TABULAR_EXPLORE_URL`, `TABULAR_ALLOW_REMOTE`. Famílias de formato já classificadas: `TABULAR_FORMATS` (csv, parquet, xls, xlsx, ods, tsv), `MACHINE_READABLE_FORMATS` (json, xml, rdf, jsonl…), `GEOGRAPHICAL_FORMATS` (shp, geojson, gpkg, kml…), `DOCUMENTS_FORMATS`.

> **Conclusão importante:** o ponto de ligação para a pré-visualização está **pronto e à espera do Hydra**. O extra `analysis:parsing:parsing_table` é escrito pelo Hydra (estados de análise CSV). O que falta é a cadeia de serviços (Hydra a analisar + api-tabular a servir + explorador a apresentar) e as variáveis de ambiente apontadas.

---

## 3. O Hydra — confirmação de armazenamento, sincronismo e data lake

### 3.1 O que é [FACTO]

`amagovpt/hydra-pt` é um **derivado (fork) do `datagouv/hydra` (udata-hydra)** — rastreador **assíncrono de metadados** para portais udata. Tecnologias: Python ≥3.11, `aiohttp`, **PostgreSQL**, **Redis + rq** (processos de trabalho), `libmagic`. Três serviços: **rastreador** (`udata-hydra-crawl`), **processo de trabalho** (tarefas longas: análise CSV, conversões), **API** REST (aiohttp, porta 8000).

> **Nota:** o fork da AMA aparenta ser, ao nível público, **idêntico ao upstream francês** (README/CHANGELOG referenciam data.gouv.fr e PRs do datagouv). [A CONFIRMAR] divergências de código/config via `git diff` contra `datagouv/hydra`.

### 3.2 Pergunta crítica: armazena dados locais E remotos? [FACTO + INFERÊNCIA]

**Resposta:** O Hydra não distingue origem — **rastreia qualquer URL presente no catálogo do portal**, seja um recurso carregado para o dados.gov.pt (servido através da ligação permanente `/r/<id>`) ou uma ligação remota de terceiros. [INFERÊNCIA forte: para o Hydra ambos são "apenas um URL"; não há evidência de tratamento diferenciado.]

O que efetivamente guarda:

| Tipo de recurso | O que o Hydra guarda |
| --- | --- |
| **Qualquer recurso** | metadados de rastreio: estado HTTP, cabeçalhos, `content-length`, `last-modified`, tempo de resposta, **soma de verificação**, datas — tabelas `catalog` e `checks` (PostgreSQL) |
| **Tabular (CSV/XLS…)** | **conteúdo convertido** → tabelas em PostgreSQL (`DATABASE_URL_CSV`) + export **Parquet** |
| **Geoespacial (GeoJSON)** | conteúdo convertido → **PMTiles** |
| **Ficheiro original (blob)** | **não guarda** — isso é função do udata (upload) |

> Para análise tabular e cálculo da soma de verificação, o rastreador tem necessariamente de fazer **GET ao corpo do ficheiro** [INFERÊNCIA forte]. [A CONFIRMAR] se usa HEAD vs GET por etapa para recursos não-tabulares.

### 3.3 Sincronismo / atualização incremental [FACTO]

Deteção de alteração por três sinais: **data de colheita** no catálogo, **cabeçalhos HTTP** (`content-length`, `last-modified`) e **soma de verificação** ao longo do tempo. Rastreio periódico governado por `CHECK_DELAYS`; novos recursos entram como prioritários através de notificação (webhook) do udata (`POST /api/resources`). Recursos eliminados são marcados, não apagados. Limitação de ritmo por domínio (`BACKOFF_NB_REQ` / `BACKOFF_PERIOD`) protege as fontes.

### 3.4 Validação de qualidade [FACTO]

Disponibilidade de links (status/erros/tempos), deteção de tipo (`libmagic`), análise de conteúdo CSV antes de converter, métricas agregadas (`GET /api/checks/aggregate`). [A CONFIRMAR] validação semântica/schema avançada (tipo Frictionless/GoodTables) — não evidenciada.

### 3.5 API / integração [FACTO]

API REST JSON: `/api/checks/{latest,all,aggregate}`, `/api/resources[/{id}]`, `/api/resources-exceptions`, `/api/status/{crawler,worker}`, `/api/stats`, `/api/health`. As escritas exigem autenticação por *token* (`API_KEY`). Integração **bidirecional com o udata através de notificações (webhooks)**.

### 3.6 Pode ser usado como "Data Lake" com sincronismo? — análise

**Sim, com ressalvas terminológicas.** O Hydra entrega uma **camada de dados consultável e sincronizada** sobre o catálogo:

- ✅ **Cobertura local + remota** — rastreia todos os URLs do catálogo.
- ✅ **Conteúdo materializado** para tabular (PostgreSQL/Parquet) e geo (PMTiles) — não é só metadados.
- ✅ **Sincronismo incremental** (soma de verificação/cabeçalhos/notificação + rastreio periódico).
- ⚠️ **Não é um data lake genérico** no sentido clássico (não guarda blobs arbitrários nem todos os formatos). É um **"lakehouse tabular/geo"** focado nos formatos que sabe converter. PDFs, ficheiros proprietários, etc., ficam apenas como metadados+checksum.
- ⚠️ O **Parquet** gerado é, na prática, o formato ideal para alimentar um data lake "a sério" (object storage + engine de query tipo DuckDB/Trino) — é o ponto de extensão natural.

> **Recomendação:** tratar o Hydra como a **camada de ingestão/normalização** (CSV→PostgreSQL/Parquet, GeoJSON→PMTiles) e, se for preciso um data lake analítico completo, **publicar os Parquet em object storage (S3/MinIO)** e consultar com DuckDB/Trino. O object storage já é suportado pelo udata (`S3_*`).

---

## 4. Habilitar MCP (Model Context Protocol)

**Estado da arte [FACTO]:** existem servidores MCP maduros para **CKAN** (ex.: `ondics/ckan-mcp-server` — pesquisa Solr, SQL ao DataStore, metadados, NL→API; testado em data.gov, open.canada.ca, data.gov.uk, opendata.swiss; compatível com Claude Desktop/ChatGPT/Cursor/VS Code). **Não existe publicamente um MCP nativo para udata** [INFERÊNCIA — confirmar no GitHub datagouv antes de afirmar como definitivo].

**Como expor o dados.gov.pt via MCP:**

1. **Camada de catálogo (metadados)** — MCP server sobre `/api/1` e `/api/2` (udata): ferramentas `search_datasets`, `get_dataset`, `list_organizations`, `get_resource_metadata`.
2. **Camada de dados tabulares** — ferramenta `query_table` que traduz linguagem natural → filtros do **api-tabular** (operadores `column__exact`, `column__greater`, `column__groupby`) sobre as tabelas que o Hydra materializou em PostgreSQL.
3. **Camada de qualidade** — ferramenta `resource_health` lendo `/api/checks/*` do Hydra (disponibilidade, último check, checksum).

> **Sinergia direta:** o Hydra é o que torna os dados **consultáveis por SQL/filtros** — é precisamente o que dá "substância" a um MCP. Sem o Hydra, o MCP só veria metadados; com o Hydra, vê **dados**. Isto faz do par **Hydra + MCP udata** uma diferenciação concreta e alinhada com 2025/2026. A skill `mcp-builder` do projeto cobre os princípios de design.

---

## 5. Soluções de visualização de dados

### 5.1 O que fazem os portais de referência [FACTO]

| Portal / tecnologia | Camada de dados | Visualização |
| --- | --- | --- |
| **data.gouv.fr (udata)** | udata-hydra → PostgreSQL/Parquet; **api-tabular** (intermediário seguro sobre PostgREST) | **explore.data.gouv.fr** + `udata-tabular-preview` (pré-visualização tabular na página do conjunto de dados) |
| **CKAN** (data.gov EUA/UK, open.canada.ca) | **DataStore** (PostgreSQL) + DataPusher/xloader | **Data Explorer** (React; recline.js em fim de vida): tabela, gráficos, mapas |
| **data.europa.eu** | catálogo DCAT-AP | **visualização CSV embebida (2025)**: linha/barra/donut; mapas; data stories |
| **Socrata** (Tyler) | proprietário + SODA API | gráficos/mapas/KPIs embebíveis nativos |

> **Padrão comum:** *ficheiro → BD relacional (PostgreSQL) → API REST/SQL com filtros → visualização*. O dados.gov.pt, sendo udata, tem o **caminho de menor atrito** no conjunto de ferramentas da Etalab (Hydra + api-tabular + tabular-preview/explorador) — e já tem o ponto de ligação de pré-visualização no código (secção 2.4).

### 5.2 Bibliotecas recomendadas para o frontend [FACTO]

| Necessidade | Recomendação | Porquê |
| --- | --- | --- |
| Gráficos declarativos | **Vega-Lite** | especificação JSON validável (ideal para gerar por LLM com segurança) |
| Gráficos interativos | **Plotly** / **Observable Plot** | maturidade, interatividade |
| Embeds jornalísticos | **Datawrapper / Flourish** | rápido, embebível |
| Mapas simples | **Leaflet** / **MapLibre GL** | leve / WebGL open source |
| Geo de larga escala | **deck.gl / Kepler.gl** | milhões de pontos (assenta em MapLibre + deck.gl); usado no NYC Open Data |
| Dashboards/BI | **Metabase** (self-service) / **Apache Superset** (SQL) | analítica para equipas internas |

### 5.3 APIs de dados tabulares [FACTO]

- **api-tabular (Etalab) + udata-hydra** — PostgREST sobre PostgreSQL; filtros/sort/groupby; proxy seguro. **Produção.** Caminho recomendado.
- **csvapi (Etalab)** — "API JSON instantânea para CSV"; mais antigo.
- **CKAN DataStore API** — SQL-like sobre PostgreSQL.
- **Frictionless Data / Table Schema** — padrão de schema de tabelas (tipos/constraints); base para validação e interoperabilidade.

---

## 6. Como a IA pode ajudar os dados abertos

| Caso de uso | O que faz | Maturidade | Risco/mitigação |
| --- | --- | --- | --- |
| **Metadados automáticos** | LLM gera descrições, tags, resumos a partir de cabeçalhos/conteúdo | Emergente→produção | human-in-the-loop na publicação |
| **Deteção de schema/tipos de coluna** | inferência de tipos e domínios semânticos | Produção (regras) / Emergente (ML) | já parcialmente feito por Hydra |
| **Deteção de PII** | scan de colunas (regex + ML) para impedir republicação de dados pessoais | Produção (plataformas dados) / Emergente (portais) | crítico em open data; alerta pré-publicação |
| **"Chat with data" / text-to-SQL** | RAG + NL→SQL sobre catálogo e tabelas (padrão **Vanna**) | Emergente | schema linking; validar SQL gerado; só leitura |
| **Geração de visualizações por NL** | NL → especificação **Vega-Lite** (padrão **Microsoft LIDA**) | Emergente | gerar especificação declarativa (não código arbitrário) |
| **Validação de conformidade HVD** | classificar categoria + verificar formato/licença/API/metadados/frescura | Emergente | **candidato ideal a PoC** (secção 7) |
| **Exposição via MCP** | catálogo+dados consultáveis por assistentes IA | Emergente/oportunidade | secção 4 |

> Exemplos reais em produção governamental: **GOV.UK Chat** (RAG sobre conteúdo GOV.UK, beta público 2025); **data.europa.eu** (open data como combustível de IA confiável, AI Act).

---

## 7. PoC proposta — Validação de HVDs com IA

### 7.1 Enquadramento [FACTO]

**High Value Datasets (HVD)** — Diretiva (UE) 2019/1024 + **Regulamento de Execução (UE) 2023/138** (aplicável desde 2024). **6 categorias:** geoespacial; observação da Terra e ambiente; meteorologia; estatística; empresas e propriedade de empresas; mobilidade.

**Requisitos-chave:** gratuitos; formatos **legíveis por máquina**; disponíveis via **API** + **bulk download**; metadados conforme **DCAT-AP HVD** (marcação `hvd`); conformidade com proteção de dados/PI. [A CONFIRMAR no texto do Regulamento e Data Provider Manual: licença CC BY 4.0 e frequência de atualização exatas.]

### 7.2 Objetivo da PoC

Um **validador automático assistido por IA** que, para cada dataset candidato a HVD, produz um **relatório de conformidade** com pontuação e *gaps* acionáveis.

### 7.3 Arquitetura (reutilizando o que já existe)

```
Catálogo udata (/api/2/datasets)  ──┐
Checks do Hydra (/api/checks/*)    ──┼──► Validador HVD ──► Relatório de conformidade
Metadados DCAT-AP (RDF endpoints)  ──┘        │                 (score + gaps + sugestões)
                                              ├─ Regras determinísticas (formato, API, bulk, licença, metadados)
                                              └─ LLM (classificação de categoria HVD + sugestão de metadados em falta)
```

### 7.4 Verificações (regras determinísticas — sem IA)

1. **Formato machine-readable** — `resource.format ∈ TABULAR_FORMATS ∪ MACHINE_READABLE_FORMATS ∪ GEOGRAPHICAL_FORMATS` (já classificado no backend).
2. **API disponível** — existe recurso `type="api"`/dataservice associado?
3. **Bulk download** — existe recurso descarregável (permalink) com `filesize` razoável?
4. **Disponibilidade** — `extras["check:available"]` / `/api/checks/latest` do Hydra (status HTTP).
5. **Licença** — `dataset.license` ∈ conjunto aberto compatível (verificar CC BY 4.0).
6. **Metadados DCAT-AP HVD** — campos obrigatórios + marcação `hvd` presentes.
7. **Frescura** — `last_modified` vs frequência declarada (deteção de "obsoleto" via datas do Hydra).

### 7.5 Camada de IA (LLM)

- **Classificação de categoria HVD** (1 de 6) a partir de título/descrição/colunas — com justificação e grau de confiança.
- **Sugestão de metadados em falta** (descrição, tags, keywords DCAT-AP) — *draft* para revisão humana.
- **Deteção de PII** nas colunas tabulares materializadas pelo Hydra — alerta pré-publicação.
- **(Opcional)** geração de uma visualização-resumo (Vega-Lite) por dataset validado.

### 7.6 Entregáveis e métricas

- Relatório por dataset: `score` (0–100), checklist de requisitos, *gaps* e sugestões.
- Dashboard agregado: % de HVDs conformes por categoria/organização (espelha o Open Data Maturity da UE).
- Métricas de sucesso: precisão da classificação de categoria (vs rótulo humano); % de *gaps* reais confirmados; redução de tempo de curadoria.

### 7.7 Princípios

- **Human-in-the-loop** — a IA sugere, não publica. Adequado a PoC, não a SLA crítico.
- **Reutilização máxima** — assenta em udata API + Hydra checks + classificação de formatos já existente. Esforço incremental baixo.

---

## 8. Recomendações e roadmap

| Fase | Ação | Depende de | Maturidade |
| --- | --- | --- | --- |
| **1. Ativar visualização** | Confirmar/ativar Hydra + api-tabular + explorador; configurar `TABULAR_EXPLORE_URL`/`TABULAR_API_DATASERVICE_ID` | Hydra em produção | Produção |
| **2. Enriquecer frontend** | Vega-Lite para gráficos + MapLibre/Leaflet para geo nas páginas de dataset | Fase 1 | Produção |
| **3. Data lake analítico** | Publicar Parquet do Hydra em S3/MinIO; query com DuckDB/Trino | `S3_*` (já suportado) | Produção |
| **4. MCP udata** | MCP server sobre `/api/1`,`/api/2` + api-tabular + checks Hydra | Fases 1–3 | Oportunidade |
| **5. PoC HVD com IA** | Validador de conformidade (regras + LLM), human-in-the-loop | udata API + Hydra | Emergente |
| **6. IA generativa** | metadados automáticos, "chat with data" (Vanna), viz por NL (LIDA) | Fases 1,4 | Emergente |

### Ações de verificação imediata [A CONFIRMAR]

1. Confirmar se o **Hydra está em produção** no dados.gov.pt e a popular `analysis:parsing:*`.
2. `git diff amagovpt/hydra-pt` vs `datagouv/hydra` — divergências de config/código.
3. Confirmar valores de `TABULAR_EXPLORE_URL`, `TABULAR_API_DATASERVICE_ID`, `TABULAR_ALLOW_REMOTE` no ambiente.
4. Confirmar inexistência de MCP udata no GitHub datagouv antes de o construir.

---

## 9. Implementação: equipa, perfis, esforço e arquitetura

Esta secção responde a "o que envolve, na prática, implementar isto?" — usando o **MCP como exemplo central** e estendendo a análise às mudanças de arquitetura (data lake, capacidade de servidores, custos).

> **Aviso de estimativa.** Os valores de esforço são **ordens de grandeza** (pessoa-semanas), assumindo perfis séniores e reutilização máxima dos componentes da Etalab já existentes. Devem ser refinados com a equipa após a verificação dos pré-requisitos da secção 8. *Pessoa-semana* = uma pessoa a tempo inteiro durante uma semana.

### 9.1 Dois cenários de âmbito

| Cenário | O que inclui | Esforço total (aprox.) | Equipa |
| --- | --- | --- | --- |
| **A — MCP mínimo** | MCP só de metadados, sobre a API udata já existente (`/api/1`,`/api/2`). Sem dados tabulares. | **4–7 pessoa-semanas** | 1 programador sénior + apoio pontual de DevOps |
| **B — Plataforma completa** | Fases 1→6 do roteiro (secção 8): visualização + data lake + MCP com dados + PoC HVD com IA | **9–14 pessoa-meses** | esquadra de 4–6 pessoas ao longo de ~4–6 meses |

> **Conclusão prática:** um MCP **útil** (que responda sobre *dados*, não só metadados) depende da **Fase 1** (Hydra + api-tabular ativos). O MCP em si é barato; o que custa é a camada de dados por baixo.

### 9.2 Perfis necessários

| Perfil | Responsabilidade | Onde é crítico |
| --- | --- | --- |
| **Arquiteto / Tech lead** | Desenho da solução, decisões transversais, contrato de APIs | Todas as fases |
| **Programador Backend Python (udata)** | API udata, MCP (se em Python/FastMCP), integração Hydra | Fases 1, 4, 5 |
| **Engenheiro DevOps / SRE** | Implantação de Hydra/PostgreSQL/Redis, object storage, observabilidade, *rate-limit* | Fases 1, 3, 4 |
| **Engenheiro de Dados** | Pipeline de materialização, Parquet, data lake, motores de consulta | Fases 1, 3 |
| **Programador Frontend (Next.js)** | Componentes de visualização (Vega-Lite, MapLibre), explorador tabular | Fases 1, 2 |
| **Designer UI/UX** (parcial) | Desenho dos componentes de visualização e do fluxo de revisão humana | Fases 2, 5 |
| **Cientista de Dados / Engenheiro de IA** | Classificação HVD, deteção de PII, *text-to-SQL*, geração de visualizações | Fases 5, 6 |
| **QA / Testes** (parcial) | Testes de carga (reutilizar `scripts/loadtest_*`), validação funcional | Fases 1, 4 |
| **Product Owner / Coordenação** (parcial) | Priorização, ligação com a AMA, conformidade legal (HVD, RGPD) | Todas |

> **Equipa mínima viável (cenário B faseado):** Tech lead + 1 backend + 1 DevOps + 1 frontend + 1 cientista de dados (estes dois a tempo parcial nas fases iniciais). Os perfis podem acumular em equipas pequenas.

### 9.3 MCP em detalhe (o exemplo pedido)

#### Decisões de desenho

1. **Linguagem/SDK:** **Python com FastMCP** (reutiliza modelos e clientes da API udata) **ou** TypeScript (SDK oficial mais maduro, como o `ckan-mcp-server` de referência). Recomendação: **Python**, pela proximidade ao backend.
2. **Modo de implantação:**
   - **Remoto/alojado (HTTP, *streamable*)** — servidor central a que assistentes (Claude, etc.) se ligam. Requer autenticação (OAuth ou chaves de API) e exposição controlada. **Recomendado para uso institucional.**
   - **Local (stdio)** — distribuído como pacote que cada utilizador corre na sua máquina. Mais simples, sem infraestrutura, mas sem controlo central.
3. **Ferramentas a expor (read-only):**
   - `search_datasets`, `get_dataset`, `list_organizations`, `get_resource_metadata` → sobre `/api/1`,`/api/2` (disponível **hoje**).
   - `query_table` → consulta tabular via **api-tabular** (operadores `column__exact`, `column__groupby`, …). **Depende da Fase 1.**
   - `resource_health` → estado/disponibilidade via `/api/checks/*` do **Hydra**. **Depende da Fase 1.**

#### Integração com a arquitetura existente

- **Sem alterações ao MongoDB nem ao modelo de dados** — o MCP é um cliente das APIs já existentes.
- **Serviço novo, leve** (um contentor; alta disponibilidade = dois). CPU/memória reduzidos.
- ⚠️ **`Rate-limit` obrigatório por causa do F5/WAF:** atrás do balanceador, todo o tráfego anónimo chega com o **mesmo IP de origem** ([[ip-collapse-ratelimit-convention]]). Um MCP público que reencaminhe pedidos para os endpoints udata tem de usar limite por `user_or_ip` (clientes autenticados ganham o seu próprio balde) — caso contrário esgota o teto partilhado do site. **Clientes MCP autenticados (chave de API) devem ter balde próprio.**
- **Observabilidade e *caching*** — reutilizar `@cache.cached` e métricas existentes.

#### Esforço MCP

| Item | Esforço |
| --- | --- |
| MVP read-only de metadados (sobre API atual) | 2–3 pessoa-semanas |
| Ferramentas `query_table` + `resource_health` (após Fase 1) | +1–2 pessoa-semanas |
| Autenticação, *rate-limit* por `user_or_ip`, endurecimento, testes de carga | +1–2 pessoa-semanas |
| **Total MCP** | **4–7 pessoa-semanas** (1 programador sénior) |

### 9.4 Mudanças de arquitetura por fase

| Fase | Componentes novos | Alteração estrutural |
| --- | --- | --- |
| **1. Visualização (Hydra + api-tabular)** | **PostgreSQL** (catálogo + checks), **PostgreSQL CSV** (tabelas materializadas), **Redis**, serviços Hydra (rastreador + processo de trabalho + API), api-tabular (PostgREST) | Introdução de um motor relacional **ao lado** do MongoDB. Maior pegada operacional. |
| **2. Frontend de visualização** | Bibliotecas no Next.js (Vega-Lite, MapLibre/Leaflet) | Sem novo serviço; só dependências de frontend. |
| **3. Data lake analítico** | **Object storage** (S3/MinIO — já suportado) para Parquet/PMTiles; motor de consulta (**DuckDB**/**Trino**) | Camada analítica desacoplada; permite consulta a grande escala sem sobrecarregar o operacional. |
| **4. MCP** | 1 serviço leve (contentor) | Sem alteração ao núcleo; cliente das APIs. |
| **5. PoC HVD com IA** | Serviço/tarefa de validação; integração com fornecedor de **LLM**; interface de revisão humana | Acesso a LLM (API externa ou modelo próprio). Considerar **residência de dados na UE**. |
| **6. IA generativa** | Igual à Fase 5, mais intensivo em LLM | Custos recorrentes de inferência. |

### 9.5 Capacidade de servidores e custos

| Recurso | Necessidade | Dimensionamento (a validar) |
| --- | --- | --- |
| **MongoDB** (existente) | Sem alteração para MCP/visualização | — |
| **PostgreSQL** (catálogo + checks do Hydra) | Pequeno/moderado | Dezenas de GB; instância dedicada |
| **PostgreSQL CSV** (tabelas materializadas) | **O item mais pesado** — cresce com o nº e tamanho dos recursos tabulares | Começar com 100–500 GB e escalar; opções de carregamento parcial/TTL para conter crescimento |
| **Redis** | Fila de tarefas do Hydra | Pequeno |
| **Object storage (S3/MinIO)** | Parquet + PMTiles | Por volume; já suportado (`S3_*`) |
| **Computação Hydra** (rastreador/processo) | Largura de banda + CPU para análise CSV | 2+ contentores, escaláveis horizontalmente |
| **Servidor MCP** | Muito leve | 1 contentor (2 para alta disponibilidade) |
| **LLM (Fases 5–6)** | Inferência | **API externa** (custo por *token*, arranque rápido, baixo custo em PoC) **ou** **modelo próprio em GPU** (soberania/residência de dados, custo fixo elevado) |

> **Nota de soberania (setor público PT/UE):** para validar HVDs e "conversar com dados", ponderar **residência de dados na UE** e o tratamento de dados pessoais (RGPD). Em PoC pode usar-se API externa com dados não sensíveis; para produção, avaliar modelo alojado na UE ou *on-premises*.

### 9.6 Estimativa de esforço por fase (cenário B)

| Fase | Esforço (pessoa-semanas) | Perfis principais | Depende de |
| --- | --- | --- | --- |
| 1. Ativar visualização (Hydra + api-tabular) | 8–12 | DevOps, Backend, Eng. Dados | Hydra disponível |
| 2. Frontend de visualização | 4–8 | Frontend, Designer | Fase 1 |
| 3. Data lake analítico | 6–10 | Eng. Dados, DevOps | Fase 1 |
| 4. MCP | 4–7 | Backend | Fase 1 (para dados) |
| 5. PoC HVD com IA | 6–10 | Cientista de Dados, Backend | API udata + Hydra |
| 6. IA generativa | 8–14 | Cientista de Dados, Backend | Fases 1, 4 |

> **Caminho crítico:** a **Fase 1** desbloqueia quase tudo (visualização útil, `query_table` do MCP, materialização para o data lake e dados para a IA). É o investimento de maior alavancagem.

### 9.7 Riscos e pré-requisitos

- **[A CONFIRMAR] Hydra em produção** — se já estiver a popular `analysis:parsing:*`, a Fase 1 reduz-se a configuração; se não, há trabalho de implantação completo.
- **Divergência do `hydra-pt`** face ao *upstream* — validar via `git diff` antes de planear.
- **Crescimento da PostgreSQL CSV** — definir política de retenção/TTL para não crescer sem limite.
- **`Rate-limit`/WAF** — qualquer endpoint novo (incl. MCP) tem de seguir a convenção `user_or_ip` ([[ip-collapse-ratelimit-convention]]).
- **Qualidade da IA** — manter **humano no circuito** (a IA sugere, não publica); não aplicar a SLA crítico sem validação.
- **Conformidade legal** — RGPD e residência de dados na UE para as componentes de IA.

### 9.8 Recomendação de sequência

1. **Verificar pré-requisitos** (secção 8) — 1 pessoa-semana, antes de comprometer plano.
2. **Fase 1** — maior alavancagem; desbloqueia visualização, MCP-com-dados e data lake.
3. **MCP (Fase 4) em paralelo** — o MVP de metadados pode arrancar **já** (não depende da Fase 1); ganha as ferramentas de dados quando a Fase 1 estiver pronta.
4. **PoC HVD (Fase 5)** — alto valor demonstrativo e de conformidade, esforço contido, reutiliza o que já existe.
5. **Data lake (Fase 3) e IA generativa (Fase 6)** — quando houver tração e orçamento de inferência.

---

## Anexo A — Fontes

**Código analisado (dadosgov):** `backend/udata/core/dataset/models.py`, `constants.py`, `preview.py`, `api.py`, `rdf.py`, `download_proxy.py`; `backend/udata/core/storages/`; `backend/udata/storage/s3.py`; `backend/udata/harvest/`; `backend/udata/settings.py`; `frontend/src/service/types/dataset/dataset.ts`.

**Hydra:** github.com/amagovpt/hydra-pt · github.com/datagouv/hydra · pypi.org/project/udata-hydra · udata.readthedocs.io/en/stable/harvesting

**Visualização / API tabular:** github.com/datagouv/api-tabular · github.com/etalab/csvapi · github.com/datagouv/explore.data.gouv.fr · libraries.io/pypi/udata-tabular-preview · docs.ckan.org/en/latest/maintaining/data-viewer.html · data.europa.eu · tylertech.com/products/data-insights/open-data-platform · github.com/keplergl/kepler.gl

**IA:** microsoft.github.io/lida · github.com/vanna-ai/vanna · github.com/DEEP-PolyU/Awesome-LLM-based-Text2SQL · insidegovuk.blog.gov.uk (GOV.UK Chat) · aimultiple.com/open-source-sensitive-data-discovery

**HVD:** eur-lex.europa.eu/eli/reg_impl/2023/138/oj/eng · data.europa.eu/en/news-events/news/high-value-datasets-what-has-changed-and-what-will-come-next · dataeuropa.gitlab.io/data-provider-manual/hvd

**MCP:** ondata.github.io/ckan-mcp-server · github.com/ondics/ckan-mcp-server · lobehub.com/mcp/openascot-ckan-mcp

---

## Anexo B — Quadro FACTO vs INFERÊNCIA (Hydra)

| Tema | Estatuto |
| --- | --- |
| Stack Python/aiohttp/PostgreSQL/Redis/rq | FACTO |
| Guarda metadados + checksums por URL | FACTO |
| Converte CSV→PostgreSQL/Parquet, GeoJSON→PMTiles | FACTO |
| Não guarda ficheiros originais como blobs | FACTO |
| Cobre recursos locais E remotos (ambos são URL) | INFERÊNCIA forte |
| Faz GET ao corpo para análise CSV/checksum | INFERÊNCIA forte |
| HEAD vs GET por etapa | A CONFIRMAR |
| Deteção incremental (harvest-date/headers/checksum) | FACTO |
| API REST + webhooks + Bearer auth | FACTO |
| hydra-pt tem customizações próprias vs upstream | A CONFIRMAR |
| Pré-visualização tabular já ligada no dadosgov (`TabularAPIPreview`) | FACTO |
| Não existe MCP nativo udata | INFERÊNCIA (confirmar) |
