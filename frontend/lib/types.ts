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

export interface LeadContactUpdate {
  email?: string;
  phone?: string;
  address?: string;
  city?: string;
  country?: string;
  notes?: string;
  decision_makers?: ContactInfo[];
}

export interface LeadManualCreate {
  company_name: string;
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
  funding_stage?: string;
  funding_amount_millions?: number;
  founded_year?: number;
  tech_stack?: string[];
  venture?: string;
  notes?: string;
  decision_makers?: ContactInfo[];
  social_media?: Record<string, string>;
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
  venture?: string;
  source_query?: string;
}

export type CampaignStatus =
  | "draft"
  | "scheduled"
  | "running"
  | "paused"
  | "completed"
  | "cancelled";

export interface EmailTemplate {
  subject_line: string;
  body: string;
}

export interface Campaign {
  id?: string;
  name: string;
  status: CampaignStatus;
  campaign_goal?: string;
  created_at: string;
  scheduled_at?: string;
  started_at?: string;
  completed_at?: string;
  send_from_email?: string;
  send_from_name?: string;
  follow_up_days?: number[];
  send_timezone?: string;
  min_delay_seconds?: number;
  max_delay_seconds?: number;
  total_leads: number;
  emails_sent: number;
  emails_opened: number;
  emails_clicked: number;
  emails_replied: number;
  emails_bounced: number;
}

export interface CampaignAttachment {
  id: string;
  campaign_id: string;
  email_id?: string | null;
  filename: string;
  content_type?: string;
  size_bytes?: number;
  created_at?: string;
}

export interface CampaignEmail {
  id: string;
  campaign_id: string;
  lead_id: string;
  lead_name?: string;
  recipient_email: string;
  recipient_name?: string;
  subject?: string;
  body?: string;
  sent_at?: string;
  opened_at?: string;
  clicked_at?: string;
  follow_up_number: number;
  error_message?: string;
  attachments?: CampaignAttachment[];
}

export interface CampaignCreatePayload {
  name: string;
  lead_ids: string[];
  campaign_goal: string;
  email_template: EmailTemplate;
  send_from_email: string;
  send_from_name: string;
  follow_up_days?: number[];
  send_timezone?: string;
  min_delay_seconds?: number;
  max_delay_seconds?: number;
}

export interface CampaignSchedulePayload {
  scheduled_local: string;
  send_timezone: string;
  min_delay_seconds?: number;
  max_delay_seconds?: number;
}

export interface CampaignMetrics {
  campaign_id: string;
  open_rate: number;
  click_rate: number;
  response_rate: number;
  bounce_rate: number;
  conversion_rate: number;
}

export interface VentureCount {
  venture: string;
  count: number;
}

export interface LeadCampaignHistory {
  campaign_id: string;
  campaign_name: string;
  campaign_status: string;
  email_id: string;
  subject?: string;
  sent_at?: string;
  follow_up_number: number;
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

export interface SavedSearch {
  id: string;
  name: string;
  query: string;
  max_results: number;
  venture?: string;
  cadence: "off" | "daily" | "weekly";
  enabled: boolean;
  last_run_at?: string;
  last_run_new_count: number;
  total_found: number;
  created_at: string;
}

export interface SavedSearchPayload {
  name: string;
  query: string;
  max_results?: number;
  venture?: string;
  cadence?: "off" | "daily" | "weekly";
  enabled?: boolean;
}

export interface Analytics {
  funnel: { stage: string; key: string; count: number }[];
  email_performance: {
    sent: number;
    opened: number;
    clicked: number;
    replied: number;
    bounced: number;
    open_rate: number;
    click_rate: number;
    reply_rate: number;
    bounce_rate: number;
  };
  top_subjects: { subject: string; sends: number; opens: number; open_rate: number }[];
  by_country: { label: string; sent: number; replied: number; reply_rate: number }[];
  by_industry: { label: string; sent: number; replied: number; reply_rate: number }[];
  best_send_hours: { hour: number; sends: number; opens: number; open_rate: number }[];
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
  role?: string;
  profile_picture?: string;
  last_loggedin_at?: string;
  created_at: string;
  updated_at: string;
}

export interface SmtpSettings {
  smtp_host?: string;
  smtp_port?: number;
  smtp_username?: string;
  smtp_from_email?: string;
  smtp_from_name?: string;
  password_set?: boolean;
  smtp_password?: string;
  imap_host?: string;
  imap_port?: number;
  reply_scan_enabled?: boolean;
}

export interface SmtpSettingsUpdate {
  smtp_host?: string;
  smtp_port?: number;
  smtp_username?: string;
  smtp_password?: string;
  smtp_from_email?: string;
  smtp_from_name?: string;
  imap_host?: string;
  imap_port?: number;
  reply_scan_enabled?: boolean;
}

export interface SmtpProvider {
  id: string;
  label: string;
  host: string;
  port: number;
  imap_host?: string;
  imap_port?: number;
}

export interface InviteUserPayload {
  email: string;
  first_name?: string;
  last_name?: string;
  role?: string;
  password?: string;
}

export interface UserListItem {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  role: string;
  last_loggedin_at?: string;
  created_at: string;
}
