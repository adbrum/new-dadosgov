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
| `PreToolUse` / `Bash` | `guard-protected-branch.py` | **Nega** commit/push/merge/rebase/reset --hard em `backend/` ou `frontend/` quando o submódulo está em `develop`, `tst`, `ppr` ou `main`. O alvo vem do **`cwd` do payload** e de todos os `-C`/`cd` do comando — ler só o texto deixava passar `cd backend` numa chamada e `git commit` na seguinte. Nega force-push em qualquer sítio (mas não confunde um heredoc que só menciona o comando com a sua execução). O monorepo está fora de âmbito, por opção. |
| `PostToolUse` / `Write\|Edit` | `lint-changed-file.py` | `uv run ruff check --fix` + `ruff format` em `backend/**.py` (~0,5 s); `npx eslint --fix` em `frontend/**.ts(x)` (~2 s). O que não é auto-corrigível volta ao modelo como contexto, para ser corrigido no mesmo turno. |
| `SessionStart` | `session-context.py` | Injeta o estado real: branch e ficheiros modificados de cada submódulo, PRs abertos em cada repo, e o fluxo de promoção. Elimina a suposição errada mais comum — "em que branch e em que repo estou". |
| `PreToolUse` / `Edit\|Write\|Bash` | `guard-test-surface.py` | Enquanto existir `.claude/state/fix-loop.lock`, **nega** escritas em ficheiros de teste (ver secção 2). Inerte sem lock. |
| `Stop` | `stop-verify.py` | Antes de o turno fechar, diz que suite de testes ficou em dívida para os ficheiros efetivamente tocados. Não corre pytest (leva minutos) — só impede que a verificação seja silenciosamente saltada. |

| — (CLI) | `harness_root.py` | Resolve **uma só vez** qual é o checkout cujo `.claude/` manda: `CLAUDE_HARNESS_ROOT`, depois `CLAUDE_PROJECT_DIR`, depois a pasta do próprio ficheiro. Antes, cada hook derivava a raiz do seu `__file__` — e como `abspath` normaliza lexicalmente, a resposta dependia da string de invocação. |
| — (CLI) | `harness_patterns.py` | As três expressões que mais de um hook tem de partilhar: Conventional Commits, atribuição de IA, e a superfície de teste congelada (em duas formas — texto de shell e caminhos de git). Estavam duplicadas, cada cópia com um comentário a dizer que era mantida "em sintonia" com a outra à mão. |
| — (CLI) | `ticket-worktree.py` | `create`/`list`/`remove` das árvores por ticket (secção 3). |

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
| `plan-auditor` | Julga um plano da Fase 4 antes de um humano o ler: satisfaz os critérios, replica o precedente, mantém-se no âmbito, as provas provam algo. Read-only — um auditor que pode editar o que audita não é auditor. |

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

E os subcomandos do estado do ticket que se usam à mão:
`ticket-state.py doctor` (onde é que tudo resolveu), `status` (todos os tickets em curso),
`claim` (que repos e que árvore este ticket toca), `plan-audit` (a metade verificável de um
plano), `park`/`unpark` (parar com a decisão em dívida escrita).

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

### Loop de correção guardado (`/fix-loop`)

Um loop com o objetivo "ficar verde" tem uma solução degenerada: enfraquecer o teste. Apaga a
asserção, marca `it.skip`, estreita o `include` do runner — fica verde e o bug fica lá. O
`/fix-loop` retira a capacidade em vez de pedir contenção.

