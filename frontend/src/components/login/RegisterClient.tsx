'use client';

import React, { useState } from 'react';
import {
    Button,
    InputText,
    InputPassword,
    Checkbox,
} from '@ama-pt/agora-design-system';
import { fetchCsrfToken, register } from '@/services/api';
import { useRouter } from 'next/navigation';

export default function RegisterClient() {
    const router = useRouter();
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        setIsLoading(true);
        setError(null);
        setSuccess(null);

        const formData = new FormData(e.currentTarget);
        const email = formData.get('email') as string;
        const password = formData.get('password') as string;
        const passwordConfirm = formData.get('confirm-password') as string;
        const firstName = formData.get('first-name') as string;
        const lastName = formData.get('last-name') as string;
        const acceptConditions = formData.get('accept_conditions');

        if (!email || !password || !passwordConfirm || !firstName || !lastName) {
            setError('Por favor, preencha todos os campos obrigatórios.');
            setIsLoading(false);
            return;
        }

        if (password !== passwordConfirm) {
            setError('As senhas não coincidem.');
            setIsLoading(false);
            return;
        }

        if (!acceptConditions) {
            setError('Deve aceitar os termos e condições.');
            setIsLoading(false);
            return;
        }

        try {
            // 1. Get CSRF Token
            const csrfToken = await fetchCsrfToken();

            // 2. Prepare payload for backend
            const payload = new FormData();
            payload.append('email', email);
            payload.append('password', password);
            payload.append('password_confirm', passwordConfirm);
            payload.append('first_name', firstName);
            payload.append('last_name', lastName);
            payload.append('accept_conditions', 'y');
            payload.append('csrf_token', csrfToken);

            // 3. Register
            const response = await register(payload);

            // 4. Handle response
            if (response.requireEmailConfirmation) {
                setSuccess(
                    'Registo efetuado com sucesso. Verifique o seu email para confirmar a conta.'
                );
            } else {
                router.push(response.redirect || '/');
            }
        } catch (err: any) {
            console.error('Registration error:', err);
            setError(err.message || 'Ocorreu um erro ao tentar registar.');
        } finally {
            setIsLoading(false);
        }
    };

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

                    {error && (
                        <div className="p-16 rounded-8 bg-red-50 text-red-700 text-sm font-medium border border-red-200 mb-24">
                            {error}
                        </div>
                    )}

                    {success && (
                        <div className="p-16 rounded-8 bg-green-50 text-green-700 text-sm font-medium border border-green-200 mb-24">
                            {success}
                        </div>
                    )}

                    {/* Registration Form */}
                    <form className="flex flex-col gap-24" onSubmit={handleSubmit}>
                        <InputText
                            label="Endereço de email *"
                            placeholder="Introduza aqui o texto"
                            id="email"
                            name="email"
                            type="email"
                            className="w-full"
                            disabled={isLoading}
                        />

                        <InputPassword
                            label="Senha *"
                            placeholder="Introduza aqui o texto"
                            id="password"
                            name="password"
                            className="w-full"
                            disabled={isLoading}
                        />

                        <InputPassword
                            label="Confirme a senha *"
                            placeholder="Introduza aqui o texto"
                            id="confirm-password"
                            name="confirm-password"
                            className="w-full"
                            disabled={isLoading}
                        />

                        <InputText
                            label="Nome *"
                            placeholder="Introduza aqui o texto"
                            id="first-name"
                            name="first-name"
                            className="w-full"
                            disabled={isLoading}
                        />

                        <InputText
                            label="Apelido *"
                            placeholder="Introduza aqui o texto"
                            id="last-name"
                            name="last-name"
                            className="w-full"
                            disabled={isLoading}
                        />

                        <div className="flex items-center">
                            <Checkbox
                                label="Li e concordo com os termos e condições de uso do serviço."
                                id="accept_conditions"
                                name="accept_conditions"
                                disabled={isLoading}
                            />
                        </div>

                        <div className="flex justify-center mt-32">
                            <Button
                                variant="primary"
                                type="submit"
                                className="min-w-[200px] h-11 px-48"
                                id="submit-register"
                                disabled={isLoading}
                            >
                                {isLoading ? 'A registar...' : 'Registar'}
                            </Button>
                        </div>
                    </form>
                </div>
            </div>
        </main>
    );
}
