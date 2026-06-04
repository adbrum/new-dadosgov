# F5/WAF em PPR/PRD: porque causa erros que não existem em TST/DEV - e como obter paridade de ambientes

> **Audiência:** Equipa de Infraestrutura e Comunicações
> **Autor:** Equipa de desenvolvimento dados.gov.pt
> **Data da evidência:** 2026-06-04 (capturas `curl` reais a partir da rede interna, incluídas abaixo)
> **Objetivo:** (1) demonstrar com evidência que os erros que só ocorrem em PPR/PRD têm origem na cadeia de tráfego F5/WAF, ausente em TST/DEV; (2) propor a replicação da mesma estrutura de WAF em TST/DEV para que o desenvolvimento e os testes ocorram em condições literalmente iguais às de produção.

---

## 1. Sumário executivo

A aplicação dados.gov.pt (backend Flask + frontend Next.js) é estável quando o tráfego chega diretamente à VM (TST/DEV). Em PPR e PRD, todo o tráfego atravessa um **appliance F5/WAF** que **modifica ativamente** pedidos e respostas: injeta cookies de persistência, reescreve atributos de cookies da aplicação (`SameSite`), duplica e injeta headers, mascara a identidade do servidor e faz NAT do IP de origem.

Estas modificações já foram a **causa-raiz de múltiplos incidentes em PPR/PRD** (falha no login CMD, logouts em massa, bloqueios CSRF) que, à exceção de um (4.3, reproduzível em TST - ver correção nessa secção), eram **impossíveis de reproduzir em TST/DEV** - porque nesses ambientes o appliance não existe. Cada incidente custou dias de diagnóstico e os utilizadores foram afetados antes de qualquer deteção ser possível.

**Não pedimos a remoção do WAF.** Pedimos que a **mesma estrutura de F5/WAF, com as mesmas políticas, seja colocada à frente de TST/DEV** (secção 6), para que qualquer problema se manifeste primeiro nos ambientes de teste e nunca pela primeira vez em produção.

---

## 2. Topologia atual - a diferença fundamental

Mapeamento dos ambientes e evidência de resolução DNS (capturado em 2026-06-04):

| Ambiente | Hostname público           | Resolve para                        | VM de destino |
| -------- | -------------------------- | ----------------------------------- | ------------- |
| **PRD**  | `prd-dadosgov.arte.gov.pt` | **62.28.186.196** (VIP do F5)       | 10.50.37.70   |
| **PPR**  | `ppr-dadosgov.arte.gov.pt` | **62.28.186.196** (o **mesmo** VIP) | 10.52.37.70   |
| **TST**  | - (acesso por IP)          | 10.55.37.38 (a própria VM)          | 10.55.37.38   |

```
PRD/PPR:
  Cliente ──▶ 62.28.186.196 (F5/WAF - VIP partilhado) ──▶ VM 10.50.37.70 (PRD)
                                                      └──▶ VM 10.52.37.70 (PPR)
              ▲ injeta cookies, reescreve SameSite, duplica headers,
                mascara Server, NAT do IP de origem, termina TLS

TST:
  Cliente ──────────────────────────────────────────────▶ VM 10.55.37.38
              (tráfego chega intacto: nginx ──▶ Next.js ──▶ Flask)
```

Factos verificados:

1. **PPR e PRD partilham o mesmo VIP** (62.28.186.196) - o F5 encaminha por hostname. As políticas WAF aplicadas são as mesmas nos dois ambientes (evidência 3.2: cookies injetados idênticos).
2. **As VMs 10.50.37.70 e 10.52.37.70 não respondem a acessos diretos** a partir da rede interna de desenvolvimento - só aceitam tráfego vindo do F5. Correto do ponto de vista de segurança, mas significa que **toda** a interação com PPR/PRD passa obrigatoriamente pelas modificações do appliance.
3. **TST (10.55.37.38) é acedido diretamente**, sem qualquer intermediário.

Consequência: **TST/DEV não são representativos de PPR/PRD.** Qualquer comportamento do F5 só se manifesta depois do deploy para PPR - ou, pior, para PRD.

---

## 3. Evidência capturada (2026-06-04)

### 3.1 TST - resposta limpa, direta da aplicação

```
$ curl -skI https://10.55.37.38/saml/login
HTTP/2 200
server: nginx/1.20.1                  ← banner real
set-cookie: session=eyJ...; HttpOnly; Path=/; SameSite=Lax
                                      ← um único cookie: o da aplicação
```

### 3.2 PPR e PRD - cookies injetados pelo F5 (idênticos nos dois ambientes)

