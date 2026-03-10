"use client";

import { useEffect, useState } from "react";
import {
  Button,
  Icon,
  CardArticle,
  CardGeneral,
} from "@ama-pt/agora-design-system";
import Link from "next/link";
import SearchDropdown from "@/components/search/SearchDropdown";
import {
  fetchLatestDatasets,
  fetchLatestReuses,
  fetchPosts,
  fetchSiteInfo,
} from "@/services/api";
import { Dataset, Post, Reuse, SiteInfo } from "@/types/api";
import { formatDistanceToNow, format } from "date-fns";
import { pt } from "date-fns/locale";

function formatStatNumber(value: number): { number: string; suffix: string } {
  if (value >= 1_000_000) {
    const formatted = (value / 1_000_000).toFixed(1).replace(".", ",");
    return { number: formatted, suffix: "milhões" };
  }
  if (value >= 1_000) {
    const formatted = new Intl.NumberFormat("pt-PT").format(value);
    return { number: formatted, suffix: "" };
  }
  return { number: String(value), suffix: "" };
}

export default function Home() {
  const [siteInfo, setSiteInfo] = useState<SiteInfo | null>(null);
  const [latestDatasets, setFeaturedDatasets] = useState<Dataset[]>([]);
  const [latestReuses, setFeaturedReuses] = useState<Reuse[]>([]);
  const [posts, setPosts] = useState<Post[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadHomepageData() {
      try {
        const [siteRes, datasetsRes, reusesRes, postsRes] = await Promise.all([
          fetchSiteInfo(),
          fetchLatestDatasets(3),
          fetchLatestReuses(3),
          fetchPosts(1, 3),
        ]);

        setSiteInfo(siteRes);
        setFeaturedDatasets(datasetsRes.data || []);
        setFeaturedReuses(reusesRes.data || []);
        setPosts(postsRes.data || []);
      } catch (error) {
        console.error("Failed to fetch homepage data:", error);
      } finally {
        setIsLoading(false);
      }
    }

    loadHomepageData();
  }, []);

  const stats = siteInfo?.metrics;

  return (
    <main className="flex-grow">
      <div className="w-full homepage">
        {/* Hero Section */}
        <div
          className="agora-card-highlight-newsletter"
          style={{
            backgroundImage: 'url("/Banner/hero-bg.png")',
            backgroundRepeat: "no-repeat",
            backgroundSize: "cover",
            backgroundPosition: "center right",
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
                  Aceda, explore e reutilize dados públicos de forma
                  transparente e acessível. Milhares de
                  <br />
                  conjuntos de dados ao seu dispor.
                </div>
              </div>
            </div>
            <div className="input-container">
              <div className="email-bar">
                <div className="container mx-auto grid xs:grid-cols-4 md:grid-cols-8 xl:grid-cols-12 gap-32 ">
                  <div className="xs:col-span-4 md:col-span-7 xl:col-span-7">
                    <SearchDropdown
                      id="portal-search"
                      darkMode={true}
                      hasVoiceActionButton={true}
                      label="O que procura no Portal?"
                      placeholder="Pesquisar datasets, organizações, temas..."
                    />
                    <div className="mt-8 text-s-regular text-neutral-200">
                      Exemplos: &quot;educação&quot;, &quot;saúde
                      pública&quot;, &quot;ambiente&quot;
                    </div>
                    <div className="mt-64">
                      <Button
                        variant="primary"
                        darkMode={true}
                        hasIcon={false}
                        className="px-24 py-16 rounded-8 h-auto"
                      >
                        <span className="text-lg font-medium">
                          Publicar{" "}
                          <span className="font-bold">dados.gov</span>
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
                  <br />
                  <span className="xs:text-xl-light md:text-2xl-light xl:text-2xl-light whitespace-nowrap">
                    Dinâmica e empenhada
                  </span>
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
                    {/* Conjuntos de Dados */}
                    <div className="flex items-center gap-24">
                      <div className="stats-icon-wrapper text-[#A6D5FF] border-[#A6D5FF]">
                        <Icon
                          name="agora-line-layers-menu"
                          aria-hidden="true"
                          className="w-[24px] h-[24px]"
                        />
                      </div>
                      <div className="flex flex-col">
                        <div className="flex items-baseline gap-8">
                          {isLoading ? (
                            <span className="text-2xl-semibold">...</span>
                          ) : (
                            <>
                              <span className="text-2xl-semibold">
                                {formatStatNumber(stats?.datasets ?? 0).number}
                              </span>
                              {formatStatNumber(stats?.datasets ?? 0).suffix && (
                                <span className="text-l-bold">
                                  {formatStatNumber(stats?.datasets ?? 0).suffix}
                                </span>
                              )}
                            </>
                          )}
                        </div>
                        <span>Conjuntos de Dados</span>
                      </div>
                    </div>

                    {/* Reutilizações */}
                    <div className="flex items-center gap-24">
                      <div className="stats-icon-wrapper text-[#D600FF] border-[#D600FF]">
                        <svg
                          width="15"
                          height="24"
                          viewBox="0 0 15 24"
                          fill="none"
                          xmlns="http://www.w3.org/2000/svg"
                          className="w-[15px] h-[24px]"
                        >
                          <path
                            d="M0 22.9091V15.2727C0 14.6702 0.479695 14.1818 1.07143 14.1818C1.66316 14.1818 2.14286 14.6702 2.14286 15.2727V22.9091C2.14286 23.5116 1.66316 24 1.07143 24C0.479695 24 0 23.5116 0 22.9091ZM6.42857 22.9091V1.09091C6.42857 0.488417 6.90827 0 7.5 0C8.09173 0 8.57143 0.488417 8.57143 1.09091V22.9091C8.57143 23.5116 8.09173 24 7.5 24C6.90827 24 6.42857 23.5116 6.42857 22.9091ZM12.8571 22.9091V9.81818C12.8571 9.21569 13.3368 8.72727 13.9286 8.72727C14.5203 8.72727 15 9.21569 15 9.81818V22.9091C15 23.5116 14.5203 24 13.9286 24C13.3368 24 12.8571 23.5116 12.8571 22.9091Z"
                            fill="currentColor"
                          />
                        </svg>
                      </div>
                      <div className="flex flex-col">
                        <div className="flex items-baseline gap-8">
                          {isLoading ? (
                            <span className="text-2xl-semibold">...</span>
                          ) : (
                            <>
                              <span className="text-2xl-semibold">
                                {formatStatNumber(stats?.reuses ?? 0).number}
                              </span>
                              {formatStatNumber(stats?.reuses ?? 0).suffix && (
                                <span className="text-l-bold">
                                  {formatStatNumber(stats?.reuses ?? 0).suffix}
                                </span>
                              )}
                            </>
                          )}
                        </div>
                        <span>Reutilizações</span>
                      </div>
                    </div>
                  </div>
                  <div className="xl:col-span-6 flex flex-col gap-48">
                    {/* Organizações */}
                    <div className="flex items-center gap-24">
                      <div className="stats-icon-wrapper text-[#CBFF3F] border-[#CBFF3F]">
                        <Icon
                          name="agora-line-document"
                          aria-hidden="true"
                          className="w-[24px] h-[24px]"
                        />
                      </div>
                      <div className="flex flex-col">
                        <div className="flex items-baseline gap-8">
                          {isLoading ? (
                            <span className="text-2xl-semibold">...</span>
                          ) : (
                            <>
                              <span className="text-2xl-semibold">
                                {formatStatNumber(stats?.organizations ?? 0).number}
                              </span>
                              {formatStatNumber(stats?.organizations ?? 0).suffix && (
                                <span className="text-l-bold">
                                  {formatStatNumber(stats?.organizations ?? 0).suffix}
                                </span>
                              )}
                            </>
                          )}
                        </div>
                        <span>Organizações</span>
                      </div>
                    </div>

                    {/* Utilizadores */}
                    <div className="flex items-center gap-24">
                      <div className="stats-icon-wrapper text-[#FFD700] border-[#FFD700]">
                        <Icon
                          name="agora-line-user-group"
                          aria-hidden="true"
                          className="w-[24px] h-[24px]"
                        />
                      </div>
                      <div className="flex flex-col">
                        <div className="flex items-baseline gap-8">
                          {isLoading ? (
                            <span className="text-2xl-semibold">...</span>
                          ) : (
                            <>
                              <span className="text-2xl-semibold">
                                {formatStatNumber(stats?.users ?? 0).number}
                              </span>
                              {formatStatNumber(stats?.users ?? 0).suffix && (
                                <span className="text-l-bold">
                                  {formatStatNumber(stats?.users ?? 0).suffix}
                                </span>
                              )}
                            </>
                          )}
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
              {isLoading ? (
                <div className="xl:col-span-3 text-center py-32 text-neutral-500">
                  A carregar conjuntos de dados...
                </div>
              ) : latestDatasets.length > 0 ? (
                latestDatasets.map((dataset) => (
                  <Link
                    key={dataset.id}
                    href={`/pages/datasets/${dataset.slug}`}
                    className="dataset-card-home border-2 border-[#1A65FA] rounded-[4px] overflow-hidden h-full flex flex-col"
                  >
                    <CardGeneral
                      variant="white"
                      pillText={
                        dataset.last_modified
                          ? formatDistanceToNow(
                              new Date(dataset.last_modified),
                              { locale: pt, addSuffix: true },
                            )
                          : "Desconhecido"
                      }
                      subtitleText={
                        dataset.organization?.name || "Sem Organização"
                      }
                      titleText={dataset.title}
                      descriptionText={
                        (
                          <div className="flex flex-col grow">
                            <div className="flex items-center text-neutral-900 mb-8">
                              <Icon
                                name="agora-solid-bullet"
                                className="w-8 h-8 text-primary-600"
                                aria-hidden="true"
                              />
                              <span>
                                {dataset.metrics?.views || 0} visualizações
                              </span>
                            </div>
                            <span className="text-m-regular text-neutral-800 dataset-content-proper mb-16 line-clamp-3">
                              {dataset.description}
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
                      anchor={{
                        href: `/pages/datasets/${dataset.slug}`,
                      }}
                    />
                  </Link>
                ))
              ) : (
                <div className="xl:col-span-3 text-center py-32 text-neutral-500">
                  Nenhum conjunto de dados encontrado.
                </div>
              )}
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
              {["arte.svg", "ADC.svg", "IMPIC.svg", "DSPA.svg", "apa.svg"].map(
                (logo, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-center"
                  >
                    <img
                      src={`/Logos/${logo}`}
                      alt={`Logo ${logo.replace(".svg", "")}`}
                      className="h-12 md:h-14 xl:h-16 w-auto object-contain"
                    />
                  </div>
                ),
              )}
            </div>
          </div>
        </div>

        {/* Reuses / Storytelling */}
        <div className="xl:py-64 bg-primary-900">
          <div className="container mx-auto px-4">
            <h2 className="text-xl-bold text-white">Storytelling</h2>
            <p className="mt-16 mb-32 max-w-3xl text-white">
              Precisa de uma descrição uma vez que é um titulo estrangeiro e
              novidade no dados.gov
            </p>
            <div className="grid xs:grid-cols-1 sm:grid-cols-2 md:grid-cols-2 xl:grid-cols-3 gap-32 storytellings">
              {isLoading ? (
                <div className="xl:col-span-3 text-center py-32 text-neutral-300">
                  A carregar reutilizações...
                </div>
              ) : latestReuses.length > 0 ? (
                latestReuses.map((reuse) => (
                  <CardArticle
                    key={reuse.id}
                    variant="indented"
                    image={{
                      src: reuse.image_thumbnail || reuse.image || "",
                      alt: reuse.title,
                    }}
                    subtitle={
                      reuse.created_at
                        ? `Publicado a ${format(new Date(reuse.created_at), "dd MMM yyyy", { locale: pt })}`
                        : ""
                    }
                    title={reuse.title}
                    mainAnchor={{
                      href: `/pages/reuses/${reuse.slug}`,
                    }}
                    blockedLink={true}
                  />
                ))
              ) : (
                <div className="xl:col-span-3 text-center py-32 text-neutral-300">
                  Nenhuma reutilização encontrada.
                </div>
              )}
            </div>
            <div className="mt-32">
              <Link href="/pages/reuses">
                <Button
                  variant="primary"
                  appearance="link"
                  hasIcon={true}
                  trailingIcon="agora-line-arrow-right-circle"
                  trailingIconHover="agora-solid-arrow-right-circle"
                  className="p-0! h-auto icon-white"
                  darkMode={false}
                >
                  <span className="text-white">
                    Ver todas as Data Stories
                  </span>
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
              {isLoading ? (
                <div className="xl:col-span-3 text-center py-32 text-neutral-500">
                  A carregar novidades...
                </div>
              ) : posts.length > 0 ? (
                posts.map((post) => (
                  <div key={post.id} className="latest-news-card-wrapper h-full">
                    <CardArticle
                      image={{
                        src: post.image_thumbnail || post.image || "",
                        alt: post.name,
                      }}
                      subtitle={
                        post.created_at
                          ? `Publicado em ${format(new Date(post.created_at), "dd 'de' MMMM 'de' yyyy", { locale: pt })}`
                          : ""
                      }
                      title={post.name}
                      blockedLink={false}
                    >
                      <div className="mt-auto pt-16">
                        <Link href={`/pages/article/${post.slug}`}>
                          <Button
                            variant="primary"
                            appearance="link"
                            hasIcon={true}
                            trailingIcon="agora-line-arrow-right-circle"
                            trailingIconHover="agora-solid-arrow-right-circle"
                            className="p-0! h-auto"
                          >
                            <span>Ler mais</span>
                          </Button>
                        </Link>
                      </div>
                    </CardArticle>
                  </div>
                ))
              ) : (
                <div className="xl:col-span-3 text-center py-32 text-neutral-500">
                  Nenhuma novidade encontrada.
                </div>
              )}
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
    </main>
  );
}
