import { fetchDataset } from '@/services/api';
import DatasetDetailClient from '@/components/datasets/DatasetDetailClient';

export default async function Page({
    params,
}: {
    params: Promise<{ slug: string }>;
}) {
    const { slug } = await params;
    const dataset = await fetchDataset(slug);

    return <DatasetDetailClient dataset={dataset} />;
}
