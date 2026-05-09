"use client";

import { ExternalLink } from "lucide-react";
import { Recommendation, TEST_TYPE_COLORS, TEST_TYPE_LABELS } from "@/lib/api";

interface Props {
  rec: Recommendation;
  index: number;
}

export default function RecommendationCard({ rec, index }: Props) {
  // Show all type codes if available, else fall back to primary
  const types = (rec.test_types && rec.test_types.length > 0)
    ? rec.test_types
    : [rec.test_type];

  return (
    <a
      href={rec.url}
      target="_blank"
      rel="noopener noreferrer"
      className="group flex items-start gap-3 p-3 rounded-xl border border-slate-200 bg-white hover:border-shl-teal hover:shadow-sm transition-all"
    >
      {/* Number badge */}
      <span className="flex-shrink-0 w-6 h-6 rounded-full bg-shl-blue text-white text-xs font-bold flex items-center justify-center mt-0.5">
        {index + 1}
      </span>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-slate-800 group-hover:text-shl-blue leading-snug">
          {rec.name}
        </p>

        {/* Type badges — one per code */}
        <div className="flex flex-wrap gap-1 mt-1.5">
          {types.map((code) => (
            <span
              key={code}
              className={`inline-block text-xs font-medium px-2 py-0.5 rounded-full ${
                TEST_TYPE_COLORS[code] ?? "bg-slate-100 text-slate-700"
              }`}
            >
              {TEST_TYPE_LABELS[code] ?? code}
            </span>
          ))}
        </div>

        {/* View link hint */}
        <p className="text-xs text-slate-400 mt-1.5 group-hover:text-shl-teal transition-colors">
          View on SHL catalog ↗
        </p>
      </div>

      <ExternalLink className="flex-shrink-0 w-4 h-4 text-slate-400 group-hover:text-shl-teal mt-0.5 transition-colors" />
    </a>
  );
}
