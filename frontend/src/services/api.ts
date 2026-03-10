import {
  APIResponse,
  Dataset,
  GlobalSearchSuggestion,
  Organization,
  Post,
  Reuse,
  SiteInfo,
} from "@/types/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE || "https://dados.gov.pt/api/1";

/**
 * Fetch CSRF token from backend
 */
export async function fetchCsrfToken(): Promise<string> {
  const res = await fetch("/get-csrf", { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch CSRF token");
  const data = await res.json();
  return data.response.csrf_token;
}

/**
 * Perform login using the frontend route handler proxy
 */
export async function login(formData: FormData): Promise<{ message: string; redirect?: string }> {
  const res = await fetch("/login", {
    method: "POST",
    body: new URLSearchParams(formData as any),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.message || "Login failed");
  }
  return data;
}

/**
 * Perform logout
 */
export async function logout(): Promise<void> {
  const res = await fetch("/logout/", { method: "GET" });
  if (!res.ok) throw new Error("Logout failed");
}

export async function fetchDatasets(
  page: number = 1,
  pageSize: number = 20,
  organization?: string | string[]
): Promise<APIResponse<Dataset>> {
  try {
    console.log("fetchDatasets called with org:", organization);
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

    console.log("API Fetch URL:", url);

    const res = await fetch(url, {
      cache: "no-store", // Ensure fresh data
    });

    if (!res.ok) {
      throw new Error(`Failed to fetch datasets: ${res.statusText}`);
    }

    return await res.json();
  } catch (error) {
    console.error("Error fetching datasets:", error);
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
      cache: "no-store",
    });

    if (!res.ok) {
      throw new Error(`Failed to fetch dataset: ${res.statusText}`);
    }

    return await res.json();
  } catch (error) {
    console.error("Error fetching dataset:", error);
    throw error;
  }
}

export async function fetchOrganizations(
  page: number = 1,
  pageSize: number = 20
): Promise<APIResponse<Organization>> {
  try {
    const res = await fetch(`${API_BASE_URL}/organizations/?page=${page}&page_size=${pageSize}`, {
      cache: "no-store",
    });

    if (!res.ok) {
      throw new Error(`Failed to fetch organizations: ${res.statusText}`);
    }

    return await res.json();
  } catch (error) {
    console.error("Error fetching organizations:", error);
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
export async function fetchOrganization(slug: string): Promise<Organization> {
  try {
    const res = await fetch(`${API_BASE_URL}/organizations/${slug}/`, {
      cache: "no-store",
    });

    if (!res.ok) {
      throw new Error(`Failed to fetch organization: ${res.statusText}`);
    }

    return await res.json();
  } catch (error) {
    console.error("Error fetching organization:", error);
    throw error;
  }
}
export async function fetchReuses(
  page: number = 1,
  pageSize: number = 20
): Promise<APIResponse<Reuse>> {
  try {
    const url = `${API_BASE_URL}/reuses/?page=${page}&page_size=${pageSize}`;
    const res = await fetch(url, {
      cache: "no-store",
    });

    if (!res.ok) {
      throw new Error(`Failed to fetch reuses: ${res.statusText}`);
    }

    return await res.json();
  } catch (error) {
    console.error("Error fetching reuses:", error);
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
      cache: "no-store",
    });

    if (!res.ok) {
      throw new Error(`Failed to fetch reuse: ${res.statusText}`);
    }

    return await res.json();
  } catch (error) {
    console.error("Error fetching reuse:", error);
    throw error;
  }
}

export async function fetchSiteInfo(): Promise<SiteInfo> {
  try {
    const res = await fetch(`${API_BASE_URL}/site/`, {
      cache: "no-store",
    });

    if (!res.ok) {
      throw new Error(`Failed to fetch site info: ${res.statusText}`);
    }

    return await res.json();
  } catch (error) {
    console.error("Error fetching site info:", error);
    return {
      id: "",
      title: "",
      metrics: { datasets: 0, organizations: 0, reuses: 0, users: 0 },
    };
  }
}

