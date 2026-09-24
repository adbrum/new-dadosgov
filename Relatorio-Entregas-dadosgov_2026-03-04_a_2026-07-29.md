# dados.gov.pt — Relatório de Entregas

**Período:** 4 de março de 2026 – 29 de julho de 2026
**Última versão em produção:** v1.4.10, colocada em produção a 28 de julho de 2026

---

## 1. Sumário executivo

| Indicador | Valor |
| --- | --- |
| Itens de trabalho concluídos | **817** |
| — Correções de erros | 264 |
| — Novas funcionalidades e melhorias | 553 |
| Versões colocadas em produção | **14** (v1.3.5 → v1.4.10) |
| Vulnerabilidades de segurança fechadas | **12 novas + 17 remanescentes de auditorias anteriores** |
| Vulnerabilidades em componentes de terceiros corrigidas | 96 |

**Três mensagens principais:**

1. **O portal novo foi construído e colocado em produção neste período.** Área pública e área de administração renovadas, autenticação por Chave Móvel Digital e eIDAS, gestão de conteúdos autónoma, área de APIs, e catálogo — com 14 versões sucessivas em produção.

2. **Todas as vulnerabilidades reportadas nas auditorias de segurança foram corrigidas, com testes automáticos que impedem a sua reintrodução** — incluindo uma vulnerabilidade **crítica** que permitia a tomada de contas de utilizador.

3. **Os problemas de estabilidade em produção foram resolvidos na origem**, e não com paliativos: eliminadas as causas dos "logouts aleatórios", das listagens que apareciam vazias, da corrupção ocasional de ficheiros carregados, e dos tempos de espera excessivos na recolha automática de dados (melhoria de cerca de 70 vezes).

---

## 2. Segurança

### 2.1 Vulnerabilidades das auditorias — corrigidas e testadas

| Ref. auditoria | Gravidade | Vulnerabilidade | Correção |
| --- | --- | --- | --- |
| **VULN-2077** | **Crítica** | **Tomada de conta através da autenticação com Chave Móvel Digital / eIDAS.** Era possível forjar uma resposta de autenticação e assumir a identidade de qualquer utilizador, porque um caminho alternativo do código lia os dados de identificação sem revalidar a assinatura digital. | Passou a aceitar exclusivamente dados de respostas com assinatura validada; em caso de falha de validação, o acesso é recusado (comportamento "fecha por omissão"). Acrescentadas: verificação da entidade emissora, ligação obrigatória entre a identidade e o número de identificação civil, proteção contra reutilização de respostas antigas, e registo de auditoria de todas as decisões de autenticação. Cobertura por 12 testes automáticos. |
| **VULN-2092** | Alta | **Controlo de acesso quebrado nos dados de utilizadores.** Endereços de contacto (dados pessoais) e listas de utilizadores eram acessíveis sem sessão iniciada. | Autenticação passou a ser obrigatória em todas as leituras de dados de utilizador. |
| **VULN-2075**<br>**VULN-2076** | Alta | **Injeção de código em conteúdos (XSS armazenado)** nas descrições de organizações, reutilizações, APIs e recursos da comunidade. | Limpeza dos conteúdos no momento da gravação, no servidor e no cliente, e endurecimento das políticas de segurança do navegador. |
| **VULN-2079**<br>**VULN-2084** | Alta | **Pedidos forjados a partir do servidor (SSRF)** — no conversor de ficheiros CSV e nos endereços das fontes de recolha automática de dados. | Validação e bloqueio de destinos internos e privados; estendido a todos os mecanismos de recolha, incluindo os desenvolvidos especificamente para Portugal, e reativada a verificação de certificados de segurança. |
| **VULN-2088** | Média | **Sessão não terminada no logout.** Uma sessão capturada antes do encerramento continuava válida no servidor. | O encerramento de sessão passou a invalidar imediatamente todas as sessões ativas do utilizador, em todos os dispositivos. |
| **VULN-2090** | Média | **Enumeração de contas de utilizador.** As respostas do sistema permitiam distinguir contas existentes de inexistentes. | As respostas passaram a ser indistinguíveis para pedidos não autenticados. |
| **VULN-2078**<br>**VULN-2083**<br>**VULN-2089** | Média | **Submissão em massa** no formulário público de contacto, nas discussões e nos recursos da comunidade — permitia inundar a caixa de suporte e o portal. | Limites de submissão por endereço e por utilizador, com eliminação de duplicados. Complementado com reCAPTCHA. |
| **VULN-2091** | Baixa | **Exposição de informação técnica em mensagens de erro.** | Confirmado que não ocorre na configuração de produção; como defesa adicional, foram removidas as sugestões de rotas nas mensagens de erro. |
| **VULN-1376, 1377, 1379, 1496, 1497, 1498, 1515, 1532, 1533, 1534, 1593, 1594, 1595, 1596, 1688, 1878, 1882** | — | **17 vulnerabilidades remanescentes de auditorias anteriores** (lote KITS24) | Verificadas, corrigidas e cobertas por testes automáticos de regressão, tanto na camada de serviços como na interface. |

