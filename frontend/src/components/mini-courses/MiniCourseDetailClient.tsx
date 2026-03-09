'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Button, Breadcrumb, CardExpandable } from '@ama-pt/agora-design-system';
import PageBanner from '@/components/PageBanner';
import Separator from '@/components/Separator';

interface Props {
  slug?: string;
}


export default function MiniCourseDetailClient({ slug }: Props) {
  const router = useRouter();
  const [isFavorite, setIsFavorite] = useState(false);

  const handleConcluirCurso = () => {
    const base = slug
      ? `/pages/mini-courses/${slug}/conclusion`
      : 'conclusion';
    router.push(base);
  };

  const relatedCourses = [
    {
      title: 'Minicurso sobre reutilizações de dados abertos',
      description: 'Este minicurso apresenta como reutilizar dados abertos de forma prática e segura.',
      slug: 'reutilizacao-dados-abertos'
    },
    {
      title: 'Minicurso sobre Metadados',
      description: 'Este minicurso apresenta os conceitos introdutórios fundamentais dos metadados relacionados com dados abertos, explicando o que são, para que servem e porque são essenciais para a descoberta, compreensão e reutilização correta da informação.',
      slug: 'metadados'
    },
    {
      title: 'Minicurso sobre os diferentes formatos de datasets',
      description: 'Este minicurso apresenta os conceitos essenciais sobre a publicação de dados abertos no dados.gov.pt, com foco nos formatos de datasets, metadados e no modelo das 5 Estrelas dos Dados Abertos.',
      slug: 'formatos-datasets'
    }
  ];

  const socialLinks = [
    { name: 'Facebook', icon: 'agora-line-facebook', color: '#1877F2' },
    { name: 'Twitter', icon: 'agora-line-twitter', color: '#1DA1F2' },
    { name: 'LinkedIn', icon: 'agora-line-linkedin', color: '#0A66C2' },
    { name: 'WhatsApp', customIcon: '/Icons/whatsapp.svg', color: '#25D366' },
    { name: 'e-mail', icon: 'agora-line-mail', color: '#EA4335' }
  ];

  return (
    <div className="flex flex-col font-sans text-neutral-900 bg-white min-h-screen">
      <main className="flex-grow bg-white">
        <div className="bg-[#F8F9FC] py-64">
          <div className="container mx-auto px-4 lg:px-64">
            <Breadcrumb
              items={[
                { label: 'Início', url: '/' },
                { label: 'Minicursos', url: '/pages/mini-cursos' }
              ]}
              className="mb-64"
            />
            <div className="flex gap-[84px]">
              <div className="w-1/2 pr-32">
                <h1 className="text-[40px] leading-[48px] font-bold text-primary-600 mb-16">
                  Minicurso sobre a introdução aos dados abertos
                </h1>

                <div className="text-[18px] leading-[28px] space-y-16 w-[94%]">
                  <p>
                    Este mini curso apresenta as informações introdutórias fundamentais dos dados abertos, explicando o que são, para que servem e porque são importantes para a transparência, inovação e reutilização da informação.
                    As imagens utilizadas são apenas ilustrativas e podem ser substituídas ou adaptadas conforme o contexto da apresentação.
                  </p>
                </div>

                <div className="mt-64">
                  Atualizado em 30.09.2025
                </div>
              </div>
              <div className="img-container">
                <img src="/minicourses/medal.png" alt="Minicursos" className="w-[446px] h-[428px] mt-[-85px] " />
              </div>
            </div>
          </div>
        </div>

        <div className="container mx-auto px-4 py-64">
          {/* Specific Course Header Section */}


          <div className="grid md:grid-cols-3 xl:grid-cols-12 gap-32">
            {/* Main Content Column */}
            <div className="xl:col-span-6 xl:block">
              <article className="prose max-w-none text-neutral-800 space-y-48">
                <section className="mb-32">
                  <h2 className="font-bold mb-16 text-brand-blue-dark">1. O que são dados abertos?</h2>
                  <p className="text-base leading-relaxed">
                    São dados disponibilizados de forma livre, que qualquer pessoa pode aceder, utilizar, modificar e partilhar. Devem estar acessíveis sem barreiras técnicas ou legais, permitindo a sua reutilização para fins pessoais, profissionais, científicos ou comerciais.
                  </p>
                </section>

                <section className="mb-32">
                  <h2 className="font-bold mb-16 text-brand-blue-dark">2. Para que servem os dados abertos?</h2>
                  <p className="text-base leading-relaxed">
                    Os dados abertos servem para aumentar a transparência das instituições públicas e apoiar a tomada de decisões informadas. Permitem a investigação, a participação cidadã e a criação de novos serviços, aplicações e soluções inovadoras que beneficiam a sociedade.
                  </p>
                </section>

                <section className="mb-32">
                  <h2 className="font-bold mb-16 text-brand-blue-dark">3. Quem pode usar dados abertos?</h2>
                  <p className="text-base leading-relaxed">
                    Todos. O formato determina o quão fácil é aceder, reutilizar, analisar e integrar os dados noutros sistemas. Formatos inadequados podem limitar a reutilização, mesmo que os dados estejam publicamente disponíveis.
                  </p>
                </section>

                <div className="my-64 rounded-16 overflow-hidden shadow-sm border border-neutral-100 ">
                  <img
                    src="/minicourses/medal_people.png"
                    alt="Ilustração de dados abertos"
                    className="w-full h-auto"
                  />
                </div>

                <section className="mb-32">
                  <h2 className="font-bold mb-16 text-brand-blue-dark">4. Quais são as principais características dos dados abertos?</h2>
                  <p className="text-base leading-relaxed">
                    Os dados abertos devem ser facilmente acessíveis e gratuitos, sem discriminação de quem os utiliza. Devem estar completos, atualizados e disponíveis de forma a permitir a reutilização livre, garantindo utilidade, transparência e confiança na informação.
                  </p>
                </section>

                <section className="mb-32">
                  <h2 className="font-bold mb-16 text-brand-blue-dark">5. Qual a diferença entre dados públicos e dados abertos?</h2>
                  <p className="text-base leading-relaxed">
                    Dados públicos são informações disponibilizadas por entidades públicas, mas nem sempre podem ser reutilizadas. Os dados abertos, além de públicos, são disponibilizados de forma a permitir o acesso, a reutilização e a partilha livre por qualquer pessoa.
                  </p>
                </section>

                <section className="mb-32">
                  <h2 className="font-bold mb-16 text-brand-blue-dark">6. Os dados abertos devem estar disponíveis para todos em condições iguais?</h2>
                  <p className="text-base leading-relaxed">
                    Sim. O acesso aos dados abertos deve ser igual para todos, sem discriminação de pessoas, organizações ou finalidades de uso. Este princípio garante transparência, equidade e oportunidades iguais de reutilização da informação.
                  </p>
                </section>

                <section className="mb-32">
                  <h2 className="font-bold mb-16 text-brand-blue-dark">7. Os dados abertos devem estar atualizados?</h2>
                  <p className="text-base leading-relaxed">
                    Sim, para serem úteis e confiáveis, os dados abertos precisam refletir a realidade atual, permitindo decisões precisas e soluções eficazes. A atualização regular garante que empresas, cidadãos e pesquisadores possam aproveitar a informação de forma segura e eficiente.
                  </p>
                </section>

                <section className="mb-32">
                  <h2 className="font-bold mb-16 text-brand-blue-dark">8. Pode haver limites no processo de abertura de dados?</h2>
                  <p className="text-base leading-relaxed">
                    Sim. Nem todos os dados podem ser abertos, especialmente dados pessoais, sensíveis ou confidenciais. A proteção da privacidade, da segurança e do interesse público deve ser sempre garantida antes da publicação de dados abertos.
                  </p>
                </section>

                <section className="mb-32">
                  <h2 className="font-bold mb-16 text-brand-blue-dark">9. Os dados abertos podem ser reutilizados e modificados?</h2>
                  <p className="text-base leading-relaxed">
                    Sim, inclusive para fins comerciais. Podem ser usados, combinados e adaptados por qualquer pessoa, permitindo criar novos serviços, produtos e soluções inovadoras.
                  </p>
                </section>

                <section className="mb-32">
                  <h2 className="font-bold mb-16 text-brand-blue-dark">10. Como é que os dados abertos beneficiam a economia?</h2>
                  <p className="text-base leading-relaxed">
                    Os dados abertos estimulam a criação de novos serviços, produtos e empregos, e aumentam a eficiência das empresas. Estudos da UE estimam que o mercado de dados abertos poderá gerar quase 200 mil milhões de euros até 2030. Além disso, promovem inovação, melhoram decisões empresariais e fortalecem a economia digital.
                  </p>
                </section>
              </article>

              <div className="flex flex-wrap justify-end gap-16 mt-64 pt-48 border-t border-neutral-100">
                <Button
                  variant="primary"
                  appearance={isFavorite ? 'solid' : 'outline'}
                  hasIcon={true}
                  leadingIcon={isFavorite ? 'agora-solid-star' : 'agora-line-star'}
                  leadingIconHover="agora-solid-star"
                  onClick={() => setIsFavorite(!isFavorite)}
                  className="px-24 h-48"
                >
                  {isFavorite ? 'Remover dos favoritos' : 'Adicionar aos favoritos'}
                </Button>
                <Button
                  variant="primary"
                  appearance="solid"
                  hasIcon={true}
                  leadingIcon="agora-line-check-circle"
                  leadingIconHover="agora-solid-check-circle"
                  onClick={handleConcluirCurso}
                  className="px-24 h-48"
                >
                  Concluir curso
                </Button>
              </div>
            </div>


            {/* Sidebar Column */}
            <aside className="xl:col-span-6 md:pt-64 md:pl-64">
              <div className="rounded-16 p-32 sticky top-32 md:pl-64">
                <h3 className="text-lg font-medium text-neutral-700 mb-24">
                  Outros <span className="font-bold text-neutral-900">minicursos</span> relacionados
                </h3>
                <div className="flex flex-col">
                  {relatedCourses.map((course, index) => (
                    <div key={course.slug} className="group cursor-pointer">
                      <h4 className="font-bold text-neutral-900 group-hover:text-primary-700 transition-colors mb-8">
                        {course.title}
                      </h4>
                      <p className="text-sm text-brand-blue-secondary leading-relaxed">
                        {course.description}
                      </p>
                      {index < relatedCourses.length - 1 && (
                        <Separator className="my-32" />
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </aside>
          </div>

          <div className="mt-64 pt-32 md:pl-64">
            <p className="text-sm text-brand-blue-secondary mb-16 tracking-wider ">Partilhar este minicurso</p>
            <div className="flex flex-wrap gap-16">
              {socialLinks.map((link) => (
                <Link key={link.name} href="#" className="no-underline">
                  <Button
                    appearance="link"
                    variant="primary"
                    hasIcon={!!link.icon}
                    leadingIcon={link.icon}
                    leadingIconHover={link.icon?.replace('agora-line-', 'agora-solid-')}
                    className="!flex !items-center !text-neutral-700 hover:!text-primary-700 font-medium !gap-8"
                  >
                    <div className="flex items-center gap-8">
                      {!link.icon && link.customIcon && (
                        <img src={link.customIcon} alt="" className="w-20 h-20 flex-shrink-0" />
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
