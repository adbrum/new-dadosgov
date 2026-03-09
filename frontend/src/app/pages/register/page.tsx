import type { Metadata } from 'next';
import RegisterClient from '@/components/login/RegisterClient';

export const metadata: Metadata = {
    title: 'Registe-se - dados.gov',
    description: 'Crie uma conta no portal dados.gov para aceder a funcionalidades exclusivas. Partilhe e reutilize dados públicos.',
};

export default function RegisterPage() {
    return <RegisterClient />;
}