### 2.2 Endurecimento transversal

- **reCAPTCHA** implementado na recuperação de palavra-passe e na página de Ajuda e Contactos.
- **Limitação de tentativas** nas operações de autenticação, para travar ataques de força bruta.
- **Políticas de segurança do navegador** reforçadas, eliminando a execução de código não assinado nas páginas.
- **Número de identificação civil armazenado de forma irreversível** (não é guardado em claro).
- **Todos os ficheiros do catálogo são servidos como transferência** e nunca abertos diretamente no navegador, o que elimina uma via de ataque por ficheiro malicioso.
- **Validação de ficheiros carregados** unificada para a área de administração e para os acessos programáticos: tipo, formato real do ficheiro, e deteção de conteúdo perigoso.
- **Isolamento reforçado da infraestrutura** — os serviços deixaram de correr com privilégios elevados; ocultada a versão do servidor.
- **96 vulnerabilidades em componentes de terceiros corrigidas** (1 crítica, 24 de gravidade alta, 62 média, 9 baixa).
- **Novo sistema de chaves de acesso à API** — várias chaves por utilizador, revogáveis individualmente, em substituição da chave única anterior.

---

## 3. Estabilidade e fiabilidade em produção

Estes foram os problemas com maior impacto sentido pelos utilizadores. Todos foram diagnosticados até à causa de origem.

### 3.1 Bloqueios generalizados do portal — cinco vagas de correção

**Sintomas reportados:** utilizadores desligados aleatoriamente da sessão, listagens que apareciam vazias, páginas públicas que deixavam de carregar, e carregamento de ficheiros a falhar para todos os editores em simultâneo.

**Causa de origem:** o equipamento de segurança perimetral apresenta todo o tráfego ao portal como vindo de um único endereço. O mecanismo de proteção contra abuso, que conta pedidos por endereço, passava assim a funcionar como um **limite partilhado por todos os visitantes do site**: bastava o volume agregado atingir o teto para que todos os utilizadores ficassem bloqueados.

**Correções, aplicadas por área:** pesquisa e listagens públicas; transferências, exportações e feeds; carregamento de ficheiros; leituras públicas e sugestões de pesquisa; e verificação de sessão do utilizador — esta última responsável pelos **logouts aleatórios**, agora eliminados. Complementarmente, o portal passou a comunicar corretamente o endereço real de cada visitante, para que a contagem seja individual e não coletiva.

Foi também isolado o robô de análise de qualidade dos dados, que estava a perder os resultados do seu trabalho por ser bloqueado a meio de cada varrimento do catálogo.

### 3.2 Corrupção ocasional de ficheiros carregados

Ficheiros carregados ou substituídos pela área de administração ficavam por vezes corrompidos. Foram identificadas três causas: dois carregamentos do mesmo ficheiro no mesmo segundo podiam escrever em cima um do outro; a recomposição do ficheiro a partir dos seus fragmentos não verificava a integridade do resultado; e uma repetição automática de envio, provocada por uma quebra de rede, gerava erro.

**Correção:** os fragmentos passaram a poder ser reenviados sem efeitos secundários; o ficheiro final só é aceite se a totalidade dos fragmentos existir e o tamanho corresponder ao anunciado; a gravação é atómica, pelo que nunca é possível ler um ficheiro incompleto. Do lado do utilizador, é agora apresentada uma mensagem clara quando o ficheiro é alterado em disco a meio do envio, e as repetições de envio deixaram de gerar recursos duplicados.

### 3.3 Ficheiros grandes

- Carregamentos passaram a ser feitos por fragmentos, para atravessar o equipamento de segurança perimetral.
- Corrigida uma falha de memória que provocava erro nos ficheiros de grande dimensão.
- Limite máximo de 800 MB por recurso, agora imposto no servidor.
- **Transferências de ficheiros grandes passaram a ser retomáveis** — antes, uma transferência interrompida (por exemplo, de um ficheiro geográfico de 634 MB) reiniciava sempre do zero.
- Suporte a novos formatos: pacotes geográficos comprimidos e documentos Word.

### 3.4 Ficheiros de dados legítimos rejeitados indevidamente

