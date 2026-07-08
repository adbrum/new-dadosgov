# Permissões de Visualização e Acesso - Portal dados.gov.pt

**Frontoffice (portal público) e Backoffice (área de administração)**

> Documento técnico-funcional que descreve, por tipo de utilizador, o que cada perfil pode **ver** e **fazer** em todo o portal dados.gov.pt. Baseado na análise do código do backend (`udata` - Flask/MongoDB) e do frontend (Next.js/React).

---

## 1. Sumário executivo

O controlo de acessos do dados.gov.pt assenta em duas camadas:

- **Backend (fonte única de verdade)** - Toda a autorização é decidida no backend, com base em **Flask-Principal** (modelo de _Needs_ / _Permissions_ / _Identity_) e **Flask-Security** (autenticação e papéis). Cada objeto (dataset, reutilização, organização, etc.) é serializado na API com um objeto `permissions` calculado **para o utilizador do pedido** (`edit`, `delete`, `members`, `harvest`, `private`, …).
- **Frontend (apresentação)** - O frontend **lê** essas _flags_ de permissão para mostrar/esconder botões e secções, e aplica um _guard_ de rota no lado do cliente para o backoffice. **Não impõe autorização por si só** - a proteção real dos dados depende sempre do backend rejeitar chamadas não autorizadas.

Existem dois grandes níveis de papel:

| Nível                    | Onde é guardado            | Valores                                   |
| ------------------------ | -------------------------- | ----------------------------------------- |
| **Papel de site**        | `User.roles` (lista)       | `admin` (sysadmin), `editor`, `moderator` |
| **Papel de organização** | `Member.role` (por membro) | `admin`, `editor`, `partial_editor`       |

> **Nota importante:** apesar de estarem definidos os papéis de site `editor` e `moderator`, apenas o papel **`admin`** é determinante ao nível do site - as classes de permissão só reconhecem `admin`. Os papéis `editor`/`moderator` de site não conferem, no código atual, quaisquer permissões distintas.

---

## 2. Tipos de utilizador (perfis)

| #   | Perfil                                       | Descrição                                                                                        |
| --- | -------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| 1   | **Anónimo**                                  | Visitante não autenticado.                                                                       |
| 2   | **Utilizador autenticado**                   | Conta ativa, sem organização e sem papel de site.                                                |
| 3   | **Proprietário de objeto**                   | Utilizador individual que criou um objeto (dataset/reutilização/…) em seu nome, sem organização. |
| 4a  | **Membro de organização - `partial_editor`** | Editor parcial: só edita os objetos que lhe foram atribuídos.                                    |
| 4b  | **Membro de organização - `editor`**         | Editor: gere todo o conteúdo da organização.                                                     |
| 4c  | **Membro de organização - `admin`**          | Administrador da organização: conteúdo + membros + definições.                                   |
| 5   | **Sysadmin / Administrador de site**         | `User.roles` contém `admin`. Acesso total.                                                       |

### Formas de autenticação (frontoffice)

O login (`/login`) oferece três métodos:

1. **Chave Móvel Digital (CMD)** - via SAML (`autenticacao.gov.pt`).
2. **eIDAS** - autenticação europeia, via SAML.
3. **E-mail e palavra-passe** - login clássico.

- Sessões CMD/eIDAS são marcadas como `saml_login` (o _logout_ é encaminhado para `/saml/logout`).
- Existe deteção de **contas legadas** que necessitam de migração (`migration_required` → fluxo de migração de conta).
- O registo de conta é público (`/register`).

---

## 3. Como funciona a autorização (arquitetura)

### 3.1 Backend - Needs, Permissions e Identity

- A classe base `Permission` (`udata/auth/__init__.py`) **inclui sempre** `RoleNeed("admin")`. Consequência: **o administrador de site satisfaz qualquer permissão** derivada desta classe. `admin_permission` (sem _needs_ extra) é o portão "só sysadmin".
- Ao carregar a identidade de um pedido, o Flask-Security adiciona um `RoleNeed(<papel>)` por cada papel do utilizador e um `UserNeed(user)`. As permissões de organização são injetadas por sinal: para cada organização de que o utilizador é membro, adiciona-se `OrganizationNeed(<papel>, org.id)` e, para editores parciais, `AssignmentNeed(...)` por objeto atribuído.

### 3.2 Backend - imposição na API

