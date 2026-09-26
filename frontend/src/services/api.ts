import axios from "axios";


const API_BASE = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api";

const api = axios.create({ baseURL: API_BASE });

export type DatasetStats = {
  dataset: {
    total_transactions: number;
    unique_senders: number;
    unique_receivers: number;
    total_amount: number;
  };
  crypto: {
    crypto_transactions: number;
    unique_crypto_wallets: number;
  };
  network: {
    shared_devices: number;
    shared_ips: number;
  };
};

export type Alert = {
  alert_id: string;
  account: string;
  risk_score: number;
  risk_level: string;
  patterns: string[];
  reasons: string[];
  status: string;
};

export type AlertsResponse = {
  status: string;
  total_alerts: number;
  alerts: Alert[];
};

export async function getStats(): Promise<DatasetStats> {
  const response = await api.get<DatasetStats>("/stats");
  return response.data;
}

export async function getAlerts(): Promise<AlertsResponse> {
  const response = await api.get<AlertsResponse>("/alerts");
  return response.data;
}

export async function uploadDataset(file: File): Promise<void> {
  const body = new FormData();
  body.append("file", file);
  await api.post("/upload", body);
}

export function apiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (!error.response) {
      return "Cannot reach the API. Start the backend and try again.";
    }
  }
  return "The request failed. Please try again.";
}
