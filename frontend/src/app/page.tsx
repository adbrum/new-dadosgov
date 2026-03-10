'use client';

import {
  Button,
  InputSearchBar,
  Icon,
  CardArticle,
  CardGeneral,
} from '@ama-pt/agora-design-system';
import Link from 'next/link';

export default function Home() {
  return (
    <main className="flex-grow">
      <div className="w-full homepage">
        {/* Hero Section */}
        <div
          className="agora-card-highlight-newsletter"
          style={{
            backgroundImage: 'url("/Banner/hero-bg.png")',
            backgroundRepeat: 'no-repeat',
            backgroundSize: 'cover',
            backgroundPosition: 'center right',
          }}
        >
          <div className="card-container">
            <div className="card-content">
              <div className="title">
                <h1 className="container mx-auto text-white flex flex-col items-start leading-tight">
                  <span className="xs:text-xl-bold md:text-2xl-bold xl:text-2xl-bold">
                    Plataforma aberta
                  </span>
                  <span className="xs:text-xl-light md:text-2xl-light xl:text-2xl-light">
                    de dados públicos portugueses
                  </span>
                </h1>
              </div>
              <div className="subtitle">
                <div className="container mx-auto text-left max-w-ch">
                  Aceda, explore e reutilize dados públicos de forma transparente e acessível. Milhares de
                  <br />
                  conjuntos de dados ao seu dispor.
                </div>
              </div>
            </div>
            <div className="input-container">
              <div className="email-bar">
                <div className="container mx-auto grid xs:grid-cols-4 md:grid-cols-8 xl:grid-cols-12 gap-32 ">
                  <div className="xs:col-span-4 md:col-span-7 xl:col-span-7">
                    <InputSearchBar
                      label="O que procura no Portal?"
                      placeholder="Pesquisar datasets, organizações, temas..."
                      id="portal-search"
                      hasVoiceActionButton={true}
                      voiceActionAltText="Pesquisar por voz"
                      searchActionAltText="Pesquisar"
                      darkMode={true}
                    />
                    <div className="mt-8 text-s-regular text-neutral-200">
                      Exemplos: &quot;educação&quot;, &quot;saúde pública&quot;, &quot;ambiente&quot;
                    </div>
                    <div className="mt-64">
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
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>


        {/* Stats Section / Communities */}
        <div className="py-64 bg-primary-900 text-white -mt-8 relative z-20 rounded-t-3xl shadow-top-low md:mt-0 md:border-none md:shadow-none">
          <div className="container mx-auto px-4">
            <div className="grid xs:grid-cols-1 xl:grid-cols-12 gap-64 items-center">
              {/* Left: title + description */}
              <div className="xl:col-span-5 flex flex-col gap-24">
                <h2 className="text-white">
                  <span className="text-l-bold">Uma comunidade</span>
                  <br></br>
                  <span className="xs:text-xl-light md:text-2xl-light xl:text-2xl-light whitespace-nowrap">Dinâmica e empenhada</span>
                </h2>
                <p className="text-m-regular max-w-sm">
                  Partilhe a utilização e a troca de dados entre produtores e
                  reutilizadores de dados.
                </p>
              </div>

              {/* Right: 2x2 stats grid */}
              <div className="xl:col-span-7 grid xs:grid-cols-1 sm:grid-cols-2 gap-x-64 gap-y-48">
                <div className="grid md:grid-cols-3 xl:grid-cols-12 gap-32">
                  <div className="xl:col-span-6 flex flex-col gap-48">
                    {/* Item 1 */}
                    <div className="flex items-center gap-24">
                      <div className="stats-icon-wrapper text-[#A6D5FF] border-[#A6D5FF]">
                        <Icon name="agora-line-layers-menu" aria-hidden="true" className="w-[24px] h-[24px]" />
                      </div>
                      <div className="flex flex-col">
                        <div className="flex items-baseline gap-8">
                          <span className="text-2xl-semibold">47 825</span>
                          <span className="text-l-bold ">mil</span>
                        </div>
                        <span>Conjuntos de Dados</span>
                      </div>
                    </div>

                    {/* Item 3 */}
                    <div className="flex items-center gap-24">
                      <div className="stats-icon-wrapper text-[#D600FF] border-[#D600FF]">
                        <svg width="15" height="24" viewBox="0 0 15 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-[15px] h-[24px]">
                          <path d="M0 22.9091V15.2727C0 14.6702 0.479695 14.1818 1.07143 14.1818C1.66316 14.1818 2.14286 14.6702 2.14286 15.2727V22.9091C2.14286 23.5116 1.66316 24 1.07143 24C0.479695 24 0 23.5116 0 22.9091ZM6.42857 22.9091V1.09091C6.42857 0.488417 6.90827 0 7.5 0C8.09173 0 8.57143 0.488417 8.57143 1.09091V22.9091C8.57143 23.5116 8.09173 24 7.5 24C6.90827 24 6.42857 23.5116 6.42857 22.9091ZM12.8571 22.9091V9.81818C12.8571 9.21569 13.3368 8.72727 13.9286 8.72727C14.5203 8.72727 15 9.21569 15 9.81818V22.9091C15 23.5116 14.5203 24 13.9286 24C13.3368 24 12.8571 23.5116 12.8571 22.9091Z" fill="currentColor" />
                        </svg>
                      </div>
                      <div className="flex flex-col">
                        <div className="flex items-baseline gap-8">
                          <span className="text-2xl-semibold">8 234</span>
                          <span className="text-l-bold ">mil</span>
                        </div>
                        <span>Reutilizações</span>
                      </div>
                    </div>
                  </div>
                  <div className="xl:col-span-6 flex flex-col gap-48">
                    {/* Item 2 */}
                    <div className="flex items-center gap-24">
                      <div className="stats-icon-wrapper text-[#CBFF3F] border-[#CBFF3F]">
                        <Icon name="agora-line-document" aria-hidden="true" className="w-[24px] h-[24px]" />
                      </div>
                      <div className="flex flex-col">
                        <div className="flex items-baseline gap-8">
                          <span className="text-2xl-semibold">2 456</span>
                          <span className="text-l-bold ">mil</span>
                        </div>
                        <span>Organizações</span>
                      </div>
                    </div>

                    {/* Item 4 */}
                    <div className="flex items-center gap-24">
                      <div className="stats-icon-wrapper text-[#FFD700] border-[#FFD700]">
                        <Icon name="agora-line-user-group" aria-hidden="true" className="w-[24px] h-[24px]" />
                      </div>
                      <div className="flex flex-col">
                        <div className="flex items-baseline gap-8">
                          <span className="text-2xl-semibold">+152</span>
                          <span className="text-l-bold">milhões</span>
                        </div>
                        <span>Utilizadores</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        {/* Featured Datasets */}
        <div className="xl:pt-64 bg-white">
          <div className="container mx-auto px-4">
            <h2 className="text-xl-bold mb-32 text-primary-900 ">
              Conjunto de dados
            </h2>

            <div className="grid xs:grid-cols-1 sm:grid-cols-2 md:grid-cols-2 xl:grid-cols-3 gap-32">
              {[
                {
                  time: 'Hoje',
                  org: 'Agência Portuguesa do Ambiente',
                  title: 'Indicadores de Qualidade do Ar',
                  desc: 'Medições diárias da qualidade do ar em estações de monitorização em todo o país.',
                  views: '34 567',
                },
                {
                  time: '2 dias atrás',
                  org: 'Ministério da Saúde',
                  title: 'Base de Dados de Estabelecimentos de Saúde',
                  desc: 'Lista completa de todos os estabelecimentos de saúde em Portugal, incluindo hospitais, centros de saúde e clínicas.',
                  views: '45 678',
                },
                {
                  time: '3 dias atrás',
                  org: 'Instituto Nacional de Estatística',
                  title: 'Dados Demográficos Municipais',
                  desc: 'População, densidade, faixas etárias e indicadores demográficos por município.',
                  views: '52 341',
                },
              ].map((item, i) => (
                <div key={i} className="dataset-card-home border-2 border-[#1A65FA] rounded-[4px] overflow-hidden h-full flex flex-col">
                  <CardGeneral
                    variant="white"
                    pillText={item.time}
                    subtitleText={item.org}
                    titleText={item.title}
                    descriptionText={
                      (
                        <div className="flex flex-col grow">
                          <div className="flex items-center text-neutral-900 mb-8">
                            <Icon
                              name="agora-solid-bullet"
                              className="w-8 h-8 text-primary-600"
                              aria-hidden="true"
                            />
                            <span>{item.views} visualizações</span>
                          </div>
                          <span className="text-m-regular text-neutral-800 dataset-content-proper mb-16">
                            {item.desc}
                          </span>
                          <div className="flex items-center gap-8 text-primary-600 mt-auto">
                            <Icon
                              name="agora-line-arrow-right-circle"
                              className="w-32 h-32"
                              aria-hidden="true"
                            />
                          </div>
                        </div>
                      ) as unknown as string
                    }
                    isBlockedLink={true}
                    anchor={{ href: '#' }}
                  />
                </div>
              ))}
            </div>
            <div className="mt-32">
              <Link href="/pages/datasets">
                <Button
                  variant="primary"
                  appearance="link"
                  hasIcon={true}
                  trailingIcon="agora-line-arrow-right-circle"
                  trailingIconHover="agora-solid-arrow-right-circle"
                  className="p-0! h-auto"
                >
                  <span>Ver todos os conjuntos de dados</span>
                </Button>
              </Link>
            </div>
          </div>
        </div>

        {/* Utilizado diariamente por */}
        <div className="xl:pb-64 bg-white">
          <div className="container mx-auto px-4">
            <h2 className="mb-48 text-gray-medium mt-32 text-m-bold">
              Utilizado diariamente por:
            </h2>
            <div className="flex flex-wrap items-center justify-between gap-x-32 gap-y-32">
              {['arte.svg', 'ADC.svg', 'IMPIC.svg', 'DSPA.svg', 'apa.svg'].map(
                (logo, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-center"
                  >
                    <img
                      src={`/Logos/${logo}`}
                      alt={`Logo ${logo.replace('.svg', '')}`}
                      className="h-12 md:h-14 xl:h-16 w-auto object-contain"
                    />
                  </div>
                )
              )}
            </div>
          </div>
        </div>

        {/* Reuses */}
        <div className="xl:py-64 bg-primary-900">
          <div className="container mx-auto px-4">
            <h2 className="text-xl-bold text-white">
              Storytelling
            </h2>
            <p className="mt-16 mb-32 max-w-3xl text-white">
              Precisa de uma descrição uma vez que é um titulo estrangeiro e novidade no dados.gov
            </p>
            <div className="grid xs:grid-cols-1 sm:grid-cols-2 md:grid-cols-2 xl:grid-cols-3 gap-32">
              {[
                {
                  img: 'Storytellings/storytelling1.svg',
                  title: 'Gestão de resíduos contentores e ecopontos',
                  subtitle: 'Publicado a DD MM AAAA',
                },
                {
                  img: 'Storytellings/storytelling2.svg',
                  title:
                    'Sistema de Monitorização do Ordenamento do Território (SMOT)',
                  subtitle: 'Publicado a DD MM AAAA',
                },
                {
                  img: 'Storytellings/storytelling3.svg',
                  title:
                    'Emissões GEE por setor (Portugal) — visualização + API (P7CO®)',
                  subtitle: 'Publicado a DD MM AAAA',
                },
              ].map((story, i) => (
                <CardArticle
                  key={i}
                  variant="indented"
                  image={{
                    src: `/${story.img}`,
                    alt: story.title,
                  }}
                  subtitle={story.subtitle}
                  title={story.title}
                  mainAnchor={{

                  }}
                  blockedLink={true}
                />
              ))}
            </div>
            <div className="mt-32">
              <Link href="#">
                <Button
                  variant="primary"
                  appearance="link"
                  hasIcon={true}
                  trailingIcon="agora-line-arrow-right-circle"
                  trailingIconHover="agora-solid-arrow-right-circle"
                  className="p-0! h-auto icon-white"
                  darkMode={false}
                >
                  <span className="text-white">Ver todas as Data Stories</span>
                </Button>
              </Link>
            </div>
          </div>
        </div>

        {/* Latest News */}
        <div className="xl:py-64 bg-white latest-news-section">
          <div className="container mx-auto px-4">
            <h2 className="text-xl-bold mb-32 text-primary-900">
              Últimas novidades
            </h2>
            <div className="grid xs:grid-cols-1 sm:grid-cols-2 md:grid-cols-2 xl:grid-cols-3 gap-32">
              {[
                {
                  img: 'Articles/last-new1.svg',
                  title: 'Webinar Developers e Data Scientists: Publicação e uso de dados abertos',
                  slug: 'webinar-developers-data-scientists',
                },
                {
                  img: 'Articles/last-new2.svg',
                  title: 'NOVA DATA - Webinar Dados Abertos: Importância para as empresas',
                  slug: 'nova-data-webinar-empresas',
                },
                {
                  img: 'Articles/last-new3.svg',
                  title: 'Webinar Developers e Data Scientists: Publicação e uso de dados abertos',
                  slug: 'workshop-visualizacao-dados',
                },
              ].map((news, i) => (
                <div key={i} className="latest-news-card-wrapper h-full">
                  <CardArticle
                    image={{
                      src: `/${news.img}`,
                      alt: news.title,
                    }}
                    subtitle="Publicado em 21 de novembro de 2024"
                    title={news.title}
                    blockedLink={false}
                  >
                    <div className="mt-auto pt-16">
                      <Link href={`/pages/article/${news.slug}`}>
                        <Button
                          variant="primary"
                          appearance="link"
                          hasIcon={true}
                          trailingIcon="agora-line-arrow-right-circle"
                          trailingIconHover="agora-solid-arrow-right-circle"
                          className="p-0! h-auto"
                        >
                          <span>Saber mais</span>
                        </Button>
                      </Link>
                    </div>
                  </CardArticle>
                </div>
              ))}
            </div>
            <div className="mt-32">
              <Link href="/pages/article">
                <Button
                  variant="primary"
                  appearance="link"
                  hasIcon={true}
                  trailingIcon="agora-line-arrow-right-circle"
                  trailingIconHover="agora-solid-arrow-right-circle"
                  className="p-0! h-auto"
                >
                  <span>Ver todas as novidades</span>
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>
    </main >
  );
}
