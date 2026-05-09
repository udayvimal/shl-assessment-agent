"use client";

import { Message, Recommendation } from "@/lib/api";
import RecommendationCard from "./RecommendationCard";
import { Bot, User, ClipboardList } from "lucide-react";

interface Props {
  message: Message;
  recommendations?: Recommendation[];
}

export default function MessageBubble({ message, recommendations }: Props) {
  const isUser = message.role === "user";
  const hasRecs = !isUser && recommendations && recommendations.length > 0;

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      {/* Avatar */}
      <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
        isUser ? "bg-shl-blue" : "bg-shl-teal"
      }`}>
        {isUser
          ? <User className="w-4 h-4 text-white" />
          : <Bot className="w-4 h-4 text-white" />
        }
      </div>

      <div className={`flex flex-col gap-2 max-w-[82%] ${isUser ? "items-end" : "items-start"}`}>
        {/* Message bubble */}
        <div className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
          isUser
            ? "bg-shl-blue text-white rounded-tr-sm"
            : "bg-white border border-slate-200 text-slate-800 rounded-tl-sm shadow-sm"
        }`}>
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>

        {/* Recommendation cards */}
        {hasRecs && (
          <div className="w-full space-y-2">
            {/* Header row */}
            <div className="flex items-center gap-2 px-1">
              <ClipboardList className="w-4 h-4 text-shl-teal" />
              <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
                Recommended Assessments
              </p>
              <span className="ml-auto bg-shl-blue text-white text-xs font-bold px-2 py-0.5 rounded-full">
                {recommendations!.length}
              </span>
            </div>

            {recommendations!.map((rec, i) => (
              <RecommendationCard key={rec.url} rec={rec} index={i} />
            ))}

            {/* Footer note */}
            <p className="text-xs text-slate-400 px-1 pt-0.5">
              Click any assessment to open its SHL catalog page.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
