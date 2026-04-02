# Opções de Ordenação dos Filtros — dados.gov.pt

Este documento descreve as opções de ordenação disponíveis nas páginas de listagem de Conjuntos de Dados, Organizações e Reutilizações.

---

## Como funciona a ordenação

Quando o utilizador acede a uma listagem (por exemplo, a página de conjuntos de dados), pode escolher como pretende ordenar os resultados através de um seletor de filtro. A ordenação padrão — aplicada quando nenhuma opção é escolhida — é sempre **do mais recente para o mais antigo**.

---

## Relevância

A **Relevância** é a opção de ordenação mais inteligente e é a predefinição quando existe uma pesquisa por texto.

### O que faz

Ordena os resultados pelo grau de correspondência com o texto que o utilizador escreveu na barra de pesquisa. Os resultados que melhor correspondem à pesquisa aparecem no topo.

### Critérios de ordenação

A pontuação de cada resultado é calculada com base em **quão bem o texto da pesquisa aparece nos campos indexados** de cada item. Os campos considerados são:

- **Conjuntos de dados**: título, descrição, palavras-chave (tags) e nome da organização
- **Organizações**: nome e descrição
- **Reutilizações**: título e descrição

A pontuação é mais alta quando:
- **Todos os termos pesquisados estão presentes** — a pesquisa funciona em modo AND, ou seja, um resultado que contenha todas as palavras da pesquisa pontua mais do que um que contenha apenas algumas.
- **Os termos aparecem em campos mais importantes** — por exemplo, um termo no título tem mais peso do que o mesmo termo apenas na descrição.
- **Os termos aparecem várias vezes** ao longo do conteúdo do item.

### Quando não há texto pesquisado

Se o utilizador navegar na listagem sem escrever nada na pesquisa e selecionar "Relevância", o portal aplica a ordenação padrão (**mais recente primeiro**), pois não existe nenhum critério de correspondência para calcular.

---

## Conjuntos de Dados

Ordenação padrão: **mais recente primeiro**

| Opção | O que ordena |
|---|---|
| Relevância | Grau de correspondência com a pesquisa (ver secção acima) |
| Mais recente | Data de publicação, do mais recente para o mais antigo |
| Última atualização | Data da última alteração ao conjunto de dados, da mais recente para a mais antiga |
| Seguidores | Número de seguidores, do mais seguido para o menos |
| Reutilizações | Número de reutilizações registadas, do mais reutilizado para o menos |

---

## Organizações

Ordenação padrão: **mais recente primeiro**

| Opção | O que ordena |
|---|---|
| Relevância | Grau de correspondência com a pesquisa (ver secção acima) |
| Mais recente | Data de última modificação, da mais recente para a mais antiga |
| Mais antigo | Data de última modificação, da mais antiga para a mais recente |
| Subscritores | Número de subscritores, do mais subscrito para o menos |
| Reutilizações | Número de reutilizações registadas, do mais reutilizado para o menos |

---

## Reutilizações

Ordenação padrão: **mais recente primeiro**

| Opção | O que ordena |
|---|---|
| Relevância | Grau de correspondência com a pesquisa (ver secção acima) |
| Mais recente | Data de última modificação, da mais recente para a mais antiga |
| Mais antigo | Data de última modificação, da mais antiga para a mais recente |
| Seguidores | Número de seguidores, do mais seguido para o menos |

---

## Comparação entre secções

| Opção de ordenação | Conjuntos de Dados | Organizações | Reutilizações |
|---|:---:|:---:|:---:|
| Relevância | Sim | Sim | Sim |
| Mais recente | Sim | Sim | Sim |
| Mais antigo | — | Sim | Sim |
| Última atualização | Sim | — | — |
| Seguidores / Subscritores | Sim | Sim | Sim |
| Reutilizações | Sim | Sim | — |
