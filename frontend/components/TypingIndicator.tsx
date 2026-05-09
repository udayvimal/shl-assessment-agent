"use client";

import { Bot } from "lucide-react";

export default function TypingIndicator() {
  return (
    <div className="flex gap-3 items-start">
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-shl-teal flex items-center justify-center">
        <Bot className="w-4 h-4 text-white" />
      </div>
      <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
        <div className="flex gap-1 items-center h-4">
          <span className="typing-dot w-2 h-2 rounded-full bg-slate-400" />
          <span className="typing-dot w-2 h-2 rounded-full bg-slate-400" />
          <span className="typing-dot w-2 h-2 rounded-full bg-slate-400" />
        </div>
      </div>
    </div>
  );
}
