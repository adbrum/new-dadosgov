# Projeto Ágora - Mapeamento do Código

> Inventário de componentes e rotas do projeto udata_agora.

---

## 🗺️ Rotas (Páginas)

As rotas estão localizadas em `src/app/pages/`.

| Rota | Descrição | Componente Principal |
| :--- | :--- | :--- |
| `/` | Homepage | `src/app/page.tsx` |
| `/pages/datasets` | Listagem de Datasets | `DatasetsClient` |
| `/pages/datasets/[id]` | Detalhe de Dataset | `DatasetDetailClient` |
| `/pages/reuses` | Listagem de Reutilizações | `ReusesClient` |
| `/pages/reuses/[id]` | Detalhe de Reutilização | `ReuseDetailClient` |
| `/pages/organizations` | Listagem de Organizações | `OrganizationsClient` |
| `/pages/mini-courses` | Minicursos | `MiniCoursesClient` |
| `/pages/login` | Login | `LoginClient` |
| `/pages/register` | Registo | `RegisterClient` |
| `/pages/support` | Suporte/Contacto | `SupportPage` |

---

## 🧩 Componentes Principais

### Estrutura Global
- `Header.tsx`: Cabeçalho integrado com Ágora Design System.
- `Footer.tsx`: Rodapé do portal.
- `PageBanner.tsx`: Banner superior das páginas.

### Datasets (`src/components/datasets/`)
- `DatasetsClient.tsx`: Container principal da listagem.
- `DatasetDetailClient.tsx`: Página de detalhe.
- `DatasetsFilters.tsx`: Filtros de pesquisa.
- `DatasetResourcesTable.tsx`: Tabela de recursos/ficheiros.

### Reuses (`src/components/reuses/`)
- `ReusesClient.tsx`: Listagem de reutilizações.
- `ReuseDetailClient.tsx`: Detalhe da reutilização.

### Outros
- `MiniCoursesClient.tsx`: Gestão de minicursos.
- `ArticleDetail.tsx`: Detalhe de notícias/artigos.

---

## 🛠️ Serviços (`src/services/`)
- Integração com a API udata (backend).

---

## 📝 Regras de Componentização
1. Novos componentes devem ser colocados em `src/components/[feature]/`.
2. Usar `'use client'` sempre que houver interação com hooks do React ou componentes do design system que o exijam.
3. Seguir o padrão de sufixo `Client` para componentes que gerem o estado completo de uma página (`FeatureClient.tsx`).
