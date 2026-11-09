
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";
import Markdown from "react-markdown";
import {
  askTutor,
  getTutorHistory,
  deleteTutorConversation,
  HISTORY_LIMIT,
  MAX_QUESTION_LENGTH,
} from "../api/tutor";

import { errorMessage, isAbort } from "../api/client";
import type { TutorRole } from "../api/types";
import { Alert, Button, Dialog, EmptyState, Spinner } from "../components/ui";
import { formatTime } from "../lib/format";

interface ChatMessage {
  key: string;
  role: TutorRole;
  content: string;
  createdAt?: string;
}

interface ChatConversation {
  id: string;
  title: string;
  createdAt: string;
}

const STORAGE_KEY = "skillpilot-tutor-conversations";
const SELECTED_KEY = "skillpilot-tutor-selected";

const DEFAULT_CONVERSATION: ChatConversation = {
  id: "default",
  title: "Previous conversation",
  createdAt: new Date().toISOString(),
};

function readConversations(): ChatConversation[] {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);

    if (saved) {
      const parsed: unknown = JSON.parse(saved);

      if (
        Array.isArray(parsed) &&
        parsed.every(
          (item) =>
            item &&
            typeof item.id === "string" &&
            typeof item.title === "string" &&
            typeof item.createdAt === "string",
        )
      ) {
        const conversations = parsed as ChatConversation[];

        if (
          conversations.length > 0 &&
          conversations.some((chat) => chat.id === "default")
        ) {
          return conversations;
        }

        return [DEFAULT_CONVERSATION, ...conversations];
      }
    }
  } catch {
    // Use the default conversation if saved metadata is invalid.
  }

  return [DEFAULT_CONVERSATION];
}

function readSelectedConversation(conversations: ChatConversation[]): string {
  try {
    const savedId = localStorage.getItem(SELECTED_KEY);

    if (savedId && conversations.some((chat) => chat.id === savedId)) {
      return savedId;
    }
  } catch {
    // Fall back to the default conversation.
  }

  return "default";
}

function Bubble({ message }: { message: ChatMessage }) {
  const human = message.role === "human";

  return (
    <li className={`flex flex-col ${human ? "items-end" : "items-start"}`}>
      <p className="mb-1 px-1 text-xs text-muted">
        <span className="font-semibold text-ink">
          {human ? "You" : "SkillPilot"}
        </span>
        {message.createdAt && formatTime(message.createdAt) ? (
          <span> · {formatTime(message.createdAt)}</span>
        ) : null}
      </p>

      <div
        className={`max-w-[min(42rem,92%)] rounded-2xl px-4 py-3 text-[0.95rem] leading-relaxed [overflow-wrap:anywhere] ${
          human
            ? "rounded-br-md bg-brand text-white"
            : "rounded-bl-md border border-line bg-surface"
        }`}
      >
        {human ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="answer">
            <Markdown>{message.content}</Markdown>
          </div>
        )}
      </div>
    </li>
  );
}

