# Harness do agente — dadosgov

Como está configurado o Claude Code neste monorepo para trabalhar tickets de ponta a ponta, e
como correr trabalho recorrente (loops e agendado).

Dois conceitos distintos:

- **Harness engineering** — configurar o que o *runtime* faz por nós, deterministicamente:
  skills, subagentes, hooks, permissões, comandos. O modelo pode esquecer uma regra do
  `CLAUDE.md`; um hook não esquece.
- **Loop engineering** — fechar o ciclo para o agente continuar entre turnos: `/loop`,
  wake-ups auto-agendados, e agentes agendados por cron.

A ordem importa: sem harness sólido, um loop só amplifica erros.

---

## 1. O que está instalado

### Hooks (`.claude/hooks/`, ligados em `.claude/settings.json`)

| Evento | Script | O que faz |
| --- | --- | --- |
| `PreToolUse` / `Bash(git *)` | `guard-protected-branch.py` | **Nega** commit/push/merge/rebase/reset --hard em `backend/` ou `frontend/` quando o submódulo está em `develop`, `tst`, `ppr` ou `main`. Nega force-push em qualquer sítio. |
| `PostToolUse` / `Write\|Edit` | `lint-changed-file.py` | `uv run ruff check --fix` + `ruff format` em `backend/**.py` (~0,5 s); `npx eslint --fix` em `frontend/**.ts(x)` (~2 s). O que não é auto-corrigível volta ao modelo como contexto, para ser corrigido no mesmo turno. |
| `SessionStart` | `session-context.py` | Injeta o estado real: branch e ficheiros modificados de cada submódulo, PRs abertos em cada repo, e o fluxo de promoção. Elimina a suposição errada mais comum — "em que branch e em que repo estou". |
| `Stop` | `stop-verify.py` | Antes de o turno fechar, diz que suite de testes ficou em dívida para os ficheiros efetivamente tocados. Não corre pytest (leva minutos) — só impede que a verificação seja silenciosamente saltada. |

Todos os scripts saem sempre com código 0 excepto o guard, que devolve uma decisão `deny`
explícita. Um script avariado nunca bloqueia trabalho legítimo.

Para revisitar ou desativar: `/hooks`.

### Skill do ciclo de vida

`.claude/skills/jira-ticket-workflow/SKILL.md` — 9 fases, do ticket ao PR:

1. Ler o ticket no **Jira MCP** (projeto `LEDG`, site `ticapp.atlassian.net`,
   cloudId `0d1d9259-29f0-46ff-bb50-522a373f8daf`). Fallback: `docs/jira-tickets-frontend-backend.md`.
2. **Procurar precedentes** (obrigatório) — `git log --all --grep`, `gh pr list --search`, grep
   por wrappers já existentes.
3. Decidir o(s) repo(s) e, se forem os dois, a **ordem de deploy**.
4. Branch a partir de `develop`: `<type>/ledg-<n>-<descrição-em-inglês>`.
5. Implementar ponto a ponto, **um commit por ponto** (Conventional Commits, inglês, sem
   qualquer atribuição de IA).
6. Gate de verificação: lint, tipos, testes, e os critérios de aceitação um a um.
7. PR para `develop` com `gh pr create`.
8. Fechar o ciclo no Jira: comentário com o URL do PR, worklog, transição.
9. Relatório final.

### Subagentes (`.claude/agents/`)

| Agente | Para quê |
| --- | --- |
| `explorer-dadosgov` | Localizar código e precedentes nos dois submódulos. Read-only, devolve caminhos e excertos — não despeja ficheiros no contexto principal. |
| `udata-backend` | Implementar backend (Flask/MongoEngine/Celery/harvesters) com as regras do fork. |
| `next-frontend` | Implementar frontend (App Router, service layer, SSR/ISR) com as armadilhas conhecidas de cache e i18n. |
| `promoter` | Só git/GitHub: abre e acompanha PRs pelo fluxo de promoção. Nunca mexe em código de aplicação. |

### Comandos (`.claude/commands/`)

