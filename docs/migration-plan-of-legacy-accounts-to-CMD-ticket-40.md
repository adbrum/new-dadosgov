# Plano: Migração de Contas Legadas para CMD (TICKET-40)

## Contexto

O portal dados.gov.pt tem utilizadores legados com login email/password. A nova diretriz exige CMD (Chave Móvel Digital) ou eIDAS como únicos métodos de autenticação. Utilizadores legados possuem datasets, organizações e reutilizações vinculados às suas contas. É necessário migrar estes utilizadores sem perda de dados.

**Abordagem escolhida: MERGE** — manter o registo do utilizador existente e atualizar o seu método de autenticação (adicionar NIC, limpar password). Assim, todos os `ReferenceField` (datasets, orgs, reuses, discussions, follows) continuam válidos sem necessidade de transferência.

---

## Fluxos

### Fluxo A — Migração via CMD/eIDAS (fluxo principal)

```
1. Utilizador clica "CMD" ou "eIDAS" → /saml/login (ou /saml/eidas/login) → Autenticação.gov → POST /saml/sso
2. Backend extrai atributos SAML (email, NIC, nome)
3. Procura utilizador por email:
   a) Encontrado COM password E SEM auth_nic → CANDIDATO A MIGRAÇÃO
      → Guarda dados SAML na sessão (sem login)
      → Redirect para /pages/migrate-account
   b) Encontrado COM auth_nic → Já migrado, login normal
   c) Não encontrado → Cria novo utilizador automaticamente, login normal
4. Página de migração — wizard multi-step:
   → Step 1: Confirmar conta (mostra nome + email mascarado da conta legada)
   → Step 2: Escolher método de verificação (código por email OU password antiga)
   → Step 3: Verificação (introduzir código ou password)
   → Step 4: Sucesso — merge da conta (adiciona NIC, password = None, login)
5. Após migração: login legado (email/password) deixa de funcionar para esse utilizador
```

### Fluxo B — Bloqueio de login legado (forçar migração)

```
1. Utilizador legado (não migrado) faz login por email/password
2. Backend autentica com sucesso (Flask-Security)
3. Route handler do frontend chama GET /saml/migration/check
4. Backend verifica: utilizador tem password + não tem auth_nic → needs_migration: true
5. Route handler faz logout do utilizador e devolve 403 com message: "migration_required"
6. LoginClient mostra aviso de migração obrigatória:
   → "O login por email e palavra-passe vai ser descontinuado"
   → Instruções: usar CMD ou eIDAS
   → Botões: "Migrar com CMD" e "Migrar com eIDAS"
7. Utilizador clica num dos botões → Fluxo A é ativado
```

### Fallback (SAML não retorna email)
```
→ Redirect para /pages/migrate-account?no_email=true
→ Utilizador introduz email antigo OU nome+apelido
→ Backend procura conta legada correspondente
→ Mostra dados da conta encontrada para confirmação
→ Mesmo fluxo de verificação
```

### Criação de conta (sem conta legada)
```
→ CMD/eIDAS → SAML → backend não encontra utilizador → cria automaticamente
→ Não existe página de registo separada — login e criação são o mesmo ponto de entrada
→ Mensagem na página de login: "Ainda não tem conta? A sua conta será criada automaticamente."
```

---

## Backend

### 1. Modificar `_find_or_create_saml_user()` — detetar candidatos a migração

**Ficheiro:** `backend/udata/auth/saml/saml_plugin/saml_govpt.py`

Alterar retorno para tuple `(user, status)`:
- `("existing_saml")` — já tem NIC, login normal
- `("migration_candidate")` — tem password + sem NIC → migração
- `("new")` — utilizador criado
- `("error")` — sem email nem NIC

```python
def _find_or_create_saml_user(user_email, user_nic, first_name, last_name):
    user = None
    if user_email:
        user = datastore.find_user(email=user_email)
    if not user and user_nic:
        user = datastore.find_user(extras={'auth_nic': user_nic})

    if user:
        has_nic = user.extras and user.extras.get('auth_nic')
        if not has_nic and user.password:
            return user, "migration_candidate"
        return user, "existing_saml"

    # Criar novo utilizador (fluxo atual mantido)
    ...
    return user, "new"
```

### 2. Modificar `idp_initiated()` e `idp_eidas_initiated()` — redirect para migração

**Ficheiro:** `backend/udata/auth/saml/saml_plugin/saml_govpt.py`

Ambos os callbacks (CMD e eIDAS) usam o mesmo fluxo de migração:

```python
user, status = _find_or_create_saml_user(...)

if status == "migration_candidate":
    return _handle_migration_redirect(user, user_email, user_nic, first_name, last_name)

return _handle_saml_user_login(user)
```

