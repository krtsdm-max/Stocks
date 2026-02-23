export type RiskProfile = 'conservative' | 'balanced' | 'aggressive';
export type ExpertType = 'value' | 'momentum' | 'risk';
export type Action = 'hold' | 'buy' | 'add' | 'reduce' | 'sell' | 'close';
export type ConsensusLevel = 'unanimous' | 'majority' | 'split';

export interface Position {
  id: number;
  ticker: string;
  quantity: number;
  average_purchase_price: number;
  purchase_date: string;
  notes?: string;
  created_at: string;
  updated_at: string;
  current_price?: number;
  day_change?: number;
  day_change_pct?: number;
  total_value?: number;
  total_pnl?: number;
  total_pnl_pct?: number;
  portfolio_weight?: number;
}

export interface ExpertVote {
  action: Action;
  target_price?: number;
  quantity_change?: number;
  confidence_level: number;
  reasoning: string;
}

export interface ConsensusDecision {
  aggregated_action: Action;
  consensus_level: ConsensusLevel;
  expert_votes: Record<ExpertType, ExpertVote>;
  timestamp: string;
}

export interface PortfolioPosition {
  id: number;
  ticker: string;
  quantity: number;
  average_purchase_price: number;
  purchase_date: string;
  notes?: string;
  current_price?: number;
  day_change?: number;
  day_change_pct?: number;
  total_value: number;
  total_pnl: number;
  total_pnl_pct: number;
  portfolio_weight: number;
  latest_consensus?: ConsensusDecision;
}

export interface Portfolio {
  nav: number;
  total_cost: number;
  total_pnl: number;
  total_pnl_pct: number;
  day_pnl: number;
  day_pnl_pct: number;
  positions_count: number;
  market_open: boolean;
  last_updated: string;
  positions: PortfolioPosition[];
}

export interface ExpertRecommendation {
  id: number;
  position_id: number;
  expert_type: ExpertType;
  recommendation_action: Action;
  target_price?: number;
  quantity_change?: number;
  confidence_level: number;
  reasoning: string;
  market_snapshot: Record<string, unknown>;
  created_at: string;
  actual_price_1w?: number;
  actual_price_1m?: number;
  actual_price_3m?: number;
}

export interface PositionDetail {
  position_id: number;
  ticker: string;
  consensus?: ConsensusDecision;
  expert_recommendations: Record<ExpertType, {
    action: Action;
    target_price?: number;
    quantity_change?: number;
    confidence_level: number;
    reasoning: string;
    created_at: string;
  }>;
  history: Array<{
    id: number;
    expert_type: ExpertType;
    action: Action;
    target_price?: number;
    confidence_level: number;
    reasoning: string;
    created_at: string;
    actual_price_1w?: number;
    actual_price_1m?: number;
    snapshot_price?: number;
  }>;
  fundamentals?: {
    name?: string;
    sector?: string;
    industry?: string;
    pe_ratio?: number;
    pb_ratio?: number;
    dividend_yield?: number;
    market_cap?: number;
    beta?: number;
    '52w_high'?: number;
    '52w_low'?: number;
  };
  technicals?: {
    rsi?: number;
    rsi_signal?: string;
    ma50?: number;
    ma200?: number;
    above_ma50?: boolean;
    above_ma200?: boolean;
    golden_cross?: boolean;
    macd_histogram?: number;
    macd_bullish?: boolean;
    momentum_3m_pct?: number;
    momentum_6m_pct?: number;
    volatility_annual_pct?: number;
    high_52w?: number;
    low_52w?: number;
  };
}

export interface ChartData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface ExpertChatResponse {
  expert_type: ExpertType;
  expert_name: string;
  response: string;
}

export interface ChatMessage {
  id: number;
  user_message: string;
  expert_responses: ExpertChatResponse[];
  session_id: string;
  created_at: string;
}

export interface UserSettings {
  id: number;
  risk_profile: RiskProfile;
  max_position_concentration: number;
  sector_concentration_limit: number;
  target_volatility: string;
}

export interface TrackRecord {
  expert_type: ExpertType;
  expert_name: string;
  expert_title: string;
  philosophy: string;
  track_record: {
    total_recommendations: number;
    evaluated_1w: number;
    direction_accuracy_pct?: number;
    avg_price_error_1w_pct?: number;
    avg_price_error_1m_pct?: number;
    avg_price_error_3m_pct?: number;
  };
  action_distribution: Record<string, number>;
  recent_recommendations: Array<{
    id: number;
    ticker: string;
    action: Action;
    target_price?: number;
    confidence_level: number;
    reasoning: string;
    created_at: string;
    actual_price_1w?: number;
    actual_price_1m?: number;
  }>;
}
