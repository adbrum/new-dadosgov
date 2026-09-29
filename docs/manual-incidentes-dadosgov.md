# Manual de resolução de incidentes - dados.gov.pt

> Manual "como fazer" que desenvolve o ponto 7 ("Erros e Incidentes Frequentes") do Relatório de Encerramento do Projeto L11 - Evolução do Dados.gov e integração de Dados de Elevado Valor (HVD). Cada linha da tabela desse ponto é aqui um capítulo, do sintoma à resolução confirmada.
>
> Versão: 2026-09-29 · Ticket: LEDG-2569 · Comandos, caminhos e parâmetros verificados contra `develop` de `amagovpt/udata-pt` (commit `1fe3e8ad6`) e de `amagovpt/dadosgov-fe` (commit `61cae2aa`) - ver [A3](#a3-registo-da-verificação).

## Índice

- [1. Introdução](#1-introdução)
    - [1.1 Objetivo](#11-objetivo)
    - [1.2 Público-alvo](#12-público-alvo)
    - [1.3 Como está organizado](#13-como-está-organizado)
- [2. Pré-requisitos comuns](#2-pré-requisitos-comuns)
    - [PC-0. Ambientes, acessos e contactos](#pc-0-ambientes-acessos-e-contactos)
    - [PC-0b. Onde corre cada serviço](#pc-0b-onde-corre-cada-serviço)
    - [PC-1. Executar comandos `udata`](#pc-1-executar-comandos-udata)
    - [PC-2. Consultar registos](#pc-2-consultar-registos)
    - [PC-3. Estado dos containers](#pc-3-estado-dos-containers)
    - [PC-4. Reinício de serviços](#pc-4-reinício-de-serviços)
    - [PC-5. Filas Celery e jobs agendados](#pc-5-filas-celery-e-jobs-agendados)
    - [PC-6. Migrações da base de dados](#pc-6-migrações-da-base-de-dados)
    - [PC-7. Reindexação da pesquisa](#pc-7-reindexação-da-pesquisa)
    - [PC-8. Pedido direto à VM ou através do F5](#pc-8-pedido-direto-à-vm-ou-através-do-f5)
    - [PC-9. Limpar a cache da aplicação](#pc-9-limpar-a-cache-da-aplicação)
    - [PC-10. Ler a configuração efetiva sem expor segredos](#pc-10-ler-a-configuração-efetiva-sem-expor-segredos)
    - [PC-11. Smoke-test](#pc-11-smoke-test)
- [3. Capítulos por incidente](#3-capítulos-por-incidente)
    - [1. Harvesting nacional](#1-harvesting-nacional)
    - [2. Harvesting do Portal Europeu de Dados](#2-harvesting-do-portal-europeu-de-dados)
    - [3. Indexação e pesquisa](#3-indexação-e-pesquisa)
    - [4. Gestão de organizações e datasets](#4-gestão-de-organizações-e-datasets)
    - [5. Autenticação CMD](#5-autenticação-cmd)
    - [6. Problemas de publicação de conjuntos de dados](#6-problemas-de-publicação-de-conjuntos-de-dados)
    - [7. Indisponibilidade de serviços](#7-indisponibilidade-de-serviços)
    - [8. Problemas de base de dados](#8-problemas-de-base-de-dados)
    - [9. Problemas na apresentação das estatísticas na homepage](#9-problemas-na-apresentação-das-estatísticas-na-homepage)
    - [10. Falhas de armazenamento](#10-falhas-de-armazenamento)
    - [11. Problemas de certificados/keys](#11-problemas-de-certificadoskeys)
    - [12. Reinício de serviços](#12-reinício-de-serviços)
    - [13. Gestão de backups](#13-gestão-de-backups)
    - [14. Recuperação após falha](#14-recuperação-após-falha)
    - [15. Aplicação de atualizações](#15-aplicação-de-atualizações)
    - [16. Limitações conhecidas da solução](#16-limitações-conhecidas-da-solução)
    - [17. Bugs conhecidos](#17-bugs-conhecidos)
    - [18. Workarounds temporários](#18-workarounds-temporários)
    - [19. E-mail e notificações](#19-e-mail-e-notificações)
    - [20. Bloqueios por rate limit (429)](#20-bloqueios-por-rate-limit-429)
    - [21. Operações de escrita bloqueadas pelo WAF (PUT/PATCH/DELETE)](#21-operações-de-escrita-bloqueadas-pelo-waf-putpatchdelete)
    - [22. Vulnerabilidades reportadas em auditoria de segurança](#22-vulnerabilidades-reportadas-em-auditoria-de-segurança)
    - [23. Contas duplicadas e ligação da identidade CMD](#23-contas-duplicadas-e-ligação-da-identidade-cmd)
    - [24. Organizações criadas indevidamente ou sem administrador](#24-organizações-criadas-indevidamente-ou-sem-administrador)
    - [25. Contactos de datasets colhidos desatualizados ou duplicados](#25-contactos-de-datasets-colhidos-desatualizados-ou-duplicados)
    - [26. Falha da API apresentada como página vazia](#26-falha-da-api-apresentada-como-página-vazia)
    - [27. Pré-visualização de dados e análise Hydra](#27-pré-visualização-de-dados-e-análise-hydra)
    - [28. Erros de apresentação no frontend](#28-erros-de-apresentação-no-frontend)
- [4. Anexos](#4-anexos)
    - [A1. Referências cruzadas](#a1-referências-cruzadas)
    - [A2. Parâmetros de configuração](#a2-parâmetros-de-configuração)
    - [A3. Registo da verificação](#a3-registo-da-verificação)
    - [A4. Glossário](#a4-glossário)

## 1. Introdução

### 1.1 Objetivo

A tabela do ponto 7 do relatório diz, para cada incidente frequente, qual a causa, como se diagnostica e como se resolve. Serve para consulta rápida por quem já conhece a plataforma. Este manual serve para quem não a conhece: cada capítulo leva do que se observa até à confirmação de que o problema ficou resolvido, com os comandos exatos e o resultado esperado em cada passo.

### 1.2 Público-alvo

- Equipa de operação e manutenção que venha a assumir o dados.gov.pt.
- Equipa de infraestrutura (F5/WAF, VMs, MongoDB, Redis, CMS), nos capítulos em que a causa está do seu lado.
- Equipa de desenvolvimento, como referência do que já foi diagnosticado e corrigido.

Assume-se conhecimento de Linux, Docker e HTTP. Não se assume conhecimento de udata, Flask, Celery ou Next.js.

### 1.3 Como está organizado

- **Secção 2 - Pré-requisitos comuns:** acessos, ambientes, onde corre cada serviço e os procedimentos partilhados (PC-1 a PC-11). São descritos uma única vez; os capítulos remetem para eles em vez de os repetir.
- **Secção 3 - Capítulos por incidente:** um capítulo por linha da tabela do ponto 7, sempre com as mesmas cinco secções:
    - **Sintoma** - o que o utilizador ou o operador vê.
    - **Diagnóstico passo a passo** - comandos, registos e endpoints a consultar, com o resultado esperado em cada passo, até isolar a causa.
    - **Resolução passo a passo** - o procedimento para cada causa identificada.
    - **Verificação** - como confirmar que ficou resolvido.
    - **Prevenção e escalonamento** - o que evita a repetição e a quem escalar quando o capítulo não chega.
- **Secção 4 - Anexos:** referências cruzadas (tickets, PRs, documentos), parâmetros de configuração, registo da verificação e glossário.

Convenções:

- `<entre ângulos>` é um valor a substituir (identificador, slug, host).
- Os blocos de comandos indicam onde correm: **[VM]** na VM da aplicação, **[container]** dentro de um container (ver [PC-1](#pc-1-executar-comandos-udata)), **[browser]** nas ferramentas de programador do browser, **[posto]** num posto com acesso à rede interna.
- Os endereços IP, nomes internos de máquinas e credenciais não constam deste documento. Obtêm-se junto da equipa de infraestrutura (ver [PC-0](#pc-0-ambientes-acessos-e-contactos)).

## 2. Pré-requisitos comuns

### PC-0. Ambientes, acessos e contactos

| Ambiente | Endereço público | Appliance F5/WAF à frente | Uso |
| --- | --- | --- | --- |
| DEV | sem endereço público | não | desenvolvimento |
| TST | sem endereço público | não | testes de integração |
| PPR | `preprod.dados.gov.pt` | sim | pré-produção, validação final |
| PRD | `dados.gov.pt` | sim | produção |

Pontos que condicionam todo o diagnóstico:

- **PPR e PRD estão atrás de um appliance F5/WAF; DEV e TST não.** O appliance faz NAT do IP de origem (todos os visitantes chegam com o mesmo IP), injeta cookies, reescreve o atributo `SameSite`, bloqueia métodos HTTP que não sejam GET ou POST e bloqueia corpos de pedido com 16 MiB ou mais. Um problema que só existe em PPR/PRD aponta primeiro para o appliance. Análise completa em `docs/infra-adc-waf-impact-ppr-prd.md`.
- **As VMs de PPR e PRD só aceitam tráfego vindo do F5.** Para contornar o appliance é preciso estar na própria VM e pedir a `localhost` (ver [PC-8](#pc-8-pedido-direto-à-vm-ou-através-do-f5)).
- **O TLS público termina no F5.** A aplicação e o CMS recebem HTTP simples na porta 80 ou nas portas da aplicação.

Acessos necessários (pedir antes de precisar):

- SSH às VMs da aplicação de cada ambiente, com um utilizador no grupo `docker`.
- Rede até às máquinas do MongoDB e do Redis do ambiente (valores `SERVER_MONGO` e `SERVER_REDIS` do `.env`).
- Conta de administrador (sysadmin) no portal de cada ambiente, para `/admin`.
- Uma conta real de Chave Móvel Digital e uma de eIDAS para testes de autenticação.
- Permissão de escrita nos repositórios `amagovpt/udata-pt` (backend) e `amagovpt/dadosgov-fe` (frontend) e acesso ao Jira, projeto `LEDG`.

Escalonamento por tipo de causa:

| Causa | Escalar para |
| --- | --- |
| F5/WAF, VIP, certificado TLS público, VMs, rede, DNS | Equipa de infraestrutura |
| MongoDB, Redis, backups, disco das VMs | Equipa de infraestrutura |
| CMS Squidex (conteúdo e disponibilidade) | Equipa responsável pelo CMS / infraestrutura |
| Fornecedor de identidade (CMD, eIDAS), metadata SAML | AMA - Autenticação.gov |
| Fonte de harvest remota | Produtor da fonte (contacto na fonte em `/admin/harvesters`) |
| Colheita pelo data.europa.eu | Equipa do Portal Europeu de Dados |
| Defeito no código | Equipa de desenvolvimento, com ticket no projeto `LEDG` |

### PC-0b. Onde corre cada serviço

Em cada VM da aplicação o código está em `/opt/dadosgov`, com uma pasta por repositório:

| Componente | Pasta na VM | Container | Serviço compose | Porta |
| --- | --- | --- | --- | --- |
| API backend (Flask + uWSGI) | `/opt/dadosgov/backend` | `udata-backend-app` | `app` | 7000 |
| Worker Celery | `/opt/dadosgov/backend` | `udata-backend-worker` | `worker` | - |
| Agendador Celery (beat) | `/opt/dadosgov/backend` | `udata-backend-beat` | `beat` | - |
| Frontend (Next.js) | `/opt/dadosgov/frontend` | `udata-frontend-app` | `app` | 3000 |

Fora da VM, noutras máquinas:

- **MongoDB** (base `udata`), em `mongodb://<SERVER_MONGO>:27017/udata`.
- **Redis**, com uma base por função: `0` fila Celery, `1` resultados Celery, `2` cache da aplicação, `3` contadores do limitador de pedidos.
- **CMS Squidex**, que fornece o conteúdo editorial das páginas públicas.
- **Elasticsearch**, opcional: o `udata.cfg` versionado não define `ELASTICSEARCH_URL`, e nesse caso a pesquisa usa o índice de texto do MongoDB (ver capítulo [3](#3-indexação-e-pesquisa)).

Cada `docker-compose.yml` tem um serviço de arranque que faz o `chown` das pastas montadas para o utilizador `dadosgov` (UID/GID 10001 por omissão): `init-logs` no backend e `init-dirs` no frontend. Os ficheiros publicados vivem em `FS_ROOT` (por omissão `/opt/dadosgov/fs`), montado em `/dadosgov/fs` nos containers `app` e `worker`. As credenciais SAML ficam em `/opt/dadosgov/backend/udata/auth/saml/credentials/`, pasta que não está no git.

### PC-1. Executar comandos `udata`

Todos os comandos `udata` correm dentro do container da API, que já tem a configuração e o acesso ao MongoDB e ao Redis:

```
[VM]  docker exec -it udata-backend-app uv run udata <grupo> <comando> [opções]
```

Exemplos: `docker exec -it udata-backend-app uv run udata db status`, `docker exec -it udata-backend-app uv run udata harvest diagnose`. Os scripts de manutenção do backend correm da mesma forma:

```
[VM]  docker exec -it udata-backend-app uv run python scripts/<script>.py [opções]
```

No resto do documento os comandos aparecem abreviados como `udata ...`; entende-se sempre com o prefixo acima. `udata <grupo> --help` lista os comandos e as opções de cada grupo.

### PC-2. Consultar registos

| Registo | Na VM | Conteúdo |
| --- | --- | --- |
| API backend | `/opt/dadosgov/backend/logs/app.log` | pedidos, tracebacks, eventos do uWSGI (harakiri, workers reiniciados) |
| Worker Celery | `/opt/dadosgov/backend/logs/worker.log` | tarefas assíncronas: harvest, indexação, métricas, purgas |
| Beat Celery | `/opt/dadosgov/backend/logs/beat.log` | disparo dos agendamentos |
| Frontend | `/opt/dadosgov/frontend/logs/app.log` | renderização no servidor, erros de chamadas à API e ao CMS |

```
[VM]  tail -f /opt/dadosgov/backend/logs/app.log
[VM]  grep -n "Traceback" -A 30 /opt/dadosgov/backend/logs/app.log | tail -80
[VM]  zgrep "<texto>" /opt/dadosgov/backend/logs/app.log*.gz
```

Os registos rodam aos 10 MB, com 50 ficheiros comprimidos mantidos (`backend/scripts/logrotate-dadosgov.conf` e `frontend/scripts/logrotate-dadosgov-frontend.conf`; instalação em `docs/logrotate-setup.md`). Um pedido bloqueado pelo F5 **não deixa nenhuma linha** nestes registos, porque nunca chega à aplicação.

### PC-3. Estado dos containers

```
[VM]  docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"
[VM]  docker logs --tail 200 udata-backend-worker
```

Resultado esperado: os quatro containers da tabela de [PC-0b](#pc-0b-onde-corre-cada-serviço) com estado `Up`. Os containers têm `restart: unless-stopped`: um container que reinicia em ciclo aparece sempre `Up` há poucos segundos. Nesse caso, `docker logs --tail 200 <container>` mostra o erro de arranque.

Para confirmar que o código em execução é o esperado depois de um deploy:

```
[VM]  git -C /opt/dadosgov/backend log -1 --oneline
[VM]  git -C /opt/dadosgov/frontend log -1 --oneline
[VM]  docker inspect -f '{{.Created}}' udata-backend-worker
```

Uma data de criação do container anterior ao último deploy indica que ele ainda corre o código antigo (ver [PC-4](#pc-4-reinício-de-serviços)).

### PC-4. Reinício de serviços

Escolher o comando pelo que mudou:

| O que mudou | Comando (na pasta do repositório na VM) |
| --- | --- |
| Código Python, tarefas Celery, harvesters, `udata.cfg` | `docker compose restart app worker beat` |
| Variáveis do `.env` ou o próprio `docker-compose.yml` | `docker compose up -d` (recria os containers) |
| Código do frontend (novo build) | `docker compose up -d --build` na pasta `frontend` |
| Deploy completo dos dois repositórios | `python run_servers.py` na raiz do monorepo (faz `docker compose up -d --build` em `backend` e `frontend`) |

```
[VM]  cd /opt/dadosgov/backend && docker compose restart app worker beat
```

Regras:

- **O worker e o beat são processos de longa duração e não releem o código.** Depois de qualquer deploy que toque em tarefas Celery ou harvesters, reiniciar os três serviços, não só o `app`; caso contrário, as execuções assíncronas continuam com o código anterior e o deploy parece não ter efeito.
- `docker compose restart` não aplica alterações ao `.env` nem ao `docker-compose.yml`: para isso é `docker compose up -d`.
- Antes de reiniciar por causa de um 500 ou 502, ler o traceback ([PC-2](#pc-2-consultar-registos)): um erro de dados não se resolve com um reinício.

Verificação: [PC-3](#pc-3-estado-dos-containers) com os containers `Up` há poucos segundos, seguido de [PC-11](#pc-11-smoke-test).

### PC-5. Filas Celery e jobs agendados

O worker consome três filas: `default`, `high` (inclui a indexação, rota `high.search`) e `low` (harvest, rota `low.harvest`), com concorrência 4. Os agendamentos são documentos `PeriodicTask` no MongoDB, que o beat lê e dispara.

```
[container]  udata worker status              # tamanho de cada fila
[container]  udata worker status -q low        # só uma fila
[container]  udata job list                    # jobs existentes
[container]  udata job scheduled               # jobs agendados e o crontab de cada um
[container]  udata job run <nome>              # corre em primeiro plano e mostra o erro
[container]  udata job run -d <nome>           # envia para a fila
[container]  udata job schedule "<crontab>" <nome>
```

Leitura: uma fila cujo tamanho não desce entre duas leituras com um minuto de intervalo indica que o worker não está a consumir (parado, bloqueado ou saturado). Um job que devia existir e não aparece em `udata job scheduled` perdeu o agendamento, o que é frequente depois de um restauro da base.

Agendamentos de referência:

| Job | Função | Agendamento sugerido |
| --- | --- | --- |
| `aggregate-metrics` | agrega métricas | `0 2 * * *` |
| `update-metrics` | atualiza métricas dos objetos | `0 3 * * *` |
| `compute-site-metrics` | totais da homepage | `0 4 * * *` |
| `compute-geozones-metrics` | métricas por geozona | `0 9 * * *` |
| `purge-chunks` | apaga blocos de carregamento expirados | `0 * * * *` |
| `purge-datasets`, `purge-reuses`, `purge-organizations`, `purge-dataservices` | apagam definitivamente objetos marcados como eliminados | diário, fora de horas |

### PC-6. Migrações da base de dados

As migrações estão em `backend/udata/migrations/`; cada uma fica registada na coleção `migrations` depois de correr com sucesso.

```
[container]  udata db status                   # aplicadas e em falta
[container]  udata db migrate --dry-run        # o que seria aplicado, sem tocar na base
[container]  udata db migrate                  # aplica as que faltam
[container]  udata db info <ficheiro>          # descreve uma migração
[container]  udata db migrate --record         # regista como aplicadas SEM as correr
[container]  udata db unrecord <ficheiro>      # desfaz o registo de uma migração
```

- **Atenção:** `udata db migrate --record` marca como aplicadas migrações que não correram, e esconde assim alterações de esquema e de dados que ficam por fazer. Só se usa para reproduzir um histórico de migrações que se sabe já aplicado, como na sequência pós-restauro do capítulo [8](#8-problemas-de-base-de-dados). Um registo feito por engano só se desfaz com `udata db unrecord`, um ficheiro de cada vez.
- O comando é `udata db migrate`. `udata db upgrade` não existe (o `CLAUDE.md` do monorepo refere-o por engano).
- O `migrate` para na primeira migração que falhe e não corre as seguintes. Corrigir a causa e voltar a correr: as que já passaram estão registadas e não se repetem.
- Em PRD, fazer sempre um dump antes (capítulo [13](#13-gestão-de-backups)) e correr primeiro `--dry-run`.

### PC-7. Reindexação da pesquisa

Primeiro, saber que motor de pesquisa o ambiente usa ([PC-10](#pc-10-ler-a-configuração-efetiva-sem-expor-segredos)):

```
[container]  udata info config 2>/dev/null | grep '^ELASTICSEARCH_URL'
```

- **`ELASTICSEARCH_URL` vazio ou `None`** (é o caso do `udata.cfg` versionado): a pesquisa usa o índice de texto do MongoDB. Não há nada para reindexar; os comandos `udata search ...` registam `Missing ELASTICSEARCH_URL configuration` e terminam. Um problema de pesquisa é um problema do índice de texto (capítulo [8](#8-problemas-de-base-de-dados)).
- **`ELASTICSEARCH_URL` definido:** a indexação é assíncrona (cada gravação enfileira uma tarefa na fila `high.search`) e repõe-se com:

```
[container]  udata search init-es                        # cria os templates/índices se não existirem
[container]  udata search index                          # indexa tudo sobre os índices atuais
[container]  udata search index dataset                  # só um modelo
[container]  udata search index -f AAAA-MM-DD-HH-MM      # só o que mudou desde essa data
[container]  udata search index -r true                  # índices novos, troca o alias no fim
```

Atenção: `udata search clean-es` apaga índices (todos, se não se indicar modelo). Só se usa imediatamente antes de reconstruir tudo. A reconstrução total carrega o nó único de Elasticsearch: fazer numa janela planeada.

### PC-8. Pedido direto à VM ou através do F5

Repetir o mesmo pedido pelos dois caminhos isola o appliance numa só tentativa:

```
[posto]  curl -skI https://<host público>/api/1/site/
[VM]     curl -sI http://localhost:7000/api/1/site/        # backend, sem F5
[VM]     curl -sI http://localhost:3000/                   # frontend, sem F5
```

Leitura:

- Falha através do F5 e funciona na VM: a causa está no appliance (WAF, cookies, NAT, limite de tamanho). Escalar para infraestrutura com o pedido, a hora e a resposta (incluindo o `Attack ID`, quando a página do WAF o mostra).
- Falha nos dois caminhos: a causa está na aplicação ou nas suas dependências. Continuar pelos registos ([PC-2](#pc-2-consultar-registos)).
- Em TST/DEV não há appliance: um problema que se reproduz em TST não é do F5.

### PC-9. Limpar a cache da aplicação

```
[container]  udata cache flush
```

Limpa toda a cache da aplicação no Redis (base 2), não apenas uma chave. Usa-se depois de corrigir dados que estão em cache, para não esperar pela expiração (p. ex. os 300 s da homepage).

### PC-10. Ler a configuração efetiva sem expor segredos

`udata info config` imprime **toda** a configuração carregada, incluindo palavras-passe e chaves. Nunca colar o resultado completo em tickets, e-mails ou chats. Filtrar sempre a chave que interessa:

```
[container]  udata info config 2>/dev/null | grep -E '^(MAIL_SERVER|MAIL_PORT|MAIL_USE_TLS|MAIL_USE_SSL|MAIL_DEFAULT_SENDER)'
```

A configuração vem de três camadas: os valores por omissão em `backend/udata/settings.py`, o `backend/udata.cfg` (montado só de leitura no container), e as variáveis do `.env` que o `udata.cfg` lê. Sem o `.env` carregado, vários valores caem para omissões pouco seguras (p. ex. política de palavra-passe inativa, remetente `webmaster@udata`).

### PC-11. Smoke-test

Correr depois de qualquer reinício, deploy, restauro ou correção. Todos os passos devem passar:

1. Abrir a homepage: carrega, com as estatísticas e as notícias visíveis.
2. Pesquisar um termo conhecido em `/datasets`: aparecem resultados.
3. Abrir a página de um conjunto de dados.
4. Descarregar um recurso de um conjunto de dados.
5. Iniciar sessão com CMD (e, em PPR/PRD, também com eIDAS) e confirmar que `/api/1/me/` devolve 200.
6. Carregar um ficheiro pequeno num conjunto de dados de teste.
7. Em PPR/PRD, repetir os passos 5 e 6 através do F5 (é aí que os problemas do appliance aparecem).

Em simultâneo, `tail -f` do `app.log` do backend e do frontend ([PC-2](#pc-2-consultar-registos)) não deve mostrar tracebacks novos.

## 3. Capítulos por incidente

### 1. Harvesting nacional

#### Sintoma

- Conjuntos de dados de uma fonte nacional não atualizam, ou desaparecem (ficam arquivados).
- Em `/admin/harvesters`, a fonte mostra a última execução antiga, em erro, ou com muitos itens falhados.
- A execução "não corre", mas não há erro visível.

#### Diagnóstico passo a passo

1. **A fonte está agendada?**
   ```
   [container]  udata harvest diagnose
   ```
   Mostra, por fonte, se está ativa, se o agendamento (`PeriodicTask`) está ativo, o crontab, o `last_run_at` e a sua idade, o número de execuções e o estado do último job. Distingue "a fonte não está agendada" (agendamento inexistente ou inativo; ir para a resolução A) de "está agendada e falha" (continuar).
2. **Há agendamentos órfãos?**
   ```
   [container]  udata harvest orphans
   ```
   Lista `PeriodicTask` que já não correspondem a uma fonte viva: o beat despacha-os e nada acontece. Resultado esperado: lista vazia.
3. **O worker está a consumir a fila de harvest?** `udata worker status -q low` ([PC-5](#pc-5-filas-celery-e-jobs-agendados)). Um número que não desce indica o worker parado ou saturado; confirmar com [PC-3](#pc-3-estado-dos-containers). Um worker `Up` com data de criação anterior ao último deploy de harvesters corre código antigo.
4. **Qual o erro?** Ver os erros por item em `/admin/harvesters` → fonte → última execução, e em `worker.log` ([PC-2](#pc-2-consultar-registos)). Para ver o erro em primeiro plano:
   ```
   [container]  udata harvest run <slug>
   ```
5. **O erro é nosso ou da fonte?** Ler o catálogo remoto sem gravar nada:
   ```
   [container]  udata dcat parse-url <url>            # DCAT
   [container]  udata dcat parse-url --csw <url>      # CSW
   [container]  udata dcat parse-url --iso <url>      # CSW com perfil ISO
   [VM]         curl -sSI <url da fonte>
   ```
   Leitura dos resultados:
   - Erro de TLS (`CERTIFICATE_VERIFY_FAILED`): normalmente é uma cadeia de certificados incompleta no servidor da fonte (caso já visto: Ourém, LEDG-2559).
   - 403 ou página de desafio: é o WAF ou Cloudflare da fonte, não uma permissão nossa (caso já visto: `dados.cm-lisboa.pt` recusa pedidos sem cabeçalhos `Sec-Fetch-*`).
   - XML ou RDF inválido, ou campos obrigatórios em falta: a fonte mudou de contrato.
   - Erro do guarda SSRF (host recusado): o host está em `HARVEST_URL_HOST_DENYLIST`, ou o URL traz credenciais embutidas.
6. **Datasets arquivados sozinhos?** O harvest arquiva os datasets que faltam na fonte há mais de `HARVEST_AUTOARCHIVE_GRACE_DAYS` (7) dias. Confirmar na fonte se o dataset ainda é publicado.

Contexto útil: os pedidos à fonte fazem 3 tentativas (`HARVEST_HTTP_MAX_RETRIES`), com espera de 2 s a crescer até 60 s, e tempo limite de 15 s para ligar e 600 s para ler (`HARVEST_HTTP_TIMEOUT`). Uma fonte lenta pode prender um slot do worker durante vários minutos.

#### Resolução passo a passo

- **A. Fonte sem agendamento ou com crontab errado:**
  ```
  [container]  udata harvest schedule <slug> -m 0 -h 1          # todos os dias à 01:00
  [container]  udata harvest sources --scheduled
  ```
  O `schedule` recebe cada campo do crontab como opção: `-m` minuto, `-h` hora, `-d` dia da semana, `-D` dia do mês, `-M` mês.
- **B. Agendamentos órfãos:** `udata harvest purge` apaga definitivamente as fontes eliminadas e os seus agendamentos.
- **C. Worker parado ou com código antigo:** reiniciar `worker` e `beat` ([PC-4](#pc-4-reinício-de-serviços)).
- **D. URL ou configuração da fonte errados:** corrigir em `/admin/harvesters` e validar a fonte (`udata harvest validate <id>`, se estiver pendente de validação).
- **E. Erro do lado da fonte:** contactar o produtor com o erro concreto do passo 5. Enquanto se trata, `udata harvest unschedule <slug>` suspende a fonte sem a apagar. Os datasets arquivados voltam a ativos sozinhos quando a fonte volta a publicá-los.
- **F. Host recusado pelo guarda SSRF:** confirmar com a equipa de desenvolvimento se o host é legítimo; a lista de hosts recusados e permitidos (`HARVEST_URL_HOST_DENYLIST`, `HARVEST_URL_HOST_ALLOWLIST`) é configuração, não se altera a quente.

Para forçar uma execução depois de corrigir: `udata harvest run <slug>` (síncrona, mostra o erro) ou `udata harvest launch <slug>` (assíncrona, vai para a fila `low`). A execução manual a partir da interface de administração só existe com `HARVEST_ENABLE_MANUAL_RUN=True` (desligada por omissão).

#### Verificação

- `udata harvest diagnose` mostra a fonte com o último job em sucesso e `last_run_at` recente.
- Em `/admin/harvesters`, a última execução tem os itens esperados sem erros.
- Um dataset da fonte mostra a data de modificação recente na sua página.

#### Prevenção e escalonamento

- Depois de qualquer deploy que toque em harvesters, reiniciar worker e beat ([PC-4](#pc-4-reinício-de-serviços)).
- Distribuir as fontes pesadas por horários diferentes: o agendamento por omissão é diário à meia-noite (`HARVEST_DEFAULT_SCHEDULE = 0 0 * * *`) e todas competem pelo mesmo worker.
- Em código novo, todos os pedidos HTTP de um harvester passam por `BaseBackend.get/head/post` (guarda SSRF e tentativas); o `owslib` exige chamar `_guard_url` explicitamente.
- O histórico de jobs fica disponível 365 dias (`HARVEST_JOBS_RETENTION_DAYS`).
- Escalar: fonte remota → produtor; worker saturado de forma recorrente → desenvolvimento (ver capítulo [16](#16-limitações-conhecidas-da-solução)).

### 2. Harvesting do Portal Europeu de Dados

O data.europa.eu colhe o nosso catálogo DCAT-AP. Este capítulo trata esse sentido (nós somos a fonte).

#### Sintoma

- Datasets publicados no dados.gov.pt não aparecem no data.europa.eu, ou aparecem desatualizados.
- Datasets de elevado valor (HVD) aparecem sem a categoria HVD no portal europeu.
- A equipa do portal europeu reporta erros de colheita (429, 504, RDF inválido).

#### Diagnóstico passo a passo

1. **Pedir o catálogo como o colhedor o pede:**
   ```
   [posto]  curl -s -H "Accept: application/rdf+xml" "https://dados.gov.pt/api/1/site/catalog.rdf?page=1&page_size=100" -o catalog.rdf
   ```
   Resultado esperado: HTTP 200 e um RDF válido. Um 429 é o nosso limite de pedidos; um 504 é tempo esgotado no F5 numa página grande.
2. **Procurar 429 e 504** no `app.log` ([PC-2](#pc-2-consultar-registos)). Um 504 sem linha correspondente no `app.log` é do appliance.
3. **O dataset em falta é visível?** O catálogo só inclui objetos visíveis: um dataset privado, eliminado ou arquivado (p. ex. pelo auto-arquivo do harvest nacional, capítulo [1](#1-harvesting-nacional)) deixa de ser exposto, sem erro do nosso lado. Confirmar em `/api/1/datasets/<id>/`.
4. **Os HVD estão etiquetados?** `/api/1/datasets/?tag=hvd` dá o universo de datasets que devem sair com `dcatap:hvdCategory`. Comparar o total com o que o portal europeu apresenta como HVD.
5. **Os metadados obrigatórios existem?** Licença, publisher e contactPoint em falta na origem fazem o dataset falhar a validação.
6. **O RDF é válido?** Validar `catalog.rdf` contra as regras SHACL do DCAT-AP (validador do data.europa.eu).
7. **Os URLs das distribuições mudam todas as noites?** Em 8 backends de harvest, os ids de recurso `/r/<uuid>` são recriados a cada execução (capítulo [17](#17-bugs-conhecidos)); o portal europeu vê distribuições novas a cada colheita.

#### Resolução passo a passo

- **429:** pedir ao colhedor um `page_size` menor; se necessário, ajustar `EXPORT_LIMIT` (60 por minuto e 1200 por hora, em `backend/udata/api/limits.py`, com chave `user_or_ip`). Alteração de código, via PR.
- **504 no F5:** baixar o `page_size` pedido; se persistir, escalar para infraestrutura (tempo limite do appliance).
- **Metadados em falta ou HVD sem etiqueta:** corrigir na origem (organização produtora ou fonte de harvest) e acrescentar a etiqueta `hvd` aos datasets de elevado valor.
- **Dataset privado ou arquivado:** é o comportamento esperado; confirmar com o produtor se deve ser público.
- **Depois de corrigir:** pedir nova colheita à equipa do portal europeu.

Nota: os Dataservices só passam para o portal europeu como distribuições, porque o portal ainda não os colhe como entidade própria.

#### Verificação

- `curl` do passo 1 devolve 200 em todas as páginas.
- O validador SHACL não reporta violações.
- Depois da colheita seguinte, o número de datasets e de HVD no data.europa.eu coincide com o do portal.

#### Prevenção e escalonamento

- Qualquer alteração à serialização DCAT (`backend/udata/core/dataset/rdf.py`, `backend/udata/rdf.py`) passa pelo validador SHACL antes da promoção.
- Nunca pôr o endpoint do catálogo num limite só por IP: com o F5 à frente, bloquearia o colhedor e todos os visitantes ao mesmo tempo (capítulo [20](#20-bloqueios-por-rate-limit-429)).
- Estabilizar os ids de recurso reutilizando-os por URL, como já é feito em `odspt.py` (ticket de desenvolvimento).
- Escalar: colheita → equipa do portal europeu; 504 → infraestrutura.

### 3. Indexação e pesquisa

#### Sintoma

- Um dataset criado ou alterado não aparece na pesquisa, ou aparece com dados antigos.
- A pesquisa devolve sempre zero resultados ou fica lenta.

#### Diagnóstico passo a passo

1. **O objeto existe?** `curl -s https://<host>/api/1/datasets/<id>/`. Se existe na API mas não na pesquisa, o problema está no índice e não nos dados.
2. **Que motor de pesquisa está ativo?** [PC-7](#pc-7-reindexação-da-pesquisa), primeiro comando.
   - Sem `ELASTICSEARCH_URL`: a pesquisa usa o índice de texto do MongoDB, atualizado na própria gravação. Ir para o passo 5.
   - Com `ELASTICSEARCH_URL`: continuar no passo 3.
3. **O worker consome a fila de indexação?** `udata worker status -q high` ([PC-5](#pc-5-filas-celery-e-jobs-agendados)): um número a crescer indica o worker parado. Procurar `Unable to index` no `worker.log` ([PC-2](#pc-2-consultar-registos)).
4. **O Elasticsearch responde e os índices existem?**
   ```
   [VM]  curl -s <ELASTICSEARCH_URL>/_cat/indices?v
   [VM]  curl -s <ELASTICSEARCH_URL>/_cat/aliases?v
   ```
   Resultado esperado: índices de `dataset`, `reuse`, `organization` e outros, com os aliases a apontar para eles.
5. **Índice de texto do MongoDB em conflito?** Um traceback do mongoengine sobre índice de texto no `app.log` indica um índice antigo a impedir o novo (a coleção só admite um). É a mesma causa do capítulo [6](#6-problemas-de-publicação-de-conjuntos-de-dados), resolução A.

#### Resolução passo a passo

- **Worker parado:** reiniciar o worker ([PC-4](#pc-4-reinício-de-serviços)); senão o problema repete-se na gravação seguinte.
- **Índices em falta ou desatualizados (Elasticsearch):** `udata search init-es` se não existirem, e depois `udata search index`, ou `udata search index -f <data da paragem>` para repor só o período afetado ([PC-7](#pc-7-reindexação-da-pesquisa)).
- **Elasticsearch indisponível:** o cluster é de nó único, pelo que uma falha deixa toda a pesquisa em baixo. Escalar para infraestrutura; quando voltar, reindexar desde a hora da falha.
- **Índice de texto do MongoDB:** capítulo [6](#6-problemas-de-publicação-de-conjuntos-de-dados), resolução A.

#### Verificação

Pesquisar pelo título do objeto do passo 1: aparece nos resultados. Com Elasticsearch, `udata worker status -q high` volta a zero.

#### Prevenção e escalonamento

- Reindexar sempre que um deploy mude o mapping do Elasticsearch (capítulo [15](#15-aplicação-de-atualizações)).
- A reconstrução total (`-r true`) é feita à mão, numa janela planeada.
- Escalar: Elasticsearch em baixo → infraestrutura; erros `Unable to index` persistentes para o mesmo objeto → desenvolvimento, com o id.

### 4. Gestão de organizações e datasets

#### Sintoma

- Um utilizador diz que não consegue editar os dados da sua organização.
- Um dataset não se deixa editar manualmente.
- Uma conta institucional (caixa de correio partilhada) continua acessível a quem saiu da entidade.

#### Diagnóstico passo a passo

1. **Distinguir os dois eixos de permissão.** O **papel na organização** (membro `admin`, `editor` ou `partial_editor`) e o **perfil global** (sysadmin, em `user.roles`) são independentes e nunca se sincronizam.
   - Papel na organização: `/admin/organizations` → organização → membros, ou `GET /api/1/organizations/<id>/` (lista `members` com o `role`).
   - Perfil global: `/admin/users` → utilizador.
2. **Há um pedido de adesão pendente?** Em `/admin/organizations` → organização → pedidos.
3. **O dataset pertence a uma fonte de harvest?** A página de administração do dataset indica a fonte. Um dataset colhido é sobrescrito na próxima execução e não deve ser editado manualmente.
4. **Contas institucionais com identidade pessoal ligada:**
   ```
   [container]  uv run python scripts/audit_institutional_users.py --host <SERVER_MONGO> --only-flagged
   ```
   Auditoria só de leitura; lista caixas partilhadas com uma identidade CMD pessoal em `extras.auth_nic`.
5. **Referências partidas:** `udata db check-integrity` (aceita `--models` para limitar) e `udata harvest orphans`.

#### Resolução passo a passo

- **Falta de permissão na organização:** aceitar o pedido de adesão ou atribuir o papel certo dentro da organização. **Nunca conceder sysadmin global** para resolver uma permissão de organização: o sysadmin não fica registado como membro e dá acesso a tudo.
- **Dataset preso a uma fonte de harvest:** se deve passar a ser gerido à mão, soltar todos os datasets da fonte com `udata harvest detach-all-from-source <id da fonte>`.
- **Mudança de dono:** transferir a titularidade do dataset em vez de o recriar, para não perder histórico, métricas e URLs.
- **Caixa partilhada com identidade pessoal:** desligar a identidade CMD da conta antes de a pessoa sair da entidade.
- **Objetos eliminados que ainda aparecem:** ficam marcados como eliminados até às purgas; para purgar de imediato, `udata purge --datasets` (e `--reuses`, `--organizations`, `--dataservices`).

#### Verificação

O utilizador consegue editar com o seu papel; `GET /api/1/organizations/<id>/` mostra o membro com o `role` certo; a auditoria do passo 4 deixa de listar a conta.

#### Prevenção e escalonamento

- Cada organização deve ter pelo menos um membro `admin` (capítulo [24](#24-organizações-criadas-indevidamente-ou-sem-administrador)).
- Escalar: pedidos de titularidade disputados → gestão do portal (AMA); referências partidas que `check-integrity` não explica → desenvolvimento.

### 5. Autenticação CMD

Aplica-se também à autenticação eIDAS, que usa o mesmo mecanismo SAML.

#### Sintoma

- Mensagem "assinatura SAML inválida" depois de autenticar na Chave Móvel Digital.
- O login parece concluído, mas o portal continua sem sessão (`/api/1/me/` devolve 401).
- O utilizador é enviado para `/complete-registration` a cada login.
- "Sair" não termina a sessão.
- Funciona em TST mas não em PPR/PRD.

#### Diagnóstico passo a passo

1. **Seguir o fluxo no browser** [browser, separador Rede]: `/saml/login` → autenticação no fornecedor de identidade → `POST /saml/sso` → `/api/1/me/`. O eIDAS usa `/saml/eidas/login` e `/saml/eidas/sso`.
   - Falha no `POST /saml/sso`: problema da asserção SAML (passos 2 e 3).
   - `POST /saml/sso` bem-sucedido e `/api/1/me/` com 401: o cookie de sessão perdeu-se (passo 4).
2. **Ler a exceção** do python3-saml no `app.log` ([PC-2](#pc-2-consultar-registos)): indica a validação que falhou (assinatura, audiência, validade).
3. **Metadata e certificados do ambiente certo?**
   ```
   [VM]  cd /opt/dadosgov/backend/udata/auth/saml/credentials
   [VM]  openssl x509 -enddate -noout -in AMA.pem
   ```
   Extrair o certificado do fornecedor de identidade de `metadata.xml` (elemento `X509Certificate`) para um ficheiro PEM e ver de que ambiente é e quando expira:
   ```
   [VM]  openssl x509 -noout -subject -issuer -enddate -in idp.pem
   ```
   Um certificado de pré-produção em PRD (ou o contrário) produz "assinatura SAML inválida".
4. **Cookie de sessão perdido (só em PPR/PRD):** comparar os cabeçalhos através do F5 e diretamente na VM ([PC-8](#pc-8-pedido-direto-à-vm-ou-através-do-f5)):
   ```
   [posto]  curl -skI https://<host público>/saml/login
   [VM]     curl -sI http://localhost:7000/saml/login
   ```
   Cookies extra ou `SameSite` diferente através do F5 indicam o appliance.
5. **Sessão destruída pelo CSRF:** se o `/api/1/me/` passa a 401 logo a seguir a um pedido de token CSRF feito pelo browser, o pedido de token substituiu a sessão autenticada. Em fluxos já autenticados, o token deve ser gerado no servidor (ver a resolução).
6. **Encaminhado sempre para `/complete-registration`:** a conta tem e-mail provisório `saml-*@autenticacao.gov.pt` porque o fornecedor não devolveu o e-mail. É o comportamento pretendido até o utilizador indicar um e-mail real.

#### Resolução passo a passo

- **Metadata ou certificado errado ou expirado:** substituir o conteúdo de `udata/auth/saml/credentials/` pelo pacote do ambiente certo (fornecido pela AMA) e reiniciar o `app` ([PC-4](#pc-4-reinício-de-serviços)). Detalhe no capítulo [11](#11-problemas-de-certificadoskeys).
- **Cookies alterados pelo F5:** escalar para infraestrutura com a comparação do passo 4.
- **CSRF no cliente:** defeito de código; o token de fluxos autenticados é gerado no servidor. Abrir ticket para desenvolvimento.
- **E-mail provisório:** pedir ao utilizador que conclua o registo com um e-mail real.

#### Verificação

**Validar sempre com um login CMD e um login eIDAS reais** depois de qualquer alteração: não é possível simular a assinatura do fornecedor de identidade. Confirmar `/api/1/me/` com 200 e que "Sair" termina a sessão (o `/saml/logout` termina primeiro a sessão local e só depois contacta o fornecedor).

#### Prevenção e escalonamento

- Testar os dois fluxos, CMD e eIDAS: têm rotas e extração de atributos diferentes, e um pode funcionar sem o outro.
- Registar as datas de expiração dos certificados (capítulo [11](#11-problemas-de-certificadoskeys)).
- Alterações de cookies, sessão ou SAML só se dão por validadas em PPR, que tem o F5.
- Escalar: fornecedor de identidade → AMA; cookies → infraestrutura.

### 6. Problemas de publicação de conjuntos de dados

#### Sintoma

- O carregamento de um ficheiro falha com "500 {}".
- Aparece uma página do WAF em vez de uma resposta da aplicação.
- Ficheiros grandes falham e pequenos funcionam.
- O formato do ficheiro é recusado.

#### Diagnóstico passo a passo

1. **Separar as causas pelos registos** ([PC-2](#pc-2-consultar-registos)), à hora do carregamento:
   - Traceback do mongoengine sobre índice de texto em `backend/logs/app.log`: resolução A.
   - `ECONNRESET` ou `socket hang up` em `frontend/logs/app.log`: resolução B.
   - Página do WAF no browser e nenhuma linha em nenhum `app.log`: o pedido foi bloqueado pelo F5 (resolução C).
   - Erro de validação de extensão, tipo ou tamanho: resolução D.
   - Erro de CSRF: sessão expirada ou token gerado no cliente (capítulo [5](#5-autenticação-cmd), passo 5).
2. **Confirmar o F5:** carregar o mesmo ficheiro sem o appliance ([PC-8](#pc-8-pedido-direto-à-vm-ou-através-do-f5)); se funcionar, a causa é o F5.
3. **Tamanho:** o F5 bloqueia qualquer corpo com 16 MiB ou mais (attack_ID 20000026). O limite da aplicação é `RESOURCES_FILE_MAX_SIZE` (1 GB por omissão).

Contexto: o frontend envia os ficheiros em blocos de 1 MB (`resourceFileUploadChunk` em `frontend/src/config/site.ts`); o pedido final junta os blocos, grava o ficheiro e calcula o sha1. O limite de carregamento é `UPLOAD_LIMIT` (120 por minuto, 600 por hora, 2000 por dia, por utilizador; os blocos não contam).

#### Resolução passo a passo

- **A. Índice de texto obsoleto:**
  ```
  [container]  uv run python scripts/fix_mongo_text_index.py --host <SERVER_MONGO>            # só mostra
  [container]  uv run python scripts/fix_mongo_text_index.py --host <SERVER_MONGO> --apply    # corrige
  [container]  udata db migrate
  ```
- **B. Keep-alive entre o Next.js e o backend:** confirmar que `frontend/src/instrumentation.ts` (que desliga a reutilização de ligações com `setGlobalDispatcher`) está no build em execução ([PC-3](#pc-3-estado-dos-containers), commit do frontend). Se faltar, fazer deploy de um build que o inclua.
- **C. Bloqueio do F5 por tamanho:** usar o carregamento em blocos da interface (cada bloco viaja num pedido pequeno). Um cliente de API que envie o ficheiro inteiro num só pedido tem de passar a enviar em blocos.
- **D. Tamanho ou formato recusado pela aplicação:** quando o ficheiro é legítimo, ajustar `RESOURCES_FILE_MAX_SIZE`, `ALLOWED_RESOURCES_EXTENSIONS` ou `ALLOWED_RESOURCES_MIMES` na configuração e reiniciar ([PC-4](#pc-4-reinício-de-serviços)).

#### Verificação

Carregar de novo o mesmo ficheiro, através do F5, e confirmar que o recurso aparece no dataset e se descarrega com o mesmo tamanho e checksum.

#### Prevenção e escalonamento

- Alterações ao carregamento de ficheiros só se dão por validadas em PPR (com o F5).
- Manter o `proxy_read_timeout` do nginx alinhado com os 600 s do uWSGI nas rotas de carregamento.
- Escalar: bloqueio do WAF abaixo de 16 MiB → infraestrutura com o `Attack ID`; índice que volta a aparecer → desenvolvimento.

### 7. Indisponibilidade de serviços

#### Sintoma

- O portal devolve 500, 502 ou 504, ou não responde.
- Páginas públicas lentas ou em erro enquanto a API responde.
- Ciclo infinito de redirecionamentos (301) no conteúdo do CMS.

#### Diagnóstico passo a passo

1. **Os containers estão de pé?** [PC-3](#pc-3-estado-dos-containers). Um container parado ou em ciclo de reinício é a causa imediata; `docker logs --tail 200 <container>` diz porquê.
2. **Aplicação ou caminho de rede?** [PC-8](#pc-8-pedido-direto-à-vm-ou-através-do-f5): se a VM responde localmente e o endereço público não, a causa está no F5, na rede ou no DNS. Em PPR e PRD o F5 encaminha pelo hostname: confirmar com infraestrutura que o hostname aponta para a VM certa.
3. **É um 502 numa listagem?** Procurar o traceback no `app.log` antes de reiniciar o que quer que seja. Uma referência órfã (DBRef para um documento apagado) gera no uWSGI um 500 sem corpo, que o nginx mostra como 502. Confirmar com `udata db check-integrity`.
4. **Saturação?** O backend corre 4 processos uWSGI com 2 threads (8 pedidos em simultâneo, `backend/uwsgi/front.ini`). Linhas `harakiri` no `app.log` identificam os pedidos que excederam o tempo máximo (120 s; 600 s para CSV, `/upload/`, `/api/1/datasets/r/` e `proxy/download/`).
5. **O CMS responde?** Em `frontend/logs/app.log`, erros de tempo esgotado nas chamadas ao CMS (limite de 5 s, `CMS_FETCH_TIMEOUT_MS`) indicam o Squidex lento ou em baixo. Testar da VM: `curl -sI http://<host do CMS>/`.
6. **Ciclo de 301 no CMS:** `curl -sI http://<host do CMS>/` devolve `301` para `https://` do mesmo endereço.
7. **Dependências:** MongoDB ou Redis indisponíveis aparecem como erros de ligação (`ServerSelectionTimeoutError`, `ConnectionError`) no `app.log` e no `worker.log`.

#### Resolução passo a passo

- **Containers parados:** `docker compose up -d` na pasta do repositório ([PC-4](#pc-4-reinício-de-serviços)).
- **Referência órfã:** repor o documento em falta ou remover a referência (com a equipa de desenvolvimento); reiniciar não resolve.
- **Saturação:** identificar a rota lenta pelas linhas `harakiri` e tratá-la; não aumentar o número de processos às cegas.
- **CMS lento ou em baixo:** o tempo limite degrada a página em vez de a deitar abaixo, mas a causa é do CMS; escalar.
- **Ciclo de 301:** o TLS termina no F5, pelo que o vhost nginx do CMS na porta 80 tem de fazer `proxy_pass` para o Squidex e não redirecionar para https. Repor o `proxy_pass` (infraestrutura do CMS).
- **MongoDB ou Redis:** escalar para infraestrutura; quando voltarem, reiniciar `worker` e `beat` ([PC-4](#pc-4-reinício-de-serviços)).

#### Verificação

[PC-11](#pc-11-smoke-test) completo, através do F5.

#### Prevenção e escalonamento

- Monitorizar o endereço público e a porta local de cada serviço.
- Escalar: F5, rede, DNS, MongoDB, Redis → infraestrutura; CMS → responsável pelo CMS; referências órfãs recorrentes → desenvolvimento.

### 8. Problemas de base de dados

#### Sintoma

- O login falha com erro 500 e `FieldDoesNotExist` no `app.log`, normalmente depois de um restauro.
- `udata db migrate` para a meio.
- O total de resultados de uma listagem não coincide com o número de itens.
- Downloads `/r/<id>` devolvem o recurso errado.

#### Diagnóstico passo a passo

1. **Estado das migrações:** `udata db status` ([PC-6](#pc-6-migrações-da-base-de-dados)). Migrações em falta depois de um deploy ou de um restauro são a causa mais comum.
2. **`FieldDoesNotExist` no login:** confirmar no `app.log` que o campo é `apikey`. Acontece com um dump anterior à migração `2026-01-28-migrate-apikeys-to-api-tokens.py` restaurado junto com a coleção `migrations`.
3. **Integridade:**
   ```
   [container]  udata db check-integrity
   [container]  udata db check-duplicate-resources-ids
   ```
   O primeiro deteta referências partidas; o segundo deteta recursos com o mesmo id em datasets diferentes, que partem os permalinks `/r/<id>`.
4. **Totais de paginação:** sem filtro, o `count()` do MongoDB é uma estimativa lida dos metadados da coleção; o total da API pode não coincidir (LEDG-2484). Não é corrupção.

#### Resolução passo a passo

- **Migrações em falta:** `udata db migrate --dry-run` e depois `udata db migrate` ([PC-6](#pc-6-migrações-da-base-de-dados)).
- **`FieldDoesNotExist` com `apikey` depois de um restauro** (sequência de `docs/db-restore-apikey-fix.md`):
  ```
  [container]  udata db migrate --record
  [container]  udata db unrecord 2026-01-28-migrate-apikeys-to-api-tokens.py
  [container]  udata db migrate
  [container]  udata db status
  ```
  O primeiro regista como aplicadas as migrações que a origem já tinha corrido; o segundo desfaz o registo falso da migração de `apikey`; o terceiro corre-a de facto.
- **Migração falhada:** corrigir a causa indicada no erro e voltar a correr `udata db migrate`.
- **Referências partidas ou ids duplicados:** tratar com a equipa de desenvolvimento, caso a caso.

#### Verificação

`udata db status` sem migrações em falta; login funciona; `udata db check-integrity` sem erros novos.

#### Prevenção e escalonamento

- Antes de migrar em PRD: dump (capítulo [13](#13-gestão-de-backups)) e `--dry-run`.
- Escalar: MongoDB inacessível → infraestrutura; migração que falha de forma reproduzível → desenvolvimento.

### 9. Problemas na apresentação das estatísticas na homepage

#### Sintoma

Os números da homepage (datasets, organizações, reutilizações) não atualizam, ou atualizam com vários minutos de atraso.

#### Diagnóstico passo a passo

1. **Os jobs ainda estão agendados?** `udata job scheduled` ([PC-5](#pc-5-filas-celery-e-jobs-agendados)). Devem aparecer `aggregate-metrics`, `update-metrics`, `compute-site-metrics` e `compute-geozones-metrics`. Depois de um restauro é frequente desaparecerem.
2. **O beat disparou e o worker correu?** No `beat.log` procurar o disparo do job à hora do agendamento; no `worker.log` a execução e o fim ([PC-2](#pc-2-consultar-registos)).
3. **É cache?** Comparar o valor da API com o da página:
   ```
   [posto]  curl -s https://<host>/api/1/site/home/
   ```
   A API fica em cache 300 s no backend (Redis), e o frontend guarda a resposta 10 s. Se a API já tem o valor novo e a página não, é cache e não os jobs.

#### Resolução passo a passo

- **Recalcular de imediato:**
  ```
  [container]  udata metrics update
  ```
  Aceita opções para recalcular só o necessário: `-s` site, `-o` organizações, `-d` datasets, `-r` reutilizações, `-u` utilizadores, `-g` geozonas, `--dataservices`.
- **Repor os agendamentos em falta:**
  ```
  [container]  udata job schedule "0 2 * * *" aggregate-metrics
  [container]  udata job schedule "0 3 * * *" update-metrics
  [container]  udata job schedule "0 4 * * *" compute-site-metrics
  [container]  udata job schedule "0 9 * * *" compute-geozones-metrics
  ```
- **Worker ou beat parados:** [PC-4](#pc-4-reinício-de-serviços).
- **Não esperar pela cache:** [PC-9](#pc-9-limpar-a-cache-da-aplicação).

#### Verificação

`udata job scheduled` lista os quatro jobs; `/api/1/site/home/` e a homepage mostram o mesmo valor, atualizado.

#### Prevenção e escalonamento

- Confirmar os agendamentos depois de cada restauro (capítulo [14](#14-recuperação-após-falha)).
- Escalar: job que falha sempre no `worker.log` → desenvolvimento, com o traceback.

### 10. Falhas de armazenamento

#### Sintoma

- Erros de escrita (sem espaço, permissão recusada) ao carregar ficheiros ou nos registos.
- Um container novo não arranca, ou arranca sem conseguir escrever.
- Ficheiro publicado corrompido (checksum diferente do original).

#### Diagnóstico passo a passo

1. **Espaço:**
   ```
   [VM]  df -h
   [VM]  du -sh /opt/dadosgov/fs /opt/dadosgov/backend/logs /opt/dadosgov/frontend/logs
   ```
   Três frentes: ficheiros publicados (`fs/`), blocos de carregamento por limpar e registos.
2. **Os blocos de carregamento estão a ser limpos?** `udata job scheduled` deve listar `purge-chunks`; no `worker.log`, `Purging uploaded chunks` indica cada execução. Sem este job, os blocos acumulam-se, apesar da retenção de 24 h (`UPLOAD_MAX_RETENTION`).
3. **Permissões das pastas montadas:**
   ```
   [VM]  ls -ln /opt/dadosgov/backend/logs /opt/dadosgov/frontend/logs /opt/dadosgov/fs
   ```
   Resultado esperado: dono 10001:10001 (utilizador `dadosgov`). Uma pasta `0:0` (root) foi criada pelo Docker por não estar declarada no serviço de `chown`.
4. **Corrupção:** comparar o checksum do ficheiro publicado com o do original (`sha1sum`).

#### Resolução passo a passo

- **Blocos acumulados:** `udata job run purge-chunks`; se não estiver agendado, `udata job schedule "0 * * * *" purge-chunks`.
- **Registos:** confirmar que o logrotate está instalado (`docs/logrotate-setup.md`); corta aos 10 MB e mantém 50 ficheiros comprimidos.
- **Pasta com dono root:** `chown -R 10001:10001 <pasta>` e declarar a pasta no serviço de `chown` do compose (`init-logs` no backend, `init-dirs` no frontend); caso contrário volta a acontecer no próximo `up`.
- **Ficheiros publicados a crescer:** escalar para infraestrutura (aumento de disco).
- **Ficheiro corrompido:** pedir ao publicador que carregue de novo e escalar para desenvolvimento, com o id do recurso.

#### Verificação

`df -h` com margem; um carregamento de teste passa ([PC-11](#pc-11-smoke-test), passo 6); `ls -ln` com o dono certo.

#### Prevenção e escalonamento

- Qualquer bind mount novo é declarado no serviço de `chown` do compose.
- Alarme de disco nas VMs (infraestrutura).
- Escalar: disco → infraestrutura; corrupção → desenvolvimento.

### 11. Problemas de certificados/keys

#### Sintoma

- "assinatura SAML inválida" e `/api/1/me/` com 401 (capítulo [5](#5-autenticação-cmd)).
- Aviso de certificado no browser no endereço público.
- Falhas que parecem de certificado depois de mudar a configuração entre ambientes.

#### Diagnóstico passo a passo

1. **Certificado do fornecedor de serviço (nosso):** `openssl x509 -enddate -noout -in /opt/dadosgov/backend/udata/auth/saml/credentials/AMA.pem`. Validade expirada ou próxima.
2. **Certificado do fornecedor de identidade:** extraído de `metadata.xml` como no capítulo [5](#5-autenticação-cmd), passo 3. Deve ser do ambiente certo (pré-produção ou produção).
3. **Certificado TLS público:**
   ```
   [posto]  openssl s_client -connect <host público>:443 -servername <host público> </dev/null 2>/dev/null | openssl x509 -noout -enddate -subject
   ```
   O TLS público termina no F5 e é gerido pela infraestrutura.
4. **Credenciais presentes?** A pasta `udata/auth/saml/credentials/` não está no git; um deploy que recrie a pasta do backend sem a repor deixa o CMD e o eIDAS inoperacionais. `ls /opt/dadosgov/backend/udata/auth/saml/credentials/` deve mostrar `AMA.pem`, `private.pem` e `metadata.xml`.
5. **Configuração desalinhada:** comparar as chaves relevantes entre ambientes ([PC-10](#pc-10-ler-a-configuração-efetiva-sem-expor-segredos)), sem expor os valores.

#### Resolução passo a passo

- **Certificado SAML ou metadata expirados ou errados:** substituir o par de chaves (`AMA.pem`, `private.pem`) e o `metadata.xml` pelos do ambiente, reiniciar o `app` ([PC-4](#pc-4-reinício-de-serviços)) e revalidar com CMD **e** eIDAS reais.
- **Certificado TLS público:** pedido de renovação à infraestrutura, que o instala no F5; a aplicação não muda.
- **Credenciais em falta:** repor a partir da cópia de segurança cifrada (capítulo [13](#13-gestão-de-backups)).

#### Verificação

Login CMD e eIDAS reais; `openssl` mostra as novas datas.

#### Prevenção e escalonamento

- Registar as datas de expiração dos certificados SAML e TLS e pedir a renovação com pelo menos um mês de antecedência: a troca exige coordenação com a AMA.
- Guardar a cópia de segurança das credenciais fora do repositório e cifrada.
- Escalar: certificados SAML → AMA; TLS → infraestrutura.

### 12. Reinício de serviços

#### Sintoma

- Um deploy "não teve efeito": o comportamento antigo continua.
- Uma alteração de configuração não foi aplicada.
- Linhas `harakiri` ou `workers buried` no `app.log`.

#### Diagnóstico passo a passo

1. **Estado e idade dos containers:** [PC-3](#pc-3-estado-dos-containers). Um worker criado antes do último deploy corre código antigo.
2. **O commit na VM é o esperado?** [PC-3](#pc-3-estado-dos-containers), `git log -1`.
3. **O que mudou?** Código, `udata.cfg`, `.env` ou `docker-compose.yml`: determina o comando ([PC-4](#pc-4-reinício-de-serviços)).
4. **Eventos do uWSGI:** `harakiri` indica um pedido acima do tempo máximo; o uWSGI também recicla cada worker ao fim de cerca de 50 000 pedidos. Estes reinícios de worker são normais e não são incidentes.
5. **O worker Celery arrancou?** `docker logs --tail 200 udata-backend-worker` mostra o arranque e as filas.

#### Resolução passo a passo

Aplicar [PC-4](#pc-4-reinício-de-serviços) com o comando da linha certa da tabela. Depois de deploys que toquem em tarefas Celery ou harvesters, sempre `app`, `worker` **e** `beat`.

#### Verificação

[PC-3](#pc-3-estado-dos-containers) com os containers recém-criados ou reiniciados; o comportamento novo observado; [PC-11](#pc-11-smoke-test).

#### Prevenção e escalonamento

- Incluir o reinício de worker e beat no procedimento de deploy (capítulo [15](#15-aplicação-de-atualizações)).
- Escalar: `harakiri` recorrente na mesma rota → desenvolvimento.

### 13. Gestão de backups

#### Sintoma

- É preciso restaurar e não se sabe se existe um backup, de quando é, ou se funciona.
- Depois de um restauro, o login rebenta ou os jobs deixaram de correr.

#### Diagnóstico passo a passo

1. **O que tem de estar coberto** (nada disto está no git):
   - MongoDB, base `udata` (catálogo, utilizadores, agendamentos, registo de migrações).
   - `FS_ROOT` (`/opt/dadosgov/fs`): ficheiros publicados.
   - Configuração com segredos: `backend/udata.cfg`, os `.env` de backend e frontend, e `backend/udata/auth/saml/credentials/`.
   - Não precisam de backup: o Elasticsearch (reconstrói-se a partir do MongoDB) e o Redis (só dados transitórios).
2. **Existe e está atual?** Não há script de backup no repositório: o agendamento e a retenção são da infraestrutura. Confirmar com ela a existência e a data do último dump **antes** de precisar dele.
3. **O dump está completo?** Deve incluir as coleções `schedules` (sem ela, métricas, purgas e harvest deixam de correr sem aviso) e `migrations` (sem ela, o `migrate` tenta reaplicar tudo).

#### Resolução passo a passo

- **Backup** (num posto ou máquina com acesso ao MongoDB e com as ferramentas `mongodump`/`mongorestore`):
  ```
  [posto]  mongodump --uri "mongodb://<SERVER_MONGO>:27017/udata" --gzip --archive=udata-AAAAMMDD.gz
  [VM]     tar czf fs-AAAAMMDD.tgz -C /opt/dadosgov fs
  ```
  Copiar as credenciais e a configuração à parte, cifradas. Guardar tudo fora da VM que protegem.
- **Restauro.** **Atenção:** `--drop` apaga cada coleção da base de destino antes de a carregar, e o que lá estava perde-se. Antes de correr:
  1. Confirmar o `<SERVER_MONGO>` e o ambiente de destino com um segundo elemento da equipa.
  2. Fazer um dump do estado atual do destino (comando de backup acima), mesmo que esteja danificado, para poder voltar atrás.
  3. Parar `worker` e `beat` (`docker compose stop worker beat`), para nada escrever na base durante o restauro.
  ```
  [posto]      mongorestore --uri "mongodb://<SERVER_MONGO>:27017" --gzip --archive=udata-AAAAMMDD.gz --drop
  ```
  Seguido **obrigatoriamente** da sequência de migrações do capítulo [8](#8-problemas-de-base-de-dados) (resolução do `FieldDoesNotExist`) e da verificação dos agendamentos ([PC-5](#pc-5-filas-celery-e-jobs-agendados)). No fim, voltar a arrancar `worker` e `beat` (`docker compose start worker beat`).

#### Verificação

Testar o restauro num ambiente não produtivo, periodicamente: um backup nunca restaurado não está validado. Depois do restauro de teste, [PC-11](#pc-11-smoke-test).

#### Prevenção e escalonamento

- Registar quanto tempo demora cada restauro de teste.
- Escalar: agendamento, retenção e armazenamento dos backups → infraestrutura.

### 14. Recuperação após falha

#### Sintoma

Perda da VM, da base de dados, dos ficheiros ou do índice de pesquisa.

#### Diagnóstico passo a passo

1. **Determinar o que se perdeu:** base de dados, ficheiros (`fs/`), índice, configuração ou só containers. A ordem de reposição depende disso.
2. **O que se reconstrói e o que não:** o índice de pesquisa reconstrói-se a partir do MongoDB e nunca é o bloqueio; o MongoDB e o `fs/` só se recuperam de backup.
3. **Recuperações parciais criam inconsistências:** MongoDB sem `fs/` deixa recursos a apontar para ficheiros inexistentes (404 no download); o inverso deixa ficheiros órfãos.

#### Resolução passo a passo

Pela ordem, saltando o que não se perdeu:

1. Repor a VM, o código (`git clone` dos dois repositórios em `/opt/dadosgov`) e a configuração com segredos (`udata.cfg`, `.env`, credenciais SAML).
2. Repor o MongoDB (capítulo [13](#13-gestão-de-backups)) e correr as migrações ([PC-6](#pc-6-migrações-da-base-de-dados); depois de restauro, a sequência do capítulo [8](#8-problemas-de-base-de-dados)).
3. Repor `fs/` e confirmar o dono 10001:10001 (capítulo [10](#10-falhas-de-armazenamento)).
4. Subir os containers: `python run_servers.py` na raiz do monorepo ([PC-4](#pc-4-reinício-de-serviços)).
5. Se houver Elasticsearch: `udata search init-es` e `udata search index` ([PC-7](#pc-7-reindexação-da-pesquisa)).
6. Recalcular métricas: `udata metrics update` (capítulo [9](#9-problemas-na-apresentação-das-estatísticas-na-homepage)).
7. Reiniciar `worker` e `beat` para usarem os agendamentos repostos.

#### Verificação

`udata db check-integrity`, `udata job scheduled`, `udata harvest diagnose` e [PC-11](#pc-11-smoke-test) completo.

#### Prevenção e escalonamento

- Registar o tempo de cada passo, para ter um tempo de recuperação realista.
- Escalar: VM, rede, MongoDB → infraestrutura.

### 15. Aplicação de atualizações

#### Sintoma

- Uma alteração funciona em TST e falha em PPR ou PRD.
- Depois de um deploy, uma funcionalidade parte ou não muda.
- O CI de um pull request falha.

#### Diagnóstico passo a passo

1. **Foi saltado um passo pós-deploy?** Migração ([PC-6](#pc-6-migrações-da-base-de-dados)), reindexação ([PC-7](#pc-7-reindexação-da-pesquisa)) ou reinício de worker e beat ([PC-4](#pc-4-reinício-de-serviços)).
2. **Só falha em PPR/PRD?** Aponta para o F5 ([PC-8](#pc-8-pedido-direto-à-vm-ou-através-do-f5)): TST não tem o appliance.
3. **CI vermelho:** `gh pr checks <n> --repo amagovpt/<repo>`. O CI do backend (workflow `Tests`, job `Lint and test suite`) corre `ruff check`, `ruff format --check` e a suite pytest; o do frontend corre o lint. Falhas antigas já conhecidas na suite do backend estão diagnosticadas em LEDG-2322, LEDG-2328 e LEDG-2329.
4. **Que migrações vão correr?** `udata db migrate --dry-run` no ambiente de destino, antes de promover.

#### Resolução passo a passo

Fluxo de promoção, só no(s) repositório(s) alterado(s) (`amagovpt/udata-pt` backend, `amagovpt/dadosgov-fe` frontend):

1. Branch a partir de `develop` (`feature/...`, `bugfix/...`).
2. Pull request para `develop`; depois `develop` → `tst`, `tst` → `ppr`, `ppr` → `main`. Um ambiente de cada vez, nunca diretamente para `main`.
3. Depois de cada deploy: `udata db migrate`, reindexar se o mapping do Elasticsearch mudou, reiniciar `app`, `worker` e `beat` ([PC-4](#pc-4-reinício-de-serviços)) e correr [PC-11](#pc-11-smoke-test).
4. Quando a alteração abrange os dois repositórios, promover primeiro o lado compatível com a versão atual do outro (normalmente o backend, quando só acrescenta campos).

#### Verificação

[PC-11](#pc-11-smoke-test) no ambiente de destino e leitura dos registos ([PC-2](#pc-2-consultar-registos)) antes de dar a promoção por concluída.

#### Prevenção e escalonamento

- Alterações sensíveis a WAF, cookies ou carregamento de ficheiros só se dão por validadas em PPR.
- Escalar: falha só em PPR/PRD → infraestrutura com a comparação de [PC-8](#pc-8-pedido-direto-à-vm-ou-através-do-f5); regressão → desenvolvimento.

### 16. Limitações conhecidas da solução

Limitações de arquitetura e do alojamento, que não se corrigem com uma alteração de código. Gerem-se por mitigação e comunicam-se, em vez de se tratarem como incidentes.

#### Sintoma

- O problema reproduz-se em PPR/PRD e não em TST.
- Atrasos em harvest, indexação ou métricas em horas de maior carga.
- Pesquisa em baixo quando o Elasticsearch falha; páginas degradadas quando o CMS falha.

#### Diagnóstico passo a passo

1. **É o appliance?** O sintoma desaparece ao contornar o F5 ([PC-8](#pc-8-pedido-direto-à-vm-ou-através-do-f5)).
2. **É capacidade?** `udata worker status` durante o episódio ([PC-5](#pc-5-filas-celery-e-jobs-agendados)): filas a crescer com o worker ativo indicam saturação, não avaria. Capacidade fixa: 8 pedidos simultâneos no uWSGI e um único worker Celery com concorrência 4 para as três filas.
3. **É o CMS?** Erros de tempo esgotado do CMS no `frontend/logs/app.log`.

#### Resolução passo a passo

As limitações conhecidas e a mitigação em vigor:

- **F5/WAF só em PPR e PRD:** pedido formal de paridade de ambientes em `docs/infra-adc-waf-impact-ppr-prd.md`.
- **Limite de 16 MiB por pedido no F5:** carregamento em blocos (capítulo [6](#6-problemas-de-publicação-de-conjuntos-de-dados)).
- **NAT do F5 (todos os visitantes com o mesmo IP):** limites de pedidos por `user_or_ip`, nunca só por IP (capítulo [20](#20-bloqueios-por-rate-limit-429)).
- **Elasticsearch de nó único:** reindexação total só em janela planeada ([PC-7](#pc-7-reindexação-da-pesquisa)).
- **CMS externo:** tempo limite de 5 s nas chamadas ao CMS, para degradar a página em vez de a deitar abaixo.
- **Recursos recriados a cada colheita em 8 backends de harvest:** não divulgar os permalinks `/r/<uuid>` desses datasets como estáveis (capítulo [17](#17-bugs-conhecidos)).
- **Execução manual de harvesters:** desligada por omissão (`HARVEST_ENABLE_MANUAL_RUN`).

#### Verificação

A limitação está identificada e comunicada ao utilizador que a reportou.

#### Prevenção e escalonamento

- Se a capacidade do worker passar a ser o limite, separar um worker dedicado à fila `low` (harvest) de outro para `high` e `default`, em vez de subir a concorrência de um só.
- Escalar: paridade de ambientes e capacidade → infraestrutura; mudança de arquitetura → gestão do projeto.

### 17. Bugs conhecidos

Defeitos com causa identificada e sem correção aplicada em produção. Um relato que encaixe na assinatura de um deles não é um incidente novo.

#### Sintoma

Um relato de utilizador ou de operador que corresponde a uma das assinaturas da tabela abaixo.

#### Diagnóstico passo a passo

1. Comparar o que foi observado com a coluna "Assinatura".
2. Se encaixar, confirmar no Jira (projeto `LEDG`) que o ticket do defeito continua aberto e associar-lhe o relato.
3. Se não encaixar em nenhuma, é um incidente novo: seguir o capítulo da área afetada.

| Assinatura | Defeito |
| --- | --- |
| Pedidos de prefetch RSC que se repetem sem fim no separador Rede do browser | Links internos sem prefixo de idioma: o redirecionamento 307 invalida cada prefetch. Mitigado, não eliminado |
| 502 no download `/r/<id>` de recursos OGC lentos, só em PRD | O proxy de PRD corre com tempo limite de leitura de 10 s, quando o código usa 300 s (`DOWNLOAD_PROXY_READ_TIMEOUT_S`) |
| Palavras-passe fracas aceites no registo | Política de palavra-passe inativa quando o `.env` não é carregado (o `udata.cfg` sobrepõe-se às omissões) |
| O formulário de apoio confirma o envio mas não chega e-mail | O gate reCAPTCHA devolve 400 com o token em falta ou inválido (capítulo [19](#19-e-mail-e-notificações)) |
| Testes da suite do backend a falhar em `develop` sem relação com a alteração | Falhas antigas diagnosticadas em LEDG-2322, LEDG-2328 e LEDG-2329 |
| `/r/<uuid>` com 404 num dataset colhido que ainda existe | Ids de recurso recriados a cada colheita em 8 backends de harvest |

#### Resolução passo a passo

- **Prefetch RSC:** sem ação operacional; acompanhar o ticket de desenvolvimento.
- **502 OGC em PRD:** escalar para infraestrutura para alinhar o tempo limite do proxy com os 300 s.
- **Palavra-passe:** confirmar que o `.env` é carregado ([PC-10](#pc-10-ler-a-configuração-efetiva-sem-expor-segredos)).
- **Formulário de apoio:** capítulo [19](#19-e-mail-e-notificações).
- **Permalinks `/r/<uuid>`:** indicar o URL atual do recurso; a correção definitiva é reutilizar o id quando o URL coincide, como em `odspt.py`.

#### Verificação

O relato corresponde a uma assinatura e foi associado ao ticket existente.

#### Prevenção e escalonamento

O estado de cada defeito e o respetivo ticket estão no Jira, projeto `LEDG`. Um relato que não encaixe em nenhuma assinatura é um incidente novo: abrir ticket.

### 18. Workarounds temporários

Mitigações em vigor porque a correção definitiva depende de terceiros ou de trabalho ainda por fazer. Cada uma tem uma condição de remoção.

#### Sintoma

Comportamento que só se explica por uma mitigação esquecida, ou uma mitigação que desapareceu num refactor e deixou voltar o problema original.

#### Diagnóstico passo a passo

Confirmar, para cada mitigação, que ainda está no código em execução e se a condição de remoção já se cumpriu:

| Mitigação | Onde | Condição de remoção |
| --- | --- | --- |
| Keep-alive desligado entre o Next.js e o backend (evita o `ECONNRESET` nos carregamentos) | `setGlobalDispatcher` em `frontend/src/instrumentation.ts` | o problema de reutilização de ligações deixar de se reproduzir sem ela |
| Cache partilhada `listingCache.ts` em vez do Data Cache do Next (cujas chaves incluem cabeçalhos e fragmentam a cache por visitante) | `frontend/src/service/utils/listingCache.ts` | o Next deixar de incluir os cabeçalhos por visitante na chave |
| Limites por `user_or_ip` nos GET públicos (`PUBLIC_READ_LIMIT`, `PUBLIC_SEARCH_LIMIT`: 300 por minuto, 6000 por hora) | `backend/udata/api/limits.py` | o F5 passar a entregar o IP real do visitante |
| Tempo limite de 5 s nas chamadas ao CMS (`CMS_FETCH_TIMEOUT_MS`) | `frontend/src/service/utils/apollo-client.ts` | o CMS ter um tempo de resposta estável |
| Redirecionamentos dos URLs antigos com `/pages` | `frontend/next.config.ts` | os URLs antigos deixarem de receber tráfego |
| Reindexação e cálculo de métricas por comando manual | [PC-7](#pc-7-reindexação-da-pesquisa), capítulo [9](#9-problemas-na-apresentação-das-estatísticas-na-homepage) | os agendamentos serem fiáveis |
| `"strict": False` no modelo `User`, para arrancar com dumps que ainda têm `apikey` | recurso de emergência descrito em `docs/db-restore-apikey-fix.md`; **não está aplicado no código atual** (verificado a 2026-09-29) | correr a migração de `apikey` (capítulo [8](#8-problemas-de-base-de-dados)) |

#### Resolução passo a passo

- Mitigação ausente e problema de volta: repor a mitigação (ticket de desenvolvimento) e identificar o commit que a retirou.
- Condição de remoção cumprida: abrir ticket para a remover.

#### Verificação

Cada mitigação da tabela está presente no build em execução ou foi removida por decisão registada.

#### Prevenção e escalonamento

Associar cada workaround ao ticket da correção definitiva, para a remoção ficar planeada e não depender da memória da equipa.

### 19. E-mail e notificações

#### Sintoma

- O formulário de apoio confirma o envio e a mensagem não chega.
- E-mails automáticos (confirmação de conta, recuperação de palavra-passe) não chegam.

#### Diagnóstico passo a passo

1. **Houve tentativa de envio?** No `app.log` e no `worker.log`, à hora do envio ([PC-2](#pc-2-consultar-registos)):
   - Nenhuma tentativa: o pedido morreu antes, no gate reCAPTCHA (400 com o token em falta ou inválido).
   - Tentativa com erro: problema de SMTP.
2. **Configuração SMTP efetiva:** [PC-10](#pc-10-ler-a-configuração-efetiva-sem-expor-segredos), com as chaves `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USE_SSL` e `MAIL_DEFAULT_SENDER`. Um remetente `webmaster@udata` indica que o `.env` não foi carregado.
3. **Chave do reCAPTCHA:** `GOOGLE_RECAPTCHA_SECRET_KEY` definida no ambiente (confirmar apenas que não está vazia).
4. **Separar as duas causas:** pedir uma recuperação de palavra-passe para uma conta de teste. Se esse e-mail chega e o do formulário não, a causa é o gate.

#### Resolução passo a passo

- **reCAPTCHA:** repor a chave do ambiente no `.env` e recriar os containers (`docker compose up -d`, [PC-4](#pc-4-reinício-de-serviços)), ou desativar o gate onde não se aplica.
- **SMTP:** corrigir as variáveis `MAIL_*` no `.env` e recriar os containers.

#### Verificação

Enviar pelo formulário de apoio (o caminho do utilizador) e confirmar a receção; confirmar também a recuperação de palavra-passe. A confirmação de conta é válida 120 horas (`SECURITY_CONFIRM_EMAIL_WITHIN`).

#### Prevenção e escalonamento

- Documentação do sistema de e-mail em `docs/email-notifications.md`.
- Escalar: servidor SMTP → infraestrutura; reCAPTCHA → desenvolvimento.

### 20. Bloqueios por rate limit (429)

#### Sintoma

Muitos utilizadores legítimos recebem 429 (Too Many Requests) ao mesmo tempo, sobretudo em PPR/PRD.

#### Diagnóstico passo a passo

1. **De onde vêm os 429?** No `app.log`, 429 concentrados num só IP de origem, que é o do F5 e não o de nenhum visitante: o F5 faz NAT e todos partilham o mesmo contador.
2. **Que limite se aplica ao endpoint?** Procurar no recurso da API `limiter.limit(<LIMITE>, key_func=user_or_ip)` (p. ex. em `backend/udata/core/dataset/api.py`). Sem limite próprio, aplica-se o `RATELIMIT_DEFAULT` (200 por hora e 1000 por dia, **por IP**). Os limites específicos estão em `backend/udata/api/limits.py`.
3. **É um consumidor automático?** Utilizadores autenticados, incluindo por token de API, têm contador próprio (`user:<id>`). Um robô anónimo partilha o contador de todos (ver o caso da Hydra no capítulo [27](#27-pré-visualização-de-dados-e-análise-hydra)).

#### Resolução passo a passo

- **Endpoint com o limite por omissão:** passar o endpoint para chave `user_or_ip` e afinar o valor, via PR no backend (capítulo [15](#15-aplicação-de-atualizações)). Endpoints GET públicos nunca devem ficar no limite por IP neste alojamento.
- **Alívio imediato:** os contadores estão no Redis (base 3) e expiram sozinhos na janela do limite. Não apagar o Redis inteiro, que também guarda a fila e a cache.
- **Consumidor automático legítimo:** pedir-lhe que se autentique com token, ou dar-lhe um limite próprio.

#### Verificação

Depois do deploy, o mesmo padrão de tráfego deixa de gerar 429 concentrados no IP do F5.

#### Prevenção e escalonamento

- O limitador está ativo na suite de testes do backend: um limite demasiado apertado também faz falhar testes sem relação com ele.
- Escalar: entrega do IP real do visitante pelo F5 → infraestrutura; novos limites → desenvolvimento.

### 21. Operações de escrita bloqueadas pelo WAF (PUT/PATCH/DELETE)

#### Sintoma

Em PPR/PRD, a edição de perfil, a edição de datasets e outras operações de alteração ou eliminação falham com um HTTP 500 em HTML (página do WAF, cookie `cookie_adc_ext`, `Attack ID: 20000001`). Em TST/DEV funcionam.

#### Diagnóstico passo a passo

1. **O pedido chegou à aplicação?** Nenhuma linha no `backend/logs/app.log` à hora do pedido indica que foi bloqueado antes ([PC-2](#pc-2-consultar-registos)).
2. **Que método?** No separador Rede do browser: o pedido bloqueado é `PUT`, `PATCH` ou `DELETE`. A regra de *HTTP Verb Tampering* do WAF só deixa passar GET e POST.
3. **Confirmar sem o WAF:** repetir o mesmo pedido na VM ([PC-8](#pc-8-pedido-direto-à-vm-ou-através-do-f5)); os comandos de teste completos estão em `docs/http-method-override.md`.

#### Resolução passo a passo

- **Opção A (definitiva, da infraestrutura):** permitir `PUT`, `PATCH` e `DELETE` na regra do WAF para `/api/1/*` e `/api/2/*`. Pedido formal em `docs/infra-adc-waf-impact-ppr-prd.md`.
- **Opção B (aplicacional):** enviar os métodos de escrita num POST com o cabeçalho `X-HTTP-Method-Override`, reescrito por um middleware antes do encaminhamento, e ligado no frontend com `NEXT_PUBLIC_USE_METHOD_OVERRIDE=true`. **Não está integrada em `develop` de nenhum dos repositórios** (verificado a 2026-09-29): o lado do frontend está na branch `feat/http-method-override` de `amagovpt/dadosgov-fe`, e o middleware do backend nunca foi publicado em `amagovpt/udata-pt`, pelo que ainda não há uma versão completa que se possa testar. Avaliação em `docs/method-override-opcao-b-avaliacao.md`.

#### Verificação

Editar o perfil em PPR através do F5: a alteração é gravada e o `app.log` regista o pedido.

#### Prevenção e escalonamento

- Qualquer funcionalidade nova com métodos de escrita é testada em PPR antes de dar como validada.
- Escalar: regra do WAF → infraestrutura.

### 22. Vulnerabilidades reportadas em auditoria de segurança

#### Sintoma

Relato de auditoria ou de terceiros de abuso de endpoints de escrita sem limite, submissão em massa, SSRF ou enumeração de contas. Casos da auditoria externa: VULN-2078 (criação em massa de recursos comunitários), VULN-2083 (submissão em massa de discussões), VULN-2084 (SSRF na pré-visualização de fontes de harvest) e a enumeração de e-mails na troca de e-mail do perfil.

#### Diagnóstico passo a passo

1. **Reproduzir contra TST**, nunca contra PRD, com o pedido do relatório (ciclo de `curl`). Sem correção, os pedidos repetidos passam todos ou o DNS de saída é resolvido. Com correção: 429 a partir do limite, 409 para um duplicado, ou o host recusado.
2. **Seguir o runbook de verificação de cada caso:** `docs/runbook-ticket-59-vuln-2078.md`, `docs/runbook-ledg-1728-vuln-2083.md`, `docs/runbook-ledg-1729-vuln-2084.md`.
3. **Regressões do frontend:** a suite e2e `frontend-vulnerabilities` (`frontend/tests/e2e/frontend-vulnerabilities/`, `npm run test:e2e:vulns`) cobre as vulnerabilidades de frontend da mesma auditoria.

#### Resolução passo a passo

As correções em vigor, a confirmar que continuam presentes:

- Limites por utilizador em `backend/udata/api/limits.py` (`CONTENT_CREATE_LIMIT`, `COMMENT_CREATE_LIMIT`, `DISCUSSION_CREATE_LIMIT`, `HARVEST_PREVIEW_LIMIT`).
- Deduplicação de recursos comunitários por dataset, dono e URL, numa janela de 5 minutos.
- SSRF em quatro camadas: hosts proibidos e permitidos (`HARVEST_URL_HOST_DENYLIST`, `HARVEST_URL_HOST_ALLOWLIST`), validação antes da resolução DNS no formulário, e `_guard_url` em `BaseBackend.get/head/post` contra DNS rebinding.
- Troca de e-mail: resposta igual quer o endereço exista ou não, e comparação sem distinção de maiúsculas.

Uma vulnerabilidade nova segue o fluxo normal de correção (capítulo [15](#15-aplicação-de-atualizações)), com prioridade.

#### Verificação

O runbook de verificação do caso passa em TST e depois em PPR.

#### Prevenção e escalonamento

- Correr a suite `frontend-vulnerabilities` antes de promover alterações ao frontend.
- Escalar: vulnerabilidade nova → desenvolvimento e responsável de segurança, sem detalhes de exploração em canais abertos.

### 23. Contas duplicadas e ligação da identidade CMD

#### Sintoma

O mesmo cidadão tem duas contas: a conta tradicional (e-mail e palavra-passe, do portal anterior) e uma conta criada pelo login CMD com e-mail provisório `saml-*@autenticacao.gov.pt`. Não vê os seus datasets depois de entrar com CMD.

#### Diagnóstico passo a passo

1. Procurar pelo e-mail em `/admin/users` e verificar se há uma segunda conta `saml-*@autenticacao.gov.pt` com o mesmo nome.
2. Listar os NIC ainda por converter e as duplicadas que seriam juntas, sem alterar nada:
   ```
   [container]  udata user migrate-nics --dry-run
   ```
3. Contas institucionais com identidade pessoal: `scripts/audit_institutional_users.py` (capítulo [4](#4-gestão-de-organizações-e-datasets), passo 4).

#### Resolução passo a passo

- **Caminho normal:** o utilizador liga as contas no assistente `/migrate-account`, com prova de posse (código por e-mail ou palavra-passe da conta antiga). O interruptor é `MIGRATION_MODE_ENABLED`.
- **Em massa** (idempotente, sempre primeiro com `--dry-run`):
  ```
  [container]  udata user migrate-nics --dry-run
  [container]  udata user migrate-nics
  ```
- **Caso a caso:**
  ```
  [container]  udata user merge-saml <email_saml> <email_destino> --dry-run
  [container]  udata user merge-saml <email_saml> <email_destino>
  ```
  Descrição completa em `docs/saml-account-merge.md`. Juntar só depois de confirmar a posse das duas contas com o titular: sem prova de posse, uma fusão pode dar a um utilizador a conta de um homónimo.

#### Verificação

Uma só conta; o login CMD entra na conta com os datasets do utilizador.

#### Prevenção e escalonamento

- Nunca juntar contas só por nome ou por e-mail sem prova de posse.
- Escalar: fusões contestadas → gestão do portal; falhas do comando → desenvolvimento.

### 24. Organizações criadas indevidamente ou sem administrador

#### Sintoma

- Organizações sem datasets nem membros, criadas sem pedido.
- Organizações que ninguém consegue gerir (sem membro `admin`).
- Membros que apontam para utilizadores apagados.

#### Diagnóstico passo a passo

1. **Organizações sem dono:**
   ```
   [container]  udata organizations audit-unowned
   ```
   Considera o conteúdo que lhes pertence, as fontes de harvest e os pedidos de adesão pendentes.
2. **Criadas pela pré-visualização de harvest:** organizações recentes sem datasets nem membros, criadas à mesma hora que um `POST /api/1/harvest/source/preview/` no `app.log`. Os backends CKAN PT e ODS PT criavam uma organização quando o acrónimo remoto não tinha correspondência local; corrigido em LEDG-2320.
3. **Membros inexistentes:** `udata db check-integrity`.

#### Resolução passo a passo

- **Sem admin:** confirmar com a entidade quem deve gerir e atribuir-lhe o papel `admin` na organização (capítulo [4](#4-gestão-de-organizações-e-datasets)).
- **Sem conteúdo e indevidas:** eliminar em `/admin/organizations` e purgar (`udata purge --organizations`).
- **Membros órfãos:** remover o membro na organização.

#### Verificação

`udata organizations audit-unowned` deixa de listar a organização.

#### Prevenção e escalonamento

- Correr `audit-unowned` periodicamente.
- Escalar: organizações indevidas a reaparecer → desenvolvimento (regressão de LEDG-2320).

### 25. Contactos de datasets colhidos desatualizados ou duplicados

#### Sintoma

Um dataset colhido mostra o contacto antigo e o novo do publicador, ou um contacto que a fonte já não publica.

Nota: um dataset pode legitimamente ter vários publicadores e vários contactos. A anomalia são documentos `ContactPoint` idênticos ou contactos que a fonte já não publica, e não o número de contactos por papel.

#### Diagnóstico passo a passo

1. Comparar o contacto do dataset com o que a fonte publica hoje (`udata dcat parse-url <url>` para fontes DCAT; capítulo [1](#1-harvesting-nacional), passo 5).
2. Procurar documentos `ContactPoint` com o mesmo nome, e-mail, formulário, papel e dono. Afeta pelo menos os backends dgt, ogc e DCAT.

#### Resolução passo a passo

- **Até à correção:** corrigir à mão no dataset. Não impor um limite de um publicador por dataset.
- **Correção definitiva em curso (LEDG-2540, ainda não aplicada):** a reconciliação passa a substituir os contactos escritos pelo harvester pelos que a fonte publica, preservando os acrescentados à mão, e apaga os contactos que fiquem sem referência.

#### Verificação

O dataset mostra só os contactos que a fonte publica mais os acrescentados à mão.

#### Prevenção e escalonamento

Acompanhar LEDG-2540. Escalar: contactos errados na fonte → produtor.

### 26. Falha da API apresentada como página vazia

#### Sintoma

Uma listagem que devia ter conteúdo aparece vazia, ou com um ecrã de erro, enquanto a API responde bem quando chamada diretamente.

#### Diagnóstico passo a passo

1. Chamar diretamente o endpoint da listagem (`/api/1/datasets/?...`): se devolve dados, a falha está na chamada feita pelo frontend.
2. Hoje o erro é visível no ecrã (componentes `ErrorState` e `ErrorHelpCard`) e no `frontend/logs/app.log` ([PC-2](#pc-2-consultar-registos)), porque as chamadas feitas no servidor passam pelo interceptor instalado em `frontend/src/instrumentation.ts`. Procurar a linha à hora do acesso.
3. Um ecrã vazio **sem** erro no registo indica código que converte a exceção numa lista vazia, ou uma chamada marcada com `SKIP_GLOBAL_ERROR_HANDLING` que não trata o erro.

#### Resolução passo a passo

- Erro da API no registo: tratar a causa (capítulos [7](#7-indisponibilidade-de-serviços) e [20](#20-bloqueios-por-rate-limit-429)).
- Erro engolido pelo código: ticket de desenvolvimento, com a página e a hora.

#### Verificação

A listagem mostra os dados; uma falha forçada da API mostra o ecrã de erro e deixa linha no registo.

#### Prevenção e escalonamento

Em código novo, não converter uma exceção de fetch numa lista vazia. Escalar: desenvolvimento.

### 27. Pré-visualização de dados e análise Hydra

#### Sintoma

- Recursos sem os resultados da análise Hydra (formato, esquema, estatísticas) depois de um crawl.
- A pré-visualização em tabela de um recurso não aparece.

#### Diagnóstico passo a passo

1. **429 no writeback da Hydra:** no `app.log`, respostas 429 para `PUT`/`DELETE /api/2/datasets/<d>/resources/<rid>/extras/`, vindas do IP do crawler.
2. **Limite em vigor:** o writeback tem limite próprio por utilizador, `CRAWLER_WRITE_LIMIT` (1200 por minuto, 60 000 por hora). Confirmar que o crawler se autentica com token (sem token cai no limite por IP de 200 por hora).
3. **Pré-visualização:** confirmar que `TABULAR_API_URL` está definido no ambiente do container `udata-frontend-app` (é uma variável do frontend, não do backend):
   ```
   [VM]  docker exec udata-frontend-app printenv TABULAR_API_URL
   ```
4. Testar as rotas de proxy `/internal-api/proxy-tabular-data` e `/internal-api/proxy-tabular-profile` para o id do recurso. Também falha se o ficheiro remoto não responder ou vier sem `Content-Type`.

#### Resolução passo a passo

- **429:** garantir o token do crawler; depois voltar a correr o crawl para recuperar as análises perdidas.
- **`TABULAR_API_URL` em falta:** definir no `.env` do frontend e recriar o container ([PC-4](#pc-4-reinício-de-serviços)).
- **Ficheiro remoto:** contactar o publicador.

#### Verificação

Os extras de análise aparecem no recurso; a tabela de pré-visualização carrega.

#### Prevenção e escalonamento

Os proxies de pré-visualização buscam sempre pelo id do recurso através do backend (`/r/<id>`), nunca por um URL enviado pelo cliente, para não se tornarem um proxy SSRF. Escalar: serviço tabular ou Hydra em baixo → equipa responsável por esses serviços.

### 28. Erros de apresentação no frontend

#### Sintoma

- Um bloco da página pisca e muda logo depois de carregar, com aviso de *hydration* na consola do browser.
- Entidades HTML visíveis no texto (`&#x2F;`, `&amp;`), p. ex. datas como `01&#x2F;09&#x2F;2026`.

#### Diagnóstico passo a passo

1. [browser] Consola: aviso de *hydration mismatch*. O servidor desenhou uma coisa e o browser outra (tipicamente um componente que decide o que mostrar antes de `/api/1/me/` responder).
2. Texto com entidades HTML: dupla codificação (o i18next escapa e o React volta a escapar). Confirmar `escapeValue: false` em `frontend/src/app/i18n.ts`.
3. Nenhum dos dois é apanhado pelos testes automáticos: só aparecem ao carregar a página a sério.

#### Resolução passo a passo

- **Hydration:** ticket de desenvolvimento; a correção é renderizar o mesmo no servidor e no cliente e só decidir depois de os dados chegarem, ou desligar o SSR desse componente (`next/dynamic` com `ssr: false`), como no cabeçalho e no aviso de ligação da conta (LEDG-2517).
- **Dupla codificação:** repor `escapeValue: false` se tiver sido removido.

#### Verificação

Carregar a página no browser: sem aviso na consola e com o texto correto.

#### Prevenção e escalonamento

Confirmar sempre visualmente as alterações ao frontend, carregando a página. Escalar: desenvolvimento.

## 4. Anexos

### A1. Referências cruzadas

| Referência | Assunto | Capítulos |
| --- | --- | --- |
| LEDG-2320 | Pré-visualização de harvest deixou de criar organizações | [24](#24-organizações-criadas-indevidamente-ou-sem-administrador) |
| LEDG-2322, LEDG-2328, LEDG-2329 | Falhas antigas da suite de testes do backend | [15](#15-aplicação-de-atualizações), [17](#17-bugs-conhecidos) |
| LEDG-2484 | Totais de paginação estimados | [8](#8-problemas-de-base-de-dados) |
| LEDG-2517 | Hydration no aviso de ligação da conta | [28](#28-erros-de-apresentação-no-frontend) |
| LEDG-2540 | Reconciliação de contactos de harvest (em curso) | [25](#25-contactos-de-datasets-colhidos-desatualizados-ou-duplicados) |
| LEDG-2559 | Cadeia TLS incompleta na fonte de Ourém | [1](#1-harvesting-nacional) |
| udata-pt#94 | Ligação de contas CMD com prova de posse | [23](#23-contas-duplicadas-e-ligação-da-identidade-cmd) |
| udata-pt#207 | Extração de atributos eIDAS | [5](#5-autenticação-cmd) |
| udata-pt#218 | "Sair" termina primeiro a sessão local | [5](#5-autenticação-cmd) |
| dadosgov-fe `6896bd49` | Gestão global de erros no frontend | [26](#26-falha-da-api-apresentada-como-página-vazia) |
| `docs/db-restore-apikey-fix.md` | Restauro e migração de `apikey` | [8](#8-problemas-de-base-de-dados), [13](#13-gestão-de-backups) |
| `docs/http-method-override.md`, `docs/method-override-opcao-b-avaliacao.md` | Bloqueio de PUT/PATCH/DELETE pelo WAF | [21](#21-operações-de-escrita-bloqueadas-pelo-waf-putpatchdelete) |
| `docs/infra-adc-waf-impact-ppr-prd.md` | Impacto do F5/WAF e paridade de ambientes | [PC-0](#pc-0-ambientes-acessos-e-contactos), [16](#16-limitações-conhecidas-da-solução), [21](#21-operações-de-escrita-bloqueadas-pelo-waf-putpatchdelete) |
| `docs/saml-account-merge.md` | Fusão de contas SAML | [23](#23-contas-duplicadas-e-ligação-da-identidade-cmd) |
| `docs/runbook-ticket-59-vuln-2078.md`, `docs/runbook-ledg-1728-vuln-2083.md`, `docs/runbook-ledg-1729-vuln-2084.md` | Verificação das vulnerabilidades da auditoria | [22](#22-vulnerabilidades-reportadas-em-auditoria-de-segurança) |
| `docs/logrotate-setup.md` | Rotação de registos | [PC-2](#pc-2-consultar-registos), [10](#10-falhas-de-armazenamento) |
| `docs/email-notifications.md` | Sistema de e-mail | [19](#19-e-mail-e-notificações) |
| `docs/docker-setup.md`, `docs/INSTALLATION.md` | Instalação e containers | [PC-0b](#pc-0b-onde-corre-cada-serviço) |
| `docs/runbook-incidentes-dadosgov.md` | Tabela resumo que deu origem a este manual | - |

### A2. Parâmetros de configuração

Valores por omissão verificados no código (ver [A3](#a3-registo-da-verificação)). Os valores efetivos de cada ambiente leem-se com [PC-10](#pc-10-ler-a-configuração-efetiva-sem-expor-segredos).

| Parâmetro | Valor por omissão | Onde | Capítulos |
| --- | --- | --- | --- |
| `HARVEST_HTTP_MAX_RETRIES` | 3 | `udata.cfg` | [1](#1-harvesting-nacional) |
| `HARVEST_HTTP_TIMEOUT` | 15 s ligação, 600 s leitura | `udata.cfg` | [1](#1-harvesting-nacional) |
| `HARVEST_HTTP_RETRY_INITIAL_DELAY`, `HARVEST_HTTP_RETRY_MAX_DELAY` | 2 s, 60 s | `udata.cfg` | [1](#1-harvesting-nacional) |
| `HARVEST_DEFAULT_SCHEDULE` | `0 0 * * *` | `settings.py` | [1](#1-harvesting-nacional) |
| `HARVEST_AUTOARCHIVE_GRACE_DAYS` | 7 | `settings.py` | [1](#1-harvesting-nacional), [2](#2-harvesting-do-portal-europeu-de-dados) |
| `HARVEST_JOBS_RETENTION_DAYS` | 365 | `settings.py` | [1](#1-harvesting-nacional) |
| `HARVEST_ENABLE_MANUAL_RUN` | False | `settings.py` | [1](#1-harvesting-nacional), [16](#16-limitações-conhecidas-da-solução) |
| `HARVEST_URL_HOST_DENYLIST`, `HARVEST_URL_HOST_ALLOWLIST` | lista de domínios, None | `settings.py` | [1](#1-harvesting-nacional), [22](#22-vulnerabilidades-reportadas-em-auditoria-de-segurança) |
| `EXPORT_LIMIT` | 60/min, 1200/h | `api/limits.py` | [2](#2-harvesting-do-portal-europeu-de-dados) |
| `UPLOAD_LIMIT` | 120/min, 600/h, 2000/dia | `api/limits.py` | [6](#6-problemas-de-publicação-de-conjuntos-de-dados) |
| `PUBLIC_READ_LIMIT`, `PUBLIC_SEARCH_LIMIT` | 300/min, 6000/h | `api/limits.py` | [18](#18-workarounds-temporários), [20](#20-bloqueios-por-rate-limit-429) |
| `CRAWLER_WRITE_LIMIT` | 1200/min, 60 000/h | `api/limits.py` | [27](#27-pré-visualização-de-dados-e-análise-hydra) |
| `RATELIMIT_DEFAULT` | 200/h, 1000/dia, por IP | `udata.cfg` | [20](#20-bloqueios-por-rate-limit-429) |
| `RATELIMIT_STORAGE_URI` | Redis, base 3 | `udata.cfg` | [20](#20-bloqueios-por-rate-limit-429) |
| `RESOURCES_FILE_MAX_SIZE` | 1 GB | `udata.cfg` | [6](#6-problemas-de-publicação-de-conjuntos-de-dados) |
| `ALLOWED_RESOURCES_EXTENSIONS`, `ALLOWED_RESOURCES_MIMES` | listas | `udata.cfg`, `settings.py` | [6](#6-problemas-de-publicação-de-conjuntos-de-dados) |
| `UPLOAD_MAX_RETENTION` | 24 h | `settings.py` | [10](#10-falhas-de-armazenamento) |
| `ELASTICSEARCH_URL` | None (pesquisa pelo MongoDB) | `settings.py` | [PC-7](#pc-7-reindexação-da-pesquisa), [3](#3-indexação-e-pesquisa) |
| `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USE_SSL`, `MAIL_DEFAULT_SENDER` | do `.env`; remetente `webmaster@udata` sem `.env` | `udata.cfg`, `settings.py` | [19](#19-e-mail-e-notificações) |
| `GOOGLE_RECAPTCHA_SECRET_KEY` | vazio | `udata.cfg` | [19](#19-e-mail-e-notificações) |
| `SECURITY_CONFIRM_EMAIL_WITHIN` | 120 horas | `udata.cfg` | [19](#19-e-mail-e-notificações) |
| `MIGRATION_MODE_ENABLED` | True | `settings.py`, `udata.cfg` | [23](#23-contas-duplicadas-e-ligação-da-identidade-cmd) |
| `DOWNLOAD_PROXY_READ_TIMEOUT_S` | 300 s | `udata.cfg` | [17](#17-bugs-conhecidos) |
| `CMS_FETCH_TIMEOUT_MS` (frontend) | 5000 ms | `apollo-client.ts` | [7](#7-indisponibilidade-de-serviços), [18](#18-workarounds-temporários) |
| `TABULAR_API_URL` (frontend) | sem valor útil | `.env` do frontend | [27](#27-pré-visualização-de-dados-e-análise-hydra) |
| `NEXT_PUBLIC_USE_METHOD_OVERRIDE` (frontend) | só na branch `feat/http-method-override` do frontend | - | [21](#21-operações-de-escrita-bloqueadas-pelo-waf-putpatchdelete) |
| uWSGI | 4 processos, 2 threads, harakiri 120 s (600 s em CSV, upload e downloads), max-requests 50 000 | `uwsgi/front.ini` | [7](#7-indisponibilidade-de-serviços), [12](#12-reinício-de-serviços) |
| Worker Celery | concorrência 4, filas `default`, `high`, `low` | `docker-compose.yml`, `settings.py` | [PC-5](#pc-5-filas-celery-e-jobs-agendados), [16](#16-limitações-conhecidas-da-solução) |
| Cache da homepage | 300 s no backend, 10 s no frontend | `core/site/api.py`, `service/api/system` | [9](#9-problemas-na-apresentação-das-estatísticas-na-homepage) |

### A3. Registo da verificação

Verificado a 2026-09-29 contra `origin/develop` de `amagovpt/udata-pt` (`1fe3e8ad6`) e de `amagovpt/dadosgov-fe` (`61cae2aa`): todos os comandos `udata` citados e as suas opções (definições click em `udata/commands/`, `udata/harvest/commands.py`, `udata/search/commands.py`, `udata/core/*/commands.py`), os nomes dos jobs, os parâmetros da tabela [A2](#a2-parâmetros-de-configuração), os nomes dos containers e serviços compose, as filas Celery, as rotas SAML e os caminhos dos scripts e documentos.

Diferenças encontradas em relação ao texto do ponto 7 do relatório, já corrigidas neste manual:

| No relatório | Correção |
| --- | --- |
| Restauro com `docker exec -i udata-mongodb mongorestore` | Não existe container MongoDB nos ambientes: o MongoDB corre numa máquina externa (`SERVER_MONGO`); `mongodump` e `mongorestore` correm com `--uri` a partir de uma máquina com acesso |
| Serviço `init-dirs` para os bind mounts | É `init-logs` no backend e `init-dirs` no frontend |
| `udata harvest schedule <slug>` sem mais | O crontab passa-se por opções (`-m`, `-h`, `-d`, `-D`, `-M`) |
| ISR de 60 s no frontend para a homepage | É 10 s (a chamada agregada da homepage) |
| `strict: False` no modelo `User` como workaround em vigor | Não está aplicado no código atual; é um recurso de emergência documentado |
| Reindexação com `udata search index` como resolução geral | Só se aplica com `ELASTICSEARCH_URL` definido; o `udata.cfg` versionado usa a pesquisa do MongoDB |
| `udata db upgrade` (no `CLAUDE.md` do monorepo) | O comando é `udata db migrate` |
| Opção B do method override "desenvolvida e testada" | Confirmado que não está em `develop` de nenhum dos repositórios |

Para repetir a verificação depois de alterações, `udata <grupo> --help` dentro do container ([PC-1](#pc-1-executar-comandos-udata)) mostra os comandos e opções em vigor.

### A4. Glossário

- **ADC / F5 / WAF** - appliance de rede à frente de PPR e PRD que termina o TLS, faz NAT, balanceia e filtra pedidos (firewall aplicacional).
- **Beat** - processo Celery que dispara as tarefas agendadas.
- **Bind mount** - pasta da VM montada dentro de um container.
- **Carregamento em blocos (chunked)** - envio de um ficheiro em partes de 1 MB, juntas no fim.
- **CMD** - Chave Móvel Digital, autenticação do Estado português.
- **CMS / Squidex** - sistema de gestão de conteúdos que fornece o conteúdo editorial das páginas públicas.
- **Crontab** - expressão de agendamento (minuto, hora, dia do mês, mês, dia da semana).
- **DCAT-AP** - perfil europeu de metadados de catálogos de dados.
- **DBRef** - referência de um documento MongoDB para outro.
- **eIDAS** - autenticação transfronteiriça de cidadãos da UE.
- **Harakiri** - tempo máximo de um pedido no uWSGI, após o qual o worker é morto.
- **Harvest / harvester** - colheita automática de metadados de uma fonte remota.
- **HVD** - High-Value Datasets, conjuntos de dados de elevado valor (Regulamento de Execução (UE) 2023/138).
- **Hydra** - crawler que analisa os recursos e devolve os resultados ao portal.
- **ISR** - Incremental Static Regeneration, cache de páginas do Next.js com revalidação periódica.
- **Metadata SAML** - ficheiro XML com os certificados e endereços do fornecedor de identidade.
- **PeriodicTask** - documento MongoDB com um agendamento Celery.
- **Rate limit** - limite de pedidos por janela de tempo; excedido, devolve 429.
- **RSC** - React Server Components; o prefetch RSC é a pré-carga das páginas seguintes.
- **SAML** - protocolo de autenticação federada usado pela CMD e pelo eIDAS.
- **SHACL** - linguagem de validação de grafos RDF, usada pelo validador do data.europa.eu.
- **SSR** - renderização no servidor.
- **SSRF** - Server-Side Request Forgery, induzir o servidor a fazer pedidos a destinos escolhidos pelo atacante.
- **udata** - plataforma de portais de dados abertos em que assenta o backend.
- **uWSGI** - servidor de aplicações que corre o backend Python.
- **Worker** - processo Celery que executa as tarefas assíncronas.
