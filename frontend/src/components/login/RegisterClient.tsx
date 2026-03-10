'use client';

import React from 'react';
import {
    Button,
    InputText,
    InputPassword,
    Checkbox,
    Icon,
} from '@ama-pt/agora-design-system';

export default function RegisterClient() {
    return (
        <main className="flex-grow bg-white">
            <div className="container mx-auto px-16 py-64 flex flex-col items-center">
                <div className="w-full max-w-[560px]">
                    {/* Title and Intro */}
                    <h1 className="text-3xl-bold text-[#002D72] mb-32 text-left" id="register-title">
                        Registe-se
                    </h1>
                    <p className="text-sm text-neutral-700 mb-32">
                        Os campos marcados com um asterisco ( * ) são obrigatórios.
                    </p>

                    {/* Registration Form */}
                    <form className="flex flex-col gap-24" onSubmit={(e) => e.preventDefault()}>
                        <InputText
                            label="Endereço de email *"
                            placeholder="Introduza aqui o texto"
                            id="email"
                            name="email"
                            type="email"
                            className="w-full"
                        />

                        <InputPassword
                            label="Senha *"
                            placeholder="Introduza aqui o texto"
                            id="password"
                            name="password"
                            className="w-full"
                        />

                        <InputPassword
                            label="Confirme a senha *"
                            placeholder="Introduza aqui o texto"
                            id="confirm-password"
                            name="confirm-password"
                            className="w-full"
                        />

                        <InputText
                            label="Nome *"
                            placeholder="Introduza aqui o texto"
                            id="first-name"
                            name="first-name"
                            className="w-full"
                        />

                        <InputText
                            label="Apelido *"
                            placeholder="Introduza aqui o texto"
                            id="last-name"
                            name="last-name"
                            className="w-full"
                        />

                        <div className="flex items-center">
                            <Checkbox
                                label="Li e concordo com os termos e condições de uso do serviço."
                                id="terms"
                                name="terms"
                            />
                        </div>

                        <div className="flex justify-center mt-32">
                            <Button variant="primary" type="submit" className="min-w-[200px] h-11 px-48" id="submit-register">
                                Registar
                            </Button>
                        </div>
                    </form>
                </div>
            </div>
        </main>
    );
}
