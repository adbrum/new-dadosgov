'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { Button, Breadcrumb } from '@ama-pt/agora-design-system';

const relatedCourses = [
  {
    title: 'Minicurso sobre reutilizações de dados abertos',
    description:
      'Este minicurso apresenta como reutilizar dados abertos de forma prática e segura.',
    slug: 'reutilizacao-dados-abertos',
    duration: '15 min',
  },
  {
    title: 'Minicurso sobre Metadados',
    description:
      'Este minicurso apresenta os conceitos introdutórios fundamentais dos metadados '
      + 'relacionados com dados abertos, explicando o que são, para que servem e porque são '
      + 'essenciais para a descoberta, compreensão e reutilização correta da informação.',
    slug: 'metadados',
    duration: '20 min',
  },
  {
    title: 'Minicurso sobre os diferentes formatos de datasets',
    description:
      'Este minicurso apresenta os conceitos essenciais sobre a publicação de dados abertos '
      + 'no dados.gov.pt, com foco nos formatos de datasets, metadados e no modelo das 5 '
      + 'Estrelas dos Dados Abertos.',
    slug: 'formatos-datasets',
    duration: '18 min',
  },
];

const socialLinks = [
  { name: 'Facebook', icon: 'agora-line-facebook' },
  { name: 'Twitter', icon: 'agora-line-twitter' },
  { name: 'LinkedIn', icon: 'agora-line-linkedin' },
  { name: 'WhatsApp', customIcon: '/Icons/whatsapp.svg' },
  { name: 'e-mail', icon: 'agora-line-mail' },
];

interface Props {
  slug?: string;
}

export default function MiniCourseCompletionClient({ slug }: Props) {
  const [isFavorite, setIsFavorite] = useState(true);

  return (
    <div className="flex flex-col font-sans text-neutral-900 bg-white min-h-screen">
      <main className="flex-grow bg-white">

        {/* ── Hero / Congratulations Banner ── */}
        <div
          className="bg-accent-light"
        >
          <div className="card-container relative z-10 pt-32 pb-48 md:py-64">
            <div className="container mx-auto px-4">
              <Breadcrumb
                darkMode={false}
                items={[
                  { label: 'Home', url: '/' },
                  { label: 'Minicursos', url: '/pages/mini-courses' },
                  {
                    label: 'Minicurso sobre a introdução aos dados abertos',
                    url: '/pages/mini-courses/introducao-dados-abertos',
                  },
                  { label: 'Conclusão', url: '#' },
                ]}
              />

              <div className="grid md:grid-cols-3 xl:grid-cols-12 gap-32 mt-32">
                {/* Left: Texts */}
                <div className="xl:col-span-7 xl:block md:pt-32">


                  <h1
                    className="leading-60 mb-16 text-40 text-brand-blue-primary"
                  >
                    <span className="font-bold">Parabéns!</span> Concluiu o<br />
                    minicurso de Dados Abertos
                  </h1>

                  <p
                    className="text-lg leading-relaxed mb-32 text-brand-blue-secondary"
                  >
                    O seu compromisso com a informação e a transparência fará toda a diferença.<br />
                    Continue a explorar e a transformar dados em conhecimento!
                  </p>


                  {/* Action Buttons */}
                  <div className="flex flex-wrap gap-16">
                    <Button
                      variant="primary"
                      appearance="outline"
                      hasIcon={true}
                      leadingIcon="agora-line-star"
                      leadingIconHover="agora-solid-star"
                      onClick={() => setIsFavorite(!isFavorite)}
                      className="px-24 h-48"
                    >
                      Adicionar aos favoritos
                    </Button>
                    <Button
                      variant="primary"
                      appearance="solid"
                      hasIcon={true}
                      trailingIcon="agora-line-arrow-right-circle"
                      trailingIconHover="agora-solid-arrow-right-circle"
                      className="px-24 h-48"
                    >
                      Ver mais cursos
                    </Button>
                  </div>
                </div>

                {/* Right: Trophy image */}
                <div className="xl:col-span-5 md:pt-32 flex justify-center items-center">
                  <img
                    src="/minicourses/cup.png"
                    alt="Troféu de conclusão"
                    className="max-h-[320px] w-auto drop-shadow-2xl"
                    style={{ filter: 'drop-shadow(0 20px 40px rgba(var(--color-brand-blue-primary-rgb), 0.15))' }}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Share section */}
        <div className=" bg-accent-light pb-64">
          <div className="container mx-auto px-4">
            <p
              className="text-sm mb-16 tracking-wider text-brand-blue-secondary opacity-70"
            >
              Partilhar este minicurso
            </p>
            <div className="flex flex-wrap gap-16">
              {socialLinks.map((link) => (
                <Link key={link.name} href="#" className="no-underline">
                  <Button
                    appearance="link"
                    variant="primary"
                    hasIcon={!!link.icon}
                    leadingIcon={link.icon}
                    leadingIconHover={link.icon?.replace(
                      'agora-line-',
                      'agora-solid-'
                    )}
                    className="!flex !items-center !text-neutral-700 hover:!text-primary-700 font-medium !gap-8"
                  >
                    <div className="flex items-center gap-8">
                      {!link.icon && link.customIcon && (
                        <img
                          src={link.customIcon}
                          alt=""
                          className="w-20 h-20 flex-shrink-0"
                        />
                      )}
                      <span>{link.name}</span>
                    </div>
                  </Button>
                </Link>
              ))}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
