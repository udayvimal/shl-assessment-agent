"use client";

import { useEffect, useRef, useState } from "react";
import { Message, Recommendation, sendMessage } from "@/lib/api";
import MessageBubble from "@/components/MessageBubble";
import TypingIndicator from "@/components/TypingIndicator";
import ChatInput from "@/components/ChatInput";
import { BrainCircuit, RotateCcw } from "lucide-react";

interface DisplayMessage {
  message: Message;
  recommendations?: Recommendation[];
  suggestions?: string[];
}

const STARTER_PROMPTS = [
  "I'm hiring a Java developer who works with stakeholders",
  "Looking for personality and cognitive tests for a sales manager",
  "Need assessments for a mid-level data analyst role",
  "What tests would suit a software engineer, 5 years experience?",
];

export default function Home() {
  const [displayMessages, setDisplayMessages] = useState<DisplayMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [ended, setEnded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [displayMessages, loading]);

  const conversationHistory = (): Message[] =>
    displayMessages.map((d) => d.message);

  const handleSend = async (text?: string) => {
    const content = (text ?? input).trim();
    if (!content || loading || ended) return;

    setInput("");
    setError(null);

    const userMsg: Message = { role: "user", content };
    const history = [...conversationHistory(), userMsg];

    setDisplayMessages((prev) => [...prev, { message: userMsg }]);
    setLoading(true);

    try {
      const res = await sendMessage(history);
      const assistantMsg: Message = { role: "assistant", content: res.reply };
      setDisplayMessages((prev) => [
        ...prev,
        { message: assistantMsg, recommendations: res.recommendations, suggestions: res.suggestions },
      ]);
      if (res.end_of_conversation) setEnded(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setDisplayMessages([]);
    setInput("");
    setLoading(false);
    setEnded(false);
    setError(null);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header className="flex-shrink-0 bg-shl-blue text-white px-4 py-3 flex items-center justify-between shadow-md">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-shl-teal flex items-center justify-center">
            <BrainCircuit className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-base font-bold leading-tight">SHL Assessment Advisor</h1>
            <p className="text-xs text-blue-200 leading-tight">Powered by SHL's Individual Test Catalog</p>
          </div>
        </div>
        <button
          onClick={handleReset}
          className="flex items-center gap-1.5 text-xs text-blue-200 hover:text-white transition-colors px-2 py-1 rounded-lg hover:bg-white/10"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          New chat
        </button>
      </header>

      {/* Chat area */}
      <main className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {displayMessages.length === 0 && !loading && (
          <div className="flex flex-col items-center justify-center h-full gap-6 text-center">
            <div>
              <div className="w-16 h-16 rounded-2xl bg-shl-blue flex items-center justify-center mx-auto mb-4 shadow-lg">
                <BrainCircuit className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-xl font-bold text-slate-800 mb-1">Find the right assessment</h2>
              <p className="text-sm text-slate-500 max-w-xs">
                Describe the role you're hiring for and I'll recommend assessments from the SHL catalog.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-md">
              {STARTER_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => handleSend(prompt)}
                  className="text-left text-xs text-slate-600 bg-white border border-slate-200 rounded-xl px-3 py-2.5 hover:border-shl-teal hover:text-shl-blue hover:shadow-sm transition-all"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}

        {displayMessages.map((d, i) => (
          <MessageBubble
            key={i}
            message={d.message}
            recommendations={d.recommendations}
          />
        ))}

        {loading && <TypingIndicator />}

        {error && (
          <div className="flex justify-center">
            <div className="bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl px-4 py-2">
              {error}
            </div>
          </div>
        )}

        {ended && (
          <div className="flex justify-center">
            <div className="bg-green-50 border border-green-200 text-green-700 text-xs rounded-xl px-4 py-2">
              Conversation complete —{" "}
              <button onClick={handleReset} className="underline font-medium">
                start a new search
              </button>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </main>

      {/* Suggestion chips — shown from last assistant message */}
      {(() => {
        const last = [...displayMessages].reverse().find((d) => d.message.role === "assistant");
        const chips = last?.suggestions ?? [];
        if (!chips.length || loading || ended) return null;
        return (
          <div className="flex-shrink-0 px-4 pt-2 pb-1 bg-slate-50 flex flex-wrap gap-2">
            {chips.map((chip) => (
              <button
                key={chip}
                onClick={() => handleSend(chip)}
                className="text-xs text-shl-blue bg-white border border-shl-teal rounded-full px-3 py-1.5 hover:bg-shl-teal hover:text-white transition-colors shadow-sm"
              >
                {chip}
              </button>
            ))}
          </div>
        );
      })()}

      {/* Input */}
      <footer className="flex-shrink-0 border-t border-slate-200 bg-slate-50 px-4 py-3">
        <ChatInput
          value={input}
          onChange={setInput}
          onSend={() => handleSend()}
          disabled={loading || ended}
        />
        <p className="text-center text-xs text-slate-400 mt-2">
          Only recommends assessments from the official SHL catalog
        </p>
      </footer>
    </div>
  );
}
