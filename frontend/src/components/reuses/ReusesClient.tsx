'use client';

import React from 'react';
import { CardArticle, Button, InputSearchBar } from '@ama-pt/agora-design-system';
import { Pagination } from '@/components/Pagination';
import { APIResponse, Reuse } from '@/types/api';
import { format } from 'date-fns';
import { pt } from 'date-fns/locale';

import PageBanner from '@/components/PageBanner';

interface ReusesClientProps {
  initialData: APIResponse<Reuse>;
  currentPage: number;
}

export default function ReusesClient({
  initialData,
  currentPage,
}: ReusesClientProps) {
  const { data: reuses, total, page_size } = initialData;

  return (
    <div className="min-h-screen flex flex-col font-sans text-neutral-900 bg-neutral-50">
      <main className="flex-grow bg-white">
        <PageBanner
          title="Reutilizações"
          breadcrumbItems={[
            { label: 'Home', url: '/' },
            { label: 'Reutilizações', url: '/pages/reuses' }
          ]}
          subtitle={
            <p className="text-primary-100 mb-8 max-w-ch">
              Descubra como os dados abertos estão a ser utilizados para criar valor.
              Existem {total.toLocaleString('pt-PT')} reutilizações publicadas.
            </p>
          }
        >
          <InputSearchBar
            label="O que procura nas reutilizações?"
            placeholder="Pesquisar datasets, organizações, temas..."
            id="reuses-search"
            hasVoiceActionButton={true}
            voiceActionAltText="Pesquisar por voz"
            searchActionAltText="Pesquisar"
            darkMode={true}
          />
          <div className="mt-64">
            <Button
              variant="primary"
              hasIcon={false}
              className="!bg-[#7BB2FF] !text-[#002D72] px-24 py-16 rounded-8 h-auto [&_svg]:!fill-black"
            >
              <span className="text-lg font-medium">
                Publicar <span className="font-bold">dados gov</span>
              </span>
            </Button>
          </div>
        </PageBanner>

        {/* Main Content - Grid of Reuses */}
        <div className="container mx-auto md:gap-32 xl:gap-64">
          <div className="pt-32 pb-64">
            <div className="grid md:grid-cols-2 xl:grid-cols-12 gap-32 mb-16 items-center mt-[12px]">
              <span className="text-neutral-900 font-medium text-base xl:col-span-7 mt-[32px]">
                {total.toLocaleString('pt-PT')} Resultados
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
                <div className="flex-grow max-w-[240px]">
                  <InputSelect
                    label="Ordenar por :"
                    id="sort-reuses"
                    defaultValue="reutilizacoes"
                    className="selectReuse"
                  >
                    <DropdownSection name="order">
                      <DropdownOption value="reutilizacoes">Número de reutilizações</DropdownOption>
                      <DropdownOption value="recentes">Mais recentes</DropdownOption>
                      <DropdownOption value="visualizados">Mais visualizados</DropdownOption>
                    </DropdownSection>
                  </InputSelect>
                </div>
              </div>
            </div>

            <div className="divider-neutral-200 mt-[14px] mb-24" />

            <div className="grid grid-cols-2 agora-card-links-datasets-px0 gap-32">
              {reuses.length > 0 ? (
                reuses.map((reuse) => (
                  <div key={reuse.id} className="h-full">
                    <CardLinks
                      onClick={() => router.push(`/pages/reuses/${reuse.slug}`)}
                      className="cursor-pointer text-neutral-900"
                      variant="transparent"
                      image={{
                        src: reuse.image_thumbnail || reuse.image || '/laptop.png',
                        alt: reuse.title,
                      }}
                      category={reuse.organization?.name || 'Reutilização'}
                      title={<div className="underline text-xl-bold">{reuse.title}</div>}
                      description={
                        reuse.description ? (
                          <p className="text-sm line-clamp-3 leading-relaxed text-neutral-900 mt-[8px] max-w-[592px]">
                            {reuse.description}
                          </p>
                        ) : undefined
                      }
                      date={
                        <span className="font-[300]">
                          Atualizado {format(new Date(reuse.last_modified || reuse.created_at), 'dd MM yyyy', { locale: pt })}
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
                          children: reuse.metrics?.views?.toLocaleString('pt-PT') || '0',
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
                          children: `${reuse.datasets?.length || 0} mil`,
                          title: 'Datasets',
                          onClick: (e: React.MouseEvent) => e.preventDefault(),
                          className: 'text-[#034AD8]',
                        },
                        {
                          href: '#',
                          hasIcon: false,
                          children: (
                            <span className="flex items-center gap-8">
                              <img src="/Icons/bar_chart.svg" alt="" aria-hidden="true" />
                              <span>{reuse.metrics?.reuses || 0}</span>
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
                          children: reuse.metrics?.followers || 0,
                          title: 'Favoritos',
                          onClick: (e: React.MouseEvent) => e.preventDefault(),
                          className: 'text-[#034AD8]',
                        },
                      ]}
                      mainLink={
                        <Link href={`/pages/reuses/${reuse.slug}`}>
                          <span className="underline">{reuse.title}</span>
                        </Link>
                      }
                      blockedLink={true}
                    />
                  </div>
                ))
              ) : (
                <div className="col-span-2">
                  <CardNoResults
                    icon={<Icon name="agora-line-search" className="w-12 h-12 text-primary-500" />}
                    title="Não encontrou nenhuma reutilização?"
                    subtitle={<span className="font-bold">Tente redefinir os filtros para ampliar sua busca.</span>}
                    description="Explore a nossa lista completa de reutilizações de dados abertos."
                    position="center"
                    hasAnchor={true}
                    valueAnchor="Redefinir filtros"
                    anchorHref="/pages/reuses"
                    anchorTrailingIcon="agora-line-arrow-right-circle"
                    anchorTrailingIconHover="agora-solid-arrow-right-circle"
                  />
                </div>
              )}
            </div>

            {/* Pagination */}
            <div className="mt-64 flex justify-center pb-12">
              <Pagination
                currentPage={currentPage}
                totalItems={total}
                pageSize={page_size}
                baseUrl="/pages/reuses"
              />
            ))}
          </div>

          {/* Pagination */}
          <div className="mt-64 flex justify-center pb-12">
            <Pagination
              currentPage={currentPage}
              totalItems={total}
              pageSize={page_size}
              baseUrl="/pages/reuses"
            />
          </div>
        </div>
      </main>
    </div>
  );
}
