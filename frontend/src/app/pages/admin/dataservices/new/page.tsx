import type { Metadata } from 'next';
import ApiRegistrationClient from '@/components/admin/dataservices/ApiRegistrationClient';

export const metadata: Metadata = {
    title: 'Descreva a sua API - Admin - dados.gov',
    description: 'Formulário de inscrição para novas APIs no portal dados.gov.',
};

export default function ApiRegistrationPage() {
    return <ApiRegistrationClient />;
}
