import { ChatInterface } from '../components/Chat/ChatInterface';

interface Props {
  defaultTicker?: string;
}

export function ChatPage({ defaultTicker }: Props) {
  return (
    <div>
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Investment Committee Chat</h2>
        <p className="text-sm text-gray-500">
          Ask Victoria (Value), Marcus (Momentum), and Sophie (Risk) anything about your portfolio.
        </p>
      </div>
      <ChatInterface defaultTicker={defaultTicker} />
    </div>
  );
}
