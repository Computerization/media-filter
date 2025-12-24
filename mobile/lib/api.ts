// API configuration
// For local development on device, change to your computer's IP address
// e.g., "http://192.168.1.100:8000"
const API_BASE_URL = "http://localhost:8000";

export interface AnalyzeResponse {
  title: string;
  verdict: "reliable" | "caution" | "misleading";
  verdict_emoji: string;
  summary: string;
  details: string;
  original_text: string;
}

export async function analyzeContent(
  url?: string,
  text?: string
): Promise<AnalyzeResponse> {
  const response = await fetch(`${API_BASE_URL}/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ url, text }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "分析失败，请稍后重试");
  }

  return response.json();
}

export function getVerdictColor(verdict: string): string {
  switch (verdict) {
    case "reliable":
      return "#22C55E";
    case "caution":
      return "#F59E0B";
    case "misleading":
      return "#EF4444";
    default:
      return "#6B7280";
  }
}

export function getVerdictText(verdict: string): string {
  switch (verdict) {
    case "reliable":
      return "内容可信";
    case "caution":
      return "需要谨慎";
    case "misleading":
      return "可能不实";
    default:
      return "未知";
  }
}
