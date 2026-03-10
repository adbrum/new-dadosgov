'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { CardLinks, InputSearchBar, Button, InputSelect, DropdownSection, DropdownOption, Icon } from '@ama-pt/agora-design-system';
import PageBanner from '@/components/PageBanner';
import { Pagination } from '@/components/Pagination';

// Mock data for articles
const MOCK_ARTICLES = [
  {
    id: '1',
    slug: 'webinar-developers-data-scientists',
    title: 'Webinar Developers e Data Scientists: Publicação e uso de dados abertos',
    description: 'Participe no nosso próximo webinar focado em ferramentas e APIs para a comunidade técnica. Saiba como tirar o melhor partido dos dados abertos portugueses.',
    date: '21 de novembro de 2024',
    organization: 'Portal Dados Abertos',
    image: '/Articles/last-new1.svg',
    views: '1 234',
    comments: '12'
  },
  {
    id: '2',
    slug: 'nova-data-webinar-empresas',
    title: 'NOVA DATA - Webinar Dados Abertos: Importância para as empresas',
    description: 'Devido à elevada procura, agendámos uma nova data para o webinar sobre o impacto económico e social da abertura de dados no setor empresarial.',
    date: '15 de novembro de 2024',
    organization: 'Ministério da Economia',
    image: '/Articles/last-new2.svg',
    views: '856',
    comments: '5'
  },
  {
    id: '3',
    slug: 'workshop-visualizacao-dados',
    title: 'Workshop Prático: Visualização de Dados para o Cidadão',
    description: 'Aprenda a criar visualizações impactantes a partir de conjuntos de dados públicos utilizando ferramentas gratuitas e acessíveis.',
    date: '10 de novembro de 2024',
    organization: 'Laboratório de Inovação',
    image: '/Articles/last-new3.svg',
    views: '2 105',
    comments: '24'
  },
  {
    id: '4',
    slug: 'retrospectiva-temporada',
    title: 'Uma retrospectiva da temporada de volta às aulas do data.gouv.fr',
    description: '3 meses de eventos focados em dados públicos. Encontre todos os replays desde o início da nova temporada.',
    date: '18 de dezembro de 2025',
    organization: 'ADMIN',
    image: '/Banner/cubes.svg',
    views: '3 420',
    comments: '45'
  }
];

export default function ArticleClient({ currentPage }: { currentPage: number }) {
  const router = useRouter();

  return (
    <div className="min-h-screen flex flex-col font-sans text-neutral-900 bg-neutral-50 filters article">
      <main className="grow bg-primary-50">
        <PageBanner
          title="Últimas novidades"
          backgroundImageUrl="/Banner/hero-bg.png"
          backgroundPosition="center right"
          breadcrumbItems={[
            { label: 'Home', url: '/' },
            { label: 'Últimas novidades', url: '/pages/article' }
          ]}
        >
          <InputSearchBar
            label="O que procura nas novidades?"
            placeholder="Pesquisar artigos, notícias, webinars..."
            id="articles-search"
            hasVoiceActionButton={true}
            voiceActionAltText="Pesquisar por voz"
            searchActionAltText="Pesquisar"
            darkMode={true}
          />
          <div className="mt-8 text-s-regular text-neutral-200">
            Exemplos: &quot;webinar&quot;, &quot;estudos&quot;, &quot;eventos&quot;
          </div>
        </PageBanner>

        <div className="container mx-auto md:gap-32 xl:gap-64">
          <div className="pt-32 pb-64">
            <div className="grid md:grid-cols-2 xl:grid-cols-12 gap-32 mb-16 items-center mt-[12px]">
              <span className="text-neutral-900 font-medium text-base xl:col-span-7 mt-[32px]">
                {MOCK_ARTICLES.length} Resultados
              </span>
              <div className="w-full md:w-auto xl:col-span-5 flex items-end gap-16 justify-end">
                <Button
                  variant="primary"
                  appearance="link"
                  hasIcon={true}
                  trailingIcon="agora-line-settings"
                  trailingIconHover="agora-solid-settings"
                >
                  Filtrar
                </Button>
                <div className="grow max-w-[240px]">
                  <InputSelect
                    label="Ordenar por :"
                    id="sort-articles"
                    defaultValue="recentes"
                    className="selectArticle"
                  >
                    <DropdownSection name="order">
                      <DropdownOption value="recentes">Mais recentes</DropdownOption>
                      <DropdownOption value="antigos">Mais antigos</DropdownOption>
                      <DropdownOption value="visualizados">Mais visualizados</DropdownOption>
                    </DropdownSection>
                  </InputSelect>
                </div>
              </div>
            </div>

            <div className="divider-neutral-200 mt-[14px] mb-24" />

            <div className="grid grid-cols-2 agora-card-links-datasets-px0 gap-32">
              {MOCK_ARTICLES.map((article) => (
                <div key={article.id} className="h-full">
                  <CardLinks
                    onClick={() => router.push(`/pages/article/${article.slug}`)}
                    className="cursor-pointer text-neutral-900"
                    variant="transparent"
                    image={{
                      src: article.image || '/laptop.png',
                      alt: article.title,
                    }}
                    category={article.organization}
                    title={<div className="underline text-xl-bold">{article.title}</div>}
                    description={
                      <p className="text-sm line-clamp-3 leading-relaxed text-neutral-900 mt-[8px]">
                        {article.description}
                      </p>
                    }
                    date={
                      <span className="font-[300]">
                        {article.date}
                      </span>
                    }
                    links={[
                      {
                        href: '#',
                        hasIcon: true,
                        leadingIcon: 'agora-line-eye',
                        leadingIconHover: 'agora-solid-eye',
                        trailingIcon: '',
                        trailingIconHover: '',
                        trailingIconActive: '',
                        children: article.views,
                        title: 'Visualizações',
                        onClick: (e: React.MouseEvent) => e.preventDefault(),
                        className: 'text-[#034AD8]',
                      },
                      {
                        href: '#',
                        hasIcon: true,
                        leadingIcon: 'agora-line-calendar',
                        leadingIconHover: 'agora-solid-calendar',
                        trailingIcon: '',
                        trailingIconHover: '',
                        trailingIconActive: '',
                        children: '0 mil',
                        title: 'Data',
                        onClick: (e: React.MouseEvent) => e.preventDefault(),
                        className: 'text-[#034AD8]',
                      },
                      {
                        href: '#',
                        hasIcon: false,
                        children: (
                          <span className="flex items-center gap-8">
                            <img src="/Icons/bar_chart.svg" alt="" aria-hidden="true" />
                            <span>0</span>
                          </span>
                        ),
                        title: 'Métricas',
                        onClick: (e: React.MouseEvent) => e.preventDefault(),
                      },
                      {
                        href: '#',
                        hasIcon: true,
                        leadingIcon: 'agora-line-star',
                        leadingIconHover: 'agora-solid-star',
                        trailingIcon: '',
                        trailingIconHover: '',
                        trailingIconActive: '',
                        children: article.comments,
                        title: 'Favoritos',
                        onClick: (e: React.MouseEvent) => e.preventDefault(),
                        className: 'text-[#034AD8]',
                      },
                    ]}
                    mainLink={
                      <Link href={`/pages/article/${article.slug}`}>
                        <span className="underline">{article.title}</span>
                      </Link>
                    }
                    blockedLink={true}
                  />
                </div>
              ))}
            </div>

            <div className="pb-64 mt-8 flex justify-center">
              <Pagination
                currentPage={currentPage}
                totalItems={24} // Mock total for visual demonstration
                pageSize={12}
                baseUrl="/pages/article"
              />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
