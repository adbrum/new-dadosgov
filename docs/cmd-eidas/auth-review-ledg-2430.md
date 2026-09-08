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
> 🚨 **A verificação de colisões é ESTRUTURALMENTE CEGA em `--dry-run`.** O
> `_find_shared_nics()` filtra por `is_nic_hashed`; num ambiente onde nada está hasheado
> ainda, não tem nada para olhar. O `0 duplicados` de um dry-run é **garantido, não
> medido** — e a ambiguidade **já existe antes de qualquer hash**, porque o passo 1b do
> lookup faz `User.objects(extras__auth_nic=user_nic).first()` sobre valores em claro.

### `scripts/audit_institutional_users.py` — o segundo, e ainda NÃO versionado

Só de leitura, recebe `--host`, e classifica o link CMD **nas mesmas quatro categorias** do
comando (`yes (hashed)`, `stale (legacy-encrypted)`, `stale (plain NIC)`,
`stale (unrecognized)`). Já conta contas com prefixo, pertença a organização, `last_login_at`
e domínios institucionais → cobre boa parte das perguntas 1 a 4.

Os hosts dos ambientes estão no seu docstring: **DEV `10.55.37.143`**, **TST `10.55.37.40`**.

⚠️ **Está untracked em `backend/scripts/`** — não está em branch nenhuma. O LEDG-2434 pede
explicitamente um script versionado, porque o levantamento vai ter de ser repetido depois das
correcções. **Versioná-lo é o primeiro ponto do LEDG-2434**, não escrever um novo.

⚠️ **O que lhe falta:** os dois eixos de colisão — `auth_nic` repetido (pergunta 7) e
`email` repetido em minúsculas (pergunta 8). É a extensão a fazer, e resolve de uma vez a
cegueira do dry-run: **valores em claro iguais produzem hashes iguais**, logo agrupar os
valores em claro responde à pergunta sem hashear nada e sem depender do `SECRET_KEY`.

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

| # | Ticket | O quê | Onde | Feito? | Dependência |
| --- | --- | --- | --- | --- | --- |
| **1** | LEDG-2432 | Repor o login por email e palavra-passe | Frontend | ✅ **Sim** — em `develop` e `tst` | 🚨 Regressão; desbloqueou o `tst → ppr` |
| **2** | LEDG-2456 | Fuga de existência de conta **+ e-mails em inglês** | Backend | ✅ **Sim** — em `develop` e `tst` | Nenhuma — e torna o 7 menor |
| **3** | LEDG-2433 | Campo do método de autenticação (CMD/eIDAS) | Backend | ✅ **Sim** — 6 commits, suite completa verde; em `develop` e `tst` | Nenhuma — aditivo |
| **4** | LEDG-2457 | Tipo de cidadão **declarado** (nacional/estrangeiro) | Full-stack | ✅ **Sim** — 5 commits nos dois repos; em `develop` e `tst` | **Depende do 3** |
| 5 | LEDG-2434 | Levantamento de dados e de impacto | Spike | ❌ Não | Nenhuma — paralelizável com o 3 e o 4 |
| 6 | LEDG-2435 | **Uma identidade, uma conta** — as duas classes de duplicado | Backend | ❌ Não | Desenho depende do **5** |
| 7 | LEDG-2431 | Associar a uma conta tradicional existente | Full-stack | ❌ Não | Depende do **2**, do **5** e do **6** |
| 8 | LEDG-2438 | **Estrangeiros: identidade por documento em vez de NIC** | Backend | ❌ Não | Confirmar sobreposição com LEDG-2288 |
| 9 | LEDG-2436 | Identidade sem identificador (eIDAS **e** CMD) | Backend | ❌ Não | **Depende do 8**; escolha bloqueada por LEDG-2288 |

**Próximo a implementar:** o **5** (LEDG-2434). Os pontos 1 a 4 estão em `develop` e `tst`, e
o 5 é o único que não depende de nada — e é o que desbloqueia o desenho do 6 e do 7. O dry-run
já correu (ver acima); falta versionar o script de levantamento, acrescentar-lhe os dois eixos
de colisão, e correr nos quatro ambientes.

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
frontend.** A resposta genérica construída aqui **é a restrição 2 do ponto 7** — o 7 estende-a
em vez de a reinventar.

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

⚠️ **Este valor nunca gateia nada.** Vem de um radio button. Quando o ponto 8 trouxer o provado,
**o provado ganha** — e o desacordo entre os dois passa a ser o sinal de IdP mal configurado que
falta ao ponto 9.

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
(`10.55.37.143`)** e **TST (`10.55.37.40`)**. É para isso que o script recebe o parâmetro.

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
   NIC português. **Prova a favor do ponto 8 (LEDG-2438).**

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

### 6 — LEDG-2435 · Uma identidade, uma conta *(backend)*

Invariante: **uma identidade CMD/eIDAS → no máximo uma conta.** Cobre as duas classes:

- **(a) IdP sem email** → não criar a conta ainda: identidade em sessão, encaminhar para o
  registo. **Inclui desacoplar da flag** — **sem remover as guardas `nic_required`**.
- **(b) email já pertence a outra conta** → encaminhar para a associação.
  ⚠️ **Não pode ser desligado antes do ponto 7 existir.**
- **(c) capitalização diferente** → alinhar a verificação `exact` com a `ci`.
  ⚠️ **O mesmo problema existe no `change_email`**, e o LEDG-2456 deixou-o registado como achado
  rejeitado para este ponto o apanhar. **Cobrir os dois sítios.**

A fechar de passagem, por estarem na mesma zona: a guarda em falta na `/saml/migration/skip`, e
o alinhamento dos três defaults da flag.

### 7 — LEDG-2431 · Associar a uma conta tradicional existente *(a lacuna real)*

Três restrições obrigatórias: **prova de posse** do email de destino, **resposta genérica** (já
construída pelo ponto 2 — **estender, não reinventar**: o aviso ao dono da caixa passa a ser um
link que associa), e **tratar o conteúdo da conta de origem** (recusar ou transferir — decisão do
ponto 5). Entra pelo `_link_identity_and_login`.

É também aqui que entra a decisão 6: **um campo de email**, com o endereço do CMD pré-preenchido
quando existe, e a prova por link mantida mesmo nesse caso.

### 8 — LEDG-2438 · Estrangeiros: a identidade é o documento, não o NIC *(backend)*

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

**Porque vem antes do 9:** os dois handlers ACS são idênticos, logo um estrangeiro com CMD cai
**exactamente** no bug do ponto 9 — mas a resposta certa é oposta. O 9 recomenda **rejeitar**
quem não tem identificador; um estrangeiro **tem**, só não lho pedimos. Resolver o 8 primeiro
**tira os estrangeiros do âmbito do 9**.

**O ponto 4 ajuda aqui:** o tipo declarado dá a verificação cruzada contra o que a asserção traz.

### 9 — LEDG-2436 · Identidade sem identificador *(bug)*

⚠️ **Afeta os dois provedores**, não só o eIDAS: os handlers ACS são idênticos a partir do
`_find_or_create_saml_user`. **Uma correção num handler só deixa o outro intacto.**

Com a flag a `True`, **os três ramos do wizard recusam a identidade com `nic_required` 400** —
beco sem saída por desenho, e a recusa está no sítio errado. Com a flag a `False`, **cada login
cria uma conta nova**.

**A metade da multiplicação de contas não depende de decisão nenhuma** e pode sair com o ponto 6.
O que está bloqueado é só **a escolha entre rejeitar e ligar pelo email** — pelo LEDG-2288 e pelo
ponto 8.

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
