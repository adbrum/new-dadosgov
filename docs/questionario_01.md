# Questionário F5/WAF — Preparação da aplicação para os crivos de segurança

> **De:** Equipa de desenvolvimento dados.gov.pt
> **Para:** Equipa de Comunicações / Infraestrutura (responsável pelo F5/WAF)
> **Data:** 2026-06-05
> **Contexto:** A aplicação dados.gov.pt (backend Flask + frontend Next.js) corre em PPR/PRD atrás do F5/WAF (VIP 62.28.186.196). Três incidentes em produção tiveram origem na interação entre o appliance e a aplicação (detalhe em `infra-adc-waf-impact-ppr-prd.md`). Cada pergunta abaixo indica o **evento** que a motiva — incidente já ocorrido, evidência capturada, ou risco identificado e ainda não coberto. Pedimos resposta a todas, mesmo que seja "não aplicável".

---

## 1. Política WAF/ASM — âmbito geral

**1.1.** Que política de segurança está aplicada aos virtual servers de PPR e PRD (nome/versão da política ASM/Advanced WAF)? É exatamente a mesma nos dois ambientes?
**Evento:** Capturas de 2026-06-04 mostram cookies injetados (`cookiesession1`, `cookie_adc_ext`) e padrões de headers idênticos em PPR e PRD, sugerindo a mesma política — mas nunca foi confirmado formalmente.

**1.2.** A política está em modo **blocking** ou **transparent** (só alertas)? Se blocking, desde quando?
**Evento:** Sem incidente registado — desconhecemos se pedidos legítimos já foram silenciosamente bloqueados; nunca recebemos qualquer relatório de bloqueios.

**1.3.** Que conjuntos de assinaturas de ataque estão ativos (e.g. SQL injection, XSS, command injection, path traversal)? Com que frequência são atualizados?
**Evento:** Risco preventivo — o portal aceita texto livre do público (descrições de datasets, discussões) que pode conter padrões semelhantes a ataques (exemplos de código, SQL em documentação).

**1.4.** Existe staging de assinaturas novas (período de observação antes de bloquear), ou entram diretamente em enforcement?
**Evento:** Padrão comum dos três incidentes documentados: alterações do lado do appliance manifestam-se primeiro em produção, sem aviso prévio à equipa de desenvolvimento (secção 4.4 de `infra-adc-waf-impact-ppr-prd.md`).

**1.5.** Quando um pedido é bloqueado, o que recebe o cliente — código HTTP, página de bloqueio, _support ID_? Podemos ter um exemplo da resposta de bloqueio para a reconhecermos nos nossos logs?
**Evento:** Nos incidentes de 2026 o diagnóstico exigiu engenharia inversa por capturas de headers; não sabemos sequer reconhecer uma resposta de bloqueio do WAF nos nossos logs.

## 2. Corpo dos pedidos — limites e tipos de conteúdo

**2.1.** Qual é o **tamanho máximo de request body** permitido pelo WAF? E o tamanho máximo analisado (buffer de inspeção)?
**Evento:** Risco preventivo — o portal aceita upload de ficheiros de dados (CSV, JSON, ZIP, XML, GeoJSON) que podem atingir dezenas/centenas de MB; um limite desconhecido no WAF resultaria em uploads falhados sem causa visível nos nossos logs.

**2.2.** Há restrições de **Content-Type**? `multipart/form-data` (uploads), `application/json` (API), `application/x-www-form-urlencoded` (formulários e SAML POST) estão todos permitidos?
**Evento:** Risco preventivo — os três Content-Types são usados em fluxos críticos (upload de recursos, API pública, login CMD).

**2.3.** Conteúdo de campos JSON com padrões tipo SQL/HTML/script (e.g. uma descrição de dataset que contenha `SELECT * FROM…` ou `<script>` num exemplo) é bloqueado pelas assinaturas? Existe parsing JSON-aware ou as assinaturas correm sobre o body em bruto?
**Evento:** Risco preventivo — datasets técnicos (e.g. de informática, estatística) incluem legitimamente fragmentos de código nas descrições; um falso positivo aqui bloquearia a publicação.

**2.4.** Ficheiros comprimidos (ZIP) ou binários em upload são inspecionados/bloqueados (antivírus, deteção de conteúdo)? Há tipos de ficheiro proibidos?
**Evento:** Risco preventivo — uma parte significativa dos recursos publicados no portal são ZIP/binários.

**2.5.** Qual o limite de **tamanho de URL** e de **query string**?
**Evento:** Risco preventivo — a API usa filtros compostos (`?tag=a&tag=b&geozone=…&temporal_coverage=…`) que geram URLs longos; a pesquisa também propaga o estado completo na query string.

## 3. Métodos HTTP e normalização de URLs

