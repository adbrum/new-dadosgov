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
            label="Pesquisar reutilizações"
            hideLabel={true}
            placeholder="Exemplo: Eleição presidencial de 2022"
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
        <div className="container mx-auto px-4 py-64">
          <div className="grid xs:grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3 gap-32">
            {reuses.map((reuse) => (
              <CardArticle
                key={reuse.id}
                image={{
                  src: reuse.image_thumbnail || reuse.image || '/laptop.png',
                  alt: reuse.title,
                }}
                subtitle={`Publicado a ${format(new Date(reuse.created_at), 'dd MM yyyy', { locale: pt })}`}
                title={reuse.title}
                mainAnchor={{
                  href: `/pages/reuses/${reuse.slug}`,
                  target: '_self',
                  title: 'Ver mais',
                  hasIcon: true,
                  iconOnly: true,
                  leadingIcon: 'agora-line-arrow-right-circle',
                  leadingIconHover: 'agora-solid-arrow-right-circle',
                  variant: 'primary',
                }}
                blockedLink={true}
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
