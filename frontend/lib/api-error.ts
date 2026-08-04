type ErrorObject = Record<string, unknown>;

function messageFromDetail(detail: unknown): string | undefined {
  if (typeof detail === "string" && detail.trim()) return detail.trim();

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === "string") return item.trim();
        if (item && typeof item === "object") {
          const message = (item as ErrorObject).msg;
          return typeof message === "string" ? message.trim() : "";
        }
        return "";
      })
      .filter(Boolean);
    if (messages.length) return messages.join(" ");
  }

  if (detail && typeof detail === "object") {
    const message = (detail as ErrorObject).message;
    if (typeof message === "string" && message.trim()) return message.trim();
  }

  return undefined;
}

export function apiErrorMessage(payload: unknown, fallback: string): string {
  if (payload && typeof payload === "object" && !Array.isArray(payload)) {
    const detail = (payload as ErrorObject).detail;
    return messageFromDetail(detail) ?? fallback;
  }
  return messageFromDetail(payload) ?? fallback;
}
