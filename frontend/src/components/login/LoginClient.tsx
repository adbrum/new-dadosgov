'use client';

import React, { useState } from 'react';
import NextImage from 'next/image';
import {
  Button,
  RadioButton,
  Checkbox,
  Icon,
  Breadcrumb,
  Tabs,
  Tab,
  TabHeader,
  TabBody,
} from '@ama-pt/agora-design-system';

export default function LoginClient() {
  const [isHovered, setIsHovered] = useState(false);
  const breadcrumbItems = [
    { label: 'Home', url: '/' },
    { label: 'Autenticação', url: '#' },
  ];

  return (
    <main className="flex-grow bg-white min-h-screen">
      <div className="container mx-auto px-16 py-32 max-w-7xl">
        {/* Breadcrumb */}
        <div>
          <Breadcrumb items={breadcrumbItems} />
        </div>

        {/* Title Section */}
        <div>
          <h1 className="text-32 font-bold text-brand-blue-dark mt-64 mb-16">
            Autenticação
          </h1>
          <p className="text-lg text-gray-medium max-w-2xl mb-32">
            Escolha um meio de autenticação para se autenticar no portal e ter acesso aos vários <br />
            serviços e funcionalidades online.
          </p>
        </div>

        {/* Main Content with Vertical Tabs */}
        <Tabs vertically className="mt-24">
          <Tab>
            <TabHeader>Chave Móvel Digital (CMD)</TabHeader>
            <TabBody>
              <div className="p-64 rounded-8">
                <div className="flex flex-col gap-40">
                  <div className="grid mt-32 gap-32 xs:grid-cols-4 md:grid-cols-8 xl:grid-cols-12">
                    <div className="xs:col-span-4 md:col-span-5 xl:col-span-7">
                      <div className="bg-[#E9EBFF] p-12 rounded-8 w-fit">
                        <Icon name="agora-line-user" className="w-24 h-24 text-brand-blue-primary" />
                      </div>
                      <div>
                        <h2 className="text-24 font-bold text-brand-blue-dark mb-8">Para se autenticar</h2>
                        <p className="">
                          Precisa do código PIN da sua CMD e do telemóvel que lhe está associado.
                        </p>
                      </div>
                    </div>
                    <div className="xs:col-span-4 md:col-span-3 xl:col-span-5 flex items-center justify-start md:justify-end">
                      <div className="w-[278px] md:flex md:justify-end xl:flex xl:justify-end">
                        <NextImage
                          src="/Logos/autenticacao_gov.svg"
                          alt="Autenticação.gov"
                          width={240}
                          height={48}
                          className="h-48 w-auto"
                        />
                      </div>

                    </div>
                  </div>

                  <div className="w-full h-[2px] bg-neutral-200 mt-32 mb-16"></div>

                  <div className="flex flex-col gap-24">
                    <div className="flex flex-col gap-16">
                      <RadioButton
                        label="Cidadão nacional"
                        id="nacional"
                        name="citizen-type"
                        defaultChecked
                        className="text-lg"
                      />
                      <RadioButton
                        label="Cidadão estrangeiro"
                        id="estrangeiro"
                        name="citizen-type"
                        className="text-lg"
                      />
                    </div>

                    <div className="mt-8">
                      <Checkbox
                        label="Declaro que li e aceito os termos e condições para o tratamento dos meus dados pessoais no acesso e utilização da Área Reservada do dadosgov.pt"
                        id="terms"
                        className="text-sm text-neutral-700 leading-relaxed"
                      />
                    </div>
                  </div>

                  <div className="mt-16">
                    <Button
                      variant="primary"
                      className="px-48 h-56 rounded-8 text-lg font-bold shadow-md hover:shadow-lg transition-all"
                      hasIcon={true}
                      trailingIcon={isHovered ? "agora-solid-arrow-right-circle" : "agora-line-arrow-right-circle"}
                      onMouseEnter={() => setIsHovered(true)}
                      onMouseLeave={() => setIsHovered(false)}
                    >
                      Autenticar com CMD
                    </Button>
                  </div>
                </div>
              </div>
            </TabBody>
          </Tab>
          <Tab>
            <TabHeader>Autenticação europeia (eIDAS)</TabHeader>
            <TabBody>
              <div className=" p-64 rounded-8 flex flex-col items-center justify-center text-center">
                <Icon name="agora-line-globe" className="w-64 h-64 text-brand-blue-primary mb-24" />
                <h2 className="text-2xl font-bold text-brand-blue-dark mb-16">Autenticação europeia (eIDAS)</h2>
                <p className="text-neutral-600 max-w-md">
                  Utilize os seus meios de autenticação de outros estados-membros da União Europeia.
                </p>
              </div>
            </TabBody>
          </Tab>
          <Tab>
            <TabHeader>Iniciar sessão</TabHeader>
            <TabBody>
              <div className="p-64 rounded-8 flex flex-col items-center justify-center text-center">
                <Icon name="agora-line-lock" className="w-64 h-64 text-brand-blue-primary mb-24" />
                <h2 className="text-2xl font-bold text-brand-blue-dark mb-16">Iniciar sessão</h2>
                <p className="text-neutral-600 max-w-md">
                  Utilize as suas credenciais do portal dados.gov para iniciar sessão.
                </p>
              </div>
            </TabBody>
          </Tab>
        </Tabs>
      </div>
    </main>
  );
}