| Comando | O que faz |
| --- | --- |
| `/ticket LEDG-XXXX` | Ciclo completo do ticket (invoca a skill acima). |
| `/promote <repo> <ambiente>` | Abre o PR de promoção para o ambiente seguinte. |
| `/ci [repo] [pr]` | Estado do CI, com a asserção real que falhou. |
| `/deploy-check <ambiente>` | Smoke test dos pontos que historicamente quebram primeiro. |
| `/watch-pr [repo] [pr]` | Um *tick* de vigilância de PR — desenhado para correr sob `/loop`. |
| `/triage-sprint` | Relatório read-only do sprint e do que falta promover. |
| `/install [backend\|frontend]` | Instalar dependências. |

---

## 2. Loop engineering

### Loop in-session (auto-cadenciado)

```
/loop /watch-pr frontend 579
```

Sem intervalo, o agente escolhe a cadência: para CI usa `gh run watch` em background em vez de
poll curto, e termina o loop quando já não há nada para observar. Regra fixada no
`/watch-pr`: **parar** quando todos os PRs em escopo estão merged, fechados ou reportados
vermelhos.

### Loop com intervalo fixo

```
/loop 15m /deploy-check ppr
```

Para vigiar um ambiente durante uma janela de deploy. Um tick sem novidade deve reportar-se
como *noop* — assim as observações silenciosas colapsam no terminal em vez de o encherem.

### Agendado (cron) — opção disponível, deliberadamente não usada

**Não há nada agendado neste projeto, por decisão.** `/triage-sprint` e `/deploy-check` são
comandos normais: corre-se quando se quer, escrevendo-os. O cron seria apenas um despertador
por cima deles — não acrescenta capacidade nenhuma, só remove o "quando" das mãos de quem
trabalha. O mesmo vale para o `/loop`: só arranca quando é escrito.

Se algum dia se quiser agendar, prepara-se com `/schedule`. Candidatos naturais, caso a
decisão mude:

| Quando | O quê |
| --- | --- |
| Dias de semana, 08:30 | `/triage-sprint` — sprint sem critérios de aceitação, itens parados, promoções pendentes |
| Dias de semana, 09:00 | `/deploy-check ppr` — saúde do ambiente antes do dia começar |

Regras que se aplicariam a qualquer cron neste projeto:

- **Read-only por omissão.** Um cron não transiciona tickets, não faz merge, não faz push para
  `main`. Produz relatório; a decisão é humana.
- Não correm em `bypassPermissions` — usar o allowlist explícito de `.claude/settings.json`,
  porque um loop autónomo para em cada prompt de permissão.
- Cada cron escreve um relatório curto. Se não há nada a dizer, diz "nada a reportar".

---

## 3. Fechar o ciclo (Fase 7)

Depois de 3–5 tickets, a pergunta a fazer não é "o agente portou-se bem?" mas **onde é que ele
parou e precisou de mim?**. Cada paragem cai numa de três categorias, e cada uma tem um sítio
próprio para ser corrigida:

| Sintoma | Causa | Onde corrigir |
| --- | --- | --- |
| Parou num prompt de permissão | Regra em falta no allowlist | `.claude/settings.json` → `permissions.allow` (ou `/fewer-permission-prompts`) |
| Fez algo que a equipa proíbe | Regra que estava só em prosa | Um hook em `.claude/hooks/` |
| Repetiu uma investigação já feita | Conhecimento não persistido | Memória do projeto, ou uma linha no `CLAUDE.md` |
| Escolheu o padrão errado | Precedente não encontrado | Reforçar a fase de precedentes na skill |

Corrigir aí — não no prompt seguinte. Um prompt corrige um turno; o harness corrige todos os
turnos futuros.

---

## 4. Decisões deliberadas e pendências

**Decidido:** nada corre por agendamento. Todo o trabalho recorrente é invocado à mão
(`/triage-sprint`, `/deploy-check`, `/loop /watch-pr`). Não é uma pendência — é a opção
tomada, e é reversível a qualquer momento com `/schedule`.

**Pendente:** a instrução condicional sobre o `gh` está aplicada no monorepo e proposta nos
dois submódulos — PRs [udata-pt#222](https://github.com/amagovpt/udata-pt/pull/222) e
[dadosgov-fe#580](https://github.com/amagovpt/dadosgov-fe/pull/580), à espera de integração em
`develop`. Até lá, os `CLAUDE.md` desses repos continuam a afirmar que o `gh` não existe.
