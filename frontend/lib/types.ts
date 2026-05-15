export type LeadStatus =
  | "discovered"
  | "enriching"
  | "enriched"
  | "qualified"
  | "contacted"
  | "responded"
  | "converted"
  | "disqualified";

export type FundingStage =
  | "Pre-Seed"
  | "Seed"
  | "Series A"
  | "Series B"
  | "Series C+"
  | "Bootstrapped"
  | "Public"
  | "Unknown";

export interface CompanyInfo {
  name: string;
  website?: string;
  description?: string;
  industry?: string;
  employee_count?: number;
  phone?: string;
  email?: string;
  address?: string;
  location?: string;
  city?: string;
  country?: string;
  funding_stage?: FundingStage;
  funding_amount_millions?: number;
  founded_year?: number;
  tech_stack?: string[];
}

export interface ContactInfo {
  name?: string;
  title?: string;
  email?: string;
  linkedin_url?: string;
  phone?: string;
}

export interface LeadEnrichmentData {
  decision_makers?: ContactInfo[];
  social_media?: Record<string, string>;
  additional_data?: Record<string, unknown>;
}

export interface Lead {
  id?: string;
  company_info: CompanyInfo;
  enrichment_data?: LeadEnrichmentData;
  status: LeadStatus;
  discovered_at: string;
  enriched_at?: string;
  last_contacted_at?: string;
  notes?: string;
}

export interface LeadListResponse {
  leads: Lead[];
  total: number;
  page: number;
  page_size: number;
}

export interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data: T;
}

export interface DashboardStats {
  total_leads: number;
  total_enriched: number;
  monthly_leads: number;
  location_breakdown: { location: string; count: number }[];
  city_breakdown: { city: string; count: number }[];
}

export interface TrendPoint {
  month: string;
  month_label: string;
  count: number;
}

export interface UserProfile {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  profile_picture?: string;
  last_loggedin_at?: string;
  created_at: string;
  updated_at: string;
}
