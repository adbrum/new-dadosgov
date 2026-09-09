# Revisão da autenticação do portal — LEDG-2430

> **Este documento é o espelho do [LEDG-2430](https://ticapp.atlassian.net/browse/LEDG-2430).**
>
> É a fonte no repositório para quem trabalha este refinamento sem abrir o Jira. **Sempre que o
> ticket for alterado, este ficheiro é alterado no mesmo passo** — e o contrário também. Se
> divergirem, **o Jira prevalece** e este ficheiro está desatualizado, porque é lá que as
> decisões são tomadas e comentadas.
>
> **Última sincronização: 2026-09-08.**

---

## 🛑 DECISÃO DE PROMOÇÃO: nada sai de `tst` até a reformulação estar completa

Decidido a **2026-09-08**: as promoções `tst → ppr` e `ppr → main` só acontecem quando **toda**
a reformulação CMD/eIDAS estiver feita e validada. **Não se promove por ticket.**

- O `tst` vai **acumular os pontos todos** antes de subir, logo a promoção final será grande. É
  o custo aceite — e a alternativa (promover ticket a ticket) tem o risco de deixar o fluxo
  **meio-migrado** em produção, que é exactamente o que produziu as duas regressões descritas
  abaixo.
  📊 **Já medido, com os pontos 1 a 4 feitos:** `tst → ppr` espera **85 commits no backend** e
  **80 no frontend** (2026-09-08). Uma parte é anterior a este refinamento e já lá estava; o
  ponto é que o número não vai descer, e a promoção final não será revisível commit a commit.
  **Registar aqui a contagem em cada ponto que entra** dá a curva, e a curva é o argumento a
  usar se a decisão tiver de ser reavaliada.
- ⚠️ **O LEDG-2437 deixa de ser uma ação de release independente.** Fechava com um
  `ppr → main` do frontend a qualquer momento; passa a esperar pelo conjunto. **O 404 em
  produção mantém-se até lá** — risco aceite, e agora por mais tempo do que o previsto.
- Quanto mais o `tst` acumular, **mais importa testar lá cada ponto à medida que entra**, e não
  só no fim. Uma regressão descoberta na promoção final é muito mais caro de localizar entre
  nove pontos do que entre um.

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

O plugin SAML importa o `login_user` do **`flask_login`** ([saml_govpt.py:31](backend/udata/auth/saml/saml_plugin/saml_govpt.py#L31)),
que **não escreve** nenhum destes campos; quem os escreve é o `login_user` do
`flask_security`, que não é importado. E os dados confirmam a consequência, por data de
criação das contas **com** `auth_nic`:

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
2. **É um defeito por si só**, e não está em nenhum dos nove pontos: qualquer lógica que
   dependa de inactividade — limpezas, notificações, relatórios de utilização — trata
   **todos** os utilizadores de CMD/eIDAS recentes como dormentes. Merece ticket próprio.

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
- **A auditoria SAML não emite em produção:** o `_audit_saml` escreve para um logger fora da
  árvore `udata.*` (LEDG-2371). **Tudo o que está acima pode estar a acontecer há meses sem
  deixar rasto.**
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

## Decomposição, pela ordem de implementação

> 🔄 **Reordenado a 2026-09-09, com os dados de produção.** A ordem anterior assumia que o
> problema eram as ~200 contas sintéticas e que essas contas eram poucas pessoas com muitas
> contas cada. **Os dados dizem o contrário** (120 contas = 120 pessoas, e só 6 com conteúdo),
> o que simplifica o 2435, esvazia a justificação do 2436 por esta via, e faz aparecer quatro
> problemas que não estavam em ponto nenhum.

| # | Ticket | O quê | Onde | Feito? | Dependência |
| --- | --- | --- | --- | --- | --- |
| **1** | LEDG-2432 | Repor o login por email e palavra-passe | Frontend | ✅ **Sim** — em `develop` e `tst` | 🚨 Regressão; desbloqueou o `tst → ppr` |
| **2** | LEDG-2456 | Fuga de existência de conta **+ e-mails em inglês** | Backend | ✅ **Sim** — em `develop` e `tst` | Nenhuma — e torna o 10 menor |
| **3** | LEDG-2433 | Campo do método de autenticação (CMD/eIDAS) | Backend | ✅ **Sim** — 6 commits, suite completa verde; em `develop` e `tst` | Nenhuma — aditivo |
| **4** | LEDG-2457 | Tipo de cidadão **declarado** (nacional/estrangeiro) | Full-stack | ✅ **Sim** — 5 commits nos dois repos; em `develop` e `tst` | **Depende do 3** |
| 5 | LEDG-2434 | Levantamento — **falta PPR e as perguntas 2/3/4 fora de PRD** | Spike | 🟡 Parcial | Nenhuma |
| 6 | **LEDG-2462** | **Campos de sessão vazios no login SAML** (`last_login_at`, `current_login_at`, `login_count`, `last_login_ip`) | Backend | ❌ Não | Nenhuma. Paralelo ao 5 — **este é código, o 5 é humano** |
| 7 | **LEDG-2463** | **As 6 contas com conteúdo, 4 delas admin ÚNICO** — plano nomeado | Operação | ❌ Não | **Pré-requisito do LEDG-2431.** Bloqueia qualquer recusa ou limpeza |
| 8 | **LEDG-2464** | **Login ambíguo:** identificador duplicado resolvido por `.first()` | Backend | ❌ Não | Nenhuma — verificado no código, independente das contas sintéticas |
| 9 | LEDG-2435 | **Uma identidade, uma conta** — as duas classes de duplicado | Backend | ❌ Não | Depende do **5**. 🟢 **Mais simples do que desenhado:** reconciliação é 1:1 |
| 10 | LEDG-2431 | Associar a uma conta tradicional existente | Full-stack | ❌ Não | Depende do **2**, **5**, **7** e **9**. ✅ **Desenho decidido pelos dados: recusar quando há conteúdo** |
| 11 | LEDG-2438 | **Estrangeiros: identidade por documento em vez de NIC** | Backend | ❌ Não | Confirmar sobreposição com LEDG-2288 |
| 12 | LEDG-2436 | Identidade sem identificador (eIDAS **e** CMD) | Backend | ❌ Não | **Depende do 11**. 🔻 **Despromovido:** zero casos nas 120; só se justifica pelo eIDAS |
| — | ~~NOVO-D~~ | ~~**Organizações AGIT duplicadas** (3 registos)~~ | — | ❌ **Não se cria** | A consulta desfez a suspeita — ver acima |

**Próximo a implementar:** o **5** (LEDG-2434). Os pontos 1 a 4 estão em `develop` e `tst`, e
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
> só aqui. Foi aplicado aos quatro (LEDG-2431, LEDG-2433, LEDG-2434, LEDG-2435) em 2026-09-08.

O **LEDG-2371** é pré-requisito prático de tudo isto: sem ele nada é mensurável — e no caso do
8/9 é a **única** forma de saber quantos casos são estrangeiros com CMD e quantos são eIDAS mal
formado.

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

### 9 — LEDG-2435 · Uma identidade, uma conta *(backend)*

Invariante: **uma identidade CMD/eIDAS → no máximo uma conta.** Cobre as duas classes:

- **(a) IdP sem email** → não criar a conta ainda: identidade em sessão, encaminhar para o
  registo. **Inclui desacoplar da flag** — **sem remover as guardas `nic_required`**.
- **(b) email já pertence a outra conta** → encaminhar para a associação.
  ⚠️ **Não pode ser desligado antes do LEDG-2431 existir.**
- **(c) capitalização diferente** → alinhar a verificação `exact` com a `ci`.
  ⚠️ **O mesmo problema existe no `change_email`**, e o LEDG-2456 deixou-o registado como achado
  rejeitado para este ponto o apanhar. **Cobrir os dois sítios.**

A fechar de passagem, por estarem na mesma zona: a guarda em falta na `/saml/migration/skip`, e
o alinhamento dos três defaults da flag.

### 10 — LEDG-2431 · Associar a uma conta tradicional existente *(a lacuna real)*

Três restrições obrigatórias: **prova de posse** do email de destino, **resposta genérica** (já
construída pelo ponto 2 — **estender, não reinventar**: o aviso ao dono da caixa passa a ser um
link que associa), e **tratar o conteúdo da conta de origem** (recusar ou transferir — decisão do
ponto 5). Entra pelo `_link_identity_and_login`.

É também aqui que entra a decisão 6: **um campo de email**, com o endereço do CMD pré-preenchido
quando existe, e a prova por link mantida mesmo nesse caso.

### 11 — LEDG-2438 · Estrangeiros: a identidade é o documento, não o NIC *(backend)*

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

### 12 — LEDG-2436 · Identidade sem identificador *(bug)*

⚠️ **Afeta os dois provedores**, não só o eIDAS: os handlers ACS são idênticos a partir do
`_find_or_create_saml_user`. **Uma correção num handler só deixa o outro intacto.**

Com a flag a `True`, **os três ramos do wizard recusam a identidade com `nic_required` 400** —
beco sem saída por desenho, e a recusa está no sítio errado. Com a flag a `False`, **cada login
cria uma conta nova**.

**A metade da multiplicação de contas não depende de decisão nenhuma** e pode sair com o
LEDG-2435. O que está bloqueado é só **a escolha entre rejeitar e ligar pelo email** — pelo
LEDG-2288 e pelo LEDG-2438.

---

## 🛑 LEDG-2437 — retido pela decisão de promoção

**Não tem código.** Fecha quando a promoção `ppr → main` do frontend for feita — e essa, **por
decisão de 2026-09-08, só acontece quando toda a reformulação estiver completa e validada**.

Técnicamente **não depende de nenhum dos pontos 1 a 9**, mas a decisão de promover em bloco
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

---

## Cobertura de testes

- `udata/tests/frontend/test_saml.py` — **149 testes** de base, **160 depois do LEDG-2433** (as
  duas classes do provedor), **169 depois do LEDG-2457** (`SAMLDeclaredCitizenTypeTest`), e
  **170 + 8 subtests** hoje, com o teste do link por email. Medido em `develop`.
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
