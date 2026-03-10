import { fetchOrganization } from '@/services/api';
import OrganizationDetailClient from '@/components/organizations/OrganizationDetailClient';

export default async function Page({
    params,
}: {
    params: Promise<{ slug: string }>;
}) {
    const { slug } = await params;
    const organization = await fetchOrganization(slug);

    return <OrganizationDetailClient organization={organization} />;
}