A verificação de segurança dos ficheiros carregados aplicava-se indiscriminadamente a todos os formatos. Um ficheiro CSV de grande dimensão que contivesse, numa célula, texto semelhante a código era rejeitado como perigoso — e quanto maior o ficheiro, maior a probabilidade de isto acontecer. A verificação passou a aplicar-se apenas aos formatos que o navegador pode interpretar; os formatos de dados deixaram de ser afetados.

### 3.5 Desempenho

| Situação | Antes | Depois |
| --- | --- | --- |
| Histórico de recolhas de dados do INE (cerca de 13 mil registos) — página não carregava | 8,4 MB transferidos, ~29 segundos | 477 bytes, 0,03 segundos |
| Recolha automática de dados do INE, fase de deteção de alterações | 5 362 ms por bloco | 77 ms por bloco (**~70× mais rápido**) |
| Conjuntos de dados em destaque a surgir na página inicial | até 6 minutos de atraso | imediato |

Trabalho estrutural associado: otimização da base de dados que beneficia **todos** os mecanismos de recolha; consolidação de chamadas ao serviço, eliminando as quebras de ligação que ocorriam sob carga elevada; e geração das páginas no servidor com cache, reduzindo o tempo de resposta ao visitante.

### 3.6 Operação

- Registos de atividade movidos para armazenamento externo aos serviços, com rotação automática.
- O sistema passou a recusar arrancar em caso de indisponibilidade da base de dados, em vez de arrancar num estado inconsistente.
- Controlado o crescimento do espaço ocupado pela cache de imagens.
- Dois incidentes de falta de espaço em produção (2 e 13 de julho) analisados e resolvidos.

---

## 4. Novas funcionalidades entregues

### 4.1 Portal novo

**Área pública:** página inicial, catálogo de dados com filtros avançados, organizações, reutilizações, notícias e artigos, data stories, perfil de utilizador e perfil público, pesquisa global transversal, áreas de conhecimento e aprendizagem com minicursos, perguntas frequentes, licenças e termos de utilização, roadmap público, áreas temáticas e publicações.

**Área de administração:** publicação e edição de conjuntos de dados (com arrastar-e-largar e carregamento múltiplo), reutilizações, organizações e respetivos membros, mecanismos de recolha automática, artigos, recursos da comunidade, discussões, gestão de utilizadores, estatísticas, gestão editorial, consulta de registos de sistema, e transferência de titularidade de conjuntos de dados e reutilizações.

### 4.2 Autenticação

- **Chave Móvel Digital** e **eIDAS**, através da Autenticação.gov.
- Migração das contas antigas para os novos meios de autenticação.
- Regras de associação de conta: o acesso direto exige correspondência do número de identificação civil; a correspondência apenas por endereço de email exige confirmação de titularidade — o que fecha uma via de apropriação indevida de contas.

### 4.3 Área de APIs

Restituição completa da área de APIs do portal:

- Listagem pública com filtros funcionais e contagem correta dos conjuntos de dados associados.
- Página de detalhe com informação técnica, autoria, discussões e conjuntos de dados relacionados.
- **Documentação técnica interativa (Swagger)** integrada na página, quando a API a disponibiliza.
- Criação e edição na área de administração, com publicação imediata ou guardar como rascunho.
- Listagem das APIs próprias no perfil do utilizador.
- APIs relacionadas visíveis na página de cada conjunto de dados.
- **Publicação de APIs restrita a organizações com o emblema "Serviço público"**, regra imposta no serviço e não apenas na interface.

### 4.4 Gestão de conteúdos autónoma

Os conteúdos editoriais do portal passaram a ser geridos por uma plataforma de gestão de conteúdos, permitindo à equipa de conteúdos alterar textos sem depender de intervenção de desenvolvimento: página inicial, cabeçalho e rodapé, páginas institucionais, perguntas frequentes, licenças e termos de utilização, áreas temáticas, publicações, roadmap, minicursos e materiais de aprendizagem, tutorial de utilização da API e acesso ao catálogo por consulta estruturada. Instalado e validado em todos os ambientes.

### 4.5 Versão em inglês

Preparação do portal para funcionar em português e inglês, com tradução progressiva: autenticação, conjuntos de dados, reutilizações, organizações, APIs, data stories e área de administração. Datas, números e dimensões de ficheiro passaram a seguir o idioma ativo. Traduzidos para português os níveis administrativos (distrito, concelho, freguesia) e as mensagens de erro.

### 4.6 Explorador de dados

Em desenvolvimento: base da aplicação, ligação ao serviço de dados tabulares, visualização em tabela e configuração de filtros.

### 4.7 Outras funcionalidades