### 3. Funções auxiliares de migração

**Ficheiro:** `backend/udata/auth/saml/saml_plugin/saml_govpt.py`

#### `_handle_migration_redirect(user, user_email, user_nic, first_name, last_name)`
- Guarda dados SAML na sessão (`session['saml_migration_pending']`)
- Redirect para `/pages/migrate-account` (ou `?no_email=true` se sem email)

#### `_mask_email(email)`
- Mascarar email para display seguro (ex: `j***@example.com`)

#### `_send_migration_code(user, code)`
- Envia email com código de verificação via `MailMessage` + `send_mail()`

#### `_find_legacy_user(email, first_name, last_name)`
- Procura conta legada (com password, sem NIC, não eliminada) por email ou nome

### 4. Novos endpoints de migração no Blueprint SAML

**Ficheiro:** `backend/udata/auth/saml/saml_plugin/saml_govpt.py`

Os endpoints ficam no Blueprint `autenticacao_gov` porque precisam de acesso à sessão sem autenticação (o utilizador ainda não fez login).

#### `GET /saml/migration/check`
- Verifica se o utilizador **autenticado** é legado (tem password, sem NIC)
- Usado pelo route handler do login para bloquear utilizadores legados
- Retorna `{ needs_migration: true }` ou `{ needs_migration: false }`

#### `GET /saml/migration/pending`
- Lê `session['saml_migration_pending']`
- Busca dados da conta legada (nome, apelido) para confirmação do utilizador
- Retorna `{ pending: true, email: "j***@example.com", has_email: true, first_name: "João", last_name: "Silva" }` ou `{ pending: false }`

#### `POST /saml/migration/search`
- Aceita `{ email: "..." }` ou `{ first_name: "...", last_name: "..." }`
- Procura conta legada (com password, sem NIC, não eliminada)
- Se encontrada, atualiza `session['saml_migration_pending']['legacy_user_id']`
- Retorna `{ found: true, email: "j***@..." }` ou `{ found: false }`

#### `POST /saml/migration/send-code`
- Gera código numérico de 6 dígitos
- Guarda `session['migration_code'] = { code, expires, attempts: 0 }`
- Envia email ao utilizador legado com o código via `MailMessage`
- Rate limit: máx 3 envios por sessão
- Retorna `{ sent: true }`

#### `POST /saml/migration/confirm`
- Aceita `{ method: "code", code: "123456" }` ou `{ method: "password", password: "..." }`
- **Verificação por código:** compara com `session['migration_code']`, verifica expiração (10 min), incrementa tentativas (máx 5)
- **Verificação por password:** usa `verify_and_update_password()` do Flask-Security
- **Merge:** adiciona NIC a `extras`, `password = None` (desativa login legado), atualiza nomes, `login_user()`, `session['saml_login'] = True`
- Limpa dados de migração da sessão
- Retorna `{ success: true }`

#### `POST /saml/migration/skip`
- Para utilizadores que não reconhecem a conta legada e querem criar conta nova
- Cria novo utilizador com email placeholder, faz login
- Retorna `{ success: true }`

### 5. Rewrites no Next.js para as novas rotas

**Ficheiro:** `frontend/next.config.ts`

Adicionar ao `beforeFiles`:
```typescript
{ source: "/saml/migration/:path*", destination: `${BACKEND_URL}/saml/migration/:path*` },
```

### 6. Template de email para código de verificação

**Ficheiro:** `backend/udata/auth/saml/saml_plugin/saml_govpt.py` (função auxiliar)

Usar o sistema `MailMessage` + `send_mail()` de `udata/mail.py`:
```python
def _send_migration_code(user, code):
    msg = MailMessage(
        subject=_("Account migration verification code"),
        paragraphs=[
            _("Someone is linking a CMD identity to your %(site)s account.",
              site=current_app.config.get("SITE_TITLE", "dados.gov.pt")),
            _("Your verification code is: %(code)s", code=code),
            _("This code expires in 10 minutes."),
            _("If you did not request this, ignore this email."),
        ],
    )
    send_mail(user, msg)
```

---

## Frontend

### 7. Remoção da página de registo

A página de registo (`/pages/register`) e a página de login+registo (`/pages/loginregister`) foram eliminadas. CMD/eIDAS são os únicos métodos de autenticação — a criação de conta é automática no primeiro login SAML.

**Ficheiros removidos:**
- `frontend/src/components/login/RegisterClient.tsx`
- `frontend/src/components/login/LoginRegisterClient.tsx`
- `frontend/src/app/register/route.ts` (proxy de registo para backend)