- `@api.secure` (simples) → exige autenticação: devolve **401** se não autenticado (e **423** em modo só-leitura para não-admins).
- `@api.secure(admin_permission)` → exige papel de site `admin`, senão **403**.
- Verificações ao nível do objeto: `obj.permissions["edit"].test()` (levanta 403) ou `.can()` (booleano) dentro dos _handlers_.
- Objetos **ocultos** (privados/apagados) devolvem **404** (para não revelar existência) ou **410** (apagado) a quem não tem permissão de leitura.

### 3.3 Frontend - leitura de permissões e _guard_ de rota

- **Estado de autenticação** (`AuthContext` / `useAuth()`): obtém o utilizador via `GET /auth/me`; expõe `isAdmin` (`roles` inclui `"admin"`), `hasOrganization`, `samlLogin`.
- **Guard do backoffice** (`AdminRouteGuard`): único portão do frontend para `/admin/*`.
- **Renderização condicional**: botões de editar/apagar/criar mostram-se conforme a _flag_ `permissions.*` que vem do backend (via helper `can(entidade, ação)`).

> ⚠️ **Avisos de segurança a reter**
>
> 1. Todo o _gating_ do backoffice no frontend é do lado do cliente. As páginas de admin não têm imposição server-side - a proteção real é o backend rejeitar as chamadas à API.
> 2. O botão **Editar** na página pública de um _dataset_ usa uma verificação de propriedade derivada no cliente (é admin, ou dono, ou a organização do dataset está entre as suas), em vez da _flag_ `permissions.edit` usada em todos os outros tipos de objeto. É uma inconsistência de padrão (a autorização real continua no backend).

---

## 4. Papéis de organização em detalhe

| Papel              | Ver conteúdo privado da org. | Criar conteúdo na org. | Editar/apagar conteúdo         | Gerir membros | Editar/apagar a organização |                Harvesters                | Badges |
| ------------------ | :--------------------------: | :--------------------: | ------------------------------ | :-----------: | :-------------------------: | :--------------------------------------: | :----: |
| **partial_editor** |              ✅              |  ✅ (auto-atribuído)   | Só objetos **atribuídos** a si |      ❌       |             ❌              |                    ❌                    |   ❌   |
| **editor**         |              ✅              |           ✅           | **Todo** o conteúdo da org.    |      ❌       |             ❌              |               Só _preview_               |   ❌   |
| **admin**          |              ✅              |           ✅           | **Todo** o conteúdo da org.    |      ✅       |             ✅              | Gestão completa (editar/apagar/executar) |   ✅   |

**Mecânica do `partial_editor`:** não recebe direitos gerais sobre todo o conteúdo da organização. Cada objeto que cria é automaticamente **atribuído** a si (`Assignment`); só pode editar/apagar os objetos que lhe estão atribuídos.

**Nota sobre harvesters:** editar/apagar/executar uma fonte de recolha (_harvester_) exige papel de organização **admin** (ou o proprietário) - **os editores não podem**. As ações `validar` e `agendar` são exclusivas do **sysadmin**.

---

## 5. Permissões no FRONTOFFICE (portal público)

Todas as páginas públicas são acessíveis a **qualquer** perfil (incluindo anónimo). O que muda é a capacidade de **interagir**.

| Ação / Página                                                                                                            |     Anónimo     |                   Autenticado                    |          Membro de org.          |    Sysadmin     |
| ------------------------------------------------------------------------------------------------------------------------ | :-------------: | :----------------------------------------------: | :------------------------------: | :-------------: |
| Ver datasets, reutilizações, dataservices, organizações, temas, publicações, perfis, pesquisa, datastories, documentação |       ✅        |                        ✅                        |                ✅                |       ✅        |
| Ver apenas conteúdo **público** (não-privado, não-apagado, não-arquivado)                                                |       ✅        |              ✅ (+ os seus ocultos)              |      ✅ (+ ocultos da org.)      |    ✅ (tudo)    |
| Resultados de pesquisa (Elasticsearch) - só itens visíveis                                                               |       ✅        |                        ✅                        |                ✅                |       ✅        |
| Login / Registo / Migração de conta                                                                                      |       ✅        |                 (redirecionado)                  |         (redirecionado)          | (redirecionado) |
| Seguir / favoritar, pedir adesão a organização                                                                           | ❌ (pede login) |                        ✅                        |                ✅                |       ✅        |
| Abrir discussão / comentar                                                                                               |       ❌        |                        ✅                        |                ✅                |       ✅        |
| Botão **Editar** no detalhe de um objeto                                                                                 |       ❌        | Só se `permissions.edit` (ou dono, nos datasets) | ✅ onde as permissões o permitam |       ✅        |