**3.1.** Que métodos HTTP são permitidos? `PUT`, `PATCH` e `DELETE` passam sem restrição?
**Evento:** Risco preventivo — a API REST (`/api/1`, `/api/2`) usa os cinco métodos; WAFs com perfil conservador bloqueiam frequentemente os três últimos.

**3.2.** O header `X-HTTP-Method-Override` é permitido ou removido/bloqueado?
**Evento:** A aplicação suporta override de método para clientes limitados a GET/POST (implementação documentada em `docs/http-method-override.md`); se o appliance remover o header, esses clientes recebem comportamento errado sem erro explícito.

**3.3.** Que normalizações de URL faz o appliance (decode de `%xx`, colapso de `//`, remoção de `..`)? Caracteres UTF-8 percent-encoded em paths (e.g. `/datasets/educa%C3%A7%C3%A3o`) são aceites?
**Evento:** Risco preventivo — os slugs de datasets e organizações portuguesas contêm acentuação; uma normalização agressiva partiria URLs públicos já indexados.

**3.4.** Há bloqueio de caracteres específicos em query strings (aspas, parênteses, `;`, `|`)?
**Evento:** Risco preventivo — a pesquisa full-text envia input livre do utilizador em `?q=`; pesquisas legítimas (e.g. `q=orçamento (2024)`) não podem ser bloqueadas.

## 4. Cookies

**4.1.** A política de reescrita de cookies (re-anexar `SameSite=Lax`, `Secure`, `HttpOnly`) continua ativa? A que cookies se aplica?
**Evento:** **Incidente 4.1 (PRD)** — o appliance re-anexava `SameSite=Lax` ao cookie de sessão (`set-cookie: session=…; SameSite=None; SameSite=Lax`); o browser honrava o último atributo e descartava o cookie no POST cross-site do autenticacao.gov.pt, partindo o login CMD com erro 500 no passo final.

**4.2.** É possível **isentar o cookie `session`** da aplicação dessa reescrita? Se sim, que processo seguimos para o pedir formalmente?
**Evento:** Mesmo incidente 4.1 — alterar a configuração da aplicação (`SESSION_COOKIE_SAMESITE='None'`) não resolvia, porque o appliance reescrevia por cima; a aplicação teve de ser redesenhada (estado SAML espelhado em Redis, commit backend `aeb6d768`). A isenção evitaria nova dependência deste workaround.

**4.3.** Os cookies injetados pelo ADC (`cookiesession1`, `cookie_adc_ext`) são obrigatórios para a persistência do pool? Que método de persistência está configurado? A mudança de membro do pool a meio de uma sessão tem impacto?
**Evento:** Capturas de 2026-06-04 — ambos os cookies aparecem em todas as respostas de PPR/PRD (o padrão `rs1|…` identifica o _real server_); desconhecemos as implicações para sessões longas.

**4.4.** Há limite ao número/tamanho total de cookies por pedido?
**Evento:** Risco preventivo — somam-se o cookie `session` (Flask), cookies do Next.js e os 2 injetados pelo ADC; o cookie de sessão Flask transporta dados serializados e pode crescer.

**4.5.** O WAF valida/assina cookies da aplicação (cookie tampering protection)? Isso interfere com cookies que a aplicação legitimamente regenera (rotação de sessão no login)?
**Evento:** Risco preventivo — a aplicação regenera o cookie de sessão na autenticação; uma proteção de tampering mal afinada classificaria a rotação como adulteração.

## 5. Headers — injeção, remoção e encaminhamento

**5.1.** O F5 envia **`X-Forwarded-For` com o IP real do cliente** até ao backend? Em que formato? Podemos contar com isso como garantia contratual?
**Evento:** **Incidente 4.2 (PRD)** — atrás do F5, o backend via todos os utilizadores com o mesmo IP de origem; o rate-limit por IP em `/api/1/me/` somava os pedidos de todos como se fossem um só → 429 → o frontend interpretava como sessão expirada → logouts aleatórios em massa. O fix aplicacional (rate-limit por utilizador + propagação de `X-Forwarded-For`) só é fiável se o F5 preservar o IP real.

**5.2.** Que outros headers o F5 acrescenta/modifica no caminho cliente→backend (`X-Forwarded-Proto`, `X-Forwarded-Host`, `Via`…)?
**Evento:** **Incidente 4.3** — o `X-Forwarded-Proto: https` adicionado pela cadeia de terminação TLS ativou a validação CSRF estrita do framework (`WTF_CSRF_SSL_STRICT`), que rejeitava com 400/401 pedidos servidor-a-servidor legítimos sem `Referer`, bloqueando o login local.

