import axios from 'axios';
import type {
  Portfolio, Position, PositionDetail, ChartData,
  ChatMessage, ExpertChatResponse, UserSettings, TrackRecord,
} from '../types';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

// Chat endpoint needs more time — 3 parallel LLM calls can take up to 60s
const chatApi = axios.create({
  baseURL: '/api',
  timeout: 90000,
});

// ── Portfolio ──────────────────────────────────────────────────────────────────
export const getPortfolio = (): Promise<Portfolio> =>
  api.get('/portfolio').then(r => r.data);

export const getPositionChart = (ticker: string, period: string): Promise<{ data: ChartData[] }> =>
  api.get(`/portfolio/chart/${ticker}`, { params: { period } }).then(r => r.data);

// ── Positions ─────────────────────────────────────────────────────────────────
export const getPositions = (): Promise<Position[]> =>
  api.get('/positions').then(r => r.data);

export const createPosition = (data: {
  ticker: string;
  quantity: number;
  average_purchase_price: number;
  purchase_date: string;
  notes?: string;
}): Promise<Position> =>
  api.post('/positions', data).then(r => r.data);

export const updatePosition = (id: number, data: Partial<{
  quantity: number;
  average_purchase_price: number;
  purchase_date: string;
  notes: string;
}>): Promise<Position> =>
  api.put(`/positions/${id}`, data).then(r => r.data);

export const deletePosition = (id: number): Promise<void> =>
  api.delete(`/positions/${id}`).then(r => r.data);

export const sellPosition = (
  ticker: string,
  quantity: number,
): Promise<{ sold: number; ticker: string; remaining: number }> =>
  api.post(`/positions/${ticker}/sell`, { quantity }).then(r => r.data);

export const validateTicker = (ticker: string): Promise<{
  ticker: string;
  valid: boolean | null;  // null = network unavailable
  name: string | null;
  price: number | null;
  exchange: string | null;
}> =>
  api.get(`/validate-ticker/${ticker}`).then(r => r.data);

// ── Recommendations ────────────────────────────────────────────────────────────
export const getRecommendations = (positionId: number): Promise<PositionDetail> =>
  api.get(`/recommendations/${positionId}`).then(r => r.data);

export const refreshRecommendations = (positionId: number): Promise<unknown> =>
  api.post(`/recommendations/refresh/${positionId}`).then(r => r.data);

export const refreshAllRecommendations = (): Promise<unknown> =>
  api.post('/recommendations/refresh-all', null, { timeout: 120000 }).then(r => r.data);

// ── Chat ───────────────────────────────────────────────────────────────────────
export const sendChatMessage = (data: {
  message: string;
  session_id?: string;
  position_ticker?: string;
}): Promise<ChatMessage> =>
  chatApi.post('/chat', data).then(r => r.data);

export const getChatHistory = (sessionId?: string, limit = 20): Promise<ChatMessage[]> =>
  chatApi.get('/chat/history', { params: { session_id: sessionId, limit } }).then(r => r.data);

type StreamEvent =
  | { type: 'expert'; expert: ExpertChatResponse }
  | { type: 'done'; message_id: number; session_id: string; created_at: string };

export async function* streamChatMessage(data: {
  message: string;
  session_id?: string;
  position_ticker?: string;
}): AsyncGenerator<StreamEvent> {
  const response = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const jsonStr = line.slice(6).trim();
        if (jsonStr) yield JSON.parse(jsonStr) as StreamEvent;
      }
    }
  }
}

// ── Experts ────────────────────────────────────────────────────────────────────
export const getExpertTrackRecord = (expertType: string): Promise<TrackRecord> =>
  api.get(`/experts/${expertType}/track-record`).then(r => r.data);

// ── Settings ───────────────────────────────────────────────────────────────────
export const getSettings = (): Promise<UserSettings> =>
  api.get('/settings').then(r => r.data);

export const updateSettings = (data: { risk_profile: string }): Promise<UserSettings> =>
  api.post('/settings', data).then(r => r.data);

// ── Cash ───────────────────────────────────────────────────────────────────────
export const updateCash = (amount: number): Promise<{ amount: number }> =>
  api.patch('/cash', { amount }).then(r => r.data);
