
'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button, InputSearchBar, Icon, CardGeneral, CardLinks, InputSelect, DropdownSection, DropdownOption, Pill, CardNoResults } from '@ama-pt/agora-design-system';
import { Pagination } from '@/components/Pagination';
import { DatasetsFilters } from '@/components/datasets/DatasetsFilters';
import { APIResponse, Dataset } from '@/types/api';
import { formatDistanceToNow } from 'date-fns';
import { pt } from 'date-fns/locale';

import PageBanner from '@/components/PageBanner';

interface DatasetsClientProps {
  initialData: APIResponse<Dataset>;
  currentPage: number;
}

export default function DatasetsClient({
  initialData,
  currentPage,
}: DatasetsClientProps) {
  const router = useRouter();
  const { data: datasets, total, page_size } = initialData;

  return (
    <div className="min-h-screen flex flex-col font-sans text-neutral-900 bg-neutral-50 filters dataset">
      <main className="flex-grow bg-primary-50">
        <PageBanner
          title="Conjunto de dados"
          backgroundImageUrl="/Banner/hero-bg.png"
          backgroundPosition="center right"
          //containerClassName="dataset"
          breadcrumbItems={[
            { label: 'Home', url: '/' },
            { label: 'Conjunto de dados', url: '/pages/datasets' }
          ]}
          subtitle={
            <p className="text-primary-100 max-w-3xl">
              Pesquise através de {total.toLocaleString('pt-PT')} conjuntos
              de dados em dados.gov
            </p>
          }
        >
          <InputSearchBar
            label="O que procura no Portal?"
            placeholder="Pesquisar datasets, organizações, temas..."
            id="datasets-search"
            hasVoiceActionButton={true}
            voiceActionAltText="Pesquisar por voz"
            searchActionAltText="Pesquisar"
            darkMode={true}
          />
          <div className="mt-8 text-s-regular text-neutral-200">
            Exemplos: &quot;educação&quot;, &quot;saúde pública&quot;, &quot;ambiente&quot;
          </div>
          <div className="mt-[32px]">
            <Button
              variant="primary"
              darkMode={true}
              hasIcon={false}
              className="px-24 py-16 rounded-8 h-auto"
            >
              <span className="text-lg font-medium">
                Publicar <span className="font-bold">dados.gov</span>
              </span>
            </Button>
          </div>
          <div className="absolute w-full mb-64 bg-white text-neutral-900 shadow-lg dropdown"></div>
        </PageBanner>

        {/* Main Content */}
        {/* Main Content - Full Width Layout */}
        {/* Main Content - Full Width Layout Wrapper */}
        {/* Main Content */}
        <div className="container mx-auto md:gap-32 xl:gap-64 bg-white">
          <div className="grid md:grid-cols-3 xl:grid-cols-12 grid-filters">
            {/* Sidebar */}
            <div className="xl:col-span-4 xl:block bg-primary-100 p-32 pl-0">
              <DatasetsFilters />
            </div>

            {/* Results Area */}
            <div className="xl:col-span-8 mt-[36px]">
              <div>
                <div className="grid md:grid-cols-2 xl:grid-cols-12 gap-32 mb-16 items-center mt-[12px]">
                  <span className="text-neutral-900 font-medium text-base xl:col-span-6 mt-[32px]">
                    {total.toLocaleString('pt-PT')} resultados
                  </span>
                  <div className="w-full md:w-auto xl:col-span-6 ">
                    <InputSelect
                      label="Ordenar por :"
                      id="sort-datasets"
                      defaultValue="reutilizacoes"
                      className="selectDataset"
                    >
                      <DropdownSection name="order">
                        <DropdownOption value="reutilizacoes">Número de reutilizações</DropdownOption>
                        <DropdownOption value="recentes">Mais recentes</DropdownOption>
                        <DropdownOption value="visualizados">Mais visualizados</DropdownOption>
                      </DropdownSection>
                    </InputSelect>
                  </div>
                </div>
                <div className="divider-neutral-200 mt-[14px] mb-24" />
                <div className="grid grid-cols-1 md:grid-cols-2 agora-card-links-datasets">
                  {datasets.length > 0 ? (
                    datasets.map((dataset) => (
                      <div key={dataset.id} className="h-full">
                        <CardLinks
                          onClick={() => router.push(`/pages/datasets/${dataset.slug}`)}
                          className="cursor-pointer text-neutral-900"
                          variant="white"
                          image={{
                            src: dataset.organization?.logo || '/images/placeholders/organization.png',
                            alt: dataset.organization?.name || 'Organização sem logo',
                          }}
                          category={dataset.organization?.name}
                          title={dataset.title}
                          description={
                            <div className="flex flex-col gap-12">
                              <p className="text-sm line-clamp-3 leading-relaxed text-neutral-900 mt-[8px]">
                                {dataset.description}
                              </p>
                              <div className="flex flex-wrap gap-8 items-center mt-[8px]">
                                <span className="text-sm font-medium text-neutral-900">
                                  Metadados: 35%
                                </span>
                              </div>
                              <div className="flex items-center flex-wrap gap-[32px] text-xs mt-[32px] text-[#034AD8] mb-[32px]">
                                <div className="flex items-center gap-8" title="Visualizações">
                                  <Icon name="agora-line-eye" className="" aria-hidden="true" />
                                  <span>
                                    {dataset.metrics?.views
                                      ? dataset.metrics.views >= 1000000
                                        ? (dataset.metrics.views / 1000000).toFixed(1).replace('.', ',') + ' M'
                                        : dataset.metrics.views >= 1000
                                          ? (dataset.metrics.views / 1000).toFixed(0) + ' mil'
                                          : dataset.metrics.views
                                      : '0'}
                                  </span>
                                </div>
                                <div className="flex items-center gap-8" title="Downloads">
                                  <Icon name="agora-line-download" className="" aria-hidden="true" />
                                  <span>
                                    {dataset.metrics?.downloads
                                      ? dataset.metrics.downloads >= 1000
                                        ? (dataset.metrics.downloads / 1000).toFixed(0) + ' mil'
                                        : dataset.metrics.downloads
                                      : '0'}
                                  </span>
                                </div>
                                <div className="flex items-center gap-8" title="Reutilizações">
                                  <img src="/Icons/bar_chart.svg" className="" alt="" aria-hidden="true" />
                                  <span>{dataset.metrics?.reuses || 0}</span>
                                </div>
                                <div className="flex items-center gap-8" title="Favoritos">
                                  <img src="/Icons/favorite.svg" className="" alt="" aria-hidden="true" />
                                  <span>
                                    {dataset.metrics?.followers
                                      ? dataset.metrics.followers >= 1000
                                        ? (dataset.metrics.followers / 1000).toFixed(0) + ' mil'
                                        : dataset.metrics.followers
                                      : '0'}
                                  </span>
                                </div>
                              </div>
                            </div>
                          }
                          date={<span className="font-[300]">{`Atualizado há ${formatDistanceToNow(new Date(dataset.last_modified), { locale: pt })}`}</span>}
                          mainLink={
                            <Link href={`/pages/datasets/${dataset.slug}`}>
                              <span className="underline">{dataset.title}</span>
                            </Link>
                          }
                          blockedLink={true}

                        />
                      </div>
                    ))
                  ) : (
                    <div className="col-span-2">
                      <CardNoResults
                        icon={<Icon name="agora-line-search" className="justify-center icon-xl" />}
                        title="Não encontrou o que procurava?"
                        className="font-bold"
                        subtitle={<span className="font-bold">Tente redefinir os filtros para ampliar sua busca.</span>}
                        description="Você também pode visualizar as solicitações atuais e enviar as suas próprias em nosso fórum dedicado à pesquisa de dados e ao acesso aberto."
                        position="center"
                        hasAnchor={false}
                        extraDescription={
                          <div className="mt-32">
                            <Button
                              variant="primary"
                              appearance="solid"
                              hasIcon={true}
                              trailingIcon="agora-line-arrow-right-circle"
                              trailingIconHover="agora-solid-arrow-right-circle"
                              className="h-auto mt-32"
                              onClick={() => router.push('/pages/datasets')}
                            >
                              Redefinir filtros
                            </Button>
                          </div>
                        }
                      />
                    </div>
                  )}
                </div>

                <div className="pt-64 flex justify-center pb-64 pagination-filters">
                  <Pagination
                    currentPage={currentPage}
                    totalItems={total}
                    pageSize={page_size}
                  />
                </div>
              </div>
            </div>
          </div>


        </div>

      </main >
    </div >
  );


}
