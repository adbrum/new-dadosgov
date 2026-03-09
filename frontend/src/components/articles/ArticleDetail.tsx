'use client';

import React from 'react';
import { Button, Icon, Breadcrumb, CardArticle, CardHighlight, Tag } from '@ama-pt/agora-design-system';

export default function ArticleDetail() {
    return (
        <div className="flex flex-col font-sans text-neutral-900 bg-white min-h-screen">
            <main className="flex-grow">
                <div className="container mx-auto px-4 pt-32 pb-32">
                    <Breadcrumb
                        items={[
                            { label: 'Página inicial', url: '/' },
                            { label: 'Últimas novidades', url: '#' },
                            { label: 'Uma retrospectiva da temporada...', url: '#' }
                        ]}
                    />
                </div>

                {/* Hero section with CardHighlight */}
                <CardHighlight
                    image={{
                        src: '/Banner/cubes.svg',
                        alt: 'Uma retrospectiva da temporada de volta às aulas do data.gouv.fr',
                        style: { objectFit: 'cover', width: '100%', minHeight: '400px' }
                    }}
                    highlightAreaPosition="interior"
                    cardPosition="middle"
                    subtitle={
                        <div className="mb-16">
                            <span className="text-neutral-600 block text-sm">Publicado em 18.12.2025</span>
                        </div>
                    }
                    title={
                        <h1 className="text-3xl md:text-3xl xl:text-4xl font-bold text-primary-900 leading-tight">
                            Uma retrospectiva da temporada de volta às aulas do data.gouv.fr - 3 meses de eventos focados em dados públicos.
                        </h1>
                    }
                    description={
                        <p className="text-neutral-700 mt-12">
                            Encontre todos os replays desde o início da nova temporada.
                        </p>
                    }
                    links={[]}
                />

                <div className="container mx-auto px-4 py-64">

                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-64">
                        {/* Main Content */}
                        <article className="lg:col-span-8">
                            <div className="text-neutral-800 leading-relaxed text-lg">
                                <p className="mb-32">
                                    Durante o outono de 2025, organizamos uma série excepcional de encontros, webinars e workshops sobre dados públicos. Este evento, denominado “Volta às Aulas” da Datagouv, reuniu uma comunidade ampla e ativa de cidadãos, funcionários públicos, empresas, pesquisadores e entusiastas de dados durante três meses para discutir o acesso, a circulação e o uso de dados públicos.
                                </p>

                                <h2 className="text-2xl font-bold text-primary-900 mb-16 mt-48">
                                    Três meses de acontecimentos para reviver
                                </h2>
                                <p className="mb-24">
                                    O período de volta às aulas <a href="#" className="text-primary-600 underline font-medium hover:text-primary-700">do data.gouv.fr</a> ocorreu de setembro a dezembro de 2025 e utilizou diversos formatos:
                                </p>
                                <ul className="list-disc pl-24 space-y-12 mb-32">
                                    <li>Mesas-redondas para refletir sobre os desafios dos dados abertos e compartilhar experiências concretas;</li>
                                    <li>Sessões de perguntas e respostas e tempo para discussão com as equipes da plataforma e as partes interessadas no ecossistema;</li>
                                    <li>Workshops práticos e demonstrações para desenvolver habilidades em ferramentas, APIs e melhores práticas;</li>
                                    <li>Webinários temáticos;</li>
                                    <li>Hackathon sobre projeções climáticas, coorganizado com a Météo-France.</li>
                                </ul>

                                <h2 className="text-2xl font-bold text-primary-900 mb-16 mt-48">
                                    Todas as gravações já estão disponíveis
                                </h2>
                                <p className="mb-24">
                                    Boas notícias: todos os webinars e sessões gravadas estão disponíveis para reprodução! Se você perdeu alguma sessão ou deseja aprofundar-se em tópicos específicos, pode assisti-los (ou reassistir-los) a qualquer momento.
                                </p>
                                <p className="mb-48">
                                    <a href="#" className="text-primary-600 underline font-medium hover:text-primary-700">Encontre as gravações dos webinars na página dedicada</a>.
                                </p>

                                <div className="my-24 rounded-2xl overflow-hidden shadow-sm">
                                    <img
                                        src="/Articles/building.png"
                                        alt="Arquitetura e colaboração"
                                        className="w-full h-auto object-cover max-h-[400px]"
                                    />
                                </div>

                                <h2 className="text-2xl font-bold text-primary-900 mb-16 mt-48">
                                    Quer ir mais longe?
                                </h2>
                                <p>
                                    <a href="#" className="text-primary-600 underline font-medium hover:text-primary-700">Assine a</a> newsletter do data.gouv.fr para receber os próximos eventos diretamente na sua caixa de entrada.
                                </p>
                            </div>
                        </article>
                    </div>
                </div>
            </main>
        </div>
    );
}
