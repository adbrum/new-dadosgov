# Estimativa de Esforço — MCP e IA para o dados.gov.pt

**Documento**: Estimativa ROM (Rough Order of Magnitude)
**Âmbito**: 1) Criar MCP sobre as APIs do portal · 2) Datasets normalizados para consumo analítico e IA · 3) Funcionalidades de IA para o portal
**Base de análise**: codebase dadosgov (backend udata Flask+MongoDB+Elasticsearch; frontend Next.js 16)
**Data**: 2026-06-23

> Estimativa ROM com precisão de ±40%. Unidade: **PD = pessoa-dia** (~21 PD por pessoa-mês). Para cada frente é apresentado um **MVP** e um **alvo completo**. Não inclui provisionamento de cloud nem custos recorrentes de inferência LLM (OPEX), apenas esforço de desenvolvimento.

---

## 1. Contexto técnico que sustenta a estimativa

| Fator | Estado atual | Impacto |
| --- | --- | --- |
| API REST | v1 + v2 documentada (Flask-RestX/Swagger), 7 entidades principais + search ES | Facilita o MCP (WS1) |
| Pesquisa | Elasticsearch 8 com analisador morfológico; **sem vetorial/semântica** | Vetorial é infra nova (WS2/WS3) |
| Dados | Resources heterogéneos (csv, xlsx, parquet, json, geo…); preview tabular via serviço externo | Conteúdo já normalizado pelo **Hydra** (ver abaixo) |
| **Hydra** | Crawler/analisador de recursos do ecossistema udata: faz parsing dos ficheiros (deteção de tipos via csv-detective) e guarda o conteúdo numa BD consultável; já ligado via `TABULAR_EXPLORE_URL` (`TabularAPIPreview`) | **Reduz drasticamente o WS2** — passa de *construir o pipeline* para *consumir o Hydra* |
| IA/LLM | **Inexistente** em backend e frontend | Tudo é greenfield (prompts, guardrails, custos, eval) |
| Async/cache | Celery + Redis + Flask-Caching já em uso | Reaproveitável para a camada de consumo |

> **Decisão de arquitetura**: todo o conteúdo dos ficheiros (recursos) dos datasets vive já no **Hydra**, e **todas as consultas de dados feitas pela IA (via MCP) são executadas contra o Hydra**. Não é construído um *store* analítico próprio nem um pipeline de ingestão/parsing — esse trabalho é fornecido pelo Hydra.

---

## 2. WS1 — MCP sobre as APIs do portal

Servidor MCP (Python, alinhado ao stack do backend) que expõe os endpoints públicos como *tools* read-only.

| Bloco | PD |
| --- | --- |
| Scaffold MCP SDK + configuração (base URL, API key opcional) | 2 |
| Tools: datasets (search/get/resources) | 3 |
| Tools: organizations, reuses, dataservices, topics, spatial, tags | 5 |
| **Tool de consulta de dados no Hydra** (filtros/agregações sobre o conteúdo dos recursos) | 4 |
| Paginação, rate-limit, normalização de erros, output token-efficient | 3 |
| MCP resources (navegação de catálogo) + prompts | 2 |
| Testes (unit + integração contra staging) | 3 |
| Packaging, Docker, deploy, CI, documentação de uso | 3.5 |
| Buffer/revisão | 3 |

- **MVP** (datasets + organizations + search + consulta Hydra): **~16 PD**
- **Completo**: **~28–32 PD** (≈ 6 semanas, 1 dev)
- **Risco**: baixo · **Dependências**: acesso ao Hydra (WS2)

---

## 3. WS2 — Camada de consumo analítico sobre o Hydra

Como o **Hydra já contém o conteúdo dos recursos parseado e tipado**, esta frente deixa de incluir ingestão, parsing, deteção de schema, qualidade e *store* analítico (tudo fornecido pelo Hydra). O esforço concentra-se na **camada de acesso/consulta** que a IA (MCP) usa para consultar o Hydra.

**Núcleo (obrigatório):**

| Fase | PD |
| --- | --- |
| A. Discovery: mapear schema/API do Hydra (tabular-api), modelo dos recursos parseados, autenticação | 3 |
| B. Conector/camada de acesso ao Hydra (query, filtros, agregações, paginação, segurança) | 6 |
| C. Exposição de dicionário de dados / metadados de colunas (a partir do csv-detective/Hydra) | 3 |
| D. Caching, rate-limit e monitoria sobre as queries ao Hydra | 3 |
| E. Testes, docs, hardening | 3 |