> **Conteúdo oculto:** objetos **privados**, **apagados** (_soft delete_) ou **arquivados** nunca aparecem em listagens públicas nem na pesquisa. Não existe um estado "rascunho" separado - o equivalente é `private = true` (não publicado), sujeito às mesmas regras dos privados.

---

## 6. Permissões no BACKOFFICE (`/admin/*`)

O backoffice exige **sempre login**. O `AdminRouteGuard` aplica:

- **Não autenticado** → redireciona para `/login`.
- **`/admin/system/*`** → exige `isAdmin` (sysadmin); caso contrário redireciona para `/admin/me/datasets`.
- **`/admin/org/[orgId]/*`** → exige ter organização (`hasOrganization`); caso contrário redireciona para a rota por defeito.
- Restante `/admin/*` → acessível a qualquer utilizador autenticado.

### 6.1 Âmbitos do backoffice

| Âmbito          | Rota                   | Quem acede             | Conteúdo                                                                                                                                         |
| --------------- | ---------------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Pessoal**     | `/admin/me/*`          | Qualquer autenticado   | Os meus datasets, reutilizações, dataservices, recursos de comunidade, estatísticas, perfil                                                      |
| **Organização** | `/admin/org/[orgId]/*` | Membros da organização | Datasets, reutilizações, dataservices, harvesters, discussões, **membros**, perfil, estatísticas da org.                                         |
| **Sistema**     | `/admin/system/*`      | Só sysadmin            | Utilizadores, organizações, datasets, reutilizações, dataservices, recursos de comunidade, harvesters, tópicos, editorial, **logs**, publicações |

O grupo **Sistema** só aparece no menu lateral quando o utilizador é sysadmin. É criado um grupo de menu por cada organização a que o utilizador pertence.

### 6.2 Acesso ao backoffice por perfil

| Secção                                                      |  Anónimo   | Autenticado (sem org.) |                  Membro de org.                   | Sysadmin |
| ----------------------------------------------------------- | :--------: | :--------------------: | :-----------------------------------------------: | :------: |
| Qualquer `/admin/*`                                         | ❌ → login |           ✅           |                        ✅                         |    ✅    |
| `/admin/me/*` (pessoal)                                     |     ❌     |           ✅           |                        ✅                         |    ✅    |
| `/admin/org/[orgId]/*`                                      |     ❌     |   ❌ → rota defeito    |                        ✅                         |    ✅    |
| Gestão de membros (adicionar/remover/papel)                 |     ❌     |           ❌           | Só se `org.permissions.members` (= admin da org.) |    ✅    |
| `/admin/system/*` (utilizadores, logs, editorial, tópicos…) |     ❌     |   ❌ → rota defeito    |                 ❌ → rota defeito                 |    ✅    |

---

## 7. Matriz de permissões por tipo de objeto (backend)

Legenda: **A**=Anónimo · **U**=Autenticado · **Dono** · **pE**=partial_editor · **E**=editor org. · **oA**=admin org. · **SA**=sysadmin

### 7.1 Datasets / Reutilizações / Dataservices (objetos "ownable")

| Ação                         |  A  |  U  | Dono |      pE       |  E  | oA  | SA  |
| ---------------------------- | :-: | :-: | :--: | :-----------: | :-: | :-: | :-: |
| Ver (público)                | ✅  | ✅  |  ✅  |      ✅       | ✅  | ✅  | ✅  |
| Ver oculto (privado/apagado) | ❌  | ❌  |  ✅  |      ✅       | ✅  | ✅  | ✅  |
| Criar                        | ❌  | ✅  |  ✅  |      ✅       | ✅  | ✅  | ✅  |
| Editar                       | ❌  | ❌  |  ✅  | Só atribuídos | ✅  | ✅  | ✅  |
| Apagar (_soft delete_)       | ❌  | ❌  |  ✅  | Só atribuídos | ✅  | ✅  | ✅  |
| Sub-ações administrativas    | ❌  | ❌  |  ❌  |      ❌       | ❌  | ❌  | ✅  |

> Ao criar, o `owner` fica restrito ao próprio e a `organization` a uma de que se é membro. Ver/editar objetos ocultos segue a permissão de leitura: público → todos; oculto → dono / membro da org. / sysadmin.

### 7.2 Organizações

