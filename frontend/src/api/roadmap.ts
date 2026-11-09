
import { request } from "./client";
import { parseProposal, parseRoadmap, parseRoadmapList } from "./guards";
import type {
  CareerRoadmap,
  RoadmapGenerateRequest,
  RoadmapRevisionProposal,
} from "./types";

// GET /roadmap/list
export async function listRoadmaps(
  signal?: AbortSignal,
): Promise<CareerRoadmap[]> {
  return parseRoadmapList(
    await request<unknown>("/roadmap/list", { signal }),
  );
}

// GET /roadmap/{roadmap_id}
export async function getRoadmap(
  id: string,
  signal?: AbortSignal,
): Promise<CareerRoadmap> {
  return parseRoadmap(
    await request<unknown>(`/roadmap/${encodeURIComponent(id)}`, {
      signal,
    }),
  );
}

// POST /roadmap/generate — generates AND saves a new roadmap.
export async function generateRoadmap(
  payload: RoadmapGenerateRequest,
): Promise<CareerRoadmap> {
  return parseRoadmap(
    await request<unknown>("/roadmap/generate", {
      method: "POST",
      body: payload,
      timeoutMs: 300_000,
    }),
  );
}

// POST /roadmap/revise — returns a proposal only; nothing is saved.
export async function proposeRevision(
  roadmapId: string,
  instructions: string,
): Promise<RoadmapRevisionProposal> {
  return parseProposal(
    await request<unknown>("/roadmap/revise", {
      method: "POST",
      body: { roadmap_id: roadmapId, instructions },
      timeoutMs: 300_000,
    }),
  );
}

// POST /roadmap/{roadmap_id}/accept-revision — overwrites the stored roadmap.
export async function acceptRevision(
  roadmapId: string,
  proposal: RoadmapRevisionProposal,
): Promise<CareerRoadmap> {
  return parseRoadmap(
    await request<unknown>(
      `/roadmap/${encodeURIComponent(roadmapId)}/accept-revision`,
      {
        method: "POST",
        body: proposal,
      },
    ),
  );
}

// PATCH /roadmap/{roadmap_id}/milestones/{milestone_index}/tasks/{task_index}
export async function updateTaskCheckpoint(
  roadmapId: string,
  milestoneIndex: number,
  taskIndex: number,
  completed: boolean,
): Promise<void> {
  await request<unknown>(
    `/roadmap/${encodeURIComponent(roadmapId)}/milestones/${milestoneIndex}/tasks/${taskIndex}`,
    {
      method: "PATCH",
      body: { completed },
    },
  );
}

// DELETE /roadmap/{roadmap_id} — permanently deletes the selected roadmap.
export async function deleteRoadmap(roadmapId: string): Promise<void> {
  await request<unknown>(
    `/roadmap/${encodeURIComponent(roadmapId)}`,
    {
      method: "DELETE",
    },
  );
}
