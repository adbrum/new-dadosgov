# Questionário F5/WAF — Versão prioritária (eventos de 2026-06-04 e pontos críticos)

> **De:** Equipa de desenvolvimento dados.gov.pt
> **Para:** Equipa de Comunicações / Infraestrutura (responsável pelo F5/WAF)
> **Data:** 2026-06-05
> **Âmbito:** Versão condensada do questionário completo (`questionario-f5-waf-comunicacoes.md`). Contém apenas (A) as perguntas ligadas aos eventos levantados a **2026-06-04** — capturas de evidência, teste de carga em PPR e confirmação do mecanismo CSRF — e (B) as perguntas mais críticas, associadas aos incidentes que já afetaram utilizadores em produção. A numeração original é mantida entre parênteses para cruzamento com o questionário completo.

---

## A. Eventos levantados a 2026-06-04

**A.1.** (1.1) Que política de segurança está aplicada aos virtual servers de PPR e PRD (nome/versão da política ASM/Advanced WAF)? É exatamente a mesma nos dois ambientes?
**Evento (2026-06-04):** As capturas `curl` mostram cookies injetados (`cookiesession1`, `cookie_adc_ext`) e padrões de headers idênticos em PPR e PRD, sugerindo a mesma política — mas nunca foi confirmado formalmente.

**A.2.** (4.3) Os cookies injetados pelo ADC (`cookiesession1`, `cookie_adc_ext`) são obrigatórios para a persistência do pool? Que método de persistência está configurado? A mudança de membro do pool a meio de uma sessão tem impacto?
**Evento (2026-06-04):** Ambos os cookies aparecem em todas as respostas capturadas em PPR/PRD (o padrão `rs1|…` identifica o _real server_); desconhecemos as implicações para sessões longas.

**A.3.** (5.4) No sentido backend→cliente, é possível **deixar de injetar os headers que a aplicação já envia** (`X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Cache-Control`) e **remover o `X-XSS-Protection`**?
**Evento (2026-06-04):** Nas capturas, cada um destes headers aparece duplicado em PPR/PRD (a aplicação envia, o appliance injeta por cima), e o `X-XSS-Protection` — obsoleto e desaconselhado — é injetado apesar de a aplicação deliberadamente não o enviar. Headers duplicados/contraditórios têm comportamento indefinido nos browsers.

**A.4.** (7.4) Quando fizermos **testes de carga autorizados**, que procedimento devemos seguir para o tráfego não ser bloqueado/desviado e não gerar alarmes na vossa equipa?
**Evento (2026-06-04):** Teste de carga real em PPR (`scripts/loadtest_me_ratelimit.py`, 360 pedidos agregados de um único IP, travessia do F5 confirmada pelos cookies injetados nas 12 sessões) — correu sem coordenação prévia convosco; queremos formalizar o procedimento antes do próximo.

**A.5.** (5.2) Que headers o F5 acrescenta/modifica no caminho cliente→backend (`X-Forwarded-Proto`, `X-Forwarded-Host`, `Via`…)?
**Evento (2026-06-04):** Foi confirmado em TST que o `X-Forwarded-Proto: https` da cadeia de terminação TLS ativa a validação CSRF estrita do framework (`WTF_CSRF_SSL_STRICT`) — o mesmo mecanismo do incidente 4.3 que bloqueou logins com 400/401. Precisamos do inventário exato do que o F5 acrescenta para configurar a validação corretamente.

**A.6.** (9.2) O tráfego F5→backend segue em HTTPS ou HTTP? Que certificado é esperado do lado do backend (validação ativa?)?
**Evento (2026-06-04):** A confirmação do mecanismo CSRF (acima) mostrou que o comportamento da aplicação depende diretamente de onde o TLS termina e re-encripta — a cadeia exata nunca nos foi comunicada.

## B. Pontos críticos — incidentes com utilizadores afetados em produção

**B.1.** (4.1) A política de reescrita de cookies (re-anexar `SameSite=Lax`, `Secure`, `HttpOnly`) continua ativa? A que cookies se aplica?
**Evento — incidente 4.1 (PRD):** O appliance re-anexava `SameSite=Lax` ao cookie de sessão (`session=…; SameSite=None; SameSite=Lax`); o browser honrava o último atributo e descartava o cookie no POST cross-site do autenticacao.gov.pt — **login CMD inutilizável**, erro 500 no passo final.

