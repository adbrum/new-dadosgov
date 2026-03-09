'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { SearchPagination } from '@ama-pt/agora-design-system';

interface PaginationProps {
  currentPage: number;
  totalItems: number;
  pageSize: number;
  baseUrl?: string;
}

export const Pagination = ({
  currentPage,
  totalItems,
  pageSize,
  baseUrl = '/pages/datasets',
}: PaginationProps) => {
  const router = useRouter();
  const totalPages = Math.ceil(totalItems / pageSize);

  const handlePageChange = (page: number) => {
    // SearchPagination component uses 0-based indexing for pages
    const targetPage = page + 1;

    // Only navigate if the page is different from current to avoid infinite loops
    // since SearchPagination might trigger onChange(0) on mount
    if (targetPage !== currentPage) {
      router.push(`${baseUrl}?page=${targetPage}`);
    }
  };

  if (totalPages <= 1) return null;

  return (
    <SearchPagination
      totalPages={totalPages}
      onChange={handlePageChange}
      label="Paginação"
      nextPageAriaLabel="Próxima página"
      previousPageAriaLabel="Página anterior"
      boundaryCount={1}
      siblingCount={1}
    />
  );
};