**Ficheiros convertidos em redirects para `/pages/login`:**
- `frontend/src/app/pages/register/page.tsx`
- `frontend/src/app/pages/loginregister/page.tsx`

**Ficheiros atualizados:**
- `frontend/src/components/Header.tsx` — referências a `/pages/loginregister` apontam para `/pages/login`
- `frontend/src/services/api.ts` — função `register()` removida
- `frontend/src/components/login/LoginClient.tsx` — tabs CMD e eIDAS incluem mensagem: "Ainda não tem conta? Ao autenticar-se, a sua conta será criada automaticamente."

### 8. Bloqueio de login legado e aviso de migração

**Ficheiro:** `frontend/src/app/login/route.ts`

O route handler do login foi modificado para interceptar utilizadores legados:
1. Após login bem-sucedido (302), constrói cookie string com a sessão autenticada
2. Chama `GET /saml/migration/check` no backend com os cookies da sessão
3. Se `needs_migration: true`:
   - Faz logout do utilizador (`GET /logout/`)
   - Devolve `403` com `{ message: "migration_required" }`
4. Se `needs_migration: false` → login normal

**Ficheiro:** `frontend/src/components/login/LoginClient.tsx`

A tab "Iniciar sessão" foi atualizada para tratar a resposta `migration_required`:
- Quando o login é bloqueado, mostra estado `migrationRequired` com:
  - Título: "Migração obrigatória"
  - Explicação: login por email/password vai ser descontinuado
  - Caixa informativa (amber): como migrar via CMD ou eIDAS, garantia de que os dados são mantidos
  - Dois botões: **"Migrar com CMD"** e **"Migrar com eIDAS"**
- O formulário de login é substituído por este aviso (sem possibilidade de resubmeter)
- Os botões redirecionam para `/saml/login` e `/saml/eidas/login` respetivamente, ativando o Fluxo A

### 9. Nova página de migração

**Ficheiro:** `frontend/src/app/pages/migrate-account/page.tsx`
- Server component que renderiza `MigrateAccountClient`

**Ficheiro:** `frontend/src/components/login/MigrateAccountClient.tsx`
- Componente wizard multi-step:

**Step 1 — Deteção** (on mount)
- `GET /saml/migration/pending`
- Se `pending: false` → redirect para `/pages/login`
- Se `pending: true` + `has_email: true` → avançar para confirmação de conta
- Se `pending: true` + `has_email: false` → mostrar formulário de pesquisa

**Step 2 — Pesquisa manual** (só quando SAML não retorna email)
- Input para email OU nome + apelido
- `POST /saml/migration/search`
- Se encontrado → avançar para confirmação de conta
- Se não encontrado → mostrar opção de criar conta nova

**Step 3 — Confirmação da conta** (`confirm-account`)
- Mostra dados da conta legada encontrada:
  - Nome e apelido
  - Email mascarado (ex: `j***@example.com`)
- Botão "Sim, esta conta é minha" → avança para verificação
- Botão "Não, criar conta nova" → skip (cria conta nova via SAML)
- **Importante:** esta confirmação é visual — a prova de propriedade é feita no step seguinte

**Step 4 — Escolha do método de verificação** (`choose-method`)
- Card A: "Enviar código para o meu email" (mostra email mascarado)
- Card B: "Sei a minha palavra-passe antiga"

**Step 5a — Verificação por código** (`verify-code`)
- `POST /saml/migration/send-code`
- Input para 6 dígitos
- Botão "Reenviar" com countdown 60s
- Submit: `POST /saml/migration/confirm` com `{ method: "code", code }`

**Step 5b — Verificação por password** (`verify-password`)
- Input password
- Submit: `POST /saml/migration/confirm` com `{ method: "password", password }`

**Step 6 — Sucesso**
- "A sua conta foi migrada para a Chave Móvel Digital com sucesso."
- Redirect para `/` após 3 segundos

**UI:** segue padrão do `LoginClient.tsx` — mesma estrutura de layout, componentes agora-design-system (`InputText`, `InputPassword`, `Button`, `Icon`, `Breadcrumb`), mesmos tokens de cor.

### 10. Novas funções API no frontend

**Ficheiro:** `frontend/src/services/api.ts`

```typescript
export async function fetchMigrationPending(): Promise<{
  pending: boolean; email?: string; has_email?: boolean;
  first_name?: string; last_name?: string;
}>

export async function searchMigrationAccount(
  payload: { email?: string; first_name?: string; last_name?: string }
): Promise<{ found: boolean; email?: string }>

export async function sendMigrationCode(): Promise<{ sent: boolean }>

export async function confirmMigration(
  payload: { method: 'code'; code: string } | { method: 'password'; password: string }
): Promise<{ success: boolean }>

export async function skipMigration(): Promise<{ success: boolean }>
```

