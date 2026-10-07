export type ComplaintStatus =
  | "SUBMITTED"
  | "ASSIGNED"
  | "IN_PROGRESS"
  | "RESOLVED"
  | "CLOSED"
  | "REJECTED";

export const ALLOWED_STATUS_TRANSITIONS: Record<ComplaintStatus, ComplaintStatus[]> = {
  SUBMITTED: ["ASSIGNED", "REJECTED"],
  ASSIGNED: ["IN_PROGRESS", "REJECTED"],
  IN_PROGRESS: ["RESOLVED"],
  RESOLVED: ["CLOSED"],
  CLOSED: [],
  REJECTED: [],
};

export type ComplaintPriority = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export interface Department {
  id: number;
  name: string;
  code: string;
  description?: string | null;
  contact_email?: string | null;
  is_active: boolean;
}

export interface AdminOfficer {
  id: string;
  user_id: string;
  badge_number: string;
  designation?: string | null;
  department_id: number;
  department_name?: string | null;
  department_code?: string | null;
  is_available: boolean;
  full_name: string;
  email: string;
}

export interface DepartmentSummary {
  id: number;
  name: string;
  code: string;
  total: number;
  submitted: number;
  assigned: number;
  in_progress: number;
  resolved: number;
  closed: number;
  rejected: number;
}

export interface CategorySummary {
  id: number;
  name: string;
  total: number;
}

export interface AdminStats {
  total: number;
  submitted: number;
  assigned: number;
  in_progress: number;
  resolved: number;
  closed: number;
  rejected: number;
  department_summaries: DepartmentSummary[];
  category_summaries: CategorySummary[];
  officers_count: number;
}

export interface OfficerStats {
  total: number;
  submitted: number;
  assigned: number;
  in_progress: number;
  resolved: number;
  closed: number;
  rejected: number;
  avg_resolution_hours?: number | null;
  resolution_rate?: number | null;
}

export interface Complaint {
  id: string;
  ticket_number: string;
  title: string;
  description: string;
  category: string | ComplaintCategory;
  department?: string;
  priority?: ComplaintPriority | string | null;
  status: ComplaintStatus | string;
  location?: string;
  created_at: string;
  updated_at?: string;
}

export interface AIAnalysisData {
  id?: string;
  complaint_id?: string;
  predicted_category?: string;
  category_confidence?: number;
  recommended_department_name?: string;
  recommended_department_code?: string;
  recommended_department_id?: number | null;
  predicted_priority?: string;
  urgency_score?: number;
  is_low_confidence?: boolean;
  model_version?: string;
  created_at?: string;
  category_prediction?: {
    category: string;
    confidence: number;
  };
  recommended_department?: {
    name: string;
    code: string;
    confidence?: number;
  };
  priority_prediction?: {
    priority: ComplaintPriority | string;
    urgency_score: number;
  };
  duplicate_detection?: {
    is_potential_duplicate: boolean;
    master_ticket_number?: string;
    similarity_score?: number;
  };
  sla_estimation?: {
    estimated_hours: number;
    resolution_deadline?: string;
  };
}

export interface ComplaintCategory {
  id: number;
  name: string;
  slug: string;
  description?: string | null;
  default_sla_hours: number;
  default_priority: string;
  target_department_id?: number | null;
  is_active: boolean;
  created_at: string;
}

export interface ComplaintCreateInput {
  title: string;
  description: string;
  category_id: number;
  latitude: number;
  longitude: number;
  address?: string | null;
  location_text?: string | null;
}

export interface ComplaintAttachment {
  id: string;
  complaint_id: string;
  original_filename: string;
  stored_filename: string;
  content_type: string;
  file_size: number;
  created_at: string;
}

export interface ComplaintStatusHistory {
  id: number;
  complaint_id: string;
  old_status?: string | null;
  new_status: string;
  changed_by_user_id: string;
  remarks?: string | null;
  created_at: string;
}

export interface AssignedOfficer {
  id: string;
  badge_number: string;
  designation?: string | null;
  department_id: number;
  user?: {
    id: string;
    email: string;
    full_name: string;
  } | null;
}

export interface ComplaintResponse {
  id: string;
  ticket_number: string;
  citizen_id: string;
  category_id: number;
  category?: ComplaintCategory | null;
  assigned_officer_id?: string | null;
  assigned_officer?: AssignedOfficer | null;
  citizen?: {
    id: string;
    email: string;
    full_name: string;
    phone_number?: string | null;
  } | null;
  title: string;
  description: string;
  latitude: number;
  longitude: number;
  address?: string | null;
  location_text?: string | null;
  location?: string | null;
  department?: string | null;
  reference_priority?: string | null;
  priority?: string | null;
  status: ComplaintStatus | string;
  created_at: string;
  updated_at: string;
  resolved_at?: string | null;
  closed_at?: string | null;
  ai_analysis?: AIAnalysisData | null;
}

export interface ComplaintDetailResponse extends ComplaintResponse {
  citizen?: {
    id: string;
    email: string;
    full_name: string;
    phone_number?: string | null;
  } | null;
  assigned_officer?: AssignedOfficer | null;
  status_history: ComplaintStatusHistory[];
  attachments: ComplaintAttachment[];
}

export interface ComplaintListResponse {
  items: ComplaintResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