- **Pré-visualização de dados em tabela** para ficheiros CSV e Excel, diretamente no catálogo.
- **Emblemas de organização** — "Serviço público" e "Certificado", visíveis publicamente, atribuídos exclusivamente por administradores do portal.
- **Data stories publicadas:** emprego público, esperança de vida, densidade *versus* consumo, territórios inteligentes, serviços públicos no canal presencial, pobreza energética, gases com efeito de estufa por setor de atividade, e pressão turística.
- **Recolha automática de dados:** reescrita do mecanismo do INE, agora mais rápido e tolerante a falhas de rede; filtragem por etiquetas na recolha de dados geográficos; atualização do mecanismo de recolha de portais CKAN; fluxo de validação e rejeição de fontes; validação do agendamento; visibilidade dos erros de recolha e da entidade produtora na área de administração; remoção de um mecanismo obsoleto.
- **Métricas:** contabilização de visualizações e transferências com eliminação de duplicados, agregação por organização, e novo processo de consolidação de métricas.
- **Pesquisa:** insensível a acentuação, estendida às descrições, pesquisa de organizações por nome e por sigla, filtros de seleção múltipla, filtro por frequência de atualização e por estado de publicação.
- **Google Analytics** e **Google Search Console** configurados; metadados de partilha em redes sociais e melhorias de posicionamento em motores de busca.
- **Navegação hierárquica** (caminho de navegação) gerada automaticamente e coerente em todo o portal.
- **Notificações por email:** novas reutilizações associadas a conjuntos de dados, pedidos e aprovações de adesão a organizações, e boas-vindas a novos membros — todas traduzidas para português.
- **Ligações antigas do portal continuam a funcionar** através de redirecionamentos permanentes, preservando emails já enviados, favoritos dos utilizadores e páginas indexadas pelos motores de busca.

---

## 5. Interoperabilidade europeia

Os conjuntos de dados de elevado valor (*High Value Datasets*) não estavam a ser corretamente classificados no catálogo europeu recolhido pelo portal data.europa.eu. A causa: as designações das categorias europeias tinham sido herdadas em francês do projeto de origem, pelo que nunca correspondiam às etiquetas em português usadas nos conjuntos de dados portugueses — e a classificação era simplesmente omitida.

Corrigido com a tradução das categorias para português. **Os conjuntos de dados de elevado valor portugueses passaram a ser corretamente identificados como tal no catálogo europeu.** Trabalho relacionado: exposição dos direitos de acesso e de utilização no formato normalizado europeu, e validação do processo de recolha pelo data.europa.eu.

---

## 6. Qualidade e engenharia

- **Testes automáticos:** cada vulnerabilidade corrigida tem um teste que impede a sua reintrodução; testes de percurso completo do utilizador na área pública, na área de administração e na área de APIs; e uma bateria de testes dedicada a vulnerabilidades de interface.
- **Verificação automática de qualidade de código** integrada no processo de desenvolvimento.
- **Consolidação técnica do portal** em 17 frentes de trabalho, reduzindo duplicação e o esforço de manutenção futura.
- **Registo de alterações** mantido para ambas as componentes do portal, e processo de promoção entre ambientes documentado.
- **Documento de Arquitetura de Soluções** do dados.gov.pt criado e mantido atualizado (5 revisões no período).

---

## 7. Versões colocadas em produção

Catorze colocações em produção no período:

v1.3.5 · v1.3.6 · v1.3.7 · v1.3.8 · v1.3.9 · v1.4.0 · v1.4.1 · v1.4.2 · v1.4.3 · v1.4.4 · v1.4.7 · v1.4.8 · v1.4.9 · v1.4.10

(as versões v1.4.5 e v1.4.6 foram validadas em pré-produção e integradas em versões posteriores)

---

## 8. Pontos de atenção e próximos passos

| Tema | Situação |
| --- | --- |
| **Chaves do reCAPTCHA** | O reCAPTCHA está implementado, mas permanece inativo enquanto as respetivas chaves não forem configuradas em cada ambiente. Até lá, a proteção contra submissões automatizadas assenta apenas nos limites de tentativas. **Requer ação de configuração.** |
| **Re-teste da auditoria de segurança** | O último lote de correções está em produção e aguarda validação por re-teste da equipa de auditoria. |
| **Tempo limite do equipamento de segurança perimetral** | As transferências de ficheiros grandes estão mitigadas (passaram a ser retomáveis), mas a correção definitiva — aumentar o tempo limite de resposta para ficheiros do catálogo — depende da equipa de infraestrutura. |
| **Espaço de armazenamento em produção** | Dois incidentes no período, ambos resolvidos. Recomenda-se monitorização contínua. |
| **Transição para o modelo DevOps** | Novos procedimentos definidos para os ambientes de desenvolvimento e teste, em preparação para a migração. |
| **Em desenvolvimento** | Explorador de dados, validador automático de qualidade de dados, mapa do site, e consolidação da plataforma de análise de qualidade. |
