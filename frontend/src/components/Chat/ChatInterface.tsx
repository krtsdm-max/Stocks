import { useState, useEffect, useRef } from 'react';
import { Send, MessageSquare } from 'lucide-react';
import { streamChatMessage, getChatHistory } from '../../services/api';
import type { ChatMessage, ExpertChatResponse, ExpertType } from '../../types';
import { LoadingSpinner, InlineSpinner } from '../Common/LoadingSpinner';
import { Card } from '../Common/Card';

const EXPERT_STYLES: Record<ExpertType, { bg: string; border: string; nameColor: string; avatar: string }> = {
  value: { bg: 'bg-purple-50', border: 'border-purple-200', nameColor: 'text-purple-700', avatar: 'VC' },
  momentum: { bg: 'bg-blue-50', border: 'border-blue-200', nameColor: 'text-blue-700', avatar: 'MR' },
  risk: { bg: 'bg-orange-50', border: 'border-orange-200', nameColor: 'text-orange-700', avatar: 'SN' },
};

const EXPERT_AVATAR_BG: Record<ExpertType, string> = {
  value: 'bg-purple-200 text-purple-800',
  momentum: 'bg-blue-200 text-blue-800',
  risk: 'bg-orange-200 text-orange-800',
};

const EXPERT_ORDER: ExpertType[] = ['value', 'momentum', 'risk'];

interface StreamingMsg {
  user_message: string;
  expert_responses: ExpertChatResponse[];
  remaining: ExpertType[];
}

interface Props {
  defaultTicker?: string;
}

export function ChatInterface({ defaultTicker }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [ticker, setTicker] = useState(defaultTicker ?? '');
  const [error, setError] = useState<string | null>(null);
  const [streamingMsg, setStreamingMsg] = useState<StreamingMsg | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadHistory();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingMsg]);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const history = await getChatHistory(undefined, 20);
      if (history.length > 0) {
        setMessages(history);
        setSessionId(history[history.length - 1].session_id);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || sending) return;
    const msg = input.trim();
    setInput('');
    setSending(true);
    setError(null);

    setStreamingMsg({ user_message: msg, expert_responses: [], remaining: [...EXPERT_ORDER] });

    try {
      for await (const event of streamChatMessage({
        message: msg,
        session_id: sessionId,
        position_ticker: ticker || undefined,
      })) {
        if (event.type === 'expert') {
          setStreamingMsg(prev => prev ? {
            ...prev,
            expert_responses: [...prev.expert_responses, event.expert],
            remaining: prev.remaining.filter(t => t !== event.expert.expert_type),
          } : null);
        } else if (event.type === 'done') {
          const sid = event.session_id;
          setStreamingMsg(prev => {
            if (!prev) return null;
            const fullMsg: ChatMessage = {
              id: event.message_id,
              user_message: prev.user_message,
              expert_responses: prev.expert_responses,
              session_id: sid,
              created_at: event.created_at,
            };
            setMessages(m => [...m, fullMsg]);
            return null;
          });
          if (!sessionId) setSessionId(sid);
        }
      }
    } catch {
      setStreamingMsg(null);
      setError('Failed to get a response. Please check your connection and try again.');
      setInput(msg);
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const renderExpertCard = (response: ExpertChatResponse) => {
    const style = EXPERT_STYLES[response.expert_type as ExpertType] ?? EXPERT_STYLES.value;
    const avatarBg = EXPERT_AVATAR_BG[response.expert_type as ExpertType] ?? 'bg-gray-200';
    return (
      <div key={response.expert_type} className={`flex gap-3 ${style.bg} rounded-2xl rounded-tl-sm p-4 border ${style.border} max-w-3xl shadow-sm`}>
        <div className={`flex-none w-8 h-8 rounded-full ${avatarBg} flex items-center justify-center text-xs font-bold`}>
          {style.avatar}
        </div>
        <div className="flex-1 min-w-0">
          <p className={`text-xs font-semibold mb-1.5 ${style.nameColor}`}>
            {response.expert_name}
          </p>
          <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{response.response}</p>
        </div>
      </div>
    );
  };

  const renderSpinner = (type: ExpertType) => {
    const style = EXPERT_STYLES[type];
    return (
      <div key={type} className={`flex gap-3 ${style.bg} rounded-2xl p-4 border ${style.border} max-w-xs`}>
        <InlineSpinner />
        <span className={`text-xs ${style.nameColor}`}>Analyzing...</span>
      </div>
    );
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)]">
      {/* Header */}
      <div className="bg-white rounded-t-xl border border-b-0 border-gray-200 p-4 flex items-center gap-3">
        <div className="p-2 bg-blue-100 rounded-lg">
          <MessageSquare size={20} className="text-blue-700" />
        </div>
        <div className="flex-1">
          <h2 className="font-semibold text-gray-900">Investment Committee</h2>
          <p className="text-xs text-gray-500">Ask your three expert advisors anything about your portfolio</p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-500">Context ticker:</label>
          <input
            type="text"
            value={ticker}
            onChange={e => setTicker(e.target.value.toUpperCase())}
            placeholder="e.g. AAPL"
            className="border border-gray-300 rounded px-2 py-1 text-xs w-24 focus:outline-none focus:ring-1 focus:ring-blue-400"
          />
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto bg-gray-50 border-x border-gray-200 p-4 space-y-6">
        {messages.length === 0 && !streamingMsg && (
          <div className="text-center py-12">
            <p className="text-gray-400 text-sm">No messages yet.</p>
            <p className="text-gray-400 text-xs mt-1">
              Try asking: "Should I add more AAPL?" or "How is my portfolio's risk profile?"
            </p>
          </div>
        )}

        {messages.map(msg => (
          <div key={msg.id} className="space-y-3">
            {/* User message */}
            <div className="flex justify-end">
              <div className="bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 max-w-xl text-sm shadow-sm">
                {msg.user_message}
              </div>
            </div>

            {/* Expert responses */}
            <div className="space-y-2">
              {msg.expert_responses.map(renderExpertCard)}
            </div>

            <p className="text-xs text-gray-400 text-right">
              {new Date(msg.created_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
            </p>
          </div>
        ))}

        {/* Streaming in-progress message */}
        {streamingMsg && (
          <div className="space-y-3">
            <div className="flex justify-end">
              <div className="bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 max-w-xl text-sm shadow-sm">
                {streamingMsg.user_message}
              </div>
            </div>
            <div className="space-y-2">
              {streamingMsg.expert_responses.map(renderExpertCard)}
              {streamingMsg.remaining.map(renderSpinner)}
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Error banner */}
      {error && (
        <div className="bg-red-50 border-x border-red-200 px-4 py-2 flex items-center justify-between">
          <span className="text-xs text-red-600">{error}</span>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-600 text-xs ml-4">✕</button>
        </div>
      )}

      {/* Input */}
      <div className="bg-white rounded-b-xl border border-t border-gray-200 p-4">
        <div className="flex gap-3">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask the investment committee... (Enter to send, Shift+Enter for new line)"
            rows={2}
            className="flex-1 border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || sending}
            className="self-end bg-blue-600 text-white rounded-xl px-4 py-3 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {sending ? <InlineSpinner /> : <Send size={18} />}
          </button>
        </div>
        <p className="text-xs text-gray-400 mt-1.5">
          Powered by Claude AI · Messages are saved for context continuity
        </p>
      </div>
    </div>
  );
}