```
$ curl -skI https://ppr-dadosgov.arte.gov.pt/saml/login
HTTP/2 200
server: nginx                         ← versão ocultada
set-cookie: session=eyJ...; Secure; HttpOnly; Path=/; SameSite=Lax
set-cookie: cookiesession1=678B28D04BE1BF67...;Expires=Fri, 04 Jun 2027...;Path=/;HttpOnly
set-cookie: cookie_adc_ext=rs1|aiFVo; path=/; HttpOnly; Secure; SameSite=Lax

$ curl -skI https://prd-dadosgov.arte.gov.pt/saml/login
HTTP/2 200
server: nginx
set-cookie: session=eyJ...; Secure; HttpOnly; Path=/; SameSite=Lax
set-cookie: cookiesession1=678B28D1A55B4BD0...;Expires=Fri, 04 Jun 2027...;Path=/;HttpOnly
set-cookie: cookie_adc_ext=rs1|aiFVo; path=/; HttpOnly; Secure; SameSite=Lax
```

Os cookies `cookiesession1` e `cookie_adc_ext` **não existem no código da aplicação** - são injetados pelo appliance (cookies de persistência/sessão do ADC; o padrão `rs1|…` identifica o _real server_ do pool). O facto de serem idênticos em PPR e PRD confirma que a mesma política é aplicada aos dois.

### 3.3 Headers duplicados e injetados (homepage PPR/PRD vs TST)

PPR e PRD apresentam o mesmo padrão - a aplicação envia o seu conjunto de headers de segurança e o appliance acrescenta outro por cima:

```
x-frame-options: SAMEORIGIN          ← 1.ª ocorrência
...
x-frame-options: SAMEORIGIN          ← 2.ª ocorrência (injetada)
x-content-type-options: nosniff      ← duplicado
referrer-policy: ...                 ← duplicado
cache-control: no-store              ← duplicado (a app já enviou outro valor)
pragma: no-cache                     ← injetado
x-xss-protection: 1; mode=block      ← injetado (header obsoleto que a app
                                        deliberadamente não envia)
```

No TST, cada header aparece uma única vez, com os valores definidos pela aplicação.

### 3.4 Reescrita histórica do `SameSite` (causa do incidente 4.1)

Em capturas anteriores ao fix `aeb6d768`, o `Set-Cookie` da aplicação chegava ao browser através do F5 com **dois atributos SameSite**:

```
set-cookie: session=...; SameSite=None; SameSite=Lax
                          ▲ aplicação     ▲ re-anexado pelo appliance
```

Os browsers honram o último atributo, pelo que o cookie de sessão era tratado como `Lax` e **descartado no POST cross-site** vindo do autenticacao.gov.pt - quebrando o login CMD no passo final (detalhe em 4.1).

### 3.5 Síntese

| Observação                   | TST (10.55.37.38) | PPR (via F5)                       | PRD (via F5)              |
| ---------------------------- | ----------------- | ---------------------------------- | ------------------------- |
| Resolução DNS                | direto à VM       | VIP 62.28.186.196                  | VIP 62.28.186.196 (mesmo) |
| Acesso direto à VM           | sim               | bloqueado (só via F5)              | bloqueado (só via F5)     |
| Banner `Server`              | `nginx/1.20.1`    | `nginx` (ocultado)                 | `nginx` (ocultado)        |
| Cookies injetados            | nenhum            | `cookiesession1`, `cookie_adc_ext` | idênticos a PPR           |
| Headers duplicados/injetados | não               | sim                                | sim                       |
| Reescrita de `SameSite`      | nunca             | confirmada (4.1)                   | confirmada (4.1)          |

---

## 4. Como é que o F5/WAF causa os erros - incidentes documentados

Cada mecanismo abaixo é inofensivo para um site estático, mas **interfere com autenticação, sessões e rate-limiting** - exatamente as áreas onde PPR/PRD falham. Todos os incidentes estão ligados a commits no repositório.

### 4.1 Reescrita de `SameSite` → login CMD com "Internal Server Error" (PPR/PRD)

- **Mecanismo:** política de hardening de cookies do appliance re-anexa `SameSite=Lax` a todos os `Set-Cookie` (3.4).
- **Efeito:** o cookie de sessão é descartado pelo browser no POST cross-site do autenticacao.gov.pt → a sessão chega vazia → a validação SAML rejeita a resposta como não solicitada → erro 500 no passo final do CMD.
- **Porque não acontece em TST:** sem appliance, o cookie chega ao browser exatamente como a aplicação o definiu.
- **Agravante:** mudar a configuração da aplicação (`SESSION_COOKIE_SAMESITE='None'`) **não resolvia** - o appliance continuava a acrescentar o `Lax` por cima.
- **Mitigação aplicacional:** commit `aeb6d768` (backend) - o estado SAML passou a ser espelhado em Redis via RelayState, eliminando a dependência do cookie nesse fluxo. A aplicação teve de ser redesenhada para sobreviver ao appliance.

