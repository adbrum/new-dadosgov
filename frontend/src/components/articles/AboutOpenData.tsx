'use client';

import React from 'react';
import Link from 'next/link';
import { Breadcrumb, Icon, CardArticle, Button } from '@ama-pt/agora-design-system';

const AboutOpenData = () => {
  const relatedArticles = [
    {
      date: '01 de agosto de 2025',
      title: 'Title text lorem ipsum dolor',
      image: '/Articles/last-new1.svg'
    },
    {
      date: '01 de agosto de 2025',
      title: 'Title text lorem ipsum dolor',
      image: '/Articles/last-new2.svg'
    },
    {
      date: '01 de agosto de 2025',
      title: 'Title text lorem ipsum dolorTitle text lorem ipsum dolorTitle text lorem ipsum dolor',
      image: '/Articles/last-new3.svg'
    }
  ];

  const socialLinks = [
    { name: 'Facebook', icon: 'agora-line-facebook', href: '#' },
    { name: 'Twitter', icon: 'agora-line-twitter', href: '#' },
    { name: 'LinkedIn', icon: 'agora-line-linkedin', href: '#' },
    { name: 'WhatsApp', customIcon: '/Icons/whatsapp.svg', href: '#' },
    { name: 'e-mail', icon: 'agora-line-mail', href: '#' }
  ];

  return (
    <div className="flex flex-col bg-white min-h-screen font-sans">
      <main className="flex-grow pt-32 pb-64">
        <div className="container mx-auto px-4">
          {/* Breadcrumbs */}
          <div className="mb-48">
            <Breadcrumb
              items={[
                { label: 'Início', url: '/' },
                { label: 'Conhecimento', url: '#' },
                { label: 'Sobre dados abertos', url: '/pages/about-open-data' }
              ]}
            />
          </div>

          {/* Hero Section */}
          <div className="mb-64">
            <span className="text-neutral-600 text-m-regular block mb-16">
              Publicado em 18.12.2025
            </span>
            <h1 className="text-2xl-bold md:text-3xl-bold text-primary-900 mb-24 leading-tight max-w-[800px]">
              Sobre dados abertos
            </h1>
            <p className="text-xl-light text-neutral-700 max-w-[592px]">
              Descubra como os dados abertos estão a transformar a transparência pública e a inovação em Portugal.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-64">
            {/* Main Content */}
            <div className="lg:col-span-8">
              <div className="text-neutral-800 space-y-48">
                <div className="max-w-[592px]">
                  <h2 className="text-l-bold text-primary-900 mb-16">Conjuntos de dados abertos</h2>
                  <p className="text-m-regular mb-16 italic text-neutral-600 border-l-2 border-primary-200 pl-16">
                    Um conjunto de dados, publicados ou geridos por um único agente, e disponibilizado para acesso ou download através de um ou mais formatos.
                    <br />
                    <span className="text-s-regular">— W3C Data Catalogue Vocabulary (DCAT)</span>
                  </p>
                  <p className="text-m-regular mb-16">
                    Conjuntos de dados, no contexto dos dados abertos públicos, são agrupamentos de dados em formato digital, dedicados a um tema específico. Uma lista de moradas de serviços de atendimento ao público, por exemplo, ou dados mensais sobre práticas de gestão ou contratação de um organismo público.
                  </p>
                </div>

                <div className="max-w-[592px]">
                  <h2 className="text-l-bold text-primary-900 mb-16">Dados sem restrições de reutilização</h2>
                  <p className="text-m-regular mb-16">
                    Um dos pontos fundamentais dos dados abertos é a ideia de que qualquer pessoa ou entidade pode utilizar, transformar ou adaptar os dados públicos para rentabilizar num contexto de negócio.
                  </p>
                  <p className="text-m-regular mb-16">
                    Quando falamos em dados abertos públicos, podemos considerar dados relativos a: contratação pública, gestão de organismos públicos, estatísticas económicas e financeiras, despesas e receitas públicas, resultados eleitorais, georreferenciação de moradas e serviços públicos, horários de transportes, indicadores de qualidade de serviço, entre muitos outros.
                  </p>
                  <p className="text-m-regular mb-16">
                    Grande parte desta informação pode até já estar disponível publicamente, mas para que um determinado conjunto de dados governamentais possa ser classificado como Aberto é necessário que não existam restrições ao seu acesso, sejam estas legais ou políticas, tecnológicas ou financeiras.
                  </p>
                  <p className="text-m-regular mb-16">
                    Assim, distingue-se dados abertos de dados que sejam apenas disponibilizados ao público. Os dados abertos são sempre abrangidos por licenças abertas, que permitem reutilização comercial. Se assim não for – não poderão ser considerados dados abertos.
                  </p>
                </div>

                <div className="max-w-[592px]">
                  <h2 className="text-l-bold text-primary-900 mb-16">Privacidade e dados abertos</h2>
                  <p className="text-m-regular mb-16">
                    Nem toda a informação do sector público deve ser tornada pública. Há um vasto conjunto de dados na Administração Pública que deve continuar na esfera de acesso restrito, seja por razões de segurança, razões legais, ou direito à privacidade dos cidadãos. As políticas de dados abertos não estipulam que se “abra” toda a informação do Estado, apenas aquela que pode ser considerada pública.
                  </p>
                  <p className="text-m-regular mb-16">
                    As considerações relativamente à abertura de dados de sectores específicos cabem às entidades que os gerem em consonância com organismos como a Comissão Nacional de Proteção de Dados.
                  </p>
                  <p className="text-m-regular mb-16">
                    Quando se fala de dados abertos fala-se sobretudo em dados governamentais que já estão ou deveriam estar disponíveis para a sociedade e que, assim, têm o potencial de se tornarem abertos, garantindo sua reutilização em novos projetos.
                  </p>
                </div>

                <div className="max-w-[592px]">
                  <h2 className="text-l-bold text-primary-900 mb-16">Como identificar conjuntos de dados para publicação?</h2>
                  <p className="text-m-regular mb-16">
                    No caso de não existirem ainda vários conjuntos de dados delimitados e estruturados num organismo, que possam ser imediatamente abertos, podemos começar por abrir apenas um subconjunto desses dados.
                  </p>
                  <p className="text-m-regular mb-24">
                    Podemos começar por considerar disponibilizar informação que já está disponível ao público, seja sob a forma de conteúdos num site ou através de pedidos à organização, sob a forma menos "tratada" de conjuntos de dados. Aqui é patente a vantagem de disponibilizar dados em bruto, em formatos abertos e lidos por máquina, de forma a privilegiar a sua reutilização de forma livre.
                  </p>
                  <p className="text-m-semibold mb-16">
                    Regra geral, são especialmente apreciados pelos reutilizadores de dados que privilegiem preocupações como:
                  </p>
                  <ul className="list-disc pl-24 space-y-12 mb-24">
                    <li>Acesso às entidades, serviços disponíveis e pontos de atendimento;</li>
                    <li>Transparência das contas, atividades e recursos da entidade;</li>
                    <li>Monitorização de um tema, setor ou área de interesse público.</li>
                  </ul>
                  <p className="text-m-regular mb-16">
                    É muito importante estabelecer também um compromisso de manutenção e atualização dos dados. Nesse sentido, e embora o esforço inicial seja um pouco mais elevado, é recomendável a utilização de mecanismos automatizados (ex. API), para garantir que o processo decorra de forma regular.
                  </p>
                </div>

                <div className="max-w-[592px]">
                  <h3 className="text-m-bold text-primary-900 mb-16">Dados com informação geográfica</h3>
                  <p className="text-m-regular mb-16">
                    Nos dados a abrir deverá ser dedicada uma atenção e esforço especiais à georreferenciação da informação, porque eleva significativamente o interesse e o potencial de utilização dos dados abertos. Ao enriquecer um conjunto de dados com campos de referência geográfica, a entidade está a abrir o potencial para o desenvolvimento de aplicações que permitem visualizar os dados sobre um mapa.
                  </p>
                </div>

                <div className="max-w-[592px]">
                  <h3 className="text-m-bold text-primary-900 mb-16">Interagir com os reutilizadores</h3>
                  <p className="text-m-regular mb-16">
                    A interação com a comunidade de reutilizadores poderá fornecer pistas preciosas sobre o tipo de dados a disponibilizar.
                  </p>
                  <p className="text-m-regular">
                    O organismo poderá fazer algum tipo de consulta pública e perguntar aos seus interlocutores mais frequentes, ou a outras partes interessadas, a que tipo de dados gostaria de ter acesso.
                  </p>
                </div>

                <div className="max-w-[592px] pt-32">
                  <p className="text-m-regular">
                    A ARTE também poderá ajudar neste processo, incluindo colaborar na organização de workshops / eventos com vista a promover estas interações, contacte-nos em <Link href="mailto:dados@ama.pt" className="text-primary-600 underline font-medium hover:text-primary-700">dados@ama.pt</Link>.
                  </p>
                </div>

                {/* Newsletter Box */}
                <div className="bg-[#F2F2F2] rounded-16 p-32 md:p-48 mt-64 relative overflow-hidden">
                  {/* Background Icon 'A' decoration */}
                  <div className="absolute right-0 bottom-0 opacity-10 pointer-events-none transform translate-x-1/4 translate-y-1/4">
                    <Icon name="agora-solid-agora" className="w-[300px] h-[300px] text-primary-900" />
                  </div>

                  <div className="relative z-10">
                    <h3 className="text-xl-bold text-primary-900 mb-16">Fique a par das novidades</h3>
                    <p className="text-m-regular text-neutral-700 mb-32 max-w-[480px]">
                      Subscreva a nossa newsletter para receber atualizações sobre novos conjuntos de dados, eventos e histórias de reutilização.
                    </p>

                    <div className="flex flex-col gap-16">
                      <label htmlFor="email" className="text-s-bold text-neutral-900">O seu email</label>
                      <div className="flex flex-col sm:flex-row gap-16">
                        <input
                          type="email"
                          id="email"
                          placeholder="Introduza o seu email"
                          className="flex-grow h-48 px-16 rounded-8 border border-neutral-300 focus:outline-none focus:ring-2 focus:ring-primary-600 bg-white"
                        />
                        <Button
                          variant="primary"
                          className="h-48 w-48 p-0 flex items-center justify-center rounded-8"
                        >
                          <Icon name="agora-line-paper-plane" className="w-24 h-24" />
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Social Sharing */}
                <div className="pt-48 border-t border-neutral-200">
                  <span className="text-s-regular text-neutral-600 block mb-24">Partilhar esta notícia</span>
                  <div className="flex flex-wrap gap-24 md:gap-32">
                    {socialLinks.map((link) => (
                      <Link key={link.name} href={link.href} className="flex items-center gap-8 text-primary-600 hover:text-primary-700 transition-colors">
                        {link.icon ? (
                          <Icon name={link.icon as any} className="w-20 h-20" aria-hidden="true" />
                        ) : (
                          <img src={link.customIcon} alt="" className="w-20 h-20" />
                        )}
                        <span className="text-s-bold">{link.name}</span>
                      </Link>
                    ))}
                  </div>
                </div>
              </div>
            </div>

          </div>
        </div>
      </main>
    </div>
  );
};

export default AboutOpenData;
