'use client';

import Link from 'next/link';
import { Breadcrumb, InputSearch, Icon, CardGeneral, Feedback } from '@ama-pt/agora-design-system';
import { MiniCoursesFilters } from './MiniCoursesFilters';
import { Pagination } from '@/components/Pagination';

function toSlug(title: string): string {
  return title
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-');
}

export default function MiniCoursesClient() {
  return (
    <div className="min-h-screen flex flex-col font-sans text-neutral-900 bg-neutral-50 ">
      <main className="flex-grow">
        <div className="bg-[#F8F9FC]">
          <div className="container mx-auto px-4 my-64 lg:px-64">
            <Breadcrumb
              items={[
                { label: 'Início', url: '/' },
                { label: 'Minicursos', url: '/pages/mini-cursos' }
              ]}
              className="mb-64"
            />
            <div className="flex">
              <div className="w-1/2 pr-32">
                <h1 className="text-[40px] leading-[48px] font-bold text-primary-600 mb-32">
                  Minicursos
                </h1>

                <div className="text-[18px] leading-[28px] space-y-16 w-[94%]">
                  <p>
                    As formações do Mosaico destinam-se a diferentes perfis da Administração Pública e visam apoiar o desenvolvimento de competências essenciais para a transformação digital do Estado. Através de uma abordagem prática, permitem desenvolver conhecimentos técnicos e estratégicos para modernizar serviços públicos e melhorar a eficiência e a qualidade do atendimento.
                  </p>
                </div>

                <div className="mt-64">
                  Atualizado em 30.09.2025
                </div>
              </div>
              <div className="img-container">
                <img src="/minicourses/mini_cursos.svg" alt="Minicursos" className="w-[597px] h-[390px]" />
              </div>
            </div>
          </div>
        </div>


        <div className="bg-white py-64 border-t border-neutral-100">
          <div className="container mx-auto px-4 lg:px-64">
            <div className="grid md:grid-cols-3 xl:grid-cols-12 gap-[36px]">
              {/* Sidebar */}
              <div className="xl:col-span-3">
                <MiniCoursesFilters />
              </div>

              {/* Results Area */}
              <div className="xl:col-span-9">


                <div className="bg-white pt-64 pb-64">
                  <div className="container px-4 lg:px-64">
                    <div className="max-w-[700px]">
                      <h2 className="text-[18px] font-bold text-[#000066] mb-16">
                        Que minicurso procura?
                      </h2>
                      <InputSearch
                        id="courses-search"
                        label="Pesquisar minicursos"
                        hideLabel
                        placeholder="Pesquise pelo nome da formação, área técnica ou perfil"
                      />
                    </div>
                  </div>
                </div>


                <div className="flex justify-end mb-16">
                  <span className="text-[14px] text-neutral-500 font-medium tracking-tight">4 de 8 resultados</span>
                </div>

                <div className="flex flex-col gap-24">
                  {miniCourses.map((course, index) => (
                    <div
                      key={index}
                      className="bg-accent-light p-24 rounded-8 mini-course-card-wrapper"
                    >
                      <div className="dataset-card-modern">
                        <div className="card-general">
                          <CardGeneral
                            isCardHorizontal={true}
                            variant="white"
                            titleText={
                              (
                                <Link href={`/pages/mini-courses/${toSlug(course.title)}`} className="hover:underline text-primary-900 font-bold text-lg">
                                  {course.title}
                                </Link>
                              ) as unknown as string
                            }
                            descriptionText={course.description}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Pagination */}
                <div className="mt-64 flex justify-center pb-64 mini-courses-pagination">
                  <Pagination
                    currentPage={1}
                    totalItems={8}
                    pageSize={4}
                    baseUrl="/pages/mini-cursos"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-accent-light">
          <div className="container mx-auto">
            <div>
              <Feedback
                title="O conteúdo da página foi útil?"
                subtitle="Avalie a sua experiência nesta página e deixe-nos um comentário."
                ratingButtons={{
                  likeButton: { children: 'Sim', appearance: 'outline', variant: 'success' },
                  dislikeButton: { children: 'Não', appearance: 'outline', variant: 'danger' }
                }}
              />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

const miniCourses = [
  {
    title: "Minicurso sobre a introdução aos dados abertos",
    description: "Este minicurso apresenta as informações introdutórias fundamentais dos dados abertos, explicando o que são, para que servem e porque são fundamentais para a transparência, inovação e reutilização da informação.",
    updatedAt: "2 dias",
    duration: "30 min",
    organization: {
      name: "dados.gov",
      logo: "/Logos/logo.png"
    },
    metrics: {
      views: "1.2k",
      downloads: "450",
      stars: "125"
    }
  },
  {
    title: "MiniCurso sobre reutilizações de dados abertos",
    description: "Este minicurso apresenta como reutilizar dados abertos de forma prática e segura. Veremos como transformar informação pública em conhecimento útil, os formatos e licenças mais adequados, e os benefícios de usar dados já disponíveis.",
    updatedAt: "1 semana",
    duration: "45 min",
    organization: {
      name: "AMA",
      logo: "/Logos/logo.png"
    },
    metrics: {
      views: "890",
      downloads: "320",
      stars: "98"
    }
  },
  {
    title: "Minicurso sobre Metadados",
    description: "Este minicurso apresenta os conceitos introdutórios fundamentais dos metadados relacionados com dados abertos, explicando o que são, para que servem e porque são essenciais para a descoberta.",
    updatedAt: "3 dias",
    duration: "20 min",
    organization: {
      name: "LabX",
      logo: "/Logos/logo.png"
    },
    metrics: {
      views: "2.5k",
      downloads: "1.1k",
      stars: "340"
    }
  },
  {
    title: "Minicurso sobre os diferentes formatos de datasets",
    description: "Este minicurso apresenta os conceitos essenciais sobre a publicação de dados abertos no dados.gov.pt, com foco nos formatos de datasets, metadados e no modelo das 5 Estrelas dos Dados Abertos.",
    updatedAt: "1 mês",
    duration: "1h",
    organization: {
      name: "dados.gov",
      logo: "/Logos/logo.png"
    },
    metrics: {
      views: "3.4k",
      downloads: "2.1k",
      stars: "520"
    }
  }
];
