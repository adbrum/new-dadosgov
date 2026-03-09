import { fetchReuses } from '@/services/api';
import ReusesClient from '@/components/reuses/ReusesClient';
import { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Reutilizações - dados.gov',
    description: 'Descubra como os dados abertos estão a ser utilizados para criar valor em Portugal. Explore as reutilizações da comunidade.',
};

export default async function ReusesPage({
    searchParams,
}: {
    searchParams: Promise<{ page?: string }>;
}) {
    const resolvedSearchParams = await searchParams;
    const page = Number(resolvedSearchParams?.page) || 1;
    const initialData = await fetchReuses(page, 12); // Using 12 per page as it's a grid

    return <ReusesClient initialData={initialData} currentPage={page} />;
}