**Opcional (camada de IA sobre os dados):**

| Fase | PD |
| --- | --- |
| F. Embeddings de metadados/colunas + vector store (descoberta semântica) | 7 |
| G. Enriquecimento de metadados via LLM (descrições, tags, semântica de colunas) | 5 |

- **MVP** (apenas núcleo): **~18 PD**
- **Completo** (núcleo + opcionais): **~28–32 PD** (≈ 1,5 pessoa-mês)
- **Risco**: baixo-médio (depende da maturidade/cobertura do Hydra e da estabilidade da sua API)
- **Dependências**: instância do Hydra disponível e acessível; vector store apenas se forem feitas as fases opcionais

---

## 4. WS3 — Funcionalidades de IA no portal

Backend + frontend (ambos greenfield em IA). Conjunto representativo de funcionalidades:

| Funcionalidade | Backend (PD) | Frontend (PD) |
| --- | --- | --- |
| Pesquisa semântica/híbrida (ES + vetores) | 8 | 4 |
| Assistente conversacional do catálogo (RAG sobre metadados + dados normalizados) | 12 | 8 |
| Recomendações ("datasets relacionados") | 6 | 2 |
| Resumos/auto-tags por LLM expostos na UI | 5 | 3 |
| Perguntas em linguagem natural sobre um dataset (NL→query contra o Hydra) | 8 | 6 |
| LLM-ops: gestão de prompts, guardrails, custos, cache, eval | 8 | — |
| Acessibilidade/i18n (PT) + design system Agora | — | 4 |
| Testes, docs | 4 | 2 |

- **MVP** (pesquisa semântica + assistente): **~45 PD**
- **Completo**: **~86–108 PD** (≈ 4–5 pessoa-meses)
- **Risco**: médio-alto
- **Dependências fortes**: Hydra + camada de acesso do WS2; idealmente o WS1 (o MCP alimenta o agente e executa as consultas no Hydra)

---

## 5. Resumo e roadmap recomendado

| Frente | MVP (PD) | Completo (PD) | Risco | Depende de |
| --- | --- | --- | --- | --- |
| WS1 — MCP | 16 | 28–32 | Baixo | Hydra (WS2) |
| WS2 — Consumo analítico sobre o Hydra | 18 | 28–32 | Baixo-médio | Instância Hydra |
| WS3 — Features IA | 45 | 86–108 | Médio-alto | Hydra, WS2, WS1 |
| **Total** | **~79 PD** | **~142–172 PD** | | |

> **Impacto do Hydra**: a adoção do Hydra reduz o total completo de ~186–235 PD para **~142–172 PD** (poupança de ~45–65 PD), elimina o maior foco de risco (pipeline de normalização próprio) e dispensa o provisionamento de *store* analítico/object storage para os dados.

- **Completo ≈ 142–172 PD ≈ 7–8 pessoa-meses.** Com equipa de **3** (1 backend, 1 dados/ML, 1 frontend) → **~3,5–4 meses de calendário**.
- **Sequência sugerida**: WS2 núcleo (camada de acesso ao Hydra — desbloqueia tudo) → WS1 (MCP que consulta o Hydra, entrega rápida e valor imediato) → WS3 sobre as duas anteriores.
- **Faseamento de valor**: um MVP combinado (camada Hydra + MCP + pesquisa semântica sobre metadados) é entregável em **~45–55 PD** e demonstra IA no portal logo no início.

---

## 6. Pressupostos

- API pública estável e documentada.
- **Hydra disponível, operacional e a cobrir os datasets relevantes**; todas as consultas de dados da IA (via MCP) são executadas contra o Hydra. A sua API/schema é estável e acessível pela camada de consumo.
- Infra de vector store disponibilizada apenas se forem realizadas as fases opcionais do WS2 (não está incluído o provisionamento de cloud nem os custos recorrentes de inferência LLM, que são OPEX, não esforço de desenvolvimento).
- LLM via API gerida (Claude/OpenAI), não self-hosted.
- Estimativa de desenvolvimento; não inclui gestão de projeto, UX research aprofundada nem formação de utilizadores finais.