export async function fetchFeaturedDatasets(
  pageSize: number = 3,
): Promise<APIResponse<Dataset>> {
  try {
    const res = await fetch(
      `${API_BASE_URL}/datasets/?featured=true&page_size=${pageSize}`,
      { cache: "no-store" },
    );

    if (!res.ok) {
      throw new Error(`Failed to fetch featured datasets: ${res.statusText}`);
    }

    return await res.json();
  } catch (error) {
    console.error("Error fetching featured datasets:", error);
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

export async function fetchFeaturedReuses(
  pageSize: number = 3,
): Promise<APIResponse<Reuse>> {
  try {
    const res = await fetch(
      `${API_BASE_URL}/reuses/?featured=true&page_size=${pageSize}`,
      { cache: "no-store" },
    );

    if (!res.ok) {
      throw new Error(`Failed to fetch featured reuses: ${res.statusText}`);
    }

    return await res.json();
  } catch (error) {
    console.error("Error fetching featured reuses:", error);
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

export async function fetchLatestDatasets(
  pageSize: number = 3,
): Promise<APIResponse<Dataset>> {
  try {
    const res = await fetch(
      `${API_BASE_URL}/datasets/?sort=-created&page_size=${pageSize}`,
      { cache: "no-store" },
    );

    if (!res.ok) {
      throw new Error(`Failed to fetch latest datasets: ${res.statusText}`);
    }

    return await res.json();
  } catch (error) {
    console.error("Error fetching latest datasets:", error);
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

export async function fetchLatestReuses(
  pageSize: number = 3,
): Promise<APIResponse<Reuse>> {
  try {
    const res = await fetch(
      `${API_BASE_URL}/reuses/?sort=-created&page_size=${pageSize}`,
      { cache: "no-store" },
    );

    if (!res.ok) {
      throw new Error(`Failed to fetch latest reuses: ${res.statusText}`);
    }

    return await res.json();
  } catch (error) {
    console.error("Error fetching latest reuses:", error);
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

export async function fetchPosts(
  page: number = 1,
  pageSize: number = 3,
): Promise<APIResponse<Post>> {
  try {
    const res = await fetch(
      `${API_BASE_URL}/posts/?page=${page}&page_size=${pageSize}`,
      { cache: "no-store" },
    );

    if (!res.ok) {
      throw new Error(`Failed to fetch posts: ${res.statusText}`);
    }

    return await res.json();
  } catch (error) {
    console.error("Error fetching posts:", error);
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


export async function searchDatasets(
  query: string,
  page: number = 1,
  pageSize: number = 10,
): Promise<APIResponse<Dataset>> {
  try {
    const res = await fetch(
      `${API_BASE_URL}/datasets/?q=${encodeURIComponent(query)}&page=${page}&page_size=${pageSize}`,
      { cache: "no-store" },
    );
    if (!res.ok) {
      throw new Error(`Failed to search datasets: ${res.statusText}`);
    }
    return await res.json();
  } catch (error) {
    console.error("Error searching datasets:", error);
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

export async function searchOrganizations(
  query: string,
  page: number = 1,
  pageSize: number = 10,
): Promise<APIResponse<Organization>> {
  try {
    const res = await fetch(
      `${API_BASE_URL}/organizations/?q=${encodeURIComponent(query)}&page=${page}&page_size=${pageSize}`,
      { cache: "no-store" },
    );
    if (!res.ok) {
      throw new Error(
        `Failed to search organizations: ${res.statusText}`,
      );
    }
    return await res.json();
  } catch (error) {
    console.error("Error searching organizations:", error);
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

export async function searchReuses(
  query: string,
  page: number = 1,
  pageSize: number = 10,
): Promise<APIResponse<Reuse>> {
  try {
    const res = await fetch(
      `${API_BASE_URL}/reuses/?q=${encodeURIComponent(query)}&page=${page}&page_size=${pageSize}`,
      { cache: "no-store" },
    );
    if (!res.ok) {
      throw new Error(`Failed to search reuses: ${res.statusText}`);
    }
    return await res.json();
  } catch (error) {
    console.error("Error searching reuses:", error);
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

export async function suggestGlobalSearch(
  query: string,
  size: number = 5,
): Promise<GlobalSearchSuggestion[]> {
  try {
    const res = await fetch(
      `${API_BASE_URL}/datasets/suggest/?q=${encodeURIComponent(query)}&size=${size}`,
      { cache: "no-store" },
    );

    if (!res.ok) {
      throw new Error(`Failed to fetch search suggestions: ${res.statusText}`);
    }

    return await res.json();
  } catch (error) {
    console.error("Error fetching search suggestions:", error);
    return [];
  }
}
