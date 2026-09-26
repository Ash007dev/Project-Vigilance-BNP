// Target path: frontend/src/services/api.ts
//
// Single source of truth for talking to the REAL risk API (backend built
// and verified in app/api/*.py). Every type here matches what those
// endpoints actually return -- checked directly against the FastAPI route
// code, not assumed.

const API_BASE_URL = "http://localhost:8000/api";

export type RiskLevel = "Low" | "Medium" | "High" | "Critical";

export interface AccountSummary {
  account_id: string;
  risk_score: number;
  risk_level: RiskLevel;
}

export interface RuleResult {
  rule_name: string;
  family: string;
  triggered: boolean;
  raw_value: number | string | null;
  threshold: number | null;
  contribution: number;
  severity: string | null;
  explanation: string;
  evidence: Record<string, unknown>;
}

export interface RiskAssessment {
  account_id: string;
  risk_score: number;
  risk_level: RiskLevel;
  rule_score: number;
  ml_anomaly_score: number | null;
  triggered_rules: RuleResult[];
  reasons: string[];
  feature_summary: Record<string, unknown>;
  generated_at: string;
}

// GET /api/risk-score/{id} returns everything RiskAssessment has, PLUS a
// one-paragraph narrative summary (app/explanation/explainer.py). Mock data
// never had this field -- it's a real backend capability, not available
// via plain GET /api/accounts/{id}.
export interface RiskScoreResponse extends RiskAssessment {
  summary: string;
}

export interface UploadResult {
  transactions_parsed: number;
  rows_skipped: number;
  skip_errors: string[];
  accounts_scored: number;
  ml_model_used: boolean;
  risk_level_counts: Record<RiskLevel, number>;
}

export interface DashboardSummary {
  total_accounts: number;
  total_transactions: number;
  risk_level_counts: Record<RiskLevel, number>;
  top_risk_accounts: AccountSummary[];
}

export interface TimelineEntry {
  transaction_id: string;
  timestamp: string;
  direction: "incoming" | "outgoing";
  counterparty: string | null;
  amount: number | null;
  channel: string | null;
  is_crypto: boolean;
}

export interface NetworkEdge {
  from: string;
  to: string;
  amount: number | null;
  // "indirect" is real: the backend's network endpoint does a genuine
  // 2-hop ego-graph traversal (app/api/graph.py), so an edge can connect
  // two OTHER accounts within the requested account's neighbourhood,
  // neither of which is the account itself.
  direction: "incoming" | "outgoing" | "indirect";
}

export interface NetworkData {
  account_id: string;
  hops: number;
  node_count: number;
  note: string;
  edges: NetworkEdge[];
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      // response wasn't JSON -- fall back to statusText, already set above
    }
    throw new ApiError(response.status, detail);
  }
  return response.json() as Promise<T>;
}

export async function uploadTransactions(file: File): Promise<UploadResult> {
  const formData = new FormData();
  formData.append("file", file);
  // NOTE: large files (100k+ transactions) can take real time to process
  // server-side -- see app/risk/features.py's known performance profile.
  // fetch() itself has no built-in timeout, but if you add one (e.g. via
  // AbortController) elsewhere, make sure it accounts for this.
  const response = await fetch(`${API_BASE_URL}/upload`, {
    method: "POST",
    body: formData,
  });
  return handleResponse<UploadResult>(response);
}

export async function getDashboardSummary(): Promise<DashboardSummary> {
  const response = await fetch(`${API_BASE_URL}/dashboard-summary`);
  return handleResponse<DashboardSummary>(response);
}

export async function getAccounts(params?: {
  riskLevel?: RiskLevel;
  search?: string;
}): Promise<AccountSummary[]> {
  const query = new URLSearchParams();
  if (params?.riskLevel) query.set("risk_level", params.riskLevel);
  if (params?.search) query.set("search", params.search);
  const queryString = query.toString();
  const response = await fetch(`${API_BASE_URL}/accounts${queryString ? `?${queryString}` : ""}`);
  return handleResponse<AccountSummary[]>(response);
}

export async function getAccount(accountId: string): Promise<RiskAssessment> {
  const response = await fetch(`${API_BASE_URL}/accounts/${encodeURIComponent(accountId)}`);
  return handleResponse<RiskAssessment>(response);
}

// Prefer this over getAccount() when you want the narrative summary too
// (Investigation.tsx uses this one).
export async function getRiskScore(accountId: string): Promise<RiskScoreResponse> {
  const response = await fetch(`${API_BASE_URL}/risk-score/${encodeURIComponent(accountId)}`);
  return handleResponse<RiskScoreResponse>(response);
}

export async function getAccountTimeline(accountId: string): Promise<TimelineEntry[]> {
  const response = await fetch(`${API_BASE_URL}/accounts/${encodeURIComponent(accountId)}/timeline`);
  return handleResponse<TimelineEntry[]>(response);
}

export async function getAccountNetwork(accountId: string, hops: number = 2): Promise<NetworkData> {
  const response = await fetch(`${API_BASE_URL}/accounts/${encodeURIComponent(accountId)}/network?hops=${hops}`);
  return handleResponse<NetworkData>(response);
}

// The report endpoint returns raw HTML, not JSON -- there's nothing to
// fetch() and parse here. This just builds the URL; components open it
// directly (new tab / <a href>), letting the browser render or print it.
export function getAccountReportUrl(accountId: string): string {
  return `${API_BASE_URL}/accounts/${encodeURIComponent(accountId)}/report`;
}