### 4.2 NAT do IP de origem → logouts aleatórios em massa (PRD)

- **Mecanismo:** atrás do F5 + cadeia de proxies, o backend via **todos os utilizadores com o mesmo IP de origem**.
- **Efeito:** o rate-limit por IP em `/api/1/me/` somava os pedidos de todos os utilizadores como se fossem um só → respostas 429 → o frontend interpretava como sessão expirada → utilizadores "deslogados" aleatoriamente.
- **Porque não acontece em TST:** cada cliente chega com o seu IP real; o limite por IP nunca dispara. Além disso, o volume de tráfego de TST/PPR nunca esgotaria o bucket partilhado - o erro só se manifesta com tráfego real de produção.
- **Mitigação aplicacional:** rate-limit por utilizador autenticado + propagação de `X-Forwarded-For`. Mas isto só é fiável se a cadeia (F5 incluído) **preservar o IP real do cliente** no header - algo que não controlamos nem conseguimos verificar.
- **Validação (2026-06-04):** teste de carga `scripts/loadtest_me_ratelimit.py`, reproduzindo a condição de colapso (12 utilizadores autenticados, 360 pedidos agregados a partir de um único IP de origem - acima do bucket antigo de 200/hora):
  - **TST** (acesso direto): **0×429**; um controlo negativo com 1 utilizador acima de 60/min recebeu 429 exatamente a partir do 61.º pedido, provando que o limiter está ativo e keyed por utilizador;
  - **PPR** (através do F5 real - travessia confirmada pelos cookies `cookiesession1` injetados nas 12 sessões): **0×429** nos mesmos 360 pedidos agregados, p95 = 81 ms. O fix sobrevive à cadeia F5/WAF de produção.
  - A ressalva mantém-se: o rate-limit correto continua dependente da preservação do IP real do cliente pela cadeia (ver 6.4).

### 4.3 Terminação TLS + headers encaminhados → bloqueios CSRF 400/401

- **Mecanismo:** o F5 termina o TLS e o tráfego segue com `X-Forwarded-Proto: https`; isso ativa no framework a validação CSRF estrita para HTTPS (`WTF_CSRF_SSL_STRICT`), que exige a presença e correspondência do header `Referer`.
- **Efeito:** pedidos servidor-a-servidor legítimos sem `Referer` eram rejeitados com 400/401 - login bloqueado.
- **Correção (2026-06-04):** ao contrário do que esta secção afirmava originalmente, este mecanismo **reproduz-se também em TST** - o nginx local do TST também termina TLS e encaminha `X-Forwarded-Proto: https`, ativando a mesma validação estrita. Foi confirmado em TST a 2026-06-04: um build do frontend anterior ao fix bloqueava todos os logins locais com o mesmo 400→401. O incidente estreou em PPR apenas por ordem de deploy, não por diferença de ambiente. Dos três incidentes, este é o único que TST consegue reproduzir; 4.1 e 4.2 continuam exclusivos da cadeia F5.
- **Mitigação aplicacional:** commit `73e2733c` (frontend) - encaminhar explicitamente o `Referer` nos pedidos proxied.

### 4.4 O padrão comum

1. O erro **só existe atrás do F5** (4.1 e 4.2; o 4.3 reproduz-se em qualquer cadeia com terminação TLS, incluindo o nginx do TST) → TST/DEV não servem para reproduzir nem para validar os fixes; a validação real acontece em PPR ou diretamente em PRD, com utilizadores afetados.
2. O diagnóstico exige **engenharia inversa do appliance** a partir de capturas de headers, porque a equipa de desenvolvimento não tem acesso às políticas nem aos logs do WAF.
3. A correção acaba sempre por ser feita **no lado da aplicação**, aumentando a complexidade do código. E permanece o risco estrutural: **qualquer alteração futura de política no F5 pode quebrar PRD sem nenhuma alteração de código**, e ninguém o detetará antes dos utilizadores.

---

## 5. Porque é que isto não se resolve "apenas do lado da aplicação"

