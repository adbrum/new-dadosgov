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
  InputText,
  InputPassword,
} from '@ama-pt/agora-design-system';

export default function LoginClient() {
  const [isHovered, setIsHovered] = useState(false);
  const [isHoveredEidas, setIsHoveredEidas] = useState(false);
  const breadcrumbItems = [
    { label: 'Home', url: '/' },
    { label: 'Autenticação', url: '#' },
  ];

  return (
    <main className="flex-grow bg-white min-h-screen">
      <div className="container mx-auto px-16 pt-32 pb-64 max-w-7xl login-page">
        {/* Breadcrumb */}
        <div>
          <Breadcrumb items={breadcrumbItems} />
        </div>

        {/* Title Section */}
        <div>
          <h1 className="text-2xl-medium text-brand-blue-dark mt-64 mb-16">
            Autenticação
          </h1>
          <p className="text-lg text-neutral-700 max-w-2xl mb-32">
            Escolha um meio de autenticação para se autenticar no portal e ter acesso aos vários <br />
            serviços e funcionalidades online.
          </p>
        </div>

        {/* Main Content with Vertical Tabs */}
        <Tabs vertically className="mt-24">
          <Tab>
            <TabHeader>Chave Móvel Digital (CMD)</TabHeader>
            <TabBody>
              <div className="rounded-8">
                <div className="flex flex-col gap-40">
                  <div className="grid mt-32 gap-32 xs:grid-cols-4 md:grid-cols-8 xl:grid-cols-12">
                    <div className="xs:col-span-4 md:col-span-5 xl:col-span-7">
                      <div className="bg-[#E9EBFF] rounded-8 w-fit p-16 mb-32">
                        <Icon name="agora-line-user" className="w-24 h-24 text-brand-blue-primary" />
                      </div>
                      <div>
                        <h2 className="text-xl-bold text-brand-blue-dark mb-8">Para se autenticar</h2>
                        <p className="text-[#2B363C]">
                          Precisa do código PIN da sua CMD e do telemóvel que lhe está associado.
                        </p>
                      </div>
                    </div>
                    <div className="xs:col-span-4 md:col-span-3 xl:col-span-5 flex items-center justify-start md:justify-end">
                      <div className="w-[278px] md:flex md:justify-end xl:flex xl:justify-end mt-32">
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

                  <div className="w-full h-[2px] bg-neutral-400 mt-32 mb-16"></div>

                  <div className="flex flex-col gap-24">
                    <div className="flex flex-col gap-16">
                      <RadioButton
                        label="Cidadã/o nacional"
                        id="nacional"
                        name="citizen-type"
                        defaultChecked
                        className="text-lg text-neutral-900"
                      />
                      <RadioButton
                        label="Cidadã/o estrangeira/o"
                        id="estrangeiro"
                        name="citizen-type"
                        className="text-lg text-neutral-900"
                      />
                    </div>

                    <div className="mt-8">
                      <Checkbox
                        label="Declaro que li e aceito os termos e condições para o tratamento dos meus dados pessoais no acesso e utilização da Área Reservada do dadosgov.pt"
                        id="terms-cmd"
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
              <div className="rounded-8">
                <div className="flex flex-col gap-40">
                  <div className="grid mt-32 gap-32 xs:grid-cols-4 md:grid-cols-8 xl:grid-cols-12">
                    <div className="xs:col-span-4 md:col-span-5 xl:col-span-7">
                      <div className="bg-[#E9EBFF] rounded-8 w-fit p-16 mb-32">
                        <Icon name="agora-line-globe" className="w-24 h-24 text-brand-blue-primary" />
                      </div>
                      <div>
                        <h2 className="text-xl-bold text-brand-blue-dark mb-8">Para se autenticar</h2>
                        <p className="text-neutral-900">
                          Precisa de ter um meio de autenticação digital disponibilizado pelo seu país de origem na União Europeia (UE). Este meio de autenticação está disponível para a qualquer cidadã/o da UE.
                        </p>
                      </div>
                    </div>
                    <div className="xs:col-span-4 md:col-span-3 xl:col-span-5 flex items-center justify-start md:justify-end">
                      <div className="w-[278px] md:flex md:justify-end xl:flex xl:justify-end mt-32">
                        <NextImage
                          src="/eidas.svg"
                          alt="eIDAS"
                          width={240}
                          height={48}
                          className="h-48 w-auto"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="w-full h-[2px] bg-neutral-400 mt-32 mb-16"></div>

                  <div className="flex flex-col gap-24">
                    <div className="mt-8">
                      <Checkbox
                        label="Declaro que li e aceito os termos e condições para o tratamento dos meus dados pessoais no acesso e utilização da Área Reservada do dadosgov.pt"
                        id="terms-eidas"
                        className="text-sm text-neutral-700 leading-relaxed"
                      />
                    </div>
                  </div>

                  <div className="mt-16">
                    <Button
                      variant="primary"
                      className="px-48 h-56 rounded-8 text-lg font-bold shadow-md hover:shadow-lg transition-all"
                      hasIcon={true}
                      trailingIcon={isHoveredEidas ? "agora-solid-arrow-right-circle" : "agora-line-arrow-right-circle"}
                      onMouseEnter={() => setIsHoveredEidas(true)}
                      onMouseLeave={() => setIsHoveredEidas(false)}
                    >
                      Autenticar com eIDAS
                    </Button>
                  </div>
                </div>
              </div>
            </TabBody>
          </Tab>
          <Tab>
            <TabHeader>Iniciar sessão</TabHeader>
            <TabBody>
              <div className="rounded-8">
                <div className="flex flex-col gap-32 max-w-[560px] mt-32">
                  <div>
                    <h2 className="text-24 font-bold text-brand-blue-dark mb-8">Utilize as suas credenciais</h2>
                    <p className="text-neutral-700">
                      Introduza o seu email e senha para aceder ao portal.
                    </p>
                  </div>

                  <form className="flex flex-col gap-24" onSubmit={(e) => e.preventDefault()}>
                    <InputText
                      label="Endereço de email *"
                      placeholder="seu@email.pt"
                      id="login-email"
                      name="email"
                      type="email"
                      className="w-full"
                    />

                    <div className="flex flex-col gap-8">
                      <InputPassword
                        label="Senha *"
                        placeholder="Introduza a sua senha"
                        id="login-password"
                        name="password"
                        className="w-full"
                      />
                      <div className="flex justify-end">
                        <a href="#" className="text-sm text-brand-blue-primary hover:underline font-medium">
                          Esqueceu-se da sua senha?
                        </a>
                      </div>
                    </div>

                    <div className="flex items-center">
                      <Checkbox
                        label="Lembrar-me neste dispositivo"
                        id="remember-me"
                        name="remember-me"
                      />
                    </div>

                    <div className="mt-8">
                      <Button
                        variant="primary"
                        type="submit"
                        className="px-48 h-56 rounded-8 text-lg font-bold shadow-md hover:shadow-lg transition-all"
                      >
                        Iniciar sessão
                      </Button>
                    </div>
                  </form>
                </div>
              </div>
            </TabBody>
          </Tab>
        </Tabs>
      </div>
    </main>
  );
}
