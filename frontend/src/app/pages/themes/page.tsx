'use client';

import React from 'react';
import { Icon, Accordion, AccordionGroup } from '@ama-pt/agora-design-system';
import PageBanner from '@/components/PageBanner';

export default function ThemesPage() {
  return (
    <main className="flex-grow bg-white">
      <PageBanner
        title="Dados relacionados à cultura"
        breadcrumbItems={[
          { label: 'Home', url: '/' },
          { label: 'Dados relacionados à cultura', url: '#' }
        ]}
      >
        <div className="subtitle">
          <p className="text-primary-100 mb-8 max-w-4xl text-lg leading-relaxed">
            Esta página tem como objetivo listar os principais conjuntos de dados relacionados à cultura disponíveis em dados.gov.pt. Ela não é exaustiva e <a href="#" className="underline hover:text-primary-200 transition-colors">está aberta a contribuições</a>.
          </p>
          <p className="text-primary-100 max-w-4xl text-lg leading-relaxed">
            Você pode descobrir todos os dados relacionados à cultura em <a href="#" className="underline hover:text-primary-200 transition-colors">culture.data.gouv.fr</a>, a plataforma dedicada a referenciar, promover e divulgar dados culturais públicos na França.
          </p>
        </div>
      </PageBanner>

      <div className="container mx-auto px-4 py-64">
        <div className="grid md:grid-cols-3 xl:grid-cols-12 gap-32">

          {/* Sidebar Navigation */}
          <div className="xl:col-span-4 xl:block">
            <div className="sticky top-120">
              <div className="mb-40 flex justify-center md:justify-start">
                <img
                  src="/man_sound.svg"
                  alt="Ilustração de Cultura"
                  className="w-[232px] h-[250px] object-contain"
                />
              </div>

              <div className="flex flex-col pt-16">
                <div className="py-16">
                  <a href="#" className="text-neutral-900 font-bold hover:text-primary-700 transition-colors flex items-center justify-between">
                    Observações preliminares
                  </a>
                </div>

                <AccordionGroup>
                  <Accordion headingTitle="Ofertas e espaços culturais" headingLevel="h3">
                    <div className="pl-16 flex flex-col gap-8 text-sm text-neutral-600 pb-12">
                      <a href="#heranca" className="hover:text-primary-700 transition-colors">Herança</a>
                      <a href="#livros" className="hover:text-primary-700 transition-colors">Livros e leitura</a>
                      <a href="#imprensa" className="hover:text-primary-700 transition-colors">Imprensa</a>
                      <a href="#cinema" className="hover:text-primary-700 transition-colors">Cinema</a>
                      <a href="#apresentacao" className="hover:text-primary-700 transition-colors">Apresentação ao vivo</a>
                    </div>
                  </Accordion>


                  <Accordion headingTitle="Políticas culturais" headingLevel="h3">
                    <div className="pl-16 flex flex-col gap-8 text-sm text-neutral-600 pb-12">
                      <p className="text-neutral-500">Conteúdo em breve...</p>
                    </div>
                  </Accordion>

                  <Accordion headingTitle="Economia da cultura" headingLevel="h3">
                    <div className="pl-16 flex flex-col gap-8 text-sm text-neutral-600 pb-12">
                      <p className="text-neutral-500">Conteúdo em breve...</p>
                    </div>
                  </Accordion>
                </AccordionGroup>

                <div className="py-16 px-16 border-b border-neutral-200">
                  <a href="#" className="text-neutral-900 font-bold hover:text-primary-700 transition-colors block">
                    Recursos documentais culturais
                  </a>
                </div>

                <div className="py-16 px-16 border-b border-neutral-200">
                  <a href="#" className="text-neutral-900 font-bold hover:text-primary-700 transition-colors block">
                    Reutilização de dados relacionados à cultura
                  </a>
                </div>

                <div className="py-16 px-16">
                  <a href="#" className="text-neutral-900 font-bold hover:text-primary-700 transition-colors leading-tight block">
                    Os principais produtores de dados relacionados à cultura
                  </a>
                </div>
              </div>
            </div>
          </div>

          {/* Main Content Area */}
          <div className="xl:col-span-8 ml-32 ">
            <section className="mb-64">
              <h2 className="text-xl-bold text-neutral-900 mb-24">Ofertas e espaços culturais</h2>
              <ul className="space-y-4 mb-48">
                <li>
                  <a href="#" className="text-primary-700 hover:underline flex items-center gap-8 font-medium group">
                    Base de dados de espaços e instalações culturais (Basílica)
                    <Icon name="agora-line-external-link" className="w-4 h-4 transition-transform group-hover:translate-x-1 group-hover:-translate-y-1" />
                  </a>
                </li>
              </ul>

              {/* Herança Section */}
              <div id="heranca" className="mt-48 scroll-mt-120">
                <h3 className="text-xl font-bold text-neutral-900 border-b border-neutral-200 pb-8 mb-24 flex items-center gap-12">
                  Herança
                </h3>
                <ul className="space-y-12 list-disc pl-24 text-neutral-700">
                  <li>
                    <a href="#" className="text-primary-700 hover:underline font-medium">Edifícios protegidos como Monumentos Históricos</a>
                  </li>
                  <li>
                    <a href="#" className="text-primary-700 hover:underline font-medium">Lista e localização de museus na França</a>
                  </li>
                  <li>
                    <a href="#" className="text-primary-700 hover:underline font-medium">Lista de coordenadas GPS de monumentos nacionais</a>
                  </li>
                  <li>
                    <a href="#" className="text-primary-700 hover:underline font-medium">Museus da França: Base de dados Muséofile</a>
                  </li>
                  <li>
                    <a href="#" className="text-primary-700 hover:underline font-medium">Lista de sítios patrimoniais notáveis (SPR)</a>:
                    <span className="ml-4">Cidades, vilas ou distritos cuja conservação, restauração, reabilitação ou valorização apresenta, do ponto de vista histórico, arquitetônico, arqueológico, artístico ou paisagístico, interesse público.</span>
                  </li>
                  <li>
                    <a href="#" className="text-primary-700 hover:underline font-medium">Lista de edifícios classificados como &quot;Arquitetura Contemporânea Notável&quot; (ACR)</a>:
                    <span className="ml-4">Edifícios, conjuntos arquitetônicos, obras de arte e empreendimentos cujo design apresenta interesse arquitetônico ou técnico.</span>
                  </li>
                  <li>
                    <a href="#" className="text-primary-700 hover:underline font-medium">Lista de Casas de Personalidades Ilustres</a>:
                    <span className="ml-4">Lugares cuja finalidade é preservar e transmitir a memória de mulheres e homens que se destacaram na história política, social e cultural.</span>
                  </li>
                  <li>
                    <a href="#" className="text-primary-700 hover:underline font-medium">Lista de jardins notáveis</a>:
                    <span className="ml-4">Jardins e parques de interesse cultural, estético, histórico ou botânico.</span>
                  </li>
                </ul>
              </div>

              {/* Livros e leitura Section */}
              <div id="livros" className="mt-48 scroll-mt-120">
                <h3 className="text-xl font-bold text-neutral-900 border-b border-neutral-200 pb-8 mb-24">Livros e leitura</h3>
                <ul className="space-y-12 list-disc pl-24 text-neutral-700">
                  <li>
                    <a href="#" className="text-primary-700 hover:underline font-medium">Bibliotecas municipais: endereços e dados de atividade</a>
                  </li>
                  <li>
                    <a href="#" className="text-primary-700 hover:underline font-medium">Lista de organizações beneficiadas pela exceção de direitos autorais para pessoas com deficiência</a>
                  </li>
                </ul>
              </div>

              {/* Imprensa Section */}
              <div id="imprensa" className="mt-48 scroll-mt-120">
                <h3 className="text-xl font-bold text-neutral-900 border-b border-neutral-200 pb-8 mb-24">Imprensa</h3>
                <ul className="space-y-12 list-disc pl-24 text-neutral-700">
                  <li>
                    <a href="#" className="text-primary-700 hover:underline font-medium">Lista de publicações de imprensa</a>
                  </li>
                  <li>
                    <a href="#" className="text-primary-700 hover:underline font-medium">Lista de serviços de notícias online reconhecidos</a>
                  </li>
                  <li>
                    <a href="#" className="text-primary-700 hover:underline font-medium">Lista de agências de notícias credenciadas</a>
                  </li>
                </ul>
              </div>

              {/* Cinema Section */}
              <div id="cinema" className="mt-48 scroll-mt-120">
                <h3 className="text-xl font-bold text-neutral-900 border-b border-neutral-200 pb-8 mb-24">Cinema</h3>
                <ul className="space-y-12 list-disc pl-24 text-neutral-700">
                  <li>
                    <a href="#" className="text-primary-700 hover:underline font-medium">Lista de cinemas em funcionamento</a>
                  </li>
                  <li>
                    <a href="#" className="text-primary-700 hover:underline font-medium">Cinemas do OpenStreetMap</a>
                  </li>
                </ul>
              </div>

              {/* Apresentação ao vivo Section */}
              <div id="apresentacao" className="mt-48 scroll-mt-120">
                <h3 className="text-xl font-bold text-neutral-900 border-b border-neutral-200 pb-8 mb-24">Apresentação ao vivo</h3>
                <ul className="space-y-12 list-disc pl-24 text-neutral-700">
                  <li>
                    <a href="#" className="text-primary-700 hover:underline font-medium">Ópera - Apresentações líricas e coreográficas - Temporada 2023/2024</a>
                  </li>
                </ul>
              </div>
            </section>
          </div>
        </div>
      </div>
    </main>
  );
}
