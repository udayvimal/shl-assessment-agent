"use client";

import { Send } from "lucide-react";
import { KeyboardEvent, useRef } from "react";

interface Props {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  disabled?: boolean;
}

export default function ChatInput({ value, onChange, onSend, disabled }: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!disabled && value.trim()) onSend();
    }
  };

  return (
    <div className="flex gap-2 items-end">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
          // Auto-resize
          e.target.style.height = "auto";
          e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px";
        }}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder="Describe the role you're hiring for…"
        rows={1}
        className="flex-1 resize-none rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-shl-teal focus:border-transparent disabled:opacity-50 leading-relaxed overflow-hidden"
        style={{ minHeight: "48px", maxHeight: "120px" }}
      />
      <button
        onClick={onSend}
        disabled={disabled || !value.trim()}
        className="flex-shrink-0 w-11 h-11 rounded-xl bg-shl-blue hover:bg-blue-900 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center transition-colors"
        aria-label="Send message"
      >
        <Send className="w-4 h-4 text-white" />
      </button>
    </div>
  );
}