export default function TutorPage() {
  const [conversations, setConversations] =
    useState<ChatConversation[]>(readConversations);

  const [selectedConversationId, setSelectedConversationId] = useState(
    () => readSelectedConversation(readConversations()),
  );

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const [chatToDelete, setChatToDelete] = useState<ChatConversation | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const sendingRef = useRef(false);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const selectedConversation = conversations.find(
    (chat) => chat.id === selectedConversationId,
  );

  // Save chat metadata and the currently selected chat.
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
      localStorage.setItem(SELECTED_KEY, selectedConversationId);
    } catch {
      // Chat functionality can still work if browser storage is unavailable.
    }
  }, [conversations, selectedConversationId]);

  // Load only the history belonging to the selected conversation.
  const loadHistory = useCallback(
    (conversationId: string, signal?: AbortSignal) => {
      setLoadingHistory(true);
      setHistoryError(null);
      setMessages([]);

      getTutorHistory(conversationId, signal)
        .then((history) => {
          if (signal?.aborted) return;

          setMessages(
            history.messages.map((message) => ({
              key: `db-${message.id}`,
              role: message.role,
              content: message.content,
              createdAt: message.created_at,
            })),
          );
        })
        .catch((error) => {
          if (!isAbort(error) && !signal?.aborted) {
            setHistoryError(errorMessage(error));
          }
        })
        .finally(() => {
          if (!signal?.aborted) {
            setLoadingHistory(false);
          }
        });
    },
    [],
  );

  useEffect(() => {
    const controller = new AbortController();

    loadHistory(selectedConversationId, controller.signal);

    return () => controller.abort();
  }, [loadHistory, selectedConversationId]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages, sending]);

  function createNewChat() {
    if (sendingRef.current) return;

    const conversation: ChatConversation = {
      id: crypto.randomUUID(),
      title: "New chat",
      createdAt: new Date().toISOString(),
    };

    setConversations((current) => [...current, conversation]);
    setSelectedConversationId(conversation.id);
    setDraft("");
    setSendError(null);
  }

  function selectChat(conversationId: string) {
    if (
      sendingRef.current ||
      conversationId === selectedConversationId
    ) {
      return;
    }

    setSelectedConversationId(conversationId);
    setDraft("");
    setSendError(null);
  }

  async function send() {
    const question = draft.trim();

    if (
      !question ||
      sendingRef.current ||
      loadingHistory ||
      historyError
    ) {
      return;
    }

    const conversationId = selectedConversationId;
    const pendingKey = `pending-${Date.now()}`;

    sendingRef.current = true;
    setSending(true);
    setSendError(null);
    setDraft("");

    setMessages((current) => [
      ...current,
      {
        key: pendingKey,
        role: "human",
        content: question,
        createdAt: new Date().toISOString(),
      },
    ]);

    try {
      const response = await askTutor(question, conversationId);

      setMessages((current) => [
        ...current,
        {
          key: `ai-${Date.now()}`,
          role: "ai",
          content: response.answer,
          createdAt: new Date().toISOString(),
        },
      ]);

      // Give the first question a useful title.
      setConversations((current) =>
        current.map((chat) =>
          chat.id === conversationId && chat.title === "New chat"
            ? {
                ...chat,
                title:
                  question.length > 32
                    ? `${question.slice(0, 32)}…`
                    : question,
              }
            : chat,
        ),
      );
    } catch (error) {
      setMessages((current) =>
        current.filter((message) => message.key !== pendingKey),
      );
      setDraft(question);
      setSendError(errorMessage(error));
    } finally {
      sendingRef.current = false;
      setSending(false);
      inputRef.current?.focus();
    }
  }


  async function confirmDeleteChat() {
    if (!chatToDelete || deleting || sendingRef.current) return;
  
    const conversationId = chatToDelete.id;
  
    setDeleting(true);
    setDeleteError(null);
  
    try {
      await deleteTutorConversation(conversationId);
  
      const remaining = conversations.filter(
        (chat) => chat.id !== conversationId,
      );
  
      setConversations(remaining);
      setChatToDelete(null);
  
      if (selectedConversationId === conversationId) {
        const nextChat = remaining[0] ?? {
          id: "default",
          title: "Previous conversation",
          createdAt: new Date().toISOString(),
        };
  
        if (remaining.length === 0) {
          setConversations([nextChat]);
        }
  
        setSelectedConversationId(nextChat.id);
      }
    } catch (error) {
      setDeleteError(errorMessage(error));
    } finally {
      setDeleting(false);
    }
  }




  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (
      event.key === "Enter" &&
      !event.shiftKey &&
      !event.nativeEvent.isComposing
    ) {
      event.preventDefault();
      void send();
    }
  }

  const nearLimit = draft.length > MAX_QUESTION_LENGTH * 0.9;

  return (
    <div className="mx-auto flex h-full w-full max-w-6xl flex-col px-4 sm:px-6">
      <header className="py-5">
        <h1 className="font-serif text-2xl font-semibold">Tutor</h1>
        <p className="mt-1 text-sm text-muted">
          Ask questions, start separate chats, and revisit previous conversations.
        </p>
      </header>

      <div className="flex min-h-0 flex-1 flex-col gap-4 md:flex-row">
        <aside className="flex shrink-0 flex-col gap-3 rounded-xl border border-line bg-surface p-3 md:w-56">
          <Button
            type="button"
            onClick={createNewChat}
            disabled={sending}
            className="w-full"
          >
            + New Chat
          </Button>

          <h2 className="px-1 text-xs font-semibold uppercase tracking-wide text-muted">
            Your chats
          </h2>

          <nav
            aria-label="Tutor conversations"
            className="flex max-h-40 flex-col gap-1 overflow-y-auto md:max-h-none"
          >
            {conversations.map((chat) => {
              const selected = chat.id === selectedConversationId;

              return (
                <div key={chat.id} className="flex items-center gap-1">
                  <button
                    type="button"
                    disabled={sending || deleting}
                    onClick={() => selectChat(chat.id)}
                    aria-current={selected ? "page" : undefined}
                    className={`min-w-0 flex-1 rounded-lg px-3 py-2 text-left text-sm transition-colors disabled:cursor-not-allowed ${
                      selected
                        ? "bg-brand-soft font-semibold text-brand-strong"
                        : "text-ink hover:bg-paper"
                    }`}
                  >
                    <span className="block truncate">{chat.title}</span>
                    <span className="mt-1 block text-xs text-muted">
                      {chat.id === "default" ? "Existing chat" : "Separate chat"}
                    </span>
                  </button>
              
                  {chat.id !== "default" && (
                    <Button
                      type="button"
                      variant="ghost"
                      disabled={sending || deleting}
                      onClick={() => {
                        setDeleteError(null);
                        setChatToDelete(chat);
                      }}
                      aria-label={`Delete ${chat.title}`}
                      className="px-2"
                    >
                      Delete
                    </Button>
                  )}
                </div>
              );
            })}
          </nav>
        </aside>

        <section className="flex min-h-0 min-w-0 flex-1 flex-col">
          <div className="mb-3">
            <h2 className="truncate text-sm font-semibold text-ink">
              {selectedConversation?.title ?? "Tutor conversation"}
            </h2>
          </div>

          <div
            className="min-h-0 flex-1 overflow-y-auto rounded-xl border border-line bg-paper/60 p-3 sm:p-5"
            tabIndex={0}
            aria-label="Conversation"
          >
            {loadingHistory ? (
              <div className="flex h-full items-center justify-center gap-2 text-sm text-muted">
                <Spinner label="Loading conversation" />
                Loading conversation…
              </div>
            ) : historyError ? (
              <div className="mx-auto max-w-lg pt-6">
                <Alert
                  title="Couldn't load the conversation"
                  action={
                    <Button
                      variant="secondary"
                      onClick={() =>
                        loadHistory(selectedConversationId)
                      }
                    >
                      Try again
                    </Button>
                  }
                >
                  {historyError}
                </Alert>
              </div>
            ) : messages.length === 0 && !sending ? (
              <div className="flex h-full items-center justify-center">
                <EmptyState title="Start the conversation">
                  Ask your first question below. For example: “What is the
                  difference between a list and a tuple in Python?”
                </EmptyState>
              </div>
            ) : (
              <>
                {messages.length >= HISTORY_LIMIT && (
                  <p className="mb-4 text-center text-xs text-muted">
                    Showing the latest {HISTORY_LIMIT} messages.
                  </p>
                )}

                <ol
                  role="log"
                  aria-live="polite"
                  aria-label="Messages"
                  className="space-y-5"
                >
                  {messages.map((message) => (
                    <Bubble key={message.key} message={message} />
                  ))}

                  {sending && (
                    <li className="flex flex-col items-start">
                      <p className="mb-1 px-1 text-xs font-semibold">
                        SkillPilot
                      </p>
                      <div className="flex items-center gap-2 rounded-2xl rounded-bl-md border border-line bg-surface px-4 py-3 text-sm text-muted">
                        <Spinner className="size-4" />
                        Writing an answer…
                      </div>
                    </li>
                  )}
                </ol>
              </>
            )}

            <div ref={endRef} />
          </div>

          <form
            className="py-4"
            onSubmit={(event) => {
              event.preventDefault();
              void send();
            }}
          >
            {sendError && (
              <div className="mb-3">
                <Alert title="Your question wasn't answered">
                  {sendError} Your text is still in the box so you can send it
                  again.
                </Alert>
              </div>
            )}

            <label htmlFor="question" className="sr-only">
              Your question
            </label>

            <div className="flex items-end gap-2 rounded-xl border border-line-strong bg-surface p-2 focus-within:border-brand focus-within:ring-2 focus-within:ring-brand/30">
              <textarea
                id="question"
                ref={inputRef}
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={onKeyDown}
                maxLength={MAX_QUESTION_LENGTH}
                rows={2}
                placeholder="Ask a question…"
                aria-describedby="composer-help"
                className="max-h-48 min-h-12 flex-1 resize-y bg-transparent px-2 py-1.5 text-base outline-none focus-visible:outline-none"
              />

              <Button
                type="submit"
                disabled={
                  !draft.trim() ||
                  loadingHistory ||
                  Boolean(historyError)
                }
                loading={sending}
                aria-label={sending ? "Waiting for answer" : "Send question"}
              >
                {sending ? "Sending" : "Send"}
              </Button>
            </div>

            <p
              id="composer-help"
              className="mt-1.5 flex justify-between px-1 text-xs text-muted"
            >
              <span>Enter to send, Shift+Enter for a new line</span>
              <span
                className={nearLimit ? "font-semibold text-signal" : ""}
              >
                {draft.length}/{MAX_QUESTION_LENGTH}
              </span>
            </p>
          </form>
        </section>
      </div>
      <Dialog
  open={chatToDelete !== null}
  onClose={() => {
    if (!deleting) {
      setChatToDelete(null);
      setDeleteError(null);
    }
  }}
  title="Delete conversation?"
  busy={deleting}
  footer={
    <>
      <Button
        type="button"
        variant="secondary"
        disabled={deleting}
        onClick={() => setChatToDelete(null)}
      >
        Cancel
      </Button>
      <Button
        type="button"
        variant="danger"
        loading={deleting}
        onClick={() => void confirmDeleteChat()}
      >
        Delete permanently
      </Button>
    </>
  }
>
  This permanently deletes the selected chat and its stored messages. This
  action cannot be undone.

  {deleteError && <Alert title="Deletion failed">{deleteError}</Alert>}
</Dialog>
    </div>
  );
}
