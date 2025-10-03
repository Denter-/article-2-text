export type JobStatus =
  | 'queued'
  | 'processing'
  | 'learning'
  | 'extracting'
  | 'generating_descriptions'
  | 'completed'
  | 'failed';

export type UserTier = 'free' | 'pro' | 'enterprise';

export interface User {
  id: string;
  email: string;
  tier: UserTier;
  credits: number;
  api_key: string;
  created_at: string;
  last_login_at?: string;
}

export interface Job {
  id: string;
  user_id: string;
  url: string;
  domain: string;
  status: JobStatus;
  worker_type?: string;
  progress_percent: number;
  progress_message?: string;
  result_path?: string;
  markdown_content?: string;
  title?: string;
  author?: string;
  published_at?: string;
  word_count?: number;
  image_count?: number;
  error_message?: string;
  retry_count: number;
  queued_at: string;
  started_at?: string;
  completed_at?: string;
  credits_used: number;
  created_at: string;
  updated_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  token: string;
  user: User;
}

export interface ExtractRequest {
  url: string;
}

export interface ExtractResponse {
  job: Job;
  message: string;
}

export interface JobsResponse {
  jobs: Job[];
  count: number;
}

export interface JobResponse {
  job: Job;
}

export interface QualityIssue {
  type: 'navigation' | 'javascript' | 'structure' | 'content';
  severity: 'high' | 'medium' | 'low';
  message: string;
}



