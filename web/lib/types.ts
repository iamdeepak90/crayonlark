export type BookSummary = {
  id: number;
  slug: string;
  title: string;
  subtitle: string;
  series: string;
  volume: number;
  status: string;
  etsy_status: string;
  format: string;
  trim: string;
  page_count: number;
  kdp_week_start: string | null;
  updated_at: string;
  counts: Record<string, number>;
};

export type QA = {
  score?: number;
  recommendation?: string;
  failures?: string[];
  warnings?: string[];
  grey_ratio?: number;
  black_fill?: number;
  line_px_at_print?: number;
  text_found?: string;
  width?: number;
  height?: number;
};

export type ImageItem = {
  id: number;
  position: number;
  scene_title: string;
  prompt: string;
  provider: string;
  status: string;
  approval: "pending" | "approved" | "rejected";
  qa_score: number | null;
  qa_recommendation: string | null;
  qa: QA;
  qa_cleaned: QA | null;
  vision: { verdict?: string; issues?: string[]; score?: number };
  width: number | null;
  height: number | null;
  has_cleaned: boolean;
  error: string | null;
};

export type Job = {
  id: string;
  name: string;
  status: string;
  error: string | null;
  created_at: string;
  queue?: string;
  book_id?: number | null;
  attempts?: number;
  cost_usd?: number;
  finished_at?: string | null;
};

export type BookDetail = BookSummary & {
  fields: Record<string, unknown>;
  images: ImageItem[];
  approved_count: number;
  interior_key: string | null;
  cover_key: string | null;
  pack_key: string | null;
  covers: { id: number; version: number; approval: string; template: string; width_in: number; height_in: number; spine_in: number; has_pdf: boolean }[];
  listings: { id: number; platform: string; product_kind: string; title: string; status: string }[];
  jobs: Job[];
};

export type Dashboard = {
  books_by_status: Record<string, number>;
  statuses: string[];
  failed_jobs: number;
  pending_niches: number;
  kdp_slots: {
    week_start: string;
    resets_at: string;
    paperback_used: number;
    paperback_limit: number;
    paperback_left: number;
    hardcover_used: number;
    hardcover_limit: number;
    hardcover_left: number;
    upcoming: { week_start: string; paperback: number; hardcover: number }[];
  };
  budget: { month: string; spent_inr: number; cap_inr: number; ratio: number; state: string; by_agent: { agent: string; provider: string; usd: number; calls: number }[] };
};

export type CoverItem = {
  id: number;
  version: number;
  approval: string;
  approved_by: string | null;
  template: string;
  options: Record<string, unknown>;
  ai_generated: boolean;
  width_in: number;
  height_in: number;
  spine_in: number;
  files: { pdf: string; preview: string; thumb: string; phone: string };
  created_at: string;
};

export type CoversResponse = {
  book: { id: number; title: string; status: string; page_count: number | null };
  themes: string[];
  covers: CoverItem[];
  approved_images: { id: number; scene_title: string }[];
};

export type ListingItem = {
  id: number;
  platform: "kdp" | "etsy";
  product_kind: string;
  title: string;
  subtitle: string;
  description: string;
  keywords: string[];
  categories: string[];
  tags: string[];
  age_min: number | null;
  age_max: number | null;
  price_cents: number;
  ai_disclosure: string;
  page_selection: number[];
  file_keys: Record<string, string>;
  status: string;
  approved_by: string | null;
  problems: Record<string, string[]>;
};

export type ListingsResponse = {
  book: { id: number; title: string; status: string; slug: string };
  listings: ListingItem[];
};

export type KdpSlots = {
  week_start: string;
  resets_at: string;
  paperback_used: number;
  paperback_limit: number;
  paperback_left: number;
  hardcover_used: number;
  hardcover_limit: number;
  hardcover_left: number;
  upcoming: { week_start: string; paperback: number; hardcover: number }[];
};

export type PackRow = {
  id: number;
  title: string;
  slug: string;
  status: string;
  format: string;
  page_count: number | null;
  kdp_week_start: string | null;
  pack_key: string | null;
  interior_key: string | null;
  cover_key: string | null;
  kdp_asin: string | null;
  amazon_url: string | null;
  etsy: { id: number; product_kind: string; title: string; file_keys: Record<string, string> }[];
};
