# Autenticação CMD / eIDAS

Documentação da autenticação por **Chave Móvel Digital** e **eIDAS** no dados.gov.pt: como as
identidades governamentais são resolvidas para contas do portal, e o refinamento em curso para
as tornar únicas e inequívocas.

## Nesta pasta

| Documento | O quê |
| --- | --- |
| [`auth-review-ledg-2430.md`](auth-review-ledg-2430.md) | **Espelho do LEDG-2430** — a revisão completa: o estado por ambiente, as duas classes de conta duplicada, as decisões tomadas, e a decomposição pela ordem de implementação com o estado de cada ticket. **Começar aqui.** |

## Regra de sincronização

O `auth-review-ledg-2430.md` é o **espelho** do
[LEDG-2430](https://ticapp.atlassian.net/browse/LEDG-2430), para quem trabalha o refinamento sem
abrir o Jira.

**Alterar um implica alterar o outro no mesmo passo.** Se divergirem, **o Jira prevalece** — é
lá que as decisões são tomadas e comentadas; este espelho está então desatualizado e deve ser
reposto a partir do ticket.

## Documentos do mesmo assunto que ficaram em `docs/`

Não foram movidos para cá porque **são referenciados de outros documentos** (`../infra-adc-waf-impact-ppr-prd.md`,
`../jira-tickets-frontend-backend.md`) e mover partia essas referências — e alguns não são só de
CMD/eIDAS:

| Documento | Relação com este assunto |
| --- | --- |
| [`../migration-plan-of-legacy-accounts-to-CMD-ticket-40.md`](../migration-plan-of-legacy-accounts-to-CMD-ticket-40.md) | O plano original da migração de contas legadas para CMD, com as divergências da implementação final. É o antecedente directo deste refinamento. |
| [`../login-workflow.md`](../login-workflow.md) | O fluxo de autenticação entre o frontend Next.js e o backend Flask. |
| [`../saml-account-merge.md`](../saml-account-merge.md) | A fusão de contas SAML (`merge-saml`, `migrate-nics`). |
| [`../profile-email-change.md`](../profile-email-change.md) | A alteração de email, que o LEDG-2456 modificou para deixar de revelar se um endereço já tem conta. |
| [`../translations-workflow.md`](../translations-workflow.md) | O catálogo pt — cuja lacuna silenciosa (um msgid sem entrada não falha, o `gettext` devolve o próprio msgid) deixou um e-mail de autenticação inteiro em inglês durante meses. |

## Onde vive o código

| Área | Caminho |
| --- | --- |
| Plugin SAML (as duas rotas ACS, o wizard de migração, os e-mails) | `backend/udata/auth/saml/saml_plugin/saml_govpt.py` |
| Identificador da identidade (`extras.auth_nic`) e a razão de não ter prefixo | `backend/udata/core/user/nic.py` |
| Chaves de `extras` do utilizador (`auth_provider`, endereço sintético) | `backend/udata/core/user/constants.py` |
| Formulários e views de autenticação (`change_email`, reCAPTCHA) | `backend/udata/auth/forms.py`, `backend/udata/auth/views.py` |
| E-mails de autenticação | `backend/udata/auth/mails.py` |
| Ecrã de login (separadores CMD, eIDAS, email) | `frontend/src/components/login/` |
| Ecrã de conclusão de registo | `frontend/src/components/login/CompleteRegistration*.tsx` |
| Testes do fluxo SAML | `backend/udata/tests/frontend/test_saml.py` |
| Regressão de enumeração de contas | `backend/udata/tests/test_legacy_vulns_auth_enumeration.py` |
