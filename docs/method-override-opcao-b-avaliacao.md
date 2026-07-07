# Opção B — Túnel de verbos via `X-HTTP-Method-Override` — Proposta para avaliação

## Objetivo

Desbloquear as operações de escrita da plataforma (`PUT`, `PATCH`, `DELETE`) que estão a ser rejeitadas pelo WAF NetScaler/Citrix ADC em PPR e PRD, **sem depender de alterações à política do WAF** e sem alterar o comportamento dos consumidores externos da API.

## Em que consiste

O WAF bloqueia qualquer método que não seja `GET` ou `POST`, mas **não inspeciona os cabeçalhos** do pedido. A Opção B tira partido disso:

1. O frontend envia as operações mutantes como um pedido **`POST`** normal (que o WAF deixa passar).
2. Esse `POST` transporta o cabeçalho **`X-HTTP-Method-Override: <verbo>`** (por exemplo `PUT`).
3. Do lado da aplicação, um *middleware* WSGI lê o cabeçalho e **reescreve o método real** antes do *routing* do Flask.
4. A partir daí, tudo se comporta exatamente como se o verbo real tivesse sido enviado — o *handler*, as permissões, os *rate limits* e a serialização são os mesmos.

```
Browser                     WAF (Citrix ADC)              Aplicação (Flask)
   │                            │                              │
   │  POST /api/1/me/           │                              │
   │  X-HTTP-Method-Override:   │                              │
   │  PUT                       │                              │
   ├───────────────────────────►│  POST encaminhado tal como está
   │                            ├─────────────────────────────►│  Middleware:
   │                            │                              │  POST + cabeçalho → PUT
   │                            │                              │
   │                            │                              │  handler real (MeAPI.put)
   │                            │◄─────────────────────────────┤  resposta JSON
   │◄───────────────────────────┤                              │
   │   200 OK + JSON            │                              │
```

Trata-se de um **padrão consagrado na indústria**, implementado ou suportado nativamente por frameworks e fornecedores como Rails, Symfony, Laravel, ASP.NET Core e vários CDN/WAF.

## O que abrange (âmbito da alteração)

| Camada | Alteração | Ficheiro |
|---|---|---|
| Backend | *Middleware* WSGI que reescreve o método a partir do cabeçalho | `backend/udata/method_override.py` |
| Backend | Ligação do *middleware* na criação da aplicação | `backend/udata/app.py` (`create_app`) |
| Frontend | Transformação transparente das chamadas mutantes (aplica-se automaticamente aos 43 pontos de chamada) | `frontend/src/services/api.ts` |
| Configuração | Ativação por variável de ambiente de *build* | `frontend/.env` |

No frontend, a transformação é aplicada num *wrapper* do `fetch` local ao módulo, pelo que **todos os pontos de chamada mutantes são cobertos sem edição individual**.

## Como se ativa e controla

A transformação no frontend é **opt-in**, através da variável de *build* `NEXT_PUBLIC_USE_METHOD_OVERRIDE`:

| Ambiente | Valor | Motivo |
|---|---|---|
| Desenvolvimento local | `false` (por omissão) | O backend local não tem WAF; os verbos reais funcionam e são mais fáceis de depurar. |
| Pré-produção (PPR) | `true` | O NetScaler ADC bloqueia métodos não-GET/POST. |
| Produção (PRD) | `true` | Mesma política de WAF. |

> As variáveis `NEXT_PUBLIC_*` são embebidas no momento do *build*. Após alterar o valor, o frontend **tem de ser reconstruído (`npm run build`) e reiniciado**.

O *middleware* do backend está **sempre ativo** e é inofensivo quando não existe cabeçalho de override — logo, não requer qualquer *toggle* do lado da aplicação e pode permanecer permanentemente no lugar.

## Reversibilidade (rollback)

A desativação é imediata e sem risco: definir `NEXT_PUBLIC_USE_METHOD_OVERRIDE=false` (ou remover a linha) e reconstruir o frontend. O frontend volta a enviar os verbos reais. O *middleware* do backend permanece no lugar como *no-op* — é o estado recomendado.

## Garantias de segurança

A alteração introduz, de forma **controlada e mitigada**, um ponto de *HTTP Verb Tampering*. As mitigações estão embebidas no *middleware*:

- **Só pedidos `POST`** podem transportar um override. Um `GET` com `X-HTTP-Method-Override: DELETE` é **ignorado** — evita *smuggling* através de métodos cacheáveis.
- **Lista branca estrita:** apenas `PUT`, `PATCH` e `DELETE` são aceites como alvos. `OPTIONS`, `HEAD`, `TRACE`, `CONNECT` e verbos personalizados são rejeitados.
- O cabeçalho é **removido após consumo**, pelo que o código a jusante observa um pedido limpo.
- O método original é preservado (`environ["udata.original_method"]`) para efeitos de auditoria.
- **CSRF:** sem nova superfície — os *blueprints* da API já estão `csrf.exempt`; o caminho de override herda exatamente a mesma postura do `PUT`/`DELETE` original. A autenticação continua a depender dos cookies de sessão.
- **CORS:** sem alteração de *allowlist* — o *handler* de *preflight* espelha automaticamente o cabeçalho `X-HTTP-Method-Override`.
- **Rate limits:** o limitador corre **depois** da reescrita do método, pelo que as quotas por endpoint (`put`/`delete`) são consumidas corretamente e não colapsam num *bucket* genérico de `POST`.

## Impacto operacional a considerar

- **Observabilidade:** nos logs de acesso (nginx/gunicorn), as operações mutantes passam a aparecer como `POST /api/1/...`. Para distinguir uma operação destrutiva de um `POST` benigno é necessário **correlacionar com o cabeçalho `X-HTTP-Method-Override`** (ou registar `environ["udata.original_method"]` num *hook* de log de acesso). Este ponto é relevante para análise forense/investigação de incidentes.
- **Consumidores externos da API** (harvesters, integrações governamentais, jornalistas) continuam a usar `PUT`/`DELETE` reais — assume-se que circulam por redes que contornam o WAF público ou que estão *allowlisted*. O override é uma **alternativa, não um substituto**.
- **Auditoria:** o ponto de *HTTP Verb Tampering (CWE-650)* fica sinalizado para o próximo ciclo de auditoria KITS24, com a respetiva justificação registada.

## Estado de maturidade

A solução está **desenvolvida, testada e documentada**, pronta para promoção:

- **Testes backend:** 14 testes (11 unitários WSGI + 3 de integração contra endpoints reais) — incluindo o cenário de `GET→DELETE` recusado.
- **Testes frontend:** 9 testes (Vitest) — flag desligada, verbos permitidos, normalização, e verbos não afetados.
- **PRs abertos (draft) para `develop`:** backend #132 (`amagovpt/udata-pt`) e frontend #374 (`amagovpt/dadosgov-fe`).
- **Documentação técnica completa:** `docs/http-method-override.md`.

## Verificação após implementação

1. **Diagnóstico do WAF (via `curl`):** confirmar que um `PUT` real é bloqueado (HTML 500 + `cookie_adc_ext`) e que um `POST` com `X-HTTP-Method-Override: PUT` chega à aplicação e devolve JSON (confirmar `server: dados.gov` na resposta).
2. **Smoke test:** em `.../pages/admin/me/profile`, editar e submeter o perfil; no separador Network o pedido deve ser `POST`, com o cabeçalho `X-HTTP-Method-Override: PUT` e estado `200`. Repetir com uma ação destrutiva (apagar um dataset de teste) para validar o caminho `DELETE`.

---
*Detalhe técnico e exemplos de comandos em `docs/http-method-override.md`.*
