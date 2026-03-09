'use client';

import React, { useState } from 'react';
import {
  Button,
  InputText,
  InputTextArea,
  RadioButton,
  Icon,
  Breadcrumb,
  Accordion,
  AccordionGroup,
  InputSelect,
  DropdownSection,
  DropdownOption,
  Stepper,
  Step,
} from '@ama-pt/agora-design-system';

export default function ApiRegistrationClient() {
  const [accessType, setAccessType] = useState('open');


  const auxiliarItems = [
    { title: 'Como dar nomes à sua API', content: 'Explore nomes claros e concisos que descrevam a função principal da sua API.' },
    { title: 'Adicione uma abreviação ou sigla à API.', content: 'Abreviações ajudam na identificação rápida em listas e dashboards.' },
    { title: 'Escreva uma boa descrição', content: 'Uma boa descrição deve resumir o que a API faz, quem a deve usar e os principais benefícios.' },
    { title: 'Defina o link correto para a API.', content: 'Use o endpoint base da sua API.' },
    { title: 'Adicione um link para a documentação da máquina.', content: 'Ficheiros como OpenAPI (Swagger) ou RAML.' },
    { title: 'Adicione um link para a documentação técnica.', content: 'Guias de integração, autenticação e exemplos de código.' },
    { title: 'Especifique o limite de chamadas', content: 'Indique o número máximo de pedidos por minuto/hora.' },
    { title: 'Indique a disponibilidade', content: 'Ex: 24/7, Dias úteis, 99.9% uptime.' },
    { title: 'Selecione um tipo de acesso', content: 'Explique a diferença entre acesso aberto, com conta ou restrito.' },
    { title: 'Adicione um link à solicitação de autorização', content: 'Onde os utilizadores podem pedir acesso se a API for restrita.' },
    { title: 'Adicione um link para a documentação da empresa.', content: 'Termos de serviço e políticas de privacidade.' },
  ];

  return (
    <div className="min-h-screen bg-white font-sans">
      <main className="container mx-auto px-16 py-32 max-w-7xl">
        {/* Breadcrumbs */}
        <div className="mb-48 border-b border-neutral-100 pb-16">
          <Breadcrumb
            items={[
              { label: 'Home', url: '/' },
              { label: 'APIs', url: '#' },
              { label: 'Formulário de inscrição', url: '#' },
            ]}
          />
        </div>

        <div className="grid grid-cols-12 gap-48">
          {/* Stepper (Left) */}
          <div className="col-span-12 lg:col-span-3">
            <div className="sticky top-120">
              <Stepper>
                <Step status="current">
                  Descreva a sua API
                </Step>
                <Step status="default">
                  Vincular conjuntos de dados
                </Step>
                <Step status="default">
                  Morada do titular
                </Step>
              </Stepper>
            </div>
          </div>

          {/* Main Content (Middle) */}
          <div className="col-span-12 lg:col-span-6">
            <h1 className="text-4xl font-bold text-[#002D72] mb-32">Descreva a sua API</h1>

            {/* Info Box: O que é uma API? */}
            <div className="bg-[#E6F0FF] rounded-8 p-32 mb-40 flex gap-20 border border-[#B3D1FF]">
              <Icon name="agora-solid-info-circle" className="text-[#002D72] w-28 h-28 flex-shrink-0" />
              <div>
                <h2 className="text-lg font-bold text-[#002D72] mb-6">O que é uma API?</h2>
                <p className="text-sm text-[#374151] leading-relaxed">
                  Uma API é uma ferramenta informática que permite que um website ou software se comunique com outro computador e troque dados.
                </p>
              </div>
            </div>

            <p className="text-sm text-[#4B5563] mb-40 italic">
              Os campos marcados com um asterisco ( * ) são obrigatórios.
            </p>

            <form className="flex flex-col gap-48">
              {/* Produtor Section */}
              <section>
                <h2 className="text-2xl font-bold text-[#111827] mb-24">Produtor</h2>
                <div className="flex flex-col gap-32">
                  <InputSelect
                    label="Verifique a identidade que deseja usar na publicação."
                    placeholder="Para pesquisar..."
                    id="producer-identity"
                  >
                    <DropdownSection name="organizations">
                      <DropdownOption value="org1">Minha Organização</DropdownOption>
                    </DropdownSection>
                  </InputSelect>

                  <div className="bg-[#F8FAFC] rounded-8 p-32 border border-[#E2E8F0]">
                    <h3 className="text-lg font-bold text-[#111827] mb-12">Você não pertence a nenhuma organização.</h3>
                    <p className="text-sm text-[#4B5563] mb-20 leading-relaxed">
                      Recomendamos que publique em nome de uma organização se se tratar de uma atividade profissional.
                    </p>
                    <a href="#" className="text-[#0052CC] font-bold text-sm flex items-center gap-8 hover:underline group">
                      Crie ou participe de uma organização
                      <Icon name="agora-line-arrow-right-circle" className="w-20 h-20 transition-transform group-hover:translate-x-4" />
                    </a>
                  </div>
                </div>
              </section>

              {/* Descrição Section */}
              <section>
                <h2 className="text-2xl font-bold text-[#111827] mb-32 border-b border-[#F3F4F6] pb-12">Descrição</h2>
                <div className="flex flex-col gap-32">
                  <InputText
                    label="Nome da API*"
                    placeholder="Placeholder"
                    id="api-name"
                  />
                  <InputText
                    label="Acrónimo"
                    placeholder="Placeholder"
                    id="api-acronym"
                  />
                  <div className="relative">
                    <InputTextArea
                      label="Descrição*"
                      placeholder="Placeholder"
                      id="api-description"
                      rows={6}
                      maxLength={246}
                    />
                    <div className="text-right text-xs text-neutral-400 mt-4">
                      123 / 246
                    </div>
                  </div>
                  <InputText
                    label="Link raiz da API"
                    placeholder="Placeholder"
                    id="api-root-link"
                  />
                  <InputText
                    label="Link para a documentação da API (arquivo OpenAPI ou Swagger)"
                    placeholder="Placeholder"
                    id="api-doc-openapi"
                  />
                  <InputText
                    label="Link para a documentação técnica da API"
                    placeholder="Placeholder"
                    id="api-doc-technical"
                  />
                  <InputText
                    label="Limite de chamadas"
                    placeholder="Placeholder"
                    id="api-rate-limit"
                  />
                  <InputText
                    label="Disponibilidade"
                    placeholder="Placeholder"
                    id="api-availability"
                  />
                </div>
              </section>

              {/* Acesso Section */}
              <section>
                <h2 className="text-2xl font-bold text-[#111827] mb-32 border-b border-[#F3F4F6] pb-12">Acesso</h2>
                <div className="flex flex-col gap-32">
                  <div className="flex flex-col gap-16">
                    <span className="text-sm font-bold text-[#374151]">Tipo de acesso</span>
                    <div className="flex flex-col gap-12">
                      <RadioButton
                        label="Abrir"
                        id="access-open"
                        name="access-type"
                        checked={accessType === 'open'}
                        onChange={() => setAccessType('open')}
                      />
                      <RadioButton
                        label="Abrir com conta"
                        id="access-account"
                        name="access-type"
                        checked={accessType === 'account'}
                        onChange={() => setAccessType('account')}
                      />
                      <RadioButton
                        label="Restrito"
                        id="access-restricted"
                        name="access-type"
                        checked={accessType === 'restricted'}
                        onChange={() => setAccessType('restricted')}
                      />
                    </div>
                  </div>
                  <InputText
                    label="Link para a ferramenta de autorização de acesso"
                    placeholder="Placeholder"
                    id="api-auth-tool"
                  />
                  <InputText
                    label="Link para a documentação comercial da API"
                    placeholder="Placeholder"
                    id="api-doc-commercial"
                  />
                </div>
              </section>

              <div className="flex justify-end mt-48 pb-64">
                <Button
                  variant="primary"
                  className="px-48 h-56 rounded-8 text-lg font-bold shadow-lg shadow-primary-100"
                  hasIcon
                  trailingIcon="agora-line-arrow-right-circle"
                >
                  Seguinte
                </Button>
              </div>
            </form>
          </div>

          {/* Auxiliar (Right) */}
          <div className="col-span-12 lg:col-span-3">
            <div className="sticky top-120 bg-[#F9FAFB] rounded-8 p-24 border border-[#F1F5F9]">
              <div className="flex items-center gap-10 mb-32 text-[#002D72]">
                <Icon name="agora-line-help-support" className="w-24 h-24" />
                <h2 className="text-xl font-bold">Auxiliar</h2>
              </div>
              <AccordionGroup>
                {auxiliarItems.map((item, idx) => (
                  <Accordion key={idx} headingTitle={item.title} headingLevel="h3">
                    <div className="py-12 text-sm text-[#4B5563] leading-relaxed">
                      {item.content}
                    </div>
                  </Accordion>
                ))}
              </AccordionGroup>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
