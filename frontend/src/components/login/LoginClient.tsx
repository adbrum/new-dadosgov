"use client";

import React, { useState } from "react";
import NextImage from "next/image";
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
} from "@ama-pt/agora-design-system";
import { fetchCsrfToken, login } from "@/services/api";
import { useRouter } from "next/navigation";

export default function LoginClient() {
  const router = useRouter();
  const [isHovered, setIsHovered] = useState(false);
  const [isHoveredEidas, setIsHoveredEidas] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const breadcrumbItems = [
    { label: "Home", url: "/" },
    { label: "Autenticação", url: "#" },
  ];

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    const formData = new FormData(e.currentTarget);
    const email = formData.get("email") as string;
    const password = formData.get("password") as string;

    if (!email || !password) {
      setError("Por favor, preencha todos os campos obrigatórios.");
      setIsLoading(false);
      return;
    }

    try {
      // 1. Get CSRF Token
      const csrfToken = await fetchCsrfToken();

      // 2. Prepare payload for backend
      const payload = new FormData();
      payload.append("email", email);
      payload.append("password", password);
      payload.append("csrf_token", csrfToken);

      // 3. Login
      const response = await login(payload);

      // 4. Redirect on success
      router.push(response.redirect || "/");
      router.refresh();
    } catch (err: any) {
      console.error("Login error:", err);
      setError(err.message || "Ocorreu um erro ao tentar iniciar sessão.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="flex-grow bg-white min-h-screen">
      <div className="container mx-auto px-16 pt-32 pb-64 max-w-7xl login-page">
        {/* Breadcrumb */}
        <div>
          <Breadcrumb items={breadcrumbItems} />
        </div>

        {/* Title Section */}
        <div>
          <h1 className="text-2xl-medium text-brand-blue-dark mt-64 mb-16">Autenticação</h1>
          <p className="text-lg text-neutral-700 max-w-2xl mb-32">
            Escolha um meio de autenticação para se autenticar no portal e ter acesso aos vários{" "}
            <br />
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
                  <div className="grid gap-32 xs:grid-cols-4 md:grid-cols-8 xl:grid-cols-12">
                    <div className="xs:col-span-4 md:col-span-5 xl:col-span-7">
                      <div className="bg-[#E9EBFF] rounded-8 w-fit p-16 mb-32">
                        <Icon
                          name="agora-line-user"
                          className="w-24 h-24 text-brand-blue-primary"
                        />
                      </div>
                      <div>
                        <h2 className="text-xl-bold text-brand-blue-dark mb-8">
                          Para se autenticar
                        </h2>
                        <p className="text-[#2B363C]">
                          Precisa do código PIN da sua CMD e do telemóvel que lhe está associado.
                        </p>
                      </div>
                    </div>
                    <div className="xs:col-span-4 md:col-span-3 xl:col-span-5 flex items-center justify-start md:justify-end">
                      <div className="w-[278px] md:flex md:justify-end xl:flex xl:justify-end mt-64">
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
                      className="px-48 h-56 text-lg font-bold shadow-md hover:shadow-lg transition-all"
                      hasIcon={true}
                      trailingIcon={
                        isHovered
                          ? "agora-solid-arrow-right-circle"
                          : "agora-line-arrow-right-circle"
                      }
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
                  <div className="grid gap-32 xs:grid-cols-4 md:grid-cols-8 xl:grid-cols-12">
                    <div className="xs:col-span-4 md:col-span-5 xl:col-span-7">
                      <div className="bg-[#E9EBFF] rounded-8 w-fit p-16 mb-32">
                        <Icon
                          name="agora-line-globe"
                          className="w-24 h-24 text-brand-blue-primary"
                        />
                      </div>
                      <div>
                        <h2 className="text-xl-bold text-brand-blue-dark mb-8">
                          Para se autenticar
                        </h2>
                        <p className="text-neutral-900">
                          Precisa de ter um meio de autenticação digital disponibilizado pelo seu
                          país de origem na União Europeia (UE). Este meio de autenticação está
                          disponível para a qualquer cidadã/o da UE.
                        </p>
                      </div>
                    </div>
                    <div className="xs:col-span-4 md:col-span-3 xl:col-span-5 flex items-center justify-start md:justify-end">
                      <div className="w-[278px] md:flex md:justify-end xl:flex xl:justify-end mt-64">
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
                      className="px-48 h-56 text-lg font-bold shadow-md hover:shadow-lg transition-all"
                      hasIcon={true}
                      trailingIcon={
                        isHoveredEidas
                          ? "agora-solid-arrow-right-circle"
                          : "agora-line-arrow-right-circle"
                      }
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
                <div className="flex flex-col gap-32 max-w-[560px]">
                  <div className="bg-[#E9EBFF] rounded-8 w-fit p-16">
                    <Icon name="agora-line-user" className="w-24 h-24 text-brand-blue-primary" />
                  </div>
                  <div>
                    <h2 className="text-xl-bold  text-brand-blue-dark mb-8">Iniciar sessão</h2>
                    <p className="text-neutral-900">
                      Os campos marcados com um asterisco ( * ) são obrigatórios.
                    </p>
                  </div>

                  {error && (
                    <div className="p-16 rounded-8 bg-red-50 text-red-700 text-sm font-medium border border-red-200">
                      {error}
                    </div>
                  )}

                  <form className="flex flex-col gap-24" onSubmit={handleSubmit}>
                    <InputText
                      label="Endereço de email *"
                      placeholder="Introduza aqui o texto"
                      id="login-email"
                      name="email"
                      type="email"
                      className="w-full"
                      disabled={isLoading}
                    />

                    <div className="flex flex-col gap-8">
                      <InputPassword
                        label="Palavra-passe *"
                        placeholder="Introduza aqui a palavra-passe"
                        id="login-password"
                        name="password"
                        className="w-full"
                        disabled={isLoading}
                      />
                    </div>

                    <div className="flex items-center text-neutral-900">
                      <Checkbox
                        label="Recordar palavra-passe"
                        id="remember-me"
                        name="remember-me"
                      />
                    </div>

                    <div className="mt-8">
                      <Button
                        variant="primary"
                        type="submit"
                        className="px-48 h-56 text-lg font-bold shadow-md hover:shadow-lg transition-all"
                        disabled={isLoading}
                      >
                        {isLoading ? "A iniciar sessão..." : "Iniciar sessão"}
                      </Button>
                    </div>

                    <div className="flex items-center justify-center mt-24 gap-4">
                      <span className="text-sm text-neutral-900">
                        Esqueceu-se da palavra-passe?
                      </span>
                      <Button
                        variant="primary"
                        appearance="link"
                        className="p-0 h-auto font-bold text-sm"
                      >
                        Recuperar palavra-passe
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