---

## Segurança

1. **Sem auto-linking**: migração nunca acontece sem ação explícita (código ou password)
2. **Confirmação visual**: utilizador vê nome + email da conta legada e confirma antes de prosseguir
3. **Dados na sessão server-side**: frontend vê apenas email mascarado, nomes e flags booleanas
4. **Código com expiração**: 6 dígitos, 10 minutos, máx 5 tentativas, máx 3 envios
5. **Password via Flask-Security**: `verify_and_update_password()` seguro
6. **Login legado bloqueado antes da migração**: utilizador legado que tenta login por email/password é imediatamente desautenticado e informado da obrigatoriedade de migração via CMD ou eIDAS
7. **Login legado desativado após merge**: `password = None` impede login por email/password permanentemente
8. **Proteção contra duplicação**: após merge, login via CMD/eIDAS encontra utilizador por NIC
9. **Sem página de registo**: eliminada superfície de ataque desnecessária — criação de conta só via SAML
10. **Proteção contra nomes duplicados**: mesmo com nomes iguais, a verificação por código ou password garante que só o verdadeiro dono completa a migração

---

## Ficheiros criados

| Ficheiro | Descrição |
|----------|-----------|
| `frontend/src/app/pages/migrate-account/page.tsx` | Rota da página de migração |
| `frontend/src/components/login/MigrateAccountClient.tsx` | Wizard de migração multi-step |

## Ficheiros removidos

| Ficheiro | Motivo |
|----------|--------|
| `frontend/src/components/login/RegisterClient.tsx` | Registo por email/password eliminado |
| `frontend/src/components/login/LoginRegisterClient.tsx` | Duplicado — página redirecionada para login |
| `frontend/src/app/register/route.ts` | Proxy de registo para backend — desnecessário |

## Ficheiros modificados

| Ficheiro | Alterações |
|----------|------------|
| `backend/udata/auth/saml/saml_plugin/saml_govpt.py` | `_find_or_create_saml_user()` → tuple com status; `idp_initiated()` + `idp_eidas_initiated()` → redirect migração; novos endpoints `/saml/migration/*` (incluindo `/check`); helpers `_handle_migration_redirect()`, `_mask_email()`, `_send_migration_code()`, `_find_legacy_user()` |
| `frontend/next.config.ts` | Rewrite `/saml/migration/:path*` |
| `frontend/src/app/login/route.ts` | Intercepta login legado: chama `/saml/migration/check`, faz logout e devolve 403 se `needs_migration` |
| `frontend/src/services/api.ts` | 5 novas funções de migração; função `register()` removida |
| `frontend/src/components/login/LoginClient.tsx` | Mensagem "criar conta automaticamente" nas tabs CMD e eIDAS; estado `migrationRequired` com aviso, instruções e botões "Migrar com CMD" / "Migrar com eIDAS" |
| `frontend/src/components/Header.tsx` | Referências `/pages/loginregister` → `/pages/login` |
| `frontend/src/app/pages/register/page.tsx` | Convertido em redirect para `/pages/login` |
| `frontend/src/app/pages/loginregister/page.tsx` | Convertido em redirect para `/pages/login` |

---

## Verificação

1. **Teste criação de conta**: login via CMD/eIDAS sem conta existente → conta criada automaticamente, redirect para home
2. **Teste deteção de migração via CMD**: login via CMD com email de conta legada → redirect para página de migração
3. **Teste deteção de migração via eIDAS**: login via eIDAS com email de conta legada → redirect para página de migração
4. **Teste bloqueio de login legado**: utilizador legado faz login por email/password → login bloqueado, aviso de migração obrigatória com botões CMD e eIDAS
5. **Teste confirmação visual**: página de migração mostra nome + email mascarado da conta legada
6. **Teste verificação por código**: email é enviado, código de 6 dígitos funciona, migração concluída
7. **Teste verificação por password**: password antiga é aceite, migração concluída
8. **Teste merge**: após migração, confirmar que `extras.auth_nic` está definido, `password` é `None`, e os datasets/orgs continuam associados
9. **Teste login legado desativado**: após migração, tentar login por email/password → falha (password é None)
10. **Teste re-login CMD**: após migração, login via CMD direto sem página de migração
11. **Teste re-login eIDAS**: após migração, login via eIDAS direto sem página de migração
12. **Teste fallback sem email**: SAML não retorna email → pesquisa manual por email ou nome → mesmo fluxo
13. **Teste redirects**: `/pages/register` e `/pages/loginregister` redirecionam para `/pages/login`
14. **Lint**: `npm run lint` no frontend sem novos erros
