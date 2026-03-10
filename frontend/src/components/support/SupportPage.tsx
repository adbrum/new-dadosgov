'use client';

import React from 'react';
import { Icon, Accordion, AccordionGroup, CardLinks, ButtonGroup, Button, InputSearchBar } from '@ama-pt/agora-design-system';
import PageBanner from '@/components/PageBanner';

const FAQ_DATA = [
  {
    category: "Negócios",
    items: [
      {
        question: "Seus dados estão visíveis no banco de dados Sirene e você deseja torná-los privados?",
        answer: "Informações sobre como tornar seus dados privados no banco de dados Sirene."
      },
      {
        question: "Você está procurando seu número SIRET, SIREN ou RNA?",
        answer: "Se você está procurando o seu número SIRET ou SIREN, pode visitar o site do Diretório Comercial. Se você representa uma associação e está procurando seu número de registro (RNA), pode consultar o mecanismo de busca de associações do Diário Oficial (pelo qual não nos responsabilizamos). Para mais informações, visite o site Serviço-Público.pt.",
        defaultExpanded: true
      },
      {
        question: "Tem alguma dúvida sobre uma organização de treinamento ou uma certificação Qualiopi?",
        answer: "Informações sobre organizações de treinamento e certificação Qualiopi."
      }
    ]
  },
  {
    category: "Dados fundiários, cadastro e endereços",
    items: [
      {
        question: "Você tem alguma dúvida sobre o aplicativo DVF (solicitações de valor de terreno)?",
        answer: "Informações sobre o aplicativo DVF."
      },
      {
        question: "Você tem alguma pergunta sobre o registro de imóveis?",
        answer: "Informações sobre o registro de imóveis."
      },
      {
        question: "Notei um erro na planta cadastral. Como posso corrigi-lo?",
        answer: "Instruções para corrigir erros na planta cadastral."
      },
      {
        question: "O que posso fazer com os dados?",
        answer: "Informações sobre permissões e usos dos dados."
      },
      {
        question: "Tem alguma dúvida sobre o banco de dados nacional de endereços? Algum endereço está incorreto?",
        answer: "Informações sobre o banco de dados nacional de endereços."
      }
    ]
  },
  {
    category: "APIs públicas",
    items: [
      {
        question: "Você tem alguma dúvida sobre os limites de chamadas da API de particionamento administrativo (API Geográfica)?",
        answer: "Informações sobre limites de chamadas da API Geográfica."
      },
      {
        question: "Você está procurando uma API ou um banco de dados de placas de veículos, carteiras de habilitação ou documentos de registro de veículos?",
        answer: "Informações sobre dados de veículos e habilitação."
      },
      {
        question: "Você está procurando a API de Serviços de Terceiros para se beneficiar do regime de pagamento antecipado imediato do crédito fiscal para \"serviços pessoais\"?",
        answer: "Informações sobre a API de Serviços de Terceiros."
      },
      {
        question: "Você está enfrentando algum problema com o DataPass?",
        answer: "Suporte para problemas com o DataPass."
      }
    ]
  },
  {
    category: "Outros dados",
    items: [
      {
        question: "Você tem alguma dúvida sobre o diretório nacional de infraestrutura de recarga para veículos elétricos (EVCI)?",
        answer: "Informações sobre o infraestrutura de recarga EVCI."
      },
      {
        question: "Você tem alguma pergunta sobre dados relacionados à COVID-19?",
        answer: "Informações sobre dados da COVID-19."
      }
    ]
  },
  {
    category: "Outras perguntas frequentes",
    items: [
      {
        question: "Tem alguma dúvida sobre seus dados pessoais?",
        answer: "Informações sobre tratamento de dados pessoais."
      },
      {
        question: "Você tem alguma dúvida sobre autorização de residência?",
        answer: "Informações sobre autorização de residência."
      },
      {
        question: "Você tem alguma dúvida ou já foi vítima de fraude ou golpe?",
        answer: "Informações e suporte para casos de fraude."
      },
      {
        question: "Você tem alguma dúvida sobre a conta de formação profissional (CPF)?",
        answer: "Informações sobre a conta de formação profissional."
      }
    ]
  }
];

