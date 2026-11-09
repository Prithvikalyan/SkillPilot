
import { ApiError } from "./client";
import type {
  CareerRoadmap,
  RoadmapMilestone,
  RoadmapRevisionProposal,
  TutorAnswerResponse,
  TutorHistoryResponse,
} from "./types";

const bad = () =>
  new ApiError("invalid", "The server sent data in an unexpected shape.");

const isObj = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null;

const strArr = (v: unknown): string[] =>
  Array.isArray(v)
    ? v.filter((x): x is string => typeof x === "string")
    : [];

/**
 * Task progress must have one boolean per task.
 * Older roadmaps may not have completed_tasks yet.
 */
function parseCompletedTasks(value: unknown, taskCount: number): boolean[] {
  if (!Array.isArray(value) || value.length !== taskCount) {
    return Array.from({ length: taskCount }, () => false);
  }

  // If any value is invalid, initialize all tasks as incomplete.
  if (!value.every((item) => typeof item === "boolean")) {
    return Array.from({ length: taskCount }, () => false);
  }

  return value as boolean[];
}

/** Milestones: only title is required; other fields default safely. */
export function parseMilestone(v: unknown): RoadmapMilestone {
  if (!isObj(v) || typeof v.title !== "string") {
    throw bad();
  }

  const tasks = strArr(v.tasks);

  return {
    title: v.title,
    description: typeof v.description === "string" ? v.description : "",
    topics_to_learn: strArr(v.topics_to_learn),
    tasks,
    completed_tasks: parseCompletedTasks(v.completed_tasks, tasks.length),
    project:
      typeof v.project === "string" && v.project.trim()
        ? v.project
        : null,
    completion_criteria: strArr(v.completion_criteria),
    prerequisites: strArr(v.prerequisites),
  };
}

export function parseRoadmap(v: unknown): CareerRoadmap {
  if (
    !isObj(v) ||
    typeof v.id !== "string" ||
    typeof v.title !== "string" ||
    !Array.isArray(v.milestones)
  ) {
    throw bad();
  }

  return {
    id: v.id,
    user_id: typeof v.user_id === "string" ? v.user_id : "",
    title: v.title,
    target_role: typeof v.target_role === "string" ? v.target_role : null,
    milestones: v.milestones.map(parseMilestone),
    created_at: typeof v.created_at === "string" ? v.created_at : "",
    updated_at: typeof v.updated_at === "string" ? v.updated_at : "",
  };
}

export function parseRoadmapList(v: unknown): CareerRoadmap[] {
  if (!Array.isArray(v)) {
    throw bad();
  }

  return v.map(parseRoadmap);
}

export function parseProposal(v: unknown): RoadmapRevisionProposal {
  if (
    !isObj(v) ||
    typeof v.title !== "string" ||
    !Array.isArray(v.milestones)
  ) {
    throw bad();
  }

  return {
    title: v.title,
    target_role: typeof v.target_role === "string" ? v.target_role : null,
    milestones: v.milestones.map(parseMilestone),
  };
}

export function parseAnswer(v: unknown): TutorAnswerResponse {
  if (
    !isObj(v) ||
    typeof v.answer !== "string" ||
    typeof v.question !== "string"
  ) {
    throw bad();
  }

  return {
    conversation_id: String(v.conversation_id ?? ""),
    question: v.question,
    answer: v.answer,
  };
}

export function parseHistory(v: unknown): TutorHistoryResponse {
  if (!isObj(v) || !Array.isArray(v.messages)) {
    throw bad();
  }

  return {
    conversation_id: String(v.conversation_id ?? ""),
    messages: v.messages.map((m) => {
      if (
        !isObj(m) ||
        typeof m.id !== "number" ||
        typeof m.content !== "string" ||
        (m.role !== "human" && m.role !== "ai")
      ) {
        throw bad();
      }

      return {
        id: m.id,
        role: m.role,
        content: m.content,
        created_at:
          typeof m.created_at === "string" ? m.created_at : "",
      };
    }),
  };
}