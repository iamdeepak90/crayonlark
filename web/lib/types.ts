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

export type Connection = { connected: boolean; expires_at?: string | null; scopes?: string; updated_at?: string; extra?: Record<string, unknown> };

export type EtsyOverview = {
  configured: boolean;
  connection: Connection;
  remaining_today: number | null;
  books: {
    id: number;
    title: string;
    etsy_status: string;
    problems: Record<string, string[]>;
    listings: {
      id: number;
      product_kind: string;
      title: string;
      price_cents: number;
      file_keys: Record<string, string>;
      mockups: string[];
      pins: string[];
      etsy: null | { etsy_listing_id: number | null; state: string; url: string | null; uploaded: string[]; publish_approved_by: string | null; error: string | null };
    }[];
  }[];
};

export type PinItem = {
  id: number;
  book_id: number | null;
  title: string;
  link: string;
  image_key: string;
  scheduled_at: string;
  posted_at: string | null;
  status: string;
  error: string | null;
  pinterest_pin_id: string | null;
};

export type PinterestOverview = {
  configured: boolean;
  connection: Connection;
  boards: { id: number; name: string; pinterest_board_id: string | null }[];
  upcoming: PinItem[];
  recent: PinItem[];
};

export type BudgetState = "ok" | "warn" | "stop";

export type CostCall = {
  id: number;
  at: string;
  provider: string;
  model: string;
  agent: string;
  kind: "llm" | "vision" | "image" | "search";
  status: "reserved" | "committed" | "released";
  input_tokens: number | null;
  output_tokens: number | null;
  images: number | null;
  usd: number;
  inr: number;
  book_id: number | null;
};

export type CostsResponse = {
  month: string;
  spent_usd: number;
  spent_inr: number;
  cap_inr: number;
  ratio: number;
  state: BudgetState;
  usd_inr_rate: number;
  by_agent: { agent: string; provider: string; usd: number; calls: number }[];
  daily: { day: string; usd: number }[];
  by_book: { book_id: number; title: string; usd: number; calls: number }[];
  recent: CostCall[];
};

export type LlmProvider = "offline" | "anthropic" | "openai" | "gemini";
export type ImageProvider = "manual" | "openai" | "gemini";
export type AgentModel = { provider: LlmProvider; model?: string; effort?: string };

export type AIProviders = {
  keys: { anthropic: boolean; openai: boolean; gemini: boolean; websearch: boolean };
  agents: string[];
  agent_models: Record<string, AgentModel>;
  image_provider: { provider: ImageProvider; model: string };
  llm_prices: Record<string, { input: number; output: number }>;
  image_prices: Record<string, number>;
  prices_checked: string;
};

export type ConceptsResponse = {
  status: string;
  can_make_concepts: boolean;
  can_generate: boolean;
  image_provider: ImageProvider;
  image_model: string;
  price_per_image_usd: number;
  concepts: ImageItem[];
  failed: ImageItem[];
};

export type SalesResponse = {
  start: string;
  end: string;
  days: number;
  by_platform: { platform: "etsy" | "kdp"; currency: string; units: number; revenue: number }[];
  by_book: { book_id: number | null; title: string; currency: string; units: number; revenue: number }[];
  rows: { id: number; platform: "etsy" | "kdp"; sold_on: string; title: string; book_id: number | null; marketplace: string; units: number; revenue: number; currency: string }[];
  etsy_configured: boolean;
  last_etsy_import: string | null;
  last_kdp_import: string | null;
};

export type BackupRun = {
  ok: boolean;
  day: string;
  started_at: string;
  finished_at: string;
  /** The fields below are missing when the run failed (ok: false); then `error` says why. */
  dump?: string;
  dump_mb?: number;
  buckets?: Record<string, { objects: number; copied: number; removed: number }>;
  pruned?: string[];
  offsite?: { enabled: boolean; files?: number; pruned_dumps?: number };
  error?: string;
};

export type BackupsResponse = { last: BackupRun | null; dumps: string[]; retention_days: number; offsite: boolean };

export type WeeklyReport = { text: string; data: Record<string, unknown> };

export type BudgetSettings = { month: string; spent_inr: number; cap_inr: number; usd_inr_rate: number; ratio: number; state: BudgetState };

export type PaidApi = { id: string; name: string; used_for: string; env: string[]; url: string; key_set: boolean; used_by: string[]; month_usd: number; month_inr: number };
export type PaidApis = { month: string; apis: PaidApi[] };
