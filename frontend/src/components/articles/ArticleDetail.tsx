'use client';

import React from 'react';
import Link from 'next/link';
import { Button, Icon, Breadcrumb } from '@ama-pt/agora-design-system';

const SIDEBAR_ARTICLES = [
    {
        date: '01 de agosto de 2025',
        title: 'Title text lorem ipsum dolor',
        image: '/Articles/last-new1.svg',
        slug: 'webinar-developers-data-scientists'
    },
    {
        date: '01 de agosto de 2025',
        title: 'Title text lorem ipsum dolor',
        image: '/Articles/last-new2.svg',
        slug: 'nova-data-webinar-empresas'
    },
    {
        date: '01 de agosto de 2025',
        title: 'Title text lorem ipsum dolorTitle text lorem ipsum dolorTitle text lorem ipsum dolor',
        image: '/Articles/last-new3.svg',
        slug: 'workshop-visualizacao-dados'
    }
];

export default function ArticleDetail() {
    return (
        <div className="flex flex-col font-sans text-neutral-900 bg-white min-h-screen">
            <main className="grow">
                {/* Header / Hero Area */}
                <div className="container mx-auto px-4 pt-32 pb-48">
                    <Breadcrumb
                        items={[
                            { label: 'Início', url: '/' },
                            { label: 'Artigos', url: '/pages/article' },
                            { label: 'Uma retrospectiva da temporada...', url: '#' }
                        ]}
                    />

                    <div className="mt-48 max-w-4xl">
                        <span className="text-neutral-600 block text-m-regular mb-16">Publicado em 18.12.2025</span>
                        <h1 className="text-2xl-bold md:text-3xl-bold xl:text-4xl-bold text-primary-900 leading-tight mb-24">
                            Uma retrospectiva da temporada de volta às aulas do data.gouv.fr - 3 meses de eventos focados em dados públicos.
                        </h1>
                        <p className="text-m-regular text-neutral-700">
                            Encontre todos os replays desde o início da nova temporada.
                        </p>
                    </div>
                </div>

                <div className="bg-neutral-50 py-64">
                    <div className="container mx-auto px-4">
                        <div className="grid grid-cols-1 lg:grid-cols-12 gap-64">
                            {/* Main Content */}
                            <article className="lg:col-span-8">
                                <div className="text-neutral-800 leading-relaxed text-lg">
                                    <h2 className="text-l-bold text-primary-900 mb-16">
                                        Três meses de acontecimentos para reviver
                                    </h2>
                                    <p className="mb-24 text-m-regular">
                                        O período de volta às aulas ocorreu de setembro a dezembro de 2025 e utilizou diversos formatos:
                                    </p>
                                    <ul className="list-disc pl-24 space-y-12 mb-32 text-m-regular">
                                        <li>Mesas-redondas para refletir sobre os desafios dos dados abertos e compartilhar experiências concretas;</li>
                                        <li>Sessões de perguntas e respostas e tempo para discussão com as equipes da plataforma e as partes interessadas no ecossistema;</li>
                                        <li>Workshops práticos e demonstrações para desenvolver habilidades em ferramentas, APIs e melhores práticas;</li>
                                        <li>Webinários temáticos;</li>
                                        <li>Hackathon sobre projeções climáticas, coorganizado com a Météo-France.</li>
                                    </ul>

                                    <h2 className="text-l-bold text-primary-900 mb-16 mt-48">
                                        Todas as gravações já estão disponíveis
                                    </h2>
                                    <p className="mb-24 text-m-regular">
                                        Boas notícias: todos os webinars e sessões gravadas estão disponíveis para reprodução! Se você perdeu alguma sessão ou deseja aprofundar-se em tópicos específicos, pode assisti-los (ou reassistir-los) a qualquer momento.
                                    </p>
                                    <p className="mb-32 text-m-regular">
                                        <Link href="#" className="text-primary-600 underline font-medium hover:text-primary-700">Encontre as gravações dos webinars na página dedicada</Link>.
                                    </p>

                                    <div className="my-32 rounded-lg overflow-hidden shadow-sm">
                                        <img
                                            src="/Articles/building.png"
                                            alt="Arquitetura e colaboração"
                                            className="w-full h-auto object-cover max-h-[440px]"
                                        />
                                    </div>

                                    <h2 className="text-l-bold text-primary-900 mb-16 mt-48">
                                        Quer ir mais longe?
                                    </h2>
                                    <p className="text-m-regular mb-64">
                                        <Link href="#" className="text-primary-600 underline font-medium hover:text-primary-700">Assine a</Link> newsletter do data.gouv.fr para receber os próximos eventos diretamente na sua caixa de entrada.
                                    </p>

                                    {/* Newsletter Card */}
                                    <div className="bg-[#41525E] rounded-8 p-48 relative overflow-hidden text-white mb-64">
                                        {/* Background 'A' decoration */}
                                        <div className="absolute right-0 bottom-0 opacity-10 pointer-events-none select-none translate-y-1/4 translate-x-1/4 text-white">
                                            <Icon name="agora-solid-agora" className="w-[300px] h-[300px]" />
                                        </div>

                                        <div className="relative z-10 max-w-md">
                                            <h3 className="text-xl-bold mb-16">Title</h3>
                                            <p className="text-m-regular mb-32 text-neutral-200">
                                                Description lorem ipsum dolor sit amet. Egestas sit dictum elementum, turpis morbi amet mauris nunc vitae nisl sapien ut in sed etiam mass.
                                            </p>

                                            <div className="flex flex-col gap-8">
                                                <label htmlFor="newsletter-email" className="text-s-bold">Your email</label>
                                                <div className="relative flex items-center">
                                                    <input
                                                        type="email"
                                                        id="newsletter-email"
                                                        placeholder="Please entre your email"
                                                        className="w-full h-56 px-16 rounded-8 bg-white text-neutral-900 focus:outline-none focus:ring-2 focus:ring-primary-500 border-none"
                                                    />
                                                    <button className="absolute right-8 w-40 h-40 bg-[#034AD8] rounded-full flex items-center justify-center hover:bg-blue-700 transition-colors border-none cursor-pointer">
                                                        <Icon name="agora-solid-arrow-right" className="w-16 h-16 text-white" />
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Social Share */}
                                    <div className="border-t border-neutral-200 pt-32">
                                        <div className="text-s-regular text-neutral-900 mb-16">Partilhar esta notícia</div>
                                        <div className="flex flex-wrap gap-24">
                                            <button className="bg-transparent border-none p-0 flex items-center gap-8 text-primary-600 hover:text-primary-700 transition-colors text-m-regular cursor-pointer">
                                                <Icon name="agora-line-facebook" className="w-24 h-24" />
                                                <span className="text-s-bold">Facebook</span>
                                            </button>
                                            <button className="bg-transparent border-none p-0 flex items-center gap-8 text-primary-600 hover:text-primary-700 transition-colors text-m-regular cursor-pointer">
                                                <Icon name="agora-line-twitter" className="w-24 h-24" />
                                                <span className="text-s-bold">Twitter</span>
                                            </button>
                                            <button className="bg-transparent border-none p-0 flex items-center gap-8 text-primary-600 hover:text-primary-700 transition-colors text-m-regular cursor-pointer">
                                                <Icon name="agora-line-linkedin" className="w-24 h-24" />
                                                <span className="text-s-bold">LinkedIn</span>
                                            </button>
                                            <button className="bg-transparent border-none p-0 flex items-center gap-8 text-primary-600 hover:text-primary-700 transition-colors text-m-regular cursor-pointer">
                                                <img src="/Icons/whatsapp.svg" className="w-24 h-24 text-primary-600" alt="WhatsApp" />
                                                <span className="text-s-bold">WhatsApp</span>
                                            </button>
                                            <button className="bg-transparent border-none p-0 flex items-center gap-8 text-primary-600 hover:text-primary-700 transition-colors text-m-regular cursor-pointer">
                                                <Icon name="agora-line-mail" className="w-24 h-24" />
                                                <span className="text-s-bold">e-mail</span>
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </article>

                            {/* Sidebar / Related Articles */}
                            <aside className="lg:col-span-4">
                                <h3 className="text-l-regular text-neutral-900 mb-32">
                                    Outros <span className="font-bold">artigos</span> relacionados
                                </h3>
                                <div className="flex flex-col gap-32">
                                    {SIDEBAR_ARTICLES.map((article, idx) => (
                                        <div key={idx} className="flex gap-16 group cursor-pointer border-b border-neutral-100 pb-24 last:border-0">
                                            <div className="flex-grow flex flex-col justify-between">
                                                <span className="text-xs text-neutral-500 mb-8">{article.date}</span>
                                                <Link href={`/pages/article/${article.slug}`}>
                                                    <h4 className="text-m-bold text-neutral-900 group-hover:text-primary-600 transition-colors line-clamp-3">
                                                        {article.title}
                                                    </h4>
                                                </Link>
                                            </div>
                                            <div className="w-80 h-48 shrink-0 rounded overflow-hidden">
                                                <img
                                                    src={article.image}
                                                    alt={article.title}
                                                    className="w-full h-full object-cover"
                                                />
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </aside>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}
