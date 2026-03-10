export interface Organization {
  id: string;
  name: string;
  slug: string;
  logo: string | null;
  description: string | null;
}

export interface Metric {
  nb_hits?: number;
  nb_uniq_visitors?: number;
  nb_visits?: number;
  views?: number;
  followers?: number;
  reuses?: number;
  downloads?: number;
}

export interface Resource {
  id: string;
  title: string;
  format: string;
  url: string;
  created_at: string;
  filesize?: number;
  type?: string;
}

export interface Dataset {
  id: string;
  title: string;
  slug: string;
  description: string;
  organization: Organization | null;
  last_modified: string;
  created_at: string;
  tags: string[];
  resources: Resource[];
  metrics: Metric;
  page: string; // The URL to the dataset page usually
}

export interface Reuse {
  id: string;
  title: string;
  slug: string;
  description: string;
  type: string;
  image: string | null;
  image_thumbnail: string | null;
  organization: Organization | null;
  created_at: string;
  last_modified: string;
  metrics: Metric;
  url: string;
  tags: string[];
  datasets?: Dataset[];
}

export interface APIResponse<T> {
  data: T[];
  page: number;
  page_size: number;
  total: number;
  next_page: string | null;
  previous_page: string | null;
}
