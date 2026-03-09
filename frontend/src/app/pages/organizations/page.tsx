import { fetchOrganizations } from '@/services/api';
import OrganizationsClient from '@/components/organizations/OrganizationsClient';
import { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Organizações - dados.gov',
    description: 'Explore as organizações que publicam dados abertos em Portugal.',
};

export default async function OrganizationsPage({
    searchParams,
}: {
    searchParams: Promise<{ page?: string }>;
}) {
    const resolvedSearchParams = await searchParams;
    const page = Number(resolvedSearchParams?.page) || 1;
    const initialData = await fetchOrganizations(page, 20);

    return <OrganizationsClient initialData={initialData} currentPage={page} />;
}
