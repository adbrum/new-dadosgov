'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { formatDistanceToNow } from 'date-fns';
import { pt } from 'date-fns/locale';
import { Button, Icon, Tag, Breadcrumb, Pill, ProgressBar } from '@ama-pt/agora-design-system';
import { Dataset } from '@/types/api';
import { DatasetTabs } from '@/components/datasets/DatasetTabs';

interface DatasetDetailClientProps {
  dataset: Dataset;
}

export default function DatasetDetailClient({ dataset }: DatasetDetailClientProps) {
  const [isFavorite, setIsFavorite] = useState(false);

  return (
    <div className="flex flex-col font-sans text-neutral-900 bg-white min-h-screen overflow-x-hidden">
      <main className="flex-grow container mx-auto px-4 pt-[64px]">
        {/* Breadcrumb & Action Section */}
        <div className="flex justify-between items-center mb-[24px]">
          <Breadcrumb
            items={[
              { label: 'Home', url: '/' },
              { label: 'Conjuntos de dados', url: '/pages/datasets' },
              { label: dataset.title, url: `/pages/datasets/${dataset.slug}` }
            ]}
          />
        </div>

        <div className="flex justify-end mb-[24px]">
          <Button
            variant="primary"
            appearance={isFavorite ? 'solid' : 'outline'}
            hasIcon={true}
            leadingIcon={isFavorite ? 'agora-solid-star' : 'agora-line-star'}
            leadingIconHover="agora-solid-star"
            className="flex-shrink-0"
            onClick={() => setIsFavorite(!isFavorite)}
          >
            {isFavorite ? 'Remover dos favoritos' : 'Adicionar aos favoritos'}
          </Button>
        </div>

        <div className="grid md:grid-cols-3 xl:grid-cols-12 gap-32 mb-[24px]">
          {/* Main Content Column */}
          <div className="xl:col-span-6 xl:block">
            {/* Title & Organization Header */}
            <div className="flex flex-col gap-4">
              <div className="flex justify-between items-start">
                <h1 className="text-xl-bold text-primary-900 leading-tight mb-24">
                  {dataset.title}
                </h1>
              </div>
            </div>

            {/* Description Section */}
            <div className="prose max-w-none text-neutral-700 text-lg leading-relaxed mb-12">
              <h2 className="text-xl font-bold text-neutral-900 mb-4 hidden">Descrição</h2>
              <p className="text-neutral-900 text-m-light mb-[24px]">{dataset.description}</p>

              {/* Example of extra content structure to match screenshot "Observações preliminares" */}
              <div className="mt-8">
                <h3 className="text-xl font-bold text-primary-900 mb-[16px]">Observações preliminares</h3>
                <p className="text-neutral-900 mb-[16px]">
                  Este relatório aborda as tendências demográficas e económicas do país, baseando-se em dados recolhidos ao longo do ano.
                </p>
              </div>

              {/* Example of extra content structure to match screenshot "O que é DVF?" */}
              <div className="mt-8">
                <h3 className="text-xl font-bold text-primary-900 mb-[16px]">O que é DVF?</h3>
                <p className="text-neutral-900 mb-[24px]">
                  Este conjunto de dados "Pedidos de Valores de Terrenos", publicado e produzido pela Direção Geral das Finanças Públicas, fornece informações sobre transações imobiliárias realizadas nos últimos cinco anos na França metropolitana e nos departamentos e territórios ultramarinos franceses, com exceção da Alsácia, Mosela e Mayotte. Os dados que contém provêm de escrituras notariais e informações cadastrais.
                </p>


                <div className="mt-auto flex justify-center">
                  <a href="#" className="flex items-center gap-8 text-primary-600 cursor-pointer hover:underline mb-[24px] mt-[24px]"> Leia mais
                    <svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" className="icon icon-m fill-[var(--color-primary-600)] w-32 h-32" aria-hidden="true" role="img"><path d="M11.2929 8.70711C10.9024 8.31658 10.9024 7.68342 11.2929 7.29289C11.6834 6.90237 12.3166 6.90237 12.7071 7.29289L16.7071 11.2929C17.0976 11.6834 17.0976 12.3166 16.7071 12.7071L12.7071 16.7071C12.3166 17.0976 11.6834 17.0976 11.2929 16.7071C10.9024 16.3166 10.9024 15.6834 11.2929 15.2929L13.5858 13H8C7.44772 13 7 12.5523 7 12C7 11.4477 7.44772 11 8 11H13.5858L11.2929 8.70711Z"></path><path fill-rule="evenodd" clip-rule="evenodd" d="M12 1C5.92487 1 1 5.92487 1 12C1 18.0751 5.92487 23 12 23C18.0751 23 23 18.0751 23 12C23 5.92487 18.0751 1 12 1ZM3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12Z"></path></svg>
                  </a>
                </div>
              </div>
            </div>
          </div>

          <div className="xl:col-span-6">
            <div className="flex flex-col h-fit">
              <div className="flex flex-col gap-16 bg-[#F2F6FF] rounded-4 p-32 mb-16">
                {dataset.organization?.logo ? (
                  <div className="w-fit h-[48px] card-article-3_2-img py-8 rounded-8 border-2 border-primary-300 flex items-center justify-center">
                    <img
                      src={dataset.organization.logo}
                      alt={dataset.organization.name}
                      className="max-h-full max-w-full object-contain"
                    />
                  </div>
                ) : (
                  <div className="w-fit px-12 py-6 bg-neutral-100 rounded-8 border border-neutral-200 flex items-center justify-center text-neutral-400">
                    <Icon name="agora-line-building" className="w-6 h-6" />
                  </div>
                )}

                {/* Main Information */}
                <div className="space-y-16">
                  <div className="text-neutral-900 text-m-light mb-[8px]">
                    {dataset.organization?.name || 'Organização Desconhecida'}
                  </div>
                  <div className="text-l-semibold text-neutral-900 leading-tight mb-[8px]">
                    {dataset.title}
                  </div>
                  <div className="text-neutral-900 text-sm mb-[16px]">
                    <span className="text-m-semibold">Última atualização:</span>{' '}
                    {new Date(dataset.last_modified).toLocaleDateString('pt-PT', {
                      day: 'numeric',
                      month: 'long',
                      year: 'numeric'
                    })}
                  </div>
                  <div className="pt-8">
                    <a href="#" className="text-primary-600 hover:underline font-medium text-sm">
                      Licença Aberta / Licença Aberta versão 2.0
                    </a>
                  </div>
                </div>
              </div>

              {/* Metrics Box */}
              <div className="grid grid-cols-2 gap-16 mb-16">
                <div className="bg-[#F2F6FF] rounded-4 p-32">
                  <div className="text-sm mb-[8px]">Vistas</div>
                  <div className="text-l-semibold font-bold text-neutral-900 mb-[8px]">
                    {dataset.metrics?.views
                      ? (dataset.metrics.views / 1000).toLocaleString('pt-PT', { maximumFractionDigits: 1 }) + ' mil'
                      : '0'}
                  </div>
                  <div className="flex items-center gap-1 mb-[8px]">
                    <Pill
                      appearance="outline"
                      variant="success"
                      className="h-auto"
                    >
                      +11.2 mil
                    </Pill>
                  </div>
                  <div className="text-xs text-neutral-900 mt-1">desde julho de 2022</div>
                </div>
                <div className="bg-[#F2F6FF] rounded-4 p-32">
                  <div className="text-sm mb-[8px]">Downloads</div>
                  <div className="text-l-semibold font-bold text-neutral-900 mb-[8px]">
                    {dataset.metrics?.downloads
                      ? (dataset.metrics.downloads / 1000).toLocaleString('pt-PT', { maximumFractionDigits: 1 }) + ' mil'
                      : '0'}
                  </div>
                  <div className="flex items-center gap-1 mb-[8px]">
                    <Pill
                      appearance="outline"
                      variant="success"
                      className="h-auto"
                    >
                      +37.2 mil
                    </Pill>
                  </div>
                  <div className="text-xs text-neutral-900 mt-1">desde julho de 2022</div>
                </div>
              </div>

              {/* Quality Box */}
              <div className="bg-[#F2F6FF] rounded-4 p-32 mb-16">
                <div className="flex justify-between items-end mb-4">
                  <h3 className="text-l-semibold font-bold text-neutral-900 mb-[8px]">Qualidade dos metadados</h3>
                </div>
                <ProgressBar
                  value={100}
                />
                <div className="text-xs text-neutral-500 mt-8">
                  100% (Descrição)
                </div>
                <div className="flex justify-start items-center text-sm text-primary-600 mt-[24px]">
                  <Icon name="agora-line-info-mark" className="w-24 h-24 cursor-pointer mr-[8px] fill-primary-600" />
                  <a href="#" className="hover:underline font-medium">Saiba mais sobre este indicador</a>
                </div>
              </div>

            </div>
          </div>
        </div>
        <div className="bg-primary-100 p-32 rounded-lg mb-[8px]">
          <h3 className="text-l-semibold font-bold text-neutral-900 mb-24">
            Está à procura do preço de venda de um imóvel ou terreno?
          </h3>
          <div className="flex flex-col gap-4">
            <p className="font-semibold mb-[16px]">
              O aplicativo "Dados de Valorização de Terrenos (DVF)" permite acessar informações claras sobre imóveis vendidos a partir do banco de dados da Direção Geral de Finanças Públicas.
            </p>
            <a href="#" className="text-xs text-primary-600 hover:underline inline-flex items-center gap-8 mr-4 max-w-[592px]">
              Consulte o aplicativo "Dados de Valor de Terreno (DVF)"
              <svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" className="icon icon-m fill-[var(--color-primary-600)] w-32 h-32" aria-hidden="true" role="img"><path d="M11.2929 8.70711C10.9024 8.31658 10.9024 7.68342 11.2929 7.29289C11.6834 6.90237 12.3166 6.90237 12.7071 7.29289L16.7071 11.2929C17.0976 11.6834 17.0976 12.3166 16.7071 12.7071L12.7071 16.7071C12.3166 17.0976 11.6834 17.0976 11.2929 16.7071C10.9024 16.3166 10.9024 15.6834 11.2929 15.2929L13.5858 13H8C7.44772 13 7 12.5523 7 12C7 11.4477 7.44772 11 8 11H13.5858L11.2929 8.70711Z"></path><path fill-rule="evenodd" clip-rule="evenodd" d="M12 1C5.92487 1 1 5.92487 1 12C1 18.0751 5.92487 23 12 23C18.0751 23 23 18.0751 23 12C23 5.92487 18.0751 1 12 1ZM3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12Z"></path></svg>
            </a>
          </div>
        </div>

        {/* Tabs Section at the very bottom of main content */}
        <DatasetTabs dataset={dataset} />
      </main>
    </div>
  );
}
