import { fetchDatasets } from '@/services/api';
import DatasetsClient from '@/components/datasets/DatasetsClient';

// Ensure this is a server component by not adding 'use client'
// But DatasetsClient IS a client component

export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; org_id?: string | string[] }>;
}) {
  const resolvedSearchParams = await searchParams; // Next.js 15+ needs await for params/searchParams
  console.log('Page Params:', resolvedSearchParams);
  const page = Number(resolvedSearchParams?.page) || 1;
  const organization = resolvedSearchParams?.org_id;
  const initialData = await fetchDatasets(page, 20, organization);

  return <DatasetsClient initialData={initialData} currentPage={page} />;
}