**B.2.** (4.2) É possível **isentar o cookie `session`** da aplicação dessa reescrita? Que processo seguimos para o pedir formalmente?
**Evento — incidente 4.1:** Alterar a configuração da aplicação não resolvia — o appliance reescrevia por cima; a aplicação teve de ser redesenhada (estado SAML espelhado em Redis, commit backend `aeb6d768`). A isenção eliminaria a dependência deste workaround.

**B.3.** (5.1) O F5 envia **`X-Forwarded-For` com o IP real do cliente** até ao backend? Em que formato? Podemos contar com isso como garantia contratual?
**Evento — incidente 4.2 (PRD):** Atrás do F5, o backend via todos os utilizadores com o mesmo IP de origem; o rate-limit por IP em `/api/1/me/` somava os pedidos de todos → 429 → o frontend interpretava como sessão expirada → **logouts aleatórios em massa**. O fix aplicacional só é fiável se o F5 preservar o IP real.
**Agravamento (validado em TST, 2026-06-09):** o mesmo colapso afeta a **pesquisa pública anónima** que popula as páginas de listagem (`GET /api/1/{datasets,organizations,reuses}/?q=…`). Sendo tráfego **anónimo, não há mitigação aplicacional possível** (sem utilizador para chave do limite); o balde por IP torna-se um teto **agregado de todos os visitantes** e a pesquisa deixa de funcionar para todos ao fim de algumas centenas de pesquisas/hora somadas — **DoS trivial**. Reproduzido com `scripts/loadtest_search_ratelimit.py`: através da emulação do appliance, pedidos com `X-Forwarded-For` distinto por pedido (visitantes diferentes) colapsaram num único balde e foram bloqueados com 429. **Preservar o IP real é a única correção estrutural; subir o teto só adia o bloqueio.**

**B.4.** (5.5) O header `Referer` é preservado integralmente em pedidos cross-origin (e.g. POST vindo de `autenticacao.gov.pt`)? Alguma política o trunca para origem apenas?
**Evento — incidente 4.3:** Pedidos legítimos sem `Referer` eram rejeitados com 400/401 pela validação CSRF estrita — **login bloqueado**. O fix (commit frontend `73e2733c`) envia o `Referer` explicitamente; se o appliance o remover ou truncar, o bloqueio regressa.

**B.5.** (6.1) O endpoint `/saml/acs` (POST cross-site com payload base64 volumoso, origem `autenticacao.gov.pt`) tem alguma regra/exceção específica? Já houve bloqueios registados nesse path?
**Evento — incidente 4.1:** Ocorreu precisamente neste fluxo; o padrão do pedido — POST externo com `SAMLResponse` em base64 que pode exceder 100 KB — é também o tipo de payload que assinaturas WAF genéricas classificam como suspeito. É o ponto único de falha do login CMD.

**B.6.** (6.3) Redirects 302 com query strings longas (`RelayState`, `SAMLRequest`) passam sem truncagem?
**Evento — incidente 4.1 (fix):** O commit `aeb6d768` tornou o `RelayState` portador do identificador de estado da sessão SAML — a truncagem desta query string voltaria a partir o login CMD.

**B.7.** (10.1) Que canal podemos usar para, durante um incidente, **consultar os logs do WAF** (pedidos bloqueados/modificados, support IDs)? Qual o SLA desse canal?
**Evento — incidentes 4.1–4.3:** A ausência de acesso aos logs do WAF obrigou a dias de diagnóstico por engenharia inversa de capturas de headers, com utilizadores afetados durante todo esse tempo.

**B.8.** (11.1) Podemos acordar **aviso prévio** (e janela de validação) para qualquer alteração de política no F5 que toque em cookies, headers, redirects, NAT, TLS ou assinaturas em modo blocking?
**Evento — padrão comum 4.1–4.3:** Qualquer alteração futura de política no F5 pode quebrar PRD sem nenhuma alteração de código do nosso lado, e ninguém o detetará antes dos utilizadores.

**B.9.** (11.2) Qual o estado do pedido de colocar **TST e DEV atrás do mesmo F5 com as mesmas políticas** (Opção A da secção 6 de `infra-adc-waf-impact-ppr-prd.md`)? Existe restrição de licenciamento/capacidade que o impeça?
**Evento — incidentes 4.1 e 4.2:** Eram **impossíveis de reproduzir** em TST/DEV porque o appliance lá não existe — o ciclo de qualidade está invertido: TST aprova, o erro estreia em produção.

---

## Referência

- Questionário completo (11 secções, ~45 perguntas): `docs/questionario-f5-waf-comunicacoes.md`
- Evidência e detalhe dos incidentes: `docs/infra-adc-waf-impact-ppr-prd.md`
