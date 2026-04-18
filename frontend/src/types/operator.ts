export type InboxRow = {
  email_id: string;
  subject: string | null;
  from_address: string;
  status: string;
  route: string | null;
  routing_confidence: number | null;
  approval_state: string | null;
  updated_at: string;
};

export type CaseDetail = {
  email: {
    id: string;
    subject: string | null;
    from_address: string;
    body_text: string | null;
    status: string;
    thread_id: string | null;
    in_reply_to: string | null;
    references: string | null;
  };
  extraction: unknown;
  routing: unknown;
  approval: unknown;
  jobs: Array<{ id: string; provider: string; action: string; status: string; error_detail: string | null }>;
  attempts: Array<{ attempt_id: string; provider: string; status: string; response_code: number | null; error_detail: string | null; created_at: string }>;
};

export type ApprovalRow = {
  approval_id: string;
  email_id: string;
  subject: string | null;
  from_address: string;
  reason: string;
  proposed_route: string | null;
  created_at: string;
};

export type OperationsSummary = {
  emails_total_today: number;
  emails_processed_today: number;
  failure_count: number;
  hitl_pending_today: number;
  route_distribution: Record<string, number>;
  integration_success_rate: number;
  business_value: {
    processed_fully_automated_today: number;
    processed_after_human_review_today: number;
    assumed_minutes_saved_per_automated_case: number;
    estimated_human_hours_saved_today: number;
    automation_share_of_processed_today: number;
    notes: string;
  };
  latest_completed_eval_snapshot: unknown;
};