- A aplicação não consegue impedir o appliance de reescrever cookies, duplicar headers ou esconder IPs - só pode tentar sobreviver, caso a caso, **depois** de cada incidente já ter afetado PPR/PRD.
- O ciclo de qualidade está invertido: TST aprova → o erro estreia em produção. É o oposto do propósito de um ambiente de testes.
- Sem paridade, cada deploy para PPR/PRD é um salto no escuro relativamente a tudo o que toque em cookies, sessões, redirects, IPs e TLS.

---

## 6. Proposta: a mesma estrutura de F5/WAF em TST/DEV

### 6.1 Opção A (recomendada) - VIP de TST e DEV no F5 existente

Criar no **mesmo F5** que já serve PPR/PRD um _virtual server_ adicional para TST e DEV:

```
Proposto:
  Cliente ──▶ F5 (62.28.186.196 ou VIP interno) ──▶ VM 10.55.37.38 (TST)
              hostname: fe01tstdadosgov.srv.ama.lan

  Cliente ──▶ F5 (62.28.186.196 ou VIP interno) ──▶ VM 172.31.204.12 (DEV)
              hostname: fe01devdadosgov.srv.ama.lan
```

- **Reutilizar exatamente os mesmos perfis e políticas** de PPR/PRD: política WAF/ASM, perfil de persistência de cookies (`cookiesession1`/`cookie_adc_ext`), perfil HTTP (reescrita de headers), perfil TLS do lado do cliente.
- Esforço estimado do lado F5: um _virtual server_ + um _pool_ com um membro (10.55.37.38), apontando para perfis/políticas **já existentes** - sem criação de políticas novas.
- Bloquear, como em PPR/PRD, o acesso direto à VM exceto a partir do F5 e da rede de administração - assim a equipa de desenvolvimento testa **obrigatoriamente** nas mesmas condições da produção.
- DNS: registo interno `fe01tstdadosgov.srv.ama.lan` → VIP. Não precisa de exposição pública; basta ser resolvível na rede interna.

**Critério de aceitação** (verificável por qualquer das equipas com os comandos do Anexo A): a resposta de `https://fe01tstdadosgov.srv.ama.lan/saml/login` deve apresentar os mesmos cookies injetados (`cookiesession1`, `cookie_adc_ext`) e o mesmo padrão de headers que PPR/PRD.

### 6.2 Opção B - sincronização de políticas documentada

Se houver restrição de capacidade/licenciamento no F5 para mais um _virtual server_:

- Exportar e partilhar com a equipa de desenvolvimento a configuração relevante (iRules/políticas de reescrita de cookies e headers, política WAF, perfis HTTP/TLS) de PPR/PRD;
- Compromisso de **aviso prévio** sempre que essas políticas mudarem;
- A equipa de desenvolvimento mantém uma emulação local (6.3) alinhada com essa documentação.

É inferior à Opção A porque a emulação estará sempre um passo atrás da política real - mas elimina a atual opacidade total.

### 6.3 Opção C (interina, lado dev) - emulação do comportamento conhecido à frente do TST

Enquanto A ou B não estiverem disponíveis, a equipa de desenvolvimento pode colocar à frente do nginx do TST uma camada que reproduz os comportamentos **já confirmados** do F5:

```nginx
# Emulação F5/WAF (apenas comportamentos confirmados na secção 3)
location / {
    proxy_pass https://backend_tst;

    # 4.2 - colapso do IP de origem (todos os clientes parecem o mesmo IP)
    proxy_set_header X-Forwarded-For 10.0.0.1;

    # 4.3 - terminação TLS intermediária
    proxy_set_header X-Forwarded-Proto https;

    # 3.4/4.1 - re-anexar SameSite=Lax a todos os Set-Cookie
    proxy_cookie_flags ~ samesite=lax;

    # 3.2 - cookies de persistência do ADC
    add_header Set-Cookie "cookiesession1=EMULADO;Path=/;HttpOnly";
    add_header Set-Cookie "cookie_adc_ext=rs1|emulado; path=/; HttpOnly; Secure; SameSite=Lax";

    # 3.3 - duplicação/injeção de headers
    add_header X-Frame-Options SAMEORIGIN;
    add_header X-XSS-Protection "1; mode=block";
    add_header Cache-Control "no-store";
    add_header Pragma "no-cache";
    proxy_hide_header Server;
}
```

Limitação importante: isto só emula o que **já descobrimos por engenharia inversa**. Não cobre regras WAF de bloqueio de payloads, limites de tamanho, timeouts, normalização de URLs, etc. - que são justamente o tipo de coisa que volta a surpreender-nos em produção. **Por isso a Opção A continua a ser o pedido principal.**

### 6.4 Pedidos complementares (independentes da opção escolhida)