| Ação                              |  A  |  U  | Membro | Admin org. | SA  |
| --------------------------------- | :-: | :-: | :----: | :--------: | :-: |
| Ver                               | ✅  | ✅  |   ✅   |     ✅     | ✅  |
| Criar (fica admin da nova org.)   | ❌  | ✅  |   ✅   |     ✅     | ✅  |
| Editar                            | ❌  | ❌  |   ❌   |     ✅     | ✅  |
| Apagar                            | ❌  | ❌  |   ❌   |     ✅     | ✅  |
| Gerir membros / pedidos de adesão | ❌  | ❌  |   ❌   |     ✅     | ✅  |
| Pedir adesão                      | ❌  | ✅  |   -    |     -      |  -  |
| Atribuir _badges_                 | ❌  | ❌  |   ❌   |    ❌\*    | ✅  |

> *Alterar *badges* de uma organização exige **sysadmin**. Atribuir *badges\* a datasets exige admin da organização dona (ou sysadmin).

### 7.3 Discussões

| Ação                       |  A  |  U  |       Autor        | Dono do objeto | Admin/Editor org. | SA  |
| -------------------------- | :-: | :-: | :----------------: | :------------: | :---------------: | :-: |
| Ler                        | ✅  | ✅  |         ✅         |       ✅       |        ✅         | ✅  |
| Abrir discussão / comentar | ❌  | ✅  |         ✅         |       ✅       |        ✅         | ✅  |
| Fechar                     | ❌  | ❌  |         ✅         |       ✅       |        ✅         | ✅  |
| Editar/apagar discussão    | ❌  | ❌  |         ✅         |       -        |  ✅ (se da org.)  | ✅  |
| Editar/apagar mensagem     | ❌  | ❌  | ✅ (autor da msg.) |       -        |  ✅ (se da org.)  | ✅  |

> Não é possível comentar discussões fechadas nem apagar o primeiro comentário.

### 7.4 Publicações (Posts)

| Ação                    |  A  |  U  | SA  |
| ----------------------- | :-: | :-: | :-: |
| Ver / listar            | ✅  | ✅  | ✅  |
| Criar / editar / apagar | ❌  | ❌  | ✅  |

> As publicações **não têm propriedade por objeto** - toda a gestão é exclusiva do sysadmin.

### 7.5 Tópicos / Temas

| Ação                              |  A  |  U  |        Dono/Membro        | SA  |
| --------------------------------- | :-: | :-: | :-----------------------: | :-: |
| Ver / listar (públicos)           | ✅  | ✅  |            ✅             | ✅  |
| Criar                             | ❌  | ✅  |            ✅             | ✅  |
| Editar / apagar / gerir elementos | ❌  | ❌  | ✅ (conforme propriedade) | ✅  |

### 7.6 Fontes de recolha (Harvesters)

| Ação                       |  A  |      U       | Dono |         Editor org.          | Admin org. | SA  |
| -------------------------- | :-: | :----------: | :--: | :--------------------------: | :--------: | :-: |
| Listar                     | ❌  | ✅ (as suas) |  ✅  |              ✅              |     ✅     | ✅  |
| Criar                      | ❌  |      ✅      |  ✅  | (na org.: precisa `harvest`) |     ✅     | ✅  |
| _Preview_                  | ❌  |      -       |  ✅  |              ✅              |     ✅     | ✅  |
| Editar / apagar / executar | ❌  |      ❌      |  ✅  |              ❌              |     ✅     | ✅  |
| Validar / agendar          | ❌  |      ❌      |  ❌  |              ❌              |     ❌     | ✅  |

---

## 8. Conteúdo privado, apagado e arquivado

- **Flags do modelo:** `private` (não publicado), `deleted`/`deleted_at` (_soft delete_), `archived`/`archived_at`. Um objeto é **oculto** se for privado, apagado ou arquivado.
- **Listagens** usam `visible_by_user(utilizador)`:
  - **Anónimo** → só conteúdo público;
  - **Sysadmin** → tudo;
  - **Autenticado** → conteúdo público **+** tudo o que ele ou as suas organizações possuem.
- **Pesquisa (Elasticsearch):** objetos ocultos **nunca** são indexados - não aparecem a ninguém nos resultados de pesquisa.
- **Filtros protegidos:** passar `deleted`/`archived`/`private` como filtro sendo anónimo → **401**.
- **Leitura de detalhe:** público → todos; oculto → só dono / membro da org. / sysadmin (senão **404**; apagado-não-privado → **410**).
- **"Rascunho":** não existe estado próprio - usa-se `private = true`.

---