const SupportPage = () => {
  return (
    <main className="flex-grow bg-white pb-64">
      <PageBanner
        title={
          <>
            <span className="xs:text-xl-light md:text-2xl-light xl:text-2xl-light text-white">
              Bem-vindo à página de suporte da
            </span>
            <span className="xs:text-xl-light md:text-2xl-light xl:text-2xl-light text-white">
              plataforma data.gov
            </span>
          </>
        }
        breadcrumbItems={[
          { label: 'Home', url: '/' },
          { label: 'Apoiar', url: '#' }
        ]}
        backgroundImageUrl="/Banner/hero-bg.png"
        backgroundPosition="center right"
        subtitle={
          <>
            <label className="block text-[20px] font-bold text-white mt-[48px]">Antes de nos contactar, consulte o fórum e os nossos guias:<br />poderá já encontrar a resposta à sua pergunta lá!</label>

            <div className="absolute w-full mb-64 bg-white text-neutral-900 shadow-lg dropdown"></div>

            <div className="mt-[16px] flex flex-wrap gap-[32px]">
              <a href="#" target="_blank" rel="noopener noreferrer" className="flex items-center gap-8 text-white cursor-pointer hover:underline">
                Consulte a documentação em data.gov.pt
                <svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" className="icon icon-m fill-white w-32 h-32" aria-hidden="true" role="img"><path d="M11.2929 8.70711C10.9024 8.31658 10.9024 7.68342 11.2929 7.29289C11.6834 6.90237 12.3166 6.90237 12.7071 7.29289L16.7071 11.2929C17.0976 11.6834 17.0976 12.3166 16.7071 12.7071L12.7071 16.7071C12.3166 17.0976 11.6834 17.0976 11.2929 16.7071C10.9024 16.3166 10.9024 15.6834 11.2929 15.2929L13.5858 13H8C7.44772 13 7 12.5523 7 12C7 11.4477 7.44772 11 8 11H13.5858L11.2929 8.70711Z"></path><path fillRule="evenodd" clip-rule="evenodd" d="M12 1C5.92487 1 1 5.92487 1 12C1 18.0751 5.92487 23 12 23C18.0751 23 23 18.0751 23 12C23 5.92487 18.0751 1 12 1ZM3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12Z"></path></svg>
              </a>

              <a href="#" target="_blank" rel="noopener noreferrer" className="flex items-center gap-8 text-white cursor-pointer hover:underline">
                Consulte os guias sobre dados abertos
                <svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" className="icon icon-m fill-white w-32 h-32" aria-hidden="true" role="img"><path d="M11.2929 8.70711C10.9024 8.31658 10.9024 7.68342 11.2929 7.29289C11.6834 6.90237 12.3166 6.90237 12.7071 7.29289L16.7071 11.2929C17.0976 11.6834 17.0976 12.3166 16.7071 12.7071L12.7071 16.7071C12.3166 17.0976 11.6834 17.0976 11.2929 16.7071C10.9024 16.3166 10.9024 15.6834 11.2929 15.2929L13.5858 13H8C7.44772 13 7 12.5523 7 12C7 11.4477 7.44772 11 8 11H13.5858L11.2929 8.70711Z"></path><path fillRule="evenodd" clip-rule="evenodd" d="M12 1C5.92487 1 1 5.92487 1 12C1 18.0751 5.92487 23 12 23C18.0751 23 23 18.0751 23 12C23 5.92487 18.0751 1 12 1ZM3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12Z"></path></svg>
              </a>

              <a href="#" target="_blank" rel="noopener noreferrer" className="flex items-center gap-8 text-white cursor-pointer hover:underline">
                Consulte os guias sobre como usar os dados
                <svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" className="icon icon-m fill-white w-32 h-32" aria-hidden="true" role="img"><path d="M11.2929 8.70711C10.9024 8.31658 10.9024 7.68342 11.2929 7.29289C11.6834 6.90237 12.3166 6.90237 12.7071 7.29289L16.7071 11.2929C17.0976 11.6834 17.0976 12.3166 16.7071 12.7071L12.7071 16.7071C12.3166 17.0976 11.6834 17.0976 11.2929 16.7071C10.9024 16.3166 10.9024 15.6834 11.2929 15.2929L13.5858 13H8C7.44772 13 7 12.5523 7 12C7 11.4477 7.44772 11 8 11H13.5858L11.2929 8.70711Z"></path><path fillRule="evenodd" clip-rule="evenodd" d="M12 1C5.92487 1 1 5.92487 1 12C1 18.0751 5.92487 23 12 23C18.0751 23 23 18.0751 23 12C23 5.92487 18.0751 1 12 1ZM3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12Z"></path></svg>
              </a>
            </div>
          </>
        }
      />



      <div className="container mx-auto px-4 py-64">
        <div className="grid md:grid-cols-2 gap-32 mb-64">
        </div>

        {/* FAQ Section */}
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl-bold mb-48">Perguntas frequentes</h2>

          <div className="space-y-48">
            {FAQ_DATA.map((category, idx) => (
              <section key={idx}>
                <h3 className="text-lg-bold text-primary-700 mb-24">{category.category}</h3>
                <AccordionGroup>
                  {category.items.map((item, itemIdx) => (
                    <Accordion
                      key={itemIdx}
                      headingTitle={item.question}
                      headingLevel="h4"
                      defaultExpanded={item.defaultExpanded}
                    >
                      <div className="py-16 text-neutral-700 leading-relaxed">
                        {item.answer}
                      </div>
                    </Accordion>
                  ))}
                </AccordionGroup>
              </section>
            ))}
          </div>
        </div>

        {/* Bottom Support Options */}
        <div className="mt-80 pt-64 border-t border-neutral-200">
          <h2 className="text-2xl-bold mb-16">Ajuda</h2>
          <h3 className="text-xl-bold mb-48">Não encontrou o que procurava??</h3>

          <ButtonGroup fullWidth={true}>
            <Button
              variant="primary"
              appearance="outline"
              leadingIcon="agora-line-question-mark"
              leadingIconHover="agora-solid-question-mark"
              hasIcon={true}
            >
              Tenho uma pergunta
            </Button>
            <Button
              variant="primary"
              appearance="outline"
              leadingIcon="agora-line-help-support"
              leadingIconHover="agora-solid-help-support"
              hasIcon={true}
            >
              Solicitação de Dados
            </Button>
            <Button
              variant="primary"
              appearance="outline"
              leadingIcon="agora-line-alert-triangle"
              leadingIconHover="agora-solid-alert-triangle"
              hasIcon={true}
            >
              Enviar um bug
            </Button>
            <Button
              variant="primary"
              appearance="outline"
              leadingIcon="agora-line-chat"
              leadingIconHover="agora-solid-chat"
              hasIcon={true}
            >
              Envie seu feedback em data.gov.pt
            </Button>
          </ButtonGroup>
        </div>
      </div>
    </main>
  );
};

export default SupportPage;