1. **Preservação do IP de origem:** garantir que o F5 envia `X-Forwarded-For` com o IP real do cliente até ao backend (necessário para rate-limiting, auditoria e logs - incidente 4.2). Não é só o `/me`: os endpoints de autenticação (login, registo, recuperação de password) têm proteção anti-brute-force limitada por IP. A aplicação já mitigou o pior cenário (o limite de tentativas passou a ser por credencial, com um teto por IP), mas **qualquer limite por IP só funciona se o IP que chega ao backend for o do cliente real** - se o F5 colapsar os IPs, os tetos por IP somam todos os utilizadores de PRD como se fossem um só.
2. **Isenção do cookie `session`:** excluir o cookie de sessão da aplicação da política de reescrita de `SameSite` (causa do incidente 4.1).
3. **Headers duplicados:** deixar de injetar headers que a aplicação já envia (`X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Cache-Control`) - duplicados/contraditórios têm comportamento indefinido nos browsers - e remover o `X-XSS-Protection`, obsoleto e desaconselhado (os browsers modernos ignoram-no; a funcionalidade que ativava foi ela própria fonte de vulnerabilidades).
4. **Gestão de alterações:** comunicação prévia à equipa de desenvolvimento de qualquer alteração de política no F5 que toque em cookies, headers, redirects, NAT ou TLS.
5. **Acesso a logs em incidentes:** canal para consultar os logs do WAF (pedidos bloqueados/modificados) quando há um incidente em PPR/PRD.

---

## 7. Conclusão

Os erros que afetam PPR e PRD não resultam de instabilidade da aplicação - o mesmo código é estável quando o tráfego chega intacto (TST). Resultam do facto de **só PPR/PRD terem à frente um F5/WAF que modifica o tráfego**, e de a equipa de desenvolvimento testar num ambiente onde essas modificações não existem. A solução estrutural é simples de enunciar e, na Opção A, de implementar: **pôr o TST e o DEV atrás do mesmo F5, com as mesmas políticas**. A partir daí, qualquer interação entre o appliance e a aplicação manifesta-se primeiro em TST e DEV - onde deve - e PPR/PRD deixam de ser o local onde estes problemas são descobertos.

---

## Anexo A - Comandos de verificação (reproduzíveis por qualquer equipa)

```bash
# 1. Resolução DNS - PPR e PRD partilham o VIP do F5; TST é direto
getent hosts ppr-dadosgov.arte.gov.pt    # → 62.28.186.196
getent hosts prd-dadosgov.arte.gov.pt    # → 62.28.186.196 (o mesmo VIP)

# 2. Cookies injetados pelo F5 (cookiesession1, cookie_adc_ext) - só via hostname
curl -skI https://ppr-dadosgov.arte.gov.pt/saml/login | grep -i set-cookie
curl -skI https://prd-dadosgov.arte.gov.pt/saml/login | grep -i set-cookie
curl -skI https://10.55.37.38/saml/login              | grep -i set-cookie  # TST: só 'session'

# 3. Headers duplicados em PPR/PRD (cada um aparece 2x; no TST, 1x)
curl -skI https://ppr-dadosgov.arte.gov.pt/ | grep -ic x-frame-options   # → 2
curl -skI https://10.55.37.38/              | grep -ic x-frame-options   # → 1

# 4. VMs de PPR/PRD inacessíveis diretamente (só o F5 lhes chega)
curl -skI --max-time 10 https://10.52.37.70/   # timeout
curl -skI --max-time 10 https://10.50.37.70/   # timeout
```

## Anexo B - Referências internas

- Commit backend `aeb6d768` - `fix(saml): mirror outstanding bucket to Redis via RelayState` (incidente 4.1; a descrição do commit documenta a reescrita do SameSite pelo appliance)
- Commit frontend `73e2733c` - `fix: send Referer on proxied backend requests to satisfy SSL-strict CSRF` (incidente 4.3)
- Fix de rate-limit por utilizador em `/api/1/me/` + propagação de `X-Forwarded-For` (incidente 4.2)
- `scripts/loadtest_me_ratelimit.py` - teste de carga que valida o fix do incidente 4.2 sob condições de colapso de IP (executado com sucesso em TST a 2026-06-04; execução em PPR pendente)
- Rate-limit de autenticação em dois níveis (por credencial + teto por IP) em `udata/auth/views.py`, com suite de regressão em `udata/tests/test_auth_ratelimit_ip_collapse.py` - mitigação preventiva do colapso de IP nos endpoints de auth (secção 6.4, ponto 1)
- `docs/login-workflow.md`, `docs/saml-account-merge.md`