## 9. Acesso por API (tokens)

- Autenticação por token via cabeçalho **`X-API-KEY`** (ou OAuth2). Um token válido autentica o pedido **como o utilizador dono do token** - carrega exatamente as permissões desse utilizador.
- O token é guardado como _hash_ (HMAC-SHA256), com `expires_at` e `revoked_at`; erros possíveis: `invalid`, `revoked`, `expired`.
- **O browser do portal não usa API key** - a autenticação do frontend é feita por _cookie_ de sessão (Flask-Security). O campo `apikey` que aparece no perfil é apenas informativo/para uso externo.

---

## 10. Resumo por perfil

**1. Anónimo** - Lê todo o conteúdo público (datasets, reutilizações, dataservices, organizações, tópicos, publicações, discussões). A pesquisa devolve só itens visíveis. Qualquer endpoint protegido → 401. Sem escrita.

**2. Utilizador autenticado** - Tudo o que o anónimo faz, mais: criar datasets/reutilizações/dataservices/tópicos/discussões/comentários/organizações/harvesters (como dono individual); editar/apagar **apenas o que possui**; ver os seus objetos ocultos; pedir adesão a organizações; editar o próprio perfil e notificações. Não mexe em publicações, _badges_ nem conteúdo alheio.

**3. Proprietário de objeto (individual)** - Controlo total de leitura/edição/eliminação sobre os seus objetos, transferência de propriedade, gestão das suas discussões. Igual ao autenticado, limitado ao que possui.

**4a. Membro `partial_editor`** - Vê os ativos privados da organização; cria conteúdo na org. (auto-atribuído); edita/apaga **só os objetos atribuídos**. Não gere membros, definições, harvesters, nem conteúdo não atribuído.

**4b. Membro `editor`** - Edita/apaga **todo** o conteúdo da organização; abre discussões da org.; _preview_ de harvesters. **Não** gere membros, não edita/apaga a organização, não gere harvesters (admin), não atribui _badges_.

**4c. Membro `admin`** - Todos os direitos de editor **mais**: gerir membros e pedidos/convites, editar/apagar a organização, gestão completa de harvesters (editar/apagar/executar), atribuir _badges_ nos datasets da org., transferir propriedade.

**5. Sysadmin / Administrador de site** (`User.roles` ∋ `admin`) - Ultrapassa **todas** as permissões. Vê todos os objetos. Único a poder: CRUD de publicações, sub-ações administrativas de datasets/reutilizações/dataservices, atribuir _badges_ de organização, validar/agendar harvesters, ver detalhes de harvesters, editar qualquer utilizador, aceder a `/admin/system/*` (utilizadores, logs, editorial). Ignora o modo só-leitura.

---

## 11. Referências de código

**Backend (`backend/udata/`)**

- Base de permissões e `admin_permission`: `auth/__init__.py`
- Papéis de site: `core/user/permissions.py`, `core/user/models.py`
- Papéis e _needs_ de organização: `core/organization/permissions.py`, `core/organization/constants.py`, `core/organization/models.py`
- Objetos "ownable" (datasets/reutilizações/dataservices): `core/dataset/permissions.py`, `core/reuse/permissions.py`, `core/dataservices/permissions.py`
- Editores parciais / atribuições: `core/organization/assignment.py`
- Discussões / publicações / tópicos / harvest / badges: `core/discussions/permissions.py`, `core/post/permissions.py`, `core/topic/permissions.py`, `harvest/permissions.py`, `core/badges/permissions.py`
- Visibilidade (privado/apagado): `core/owned.py`, `core/dataset/models.py`, `core/dataset/search.py`
- Imposição na API e tokens: `api/__init__.py`, `core/api_token/models.py`

**Frontend (`frontend/src/`)**

- Estado de autenticação: `context/AuthContext.tsx`, `service/api/auth/index.ts`, `app/auth/*/route.ts`
- _Guard_ do backoffice: `components/admin/AdminRouteGuard.tsx`, `app/[locale]/(admin)/layout.tsx`
- Menu por perfil: `components/admin/AdminSideNavigation.tsx`
- Helper de permissões: `utils/permissions.ts`
- Tipos de identidade/papéis: `service/types/identity/identity.ts`
- Camada de API (público vs autenticado): `service/utils/API.ts`
- Login CMD/eIDAS/e-mail: `components/login/LoginContent.tsx`

---

_Documento gerado a partir da análise do código-fonte (submódulos backend `udata-pt` e frontend `dadosgov-fe`)._
