"use client";

import { useEffect, useState, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Button, Icon } from "@ama-pt/agora-design-system";
import {
  searchDatasets,
  searchOrganizations,
  searchReuses,
} from "@/services/api";
import { Dataset, Organization, Reuse } from "@/types/api";
import SearchDropdown from "@/components/search/SearchDropdown";

type SearchType = "datasets" | "organizations" | "reuses";

const TYPES: { type: SearchType; label: string; icon: string }[] = [
  {
    type: "datasets",
    label: "Conjuntos de Dados",
    icon: "agora-line-layers-menu",
  },
  {
    type: "reuses",
    label: "Reutilizações",
    icon: "agora-line-arrow-right-circle",
  },
  {
    type: "organizations",
    label: "Organizações",
    icon: "agora-line-document",
  },
];

const PAGE_SIZE = 10;

export default function SearchClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const query = searchParams.get("q") || "";
  const tabParam = searchParams.get("type") as SearchType | null;
  const pageParam = Number(searchParams.get("page")) || 1;

  const [activeTab, setActiveTab] = useState<SearchType>(
    tabParam || "datasets",
  );

  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [reuses, setReuses] = useState<Reuse[]>([]);

  const [totals, setTotals] = useState({
    datasets: 0,
    organizations: 0,
    reuses: 0,
  });

  const [isLoading, setIsLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(pageParam);

  useEffect(() => {
    if (tabParam && TYPES.some((t) => t.type === tabParam)) {
      setActiveTab(tabParam);
    }
  }, [tabParam]);

  useEffect(() => {
    setCurrentPage(pageParam);
  }, [pageParam]);

  // Fetch totals for all types when query changes
  useEffect(() => {
    if (!query) return;

    async function fetchTotals() {
      const [dsRes, orgRes, reuseRes] = await Promise.all([
        searchDatasets(query, 1, 1),
        searchOrganizations(query, 1, 1),
        searchReuses(query, 1, 1),
      ]);
      setTotals({
        datasets: dsRes.total,
        organizations: orgRes.total,
        reuses: reuseRes.total,
      });
    }

    fetchTotals();
  }, [query]);

  // Fetch results for active tab
  useEffect(() => {
    if (!query) return;

    async function fetchResults() {
      setIsLoading(true);
      try {
        if (activeTab === "datasets") {
          const res = await searchDatasets(
            query,
            currentPage,
            PAGE_SIZE,
          );
          setDatasets(res.data || []);
        } else if (activeTab === "organizations") {
          const res = await searchOrganizations(
            query,
            currentPage,
            PAGE_SIZE,
          );
          setOrganizations(res.data || []);
        } else if (activeTab === "reuses") {
          const res = await searchReuses(
            query,
            currentPage,
            PAGE_SIZE,
          );
          setReuses(res.data || []);
        }
      } catch (error) {
        console.error("Error searching:", error);
      } finally {
        setIsLoading(false);
      }
    }

    fetchResults();
  }, [query, activeTab, currentPage]);

  const buildUrl = useCallback(
    (params: { type?: string; page?: number }) => {
      const t = params.type || activeTab;
      const p = params.page || 1;
      return `/pages/search?q=${encodeURIComponent(query)}&type=${t}&page=${p}`;
    },
    [query, activeTab],
  );

  const handleTabChange = (tab: SearchType) => {
    setActiveTab(tab);
    setCurrentPage(1);
    router.push(buildUrl({ type: tab, page: 1 }));
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    router.push(buildUrl({ page }));
  };

  const totalForActiveTab = totals[activeTab];
  const totalPages = Math.ceil(totalForActiveTab / PAGE_SIZE);
  const headingMap: Record<SearchType, string> = {
    datasets: "Pesquisa avançada de conjuntos de dados",
    reuses: "Pesquisa avançada de reutilizações",
    organizations: "Pesquisa de organizações",
  };

  return (
    <div className="container mx-auto px-4 py-48">
      {/* Breadcrumb */}
      <nav className="text-s-regular text-neutral-500 mb-16">
        <Link href="/" className="hover:text-primary-600">
          Início
        </Link>
        <span className="mx-8">&gt;</span>
        <span className="text-neutral-700">Pesquisa</span>
      </nav>

      {/* Heading */}
      <h1 className="text-xl-bold text-primary-900 mb-24">
        {headingMap[activeTab]}
      </h1>

      {/* Search Bar */}
      <div className="mb-32">
        <SearchDropdown
          id="search-page-input"
          placeholder="Pesquisar datasets, organizações, reutilizações..."
          label="Pesquisar no portal"
        />
      </div>

      {query && (
        <div className="grid grid-cols-1 md:grid-cols-12 gap-32">
          {/* Left Sidebar */}
          <aside className="md:col-span-3">
            {/* Type */}
            <h2 className="text-m-bold text-neutral-900 mb-16">
              Tipo
            </h2>
            <ul className="list-none m-0 p-0 mb-32">
              {TYPES.map((item) => (
                <li key={item.type}>
                  <button
                    onClick={() => handleTabChange(item.type)}
                    className={`flex items-center gap-8 w-full px-12 py-10 text-left text-s-regular rounded-4 transition-colors cursor-pointer ${
                      activeTab === item.type
                        ? "bg-primary-50 text-primary-700 font-semibold"
                        : "text-neutral-700 hover:bg-neutral-50"
                    }`}
                  >
                    <Icon
                      name={item.icon}
                      className="w-16 h-16 shrink-0"
                      aria-hidden="true"
                    />
                    <span className="flex-1">{item.label}</span>
                    <span
                      className={`text-xs font-medium px-8 py-2 rounded-full ${
                        activeTab === item.type
                          ? "bg-primary-200 text-primary-800"
                          : "bg-neutral-100 text-neutral-600"
                      }`}
                    >
                      {totals[item.type]}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </aside>

          {/* Right Content */}
          <div className="md:col-span-9">
            {/* Results header */}
            <div className="flex items-center justify-between mb-16">
              <p className="text-s-regular text-neutral-600">
                {totalForActiveTab} resultado
                {totalForActiveTab !== 1 ? "s" : ""}
              </p>
            </div>

            {/* Results */}
            {isLoading ? (
              <div className="text-center py-48 text-neutral-500">
                A pesquisar...
              </div>
            ) : (
              <>
                {/* Datasets */}
                {activeTab === "datasets" && (
                  <div className="flex flex-col gap-0">
                    {datasets.length > 0 ? (
                      datasets.map((dataset) => (
                        <Link
                          key={dataset.id}
                          href={`/pages/datasets/${dataset.slug}`}
                          className="block p-20 border border-neutral-200 -mt-px first:rounded-t-8 last:rounded-b-8 hover:border-primary-600 hover:z-10 hover:shadow-sm transition-all relative"
                        >
                          <h3 className="text-m-bold text-primary-700">
                            {dataset.title}
                          </h3>
                          {dataset.organization && (
                            <p className="text-s-regular text-neutral-500 mt-4">
                              {dataset.organization.name}
                              {dataset.last_modified && (
                                <span className="ml-8">
                                  — Atualizado a{" "}
                                  {new Date(
                                    dataset.last_modified,
                                  ).toLocaleDateString("pt-PT")}
                                </span>
                              )}
                            </p>
                          )}
                          <p className="text-s-regular text-neutral-700 mt-8 line-clamp-2">
                            {dataset.description}
                          </p>
                          {dataset.tags?.length > 0 && (
                            <div className="flex flex-wrap gap-8 mt-8">
                              {dataset.tags
                                .slice(0, 5)
                                .map((tag) => (
                                  <span
                                    key={tag}
                                    className="text-xs px-8 py-2 bg-neutral-100 text-neutral-600 rounded-full"
                                  >
                                    {tag}
                                  </span>
                                ))}
                            </div>
                          )}
                        </Link>
                      ))
                    ) : (
                      <NoResults query={query} />
                    )}
                  </div>
                )}

                {/* Organizations */}
                {activeTab === "organizations" && (
                  <div className="flex flex-col gap-0">
                    {organizations.length > 0 ? (
                      organizations.map((org) => (
                        <Link
                          key={org.id}
                          href={`/pages/organizations/${org.slug}`}
                          className="flex items-center gap-20 p-20 border border-neutral-200 -mt-px first:rounded-t-8 last:rounded-b-8 hover:border-primary-600 hover:z-10 hover:shadow-sm transition-all relative"
                        >
                          {org.logo ? (
                            <img
                              src={org.logo}
                              alt={org.name}
                              className="w-48 h-48 object-contain rounded-4 shrink-0"
                            />
                          ) : (
                            <div className="w-48 h-48 bg-neutral-100 rounded-4 flex items-center justify-center shrink-0">
                              <Icon
                                name="agora-line-document"
                                className="w-20 h-20 text-neutral-400"
                                aria-hidden="true"
                              />
                            </div>
                          )}
                          <div className="flex-1">
                            <h3 className="text-m-bold text-primary-700">
                              {org.name}
                            </h3>
                            {org.description && (
                              <p className="text-s-regular text-neutral-700 mt-4 line-clamp-2">
                                {org.description}
                              </p>
                            )}
                          </div>
                        </Link>
                      ))
                    ) : (
                      <NoResults query={query} />
                    )}
                  </div>
                )}

                {/* Reuses */}
                {activeTab === "reuses" && (
                  <div className="flex flex-col gap-0">
                    {reuses.length > 0 ? (
                      reuses.map((reuse) => (
                        <Link
                          key={reuse.id}
                          href={`/pages/reuses/${reuse.slug}`}
                          className="flex items-center gap-20 p-20 border border-neutral-200 -mt-px first:rounded-t-8 last:rounded-b-8 hover:border-primary-600 hover:z-10 hover:shadow-sm transition-all relative"
                        >
                          {reuse.image_thumbnail || reuse.image ? (
                            <img
                              src={
                                reuse.image_thumbnail ||
                                reuse.image ||
                                ""
                              }
                              alt={reuse.title}
                              className="w-48 h-48 object-cover rounded-4 shrink-0"
                            />
                          ) : (
                            <div className="w-48 h-48 bg-neutral-100 rounded-4 flex items-center justify-center shrink-0">
                              <Icon
                                name="agora-line-arrow-right-circle"
                                className="w-20 h-20 text-neutral-400"
                                aria-hidden="true"
                              />
                            </div>
                          )}
                          <div className="flex-1">
                            <h3 className="text-m-bold text-primary-700">
                              {reuse.title}
                            </h3>
                            {reuse.organization && (
                              <p className="text-s-regular text-neutral-500 mt-4">
                                {reuse.organization.name}
                              </p>
                            )}
                            <p className="text-s-regular text-neutral-700 mt-4 line-clamp-2">
                              {reuse.description}
                            </p>
                          </div>
                        </Link>
                      ))
                    ) : (
                      <NoResults query={query} />
                    )}
                  </div>
                )}

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-center gap-8 mt-32">
                    <button
                      onClick={() =>
                        handlePageChange(currentPage - 1)
                      }
                      disabled={currentPage <= 1}
                      className="px-16 py-8 text-s-regular border border-neutral-200 rounded-4 disabled:opacity-40 disabled:cursor-not-allowed hover:border-primary-600 cursor-pointer"
                    >
                      Anterior
                    </button>
                    <span className="text-s-regular text-neutral-600 px-16">
                      Página {currentPage} de {totalPages}
                    </span>
                    <button
                      onClick={() =>
                        handlePageChange(currentPage + 1)
                      }
                      disabled={currentPage >= totalPages}
                      className="px-16 py-8 text-s-regular border border-neutral-200 rounded-4 disabled:opacity-40 disabled:cursor-not-allowed hover:border-primary-600 cursor-pointer"
                    >
                      Seguinte
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {/* Empty state — no query */}
      {!query && (
        <div className="text-center py-48 text-neutral-500">
          <p className="text-m-regular">
            Introduza um termo para pesquisar no portal.
          </p>
        </div>
      )}
    </div>
  );
}

function NoResults({ query }: { query: string }) {
  return (
    <div className="text-center py-48 text-neutral-500">
      <p className="text-m-regular">
        Nenhum resultado encontrado para &quot;{query}&quot;
      </p>
      <p className="text-s-regular mt-8">
        Tente pesquisar com termos diferentes.
      </p>
    </div>
  );
}
