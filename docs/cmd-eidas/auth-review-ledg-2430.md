# Revisão da autenticação do portal — LEDG-2430

> **Este documento é o espelho do [LEDG-2430](https://ticapp.atlassian.net/browse/LEDG-2430).**
>
> É a fonte no repositório para quem trabalha este refinamento sem abrir o Jira. **Sempre que o
> ticket for alterado, este ficheiro é alterado no mesmo passo** — e o contrário também. Se
> divergirem, **o Jira prevalece** e este ficheiro está desatualizado, porque é lá que as
> decisões são tomadas e comentadas.
>
> **Última sincronização: 2026-09-09.**

---

## 🛑 DECISÃO DE PROMOÇÃO: nada sai de `tst` até a reformulação estar completa

Decidido a **2026-09-08**: as promoções `tst → ppr` e `ppr → main` só acontecem quando **toda**
a reformulação CMD/eIDAS estiver feita e validada. **Não se promove por ticket.**

- O `tst` vai **acumular os pontos todos** antes de subir, logo a promoção final será grande. É
  o custo aceite — e a alternativa (promover ticket a ticket) tem o risco de deixar o fluxo
  **meio-migrado** em produção, que é exactamente o que produziu as duas regressões descritas
  abaixo.
  📊 **A curva, medida a cada ponto que entra** — é o argumento a usar se a decisão tiver de
  ser reavaliada:

  | Quando | Pontos feitos | `tst → ppr` backend | `tst → ppr` frontend |
  | --- | --- | --- | --- |
  | 2026-09-08 | 1 a 4 | 85 | 80 |
  | 2026-09-09 | + o 6 (LEDG-2462) | **103** | 80 |
  | 2026-09-10 | + o 7 (LEDG-2465) | **108** | 80 |
  | 2026-09-10 | + o LEDG-2467 (fora da decomposição) | **113** | 80 |
  | 2026-09-11 | + o 8 (LEDG-2466) | **116** | 80 |
  | 2026-09-11 | + o 9 (LEDG-2464) | **122** | 80 |
  | 2026-09-11 | + o 10 parcial (LEDG-2468) | **126** | 80 |
  | 2026-09-11 | + o 5 (LEDG-2434) | **132** | **101** |
  | 2026-09-11 | + a alínea (c) do 13 (LEDG-2435) | **138** | 101 |
  | 2026-09-14 | *(nada deste refinamento)* — LEDG-2327, PRs #281/#282 | **144** | 101 |
  | 2026-09-14 | + o 16 (LEDG-2438), PR #284 | **152** | 101 |

  🚩 **A linha de 09-14 não tem um único commit desta reformulação.** Os seis que
  levaram o backend de 138 a 144 vieram do LEDG-2327 (harvest domain / INE ownership),
  promovido a `tst` por outra frente. O ponto 16 (LEDG-2438) está em `develop` e **ainda
  não subiu**. ⚠️ É a segunda vez que isto se regista, e é o custo concreto de promover
  em bloco: a dívida que a promoção final vai ter de rever **cresce sozinha**, por
  trabalho que esta revisão não controla nem consegue validar.

  Uma parte é anterior a este refinamento e já lá estava; o ponto é que **o número não desce**,
  e a promoção final não será revisível commit a commit.

  🚩 **E a última linha prova-o melhor do que qualquer argumento: o frontend subiu de 80 para 101
  sem este refinamento lhe ter tocado.** O LEDG-2434 é backend puro — e só `scripts/`. Os 21
  commits que apareceram no `tst` do frontend vieram de outras frentes, entre a medição de ontem e
  a de hoje. ⚠️ **É esse o custo real da decisão de promover em bloco:** a dívida cresce por
  trabalho que esta revisão não controla, e quem rever a promoção final vai ter de separar o que é
  desta reformulação do que não é. Para referência, `ppr → main` está em **86** no backend e
  **122** no frontend.

  ⚠️ **A métrica inclui os merges** (`git log origin/ppr..origin/tst`), para ser comparável com as
  medições anteriores. Sem merges, o backend está em 97.
- ⚠️ **O LEDG-2437 deixa de ser uma ação de release independente.** Fechava com um
  `ppr → main` do frontend a qualquer momento; passa a esperar pelo conjunto. **O 404 em
  produção mantém-se até lá** — risco aceite, e agora por mais tempo do que o previsto.
- Quanto mais o `tst` acumular, **mais importa testar lá cada ponto à medida que entra**, e não
  só no fim. Uma regressão descoberta na promoção final é muito mais caro de localizar entre
  dezanove pontos do que entre um.

## Objetivo

Garantir a identificação única e inequívoca dos utilizadores autenticados por Autenticação.gov
(CMD) e eIDAS, e deixar de fabricar endereços de email sintéticos para quem se autentica sem
email.

As decisões de âmbito estão tomadas e **todos os pontos têm ticket**. A ordem está justificada
e trocá-la parte a implementação.

---

## 📍 LER PRIMEIRO: o fluxo de autenticação está DIFERENTE em cada ambiente

Toda a análise deste documento descreve **`develop`**. Os quatro ambientes não têm o mesmo
código de autenticação, e foi precisamente isso que produziu as duas regressões abaixo.

Verificado com `git cat-file` / `git grep` após `fetch`, **revalidado a 2026-09-08**:

**Frontend (`dadosgov-fe`)**

| Ficheiro | develop | tst | ppr | main |
| --- | --- | --- | --- | --- |
| `EmailLoginForm.tsx` (login tradicional) | ✅ | ✅ | ✅ | ✅ |
| `complete-registration/page.tsx` | ✅ | ✅ | ✅ | ❌ |
| `CompleteRegistrationClient.tsx` | ✅ | ✅ | ✅ | ❌ |
| `CompleteRegistrationGate.tsx` | ✅ | ✅ | ✅ | ❌ |
| `ConfirmEmailNotice.tsx` | ✅ | ✅ | ❌ | ❌ |
| `__tests__/` do login | ✅ | ✅ | ❌ | ❌ |
| `auth/login/route.ts` com `migration_required` | ✅ | ✅ | ✅ | ✅ |

**Backend (`udata-pt`)**

| Marcador | develop | tst | ppr | main |
| --- | --- | --- | --- | --- |
| `has_placeholder_email` | ✅ | ✅ | ✅ | ✅ |
| redirect `/complete-registration` | ✅ | ✅ | ✅ | ✅ |
| `pending_registration` na API `/me` | ✅ | ✅ | ✅ | ✅ |
| `_link_identity_and_login` | ✅ | ✅ | ❌ | ❌ |
| guardas `nic_required` | ✅ | ✅ | ❌ | ❌ |
| `_record_login_activity` (LEDG-2462) | ✅ | ✅ | ❌ | ❌ |
| `migrate-nics` / `_find_shared_nics` | ✅ | ✅ | ✅ | ✅ |

**Saúde deste fluxo, por ambiente:**

| Branch | Página de conclusão | Login tradicional | Saudável? |
| --- | --- | --- | --- |
| `develop` | ✅ | ✅ | **Sim** |
| `tst` | ✅ | ✅ | **Sim** |
| `ppr` | ✅ | ✅ | **Sim** |
| `main` | ❌ | ✅ | Não — LEDG-2437 |

⚠️ **Reproduzir um problema num ambiente não diz nada sobre os outros neste fluxo.** Antes de
dar um bug por confirmado ou por corrigido, verificar em que branch se está.

---

## 🚩 A flag `MIGRATION_MODE_ENABLED` tem TRÊS valores por omissão diferentes

Transversal a quase todos os pontos, e invalida qualquer raciocínio que assuma um valor:

| Onde | Valor por omissão |
| --- | --- |
| `udata.cfg` — `_env_bool("MIGRATION_MODE_ENABLED", True)` | `True` |
| `udata/settings.py` (dentro de `class Testing`) | `True` |
| `_migration_enabled()` — `saml_govpt.py`, `.get(..., False)` | `False` |

O `udata.cfg` faz `load_dotenv()`, logo **o valor efetivo é o que estiver no `.env` daquele
ambiente** — e cada ambiente tem o seu, que não está no repositório.

- ❗ **Não é possível saber pelo repositório se a migração está ligada em dev, tst, ppr ou
  main.** O LEDG-2434 deve registar os quatro valores.
- "A migração está desligada" só é verdade **onde o `.env` a desliga explicitamente**. Por
  omissão do código, está **ligada**.
- O terceiro default **contradiz** os outros dois. **Vale alinhar os três.**

---

## 🚨 As duas regressões: o mesmo erro em espelho

Uma alteração full-stack cujas metades seguem por repos independentes, e uma avança sem a outra.

### LEDG-2437 — o backend foi à frente: 404 em produção

O PR #206 foi feito em duas metades no mesmo dia (2026-08-20). **Só a do backend foi promovida
a produção** — backend `main` em 25/08, frontend `main` em 14/08.

**Confirmado em produção a 2026-09-07:** `/pt/complete-registration` → **404**; controlo
`/pt/datasets` → 200. As contas com endereço sintético são autenticadas e enviadas para um 404,
**em cada login**, sem alternativa.

**Resolve-se com a promoção `ppr → main`.** Não tem implementação.

### LEDG-2432 — o frontend foi à frente: login tradicional removido ✅ CORRIGIDO

O commit `7d5c9b50` removeu o formulário de email e palavra-passe de `develop` e `tst`, a
assumir que a migração seria obrigatória. Como fica **opcional**, quem tinha conta antiga ficava
sem forma de entrar.

Corrigido e promovido a `tst`. Na correção apareceram **dois defeitos que não estavam no
pedido**, e valem como aviso:

- um **open redirect** introduzido pela própria correção, no `sanitizeNextUrl` — quatro grafias
  passavam o teste de prefixo e resolviam para outro domínio. Corrigido por comparação de
  origem, com 17 testes de regressão;
- a **barreira dos termos era contornável com a tecla Enter**, com o botão desativado.

### A lição transversal

| Onde | Erro | Consequência |
| --- | --- | --- |
| Frontend | Assumiu a flag a `True` e removeu o formulário de login | Ninguém entrava por email/palavra-passe |
| Backend | O caminho que pediria um email real está **atrás** da flag | Com a flag a `False`, continua a duplicar contas |

**Regra:** qualquer fluxo de autenticação tem de funcionar com a flag nos dois estados, e ser
**testado nos dois**. Melhor ainda — como o login já faz — **quem decide é o backend, por
conta**; o frontend não lê a flag e por isso não pode assumir o valor errado.

---

## ⚠️ O problema real é mais largo do que o pedido: DUAS classes de conta duplicada

O pedido original fala de endereços `saml-*`. Apareceram **duas** formas de duplicar a conta de
uma pessoa, e só uma passa pelo prefixo. **Enunciar o objetivo como "não gerar endereços
sintéticos" deixaria metade do problema em pé e pareceria cumprido.**

### Classe 1 — endereço fabricado, uma conta nova em CADA login

Com a flag a `False`, uma identidade que não fica ligada não recebe **uma** conta: recebe **uma
por login**.

1. Login 1 → nada corresponde → conta criada com o email real da asserção.
2. Login 2 → resolve por email → `migration_candidate` → **a conta encontrada é descartada** →
   `_create_saml_user` → email tomado → **endereço fabricado, conta nova**.
3. Login 3 → outra.

O descarte é correcto em segurança (*"never log into an unproven account"*); a alternativa
escolhida — criar outra conta — é o que multiplica os registos.

**Consequência: as ~200 contas podem não ser ~200 pessoas.**

### Classe 2 — duplicado SEM prefixo, invisível a qualquer contagem óbvia

As duas funções que decidem se um email "já existe" **não concordam**:

| Função | Como procura |
| --- | --- |
| `_find_or_create_saml_user` (regra 2) | `_find_user_by_email_ci` — **case-INsensitive** |
| `_create_saml_user` | `datastore.find_user(email=...)` — **exact** |

E o índice único de `User.email` é **case-sensitive**, logo `Maria@x.pt` e `maria@x.pt`
coexistem. Esta conta **não é contada** por nenhuma consulta filtrada por `saml-`, e **não é
vista pelo `migrate-nics`**.

É por isso que o LEDG-2434 tem de contar por **três eixos** — prefixo, `auth_nic` repetido e
colisões `email__iexact`.

⚠️ **O LEDG-2456 NÃO fechou isto** — a mesma divergência exact/ci existe no `change_email` e
ficou lá registada como achado rejeitado, por pertencer ao LEDG-2435.

---

## ✅ JÁ IMPLEMENTADO — não reconstruir

| Requisito | Onde | Em `main`? |
| --- | --- | --- |
| Detetar conta com endereço sintético | `User.has_placeholder_email` | ✅ |
| Bloquear o acesso até dar um email real | `_handle_saml_user_login` redireciona e **descarta o destino original** | ✅ |
| Cobrir também as contas antigas | o comentário diz *"or older ones from before this check"* | ✅ |
| Ser depois do login, independente da flag | está em `_handle_saml_user_login`, não no wizard | ✅ |
| Expor o estado na API (`pending_registration` em `/me`) | `udata/core/user/api_fields.py` | ✅ |
| Ecrã de conclusão de registo | `/complete-registration` + `CompleteRegistrationClient.tsx` | ❌ **LEDG-2437** |
| Verificar a posse do email indicado | `/auth/change-email` → `send_change_email_confirmation_instructions` | ✅ |
| **Resposta genérica no ecrã de conclusão** (aviso ao dono da caixa) | `change_email` + `mails.address_taken_notice` | 🔧 LEDG-2456, em `develop`+`tst` |
| **Provedor de autenticação gravado** (`extras.auth_provider`) | as duas rotas ACS → criação, login, wizard e link | 🔧 LEDG-2433, em `develop`+`tst` |

**Consequência:** a decisão "o que acontece a quem recusa dar um email" **já está tomada em
código** — é bloqueado, e volta ao mesmo ecrã em cada login.

**O que o #206 NÃO resolveu:** tratou o sintoma e não a causa. E o ecrã de conclusão **só
permite indicar um email novo** — não oferece associar a uma conta tradicional existente, que é
metade do requisito.

---

## 🔑 Ferramenta que já existe

`udata user migrate-nics --dry-run` — presente nas **quatro** branches. Itera as contas com
endereço sintético, tenta reconciliá-las, e **classifica as que não consegue resolver com
motivo** (`no NIC to merge`, `no traditional account found`, `multiple matches`, `target already
linked to a different CMD identity`).

> 🚨 `--dry-run` é opt-in; **o modo destrutivo é o PREDEFINIDO.** Sem a flag, reescreve
> identificadores e **apaga contas** com `dup._delete()`, sem transferir conteúdo.
>
> ⚠️ **Não replicar o critério de correspondência:** encontra o destino por hash e, em fallback,
> **por nome**, sem prova de posse. Aceitável num comando de administrador; **tomada de conta
> entre homónimos** se replicado num fluxo self-service.
>
> ⚠️ **E não vê a classe 2** — só itera contas com o prefixo.
>
> ⚠️ **A verificação de colisões só vê os valores JÁ hasheados.** O `_find_shared_nics()`
> filtra por `is_nic_hashed`, logo o que reporta depende do estado do ambiente:
>
> - **nada hasheado** (o caso da BD local: 0 hasheados, 1070 em claro) → não tem nada para
>   olhar, e o seu zero é **garantido, não medido**;
> - **a meio** → reporta só o subconjunto hasheado, ou seja **subconta**;
> - **tudo hasheado** (DEV e TST: 0 em claro) → aqui **funciona**, e teria reportado os 13/14
>   grupos. ❌ **Correcção a uma afirmação anterior desta doc:** escrevi que a cegueira era
>   estrutural em qualquer ambiente. Não é — é estrutural *enquanto* houver valores em claro.
>   Em DEV e TST o comando teria dito a verdade; **ninguém o correu**.
>
> A ambiguidade, por outro lado, **já existe antes de qualquer hash**: o passo 1b do lookup faz
> `User.objects(extras__auth_nic=user_nic).first()` sobre valores em claro e devolve um
> arbitrário.

### `scripts/audit_institutional_users.py` — o segundo, e ainda NÃO versionado

Só de leitura, recebe `--host`, e classifica o link CMD **nas mesmas quatro categorias** do
comando (`yes (hashed)`, `stale (legacy-encrypted)`, `stale (plain NIC)`,
`stale (unrecognized)`). Já conta contas com prefixo, pertença a organização, `last_login_at`
e domínios institucionais → cobre boa parte das perguntas 1 a 4.

Os hosts dos ambientes estão no seu docstring: **DEV o host de DEV**, **TST o host de TST**.

✅ **Resgatado em 2026-09-09**, sem alterar uma linha, na branch
`chore/ledg-2434-version-the-institutional-audit-script` — estava untracked e um `git clean`
apagava-o. Commitado **como está** de propósito, para que a correcção que se segue seja um diff
revisível em vez de um primeiro import irrevisível.

🚨 **E a correcção é necessária: os dois classificadores NÃO concordam.** O script
reimplementa a classificação do NIC em vez de a importar, e as cópias já divergiram:

| | `udata/core/user/nic.py` (o que a produção usa) | o script |
| --- | --- | --- |
| `HEX_DIGITS` | `"0123456789abcdef"` | igual |
| comparação | `for c in nic_value` | `for c in nic.lower()` ⚠️ |

Um valor em **hex maiúsculo** é portanto classificado de forma diferente pelos dois: uma cifra
legada de 512 hex em maiúsculas é `legacy-encrypted` para o script e `unrecognized` para o
login. **São 1207 contas nesse balde** — o risco está concentrado exactamente onde está o
volume.

Verificado que **no dump local não se manifesta** (nenhum dos 23 valores não reconhecidos é hex
longo). Em DEV, TST e produção é incógnita — e num levantamento cujo propósito é *contar*, um
classificador que discorda da produção produz contagens erradas.

> 💡 **É a mesma classe de bug que originou esta revisão inteira:** duas funções que decidem a
> mesma coisa e não concordam, como o `_find_user_by_email_ci` versus o `find_user` da classe 2.

✅ **CORRIGIDO em 2026-09-09** (`eeb2c4f3`). Os predicados passam a ser importados do `nic.py`
— `is_nic_hashed`, `is_nic_legacy_encrypted`, `is_nic_plain` — logo o levantamento e o
`migrate-nics` põem cada conta no mesmo balde **por construção**, não por dois autores
concordarem. Verificado: hex maiúsculo dá agora `stale (unrecognized)` nos dois, como a
produção.

Custo zero em runtime (os predicados não pedem contexto de app; só o `hash_nic` pede, para o
`SECRET_KEY`), mas o script passa a correr dentro do venv — `uv run python …`, como as linhas
de uso agora dizem. Continua estritamente só de leitura.

Três commits na branch, de propósito: o resgate como estava (`261cb5b6`), a formatação
(`5549b81f`) e o fix (`eeb2c4f3`). Sem essa separação o fix ficava enterrado debaixo de
sessenta linhas de literais reformatados.

✅ **Os dois eixos de colisão acrescentados** (`90dfe30a`) — `auth_nic` repetido (pergunta 7)
e `email` em minúsculas (pergunta 8). Agrupados pelos valores **como estão guardados**, logo
não precisam do `SECRET_KEY` e a resposta vale em qualquer ambiente: duas contas com o mesmo
NIC em claro dão o mesmo digest, logo agrupar os valores em claro encontra-as sem hashear nada.

O relatório **diz o que não vê**, em vez de dar a impressão de completude: um NIC em claro
numa conta e o hash desse mesmo NIC noutra não são reconciliáveis sem a chave, logo o número
do identificador é um **limite inferior**.

#### 🚨 Primeira corrida com os dois eixos — BD local, 2026-09-09

```
contas analisadas                       8505
parecem institucionais                   722   (336 sem CMD, 386 com)
contas com link CMD                     2296
emails sintéticos (saml-*)                 0
contas a partilhar o MESMO identificador  13 grupos   ← o dry-run diz 0
emails a colidir só na capitalização        2 grupos
```

**Treze grupos onde o login CMD é ambíguo hoje, e o `migrate-nics --dry-run` reporta zero.**
É a prova da cegueira, medida em dados reais.

⚠️ **Estes números são da BD local e não de nenhum dos quatro ambientes.** A corrida contra o
**DEV**, a 2026-09-11, dá **9 075 contas**, **931 com aparência institucional** (331 sem CMD,
600 com) e **2 875 com link CMD** — populações diferentes, portanto **o 722 e o 386 não valem
como contagem em lado nenhum**. O que se repete nos dois é o **13**: treze grupos a partilhar
identificador. Coincidência ou ascendência comum do dump, não se afirma qual.

**E o padrão é inequívoco: a mesma pessoa, dois emails, minutos de intervalo.**

| Contas | Intervalo |
| --- | --- |
| `cristiana.castro@cm-moita.pt` · `cristianaarqui@hotmail.com` | **14 s** |
| `metralha2725@gmail.com` · `otaviochunguinha123@gmail.com` | **25 s** |
| `sara.a.m.arana@gmail.com` · `sara.xana2014@gmail.com` | **31 s** |
| `pablolira@hotmail.com` · `Pablolira@hotmail.com` | **49 s** |
| `catarina.leitao.campos@gmail.com` · `cata.leitao.campos@gmail.com` | **8 min** |
| `filipe.silva@mogadouro.pt` · `filipe@ruasilva.pt` | **1 h 17** |

**É a classe 1 sem prefixo nenhum** — o efeito de "uma conta nova em cada login" previsto pela
pergunta 7, a acontecer em contas com endereço real. Nenhuma contagem por `saml-` as apanha, e
o `migrate-nics` também não porque só itera o prefixo.

#### 🚨 DEV e TST medidos — 2026-09-09

| | **DEV** | **TST** | local |
| --- | --- | --- | --- |
| contas analisadas | 8854 | 8698 | 8505 |
| `yes (hashed)` | **1399** | **1236** | **0** |
| `stale (plain NIC)` | **0** | **0** | 1070 |
| `stale (legacy-encrypted)` | **1201** | **1201** | 1203 |
| `stale (unrecognized)` | **39** | 30 | 23 |
| sem link CMD | 5922 | 5937 | 5916 |
| emails `saml-*` | **4** | **3** | 0 |
| grupos com o mesmo identificador | **13** | **14** | 13 |
| colisões de capitalização | **2** | **2** | 2 |

#### 🎯 DADOS DE PRODUÇÃO — backup de 2026-08-24 restaurado em DEV, medido a 2026-09-09

A VM de DEV (o host de DEV) recebeu um backup de PRD de **2026-08-24**. É a primeira medição
com a população real. **PPR (o host de Mongo de PPR) e PRD (o host de Mongo de PRD) não são alcançáveis** desta
máquina — testado, timeout nos dois.

##### Pergunta 1 — contas com endereço sintético: **120**

Nenhuma apagada. Criadas entre **2026-06-09 e 2026-08-24**, a ritmo estável: 44 em junho,
35 em julho, 41 em agosto — **~40/mês**.

⚠️ **Discrepância a resolver:** extrapolando ~1,6/dia, a 2026-09-09 seriam **~145**. A
verificação no backoffice de produção diz **~200**. Ou a estimativa visual é grosseira, ou o
ritmo acelerou depois de 24/08. **Não inventar a explicação** — vê-se contando no backoffice
por mês.

##### Pergunta 7 — ❌ a hipótese central do ticket NÃO se confirma

**120 contas → 120 identificadores distintos. Uma conta por pessoa.**

⚠️ **Medido duas vezes, porque a primeira consulta estava mal.** Agrupei só as 120 sintéticas
entre si — o que **não** apanharia um par *(conta real + conta sintética)* com o mesmo NIC, que
é exactamente a forma que a multiplicação teria. Reagrupado sobre **todas** as contas: **13
grupos, 26 contas, e nenhum inclui uma conta sintética.** A conclusão aguenta-se; a primeira
consulta é que não a suportava.

A pergunta 7 previa que "as ~200 contas não são ~200 pessoas" — que a mesma identidade
recebia uma conta nova em **cada** login, e que o número real de pessoas seria muito menor.
**Nos dados não há um único caso**: nenhum identificador aparece duas vezes.

Isso **simplifica** a reconciliação — é 1:1, não muitos-para-um — e **muda a comunicação**:
são ~200 pessoas, não ~200 contas de umas dezenas de pessoas.

⚠️ E remove a justificação do desenho que assumia multiplicação. O LEDG-2435 não precisa de
reconciliar N contas de uma pessoa.

**Contas sem identificador nenhum: 0.** A população do [LEDG-2436](https://ticapp.atlassian.net/browse/LEDG-2436)
— identidade sem identificador — **está vazia nesta amostra**. O ticket pode continuar a
justificar-se pelo eIDAS, mas não por estas contas.

##### 🔑 Pergunta 9 — o que a flag FAZ em produção, lido no código de `main`

`main` está **154 commits** atrás de `develop` no backend, logo o comportamento tinha de ser
lido ali. Das 9 ocorrências de `MIGRATION_MODE_ENABLED`, **só 2 são código** (uma linha de log
e o `_migration_enabled()`); as outras 7 são testes. O que decide são os **8 chamadores**, e o
central é este:

```python
user, status = _find_or_create_saml_user(user_email, user_nic, first_name, last_name)

if status == "migration_candidate":
    if _migration_enabled():
        return _handle_migration_redirect(...)     # → assistente em /migrate-account
    # Migration wizard disabled: never log into an unproven account —
    # fall back to creating a new one (scenario 4).
    user = _create_saml_user(...)                  # → conta NOVA
    status = "new"
```

🚨 **E em `main` uma identidade JÁ LIGADA devolve `migration_candidate`**, não `existing_saml`
como em `develop`:

```python
if user_nic:
    user = User.objects(extras__auth_nic=_hash_nic(user_nic)).first()
    if user:
        return user, "migration_candidate"        # develop: "existing_saml"
```

**Se a flag estiver desligada, isto implica uma conta nova em cada login de quem já está
ligado** — a multiplicação que a pergunta 7 previa. **Mas os dados dizem que ela não acontece**
(ver abaixo). As duas coisas só se reconciliam de duas maneiras: **a flag está ligada em
produção**, ou ninguém entrou duas vezes — e a segunda não é verificável, porque os campos de
sessão não são escritos (pergunta 3).

> ✅ **É isto que torna a pergunta 9 decisiva, e não uma nota de rodapé.** O valor da flag
> **discrimina entre duas histórias causais diferentes** para as mesmas 120 contas, e a
> correcção é diferente em cada uma. Não é "registar para completude" — é o que diz qual é o
> problema.

#### ✅ RESPONDIDA — a flag está LIGADA em produção (2026-09-09)

O `.env` de PRD (datado 2026-05-19) **não contém `MIGRATION_MODE_ENABLED`**. O valor efectivo
vem portanto do default, e o default que ganha é o do `udata.cfg`:

```python
# udata.cfg:377
MIGRATION_MODE_ENABLED = _env_bool("MIGRATION_MODE_ENABLED", True)

# udata.cfg:25
def _env_bool(var, default=False):
    return os.getenv(var, str(default)).lower() in ("true", "1", "yes")
```

Ausente → `os.getenv` devolve `"True"` → **`True`**. O `False` do `_migration_enabled()` é um
**fallback morto**: só se aplicaria se o `udata.cfg` não tivesse corrido, e corre sempre.

> ⚠️ **Os "três defaults contraditórios" são menos perigosos do que parecia, e mais
> enganadores.** Não estão em conflito — há uma ordem de precedência clara e o `udata.cfg`
> ganha. O problema é que **o `False` escrito no código sugere o contrário a quem lê**, e foi
> isso que me levou a assumir que produção estava desligada.

❌ **RETRACTADO — "ligar a flag trava a hemorragia".** Propus isso como a mitigação mais barata
do refinamento. **Não existe: já está ligada.** Não há nada para ligar.

##### Então de onde vêm as 120 contas sintéticas?

Com a flag ligada, um `migration_candidate` vai para o assistente, **não** cria conta nova. Logo
as 120 vêm do caminho em que **não há candidato** (`status == "new"`) e o email da asserção
**já está tomado** — o `_create_saml_user` fabrica então o endereço.

**Quem não pode ser candidato?** Uma conta já ligada a **outra** identidade CMD, excluída pelo
`_has_linked_nic`.

**Hipótese, não verificada:** são **caixas de correio partilhadas**. Um `geral@`, `sig@` ou
`informatica@cm-x.pt` já ligado à identidade do colega nº 1; o colega nº 2 entra com o seu CMD,
a asserção traz o mesmo endereço partilhado, a conta não pode ser candidata → conta nova →
endereço tomado → **endereço fabricado**.

**O que sustenta a hipótese:** este mesmo levantamento contou **386 contas com aparência
institucional E link CMD** — exactamente a população que produz este efeito. E explica porque
**não há multiplicação**: cada pessoa fica com o seu próprio identificador na sua própria conta
sintética.

**Como confirmar:** cruzar as datas de criação das 120 com as contas institucionais ligadas, e
ver se o domínio das 120 (que não é visível no endereço fabricado, mas está no `first_name`/
`last_name` e no audit log do LEDG-2366) corresponde a mailboxes partilhadas.

⚠️ **Marcada como hipótese.** Este documento já retractou quatro inferências hoje, todas por
dados novos derrubarem raciocínio a partir de código. Esta só passa a conclusão com a consulta
acima.

**Verificações feitas antes de considerar mexer na flag em produção:**

| Verificação | Resultado |
| --- | --- |
| `migrate-account` (o assistente) existe em `main`? | ✅ **sim** |
| `complete-registration` (o que a conta sintética precisa) existe em `main`? | ❌ **não** — é o 404 do LEDG-2437 |
| O frontend em `main` esconde o formulário por alguma flag? | ✅ **não** — zero referências; o bug do LEDG-2432 nunca chegou a produção |
| O backend em `main` devolve `migration_required` no login tradicional? | ✅ **não** — logo a flag **não pode** partir o login por email |

⚠️ **Não mexer na flag até se saber o seu valor actual**, precisamente porque ela discrimina
entre as duas histórias. Ligá-la sem saber pode estar a "corrigir" algo que já está ligado.

##### ✅ Pergunta 5 — onde o email é tratado como identificador (levantamento de código)

**Não há uma convenção. Há quatro**, e duas estão erradas.

O armazenamento: `email = field(StringField(max_length=255, required=True, unique=True))` —
índice único **sensível à capitalização**, e **sem normalização na escrita**. É por isso que
`Maria@x.pt` e `maria@x.pt` coexistem: **401 de 9075 contas (4,4%) têm ao menos uma maiúscula
no endereço.** Esse número é o raio de acção de tudo o que se segue.

| Convenção | Onde | Veredicto |
| --- | --- | --- |
| Exacta no input cru | `find_user(email=…)`, `objects(email=…)` — `auth/views.py`, `proconnect.py:91`, `saml_govpt.py:725`, `user/commands.py`, `api/oauth2.py:259`, `api/commands.py:84` | consistente com o índice |
| **Insensível à capitalização** | `email__iexact` — **só** no `saml_govpt.py:888` (`_find_user_by_email_ci`) | correcta, mas isolada |
| **Exacta sobre input em minúsculas** | `organization/api.py:651` | 🚨 **quebrada** |
| Normaliza e depois compara exacto | `auth/views.py:64` (`strip().lower()`) | correcta para o que escreve |

###### 🚨 Defeito 1 — convites de organização não encontram 4,4% das contas

`MembershipInviteForm`, em `organization/api.py:651`:

```python
user = User.objects(email=email.lower()).first()
if user:
    email = None  # User found, use user instead of email
```

Passa o input a minúsculas e compara **exacto** com o valor guardado. Uma conta guardada como
`Maria@x.pt` **nunca é encontrada** — o convite cai no ramo do endereço e é criado **por email
em vez de ligado à conta existente**. A pessoa recebe um convite que não a reconhece.

###### 🚨 Defeito 2 — a comparação certa está debaixo de uma consulta que a impede de correr

`match_email_invitations`, em `user/models.py:410` — corre quando alguém se registra, para lhe
atribuir convites pendentes:

```python
for org in Organization.objects(
    requests__kind="invitation", requests__email=user.email.lower(), requests__status="pending"
):
    for req in org.requests:
        if (... and req.email.lower() == user.email.lower() ...):   # ← correcto
```

A comparação em Python (linha 425) é **insensível à capitalização nos dois lados** — o autor
sabia que a capitalização importava. Mas ela só corre sobre as organizações que **a consulta já
devolveu**, e a consulta (linha 417) compara `requests.email` **exacto** contra
`user.email.lower()`.

**Um convite guardado com maiúsculas nunca é encontrado:** a organização não entra no ciclo, e a
comparação correcta nunca tem oportunidade. A pessoa registra-se e **não fica membro**, em
silêncio.

> 💡 **É o mesmo padrão do resto desta revisão, uma terceira vez:** duas funções a decidir a
> mesma coisa sem concordarem — como o `_find_user_by_email_ci` contra o `find_user`, e como os
> predicados copiados do `nic.py` no script de auditoria. **Aqui as duas estão no mesmo ficheiro,
> a oito linhas de distância.**

###### O que isto dá aos pontos seguintes

- **LEDG-2435** — a lista de sítios a alinhar. A correcção não é "usar `iexact` em todo o
  sítio": é decidir se o endereço é **normalizado na escrita** (e então migrar os 401) ou
  **comparado sem capitalização na leitura** (e então corrigir os quatro sítios). Misturar as
  duas é o que produziu isto.
- **LEDG-2431** — os dois defeitos acima são caminhos pelos quais uma conta associada pode
  perder pertenças a organizações. Têm de estar corrigidos **antes**, ou a associação herda-os.
- ⚠️ **Nenhum dos dois é específico do CMD/eIDAS.** Afectam registo por email igualmente, e
  provavelmente merecem ticket próprio em vez de irem dentro do 2435.

##### Pergunta 2 — a que mais pesa: **6 de 120 têm conteúdo ou pertença**

| | |
| --- | --- |
| contas com algo | **6 de 120** (5%) |
| datasets no total | **2** |
| reuses | **0** |
| membros de organização | 5 |
| **admin de organização** | **4** |

✅ **Isto decide o [LEDG-2431](https://ticapp.atlassian.net/browse/LEDG-2431): recusar quando
há conteúdo.** Para 114 das 120 não há nada a transferir, e transferir conteúdo é onde um erro
custa dados de utilizadores. O ticket já antecipava esta bifurcação; os dados escolhem o ramo
simples.

🚨 **Mas os casos não são "uns poucos à mão" — são um risco de integridade.** Os 4 admins são
**o ÚNICO administrador** das suas organizações:

| Conta | Organização | datasets | |
| --- | --- | --- | --- |
| `saml-dde8d633@…` | **AGIT (Agência para a Gestão do Sistema…)** | **5** | 🚨 único admin |
| `saml-9a4b1075@…` | **Instituto Nacional de Administração, I.P.** | 0 | 🚨 único admin |
| `saml-64f971fb@…` | GREEN METRICS LDA | 0 | 🚨 único admin |
| `saml-c0437c35@…` | EazyAL | 0 | 🚨 único admin |

Organismos públicos reais administrados por uma conta **cujo endereço não existe**, que não
recebe correio, e que — pelo [LEDG-2437](https://ticapp.atlassian.net/browse/LEDG-2437) — leva
**404 em produção a cada login**. Recusar ou apagar qualquer uma delas **deixa a organização
órfã**, e a da AGIT leva **5 datasets** consigo.

❌ **Correcção a um número anterior: eram 6 organizações reportadas, são 4.** A contagem de
pertença do script não filtrava organizações apagadas. Corrigido (`1a662faa`), e a correcção
está no próprio script para não voltar a acontecer.

❌ **E o quarto ticket (organizações AGIT duplicadas) NÃO se cria.** A suspeita vinha de três
registos com nomes parecidos. A consulta mostra que os **três foram criados no mesmo dia
(2026-07-18)**, que **dois já estão apagados** com 0 datasets, e que só o terceiro está vivo:
foi alguém a criar a organização três vezes até acertar no nome, e a limpeza já foi feita.
**Não havia problema — havia um palpite meu**, que é a razão pela qual não se cria ticket antes
da consulta.

##### Pergunta 3 — ⚠️ NÃO É RESPONDÍVEL, e a razão é um defeito

As 120 têm `last_login_at`, `current_login_at`, `login_count` e `last_login_ip` **todos
vazios**. A leitura fácil — "nenhuma voltou a entrar" — **está errada** e não a assumi.

A causa: o plugin SAML importava o `login_user` do **`flask_login`**
([saml_govpt.py:31](backend/udata/auth/saml/saml_plugin/saml_govpt.py#L31)), que **não escreve**
nenhum destes campos — quem os escreve é o `login_user` do `flask_security`.
✅ **Corrigido pelo LEDG-2462**, em `develop` e `tst`, e por escrita atómica dos cinco campos em
vez da troca do import (ver o ponto 6). ⚠️ **Mas isto não muda os números abaixo**: eles são de
um backup de 2026-08-24, e a correcção **não é retroactiva**. E os dados confirmam a
consequência, por data de criação das contas **com** `auth_nic`:

| criadas | contas | com `last_login_at` |
| --- | --- | --- |
| antes de 2026-01 | 2456 | 2034 — **83%** |
| 2026-01 a 05 | 190 | 108 — 57% |
| **2026-06 a 08** | 232 | **7 — 3%** |

**O campo deixou de ser mantido**, com a queda a completar-se exactamente quando as contas
sintéticas começam a aparecer (2026-06-09). Os 83% históricos vêm de contas antigas — não de
o fluxo SAML os escrever.

**Duas consequências:**

1. **A pergunta 3 do LEDG-2434 não tem resposta possível pelos dados**, e é preciso outra
   fonte (logs de acesso) ou corrigir o defeito e esperar.
2. **É um defeito por si só**, e não estava em nenhum dos pontos quando isto foi escrito:
   qualquer lógica que dependa de inactividade — limpezas, notificações, relatórios de
   utilização — trata **todos** os utilizadores de CMD/eIDAS recentes como dormentes.
   ✅ **Já corrigido pelo LEDG-2462**, o ponto 6, em `develop` e `tst`. ⚠️ **Mas não
   retroactivamente** — ver esse ponto.

---

#### ⚠️ Antes de ler os números: nenhum destes ambientes é produção

Idade dos dados, medida a 2026-09-09:

| | conta mais recente | último login | total (com apagadas) |
| --- | --- | --- | --- |
| **DEV** | 2026-09-08 | **2026-09-09** | 9202 |
| **TST** | 2026-09-08 | 2026-09-08 | 9047 |
| local | 2026-05-22 | 2026-08-04 | 8846 |

**DEV e TST estão activos** — contas criadas ontem, logins hoje. **A desactualizada é a
local**, 3,5 meses atrás. Mas o que importa é outro eixo: **DEV e TST não são cópias de
produção**, são ambientes com a sua própria população de teste. Logo qualquer contagem
absoluta lida aqui descreve *esses* ambientes, **não produção**.

**Duas conclusões, e duas retractações:**

1. ❌ **RETRACTADO — "a estimativa de ~200 contas sintéticas está errada por 50×".** Escrevi
   isso com base nos 4 de DEV e 3 de TST. **Não se sustenta:** esses ambientes não têm a
   população de produção, logo não dizem nada sobre os ~200.

   ✅ **E a estimativa foi CONFIRMADA em produção**, por verificação no backoffice
   (2026-09-09): **~200 contas com `saml-…@autenticacao.gov.pt` em PRD**. A pergunta 1 tem
   resposta. ⚠️ É uma **contagem de listagem, não uma consulta** — dá o número de contas, não
   quantas pessoas distintas são (pergunta 7) nem quantas têm conteúdo (pergunta 2).

   **PPR (o host de Mongo de PPR) e PRD (o host de Mongo de PRD) não são alcançáveis** desta máquina (timeout de
   selecção de servidor nos dois), logo tudo o que dependa de consulta a produção **é trabalho
   humano**, não automatizável a partir daqui.

   🔍 **A discrepância é o achado mais accionável de todo o levantamento:** **~200 em PRD
   contra 4 em DEV e 3 em TST**, sendo que DEV e TST estão activos (logins hoje). Se os
   endereços sintéticos fossem uma consequência inevitável do código, DEV e TST — que correm o
   mesmo código — teriam a mesma proporção. **Não têm.**

   **Hipótese, explicitamente não verificada:** a diferença é o `MIGRATION_MODE_ENABLED`. Com
   a flag a `True` o assistente corre e a conta sintética **não é criada**; com `False` o
   candidato é descartado e o `_create_saml_user` fabrica o endereço. Se PRD tiver `False` e
   DEV/TST `True`, isso explica os três números — e implica que **mudar a flag em produção
   trava a hemorragia**, sem esperar por nenhum dos nove pontos.

   **Como confirmar, por ordem de custo:**
   - ler o `MIGRATION_MODE_ENABLED` no `.env` de PRD, PPR, DEV e TST → **é a pergunta 9**, e
     passa a ser a pergunta mais importante do ticket, não uma nota de rodapé;
   - ver no backoffice as **datas de criação** das ~200: se se concentram a partir de uma
     data, essa data é quando a flag mudou ou o código entrou.

   ⚠️ **Não tratar a hipótese como conclusão.** Este documento já retractou duas conclusões
   tiradas de dados de ambientes que não são produção; esta fica marcada como hipótese até
   alguém ler os quatro `.env`.
2. ❌ **RETRACTADO — "os `unrecognized` estão a acumular (23 → 30 → 39)".** Li a ordenação
   entre três ambientes como uma série temporal. **Não é:** são três populações distintas e
   sem relação de idade entre si. Que DEV tenha 39 e a local 23 não é crescimento — é outra
   população. **Se algo continua a escrever nomes no slot do NIC, isto não o prova.**
3. ⚠️ **REENQUADRADO — as colisões de identificador.** Em DEV e TST os valores estão todos
   hasheados (`plain NIC = 0`), logo os 13/14 grupos partilham o **mesmo hash nesses
   ambientes agora**: para ~26–28 contas o login CMD resolve por `.first()` e devolve uma
   arbitrária. Isso é real e verificado **ali**. Para produção é um **limite inferior
   plausível** — as contas não costumam ser apagadas e o mecanismo que as cria é o mesmo —
   mas **não é uma medição de produção**. E a ambiguidade não depende de estarem hasheadas: o
   passo 1b faz `.first()` sobre valores em claro igualmente.
4. ✅ **MANTÉM-SE — o `migrate-nics` não toca no balde legado.** É a única conclusão que não
   depende da população, porque é sobre o **comportamento do comando**: DEV e TST têm zero em
   claro (logo algo os hasheou) e o `legacy-encrypted` ficou em **1201** nos dois, contra 1203
   na local que nunca foi migrada. Correu, e os 1201 continuam lá.

**E a classe 2, num exemplar de manual:**

```
sandra.rodrigues.1990@gmail.com   sem link CMD              criada 2022-04-18
Sandra.rodrigues.1990@gmail.com   stale (legacy-encrypted)  criada 2024-08-07
```

Conta tradicional primeiro; dois anos depois um login CMD com o endereço capitalizado de outra
forma. O resolvedor encontrou-a (`ci`), **descartou-a**, e o `_create_saml_user` — que compara
exacto — não a encontrou e criou a segunda. Exactamente o mecanismo descrito na classe 2.

---

## Estado atual do código (verificado em `develop`)

**Onde os endereços são fabricados:** `_create_saml_user()` — **um único sítio de escrita**, com
dois casos: (a) o IdP não devolve email, ou (b) o email devolvido **já pertence a outra conta**.

**Formato:** `saml-<8 hex>@autenticacao.gov.pt`.
⚠️ **O domínio indicado no pedido original não corresponde ao que está em uso** — uma consulta
com o valor errado devolve zero.

### Atributos pedidos ao IdP, por provedor

| Provedor | Atributos pedidos | Email? |
| --- | --- | --- |
| **CMD** | `CorreioElectronico`, `NIC`, `NomeProprio`, `NomeApelido` — os quatro `is_required="True"` | ✅ **sim** |
| **eIDAS** | `PersonIdentifier`, `CurrentFamilyName`, `CurrentGivenName`, `DateOfBirth` | ❌ **não** |

**O eIDAS não pede email porque o email não existe no Minimum Data Set do eIDAS** — não é
omissão nossa, e acrescentá-lo não garante que os IdPs europeus o devolvam. Logo **toda a conta
eIDAS pura passa pelo ecrã de conclusão de registo**, e sempre passará.

### 🌍 CMD nacional e CMD estrangeiro NÃO são distinguíveis hoje

Três factos verificados, e é a soma deles que fecha a porta:

1. **Uma só rota ACS para os dois.** `/saml/sso`, com o mesmo `kind="cmd"`. Não existe terceira.
2. **O frontend pergunta e descarta.** O `CmdTab.tsx` tem radios "nacional"/"estrangeiro", mas o
   valor só habilita o botão — nunca sai do browser. É o **LEDG-2457**.
3. **Os atributos de documento não existem no código.** Só há quatro constantes MDC;
   `DocType`/`DocNationality`/`DocNumber` não aparecem em sítio nenhum. É o **LEDG-2438**.

⚠️ **Inferir "estrangeiro" pela ausência de NIC está errado duas vezes:** é dedução dos
atributos e não da rota, e um CMD sem NIC é **também** o que um IdP mal configurado produz
(LEDG-2436) — gravaria "estrangeiro" no que pode ser um login avariado.

**O que fica na BD, por isso:** o LEDG-2433 grava `auth_provider` com **`cmd` ou `eidas`, e mais
nada**. Um estrangeiro com CMD fica `cmd`. As três categorias precisam do LEDG-2457 (declarado)
ou do LEDG-2438 (provado).

### Outros factos do tronco comum

- **Os dois handlers ACS são estruturalmente idênticos** a partir do
  `_find_or_create_saml_user`. **Qualquer bug nesse tronco afeta CMD e eIDAS por igual**, e uma
  correção num handler só deixa o outro intacto.
- **Uma identidade sem identificador não tem saída no wizard:** os três ramos recusam-na com
  `nic_required` 400, deliberadamente. É o LEDG-2436.
- **Fluxo de migração:** ligar conta existente exige **prova de posse por link de email**; as
  respostas são **genéricas**. A prova por palavra-passe **já não completa a associação** —
  identifica a conta e envia o link; o `confirm-link` é o **único** consumidor, e o
  `_link_identity_and_login` o único ponto que grava.
  ⚠️ **Esse clique chega sem sessão** — tudo o que precisa viaja no registo do link.
- **Uma guarda em falta:** de todas as rotas do wizard, **a `/saml/migration/skip` é a única sem
  a verificação da flag**.
- ✅ **A auditoria SAML não emitia em produção — corrigido a 2026-09-14** pelo LEDG-2371, PR
  #285, em `develop`. Eram **dois** defeitos independentes, e corrigir um só não fazia aparecer
  linha nenhuma: o logger estava fora da árvore `udata.*` (propagava para um root sem handler)
  **e** não tinha nível próprio (herdava o `WARNING` de produção, com todas as chamadas a
  `.info()`). ⚠️ **Tudo o que está acima aconteceu desde Maio sem deixar rasto** — o que se
  corrigiu foi a cegueira daqui para a frente, não o passado.
  🚩 **E dois achados que só apareceram ao corrigir:** um POST às rotas ACS sem `SAMLResponse`
  devolvia 400 **sem passar pela auditoria**, logo nem ficava registado que tinha acontecido; e
  fazer o logger emitir **sem o excluir do Sentry** teria empurrado o `ip` e o `ua` de cada
  login para lá — a integração vê records a INFO mesmo sem handler, e o projecto corre com o
  default de **não** enviar esses dados. Corrigir o bug abria o buraco.
- **🌐 Os e-mails de autenticação saíam em inglês** — medido com `pybabel`: 56 msgids em
  `udata/auth/`, 37 traduzidos, 19 não. O e-mail de associação chegava com **assunto e corpo em
  inglês**, porque as strings estavam em `_()` sem entrada no catálogo pt — e **isso falha em
  silêncio**: o `gettext` devolve o próprio msgid. O LEDG-2456 traduziu 12; 7 ficaram por terem
  o msgid já em português.

---

## Decisões tomadas

**1. O `auth_nic` fica como está. NÃO se acrescenta o prefixo.** O valor é um **hash de sentido
único** e é a chave por onde o login encontra os utilizadores; o NIC original não é recuperável,
logo os valores existentes não podem ser recalculados. Introduzi-lo obrigaria a dois formatos
indefinidamente, ou a **trancar todos os utilizadores registados**. Um campo novo desambigua sem
tocar na chave.

> ✅ **Feito no LEDG-2433**, com a justificação no docstring do `udata/core/user/nic.py` — sem
> isso, quem ler o pedido original daqui a um ano conclui que o prefixo ficou esquecido e
> acrescenta-o.

**2. A migração obrigatória fica desligada por agora**, mas **é provisório** (LEDG-1277).
⚠️ "Desligada" é verdade apenas onde o `.env` do ambiente a desliga — **por omissão do código
está ligada**.

**3. "Deixar de gerar e enviar e-mails SAML" refere-se apenas a *gerar endereços*.** O envio
mantém-se e é obrigatório: o endereço indicado **tem de ser verificado**, senão qualquer pessoa
indicaria o email de outra e ficaria com acesso à conta dela.

**4. O campo do método de autenticação fica vazio para os utilizadores existentes.** Não é
inferível retroativamente, e adivinhar gravaria uma suposição como facto. **Ausente significa
ausente.**

**5. Quem se autentica com endereço sintético tem de dar um email pessoal ou associar a uma
conta tradicional existente.** É o **mesmo ecrã**, com outro ponto de entrada.

**6. No ecrã de conclusão, o utilizador escolhe o *endereço*, não o *fluxo*.** Um só campo de
email. Apresentar "associar" e "criar nova" como duas opções obrigaria a revelar se o endereço
existe — o oráculo de enumeração que o LEDG-2361 fechou. **O endereço do CMD pode e deve ser
oferecido pré-preenchido**; no eIDAS não haverá nenhum.

**7. O tipo de cidadão é registado como *declarado*, separado do que é *provado*.** Três graus de
confiança, três chaves, nunca misturados:

| Chave | Fonte | Confiança | Ticket |
| --- | --- | --- | --- |
| `auth_provider` | a rota ACS | **provado** | LEDG-2433 — em `develop` e `tst` |
| `auth_citizen_declared` | o radio que a pessoa clica | **declarado** | LEDG-2457 — em `develop` e `tst` |
| `auth_doc_type` / `auth_doc_nationality` | a asserção do IdP | **provado** | LEDG-2438 |

O declarado **nunca gateia nada**, e quando o provado existir **o provado ganha**. O desacordo
entre os dois passa a ser o sinal de IdP mal configurado que hoje falta ao LEDG-2436.

---

**10. Decidido a 2026-09-10 — três decisões de produto, e o que cada uma mexeu.**

* **Só se entra no portal por CMD e eIDAS.** O login por email e palavra-passe é descontinuado — o
  **18** faz o levantamento e o gate, o **19** activa. ⚠️ **Facultativo primeiro**, com mensagem
  informativa, que é o que o LEDG-1277 já especificava desde o início.
* **Uma pessoa, uma conta.** O **13** pára o crescimento; o **14** funde o que existe e põe o índice
  que o torna impossível. ⚠️ **O 14 é novo porque ninguém tinha o passado** — o 13 e o 9 tratam do
  futuro e da recusa, e as 26 contas dos 13 grupos ficavam sem dono.
* **As contas institucionais deixam de existir.** Publicar passa a ser sempre por conta pessoal, em
  nome próprio ou de uma organização de que a pessoa é membro — o **12**. ✅ **A capacidade já
  existe**; o que falta é migrar quem está no modelo antigo.

⇒ **Duas coisas mudaram de natureza com isto.** O **12** pode ser a **causa** das contas sintéticas
que o **13** trata como efeito — se a hipótese das caixas partilhadas se confirmar, a decisão de
produto elimina a raiz. E o **10** deixou de ser detalhe do 11 para ser a guarda de código que o torna
seguro: o 11 arruma 4 casos, o 10 impede que voltem.

### Decisão 12 — o levantamento em produção espera por `tst` *(2026-09-14)*

**Não se corre o `audit_institutional_users.py` em produção enquanto tudo não estiver fechado
até `tst`.** A base de dados de DEV está actualizada, e é onde os testes se fazem.

**Porquê:** correr em produção agora produziria números sobre um código que ainda vai mudar —
e obrigaria a repetir a medição no fim. Medir uma vez, no estado final, é mais barato e mais
honesto do que medir cedo e citar valores que entretanto deixaram de valer.

**O que isto custa, e fica escrito para ser uma escolha e não um esquecimento:**

- **Três critérios ficam abertos mais tempo** — o 6 do LEDG-2466 (contas sem `confirmed_at`), o
  ponto 4 do LEDG-2468 (organizações órfãs) e o requisito 1 do LEDG-2469 (o que cada duplicado
  detém). Nenhum deles bloqueia código; bloqueiam o **fecho** dos tickets.
- ⏳ **O ponto 14 perde margem.** A fusão dos duplicados tem de correr **antes da promoção
  final**, e agora a medição que a informa também. Os dois passam a caber na mesma janela, no
  fim — e essa janela é a única em que ~26 contas do ponto 9 e os donos de placeholder da
  alínea (c) do 13 deixam de estar trancados.
- ⚠️ **Os números de DEV continuam a não ser os de produção.** O que muda é *quando* se mede,
  não o que os valores de DEV provam — que é que a ferramenta funciona.

## 🚨 O percurso do PRIMEIRO login, traçado de raiz a 2026-09-14

Nunca esteve escrito como percurso. Andou repartido por cinco pontos, e por isso ninguém via
que **falha inteiro** — foi preciso segui-lo de ponta a ponta para responder à pergunta *"o
cidadão que entra pela primeira vez tem de conseguir completar o processo, certo?"*. Tem.

**Quem recebe endereço `saml-*` e é obrigado a passar pelo ecrã de conclusão:**

- **eIDAS: SEMPRE.** Não existe atributo de email no Minimum Data Set do eIDAS. **Toda** a conta
  eIDAS passa por lá, e sempre passará — não é caso de fronteira, é a população inteira.
- **CMD, nacional ou estrangeiro:** quando o IdP não devolve email, ou quando o email devolvido
  **já pertence a outra conta**.

O backend, depois de autenticar, faz `redirect(f"{frontend_url}/complete-registration")` e
**descarta o destino original de propósito** — completar o registo é pré-condição dura.

**Onde essa página existe, verificado por branch no frontend:**

| Branch | `complete-registration` |
| --- | --- |
| `develop` | ✅ |
| `tst` | ✅ |
| `ppr` | ✅ |
| **`main`** | ❌ **não existe** |

⇒ **Em produção, todo o primeiro login por eIDAS termina num 404.** E todo o login CMD cujo
email já esteja tomado, também. Em cada tentativa.

### Duas falhas distintas, e só uma é o 404

| Onde falha | Quem | O que resolve |
| --- | --- | --- |
| **Só em produção** | todos os que precisam do ecrã | **LEDG-2437** — a página chegar a `main` |
| **Em todo o lado** | quem tem o email real numa conta sua já existente | **LEDG-2431** (ponto 15) |

A segunda é a menos visível e não se resolve com promoção nenhuma: o ecrã **só permite indicar
um email novo**. Quem escreve o seu endereço real, e ele pertence à sua conta antiga, recebe a
resposta genérica do LEDG-2456 — **sem mail, sem explicação** — e fica preso. É o mesmo beco que
a alínea (c) do 13 agravou, e é literalmente metade do requisito que o PR #206 não resolveu.

### A cadeia, e onde ela encalha

O **15** devia estar mais acima por isto. A tabela põe-no a depender do **11**, e o **11** depende
do **LEDG-2437** — que é uma promoção, retida pela decisão do topo.

⇒ **Enquanto o 2437 não subir, o primeiro login por eIDAS não completa em produção, e nem o 11
nem o 15 fecham.** Fica escrito como facto, não como pedido de excepção: a decisão de promover
em bloco é do topo deste documento e mantém-se.

⚠️ **O 14 (LEDG-2469) NÃO está neste percurso.** É limpeza dos duplicados que já existem; não
toca no primeiro login. Vale separá-los para não se tratar um pelo outro.

## Decomposição, pela ordem de implementação

> 🔄 **Reordenado a 2026-09-10, com as três decisões de produto da decisão 10.** Entraram seis
> tickets e a tabela passou de catorze pontos a vinte. **O LEDG-2472 entrou por último**, da ideia
> de consolidação self-service: fica **antes** do 19, porque a janela para a pessoa juntar as suas
> contas sozinha fecha quando o login por palavra-passe deixar de existir. **Duas capacidades que as decisões
> pressupunham já existiam** — publicar em nome de uma organização e transferir conteúdo entre conta e
> organização — logo o ponto 11 é migração de dados, não construção. E a **recuperação de palavra-passe**
> (LEDG-2467) entrou como linha sem número: não é CMD/eIDAS. Ficou feita a 2026-09-10, e o que
> nela era pré-requisito do 19 passou para o LEDG-2474.
>
> 🔄 **Reordenado a 2026-09-09, com os dados de produção.** A ordem anterior assumia que o
> problema eram as ~200 contas sintéticas e que essas contas eram poucas pessoas com muitas
> contas cada. **Os dados dizem o contrário** (120 contas = 120 pessoas, e só 6 com conteúdo),
> o que simplifica o 2435, esvazia a justificação do 2436 por esta via, e faz aparecer quatro
> problemas que não estavam em ponto nenhum.

> 🔄 **Reordenado a 2026-09-11 — o LEDG-2464 sobe do 12 para o 9.** Não depende de nada (a própria
> tabela já o dizia), é o **único ponto de código sem dependências** que restava, e os três que
> estavam à frente dele param todos fora do código: o antigo 9 tem três dos cinco pontos em decisão
> da AMA, e o 10 e o 11 são operação humana. 🚨 **E a severidade justifica-o por si:** um identificador
> duplicado resolve por `.first()` e devolve uma conta **arbitrária** — com os 13 grupos duplicados
> medidos em produção, é entrar na conta de outra pessoa por acaso de ordenação.
>
> ⚠️ **É a quinta vez que estes números mudam**, e é exactamente por isso que a regra transversal diz
> **referir dependências por CHAVE, nunca por número**. As células de dependência desta tabela ainda
> usam números e são o que dá trabalho a cada reordenação.

> ✅ **Revisto a 2026-09-11 sem reordenar.** Os pontos 1 a 10 estão feitos ou em curso pela ordem
> da tabela. **O 11 e o 12 não são código** — param na AMA — e o único código que restava à frente
> deles, a **alínea (c) do 13** (alinhar `exact` com `ci` nos dois sítios), não sobe sozinha porque
> o **12 pode ser a causa** do que o 13 trata como efeito. Movê-la é **decisão de âmbito, não de
> ordem** — e é isso que a distingue da subida do LEDG-2464, que não tinha essa dúvida.

| # | Ticket | O quê | Onde | Feito? | Dependência |
| --- | --- | --- | --- | --- | --- |
| **1** | LEDG-2432 | Repor o login por email e palavra-passe | Frontend | ✅ **Sim** — em `develop` e `tst` | 🚨 Regressão; desbloqueou o `tst → ppr` |
| **2** | LEDG-2456 | Fuga de existência de conta **+ e-mails em inglês** | Backend | ✅ **Sim** — em `develop` e `tst` | Nenhuma — e torna o 15 menor |
| **3** | LEDG-2433 | Campo do método de autenticação (CMD/eIDAS) | Backend | ✅ **Sim** — 6 commits, suite completa verde; em `develop` e `tst` | Nenhuma — aditivo |
| **4** | LEDG-2457 | Tipo de cidadão **declarado** (nacional/estrangeiro) | Full-stack | ✅ **Sim** — 5 commits nos dois repos; em `develop` e `tst` | **Depende do 3** |
| **5** | LEDG-2434 | Levantamento — o script responde às três contagens numa execução | Spike | 🟡 **Parcial** — PR #277/#278, corrido em DEV; em `develop` e `tst` | ⏸️ **A execução em produção espera por tudo estar em `tst`** (decisão 12). Não bloqueia código — bloqueia o fecho de critérios no 8, no 10 e no 14 |
| **6** | LEDG-2462 | **Campos de sessão vazios no login SAML** (os cinco campos trackable) | Backend | ✅ **Sim** — PR #266; 6 commits, suite completa verde, 13 testes novos; em `develop` e `tst` | Nenhuma. Paralelo ao 5 — **este é código, o 5 é humano** |
| **7** | **LEDG-2465** | **Login recusado tratado como sucesso:** sessão marcada, log diz `OK`, auditoria diz `success`, e o link de uso único fica queimado | Backend | ✅ **Sim** — PR #268; 3 commits, suite completa verde, 11 testes novos; em `develop` e `tst` | Nenhuma — mexeu nas **mesmas duas funções** do 6, e foi de facto mais barato a seguir a ele |
| **8** | **LEDG-2466** | **`datastore.commit()` é no-op em Mongo:** 3 chamadas que não gravam nada, e o `confirmed_at` **nunca chegava à BD** | Backend | ✅ **Sim** — PR #272, 4 testes novos; em `develop` e `tst` | Nenhuma — o 6 deixou de o reparar de lado, deliberadamente |
| **9** | **LEDG-2464** | **Login ambíguo:** identificador duplicado resolvido por `.first()` — devolvia **sempre a conta mais recente** | Backend | ✅ **Sim** — PR #273, 6 testes novos; em `develop` e `tst` | Nenhuma. 🚨 **Nega acesso a ~26 contas** até o 14 as fundir |
| 10 | LEDG-2468 | **Nada impede uma organização de ficar sem administrador** — os dois endpoints de membro **e** os quatro caminhos de apagamento | Backend | 🟡 **Parcial** — PR #275: os **dois endpoints** guardados, em `develop` e `tst`. 🚨 **O `mark_as_deleted` continua a orfanar** | Os pontos 3/4/5 dependem da AMA. **Quanto mais cedo o resto entrar, menos casos o 11 trata à mão** |
| 11 | LEDG-2463 | **As 6 contas com conteúdo, 4 delas admin ÚNICO** — plano nomeado | Operação | ❌ Não | 🚩 **Não há ninguém para promover** — as 4 organizações têm **1 membro**, a própria conta sintética. Os donos entram por CMD (têm `auth_nic` válido), logo passa a **depender do LEDG-2437**, não da AMA. À AMA fica só: o que fazer se algum não voltar a entrar |
| **12** | **LEDG-2470** | **Contas institucionais deixam de existir:** publicar passa a ser sempre por conta pessoal, em nome próprio ou de uma organização | Operação | ❌ Não | Depende do **10**. **Contém o 11** como subconjunto, e pode ser a **causa** que o 13 trata como efeito |
| 13 | LEDG-2435 | **Uma identidade, uma conta** — as duas classes de duplicado | Backend | 🟡 **Parcial** — a **alínea (c)** feita: PR #279/#280, 11 testes novos; em `develop` e `tst` | As (a) e (b) por fazer: a (a) depende do 5, a (b) do 15. 🚨 **A (c) deixa presos os donos de placeholder cujo endereço real está noutra grafia — é razão adicional do prazo do 14** |
| **14** | **LEDG-2469** | **Fundir os duplicados que já existem** e depois impedi-los na BD (o `extras.auth_nic` não tem índice de unicidade) | Backend + Operação | ❌ Não | Depende do **9**, **10** e **13**. Fundir antes de o crescimento parar é limpar uma torneira aberta |
| 15 | LEDG-2431 | Associar a uma conta tradicional existente | Full-stack | ❌ Não | Depende do **2**, **5**, **11** e **13**. ✅ **Desenho decidido pelos dados: recusar quando há conteúdo** |
| **16** | LEDG-2438 | **Estrangeiros: identidade por documento em vez de NIC** | Backend | ✅ **Sim** — PR #283/#284, 15 testes novos; em `develop` e `tst` | 🚨 **Por validar contra o IdP real antes de sair de `tst`** — os testes mockam o pysaml2. 🔻 **Tirou os estrangeiros do âmbito do 17** |
| 17 | LEDG-2436 | Identidade sem identificador (eIDAS **e** CMD) | Backend | ⏸️ **Estacionado a 2026-09-14** | O 16 tirou-lhe os estrangeiros, mas **a escolha entre recusar e ligar pelo email continua proibida antes do LEDG-2288** — e nem DEV nem a auditoria conseguem responder. Ver a secção |
| **18** | **LEDG-2472** | **Consolidação self-service:** avisar que só haverá uma conta por pessoa, e deixar a pessoa mover os dados das secundárias para a principal | Full-stack | ❌ Não | Depende do **requisito 4 do 14** e do **10**. 🛑 **Tem de vir ANTES do 19** — depois da obrigatoriedade, quem perdeu o email de uma conta secundária já não entra nela para empurrar o conteúdo |
| **19** | **LEDG-2471** | **Descontinuar o login por email e palavra-passe:** inventário e gate no backend | Full-stack | ❌ Não | Depende do **15**, **17**, **18**, e do LEDG-2437 e **LEDG-2474** (era o LEDG-2467, que ficou feito — a substância passou para o 2474) |
| **20** | **LEDG-1277** | **Obrigatoriedade do Autenticação.gov** — o fim do arco | Produto | 🟡 Em curso | Depende do **19**. ⚠️ **Não activar antes dele** |
| — | **LEDG-2467** | **Recuperação de palavra-passe:** os mails do flask_security saíam de `webmaster@udata` | Backend | ✅ **Sim** — PR #270; em `develop` e `tst`, e **verificado em DEV** com mail recebido do remetente certo | **Fora da decomposição** — não é CMD/eIDAS |
| — | **LEDG-2474** | **Quatro razões de recusa dão a mesma resposta de sucesso** na recuperação — e uma conta inactiva fica **sem via de entrada nenhuma** | Backend + Produto | ❌ Não | **Fora da decomposição.** Bloqueado em **decisão da AMA**. 🚨 **Passou a ser o pré-requisito do 19** que o 2467 era, e agravou-se com o **7** |
| — | ~~NOVO-D~~ | ~~**Organizações AGIT duplicadas** (3 registos)~~ | — | ❌ **Não se cria** | A consulta desfez a suspeita — ver acima |

**Próximo a implementar:** o **11** (LEDG-2463) — ou o resto do **10**, quando a AMA decidir — mexe no **mesmo ficheiro** que o 7 acabou de
tocar, e o 6 deixou-o deliberadamente sem reparar de lado. Depois dele o **9** (LEDG-2468), cujos
pontos 1 e 2 são implementáveis já; os 3, 4 e 5 estão bloqueados numa decisão da AMA. Os pontos
1 a 4, 6 e 7 estão em `develop` e `tst`, e
o 5 é o único que não depende de nada — e é o que desbloqueia o desenho do LEDG-2435 e do
LEDG-2431. O dry-run já correu, o script de levantamento já está versionado com os dois eixos
de colisão, e DEV e TST já foram medidos (ver acima); **falta PPR**, e as perguntas 2/3/4 fora
de PRD.

> ⚠️ **Os números desta tabela mudam.** Entrou o LEDG-2457 e tudo o que vinha depois desceu uma
> posição. Quatro tickets referiam-se ao seu próprio lugar por número (*"é o ponto 2 da
> decomposição"*) e ficaram errados em silêncio; os dois que se referiam **por chave**
> (*"vem depois do LEDG-2438"*) continuaram correctos apesar de ambos terem mudado de posição.
>
> **Regra:** nas descrições dos tickets, referir dependências **por chave**, e deixar a posição
> só aqui. Foi aplicado aos quatro (LEDG-2431, LEDG-2433, LEDG-2434, LEDG-2435) em 2026-09-08,
> e aos três novos (LEDG-2462, LEDG-2463, LEDG-2464) em 2026-09-09 — que por isso não levam
> número na sua própria descrição.

✅ **O LEDG-2371 era pré-requisito prático de tudo isto, e está feito** (PR #285, `develop`) —
sem ele nada era mensurável, e no caso do LEDG-2436 era a **única** forma de saber quantos casos
são estrangeiros com CMD e quantos são eIDAS mal formado. ⏳ **Mas só mede daqui para a frente**,
e só a partir do deploy: a repartição que o 17 precisa exige tempo de recolha, não só a
correcção.

### 1 — LEDG-2432 · Repor o login por email e palavra-passe *(frontend)* ✅ FEITO

Reposição de UI, e nada mais. O contrato backend estava intacto nas quatro branches e já
funcionava nos dois estados da flag **sem o frontend a ler a flag**.
⚠️ **Não introduzir leitura da flag no frontend** — seria reintroduzir a causa desta regressão.

**Estado:** em `develop` e `tst`. Ainda não em `ppr` nem `main`.

### 2 — LEDG-2456 · Fuga de existência de conta e e-mails em inglês *(backend)* ✅ FEITO

Eram **três** defeitos: o `"This email is already registered"` **revelava que o endereço tem
conta**, **não estava traduzido**, e os **e-mails de autenticação saíam em inglês** com assunto
incluído.

A verificação saiu do form (que só sabe recusar) e entrou na view (que pode responder igual nos
dois casos) — **avisa o dono da caixa** e devolve a resposta do ramo livre. **Zero alterações no
frontend.** A resposta genérica construída aqui **é a restrição 2 do LEDG-2431** — o
LEDG-2431 estende-a em vez de a reinventar.

### 3 — LEDG-2433 · Campo do método de autenticação *(backend)* ✅ FEITO

`extras.auth_provider`, com `"cmd"` ou `"eidas"` vindos da **rota ACS** — a jusante a distinção
não é inferível. Escrito na criação, no login (que é o **backfill** das contas antigas), no
wizard e no link de email. **Ausente significa ausente**: nada é gravado sem provedor e nenhum
default é substituído.

⚠️ **Não distingue nacional de estrangeiro** — ver a secção acima e o ponto 4. Inclui a
justificação da decisão 1 no `nic.py`.

### 4 — LEDG-2457 · Tipo de cidadão declarado *(full-stack)* ✅ FEITO

O `CmdTab.tsx` já pergunta se o cidadão é nacional ou estrangeiro — e **atira a resposta fora**:
o valor só habilita o botão. Este ponto envia-o e grava-o em `auth_citizen_declared`, **em chave
própria e marcada como declarada**.

O percurso é **paralelo ao `next`**, que já faz esta viagem: `CmdTab` → `buildSamlEndpoint` →
`?citizen=` → `sp_initiated` valida contra allowlist e guarda na sessão → a rota ACS lê e grava.

⚠️ **A allowlist é no backend** — o valor chega em query string controlada pelo utilizador, e um
valor não reconhecido **não grava nada**, nem cru nem default.

⚠️ **Este valor nunca gateia nada.** Vem de um radio button. Quando o LEDG-2438 trouxer o
provado, **o provado ganha** — e o desacordo entre os dois passa a ser o sinal de IdP mal
configurado que falta ao LEDG-2436.

**Dois achados da implementação, que valem para os pontos seguintes:**

- 🚨 **A declaração contaminava a sessão entre utilizadores.** Ficava na sessão depois de ser
  lida, logo o próximo login CMD no mesmo browser — alguém a abrir um `/saml/login` de bookmark,
  sem parâmetro — gravava na sua conta a resposta da pessoa anterior. É **o mesmo perigo** pelo
  qual o `saml_confirmation_pending` já é limpo duas linhas ao lado, na mesma função, com o
  raciocínio escrito acima: *"whoever signs in now owns this session"*. A chave nova faltava
  nessa lista. **Lição para quem acrescentar chaves de sessão: a lista do
  `_terminate_local_session` é manual, e é isso que a torna fácil de esquecer.**
- **O `MigrationNotice` do separador de email também arranca um login CMD**, mas esse ecrã nunca
  faz a pergunta. Tem handler próprio e não envia parâmetro — foi o TypeScript que o apanhou,
  não um teste. **Fechado a seguir** com dois testes que observam a URL de arranque SAML (a
  mesma de onde o backend lê o parâmetro): um afirma que o aviso não envia nada, o outro que o
  separador CMD envia — o par é deliberado, porque uma asserção de ausência sozinha passaria
  por vazio se a captura deixasse de registar. Ambos provados por mutação.
- **O caminho do link por email não tinha teste, e é o único sem sessão.** Descoberto por um
  login manual: a asserção CMD não trouxe email, o utilizador escreveu um novo, e o campo não
  apareceu na base de dados. **A causa era ambiente, não código** — o `develop` local do
  frontend estava quatro commits atrasado e o browser não enviava o parâmetro; o `auth_provider`
  gravou porque esse não depende do frontend, e foi esse contraste que apontou a causa. Mas
  expôs a lacuna a sério: das quatro escritas, essa era a única sem prova. **O código estava
  correcto** — o teste escrito a seguir passou à primeira. Ver a lacuna 7.

**Porque vem cedo:** o dado **só se acumula a partir do momento em que entra em produção**. O
ponto 5 não o consegue contar no dia em que correr — estará vazio em todas as contas — logo cada
semana de atraso é uma semana de logins cujo dado se perde.

### 5 — LEDG-2434 · Levantamento *(spike, sem código)*

**Quantas contas têm conteúdo**, **o que depende do email como identificador**, **quantas são a
mesma pessoa**, e **quantos duplicados existem sem prefixo**. Começa pelo
`migrate-nics --dry-run`, mas **não se fica por aí** — a classe 2 exige consulta própria.

**Acrescentar ao âmbito:**

- registar o valor efetivo de `MIGRATION_MODE_ENABLED` **nos quatro ambientes**, lido do `.env`
  de cada um;
- registar que `auth_provider` e `auth_citizen_declared` **existem e estão vazios**, e a partir
  de que data a contagem passa a ter significado.
  ⚠️ **Este spike não consegue contar estrangeiros** — o campo do ponto 4 só se preenche em
  logins futuros.

#### Primeira execução do dry-run — 2026-09-08

```
plain NICs a hashear                  1070
já hasheados                             0
legacy-encrypted (intocados)          1207   ← 52% das 2300 com auth_nic
não reconhecidos (intocados)            23
duplicados SAML a fundir                 0
```

🚨 **Correu na base de dados LOCAL, não em nenhum dos quatro ambientes.** Portanto **estes
números não respondem ao critério de aceitação**, que pede a data *e* o ambiente — e "local"
não é um dos quatro.

Os dados aparentam ser reais (emails de municípios, `ama.gov.pt`), logo a BD local é
presumivelmente um dump restaurado — de **origem e data desconhecidas**. Consequências:

- **As proporções valem como forma, não como contagem.** Que 52% estejam em cifra legada é
  um sinal forte sobre a natureza do problema; que sejam exactamente 1207 não vale para
  ambiente nenhum.
- **O "zero contas com endereço sintético" é o mais suspeito de todos.** Pode ser verdade,
  ou ser artefacto da idade do dump ou do valor local do `MIGRATION_MODE_ENABLED` — que é
  precisamente a pergunta 9, ainda sem resposta.
- **As conclusões por hash são locais por construção**, porque o `hash_nic` usa o
  `SECRET_KEY` desta máquina.

**O que falta:** correr o `audit_institutional_users.py` com `--host` contra **DEV
(o host de DEV)** e **TST (o host de TST)**. É para isso que o script recebe o parâmetro.

**O que estes números mudam:**

1. **🚨 1207 contas — 52% — ficam intocadas, e a migração que a docstring promete não
   existe.** O `is_nic_legacy_encrypted` só é referenciado pelo contador do próprio comando;
   não há desencriptação em `udata/migrations/` nem em lado nenhum. **Mas há caminho:** o
   `_has_linked_nic()` devolve `False` para uma cifra legada, logo estas contas caem no match
   por email e são candidatas ao assistente de associação — reconquistam o link provando
   posse. Ou seja, **o `MIGRATION_MODE_ENABLED` decide o acesso de 1207 contas.**

2. **Zero contas com endereço sintético neste ambiente.** Nenhuma linha `SKIP`, nenhum
   `saml-`. A estimativa de **~200 contas** do pedido original **não se confirma aqui** — o
   que reforça a leitura da classe 2: o problema pode estar todo em duplicados **sem**
   prefixo.

3. **Uma colisão de capitalização confirmada**, entre as 1093 listadas:
   `Pablolira@hotmail.com` (`67fe5ab0…`) e `pablolira@hotmail.com` (`67fe5a7f…`), criadas a
   **49 segundos** de distância. É a classe 2 em dados reais. Lower bound, não a resposta à
   pergunta 8 — só cobre contas **com** `auth_nic`.

4. **Os 23 não reconhecidos são usernames e nomes, não NICs.** Cruzando com o email não há
   dúvida: `maria.filomena.delgado@funchal.pt` → `'mafide'`,
   `iolanda.sofia.fernandes@funchal.pt` → `'iosofe'`, `carlos.mora@techframe.pt` → `'CMTF'`.
   **Só um parece documento:** `'4595P5L28'`, com letras — forma de título de residência, não
   NIC português. **Prova a favor do LEDG-2438.**

5. **13 emails malformados** — 10 com espaço final, `dora.canelas` e `gmrmatos` sem `@`, e
   `Nelinho_33@hotmail,com` com vírgula em vez de ponto. **Todos no grupo dos 1070**, que se
   auto-cura pelo NIC no primeiro login (passo 1b), logo não bloqueiam ninguém — mas o
   endereço com vírgula nunca receberá mail.

❌ **Correcção a uma leitura anterior:** dez dos 23 valores têm exactamente 12 caracteres
**porque o log os corta** — `nic[:12]` em `commands.py`. É truncagem de **impressão**, não dos
dados. Não existe limite de 12 no código de escrita, e não vale a pena procurá-lo.

⚠️ **Os hashes dependem do `SECRET_KEY` de cada ambiente** (`hash_nic` é HMAC com essa
chave), logo estes números **não são portáveis** e o levantamento é obrigatoriamente **por
ambiente**. Uma rotação de chave invalida todos os links existentes.

#### Segunda execução — 2026-09-11, agora contra o **DEV**, com o script estendido

O `audit_institutional_users.py` passou a responder, numa só execução e sem `SECRET_KEY`, às
três contagens que estavam a bloquear decisões noutros tickets. Contra o DEV, 9 075 contas:

```
accounts with NO confirmation date  2059
  ...of those, CMD-linked ......... 730

accounts sharing one stored NIC ... 13 group(s)
  (content check live: 102 accounts own content overall)
  ⚠ groups with content on MORE THAN ONE side: 0

organizations with NO administrator  63
membership rows pointing at a MISSING user  0
```

**O que cada número desbloqueia:**

1. **2 059 contas sem data de confirmação, 730 delas com link CMD.** É a população que a
   recuperação de palavra-passe recusa em silêncio — a resposta genérica anti-enumeração faz
   a recusa parecer um email enviado, e por isso ninguém a tinha contado. O subconjunto com
   CMD é o que o LEDG-2466 corrigiu **para o futuro**: as contas já criadas continuam com o
   campo a nulo e continuam a não conseguir recuperar a palavra-passe. **Falta decidir se são
   confirmadas em massa por migração** — é o critério 6 do LEDG-2466, e agora tem número.

2. **63 organizações já sem administrador.** A guarda do LEDG-2468 impede que se criem novas;
   **não repara nenhuma destas**. Cada uma está encravada: ninguém gere membros, aceita
   transferências nem a edita, e não pode promover ninguém a partir de dentro. O relatório
   lista-as pelo nome, portanto a reparação tem lista de trabalho. **Isto é o ponto 4 do
   LEDG-2468**, que estava a ser discutido sem nenhum número por trás.

3. **Zero referências de membro penduradas.** Contas apagadas em *soft delete* não contam
   como em falta — o documento continua lá; só conta um id sem documento nenhum, que é o que
   um apagamento duro deixa para trás. Neste ambiente não há nenhuma.

4. **Nenhum dos 13 grupos duplicados tem conteúdo dos dois lados.** Isto é o requisito 1 do
   LEDG-2469: se só um lado tiver conteúdo, mover o identificador chega; se ambos tiverem,
   o comando de fusão existente **apaga** o duplicado sem transferir nada. A linha
   `content check live: 102` está lá de propósito — prova que o detetor deteta, logo o zero
   é **medido**, não um varrimento partido. Dos 13 grupos, 4 têm um lado que administra uma
   organização e 2 têm um lado que é membro.

🚨 **Estes números são de DEV e não respondem às perguntas.** Esta doc já teve de retratar
uma conclusão tirada de DEV/TST: são populações próprias. A execução prova que **o script
funciona**, não que os números sejam os de produção. Quem tiver acesso a produção tem de o
correr lá — é um comando, e é a mesma saída.

### 6 — LEDG-2462 · Campos de sessão vazios no login SAML *(backend)*

O plugin importa o `login_user` do **`flask_login`** (`saml_govpt.py:31`), que **não escreve**
`last_login_at`, `current_login_at`, `login_count` nem `last_login_ip`. Quem os escreve é o
`login_user` do `flask_security`, que não é importado — e o `SECURITY_TRACKABLE = True` já está
em `settings.py:86`, portanto os campos **deviam** ser mantidos. É defeito, não decisão.

Medido: das contas com `auth_nic`, **83%** das criadas antes de 2026-01 têm `last_login_at`,
contra **3%** (7 de 232) das criadas entre junho e agosto de 2026. Os 83% históricos são contas
antigas, não prova de que o fluxo SAML escreva.

❌ **RETRACTADO — "a troca do import, sozinha, não grava nada".** Escrevi isso a partir do
docstring do próprio `login_user` (*"make sure you commit changes after this request"*).
**Não se aplica aqui:** o `MongoEngineDatastore.put()` é `model.save()`, uma escrita imediata,
e o `Datastore.commit()` da classe base é `pass` — aquele conselho é para SQLAlchemy, onde o
`put()` é só um `session.add()`. Trocar o import **chegava** para persistir. Não havia `save()`
a acrescentar, logo a prova por mutação também tinha de ser outra.

**Mas a troca não é o que se fez, e por três razões que só apareceram ao implementar.** O
`_datastore.put(user)` dentro do `flask_security.login_user` é **desprotegido**, logo um
documento legado que não valide passa de "campo perdido" a 500 no login — a regressão que o
comentário da linha 1094 existe para impedir. E a troca traz `session["fs_cc"]`/`fs_paa` e os
sinais `identity_changed`/`user_authenticated`, que nunca dispararam neste caminho. Três
mudanças de comportamento num ticket de cinco campos, e nas contas menos capazes de as
absorver. Não há unidade importável mais pequena: a semântica está inline naquele bloco.

**O que se fez:** um helper `_record_login_activity` que espelha a semântica e escreve os cinco
campos **atomicamente** (`update_one` com `inc__login_count`), chamado **só se o `login_user`
devolver verdadeiro**, com gate no `trackable` da extensão e o `datetime_factory` dela.

🚨 **E porque NÃO com `user.save()`, que era o plano aprovado.** A revisão adversarial provou
que um save arrasta `about`, `first_name` e `last_name`: o `User.pre_save` sanitiza-os em
qualquer caminho de escrita, e num documento legado o valor **muda de facto** (`Silva & Sousa`
→ `Silva &amp; Sousa`), logo o mongoengine marca-o sujo e ele vai no mesmo `$set`. **Quem
entrasse por CMD veria o próprio nome estragado no ecrã**, em silêncio, porque a escrita está
dentro de um `except` que só loga. E o mesmo acoplamento deixava um login sobrescrever uma bio
editada noutro separador. Verificado: o `sanitize_strict` **é** idempotente, e o mongoengine
só marca sujo quando o valor muda — logo o dano é de uma vez, na primeira entrada de cada
conta legada, e é isso que o torna difícil de notar.

> 💡 **Sanitizar dados legados é trabalho de migração, não efeito colateral de um login.** E o
> `inc__` atómico deu de graça uma coisa que o próprio upstream faz mal: dois logins
> simultâneos deixam de perder uma contagem.

**Prova obrigatória:** seis mutações, e três matam **exactamente um** teste cada — tornar a
chamada incondicional (mata o da conta inactiva), remover o gate do `trackable`, e trocar o
import. Voltar a `user.save()` mata o teste do apelido legado. Cobrir **os dois caminhos** —
login directo e link por email — porque foi a assimetria entre eles que produziu a lacuna 7
dos testes; comentar só a chamada do link deixa vermelho só o teste do link.

⚠️ **A lacuna de cobertura que a revisão encontrou, e que vale para o resto do ficheiro:** 9
dos 11 testes faziam `patch` do `login_user` com um mock **sempre truthy**, logo nenhum
exercitava o ramo verdadeiro da guarda com a função real. E o teste da guarda apontava para o
`User.save`, que deixou de ser chamado — **passava sem exercitar a guarda**.

✅ **Estado: em `develop` e `tst`** (PR #266), 6 commits, suite completa verde, 13 testes novos.
`ppr` e `main` retidos pela decisão de promoção em bloco. **Fez aparecer os pontos 7
(LEDG-2465) e 8 (LEDG-2466)**, e ambos mexem nestas mesmas duas funções.

⚠️ **A confirmar antes de `ppr`/`main`, não em `tst`:** o valor efectivo de
`YEARS_OF_INACTIVITY_BEFORE_DELETION` em cada ambiente, porque as contas de CMD/eIDAS entram
na maquinaria de inactividade pela primeira vez (com data recente, logo protegidas); e o
`PROXY_FIX_X_FOR`, porque o IP gravado é o que o Flask vê e o ProxyFix não valida que é um IP
— pré-existente e já pior no rate limiter, que usa a mesma fonte, mas agora o valor persiste.

⚠️ **Não recupera o passado.** As 232 contas criadas desde junho ficam sem histórico; os campos
só têm significado a partir do deploy. **A pergunta 3 do LEDG-2434 continua sem resposta para o
período já decorrido** — precisa de logs de acesso, ou de se aceitar a lacuna e escrevê-la.

⚠️ **Impacto largo, fora deste refinamento:** qualquer lógica que dependa de inactividade —
limpezas, notificações, relatórios de utilização — trata **todos** os utilizadores de CMD/eIDAS
recentes como dormentes.

### 7 — LEDG-2465 · Login recusado tratado como sucesso *(backend)*

O `flask_login.login_user` devolve `False` **sem estabelecer sessão** quando a conta não está
activa. O plugin chamava-o e **ignorava o retorno**.

**Alcançável, e não teórico:** `active = field(BooleanField())` — **sem default** no modelo.
Uma conta legada importada sem o campo cai aqui, e é a mesma população que este refinamento
trata. Nenhuma guarda do funil olha para `active`: os gates antes do login são `user is None`,
`user.deleted`, o marcador de confirmação pendente e o `requires_confirmation`. Confirmado por
tracing.

**Com o login recusado, o que a função faz a seguir:** `session["saml_login"] = True`, o log
diz `login_user OK`, o `_audit_saml("success", …)` **já foi emitido a montante**, e há **302
para o portal** sem mensagem de erro.

🚨 **Pior no caminho do link por email:** quando se chega ao `login_user`, o `user.save()`
anterior **já ligou a identidade e queimou o token de uso único**. A conta fica ligada, o link
não se repete, não há sessão, e o CMD seguinte recusa pela mesma razão. **A pessoa perde a
única prova de posse que lhe foi enviada.**

⚠️ **O LEDG-2462 só corrigiu 5 dos ~8 registos da função** — condicionou a escrita dos campos
de sessão ao retorno, com teste e mutação. A flag de sessão, o log, a auditoria e o redirect
ficaram, de propósito: decidir qual é a resposta certa a uma conta inactiva num fluxo SAML é
âmbito próprio.

⚠️ **Cuidado com a assimetria:** a auditoria de sucesso é emitida na rota ACS, **antes** do
funil correr. Corrigir só o funil deixa a linha de auditoria errada.

#### ✅ Feito — PR #268, em `develop` e `tst` (2026-09-10)

3 commits, suite completa verde, **11 testes novos (8 nas rotas + 3 no link) e nenhum a fazer patch do `login_user`** — que
era exactamente a lacuna que o LEDG-2462 deixou. Provas: 6 dos 8 testes das rotas vermelhos sem a
guarda, 2 dos 3 do link vermelhos sem o check, e a mutação do `user and` mata **exactamente um**
teste.

**A guarda ficou nas duas rotas ACS, imediatamente depois do `_find_or_create_saml_user` e antes
do ramo do wizard** — e não no retorno do `login_user`, que era o sítio óbvio e é tarde demais:
nessa altura o funil já auto-confirmou a conta e já estampou o `auth_provider`, logo recusar
depois deixaria uma conta confirmada e marcada como tendo autenticado por CMD por um login
recusado. E ficar antes do ramo do wizard é o que torna a recusa **alcançável** para a conta
legada não ligada, que é por construção quem recebe links de validação.

No caminho do link, o check entrou no `_migration_link_token_status`, que é **read-only por
construção** — o não-consumo do token passa a ser propriedade da *posição*, não de lembrar de
desfazer algo.

**Duas correcções ao plano, ambas apanhadas na execução:**

* 🚩 **O `caplog` do pytest não é injectável nesta suite.** O `APITestCase` desce de
  `unittest.TestCase`, onde o `caplog` não entra. Usa-se `self.assertLogs`, que faz o mesmo
  trabalho — anexa handler e fixa o nível — e sem isso a asserção "nenhuma linha `success`"
  passaria sobre uma captura vazia.
* ✅ **O risco de regressão grave foi descartado por verificação, não por memória.** A guarda
  podia recusar um registo CMD **novo** se as contas nascessem sem `active`. O
  `_create_saml_user` vai pelo `datastore.create_user`, e o `_prepare_create_user_args` do
  flask_security faz `kwargs.setdefault("active", True)`. Nascem activas.

⚠️ **E um defeito real que este ponto NÃO corrigiu, deliberadamente:** a linha `outcome=success`
prematura continua a existir para os ramos `deleted` e confirmação-pendente, que são alcançados
antes da emissão da rota. Quem contar `outcome=success` continua a contar a mais nesses dois.
Corrigi-lo exige decidir o vocabulário de cada ramo — em particular, a confirmação pendente **não
é** uma recusa de segurança e já tem `migration_pending`. **Recomendação: ticket próprio.**

### 8 — LEDG-2466 · `datastore.commit()` é no-op em Mongo *(backend)*

O `Datastore.commit()` da classe base do `flask_security` é literalmente `pass`, e o
`MongoEngineDatastore` **não o sobrepõe** — não precisa, porque o seu `put()` já é
`model.save()`. Logo `datastore.commit()` **não faz nada** nesta aplicação, e está usado como
se fizesse flush em **três** sítios do plugin (`_create_saml_user`,
`_create_pending_saml_user`, e o ramo de auto-confirm do funil de login).

**A consequência real:** no auto-confirm, o `user.confirmed_at` é atribuído e o `commit()` não
o grava. O valor só chega à base de dados quando o registo do `auth_provider` mais abaixo calha
salvar — o que **não acontece num login repetido com o provedor já gravado**. A intenção
escrita no próprio comentário do código não se cumpre.

**Como apareceu, e porque saiu do LEDG-2462:** a primeira versão daquela correcção escrevia com
`user.save()` e reparava dois destes três sítios **por efeito colateral**. Isso foi desfeito
(ver o ponto 6), logo o defeito volta ao estado original. ✅ **É melhor assim:** em vez de dois
sítios reparados por acidente e três chamadas mentirosas a ficar no código, este ponto trata o
problema todo.

⚠️ **A correcção não pode ser um `save()`** — tem de ser escrita restrita ao campo, como o
`_record_login_activity` passou a fazer, senão reintroduz o problema do nome legado.
E o `_create_pending_saml_user` é o caso em que a chamada é **só** enganadora: ali o
`confirmed_at` fica por desenho sem valor, e a conta é barrada antes de chegar ao funil.

> 💡 **É a terceira ocorrência da mesma classe de bug deste refinamento:** código que muta e
> não grava, ou que grava sem que se veja.

#### ✅ Feito — PR #272, em `develop` e `tst` (2026-09-11)

🚨 **O defeito era maior do que este documento descrevia.** Dizia que o `confirmed_at` *"se perde"*;
na verdade **nunca chegava à base de dados**. O `create_user` termina em `put(user)` → `model.save()`,
logo o documento é escrito **antes** de o campo ser atribuído; o objecto devolvido carrega o valor,
logo o `requires_confirmation(user)` — que é `confirmed_at is None` — dizia **False** e o auto-confirm
nem corria; e o stamp do provedor já concordava e não salvava. No login seguinte repetia-se o ciclo.

🔑 **E é a causa de um sintoma que este documento atribuía a outro ponto.** Uma conta com
`confirmed_at` nulo é recusada na recuperação de palavra-passe com `CONFIRMATION_REQUIRED` — a segunda
linha da tabela do LEDG-2474. ⇒ **Todas as contas criadas por SAML nunca conseguiram recuperar a
palavra-passe, e nunca foram informadas.** Parte do LEDG-2474 resolve-se sozinha com isto.

**Três sítios, corrigidos de três formas diferentes de propósito:** na criação o campo passa *dentro*
do `create_user` (uma escrita só, e o erro de ordem deixa de ser exprimível); na conta pendente a
chamada é removida (ali o campo fica sem valor por desenho); e no login é **escrita atómica de um só
campo** — não `save()`, que arrastaria `about`/`first_name`/`last_name` pelo `pre_save`.

✅ **Critério do âmbito fechado sem código:** as 3 chamadas eram **as únicas do repositório inteiro**.

✅ **A contagem já existe — em DEV: 2 059 contas sem data de confirmação, 730 delas com link CMD.**
A separação é o que importa: **as 730 curam-se sozinhas** no próximo login CMD, agora que a escrita
chega à base de dados — a recomendação de **não fazer migração** mantém-se e passa a ter número. As
outras ~1 329 são contas tradicionais que nunca validaram o email, o que é o comportamento normal e
não se corrige por migração nenhuma. ⚠️ **Mas nenhuma das 730 consegue recuperar a palavra-passe
até voltar a entrar por CMD** — se alguma delas perdeu o acesso ao CMD, está presa nos dois lados.
🚨 O número é de DEV; o de produção exige acesso a produção, e é o mesmo comando.

⚠️ **E uma pergunta de produto:** se alguma conta legítima depende de estar não-confirmada para ficar
bloqueada, isto desbloqueia-a. Pela leitura o auto-confirm é deliberado e não se aplica aos endereços
auto-declarados, mas é a AMA que confirma.

### 9 — LEDG-2464 · Login ambíguo: identificador duplicado resolvido por `.first()` *(backend)*

O passo 1 do resolvedor faz `User.objects(extras__auth_nic=…).first()`. Com duas contas a
partilhar o identificador, **devolve uma arbitrária** — e a mesma pessoa pode entrar hoje numa
conta e amanhã na outra, sem nada mudar.

**Medido em dados de produção: 13 grupos, 26 contas.** E **nenhum inclui uma conta sintética** —
são pares de contas com endereço real, tipicamente a mesma pessoa com dois endereços criados a
segundos ou minutos de distância. **Independente do LEDG-2435**, portanto: não é o problema das
contas sintéticas, é outro.

⚠️ **O `migrate-nics --dry-run` não o reporta de forma fiável:** o `_find_shared_nics()` filtra
por `is_nic_hashed`, logo num ambiente com valores em claro **subconta**, e num ambiente sem
nada hasheado devolve zero garantido. O script de levantamento versionado no LEDG-2434 agrupa
pelos valores **como estão guardados** e não tem esse ponto cego.

**O que o ticket tem de decidir:** o resolvedor deve **recusar** uma identidade ambígua (falhar
o login com mensagem clara e registo de auditoria) em vez de escolher uma conta ao acaso. Uma
escolha arbitrária num caminho de autenticação é pior do que uma recusa: dá acesso a uma conta
que pode não ser a da pessoa.

#### ✅ Feito — PR #273, em `develop` e `tst` (2026-09-11)

🚩 **E o ticket estava errado num ponto que importa.** Dizia *"devolve uma arbitrária, sem ordenação
definida"* e que *"a pessoa pode entrar hoje numa conta e amanhã na outra"*. **Confirmado em runtime:
o `User._meta` tem `ordering: ["-created_at"]`** — o `.first()` devolvia **sempre a conta mais
recente**, deterministicamente. Dois comentários do próprio ficheiro já o diziam.

⚠️ **E determinístico é pior, não melhor.** Aleatório seria notado por quem lhe acontecesse; assim
entrega sempre a mesma sessão errada, o mesmo conteúdo errado e as mesmas pertenças erradas, e nada
contradiz a ilusão de que a conta é sua. ⇒ **Derruba o contra-argumento do próprio ticket** contra
"tornar determinístico": já era. O que falta é **prova de posse**, que ali não existe — daí recusar.

🔑 **E fechou um caso que o código não conseguia ver.** O lookup do hash corria primeiro e o de
valores em claro **só quando o primeiro não encontrava nada** — logo uma conta com o hash e outra com
o mesmo NIC em claro eram **invisíveis uma à outra**. A pergunta certa é *quantas contas reclamam
esta identidade*, e só perguntar pelas duas formas responde.

**Desenho:** o resolvedor reporta a ambiguidade como estado próprio, e as **duas rotas ACS** recusam —
antes de qualquer escrita e antes do ramo do assistente, na mesma posição da guarda do ponto 7.
A mensagem é a convenção do ficheiro, não o `GENERIC_AUTHN_FAILED` do flask_security, que diria
*"identity or password invalid"* — enganador quando a identidade é válida e está duplicada.

⚠️ **Numa revisão ao próprio código:** a primeira versão fazia **duas** consultas, e o
`extras.auth_nic` **não tem índice** — cada lookup é um varrimento. Substituído por um `$in` numa só
consulta, em commit próprio.

🚨 **Nega acesso a ~26 contas** (os 13 grupos). É o resultado correcto — entrar na conta de outra
pessoa é pior do que não entrar — e **o congelamento do `tst → ppr` é o que o torna seguro**: chega a
`tst`, não a produção. O desbloqueio é o **14**.

⚠️ **Fora de âmbito, com razão escrita:** o `.first()` de `:3407` usa o resultado como conta, mas o
comentário do código diz *"Normally unreachable — rule 1"* e esta correcção recusa antes. Guardá-lo
seria guardar estado inalcançável — o que a revisão do ponto 7 reprovou. **Nomeado como o sítio a
rever se as guardas das rotas forem reordenadas.**

### 10 — LEDG-2468 · Nada impede uma organização de ficar sem administrador *(backend)*

`MemberAPI.put` e `MemberAPI.delete` (`udata/core/organization/api.py:748-780`) verificam **só** quem
pode gerir membros. **Nenhuma verifica que sobra pelo menos um administrador.** O `is_admin`
(`organization/models.py:363-365`) e o `by_role` são de leitura e não bloqueiam nada; procurei uma
guarda de "último admin" em todo o `udata/core/organization/` e **não existe**.

**É o vazio estrutural por trás do ponto 10.** As 4 organizações públicas cujo único administrador é
uma conta sintética existem porque nada o impediu — e nada impede que voltem a existir depois de o 10
as arrumar à mão. **O 10 trata 4 casos; este trata a causa.**

⚠️ **Contar as que já estão órfãs antes de decidir** — a guarda nova não as repara, e uma organização
sem admin não pode promover ninguém de dentro. O `audit_institutional_users.py` já sabe contar
pertenças e papéis, e é o sítio para acrescentar essa contagem.

#### 🚨 Âmbito alargado a 2026-09-10 — os endpoints de membro NÃO são o pior caminho

A versão anterior deste ponto deixava o apagamento de conta **fora de âmbito**, como risco nomeado a
medir depois. **Verificado no código, esse adiamento estava errado** — e o caminho excluído é mais
grave do que o incluído.

O `User.mark_as_deleted` (`udata/core/user/models.py:306`) **termina a remover a pessoa de todas as
organizações, com escrita directa no modelo**:

```python
for organization in self.organizations:
    organization.members = [
        member for member in organization.members if member.user != self
    ]
    organization.save()
```

🔑 **Não passa pelo `MemberAPI`** — logo uma guarda posta nos dois endpoints **não é executada por
este caminho**, e o ticket, como estava desenhado, deixaria o buraco maior aberto e pareceria fechado.

**Quatro chamadores, e nenhum passa pelos endpoints:**

| Onde | O quê | Alcance |
| --- | --- | --- |
| `user/api.py:118` | `DELETE /api/1/me/` — a pessoa apaga a própria conta | 🚨 **sem condição nenhuma** |
| `user/api.py:733` | um administrador apaga a conta de outro | sempre disponível |
| `user/tasks.py:75` | o job `delete-inactive-users` | ⚠️ gated — ver abaixo |
| `user/commands.py:84` | `udata user delete` (CLI) | sempre disponível |

🚨 **O primeiro é o que importa: o único administrador de uma organização consegue deixá-la órfã
apagando o seu próprio perfil.** Sem admin envolvido, sem aviso, sem guarda, sem privilégio nenhum.

**E um quinto caminho, que não limpa nada:** o `dup._delete()` do `_merge_cmd_duplicates` é **hard
delete** — nem passa pelo `mark_as_deleted`, logo **nem chega a remover a pertença**. Deixa uma
referência de membro pendurada para uma conta que já não existe: estado pior do que órfã, é
inconsistente.

⚠️ **O job automatizado está desligado por omissão, mas ninguém verificou os ambientes.** O
`delete_inactive_users` sai logo se `YEARS_OF_INACTIVITY_BEFORE_DELETION` for falsy, e o default é
`None` (`udata/settings.py:186`). 🚨 **O valor efectivo vem da configuração do ambiente, e é a mesma
classe de desconhecido que a flag `MIGRATION_MODE_ENABLED`** — que já produziu duas regressões neste
refinamento por se ter assumido um valor. **Acrescentado às perguntas do ponto 5.**

E se estiver ligado, a população em risco é precisamente a das 4 organizações: as contas sintéticas
levam 404 a cada login (LEDG-2437), logo são candidatas naturais a deixar de entrar → tornarem-se
inactivas → serem apagadas → **organização órfã, sem ninguém ter feito nada.** Não se afirma que
aconteça; afirma-se que **nada o impede** e que o valor não é conhecido.

#### A consequência de desenho

⚠️ **A guarda não pode ser duplicada em cinco sítios** — o sexto caminho que aparecer fica sem ela,
que é exactamente como este defeito existe hoje. Tem de ser **uma função reutilizável** chamada pelos
dois endpoints **e** pelo `mark_as_deleted`.

🚨 **E recusar o `DELETE /api/1/me/` prenderia a pessoa à conta**, o que tem implicações de protecção
de dados: quem quer sair do portal não pode ficar retido por ser a única administradora de uma
organização. A saída provável é exigir a passagem do papel antes, ou apagar e escalar a organização
para sysadmin com registo — **decisão da AMA, escrita antes de haver código.**

🔑 **E isto passou a ser pré-requisito do 14 e do 18**, que apagam contas **por desenho**: o 14 funde
os 13 grupos, e no 18 apagar a conta secundária depois de a esvaziar é uma das opções em cima da mesa.

⚠️ **E a guarda destes dois endpoints não fecha os outros caminhos:** o `mark_as_deleted` e o
`dup._delete()` do `migrate-nics` também podem deixar uma organização órfã, e não passam por aqui.

#### 🟡 Parcialmente feito — PR #275, em `develop` e `tst` (2026-09-11)

**Os dois endpoints de membro estão guardados.** Um só predicado no modelo (`is_last_admin`), chamado
pelo `delete` e pelo `put` — **no modelo e não na API**, porque quando o comportamento do apagamento
de conta for decidido esses caminhos têm de fazer **a mesma pergunta**, não repetir a regra.

Três decisões de desenho: dispara numa **mudança** de papel e não em qualquer actualização do registo;
**não** dispara numa organização que já está órfã (recusar ali congelava uma organização já presa, por
uma operação que não a piora — tem teste próprio, porque é o tipo de decisão que um leitor futuro
tomaria por esquecimento); e no `put` corre **antes** do `populate_obj`, lendo o papel novo do
formulário — depois de populado o membro já tem o papel novo, logo o predicado diria `False` e a
guarda nunca dispararia.

🚩 **Uma lacuna apanhada por mutação, no próprio código novo:** remover a condição do papel novo
deixava **todos** os testes verdes. Sem ela, um `PUT` que mantém o último admin como admin passaria a
ser recusado, e nada notava. Teste acrescentado.

## 🚨 E fica metade por fazer — a metade maior

Varrimento de todo o backend: há **exactamente dois** caminhos de remoção de membros.

| Caminho | Coberto? |
| --- | --- |
| `organization/api.py:801` — os dois endpoints | ✅ sim |
| `user/models.py:337` — o `mark_as_deleted`, com **escrita directa** | ❌ **não** |

⇒ **Uma organização pode continuar a ficar sem administrador** por apagamento de conta: pela própria
pessoa, por um admin, pelo job de inactividade, ou pelo CLI.

⚠️ **Não é "pôr a mesma guarda".** Recusar o `DELETE /api/1/me/` prenderia a pessoa a uma conta que
quer abandonar, com implicações de protecção de dados. **É decisão da AMA**, e está escrita no
CHANGELOG e no corpo do PR — não em rodapé, porque *"organizações não podem ficar sem administrador"*
é exactamente a frase que alguém leria como fechada.

✅ **Já estão contadas — em DEV: 63 organizações sem administrador nenhum**, listadas pelo nome no
`audit_institutional_users.py`, e **zero** referências de membro penduradas. O número é de DEV; o de
produção é de quem tiver acesso, e é o mesmo comando. O que isto muda no ponto 4: deixa de ser uma
pergunta em aberto e passa a ser uma lista de reparação.

⚠️ **E ninguém contou as organizações que JÁ estão órfãs.** Esta guarda impede novas; não repara
antigas, e uma organização sem admin **não pode promover ninguém de dentro**.

### 11 — LEDG-2463 · As contas com conteúdo, e as 4 organizações com admin único *(operação)*

**Não é código — é uma decisão sobre organizações reais**, e é por isso que bloqueia o
LEDG-2431: qualquer regra de "recusar quando há conteúdo" tem de saber o que fazer com estes
casos antes de existir.

Das 120 contas com endereço sintético, **6 têm conteúdo ou pertença** (2 datasets, 0 reuses). E
os 4 que são admin são **o único administrador** da sua organização:

| Conta | Organização | datasets |
| --- | --- | --- |
| `saml-dde8d633@…` | **AGIT (Agência para a Gestão do Sistema…)** | **5** |
| `saml-9a4b1075@…` | **Instituto Nacional de Administração, I.P.** | 0 |
| `saml-64f971fb@…` | GREEN METRICS LDA | 0 |
| `saml-c0437c35@…` | EazyAL | 0 |

Organismos públicos administrados por uma conta **cujo endereço não existe**, que não recebe
correio, e que leva **404 em produção a cada login** (LEDG-2437). **Recusar ou apagar qualquer
uma deixa a organização órfã**, e a da AGIT leva 5 datasets consigo.

**O que o ticket tem de produzir:** quem passa a administrar cada uma das quatro, e por que via
— promover outro membro, ou associar a conta sintética ao seu dono real primeiro.

#### 🚩 Consultado a 2026-09-11: uma das duas vias não existe

**As quatro organizações têm exactamente UM membro — a própria conta sintética.** Não há
ninguém para promover, logo a pergunta *"quem passa a administrar"* **não tem candidatos**, e a
decisão que este ticket pedia à AMA estava a ser feita sobre uma opção inexistente.

| Organização | Membros | Papel do único membro | datasets |
| --- | --- | --- | --- |
| AGIT | **1** | `admin` — `saml-dde8d633@…` | **5** |
| Instituto Nacional de Administração, I.P. | **1** | `admin` — `saml-9a4b1075@…` | 0 |
| GREEN METRICS LDA | **1** | `admin` — `saml-64f971fb@…` | 0 |
| EazyAL | **1** | `admin` — `saml-c0437c35@…` | 0 |

✅ **A segunda via funciona, e o acesso nunca se perdeu.** As quatro contas têm `auth_nic` em
**hash 64-hex válido** e estão **activas** ⇒ a pessoa real entra por CMD e cai exactamente nessa
conta. O que a bloqueia é o ecrã de conclusão levar **404 em produção** — o LEDG-2437.

⇒ **Este ponto deixa de ser uma decisão sobre pessoas e passa a ser consequência do 2437.**
Reposto o ecrã, cada dono entra, dá um email real, e a organização mantém o administrador.
Nenhuma fica órfã e os 5 datasets da AGIT não se movem.

🚨 **A decisão da AMA que resta é mais estreita:** o que fazer se, passado o 2437, alguma destas
quatro pessoas **não voltar a entrar**. Aí sim é preciso um sysadmin — e é a única pergunta que
sobra deste ponto.

🔑 **E uma ligação que ninguém tinha feito:** as quatro têm `confirmed_at` **a nulo**. São parte
das 730 que o levantamento contou ⇒ além do 404, **nenhuma consegue recuperar a palavra-passe**.
Estão presas pelos dois lados, que é o padrão do LEDG-2474.

⚠️ **Medido em DEV**, onde as quatro contas existem com os mesmos endereços — o que sugere um
dump restaurado de produção, mas esta doc já teve de retratar uma conclusão tirada assim.
**Confirmar em produção antes de fechar o ticket**; é o mesmo comando de leitura.

### 12 — LEDG-2470 · Contas institucionais deixam de existir *(operação)*

Decisão de produto de 2026-09-10: publicar passa a ser sempre a partir de uma **conta pessoal**, em
nome próprio ou de uma **organização** de que a pessoa é membro.

✅ **A capacidade já existe, e isso reduz o ticket a uma migração.** Verificado: o mixin `Owned`
(`udata/core/owned.py:80-102`) tem `owner` e `organization`; o `check_organization_is_valid_for_current_user`
(`:62-73`) exige ser admin/editor; as permissões seguem o dono (`dataset/permissions.py:16-27`); e o
frontend **já tem o selector de produtor** (`DatasetWizardStep2.tsx:173-195`) com "conta pessoal" por
omissão. E `udata/features/transfer/` move `Dataset`/`Reuse`/`Dataservice` entre `User` e
`Organization` nos dois sentidos, com fluxo `pending`/`accepted`/`refused` e UI.

🚨 **"Conta institucional" NÃO existe como conceito no código.** Não há campo, flag, role nem tipo — o
docstring do `audit_institutional_users.py:1-22` di-lo: *"There is no 'institutional account' flag in
the user model... 'Institutional' is therefore a heuristic applied on top."* A heurística classifica
por local-part genérico (`geral@`, `dados@`, `sig@`), domínio `.gov.pt`, ou pertença a organização.
⇒ **Deixar de existir é uma operação sobre dados**, sobre uma população identificável só por convenção.

🔑 **E pode ser a causa das 120 contas sintéticas.** A hipótese das caixas partilhadas — um `geral@` já
ligado à identidade do colega nº 1, o colega nº 2 entra com o seu CMD, a asserção traz o mesmo
endereço, a conta não pode ser candidata, conta nova, endereço fabricado — tem a favor as **386 contas
com aparência institucional E link CMD** *(BD local, 2026-09-09)* — **600 em DEV, 2026-09-11**. ⚠️ **Continua não verificada, e é a primeira coisa a fazer
aqui**, porque decide se este ponto é uma limpeza ou a correcção da raiz do 13.

⚠️ **A heurística dá 722 contas (336 sem CMD, 386 com) na BD local, e 931 em DEV (331 sem CMD,
600 com) — e não são todas institucionais** — o critério
inclui "ser membro de uma organização", o que apanha contas pessoais legítimas. A lista tem de ser
**revista por humano** antes de qualquer acção.

### 13 — LEDG-2435 · Uma identidade, uma conta *(backend)*

Invariante: **uma identidade CMD/eIDAS → no máximo uma conta.** Cobre as duas classes:

- **(a) IdP sem email** → não criar a conta ainda: identidade em sessão, encaminhar para o
  registo. **Inclui desacoplar da flag** — **sem remover as guardas `nic_required`**.
- **(b) email já pertence a outra conta** → encaminhar para a associação.
  ⚠️ **Não pode ser desligado antes do LEDG-2431 existir.**
- **(c) capitalização diferente** → alinhar a verificação `exact` com a `ci`.
  ✅ **FEITA** — PR #279/#280, em `develop` e `tst`. Ver abaixo.

A fechar de passagem, por estarem na mesma zona: a guarda em falta na `/saml/migration/skip`, e
o alinhamento dos três defaults da flag.

#### A alínea (c), feita a 2026-09-11 *(as (a) e (b) continuam por fazer)*

O helper que já fazia a coisa certa saiu do plugin SAML para junto do `User`, e os **três**
sítios que perguntavam `exact` passaram a perguntar-lhe: o `_create_saml_user`, o `change_email`
e o `confirm_change_email`.

🔑 **O que este ponto ensinou, e não estava em lado nenhum:** o `flask_security` tem um
`find_user(case_insensitive=True)` nativo, e **já estava a ser usado em três sítios deste
ficheiro**. Adoptá-lo teria sido o caminho óbvio e **teria reintroduzido o bug** — é
`objects(email__iexact=…).first()`, sem preferência pelo exacto, logo devolve sempre a linha
mais recente. É o mesmo `.first()` que o ponto 9 provou não ser um sorteio. O docstring do
helper diz agora porquê, para ninguém o simplificar de volta.

🚨 **Consequência conhecida, aceite de olhos abertos.** Quem tem endereço com placeholder e o
seu endereço real está noutra grafia **deixa de o poder pôr**, e a resposta genérica do
LEDG-2456 faz com que não seja informado porquê. Antes recebia um duplicado; a recusa é
correcta, mas é uma recusa. **A população que fica presa é exactamente a do ponto 14** — mais
uma razão para o prazo dele.

⚠️ **E o ponto 2 corrige um caminho que hoje não corre em produção:** o `_create_saml_user` só
é alcançado no ramo `else` do `if _migration_enabled()`, e em PRD a flag está ligada. **Não se
afirma que isto fecha a origem dos duplicados medidos** — essa origem continua por explicar.

**Quatro portas ficaram abertas, todas descobertas aqui e nenhuma no ticket:** os três usos do
kwarg nativo (`saml_govpt.py:1724`, `:3403`, `:3551`), o `proconnect.py:91` — **um terceiro
provedor de login com exactamente o mesmo lookup `exact`** —, o `organization/api.py:651`
(quarto padrão, `email.lower()`, que só está correcto se tudo o que está guardado já estiver em
minúsculas, e não está), e a collation no índice único, que é a correcção estrutural e exige
fundir os duplicados primeiro.

### 14 — LEDG-2469 · Fundir os duplicados que já existem, e depois impedi-los na BD *(backend + operação)*

O 13 deixa de **criar** duplicados e o 12 faz o login **recusar** um identificador ambíguo. Nenhum
funde os **13 grupos, 26 contas** que já existem — pares de contas com **endereço real**, a mesma
pessoa com dois endereços a segundos de distância. ⇒ **Sem este ponto, o 12 tranca ~26 pessoas fora do
portal e não há mecanismo para as destrancar.**

🚨 **E não existe fusão de contas com conteúdo.** O `_merge_cmd_duplicates`
(`user/commands.py:159-262`) e o `merge_saml` (`:344`) fundem **só o identificador** e apagam o
duplicado — **não movem datasets, reuses, dataservices, discussões nem pertenças**. São seguros só
porque a população que tratam é tipicamente vazia (114 das 120 não têm nada); **os 13 grupos não têm
essa garantia, e ninguém a mediu.**

✅ **Agora está medida — em DEV.** O `audit_institutional_users.py` marca cada conta de cada grupo
com o que ela detém, e em DEV **nenhum dos 13 grupos tem conteúdo dos dois lados**; 4 grupos têm um
lado que **administra** uma organização e 2 têm um lado que é membro. Se isso se confirmar em
produção, mover o identificador chega para todos — mas as pertenças ainda têm de ir com ele, senão
fundir um lado administrador deixa uma organização órfã, que é exactamente o ponto 4 do LEDG-2468.
🚨 **Este número é de DEV**, e a medição em produção é de quem tem acesso lá. Até lá, aplicar o
`merge_saml` continua a poder apagar conteúdo.

✅ **A primitiva certa existe:** o `udata/features/transfer/` move um objecto de cada vez entre contas e
organizações. Uma fusão construída por cima dele orquestra transferência em vez de a inventar.

🚨 **E a alínea (c) do 13 acrescentou-lhe uma razão, a 2026-09-11.** Com o `change_email` a
tratar a variante de capitalização como endereço tomado, quem tem placeholder e o seu endereço
real numa grafia diferente **deixa de o poder pôr, e não é informado porquê** — a resposta é
genérica por desenho. A recusa é correcta; o que a desfaz é a fusão. ⇒ **Estas pessoas estão
presas até este ponto correr**, e somam-se às ~26 que o ponto 9 tranca.

🚨 **E o fecho é um índice que não existe.** O `extras.auth_nic` **não tem índice de unicidade nenhum**
— é um `MapField` (`user/models.py:123`) e os únicos índices declarados (`:141-149`) são o de texto, o
`-created_at` e o `slug`. A unicidade é aplicada **só em código**, e é exactamente por isso que os 13
grupos existem. ⚠️ **O índice só pode ser criado depois de os duplicados estarem fundidos** — é a razão
pela qual isto é um ponto e não dois.

⚠️ **Segunda unicidade a decidir, e é a raiz da classe 2:** o `email` é `unique=True` mas
**case-sensitive** (`models.py:76`, sem collation). Se o 13 decidir normalizar na escrita, o índice tem
de passar a insensível e as **401 contas com maiúsculas** migradas. Alinhar com o 13 antes de tocar.

### 15 — LEDG-2431 · Associar a uma conta tradicional existente *(a lacuna real)*

Três restrições obrigatórias: **prova de posse** do email de destino, **resposta genérica** (já
construída pelo ponto 2 — **estender, não reinventar**: o aviso ao dono da caixa passa a ser um
link que associa), e **tratar o conteúdo da conta de origem** (recusar ou transferir — decisão do
ponto 5). Entra pelo `_link_identity_and_login`.

É também aqui que entra a decisão 6: **um campo de email**, com o endereço do CMD pré-preenchido
quando existe, e a prova por link mantida mesmo nesse caso.

### 16 — LEDG-2438 · Estrangeiros: a identidade é o documento, não o NIC *(backend)* ✅ FEITO

Um cidadão estrangeiro com CMD **não tem NIC**. O portal pede o NIC como obrigatório e **não
pede** nenhum dos três atributos que o identificam:

| Atributo | Conteúdo |
| --- | --- |
| `http://interop.gov.pt/MDC/Cidadao/DocType` | `TR` título de residência, `PAS` passaporte, `CR` cartão de residência, `DR` certificado de autorização de residência |
| `http://interop.gov.pt/MDC/Cidadao/DocNationality` | ISO 3166-1 alpha-2. ⚠️ **Assume `PT`** nos títulos e cartões de residência |
| `http://interop.gov.pt/MDC/Cidadao/DocNumber` | Número do documento usado na criação da CMD |

Três armadilhas irreversíveis: a **composição do identificador fica congelada para sempre** (é
um hash); o `DocNumber` **sozinho não é único**, o que abriria a porta a duas pessoas
partilharem a mesma conta; e o identificador é **menos estável do que um NIC** — um documento
renovado muda de número, e a pessoa deixa de ser reconhecida pela sua própria conta.

**Porque vem antes do LEDG-2436:** os dois handlers ACS são idênticos, logo um estrangeiro com
CMD cai **exactamente** no bug do LEDG-2436 — mas a resposta certa é oposta. O LEDG-2436
recomenda **rejeitar** quem não tem identificador; um estrangeiro **tem**, só não lho pedimos.
Resolver este primeiro **tira os estrangeiros do âmbito do LEDG-2436**.

**O ponto 4 ajuda aqui:** o tipo declarado dá a verificação cruzada contra o que a asserção traz.

#### ✅ Feito a 2026-09-14 — PR #283, em `develop`. 222 testes (eram 207)

A composição escolhida, **congelada a partir do primeiro deploy**:

```
MDC/{DocType}/{DocNationality}/{DocNumber}      (os três em .strip().upper())
```

🚩 **O segmento `MDC` é o que impede um acesso indevido, e a razão não é óbvia.** `TR` e `CR`
são códigos **ISO 3166-1 alpha-2 válidos** (Turquia, Costa Rica), e um `PersonIdentifier` do
eIDAS tem a forma `<alpha2>/<alpha2>/<id>`. Com a nacionalidade forçada a `PT`, um titular de
título de residência comporia `TR/PT/123456` — **byte a byte o que um cidadão turco apresenta
por eIDAS**. Partilhariam conta, permanentemente e sem ninguém dar por isso. `MDC` tem três
caracteres e nunca pode ser um alpha-2.

🔑 **E a decisão central deste ponto já estava tomada no código, o que ninguém tinha visto.** O
docstring do `nic.py`, escrito no ponto 3, diz: *"the document type and nationality of a foreign
citizen's identity go in **sibling keys** when those attributes start arriving"*. E o
`constants.py` repetia-o. ⇒ O tipo e a nacionalidade foram para `extras.auth_doc_type` e
`extras.auth_doc_nationality`; **o número não**, porque identifica a pessoa e vive só dentro do
digest.

⚠️ **Isto não é o prefixo que o `nic.py` proíbe.** Aquela proibição é sobre o **valor
armazenado**, e o argumento dela é que os hashes já gravados não se recalculam. Este segmento
está na **pré-imagem**: o gravado continua a ser 64 hex e nenhum valor existente é tocado.

**O NIC ganha sempre que existe** — é a não-regressão inteira. Inverter a precedência
reescreveria a identidade de todos os nacionais cuja asserção também traga atributos de
documento, e há um teste que morre exactamente nessa mutação.

🚨 **A guarda que o auditor do plano obrigou a acrescentar:** a composição é gateada por
`DocType ∈ {TR, PAS, CR, DR}`. Sem ela, um **nacional** cuja asserção perdesse o NIC mas
trouxesse os três atributos receberia uma identidade composta nova em vez de cair no ramo
email/nome — o oposto do que este ponto existe para fazer.

⚠️ **E o que continua por provar:** os testes **mockam o pysaml2**, logo provam o nosso lado e
não o do IdP. Fica como condição de promoção: que o `isRequired="False"` no NIC é aceite e não
muda o ecrã de consentimento dos nacionais, o formato exacto dos três atributos, e **que uma
asserção de nacional não traz o trio completo com um `DocType` do conjunto** — a guarda assume
que não.

**Duas lições deste ponto, que valem para lá dele:**

1. 🚩 **Dois códigos de duas letras podem ser a mesma coisa noutro alfabeto.** `TR` e `CR` são
   tipos de documento **e** códigos ISO de país. Antes de compor um identificador, verificar se
   algum segmento pode ser lido como pertencendo a outro namespace.
2. 🚩 **Uma decisão de desenho pode já estar tomada num docstring.** Este ponto ia inventar onde
   guardar o tipo e a nacionalidade; o `nic.py` e o `constants.py` já o diziam desde o ponto 3.
   **Ler os comentários da zona antes de decidir** — este projecto escreve as razões, e não as
   reler é decidir duas vezes, mal.

🔻 **Consequência para o ponto 17:** os estrangeiros saem do âmbito do LEDG-2436. O que lá sobra
é o caso genuinamente mal formado, onde recusar é defensável — que era exactamente o argumento
para este vir primeiro.

### 17 — LEDG-2436 · Identidade sem identificador *(bug)* ⏸️ ESTACIONADO

#### Arrancado e parado a 2026-09-14, antes de haver código

O ticket tem uma instrução explícita: **"não escolher entre (a) recusar e (b) ligar pelo email
antes da resposta do LEDG-2288"**. O 2288 continua em **To Do**, atribuído a outra pessoa.

**Em vez de devolver a pergunta, tentei respondê-la com dados.** Medido em DEV, que está
actualizado:

| Medida | DEV, 2026-09-14 |
| --- | --- |
| Contas activas | 9 075 |
| Com `auth_provider=eidas` | **0** |
| Com `auth_provider=cmd` | **1** |
| Sem `auth_provider` | 9 074 |
| `saml-*` sem `auth_nic` | **0** |

🚩 **DEV não pode responder, e não é por falta de procurar.** O campo que diria quantos logins
eIDAS chegam sem `PersonIdentifier` foi criado no **ponto 3** e está praticamente vazio — uma
conta em 9 075. E a auditoria SAML não emite (LEDG-2371), logo também não há como observar em
produção **nem repartir "estrangeiro com CMD" de "eIDAS mal formado"**, que é exactamente a
repartição de que este ponto precisa.

**O custo de escolher às cegas, que é o que justifica parar:** a opção (a) arrisca recusar
cidadãos legítimos de um Estado-Membro cujo IdP omita o atributo; a (b) obriga a desfazer as
guardas `nic_required`, que existem por uma razão de segurança documentada.

✅ **O que o 16 já mudou aqui:** os estrangeiros com CMD saíram do âmbito. O que sobra é o caso
genuinamente mal formado, onde recusar é **mais** defensável do que era quando o ticket foi
escrito — mas continua a não ser decidível sem dados.

⇒ **O LEDG-2371 é o pré-requisito prático deste ponto**, e é a única coisa implementável que
resta com efeito na tabela.


⚠️ **Afeta os dois provedores**, não só o eIDAS: os handlers ACS são idênticos a partir do
`_find_or_create_saml_user`. **Uma correção num handler só deixa o outro intacto.**

Com a flag a `True`, **os três ramos do wizard recusam a identidade com `nic_required` 400** —
beco sem saída por desenho, e a recusa está no sítio errado. Com a flag a `False`, **cada login
cria uma conta nova**.

**A metade da multiplicação de contas não depende de decisão nenhuma** e pode sair com o
LEDG-2435. O que está bloqueado é só **a escolha entre rejeitar e ligar pelo email** — pelo
LEDG-2288 e pelo LEDG-2438.

### 18 — LEDG-2472 · Consolidação self-service *(full-stack)*

**A ideia:** quem entra numa conta tradicional vê um aviso de que no futuro só será possível ter
uma conta por pessoa, e quem tiver várias move os dados para a que quer manter. Facultativo,
enquanto o login por palavra-passe existir.

#### 🔑 O fluxo é ao contrário do que parece, e é isso que o torna seguro

A intuição é *"entro na conta principal e puxo os dados das outras"*. **O código não permite, e faz
bem.** O `TransferPermission` (`udata/features/transfer/permissions.py`) exige
`UserNeed(subject.owner.fs_uniquifier)` — só o **dono** pode iniciar a transferência — e o
`TransferResponsePermission` exige ser o **destinatário** para aceitar.

⇒ **Entrar na conta secundária → empurrar para a principal → a principal aceita.** Duas
propriedades vêm de graça: a **prova de posse é o próprio login** (só se move conteúdo de uma conta
em que se consegue entrar) e **ninguém recebe conteúdo sem consentir**.

#### ❓ "Como é que a app sabe qual é a principal e qual é a secundária?"

**Não sabe, e não deve decidir.** *Principal* não é um atributo da conta: é a resposta a *para onde
apontaste a transferência*. A conta de onde se empurra é, por esse acto, a secundária; a que aceita
é a principal. Não há nada a calcular — e qualquer heurística (a mais antiga, a com mais conteúdo,
a do último login) estaria errada para alguém. **Quem decide é a pessoa, e decide fazendo.**

#### 🚨 Mas nomear o destino é o furo, e a lista de pesquisa não serve

O `RecipientSelect.tsx` escolhe hoje o destinatário com `suggestUsers`, e essa lista **já está
endurecida**: o `user_suggestion_fields` (`udata/core/user/api_fields.py:204-220`) passa o email por
`member_email_with_visibility_check`, logo um não-admin vê **só o domínio**.

Bom contra enumeração, **inútil aqui**: não se distinguem duas contas próprias quando ambas
aparecem como *"Nome Apelido · @dominio.pt"* — e **dois homónimos são indistinguíveis**, logo picar
a errada envia o dataset para um estranho a quem só falta clicar em aceitar.

⇒ **O destino tem de ser uma conta cuja posse foi provada, não uma escolhida de uma lista.** E esse
mecanismo já existe, construído para isto: `sendMigrationLink()`
(`frontend/src/service/api/migration/index.ts`), com o comentário *"Takes no argument on purpose:
the recipient is never one the caller names."* — o backend envia o link para o endereço que já está
na conta, e **o clique é a designação**.

Há portanto estado a criar: um **destino confirmado por pessoa**. Mas estabelecido por prova,
**nunca inferido**.

#### 🚨 Sugerir "contas semelhantes" — rejeitado, por três razões

1. **É o oráculo de enumeração que este refinamento fechou duas vezes** (LEDG-2361 e LEDG-2456): um
   ecrã que diz *"estas também parecem suas"* ensina endereços a quem entrar em qualquer conta.
2. **A semelhança seria por nome ou email** — o fallback do `_merge_cmd_duplicates`, que o
   LEDG-2431 já registou como *não replicar*: **entre homónimos, é tomada de conta**.
3. **E é redundante:** como só se empurra de uma conta em que se entra, a pessoa **já sabe quais são
   as suas** — são aquelas em que consegue fazer login.

**Excepção legítima, e estreita:** duas contas com o mesmo `extras.auth_nic` são provadamente a
mesma pessoa. Mas é circular — o 12 (LEDG-2464) vai recusar esse login por ambíguo, logo a pessoa
não entra em nenhuma. **São os 13 grupos, e por isso são fusão operacional no 14, não self-service.**

#### ⚠️ A janela fecha — é a razão de estar antes do 19

Depois da obrigatoriedade, quem perdeu acesso ao email de uma conta secundária **já não entra nela**,
logo já não pode empurrar o conteúdo, que fica órfão sem via self-service. Fazer o 19 primeiro
converte um problema self-service num problema de suporte, conta a conta.

#### Dependências

**Requisito 4 do 14** (LEDG-2469) se oferecer *"mover tudo"* — é lá que nasce a capacidade repetível
de fundir contas com conteúdo. Sem ela, este ponto só pode guiar a pessoa pela UI objecto a objecto:
versão mais pobre, mas entregável. **E do 9** (LEDG-2468) se a conta secundária puder ser apagada no
fim — o `mark_as_deleted` não verifica se ela é administradora única de alguma organização.

### 19 — LEDG-2471 · Descontinuar o login por email e palavra-passe *(full-stack)*

O LEDG-1277 (ponto 19) é o dono da decisão e já especifica a versão suave: *"se tiver e-mail e
palavra-passe, consigo aceder mas recebo mensagem informativa em como devo aceder via
autenticacao.gov"*, com um TODO aberto — *"detalhar comportamento caso tenham e-mail e palavra-passe"*.
Este ponto é o **levantamento e o gate**, porque há coisas que dependem da palavra-passe que não são o
ecrã de login.

🚨 **As duas que quebram primeiro, e nenhuma é UI:**

1. **O OAuth2 `PasswordGrant` está registado e activo** (`udata/api/oauth2.py:255-260`, autentica em
   `:398` por `verify_password`). **É autenticação de API por email+palavra-passe**, e desligar o
   formulário no frontend não a afecta — é o tipo de dependência que se descobre em produção.
2. **O CLI `udata user create` exige palavra-passe** (`user/commands.py:30-59`), e é assim que se cria o
   primeiro sysadmin de um ambiente novo.

✅ **Duas coisas já estão do lado certo:** a arquitectura **já tolera contas sem palavra-passe**
(`saml_govpt.py:1699`: *"the account may have been created through SAML and have no usable password"*),
e a prova por palavra-passe **já não completa a associação** (`:3068-3080`) — identifica a conta e envia
o link.

🚨 **E a armadilha tem precedente:** não existe flag para desligar o login tradicional, e **há um teste
que impede reintroduzir uma no frontend** (`migration-flag-guard.test.ts`), porque foi isso que causou
o LEDG-2432. ⇒ **A descontinuação é decidida no backend e por conta, nunca por uma flag lida no
frontend.**

**Pré-requisitos já conhecidos:** o 15 (associar conta tradicional — o próprio ticket diz que o 1277
não deve ser activado antes), o LEDG-2437 (o 404 em produção), o **LEDG-2467** (a recuperação de
palavra-passe: enquanto o login por password existir, é a via de quem não tem CMD) e o 17 (quem não
consegue ligar CMD ficaria sem entrada nenhuma).

### 20 — LEDG-1277 · Obrigatoriedade do Autenticação.gov *(produto)*

O fim do arco, e o único ponto que já estava *In Progress* antes deste refinamento. ⚠️ **Não activar
antes do 18**, e o LEDG-2431 diz porquê em texto: enquanto a migração é opcional, uma conta com
endereço sintético é um problema de **contactabilidade**; quando passar a obrigatória, passa a ser de
**perda de acesso irreversível** — o endereço não existe, a recuperação de palavra-passe é impossível,
e se a pessoa perder o acesso ao meio Gov não há canal para a reidentificar.

### — LEDG-2467 · Recuperação de palavra-passe *(fora da decomposição)*

Não é CMD/eIDAS, logo não leva número — mas é **pré-requisito do 18**.

**Duas hipóteses óbvias, refutadas.** ❌ Não é busca exacta por email: o `ForgotPasswordForm` do
flask_security usa `find_user(case_insensitive=...)` com o `SECURITY_USER_IDENTITY_ATTRIBUTES`, que tem
`case_insensitive: True` por omissão e o udata não sobrepõe — **este fluxo é case-insensitive**, ao
contrário das quatro convenções da pergunta 5. ❌ E o `SEND_MAIL` tem default `True` no `udata.cfg`;
só os perfis `Testing` e `Debug` o fixam a `False`.

🚨 **A causa provável é por desenho:** `SECURITY_RETURN_GENERIC_RESPONSES = True` (`settings.py:170`)
suprime os erros do formulário, e o frontend trata **qualquer 200 como sucesso**
(`auth/reset-password/route.ts:55-58`). ⇒ **Quatro razões distintas — conta inactiva, não confirmada,
apagada, email inexistente — produzem a mesma UI de "enviámos-lhe uma mensagem".** Correcto em
anti-enumeração, indistinguível de uma avaria.

✅ **E a via de diagnóstico existe:** o `AuditMailUtil` escreve `mail_dispatch kind="reset_instructions"
recipient=m*** result=sent|error`, legível em `/admin/system/logs`.

#### 🎯 RESOLVIDO a 2026-09-10 — e a causa não era nenhuma das hipóteses acima

**Os mails do flask_security saíam de `webmaster@udata`**, um domínio que não é sequer um TLD válido.
Confirmado num mail **entregue**, não inferido.

A cadeia: o `app.log` do DEV tinha `mail_dispatch kind="reset_instructions" … result=sent error=-`,
logo **não houve recusa de formulário** (uma recusa não emite linha nenhuma) e **não houve erro de
envio**. E o remetente estava congelado, porque o `udata/settings.py` fazia, dentro da mesma classe:

```python
line  72:  MAIL_DEFAULT_SENDER   = "webmaster@udata"
line 161:  SECURITY_EMAIL_SENDER = MAIL_DEFAULT_SENDER   # copia o VALOR de classe
```

O `=` no corpo da classe **copia, não liga**. O `.env` sobrepõe só o `MAIL_DEFAULT_SENDER`, logo as
duas chaves ficavam sem relação. E o default que essa linha substituiu era
`LocalProxy(lambda: current_app.config.get("MAIL_DEFAULT_SENDER", ...))` — **resolução lazy, que
daria o valor certo**. ⇒ A correcção foi **apagar a linha**, não sobrepô-la.

⚠️ **A linha é upstream** (PR #436 do udata original, 2016), não da AMA — logo o comentário foi
mantido em 2 linhas, deixando o diff em **−1/+2**. A guarda contra reintrodução é o teste
(`SecurityMailSenderTest`), que vive em ficheiro nosso. **É um bug upstream e vale reportá-lo.**

**Afectava os seis mails do flask_security**, não só o reset: recuperação e alteração de palavra-passe,
registo, confirmação de endereço e instruções de login. Os mails enviados pelo código do udata
(`auth/views.py`) já usavam o remetente correcto — era essa a assimetria visível na caixa de correio.

✅ **Verificado em DEV depois do deploy:** mail recebido de `noreply.dados.gov@arte.gov.pt`.

🚩 **E dois bugs encontrados pelo caminho:**
* o `SEND_MAIL` **não era desligável** — o `udata.cfg` usava `_env` (string crua), logo `SEND_MAIL=False`
  dava `"False"`, que é truthy. Corrigido para `_env_bool`. ✅ **Confirmado que a variável não existe em
  `.env` nenhum**, logo o default `True` aplica-se nos quatro e a alteração não muda comportamento;
* o subject hardcoded em português do `reset_instructions()` é **código morto no envio** — o assunto
  real vem do `SECURITY_EMAIL_SUBJECT_PASSWORD_RESET`, traduzido. ❌ **Correcção ao que aqui estava
  escrito antes:** não é um assunto mal traduzido, é um campo que ninguém lê.

⚠️ **O QUE FICA ABERTO, e é o que este ponto tinha de original:** as **quatro razões de recusa
indistinguíveis** continuam lá. Não eram a causa deste relato, mas são um problema real — e ficaram
**mais graves** com o ponto 7: uma conta inactiva passou a ser recusada no login SAML *e* continua a
receber "enviado" sem envio na recuperação, logo **não tem via de entrada nenhuma nem explicação**.
Precisa de decisão de produto, e o precedente a estudar é o do LEDG-2456: **a resposta no browser é
igual nos dois casos, e é o conteúdo do email que difere.**

---

## 🔎 Encontrado na mesma investigação, e FORA deste refinamento

O diagnóstico do LEDG-2467 passou pelos logs e pela configuração dos ambientes, e apanhou coisas
que **não são de autenticação**. Ficam registadas aqui para não se perderem, e **deliberadamente
fora da tabela de decomposição** — meter trabalho não-CMD/eIDAS nessa tabela dilui-a.

### LEDG-2475 · O formulário de Ajuda e contactos devolvia 400 em PPR e PRD ✅ RESOLVIDO

✅ **Confirmado a 2026-09-11: era a chave, como o diagnóstico dizia.** O par site/secret estava
trocado em PPR/PRD — o browser apresentava um token do registo `6LfoyIMt` e o servidor validava-o
contra o segredo de outro registo, e o Google respondia `success: false`. Corrigido; o envio
funciona.

🔑 **O que provou a causa foi o tamanho da resposta, e vale como método.** Os 54 bytes
distinguiam `Invalid reCAPTCHA` (o Google respondeu e rejeitou) de `{"errors": {}}` com 14 bytes
(falha de rede a contactar o Google) e de `reCAPTCHA validation required` com 66 (token ausente).
Sem essa medição, a hipótese benigna — "PPR/PRD não alcançam o `siteverify`" — era indistinguível
da real, e teria mandado investigar rede em vez de configuração.

⚠️ **Fica por confirmar o resto do ticket:** se os `.mo` de português estão compilados no deploy
de PPR/PRD (a resposta veio em inglês, e a tradução existe), e o `MAIL_DEFAULT_RECEIVER` nesses
dois ambientes — em DEV está desviado para um endereço pessoal com um `# trocar temporariamente`.

#### O diagnóstico original, mantido por ser o registo de como se chegou lá

`POST /api/1/site/contact/` → **400**, com `Content-Length: 54`. Em DEV e TST devolve **204** e a
mensagem chega. O `udata.cfg` é versionado e igual para todos, logo a diferença está na
configuração de ambiente.

🎯 **Não é problema de correio — falha antes de qualquer envio.** O `SupportContactForm.validate`
(`core/site/forms.py:46`) chama o `validate_recaptcha()` primeiro e devolve `False` de imediato.

E o tamanho da resposta isola a causa. O corpo tem o formato `{"errors": {…}}`, e **só uma
mensagem dá 54 bytes** (referências medidas contra o DEV, com uma sonda que falha na validação e
por isso não envia mail):

| Bytes | Corpo | Significado |
| --- | --- | --- |
| **54** | `{"errors": {"recaptcha_token": ["Invalid reCAPTCHA"]}}` | 🎯 o observado em PRD |
| 60 | a mesma em português | — |
| 66 | `reCAPTCHA validation required` | token ausente |
| **14** | `{"errors": {}}` | falha de **rede** ao contactar o Google |

⇒ **O Google respondeu e rejeitou o token.** Exclui a hipótese benigna: sem alcance ao
`siteverify`, o `except RequestException` (`auth/forms.py:56-58`) devolvia `False` **sem pôr
mensagem no campo** → 14 bytes.

🎯 **CAUSA PROVADA a 2026-09-11 — o par de chaves está trocado.** Já não é hipótese: as site keys
foram extraídas dos bundles JS públicos de cada ambiente, e o segredo confirmado na configuração.

| Ambiente | Site key (JS público) | Secret (config) | Bate? |
| --- | --- | --- | --- |
| DEV | `6Lcimo4s…` | `6Lcimo4s…` | ✅ sim — e funciona |
| PPR | **`6LfoyIMt…`** | **`6Lcimo4s…`** | 🚨 **NÃO** |
| PRD | **`6LfoyIMt…`** | por confirmar | 🚨 sintoma idêntico |

⇒ O frontend pede tokens a um registo e o backend valida-os com o segredo de outro. **Não é código —
é uma variável de ambiente.** Encaixa numa pendência já registada do lote VULN-2092: *"falta re-teste
Devoteam + chaves reCAPTCHA"*.

❌ **Hipótese de um WAF à frente, excluída.** Há infraestrutura — em PRD os cabeçalhos mostram
**Dynatrace** (`X-OneAgent-JS-Injection`, `X-ruxit-JS-Agent`) e os cabeçalhos de segurança vêm
duplicados; em PPR é `nginx` simples. Mas o **tamanho da resposta** decide: um WAF a bloquear não
devolveria o formato de erro do udata, e um WAF a **retirar** o token daria `reCAPTCHA validation
required` (66 bytes). O observado é `Invalid reCAPTCHA` (54) ⇒ **o token chegou intacto e foi o Google
que o rejeitou.** O Dynatrace é monitorização, não filtragem.

⚠️ **A correcção é pôr o segredo do registo `6LfoyIMt`, não trocar a site key** — o `6Lcimo4s` é o
registo de desenvolvimento e não está autorizado para os domínios públicos.

### 🚩 As traduções não fazem efeito em PPR/PRD

Os 54 bytes são a mensagem **em inglês**. A tradução existe
(`translations/pt/LC_MESSAGES/udata.po:2826` → `reCAPTCHA inválido`) e daria 60. O DEV responde em
português; o PRD não.

⇒ Afecta **todas** as mensagens de erro da API nesses ambientes. Consistente com a matriz de
branches acima: o i18n do LEDG-2456 está em `develop` e `tst`, não em `ppr`/`main`. **Verificar se
os `.mo` estão compilados no deploy** — está dentro do LEDG-2475 como verificação.

### ⚠️ E um desvio temporário a não esquecer

O `.env` de DEV tem o `MAIL_DEFAULT_RECEIVER` apontado para um endereço pessoal, com o comentário
`# trocar temporariamente`. É a caixa onde o formulário de contacto aterra. **Vale confirmar que o
mesmo desvio não ficou noutro ambiente.**

## 🛑 LEDG-2437 — retido pela decisão de promoção

**Não tem código.** Fecha quando a promoção `ppr → main` do frontend for feita — e essa, **por
decisão de 2026-09-08, só acontece quando toda a reformulação estiver completa e validada**.

Técnicamente **não depende de nenhum dos pontos 1 a 19**, mas a decisão de promover em bloco
prevalece.

Verificado que o `7d5c9b50` **não está em `ppr`**, logo a promoção traz a página que falta em
produção e **não** traz a regressão do LEDG-2432.

Foram avaliados dois hotfixes e **descartados**: qualquer um cria um commit só em `main` que
depois tem de ser reconciliado — acrescentaria uma divergência entre branches para corrigir um
problema causado por divergência entre branches.

> 🚨 **Risco aceite, e agora por mais tempo:** as contas com endereço sintético continuam a
> receber **404 em produção, em cada login**, desde ~2026-08-25 e até a reformulação completa
> subir a `main`. **É a consequência direta da decisão de promoção em bloco**, e fica escrito
> para ser uma escolha e não um esquecimento.
>
> 🔑 **E o 2437 vale mais do que se julgava, descoberto a 2026-09-11.** Não é só um 404
> incómodo: é **o que resolve o ponto 11**. As 4 organizações com admin único não têm ninguém
> para promover — têm um membro cada, a própria conta sintética — mas essas contas têm
> `auth_nic` válido e estão activas, logo os donos **entram por CMD e caem na conta certa**. O
> único passo que lhes falta é o ecrã de conclusão, que é exactamente o que o 2437 repõe.
> ⇒ **Enquanto o 2437 não subir, quatro organismos — um deles com 5 datasets — não têm forma
> de recuperar o seu administrador**, e o ponto 11 não pode fechar.

---

## Cobertura de testes

- `udata/tests/frontend/test_saml.py` — **149 testes** de base, **160 depois do LEDG-2433** (as
  duas classes do provedor), **169 depois do LEDG-2457** (`SAMLDeclaredCitizenTypeTest`),
  **183 depois do LEDG-2462** (`SAMLTrackableLoginFieldsTest` + o teste do clique no link),
  **194 depois do LEDG-2465** (`SAMLInactiveAccountRefusalTest` + 3 no clique do link),
  **198 depois do LEDG-2466** (`SAMLConfirmedAtPersistenceTest`), **204 depois do LEDG-2464**
  (`SAMLAmbiguousIdentityTest`), **207 depois da alínea (c) do LEDG-2435**
  (`SAMLCaseVariantAddressTest`) e **222 depois do LEDG-2438** (quatro classes novas, mais os
  três atributos de documento acrescentados aos dois helpers que constroem as asserções).
  Medido em `develop` com `pytest --collect-only`.
  🚩 **O LEDG-2438 fechou a lacuna mais antiga deste ficheiro sem ser esse o objectivo:**
  `grep RequestedAttribute` nos testes devolvia **zero**. Os 207 cobriam todos os ramos do que
  se faz com a resposta do IdP e **nenhum da pergunta** — que era precisamente a única coisa
  que o ponto 16 mudava para os nacionais.
  🚩 **E nove mutações, todas apanhadas, duas delas por testes diferentes:** voltar a `user_nic`
  no resolvedor mata só o teste dos três logins; deixar o documento ganhar ao NIC mata só a
  não-regressão do nacional. São as duas metades da mesma decisão, e precisavam de duas provas.
  ⚠️ **Os totais medidos são a fonte, não os resumos por ticket.** O resumo do 2465 dizia
  "13 testes novos" e o real é **11** (194 − 183) — corrigido. Vale reverificar o do 2462 pela
  mesma via, porque 183 − 169 dá **14** e o resumo dele também diz 13.
- `udata/core/user/tests/test_user_model.py` — desde o LEDG-2435, **4 testes** do
  `find_user_by_email_ci`, no sítio onde o helper passou a viver.
  🚩 **A mutação que os justifica:** retirar a preferência pelo match exacto mata **exactamente
  um** deles. Sem esse teste, o helper podia ser simplificado para `.first()` sem a suite dizer
  nada — que é precisamente o que o `find_user(case_insensitive=True)` do flask_security faz.
- `udata/tests/frontend/test_auth.py` — desde o LEDG-2435, **4 testes** da variante de
  capitalização no `change_email`.
  🚩 **Um deles NÃO morre com mutação nenhuma, de propósito:** o de indistinguibilidade prova a
  **ausência** de um oráculo, que o bug não criava. Por isso tem ao lado um que morre — um prova
  que o chamador não distingue os ramos, o outro que o ramo certo correu. Confundir os dois é a
  lacuna 7 outra vez.
- `udata/tests/api/test_organizations_api.py` — **101 testes**, **6 deles** acrescentados pelo
  LEDG-2468 para a guarda do último administrador.
  🚩 **Uma mutação provou que faltava um dos seis:** retirar a condição do papel novo
  (`form.role.data != "admin"`) deixava a suite toda verde, ou seja, ninguém testava a diferença
  entre *alterar o último admin* e *tirar-lhe o papel*. O teste que faltava passou a existir, e a
  mesma mutação passou a matar exactamente esse.
- `udata/tests/api/test_security_api.py` — desde o LEDG-2467, fixa o **remetente** dos mails do
  flask_security. ⚠️ **O teste tem de fazer o `MAIL_DEFAULT_SENDER` e o `SECURITY_EMAIL_SENDER`
  DIFERIR**, senão passa com e sem o bug — é a lacuna 7 outra vez.
- `udata/tests/test_legacy_vulns_auth_enumeration.py` — regressão de enumeração. **O LEDG-2456
  acrescentou a classe que faltava** para o change-email: o ficheiro tinha uma por cada vetor da
  auditoria e nenhuma para este, que é a razão pela qual a fuga sobreviveu.
- `udata/tests/test_auth_mails.py` — desde o LEDG-2456, fixa que os e-mails de autenticação têm
  tradução pt.
- Frontend: `src/components/login/__tests__/` — **93 testes, 6 ficheiros** (eram 37 antes do
  LEDG-2457). Medido em `develop`.
  ⚠️ **Só existem em `develop` e `tst`.**

Qualquer alteração deve manter estes verdes, **em particular os de enumeração**.

### Sete lacunas a fechar

Deixaram passar todos os problemas deste refinamento:

1. **Testes nos dois estados da flag**, em todos os pontos — obrigatório, agora que se sabe que
   os três defaults não concordam.
2. **Testes de logins repetidos** da mesma identidade, a afirmar que o número de contas não
   aumenta. Testar um login só nunca revelaria a classe 1.
   ⚠️ **O LEDG-2462 acrescentou testes de segundo login**, mas para os campos de sessão — não
   para a contagem de contas. **Continua aberta.**
3. **Um teste com capitalização diferente** (`Maria@x.pt` vs `maria@x.pt`). Sem ele a classe 2
   sobrevive a qualquer correção e não aparece em contagem nenhuma.
   🚨 **Deixou de ser hipótese:** o levantamento encontrou `Pablolira@hotmail.com` e
   `pablolira@hotmail.com`, duas contas criadas a 49 segundos de distância. A classe 2 existe
   em dados reais. **Ainda aberta** — é trabalho do LEDG-2435.
4. **Os casos do tronco comum testados nos DOIS handlers.** Tudo o que está depois do
   `_find_or_create_saml_user` é partilhado, mas um teste só no eIDAS dá a impressão de cobertura
   que não existe para o CMD, e vice-versa.
   ✅ O LEDG-2433 passou a cobrir os dois em cada caso novo, precisamente por isto.
5. **Nada testa a coerência entre os dois repos.** As duas regressões passaram por todos os
   testes de cada repo, porque cada metade está correcta isoladamente. Um E2E que faça login CMD
   com endereço sintético e verifique que o destino do redirect existe teria apanhado o
   LEDG-2437.
6. **🌐 Nada afirmava que uma string de autenticação visível ao utilizador tem tradução pt** — e
   por isso um e-mail inteiro em inglês passou meses sem ser apanhado. Um msgid sem entrada no
   catálogo **não falha**: o `gettext` devolve o próprio msgid. O LEDG-2456 fechou-a para o
   conjunto que estava mal.
7. **Um caminho de escrita implementado por simetria não fica provado pela simetria.** ✅ FECHADA.
   Das quatro escritas de `auth_citizen_declared`, a do link por email era a única sem teste — e
   é a única que **não pode** usar a sessão, porque o clique chega sem nenhuma; o valor viaja no
   registo do link. Foi escrita a espelhar o `provider`, cujo teste equivalente já existia, e é
   o caminho de quem entra por CMD sem email na asserção — nem raro, nem canto. Apareceu porque
   **alguém a exercitou à mão**, não porque a suite se queixasse. Fechada com dois testes,
   provados por mutação nos dois sentidos.

   🚨 **E voltou a acontecer no LEDG-2462, em forma nova — vale mais do que a primeira.** Ali a
   lacuna não era um caminho sem teste: era **o teste a substituir a coisa que decide**. Nove
   dos onze testes faziam `patch` do `login_user` com um mock **sempre truthy**, logo nenhum
   exercitava o ramo verdadeiro da guarda com a função real. E o teste da própria guarda
   apontava para um `User.save` que deixara de ser chamado, ou seja **passava sem exercitar
   nada**. Ambos foram apanhados pela revisão adversarial, não pela suite.

   ⚠️ **A lição, generalizada:** onde a suite faz `patch` da função que toma a decisão, ninguém
   está a testar a decisão — e o ficheiro tem uma razão legítima para fazer esse patch (o
   `current_user` fica preso depois de um login real), o que torna o hábito invisível. **Sempre
   que se acrescentar um caminho que depende do retorno de uma função patcheada, é preciso um
   teste que a deixe correr a sério.**

---

## Documentos relacionados

- [`migration-plan-of-legacy-accounts-to-CMD-ticket-40.md`](../migration-plan-of-legacy-accounts-to-CMD-ticket-40.md)
  — o plano original da migração de contas legadas, com as divergências da implementação final.
- [`login-workflow.md`](../login-workflow.md) — o fluxo de autenticação entre frontend e backend.
- [`saml-account-merge.md`](../saml-account-merge.md) — a fusão de contas SAML.
- [`profile-email-change.md`](../profile-email-change.md) — a alteração de email, que o LEDG-2456
  modificou.
- [`translations-workflow.md`](../translations-workflow.md) — o catálogo pt, cuja lacuna silenciosa
  o LEDG-2456 expôs.
