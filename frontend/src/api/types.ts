export interface User {
  id: string;
  email: string;
  username: string;
  is_demo: boolean;
  account_type: string;
}

export interface Membership {
  workspace_id: string;
  role: string;
}

export interface Me {
  id: string;
  email: string;
  username: string;
  is_demo: boolean;
  account_type: string;
  memberships: Membership[];
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Course {
  id: string;
  workspace_id: string;
  name: string;
  code: string;
  term: string;
  description: string;
  join_code: string;
  created_at: string;
}

export interface Assignment {
  id: string;
  course_id: string;
  title: string;
  description: string;
  rubric_version_id: string | null;
  status: string;
  created_at: string;
}

export interface Band {
  id: string;
  level: string;
  score: number;
  description: string;
  order_index: number;
}

export interface RubricItem {
  id: string;
  name: string;
  description: string;
  max_score: number;
  order_index: number;
  bands: Band[];
}

export interface RubricVersion {
  id: string;
  version_no: number;
  frozen_at: string | null;
  items: RubricItem[];
}

export interface Rubric {
  id: string;
  title: string;
  description: string;
  created_at: string;
  versions: RubricVersion[];
}

export interface SubmissionVersion {
  id: string;
  submission_id: string;
  version_no: number;
  filename: string;
  content_type: string;
  created_at: string;
}

export interface Submission {
  id: string;
  assignment_id: string;
  student_id: string;
  student_name: string;
  status: string;
  created_at: string;
  versions: SubmissionVersion[];
}

export interface Evidence {
  id: string;
  quote: string;
  start_offset: number;
  end_offset: number;
  page: number | null;
  ref_type: string;
}

export interface HumanDecision {
  id: string;
  reviewer_id: string;
  final_band_id: string | null;
  feedback: string;
  created_at: string;
}

export interface ReviewItem {
  id: string;
  rubric_item_id: string;
  order_index: number;
  evidence_state: string;
  suggested_band_id: string | null;
  confidence: number;
  explanation: string;
  needs_review: boolean;
  review_flags: string[];
  evidences: Evidence[];
  decision: HumanDecision | null;
}

export interface PublishRecord {
  id: string;
  published_by: string;
  published_at: string;
  score: number;
  feedback: string;
}

export interface Review {
  id: string;
  submission_version_id: string;
  rubric_version_id: string;
  status: string;
  model: string;
  prompt_version: string;
  rules_version: string;
  contradictions: Array<Record<string, unknown>>;
  created_at: string;
  items: ReviewItem[];
  publish: PublishRecord | null;
}

export interface PublishedItem {
  rubric_item_name: string;
  final_band_level: string;
  score: number;
  feedback: string;
}

export interface Published {
  submission_id: string;
  version_no: number;
  score: number;
  feedback: string;
  published_at: string;
  items: PublishedItem[];
}

export interface ParsedDocument {
  id: string;
  submission_version_id: string;
  parser_version: string;
  status: string;
  raw_text: string;
  content: { blocks: Array<Record<string, unknown>> };
  error: string;
}

export interface ItemAvg {
  rubric_item_name: string;
  avg_score: number;
  max_score: number;
}

export interface AssignmentStats {
  assignment_id: string;
  published_count: number;
  avg_score: number | null;
  max_score: number | null;
  min_score: number | null;
  scores: number[];
  item_avg: ItemAvg[];
}

export interface VersionSummary {
  version_id: string;
  version_no: number;
  raw_text: string;
  score: number | null;
  feedback: string;
}

export interface VersionCompare {
  from_version: VersionSummary;
  to_version: VersionSummary;
  score_delta: number | null;
}
