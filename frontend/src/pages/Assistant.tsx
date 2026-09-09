import { useState, useRef, useEffect } from 'react';
import { useLanguage } from '../contexts/LanguageContext';
import { assistantAPI, parseApiError } from '../services/api';
import { Send, Bot, User } from 'lucide-react';
import PageHeader from '../components/PageHeader';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  source?: string;
  model?: string;
}

const suggestedQuestions: Record<string, string[]> = {
  en: [
    'Should I irrigate today?',
    'How is my crop doing?',
    'What is my current disease status?',
    'How much have I spent?',
    'What should I monitor today?',
  ],
  te: [
    'నేను ఈ రోజు నీటిపారుదల చేయాలా?',
    'నా పంట ఎలా ఉంది?',
    'నా ప్రస్తుత వ్యాధి స్థితి ఏమిటి?',
    'నేను ఎంత ఖర్చు చేశాను?',
    'ఈ రోజు ఏమి పరిశీలించాలి?',
  ],
};

export default function Assistant() {
  const { language } = useLanguage();

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async (question: string) => {
    if (!question.trim() || loading) return;

    const userMessage: Message = { role: 'user', content: question };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);
    setError('');

    try {
      const res = await assistantAPI.chat({
        question,
        language,
      });

      const assistantMessage: Message = {
        role: 'assistant',
        content: res.data.answer,
        source: res.data.source,
        model: res.data.model,
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (err: unknown) {
      setError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  return (
    <div className="page-container flex flex-col h-[calc(100vh-8rem)]">
      <PageHeader 
        title="HARVEX AI Assistant" 
        subtitle="Ask anything about your farm"
        icon={<Bot className="h-6 w-6" />}
      />

      {/* Suggested Questions */}
      {messages.length === 0 && (
        <div className="card">
          <p className="text-sm text-charcoal-500 mb-3">Suggested questions:</p>
          <div className="flex flex-wrap gap-2">
            {suggestedQuestions[language]?.map((q, i) => (
              <button
                key={i}
                onClick={() => sendMessage(q)}
                className="px-4 py-2 bg-primary-50 text-primary-700 rounded-xl text-sm font-medium 
                         hover:bg-primary-100 transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 py-4">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                msg.role === 'user'
                  ? 'bg-primary-600 text-white rounded-br-md'
                  : 'bg-white border border-charcoal-200 text-charcoal-800 rounded-bl-md'
              }`}
            >
              <div className="flex items-start gap-2">
                {msg.role === 'assistant' && (
                  <Bot className="h-5 w-5 text-primary-600 mt-0.5 flex-shrink-0" />
                )}
                <div>
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                  {msg.source === 'fallback' && (
                    <p className="text-xs text-charcoal-400 mt-2 italic">
                      (AI unavailable - using fallback response)
                    </p>
                  )}
                </div>
                {msg.role === 'user' && (
                  <User className="h-5 w-5 text-primary-200 mt-0.5 flex-shrink-0" />
                )}
              </div>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-charcoal-200 rounded-2xl rounded-bl-md px-4 py-3">
              <div className="flex items-center gap-2">
                <Bot className="h-5 w-5 text-primary-600" />
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-charcoal-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 bg-charcoal-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 bg-charcoal-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Error */}
      {error && (
        <div className="p-3 bg-danger-light border border-danger/20 rounded-xl text-danger-dark text-sm mb-4">
          {error}
        </div>
      )}

      {/* Input */}
      <form onSubmit={handleSubmit} className="flex gap-3">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={language === 'te' ? 'మీ ప్రశ్నను అడగండి...' : 'Ask about your farm...'}
          className="input-field flex-1"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="btn-primary px-6"
        >
          <Send className="h-5 w-5" />
        </button>
      </form>
    </div>
  );
}