**5.3.** Headers de pedido não-standard são removidos? A aplicação usa `X-API-KEY` (autenticação API), `X-CSRFToken` e `X-HTTP-Method-Override`.
**Evento:** Risco preventivo — a remoção silenciosa de qualquer um destes três quebraria, respetivamente, todos os clientes API, todos os POSTs autenticados, e o override de método.

**5.4.** No sentido backend→cliente, é possível **deixar de injetar os headers que a aplicação já envia** (`X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Cache-Control`) e **remover o `X-XSS-Protection`**?
**Evento:** Capturas de 2026-06-04 — em PPR/PRD cada um destes headers aparece duplicado (a aplicação envia, o appliance injeta por cima), e o `X-XSS-Protection` (obsoleto; a funcionalidade que ativava foi ela própria fonte de vulnerabilidades) é injetado apesar de a aplicação deliberadamente não o enviar. Headers duplicados/contraditórios têm comportamento indefinido nos browsers.

**5.5.** O header `Referer` é preservado integralmente em pedidos cross-origin (e.g. POST vindo de `autenticacao.gov.pt`)? Alguma política o trunca para origem apenas?
**Evento:** Mesmo incidente 4.3 — o fix aplicacional (commit frontend `73e2733c`) passou a enviar o `Referer` explicitamente nos pedidos proxied; se o appliance o remover ou truncar, o bloqueio CSRF 400/401 regressa.

## 6. Fluxo SAML / autenticação CMD

**6.1.** O endpoint `/saml/acs` (POST cross-site com payload base64 volumoso, origem `autenticacao.gov.pt`) tem alguma regra/exceção específica? Já houve bloqueios registados nesse path?
**Evento:** **Incidente 4.1** ocorreu precisamente neste fluxo (por via dos cookies); o padrão do pedido — POST externo com `SAMLResponse` em base64 que pode exceder 100 KB — é também o tipo de payload que assinaturas WAF genéricas classificam como suspeito. É o ponto único de falha do login CMD.

**6.2.** Há limite de tamanho para um único campo de formulário (`SAMLResponse`)?
**Evento:** Risco preventivo — o tamanho do `SAMLResponse` varia com os atributos devolvidos pelo IdP; um limite por campo abaixo de ~200 KB partiria logins de forma intermitente e difícil de diagnosticar.

**6.3.** Redirects 302 com query strings longas (`RelayState`, `SAMLRequest`) passam sem truncagem?
**Evento:** O fix do incidente 4.1 (commit `aeb6d768`) tornou o `RelayState` portador do identificador de estado da sessão SAML — a truncagem desta query string voltaria a partir o login CMD.

## 7. Rate-limiting, DoS e bot defense no próprio F5

**7.1.** Existe rate-limiting/L7 DoS protection no F5 (pedidos/segundo por IP, por URL)? Com que limiares?
**Evento:** Incidente 4.2 mostrou que limites baseados em IP atrás de NAT colapsam todos os utilizadores num só; precisamos de saber se o F5 aplica limites próprios que possam disparar com tráfego legítimo agregado.

**7.2.** Existe **bot defense / browser challenge** (JavaScript challenge, CAPTCHA)? Isso afeta clientes API legítimos?
**Evento:** Risco preventivo — a API pública (`/api/1`, `/api/2`) é consumida por scripts, harvesters de outros portais de dados abertos e integrações governamentais que não executam JavaScript; um challenge bloqueá-los-ia em massa.

**7.3.** Crawlers e clientes programáticos (curl, python-requests) são tratados de forma diferente por User-Agent?
**Evento:** Evidência de 2026-06-04 — as capturas `curl` à PPR/PRD funcionaram, mas não sabemos se há políticas diferenciadas por User-Agent que afetem harvesting ou indexação (SEO do portal).

**7.4.** Quando fizermos **testes de carga autorizados**, que procedimento devemos seguir para o tráfego não ser bloqueado/desviado e não gerar alarmes na vossa equipa?
**Evento:** Teste de carga real de 2026-06-04 em PPR (`scripts/loadtest_me_ratelimit.py`, 360 pedidos agregados de um único IP, travessia do F5 confirmada pelos cookies injetados) — correu sem coordenação prévia convosco; queremos formalizar o procedimento antes do próximo.

## 8. Timeouts e ligações

**8.1.** Quais são os timeouts do F5: idle timeout da ligação, tempo máximo de resposta do servidor, tempo máximo de upload?
**Evento:** Risco preventivo — o backend tem timeouts internos calibrados (60 s por pedido; 600 s para downloads CSV); se o F5 cortar antes, o utilizador vê um erro que os nossos logs não explicam (o pedido aparece como bem-sucedido do nosso lado).

**8.2.** Downloads longos (exports CSV de centenas de MB, streaming) são afetados por buffering ou limites de duração?
**Evento:** Risco preventivo — o limite de 600 s para `.csv` no uwsgi existe precisamente porque há exports longos; buffering integral no appliance duplicaria o tempo percebido e a memória consumida.

