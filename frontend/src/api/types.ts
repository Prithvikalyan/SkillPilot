
// Types mirror the FastAPI schemas in app/schemas/tutor.py and app/schemas/roadmap.py.

export type TutorRole = "human" | "ai";

export interface TutorAskRequest {
  question: string; // 1–2000 characters
  conversation_id: string; // 1–100 characters, backend default "default"
}

export interface TutorAnswerResponse {
  conversation_id: string;
  question: string;
  answer: string;
}

export interface TutorHistoryMessage {
  id: number;
  role: TutorRole;
  content: string;
  created_at: string; // ISO 8601
}

export interface TutorHistoryResponse {
  conversation_id: string;
  messages: TutorHistoryMessage[]; // oldest first
}

export interface RoadmapMilestone {
  title: string;
  description: string;
  topics_to_learn: string[];
  tasks: string[];
  completed_tasks: boolean[];
  project: string | null;
  completion_criteria: string[];
  prerequisites: string[];
}

export interface CareerRoadmap {
  id: string;
  user_id: string;
  title: string;
  target_role: string | null;
  milestones: RoadmapMilestone[];
  created_at: string;
  updated_at: string;
}

export interface RoadmapGenerateRequest {
  target_role: string; // 1–200 characters
  current_skills: string[];
  background: string | null;
}

export interface RoadmapReviseRequest {
  roadmap_id: string;
  instructions: string; // 1–2000 characters
}

// Returned by POST /roadmap/revise (not saved) and sent to POST /roadmap/{id}/accept-revision.
export interface RoadmapRevisionProposal {
  title: string;
  target_role: string | null;
  milestones: RoadmapMilestone[];
}
