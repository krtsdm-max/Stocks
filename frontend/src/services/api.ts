import axios from 'axios';
import type {
  Portfolio, Position, PositionDetail, ChartData,
  ChatMessage, UserSettings, TrackRecord,
} from '../types';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
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

export const validateTicker = (ticker: string): Promise<{ ticker: string; valid: boolean }> =>
  api.get(`/validate-ticker/${ticker}`).then(r => r.data);

// ── Recommendations ────────────────────────────────────────────────────────────
export const getRecommendations = (positionId: number): Promise<PositionDetail> =>
  api.get(`/recommendations/${positionId}`).then(r => r.data);

export const refreshRecommendations = (positionId: number): Promise<unknown> =>
  api.post(`/recommendations/refresh/${positionId}`).then(r => r.data);

export const refreshAllRecommendations = (): Promise<unknown> =>
  api.post('/recommendations/refresh-all').then(r => r.data);

// ── Chat ───────────────────────────────────────────────────────────────────────
export const sendChatMessage = (data: {
  message: string;
  session_id?: string;
  position_ticker?: string;
}): Promise<ChatMessage> =>
  api.post('/chat', data).then(r => r.data);

export const getChatHistory = (sessionId?: string, limit = 20): Promise<ChatMessage[]> =>
  api.get('/chat/history', { params: { session_id: sessionId, limit } }).then(r => r.data);

// ── Experts ────────────────────────────────────────────────────────────────────
export const getExpertTrackRecord = (expertType: string): Promise<TrackRecord> =>
  api.get(`/experts/${expertType}/track-record`).then(r => r.data);

// ── Settings ───────────────────────────────────────────────────────────────────
export const getSettings = (): Promise<UserSettings> =>
  api.get('/settings').then(r => r.data);

export const updateSettings = (data: { risk_profile: string }): Promise<UserSettings> =>
  api.post('/settings', data).then(r => r.data);
