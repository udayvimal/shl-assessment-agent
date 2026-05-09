export interface Message {
  role: "user" | "assistant";
  content: string;
}

export interface Recommendation {
  name: string;
  url: string;
  test_type: string;
  test_types?: string[];
}

export interface ChatResponse {
  reply: string;
  recommendations: Recommendation[];
  suggestions: string[];
  end_of_conversation: boolean;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function sendMessage(messages: Message[]): Promise<ChatResponse> {
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API error ${res.status}: ${err}`);
  }

  return res.json();
}

export const TEST_TYPE_LABELS: Record<string, string> = {
  A: "Ability & Aptitude",
  B: "Biodata & SJT",
  C: "Competencies",
  D: "Development & 360",
  E: "Assessment Exercises",
  K: "Knowledge & Skills",
  P: "Personality & Behavior",
  S: "Simulations",
};

export const TEST_TYPE_COLORS: Record<string, string> = {
  A: "bg-blue-100 text-blue-800",
  B: "bg-purple-100 text-purple-800",
  C: "bg-green-100 text-green-800",
  D: "bg-orange-100 text-orange-800",
  E: "bg-yellow-100 text-yellow-800",
  K: "bg-teal-100 text-teal-800",
  P: "bg-pink-100 text-pink-800",
  S: "bg-indigo-100 text-indigo-800",
};