**8.3.** Keep-alive/HTTP2 entre F5 e backend: que versão de HTTP é usada no lado servidor? Há multiplexing?
**Evento:** Risco preventivo — o tuning anti-502 do uwsgi (2025-12: `listen=1024`, `so-keepalive`, `thunder-lock`) foi feito às cegas quanto ao comportamento de ligação do lado F5.

## 9. TLS

**9.1.** Que versões de TLS e cipher suites estão ativas no lado cliente do VIP? TLS 1.3 está disponível?
**Evento:** Risco preventivo — requisitos de conformidade e compatibilidade de clientes API antigos; nunca recebemos a especificação do perfil TLS do VIP.

**9.2.** O tráfego F5→backend segue em HTTPS ou HTTP? Que certificado é esperado do lado do backend (validação ativa?)?
**Evento:** Incidente 4.3 nasceu da terminação TLS intermediária — conhecer a cadeia exata (onde termina, onde re-encripta) é necessário para configurar corretamente `X-Forwarded-Proto` e a validação CSRF.

**9.3.** Há re-encriptação com SNI? O hostname enviado ao backend é o público (`prd-dadosgov.arte.gov.pt`) ou interno?
**Evento:** Risco preventivo — a aplicação gera URLs absolutos (links em emails, sitemap, respostas da API) a partir do hostname recebido; um hostname interno produziria links errados expostos ao público.

## 10. Logs, alertas e gestão de incidentes

**10.1.** Que canal podemos usar para, durante um incidente, **consultar os logs do WAF** (pedidos bloqueados/modificados, support IDs)? Qual o SLA desse canal?
**Evento:** Nos incidentes 4.1–4.3, a ausência de acesso aos logs do WAF obrigou a dias de diagnóstico por engenharia inversa de capturas de headers, com utilizadores afetados durante todo esse tempo.

**10.2.** É possível recebermos um **feed/relatório periódico de bloqueios** relativos aos hostnames dados.gov.pt?
**Evento:** Falsos positivos são hoje invisíveis para nós — um utilizador bloqueado pelo WAF não gera qualquer rasto nos logs da aplicação (agora persistidos em `backend/logs/` e `frontend/logs/`), pelo que nem sabemos que aconteceu.

**10.3.** Quando o WAF bloqueia, o evento fica associado a um _support ID_ devolvido ao cliente? Podemos correlacioná-lo convosco?
**Evento:** Risco preventivo — sem um identificador correlacionável, cada queixa de utilizador "a página deu erro" é impossível de triar entre aplicação e appliance.

## 11. Gestão de alterações e paridade de ambientes

**11.1.** Podemos acordar **aviso prévio** (e janela de validação) para qualquer alteração de política no F5 que toque em cookies, headers, redirects, NAT, TLS ou assinaturas em modo blocking?
**Evento:** Padrão comum dos incidentes 4.1–4.3 — qualquer alteração futura de política no F5 pode quebrar PRD sem nenhuma alteração de código do nosso lado, e ninguém o detetará antes dos utilizadores.

**11.2.** Qual o estado do pedido de colocar **TST e DEV atrás do mesmo F5 com as mesmas políticas** (Opção A da secção 6 de `infra-adc-waf-impact-ppr-prd.md`)? Existe restrição de licenciamento/capacidade que o impeça?
**Evento:** Incidentes 4.1 e 4.2 eram **impossíveis de reproduzir** em TST/DEV porque o appliance lá não existe — o ciclo de qualidade está invertido (TST aprova → o erro estreia em produção).

**11.3.** Em alternativa ou complemento, é possível **exportar a configuração relevante** (políticas de reescrita, perfis HTTP/TLS, política ASM) para mantermos uma emulação local alinhada (Opção B)?
**Evento:** A emulação nginx interina (Opção C, secção 6.3 do mesmo documento) cobre apenas os comportamentos já descobertos por engenharia inversa — sem a configuração real, estará sempre um passo atrás da política em produção.

**11.4.** Quem é o ponto de contacto técnico do lado F5 para a aplicação dados.gov.pt, e qual o processo formal para pedir exceções de política (e.g. isenção do cookie `session`, exceção no `/saml/acs`)?
**Evento:** Os pedidos complementares da secção 6.4 de `infra-adc-waf-impact-ppr-prd.md` (preservação de IP, isenção do cookie, headers duplicados) estão por endereçar por não existir um canal formal definido.

---

## Referência

Evidência completa (capturas `curl` de 2026-06-04), descrição detalhada dos incidentes 4.1–4.3 e proposta de paridade de ambientes: `docs/infra-adc-waf-impact-ppr-prd.md`.
