import { APIResponse, Dataset, Organization, Reuse } from '@/types/api';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE || 'https://dados.gov.pt/api/1';

export async function fetchDatasets(
  page: number = 1,
  pageSize: number = 20,
  organization?: string | string[],
): Promise<APIResponse<Dataset>> {
  try {
    let url = `${API_BASE_URL}/datasets/?page=${page}&page_size=${pageSize}`;
    if (organization) {
      if (Array.isArray(organization)) {
        organization.forEach((org) => {
          url += `&organization=${org}`;
        });
      } else {
        url += `&organization=${organization}`;
      }
    }

    const res = await fetch(url, {
      cache: 'no-store', // Ensure fresh data
    },
    );

    if (!res.ok) {
      throw new Error(`Failed to fetch datasets: ${res.statusText}`);
    }

    return await res.json();
  } catch (error) {
    console.error('Error fetching datasets:', error);
    // Return empty state or rethrow depending on desired error handling
    return {
      data: [],
      page: 1,
      page_size: pageSize,
      total: 0,
      next_page: null,
      previous_page: null,
    };
  }
}

export async function fetchDataset(slug: string): Promise<Dataset> {
  try {
    const res = await fetch(`${API_BASE_URL}/datasets/${slug}/`, {
      cache: 'no-store',
    });

    if (!res.ok) {
      throw new Error(`Failed to fetch dataset: ${res.statusText}`);
    }

    return await res.json();
  } catch (error) {
    console.error('Error fetching dataset:', error);
    throw error;
  }
}

export async function fetchOrganizations(
  page: number = 1,
  pageSize: number = 20,
): Promise<APIResponse<Organization>> {
  try {
    const res = await fetch(
      `${API_BASE_URL}/organizations/?page=${page}&page_size=${pageSize}`,
      {
        cache: 'no-store',
      },
    );

    if (!res.ok) {
      throw new Error(`Failed to fetch organizations: ${res.statusText}`);
    }

    return await res.json();
  } catch (error) {
    console.error('Error fetching organizations:', error);
    return {
      data: [],
      page: 1,
      page_size: pageSize,
      total: 0,
      next_page: null,
      previous_page: null,
    };
  }
}
export async function fetchReuses(
  page: number = 1,
  pageSize: number = 20,
): Promise<APIResponse<Reuse>> {
  try {
    const url = `${API_BASE_URL}/reuses/?page=${page}&page_size=${pageSize}`;
    const res = await fetch(url, {
      cache: 'no-store',
    });

    if (!res.ok) {
      throw new Error(`Failed to fetch reuses: ${res.statusText}`);
    }

    return await res.json();
  } catch (error) {
    console.error('Error fetching reuses:', error);
    return {
      data: [],
      page: 1,
      page_size: pageSize,
      total: 0,
      next_page: null,
      previous_page: null,
    };
  }
}
export async function fetchReuse(rid: string): Promise<Reuse> {
  try {
    const res = await fetch(`${API_BASE_URL}/reuses/${rid}/`, {
      cache: 'no-store',
    });

    if (!res.ok) {
      throw new Error(`Failed to fetch reuse: ${res.statusText}`);
    }

    return await res.json();
  } catch (error) {
    console.error('Error fetching reuse:', error);
    throw error;
  }
}