| Garantia | Como é imposta |
| --- | --- |
| O veredicto assenta no **exit code** do runner | `verify` exige `code == 0`. Nunca numa regex sobre o output: a primeira versão dava APROVADO quando o output não era parseável (um import quebrado, um timeout, o runner ausente) |
| Testes **e configuração** não editáveis durante o loop | `PreToolUse` (`guard-test-surface.py`) nega escritas em testes, `conftest.py`, `factories.py`, `vitest.config.ts`, `playwright.config.ts`, `pyproject.toml`, `pytest.ini`, `setup.cfg`, `tox.ini` — congelar só os testes não bastava, porque estreitar a seleção do runner remove falhas igualmente bem |
| Sem loop sem falha inicial | `start` recusa se a suite já estiver verde, ou se não conseguiu correr |
| Escritas fora do hook são apanhadas | `verify` pergunta ao **git** o que mudou desde o commit da baseline — e **aborta** se o git falhar, em vez de passar vazio |
| Contagem de testes não desce, skipped não sobe | `verify` compara com a baseline (backend via `pytest --collect-only`, que é o único sítio onde a contagem aparece) |
| Marcas de enfraquecimento | Procuradas **só** na superfície congelada, senão o `.skip(offset)` de paginação MongoEngine em código-fonte dava falso positivo |
| O loop tem fim | 4 tentativas (`MAX_ATTEMPTS` em `fix-loop-state.py`, a autoridade), consumidas pelo próprio `verify` — antes o contador era voluntário e nada o impunha |

Regressões cobertas em `.claude/hooks/tests/test_guards.py` (21 casos, um por buraco
encontrado em revisão): `python3 .claude/hooks/tests/test_guards.py`.

**O limite honesto:** este processo pode libertar o seu próprio lock, e a mensagem de negação
até diz como. Torna a batota visível e trabalhosa, não impossível — por isso o `end` fica
registado em `.claude/state/fix-loop.log`.

**A autoridade que o agente não alcança é o CI.** `dadosgov-fe/.github/workflows/tests.yml`
corre a suite em cada PR e falha se a contagem de testes descer ou os skipped subirem em
relação à base. Só é um *gate* se estiver marcado como required nas branch protection rules —
caso contrário é um sinal. O backend ainda não tem equivalente: a suite é pesada e já tem
falhas conhecidas em `develop`, portanto precisa de abordagem própria.

Por omissão está **inativo**: sem lock, o hook é inerte e o `/watch-pr` reporta sem corrigir.
O autofix é opt-in explícito (`/watch-pr --autofix`).

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

## 3.5. Vários tickets ao mesmo tempo

Uma sessão por ticket. O que não se partilha não é o monorepo — é o **checkout de um
submódulo**: um checkout está numa branch, e duas suites de backend apagam e recriam a mesma
base de dados de teste Mongo.

O que estava a impedir isto não era o modelo. `active_states()` impunha **todos** os tickets
ativos a **todas** as escritas: um ticket ainda à espera do plano trancava `backend/` *e*
`frontend/` para os outros, e duas sessões acabavam à espera uma da outra. A posse passou a
ser **por repo e por árvore** — uma escrita é julgada só pelos tickets que reclamam aquele
repo naquele checkout, e um checkout que ninguém reclama não tem nada a impor. Um ticket que
ainda não chegou à Fase 3 continua a reclamar os dois submódulos, que é o que mantém o gate
da aprovação fechado antes de se saber onde o código vai cair.

```bash
python3 .claude/hooks/ticket-state.py claim LEDG-2296 --repos backend   # Fase 3
python3 .claude/hooks/ticket-worktree.py create LEDG-2301 --repos backend
python3 .claude/hooks/ticket-worktree.py list
```

**A sessão corre sempre da raiz do monorepo.** A árvore do ticket é um caminho gravado no
estado (`workdir`), não um segundo projeto: um `settings.json`, um universo de permissões,
um `.claude/state/`, um `ticket.log` para toda a frota. Dar a cada árvore o seu próprio
`.claude/` parece mais arrumado e é uma armadilha — os hooks resolvem a raiz a partir da
string de invocação, e um guard apontado ao estado errado **não falha**: não encontra ticket
nenhum e comporta-se como se não houvesse nada a impor. `ticket-state.py doctor` existe para
isso ser visível, e o `session-context` repete o aviso ao início de cada sessão.

