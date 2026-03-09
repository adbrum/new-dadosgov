import type { Metadata } from 'next';
import LoginClient from '@/components/login/LoginClient';

export const metadata: Metadata = {
    title: 'Iniciar Sessão - dados.gov',
    description: 'Inicie sessão no portal dados.gov para aceder a funcionalidades exclusivas. Partilhe e reutilize dados públicos.',
};

export default function LoginPage() {
    return <LoginClient />;
}
