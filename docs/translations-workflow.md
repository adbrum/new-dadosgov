# Traduções — Workflow PT-pt (dados.gov.pt)

> Como adicionar, atualizar e compilar as traduções do backend `udata` (e-mails, formulários, mensagens de erro, templates) para Português de Portugal.

---

## Índice

1. [Onde vivem as traduções](#1-onde-vivem-as-traduções)
2. [Configuração do idioma por omissão](#2-configuração-do-idioma-por-omissão)
3. [Como o utilizador determina o idioma do e-mail](#3-como-o-utilizador-determina-o-idioma-do-e-mail)
4. [Workflow após adicionar novas strings `_()` no código](#4-workflow-após-adicionar-novas-strings-_-no-código)
5. [Workflow após traduzir entradas no `.po`](#5-workflow-após-traduzir-entradas-no-po)
6. [Como verificar a percentagem traduzida](#6-como-verificar-a-percentagem-traduzida)
7. [Cuidados ao traduzir](#7-cuidados-ao-traduzir)
8. [Quando reiniciar serviços](#8-quando-reiniciar-serviços)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Onde vivem as traduções

Estrutura no backend:

```
backend/
├── babel.cfg                                 # configuração do extractor (jinja2 + python)
├── pyproject.toml                            # secção [tool.babel]
├── udata/translations/
│   ├── udata.pot                             # template (regenerado a partir do código)
│   ├── pt/LC_MESSAGES/
│   │   ├── udata.po                          # ficheiro de tradução PT-pt (texto)
│   │   └── udata.mo                          # ficheiro compilado (binário) — usado em runtime
│   ├── en/LC_MESSAGES/
│   ├── fr/LC_MESSAGES/
│   └── ...
```

| Ficheiro    | Quem o edita                              | Quem o lê                       |
| ----------- | ----------------------------------------- | ------------------------------- |
| `udata.pot` | gerado automaticamente por `pybabel extract` | é a base de `pybabel update` |
| `udata.po`  | manualmente (ou via Poedit/Crowdin)       | `pybabel compile`              |
| `udata.mo`  | gerado por `pybabel compile`              | **Flask-Babel** em runtime      |

> ⚠️ **Importante**: a aplicação só lê o `.mo`. Editar o `.po` sem recompilar **não tem efeito**.

---

## 2. Configuração do idioma por omissão

Definida em `backend/udata.cfg`:

```python
LANGUAGES = {
    "pt": "Português",
    "en": "English",
    "fr": "Français",
    "es": "Español",
}
DEFAULT_LANGUAGE = "pt"
```

Esta config é carregada automaticamente em `udata/app.py:165-168` a partir do `os.getcwd()` (ou da variável `UDATA_SETTINGS`). Tanto `inv serve` como `inv work` (worker do Celery, responsável pelo envio assíncrono de e-mails) têm de ser executados a partir de `backend/` para que o `udata.cfg` seja apanhado.

---

## 3. Como o utilizador determina o idioma do e-mail

`udata/i18n.py:69-71`:

```python
def _default_lang(user=None):
    lang = getattr(user or current_user, "prefered_language", None)
    return lang or current_app.config["DEFAULT_LANGUAGE"]
```

Ordem de prioridade:

1. **`user.prefered_language`** se estiver definido (campo `StringField` em `udata/core/user/models.py:60`).
2. **`DEFAULT_LANGUAGE`** do `udata.cfg` (atualmente `"pt"`).

> Se um utilizador antigo tem `prefered_language="en"`, vai continuar a receber e-mails em inglês. Para forçar PT-pt globalmente é preciso fazer um update em massa na coleção `user`:
>
> ```js
> db.user.updateMany(
>   { prefered_language: { $in: ["en", "fr", "es"] } },
>   { $set: { prefered_language: "pt" } }
> )
> ```

---

## 4. Workflow após adicionar novas strings `_()` no código

Sempre que adicionares chamadas `_("...")` / `lazy_gettext("...")` / `gettext("...")` no código Python ou em templates Jinja:

```bash
cd backend

# 1. Extrair todas as msgid do código para o ficheiro template (.pot)
uv run pybabel extract \
    -F babel.cfg \
    -k _ -k N_:1,2 -k L_ -k lazy_gettext \
    -k 'pgettext:1c,2' -k 'npgettext:1c,2,3' -k 'lazy_pgettext:1c,2' \
    -o udata/translations/udata.pot \
    udata

# 2. Sincronizar as msgid novas para todos os .po existentes
uv run pybabel update \
    -i udata/translations/udata.pot \
    -d udata/translations \
    --previous

# 3. Traduzir as entradas novas no ficheiro pt
$EDITOR udata/translations/pt/LC_MESSAGES/udata.po
#   procurar por:
#     - linhas "msgstr "" "                  → traduções em falta
#     - flag "#, fuzzy"                       → tradução automática suspeita (rever e remover a flag)

# 4. Compilar o .mo para a aplicação passar a usar as novas traduções
uv run pybabel compile \
    --domain=udata \
    --directory=udata/translations \
    --statistics
```

> 💡 Os parâmetros `-k …` (keywords) e `-F babel.cfg` já estão fixados na secção `[tool.babel]` do `pyproject.toml`, por isso a forma mais curta funciona na mesma:
>
> ```bash
> uv run pybabel extract -F babel.cfg -o udata/translations/udata.pot udata
> uv run pybabel update -i udata/translations/udata.pot -d udata/translations --previous
> uv run pybabel compile -d udata/translations --statistics
> ```

---

## 5. Workflow após traduzir entradas no `.po`

Se só editaste manualmente o `udata.po` (sem mexer no código), basta recompilar:

```bash
cd backend
uv run pybabel compile --domain=udata --directory=udata/translations --statistics
```

Output esperado para o PT-pt:

```
483 of 483 messages (100%) translated in udata/translations/pt/LC_MESSAGES/udata.po
compiling catalog udata/translations/pt/LC_MESSAGES/udata.po to udata/translations/pt/LC_MESSAGES/udata.mo
```

> ⚠️ Se vires `(64%) translated` (ou outra percentagem inferior a 100%) é porque há `msgstr ""` ou `#, fuzzy` por resolver — abre o `.po` e procura.

---

## 6. Como verificar a percentagem traduzida

Sem editor, a partir da linha de comandos:

```bash
cd backend
uv run python - <<'PY'
import polib
po = polib.pofile("udata/translations/pt/LC_MESSAGES/udata.po")
total = len([e for e in po if not e.obsolete])
empty = [e for e in po if not e.obsolete and (not e.msgstr or "fuzzy" in e.flags)]
print(f"Traduzidas: {total - len(empty)}/{total} = {(total - len(empty))*100//total}%")
print(f"Por traduzir / fuzzy: {len(empty)}")
for e in empty[:10]:
    print(f"  - {e.msgid[:90]!r}")
PY
```

Para listar **só** as strings que aparecem em e-mails:

```bash
uv run python - <<'PY'
import polib, re
po = polib.pofile("udata/translations/pt/LC_MESSAGES/udata.po")
mail = re.compile(r"(mails\.py|/auth/mails\.py|templates/mail/)")
for e in po:
    if e.obsolete:
        continue
    if not any(mail.search(occ[0]) for occ in e.occurrences):
        continue
    if not e.msgstr or "fuzzy" in e.flags:
        print(f"[{'F' if 'fuzzy' in e.flags else ' '}] {e.msgid[:90]!r}")
PY
```

---

## 7. Cuidados ao traduzir

1. **Manter os placeholders intactos** — `%(user)s`, `%(org)s`, `{url}`, `{0}` têm de aparecer iguais no `msgstr`. Trocar `%(user)s` por `%(utilizador)s` parte o template em runtime.
2. **Remover a flag `#, fuzzy`** depois de validar a tradução. O `gettext` **ignora** entradas `fuzzy` em runtime e mostra o texto original em inglês — é a causa silenciosa nº 1 de e-mails que continuam em inglês.
3. **Apagar as linhas `#| msgid …`** que o `pybabel update --previous` deixa para trás. São apenas pistas para o tradutor; quando a nova msgid é multi-linha, podem causar erros de sintaxe no `.po`. Para limpar todas de uma só vez:
   ```bash
   sed -i '/^#|/d' udata/translations/pt/LC_MESSAGES/udata.po
   ```
4. **Português europeu, não brasileiro** — `utilizador` (não "usuário"), `palavra-passe` (não "senha"), `e-mail` (não "email"), `eliminar`/`apagar` (não "deletar"), `ficheiro` (não "arquivo"), `conjunto de dados`, `reutilização`, `etiqueta` (não "tag"), `confidencialidade`, `serviço de dados` para `dataservice`.
5. **Plurais com `ngettext`** precisam dos dois `msgstr[0]` e `msgstr[1]`. O PT-pt tem 2 formas (singular/plural), igual ao inglês.
6. **Marcadores `Plural-Forms` no cabeçalho do `.po`** já estão definidos como `nplurals=2; plural=(n != 1);` — não tocar.

---

## 8. Quando reiniciar serviços

| Alteração                                  | Acão                                               |
| ------------------------------------------ | -------------------------------------------------- |
| Editaste `.po` mas **não** recompilaste    | Sem efeito. Recompilar é obrigatório.              |
| Recompilaste o `.mo`                       | Reiniciar `inv serve` **e** `inv work` (Celery).   |
| Adicionaste idioma novo no `udata.cfg`     | Reiniciar `inv serve` e `inv work`.                |
| Mudaste `DEFAULT_LANGUAGE`                 | Reiniciar `inv serve` e `inv work`.                |

> O Flask-Babel carrega os `.mo` no arranque da app e mantém-nos em cache na thread principal. Sem reiniciar não vês as alterações.

---

## 9. Troubleshooting

### E-mails continuam em inglês depois de traduzir

Verifica por esta ordem:

1. **`.mo` desatualizado**:
   ```bash
   ls -la backend/udata/translations/pt/LC_MESSAGES/udata.{po,mo}
   ```
   Se o `.po` for mais recente que o `.mo`, recompila.

2. **Entrada marcada `fuzzy`** — abre o `.po` e procura `#, fuzzy`. Remove a flag depois de confirmar a tradução.

3. **`prefered_language` do utilizador**:
   ```bash
   uv run python -c "
   from udata.app import standalone, create_app
   app = standalone(create_app())
   with app.app_context():
       from udata.core.user.models import User
       u = User.objects(email='alguem@example.com').first()
       print(u.prefered_language)
   "
   ```

4. **`DEFAULT_LANGUAGE` não carregado** — confirma que o worker está a correr de dentro de `backend/`:
   ```bash
   ps aux | grep celery
   # Deve mostrar working directory `/.../new-dadosgov/backend`
   ```

5. **`udata.cfg` ignorado** — verifica logs do arranque, devem aparecer estas configs:
   ```bash
   uv run python -c "
   from udata.app import standalone, create_app
   app = standalone(create_app())
   print('DEFAULT_LANGUAGE:', app.config['DEFAULT_LANGUAGE'])
   print('LANGUAGES:', list(app.config['LANGUAGES'].keys()))
   "
   ```

### `pybabel compile` falha com `unknown keyword`

Há linhas `#| msgid ""` mal formadas (multi-linha colapsada) no `.po`. Corre:

```bash
sed -i '/^#|/d' backend/udata/translations/pt/LC_MESSAGES/udata.po
uv run pybabel compile -d backend/udata/translations
```

### Traduções aparecem cortadas com `…` no e-mail

`LabelledContent.truncated_at` (em `udata/mail.py`) trunca o conteúdo do utilizador (não a tradução) aos 200 caracteres. É comportamento normal — não é problema de tradução.

### Conflitos no `.po` em rebases

São quase sempre triviais: cada bloco do `.po` é independente. Se o conflito for em entradas de e-mail, prefere a versão com a tradução PT-pt. Recompila no fim:

```bash
uv run pybabel compile -d backend/udata/translations
```

---

## Resumo dos comandos essenciais

```bash
cd backend

# Após adicionar/alterar _() no código:
uv run pybabel extract -F babel.cfg -o udata/translations/udata.pot udata
uv run pybabel update -i udata/translations/udata.pot -d udata/translations --previous

# Após traduzir o .po:
uv run pybabel compile -d udata/translations --statistics
```
