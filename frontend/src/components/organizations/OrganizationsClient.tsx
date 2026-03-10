'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  Button,
  InputSearchBar,
  Icon,
  CardLinks,
  InputSelect,
  DropdownSection,
  DropdownOption,
  CardNoResults
} from '@ama-pt/agora-design-system';
import { Pagination } from '@/components/Pagination';
import { OrganizationsFilters } from './OrganizationsFilters';
import { APIResponse, Organization } from '@/types/api';

import PageBanner from '@/components/PageBanner';

interface OrganizationsClientProps {
  initialData: APIResponse<Organization>;
  currentPage: number;
}

export default function OrganizationsClient({
  initialData,
  currentPage,
}: OrganizationsClientProps) {
  const router = useRouter();
  const { data: organizations, total, page_size } = initialData;

  return (
    <div className="min-h-screen flex flex-col font-sans text-neutral-900 bg-neutral-50 filters organization">
      <main className="flex-grow bg-primary-50">
        <PageBanner
          title="Organizações"
          backgroundImageUrl="/Banner/hero-bg.png"
          backgroundPosition="center right"
          //containerClassName="dataset"
          breadcrumbItems={[
            { label: 'Home', url: '/' },
            { label: 'Organizações', url: '/pages/organizations' }
          ]}
        >
          <InputSearchBar
            label="O que procura nas organizações?"
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
          <div className="mt-[32px] text-white">
            <span>Conteúdo atualizados a 23.2.2026</span>
          </div>
          <div className="absolute w-full mb-64 bg-white text-neutral-900 shadow-lg dropdown"></div>
        </PageBanner>

        {/* Main Content */}
        <div className="container mx-auto md:gap-32 xl:gap-64 bg-white">
          <div className="grid md:grid-cols-3 xl:grid-cols-12 grid-filters">
            {/* Sidebar */}
            <div className="xl:col-span-4 xl:block p-32 pl-0">
              <OrganizationsFilters />
            </div>

            {/* Results Area */}
            <div className="xl:col-span-8 mt-[36px]">
              <div>
                <div className="grid md:grid-cols-2 xl:grid-cols-12 gap-32 mb-16 items-center mt-[12px]">
                  <span className="text-neutral-900 font-medium text-base xl:col-span-6 mt-[32px]">
                    {total.toLocaleString('pt-PT')} Resultados
                  </span>
                  <div className="w-full md:w-auto xl:col-span-6">
                    <InputSelect
                      label="Ordenar por:"
                      id="sort-organizations"
                      defaultValue="relevancia"
                      className="selectOrganization"
                    >
                      <DropdownSection name="order">
                        <DropdownOption value="relevancia">Por relevância</DropdownOption>
                        <DropdownOption value="alfabetica">Ordem alfabética</DropdownOption>
                        <DropdownOption value="recentes">Mais recentes</DropdownOption>
                      </DropdownSection>
                    </InputSelect>
                  </div>
                </div>

                <div className="divider-neutral-200 mt-[14px] mb-24" />

                <div className="grid grid-cols-1 md:grid-cols-2 agora-card-links-datasets-px0">
                  {organizations.length > 0 ? (
                    organizations.map((org) => (
                      <div key={org.id} className="h-full">
                        <CardLinks
                          onClick={() => router.push(`/pages/organizations/${org.slug}`)}
                          className="cursor-pointer text-neutral-900"
                          variant="transparent"
                          image={{
                            src: org.logo || '/images/placeholders/organization.png',
                            alt: org.name,
                          }}
                          category="Organização"
                          title={<div className="underline text-xl-bold">{org.name}</div>}
                          description={
                            org.description ? (
                              <p className="text-sm line-clamp-3 leading-relaxed text-neutral-900 mt-[8px] max-w-[592px]">
                                {org.description}
                              </p>
                            ) : undefined
                          }
                          date={<span className="font-[300]">Atualizado há 3 dias</span>}
                          links={[
                            {
                              href: '#',
                              hasIcon: true,
                              leadingIcon: 'agora-line-eye',
                              leadingIconHover: 'agora-solid-eye',
                              trailingIcon: '',
                              trailingIconHover: '',
                              trailingIconActive: '',
                              children: '2 M',
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
                              children: `${Math.floor(Math.random() * 1000)} mil`,
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
                                  <span>{Math.floor(Math.random() * 200)}</span>
                                </span>
                              ),
                              title: 'Reutilizações',
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
                              children: '412',
                              title: 'Favoritos',
                              onClick: (e: React.MouseEvent) => e.preventDefault(),
                              className: 'text-[#034AD8]',
                            },
                          ]}
                          mainLink={
                            <Link href={`/pages/organizations/${org.slug}`}>
                              <span className="underline">{org.name}</span>
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
                        title="Não encontrou nenhuma organização?"
                        subtitle={<span className="font-bold">Tente redefinir os filtros para ampliar sua busca.</span>}
                        description="Explore a nossa lista completa de publicadores de dados abertos."
                        position="center"
                        hasAnchor={true}
                        valueAnchor="Redefinir filtros"
                        anchorHref="/pages/organizations"
                        anchorTrailingIcon="agora-line-arrow-right-circle"
                        anchorTrailingIconHover="agora-solid-arrow-right-circle"
                      />
                    </div>
                  )}
                </div>

                <div className="pb-64 mt-8 flex justify-center">
                  <Pagination
                    currentPage={currentPage}
                    totalItems={total}
                    pageSize={page_size}
                    baseUrl="/pages/organizations"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
