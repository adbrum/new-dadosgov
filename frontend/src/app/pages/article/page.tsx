import ArticleClient from '@/components/articles/ArticleClient';
import { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Últimas novidades - dados.gov',
    description: 'Acompanhe as últimas novidades, eventos e publicações sobre dados abertos em Portugal.',
};

export default async function ArticleListPage({
    searchParams,
}: {
    searchParams: Promise<{ page?: string }>;
}) {
    const resolvedSearchParams = await searchParams;
    const page = Number(resolvedSearchParams?.page) || 1;

    return <ArticleClient currentPage={page} />;
}
