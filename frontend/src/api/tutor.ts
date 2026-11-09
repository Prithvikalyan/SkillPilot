import { request } from "./client";
import { parseAnswer, parseHistory } from "./guards";
import type { TutorAnswerResponse, TutorHistoryResponse } from "./types";

/** The backend's default conversation. The app is single-user, so one conversation is used. */
export const DEFAULT_CONVERSATION_ID = "default";

/** Backend allows 1–100 messages per history request (default 20). */
export const HISTORY_LIMIT = 100;

export const MAX_QUESTION_LENGTH = 2000;

// POST /tutor/ask
export async function askTutor(question: string, conversationId = DEFAULT_CONVERSATION_ID): Promise<TutorAnswerResponse> {
  const data = await request<unknown>("/tutor/ask", {
    method: "POST",
    body: { question, conversation_id: conversationId },
    timeoutMs: 180_000,
  });
  return parseAnswer(data);
}

// GET /tutor/history
export async function getTutorHistory(conversationId = DEFAULT_CONVERSATION_ID, signal?: AbortSignal): Promise<TutorHistoryResponse> {
  const data = await request<unknown>("/tutor/history", {
    query: { conversation_id: conversationId, limit: HISTORY_LIMIT },
    signal,
  });
  return parseHistory(data);
}



// DELETE /tutor/conversations/:conversationId
export async function deleteTutorConversation(
  conversationId: string,
): Promise<void> {
  await request<unknown>(
    `/tutor/conversations/${encodeURIComponent(conversationId)}`,
    {
      method: "DELETE",
    }
  );
}