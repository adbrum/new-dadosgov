'use client';

import React from 'react';
import Link from 'next/link';
import { Breadcrumb, Button, Icon, Tag, Pill, Tabs, Tab, TabHeader, TabBody, CardArticle, CardLinks } from '@ama-pt/agora-design-system';
import { Reuse, Dataset } from '@/types/api';
import { format } from 'date-fns';
import { pt } from 'date-fns/locale';

interface ReuseDetailClientProps {
  reuse: Reuse;
}

export default function ReuseDetailClient({ reuse }: ReuseDetailClientProps) {
  const formatDate = (dateString: string) => {
    try {
      return format(new Date(dateString), "d 'de' MMMM 'de' yyyy", { locale: pt });
    } catch (e) {
      return dateString;
    }
  };

  const renderTabBody = (content: React.ReactNode) => (
    <TabBody>
      <div className="relative">
        <div
          className="absolute inset-y-0 -mx-4 sm:-mx-8 md:-mx-16 lg:-mx-32 xl:-mx-64 bg-neutral-50 z-0"
          aria-hidden="true"
        />
        <div className="relative z-10 ">
          <div className="container mx-auto">
            {content}
          </div>
        </div>
      </div>
    </TabBody>
  );

  return (
    <div className="flex flex-col font-sans text-neutral-900 bg-white min-h-screen overflow-x-hidden">
      {/* Hero Section */}
      <section className="bg-white text-neutral-900 pt-24 pb-48 sm:pb-64">
        <div className="container mx-auto px-4 sm:px-16 md:px-32 lg:px-64">
          {/* Breadcrumbs & Actions */}
          <div className="mb-24">
            <div className="mb-24">
              <Breadcrumb
                darkMode={false}
                items={[
                  { label: 'Home', url: '/' },
                  { label: 'Reutilizações', url: '/pages/reuses' },
                  { label: reuse.title, url: `/pages/reuses/${reuse.slug || reuse.id}` }
                ]}
              />
            </div>
            <div className="flex justify-end">
              <div className="flex flex-wrap items-center gap-16">
                <Button
                  variant="primary"
                  appearance="outline"
                  darkMode={false}
                  hasIcon={true}
                  leadingIcon="agora-line-star"
                  leadingIconHover="agora-solid-star"
                >
                  Adicionar aos favoritos
                </Button>
                <Button
                  variant="primary"
                  hasIcon={true}
                  trailingIcon="agora-line-external-link"
                  trailingIconHover="agora-line-external-link"
                  onClick={() => window.open(reuse.url, '_blank')}
                  className=""
                >
                  Veja reutilização
                </Button>
              </div>
            </div>
          </div>

          {/* Hero Content */}
          <div className="grid md:grid-cols-3 xl:grid-cols-12 gap-32 mt-6 mb-24">
            {/* Image Column */}
            <div className="xl:col-span-8">
              <div className=" w-full">
                <img
                  src={reuse.image || '/laptop.png'}
                  alt={reuse.title}
                  className="w-full object-cover rounded-[4px]"
                />
              </div>
            </div>

            {/* Card Column */}
            <div className="xl:col-span-4 card-article-3_2">
              <CardArticle
                className="h-full bg-[#F2F6FF]! border-none shadow-none [&_.container-body]:p-32 [&_.container-body]:flex [&_.container-body]:flex-col [&_.container-body]:h-full"
                title={reuse.title}
                subtitle={
                  <div className="flex flex-col gap-24 mb-16">
                    {reuse.organization?.logo ? (
                      <div className="w-fit h-[48px] card-article-3_2-img py-8 rounded-8 border-2 border-primary-300 flex items-center justify-center">
                        <img
                          src={reuse.organization.logo}
                          alt={reuse.organization.name}
                          className=""
                        />
                      </div>
                    ) : (
                      <div className="w-[160px] h-[56px] bg-white rounded-8 border border-dashed border-neutral-300 flex items-center justify-center text-neutral-400 text-xs font-bold uppercase tracking-wider shadow-sm">
                        LOGOIPSUM
                      </div>
                    )}
                    <div className="text-sm font-medium underline cursor-pointer">
                      Tempo
                    </div>
                  </div>
                }
              >
                <div className="flex flex-col gap-24 h-full">
                  <div className="flex items-center flex-wrap gap-16 text-[15px]">
                    <span className="font-semibold text-neutral-900">{reuse.type || 'Aplicação'}</span>
                    <div className="flex items-center gap-8">
                      <Icon name="agora-line-eye" className="w-20 h-20 fill-[var(--color-neutral-900)]" />
                      <span className="text-neutral-900">{reuse.metrics?.views ? (reuse.metrics.views >= 1000 ? (reuse.metrics.views / 1000).toFixed(0) + ' mil' : reuse.metrics.views) : '0'}</span>
                    </div>
                    <div className="flex items-center gap-8">
                      <Icon name="agora-line-calendar" className="w-20 h-20 fill-[var(--color-neutral-900)]" />
                      <span className="text-neutral-900">217</span>
                    </div>
                  </div>

                  <div className="mt-auto pt-24">
                    <a
                      href={reuse.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[#034AD8] text-lg hover:underline inline-flex items-center gap-8"
                    >
                      Veja reutilização
                      <Icon name="agora-line-external-link" className="w-24 h-24 fill-[#034AD8]" />
                    </a>
                  </div>
                </div>
              </CardArticle>
            </div>
          </div>
        </div>
      </section>

      {/* Tabs Section */}
      <section className="bg-white sticky top-0 z-20">
        <div className="container mx-auto px-4 sm:px-16 md:px-32 lg:px-64 mb-24">
          <Tabs>
            <Tab>
              <TabHeader>Descrição</TabHeader>
              {renderTabBody(
                <div className="grid md:grid-cols-3 xl:grid-cols-12 gap-32 mt-6">
                  {/* Main Content */}
                  <div className="xl:col-span-8 max-w-ch">
                    <div className="prose prose-lg max-w-none text-neutral-700 leading-relaxed">
                      <h2 className="text-l-bold text-neutral-900 mb-32">Descrição</h2>
                      <div className="mb-32">
                        <p className="mb-16 text-neutral-900">
                          Geolocalização dos locais oficiais de exibição de material eleitoral (atualizada em 31 de agosto de 2015) e rotas otimizadas de exibição entre esses locais.
                        </p>
                        <p className="text-neutral-900 text-m-bold">
                          Exibições de roteiros otimizadas em termos de tempo, quilômetros e impacto ambiental reduzido.
                        </p>
                      </div>

                      {/* Featured image in content */}
                      <div className="my-32 rounded-lg overflow-hidden">
                        <img
                          src="/fingermaps.svg"
                          alt="Conteúdo da reutilização"
                          className="max-h-[364px] w-full h-auto object-cover"
                        />
                      </div>

                      <p className="mb-16 text-neutral-900">
                        2015 marca o início de um período de alta densidade eleitoral ( em média, 1 eleição a cada 8 meses até 2017 ).
                      </p>
                      <p className="mb-16 text-neutral-900">
                        <a href="https://panneaux-election.fr" target="_blank" rel="noopener noreferrer" className="font-bold underline decoration-1 underline-offset-4">
                          O site panneaux-election.fr
                        </a>
                        {" "}<span className="font-bold">destina-se a ativistas políticos e cidadãos responsáveis pela afixação de cartazes eleitorais para seus candidatos em locais oficiais.</span>
                      </p>
                      <p className="text-neutral-900">
                        Os cartazes eleitorais, uma operação logística essencial durante uma campanha política, representam um investimento significativo de tempo e recursos para os ativistas. Com o panneaux-election.fr , os ativistas economizam recursos e seu trabalho é simplificado ; eles podem, assim, se concentrar no que mais importa: seu engajamento e a defesa de suas ideias.
                      </p>

                      <div className="mt-16  space-y-24">
                        <div className="space-y-16">
                          <p className="text-neutral-900 font-bold">Ao entrar em <span className="underline decoration-1 underline-offset-4 font-bold">panneaux-election.fr</span>:</p>
                          <ul className="list-disc space-y-8 text-neutral-900 mt-16 pl-32 ">
                            <li>Os ativistas retornam ao seu cantão, e a rota otimizada que conecta os diferentes locais de exibição é utilizada.</li>
                            <li>Exporte a rota para um GPS ou imprima-a.</li>
                          </ul>
                        </div>

                        <p className="text-neutral-900 mt-32">
                          O benefício (tempo, km, pegada ecológica) é medido diretamente no site e o usuário pode ver o impacto instantaneamente.
                        </p>

                        <p className="text-neutral-900 mt-16 mb-32 font-bold">
                          A utilização também se estende aos serviços municipais, que também podem se beneficiar de deslocamentos económicos e com baixas emissões de CO2 para a instalação/desinstalação e manutenção dos painéis.
                        </p>

                        <div className="space-y-16">
                          <p className="text-neutral-900 mb-16">Panneaux-election.fr em números:</p>
                          <ul className="list-disc space-y-8 text-neutral-900 pl-32">
                            <li>91 departamentos mapeados</li>
                            <li>35.000 km economizados graças a rotas otimizadas.</li>
                            <li>700 horas poupadas para ativistas e serviços municipais.</li>
                            <li>192 chamadas telefônicas para coletar os dados</li>
                          </ul>
                        </div>

                        <p className="text-neutral-900 mt-32">
                          Desenvolvimento do Quorum Impact (aplicativo web e mobile para gestão de campanhas) e do Mapotempo (software web para mapeamento digital, planejamento e otimização de rotas).
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Sidebar Metadata */}
                  <aside className="xl:col-span-4 xl:block md:pt-64 flex flex-col gap-16">
                    <div className="bg-white p-32 rounded-4">
                      <h3 className="text-sm font-bold tracking-wider mb-8">Temático</h3>
                      <p className="font-medium text-neutral-900">Política e vida pública</p>
                    </div>

                    <div className="bg-white p-32 rounded-4">
                      <h3 className="text-sm font-bold tracking-wider mb-8">Tipo</h3>
                      <p className="font-medium text-neutral-900">Aplicação</p>
                    </div>

                    <div className="bg-white p-32 rounded-4">
                      <h3 className="text-sm font-bold tracking-wider mb-8">Tags</h3>
                      <p className="font-medium text-neutral-900 mb-16">Aplicação</p>
                      <div className="flex flex-col items-start gap-8">
                        {(reuse.tags || ['mapeamento', 'dataconnexions-6', 'eleição', 'noivado', 'demonstração de impacto', 'percorrer']).map(tag => (
                          <Pill key={tag} appearance="solid" variant="primary" className="bg-primary-100 text-primary-700 h-auto py-4 px-8 text-xs font-semibold">
                            {tag}
                          </Pill>
                        ))}
                      </div>
                    </div>

                    <div className="bg-white p-32 rounded-4">
                      <h3 className="text-sm font-bold tracking-wider mb-8">Última atualização</h3>
                      <p className="font-medium text-neutral-900">{formatDate(reuse.last_modified)}</p>

                    </div>

                    <div className="bg-white p-32 rounded-4">
                      <h3 className="text-sm font-bold tracking-wider mb-8">Data de criação</h3>
                      <p className="font-medium text-neutral-900">{formatDate(reuse.created_at)}</p>
                    </div>

                    <div className="bg-white p-32 rounded-4">
                      <h3 className="text-sm font-bold tracking-wider mb-8">Vistas</h3>
                      <div className="text-2xl font-bold text-neutral-900 mb-8">
                        {reuse.metrics?.views ? (reuse.metrics.views / 1000).toLocaleString('pt-PT') + ' mil' : '1,68 mil'}
                      </div>
                      <Pill variant="success" appearance="outline" className="mb-8 h-auto">+31,25mil em janeiro de 2026</Pill>
                      <div className="text-xs">desde julho de 2022</div>
                    </div>
                  </aside>
                </div>
              )}
            </Tab>
            <Tab>
              <TabHeader>Discussões (1)</TabHeader>
              {renderTabBody(
                <div className="text-neutral-500 italic">Nenhuma discussão iniciada ainda.</div>
              )}
            </Tab>
          </Tabs>
        </div>
      </section>

      <section className="bg-neutral-000 py-64">
        <div className="container mx-auto px-4 sm:px-16 md:px-32 lg:px-64">
          {/* Associated Datasets */}
          <div className="mb-80">
            <h2 className="text-xl font-bold text-[#000032] mb-32">
              5 conjuntos de dados associados
            </h2>
            <div className="grid md:grid-cols-3 xl:grid-cols-12 gap-32">
              <div className="xl:col-span-8 xl:col-start-5 grid grid-cols-1 md:grid-cols-2 agora-card-links-datasets gap-x-32 pt-0">
                {[
                  {
                    org: 'Agência Portuguesa do Ambiente',
                    logo: 'https://dados.gov.pt/s/avatars/ae/74fb78abd9473b91d317822952654d-original.png',
                    updated: 'Actualizado há 3 dias',
                    title: 'Qualidade da Água',
                    desc: 'Relatório sobre a qualidade da água em rios e lagos, com dados de vários pontos de monitorização.',
                    meta: 'Metadados 50%',
                    views: '2 M',
                    downloads: '150 mil',
                    chart: '180',
                    stars: '412',
                    slug: 'qualidade-da-agua'
                  },
                  {
                    org: 'Instituto de Conservação da Natureza',
                    logo: 'https://dados.gov.pt/s/avatars/fe/45fd7d612740428e8d8b8d0d91d68e-original.png',
                    updated: 'Actualizado há 1 mês',
                    title: 'Biodiversidade em Portugal',
                    desc: 'Dados sobre espécies em perigo e áreas protegidas no território nacional.',
                    meta: 'Metadados 55%',
                    views: '3.5 M',
                    downloads: '400 mil',
                    chart: '220',
                    stars: '350',
                    slug: 'biodiversidade-em-portugal'
                  },
                  {
                    org: 'Instituto Nacional de Estatística',
                    logo: 'https://dados.gov.pt/s/avatars/85/a712a01eb646c4aad73fb59a2b3987-original.jpg',
                    updated: 'Actualizado há 5 dias',
                    title: 'Censo Populacional',
                    desc: 'Dados detalhados sobre a população, incluindo idade, género e localização geográfica.',
                    meta: 'Metadados 40%',
                    views: '4 M',
                    downloads: '600 mil',
                    chart: '250',
                    stars: '512',
                    slug: 'censo-populacional'
                  },
                  {
                    org: 'Direção-Geral de Energia e Geologia',
                    logo: 'https://dados.gov.pt/s/avatars/6b/fd6834e24d429dbcfb003c837849f4-original.png',
                    updated: 'Actualizado há 2 semanas',
                    title: 'Análise do Setor Energético',
                    desc: 'Relato sobre a evolução do consumo e produção de energia em Portugal.',
                    meta: 'Metadados 60%',
                    views: '6 M',
                    downloads: '800 mil',
                    chart: '300',
                    stars: '250',
                    slug: 'analise-do-setor-energetico'
                  },
                  {
                    org: 'Banco de Portugal',
                    logo: 'https://dados.gov.pt/s/avatars/85/a712a01eb646c4aad73fb59a2b3987-original.jpg',
                    updated: 'Actualizado há 15 dias',
                    title: 'Relatório Económico Trimestral',
                    desc: 'Análise das principais variáveis económicas, incluindo PIB e inflação, com dados comparativos.',
                    meta: 'Metadados 30%',
                    views: '6 M',
                    downloads: '1 M',
                    chart: '350',
                    stars: '600',
                    slug: 'relatorio-economico-trimestral'
                  }
                ].map((dataset, i) => (
                  <div key={i} className="h-full">
                    <CardLinks
                      onClick={() => { }}
                      className="cursor-pointer text-neutral-900"
                      variant="white"
                      image={{
                        src: dataset.logo,
                        alt: `Logo - ${dataset.org}`,
                      }}
                      category={dataset.org}
                      title={dataset.title}
                      description={
                        <div className="flex flex-col gap-12">
                          <p className="text-sm line-clamp-3 leading-relaxed text-neutral-900 mt-[8px]">
                            {dataset.desc}
                          </p>
                          <div className="flex flex-wrap gap-8 items-center mt-[8px]">
                            <span className="text-sm font-medium text-neutral-900">
                              {dataset.meta}
                            </span>
                          </div>
                          <div className="flex items-center flex-wrap gap-[32px] text-xs mt-[32px] text-[#034AD8] mb-[32px]">
                            <div className="flex items-center gap-8" title="Visualizações">
                              <Icon name="agora-line-eye" className="" aria-hidden="true" />
                              <span>{dataset.views}</span>
                            </div>
                            <div className="flex items-center gap-8" title="Downloads">
                              <Icon name="agora-line-download" className="" aria-hidden="true" />
                              <span>{dataset.downloads}</span>
                            </div>
                            <div className="flex items-center gap-8" title="Reutilizações">
                              <img src="/Icons/bar_chart.svg" className="" alt="" aria-hidden="true" />
                              <span>{dataset.chart}</span>
                            </div>
                            <div className="flex items-center gap-8" title="Favoritos">
                              <img src="/Icons/favorite.svg" className="" alt="" aria-hidden="true" />
                              <span>{dataset.stars}</span>
                            </div>
                          </div>
                        </div>
                      }
                      date={<span className="font-[300]">{dataset.updated}</span>}
                      mainLink={
                        <Link href={`/pages/datasets/${dataset.slug}`}>
                          <span className="underline">{dataset.title}</span>
                        </Link>
                      }
                      blockedLink={true}
                    />
                  </div>
                ))}
              </div>
            </div>
          </div>


        </div>
      </section >
    </div >
  );
}