Também não é uma worktree do monorepo: `git worktree add` não faz checkout de submódulos, pelo
que dá `backend/` e `frontend/` **vazios** — o orfão `.claude/worktrees/stupefied-buck-e8566b`
era precisamente isso, e foi apagado.

Duas coisas que uma árvore fresca não tem e que fazem as suites mentir em silêncio:
`backend/.env` e `frontend/.env` (o `create` liga-os por symlink), e as dependências (`uv sync`
/ `npm ci` a sério — um `.venv` partilhado por symlink tem o `.pth` editável a apontar para o
checkout principal, e os testes correriam contra o código errado).

**A suite de backend** partilha as BD de teste: `_clean_db` trunca todas as coleções entre
testes, logo duas corridas com o mesmo nome de BD apagam os fixtures uma da outra a meio. O
`verify` reserva a suite (pid + timestamp) e **recusa em vez de esperar** — a sessão termina o
turno e volta dentro de minutos; uma reserva cujo processo morreu é assumida automaticamente.
Um `flock` seria pior: o `verify` corre dentro de uma chamada com timeout, e ao matar o grupo
de processos o lock libertava-se **a meio do pytest**.

Um ticket com árvore própria deixa de serializar: o `verify` exporta
`UDATA_TEST_MONGO_PREFIX=…/udata_test_<ticket>` e o `udata/tests/plugin.py` dá a cada corrida
as suas BD. A reserva passa a ser por prefixo, e o `pgrep` só se aplica quando os nomes são os
por omissão. **Isto é verificado, não assumido**: uma worktree cortada antes dessa alteração
ter aterrado partilharia `udata-test` enquanto o harness acreditava o contrário — pior do que
serializar — por isso o `verify` confirma que a árvore honra a variável antes de parar de
serializar.

### Quando um ticket para: `park`

Uma sessão que encontra uma decisão que não é dela deixava a razão num transcript que ninguém
relê. `park` escreve-a: um `reason_code` de um conjunto fechado (para se poderem triar cinco
tickets estacionados), a pergunta com as opções, o diagnóstico, e a forma do trabalho no
momento em que parou — fase, branches, pontos feitos com os shas, `git status`.

Deliberadamente **não** é um `pause`: o `pause` desliga os guards, o que aqui seria ao
contrário — um ticket estacionado antes do plano aprovado tem de manter os repos trancados
enquanto espera. O caso `#T19` da suite de guards fixa isso contra o `#T3`.

## 4. Decisões deliberadas e pendências

**Decidido:** nada corre por agendamento. Todo o trabalho recorrente é invocado à mão
(`/triage-sprint`, `/deploy-check`, `/loop /watch-pr`). Não é uma pendência — é a opção
tomada, e é reversível a qualquer momento com `/schedule`.

**Pendente:** a instrução condicional sobre o `gh` está aplicada no monorepo e proposta nos
dois submódulos — PRs [udata-pt#222](https://github.com/amagovpt/udata-pt/pull/222) e
[dadosgov-fe#580](https://github.com/amagovpt/dadosgov-fe/pull/580), à espera de integração em
`develop`. Até lá, os `CLAUDE.md` desses repos continuam a afirmar que o `gh` não existe.

**Pendente:** o `UDATA_TEST_MONGO_PREFIX` está feito no `udata-pt` mas ainda tem de subir a
escada de ambientes (`develop → tst → ppr → main`). O `verify` já o usa quando a árvore o
suporta e serializa quando não — portanto o paralelismo total das suites de backend só existe
em árvores cortadas de um `develop` que já tenha essa alteração.

**Pendente:** o modo autónomo (`/ticket auto`, sem os dois gates humanos) foi desenhado e
adiado por opção — primeiro medir onde é que o loop interativo realmente para a pedir coisas,
que é a pergunta da secção 3. Todos os passos acima são pré-requisitos dele: `park` com
`reason_code`, `plan-audit` determinístico, posse por repo/árvore e a reserva da suite.
