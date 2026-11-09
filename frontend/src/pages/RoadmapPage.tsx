
import { useCallback, useEffect, useState } from "react";
import {
  acceptRevision,
  deleteRoadmap,
  getRoadmap,
  listRoadmaps,
  updateTaskCheckpoint,
} from "../api/roadmap";
import { errorMessage, isAbort } from "../api/client";
import type { CareerRoadmap, RoadmapRevisionProposal } from "../api/types";
import { Alert, Button, Dialog, EmptyState, Spinner } from "../components/ui";
import RoadmapView from "../components/RoadmapView";
import GenerateForm from "../components/GenerateForm";
import RevisePanel from "../components/RevisePanel";
import { formatDate } from "../lib/format";

type Panel = "none" | "generate" | "revise";
type ViewMode = "current" | "proposal";

export default function RoadmapPage() {
  const [roadmaps, setRoadmaps] = useState<CareerRoadmap[]>([]);
  const [listLoading, setListLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<CareerRoadmap | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [detailTick, setDetailTick] = useState(0);

  const [panel, setPanel] = useState<Panel>("none");
  const [proposal, setProposal] = useState<{
    roadmapId: string;
    data: RoadmapRevisionProposal;
  } | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("proposal");

  const [confirmAccept, setConfirmAccept] = useState(false);
  const [accepting, setAccepting] = useState(false);
  const [acceptError, setAcceptError] = useState<string | null>(null);

  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const [notice, setNotice] = useState<string | null>(null);

  const loadList = useCallback(
    (signal?: AbortSignal, selectId?: string) => {
      setListLoading(true);
      setListError(null);

      listRoadmaps(signal)
        .then((items) => {
          setRoadmaps(items);
          setSelectedId((current) =>
            selectId ??
            (current && items.some((roadmap) => roadmap.id === current)
              ? current
              : (items[0]?.id ?? null)),
          );
        })
        .catch((err) => {
          if (!isAbort(err)) setListError(errorMessage(err));
        })
        .finally(() => {
          if (!signal?.aborted) setListLoading(false);
        });
    },
    [],
  );

  useEffect(() => {
    const controller = new AbortController();
    loadList(controller.signal);
    return () => controller.abort();
  }, [loadList]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }

    const controller = new AbortController();

    setDetailLoading(true);
    setDetailError(null);

    getRoadmap(selectedId, controller.signal)
      .then(setDetail)
      .catch((err) => {
        if (!isAbort(err)) {
          setDetail(null);
          setDetailError(errorMessage(err));
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setDetailLoading(false);
      });

    return () => controller.abort();
  }, [selectedId, detailTick]);

  const activeProposal =
    proposal && proposal.roadmapId === selectedId ? proposal.data : null;

  const showingProposal =
    activeProposal !== null && viewMode === "proposal";

  async function toggleTask(
    milestoneIndex: number,
    taskIndex: number,
    completed: boolean,
  ): Promise<void> {
    if (!detail || showingProposal) {
      throw new Error("Select a saved roadmap before updating task progress.");
    }

    const roadmapId = detail.id;

    // Save to the backend before updating the visible state.
    await updateTaskCheckpoint(
      roadmapId,
      milestoneIndex,
      taskIndex,
      completed,
    );

    // Update only the task that was successfully saved.
    setDetail((current) => {
      if (!current || current.id !== roadmapId) return current;

      const milestones = current.milestones.map((milestone, index) => {
        if (index !== milestoneIndex) return milestone;

        const completedTasks = milestone.tasks.map(
          (_, taskIndexInMilestone) =>
            taskIndexInMilestone === taskIndex
              ? completed
              : milestone.completed_tasks[taskIndexInMilestone] === true,
        );

        return {
          ...milestone,
          completed_tasks: completedTasks,
        };
      });

      return { ...current, milestones };
    });
  }

  async function accept() {
    if (!selectedId || !activeProposal || accepting) return;

    setAccepting(true);
    setAcceptError(null);

    try {
      const saved = await acceptRevision(selectedId, activeProposal);

      setDetail(saved);
      setRoadmaps((list) =>
        list.map((roadmap) => (roadmap.id === saved.id ? saved : roadmap)),
      );

      setProposal(null);
      setConfirmAccept(false);
      setNotice("Revision saved. This roadmap now shows the new version.");
    } catch (err) {
      setConfirmAccept(false);
      setAcceptError(errorMessage(err));
    } finally {
      setAccepting(false);
    }
  }

  async function removeSelectedRoadmap() {
    if (!detail || deleting) return;

    const roadmapToDelete = detail;
    const roadmapId = roadmapToDelete.id;

    setDeleting(true);
    setDeleteError(null);

    try {
      await deleteRoadmap(roadmapId);

      // Remove only the roadmap confirmed for deletion.
      const remainingRoadmaps = roadmaps.filter(
        (roadmap) => roadmap.id !== roadmapId,
      );

      setRoadmaps(remainingRoadmaps);

      // Clear any unsaved proposal belonging to the deleted roadmap.
      setProposal((current) =>
        current?.roadmapId === roadmapId ? null : current,
      );

      setConfirmDelete(false);
      setPanel("none");
      setConfirmAccept(false);
      setAcceptError(null);

      // Select another roadmap if available.
      setSelectedId(remainingRoadmaps[0]?.id ?? null);
      setDetail(null);
      setDetailError(null);
      setNotice(
        `Roadmap "${roadmapToDelete.title}" was deleted successfully.`,
      );
    } catch (err) {
      setDeleteError(errorMessage(err));
    } finally {
      setDeleting(false);
    }
  }

  function select(id: string) {
    setSelectedId(id);
    setNotice(null);
    setAcceptError(null);
    setDeleteError(null);

    if (panel === "revise") setPanel("none");
  }

  function onCreated(roadmap: CareerRoadmap) {
    setPanel("none");
    setNotice(`Saved a new roadmap: “${roadmap.title}”.`);
    setRoadmaps((list) => [roadmap, ...list]);
    setSelectedId(roadmap.id);
  }

  const heading = (
    <header className="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="font-serif text-2xl font-semibold">Roadmap</h1>
        <p className="mt-1 text-sm text-muted">
          A step-by-step plan toward the role you are aiming for.
        </p>
      </div>

      <Button
        variant={panel === "generate" ? "secondary" : "primary"}
        onClick={() =>
          setPanel(panel === "generate" ? "none" : "generate")
        }
      >
        {panel === "generate" ? "Close form" : "New roadmap"}
      </Button>
    </header>
  );

  let body;

  if (listLoading && roadmaps.length === 0) {
    body = (
      <div className="flex items-center justify-center gap-2 py-20 text-sm text-muted">
        <Spinner label="Loading roadmaps" /> Loading roadmaps…
      </div>
    );
  } else if (listError) {
    body = (
      <Alert
        title="Couldn't load your roadmaps"
        action={
          <Button variant="secondary" onClick={() => loadList()}>
            Try again
          </Button>
        }
      >
        {listError}
      </Alert>
    );
  } else if (roadmaps.length === 0) {
    body =
      panel === "generate" ? null : (
        <EmptyState
          title="No roadmaps yet"
          action={
            <Button onClick={() => setPanel("generate")}>
              Generate your first roadmap
            </Button>
          }
        >
          Tell SkillPilot the role you want, and it will draft your milestones.
        </EmptyState>
      );
  } else {
    body = (
      <div className="grid gap-6 lg:grid-cols-[17rem_minmax(0,1fr)]">
        <nav aria-label="Your roadmaps">
          <h2 className="mb-2 text-sm font-semibold">Your roadmaps</h2>

          <ul className="max-h-60 space-y-1.5 overflow-y-auto lg:max-h-none">
            {roadmaps.map((roadmap) => {
              const current = roadmap.id === selectedId;

              return (
                <li key={roadmap.id}>
                  <button
                    type="button"
                    aria-current={current ? "true" : undefined}
                    onClick={() => select(roadmap.id)}
                    className={`block min-h-11 w-full rounded-lg border px-3 py-2 text-left transition-colors ${
                      current
                        ? "border-brand bg-brand-soft"
                        : "border-line bg-surface hover:border-line-strong"
                    }`}
                  >
                    <span className="block text-sm font-semibold [overflow-wrap:anywhere]">
                      {roadmap.title}
                    </span>

                    <span className="mt-0.5 block text-xs text-muted">
                      {[
                        roadmap.target_role,
                        roadmap.created_at
                          ? formatDate(roadmap.created_at)
                          : "",
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>

        <section aria-live="polite" className="min-w-0 space-y-4">
          {detailLoading ? (
            <div className="flex items-center gap-2 py-16 text-sm text-muted">
              <Spinner label="Loading roadmap" /> Loading roadmap…
            </div>
          ) : detailError ? (
            <Alert
              title="Couldn't open this roadmap"
              action={
                <Button
                  variant="secondary"
                  onClick={() => setDetailTick((tick) => tick + 1)}
                >
                  Try again
                </Button>
              }
            >
              {detailError}
            </Alert>
          ) : detail ? (
            <>
              {activeProposal && (
                <div className="space-y-3 rounded-xl border border-signal/40 bg-signal-soft p-4 text-signal">
                  <p className="text-sm font-semibold">
                    Proposed revision, not saved yet
                  </p>

                  <p className="text-sm">
                    This is a draft from the model. “{detail.title}” stays
                    exactly as it is until you accept the revision.
                  </p>

                  <div className="flex flex-wrap items-center gap-2">
                    <div
                      role="group"
                      aria-label="Which version to show"
                      className="inline-flex rounded-lg border border-signal/40 bg-white p-0.5"
                    >
                      {(["proposal", "current"] as const).map((mode) => (
                        <button
                          key={mode}
                          type="button"
                          aria-pressed={viewMode === mode}
                          onClick={() => setViewMode(mode)}
                          className={`min-h-10 rounded-md px-3 text-sm font-semibold ${
                            viewMode === mode
                              ? "bg-signal text-white"
                              : "text-signal hover:bg-signal-soft"
                          }`}
                        >
                          {mode === "proposal" ? "Proposal" : "Saved version"}
                        </button>
                      ))}
                    </div>

                    <Button
                      onClick={() => {
                        setAcceptError(null);
                        setConfirmAccept(true);
                      }}
                    >
                      Accept revision
                    </Button>

                    <Button
                      variant="secondary"
                      onClick={() => {
                        setProposal(null);
                        setViewMode("proposal");
                      }}
                    >
                      Discard proposal
                    </Button>
                  </div>
                </div>
              )}

              {notice && <Alert tone="info">{notice}</Alert>}

              {acceptError && (
                <Alert title="The revision wasn't saved">
                  {acceptError} The saved roadmap is unchanged, and your
                  proposal is still here.
                </Alert>
              )}

              {deleteError && (
                <Alert title="Couldn't delete this roadmap">
                  {deleteError}
                </Alert>
              )}

              {panel === "revise" ? (
                <RevisePanel
                  roadmapId={detail.id}
                  hasProposal={activeProposal !== null}
                  onClose={() => setPanel("none")}
                  onProposal={(data) => {
                    setProposal({ roadmapId: detail.id, data });
                    setViewMode("proposal");
                    setNotice(null);
                  }}
                />
              ) : (
                <div className="flex flex-wrap justify-end gap-2">
                  <Button
                    variant="secondary"
                    onClick={() => setPanel("revise")}
                  >
                    Ask for a revision
                  </Button>

                  <Button
                    variant="danger"
                    onClick={() => {
                      setDeleteError(null);
                      setConfirmDelete(true);
                    }}
                  >
                    Delete roadmap
                  </Button>
                </div>
              )}

              <div className="rounded-xl border border-line bg-surface p-4 sm:p-6">
                {showingProposal && activeProposal ? (
                  <RoadmapView
                    key="proposal"
                    title={activeProposal.title}
                    targetRole={activeProposal.target_role}
                    milestones={activeProposal.milestones}
                    meta="Proposed version"
                  />
                ) : (
                  <RoadmapView
                    key={detail.id}
                    title={detail.title}
                    targetRole={detail.target_role}
                    milestones={detail.milestones}
                    meta={
                      detail.updated_at
                        ? `Last updated ${formatDate(detail.updated_at)}`
                        : undefined
                    }
                    onToggleTask={toggleTask}
                  />
                )}
              </div>
            </>
          ) : null}
        </section>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6 px-4 py-5 sm:px-6">
      {heading}

      {panel === "generate" && (
        <GenerateForm
          onCreated={onCreated}
          onCancel={() => setPanel("none")}
        />
      )}

      {body}

      <Dialog
        open={confirmAccept}
        onClose={() => setConfirmAccept(false)}
        busy={accepting}
        title="Replace the saved roadmap?"
        footer={
          <>
            <Button
              variant="secondary"
              onClick={() => setConfirmAccept(false)}
              disabled={accepting}
            >
              Keep reviewing
            </Button>

            <Button
              variant="danger"
              onClick={accept}
              loading={accepting}
            >
              {accepting ? "Saving…" : "Replace with revision"}
            </Button>
          </>
        }
      >
        <p>
          This overwrites the title, target role, and every milestone of{" "}
          <strong className="text-ink">“{detail?.title}”</strong> with the
          proposed version.
        </p>

        <p>The previous version is not kept, so this can't be undone.</p>
      </Dialog>

      <Dialog
        open={confirmDelete}
        onClose={() => {
          if (!deleting) setConfirmDelete(false);
        }}
        busy={deleting}
        title="Delete this roadmap?"
        footer={
          <>
            <Button
              variant="secondary"
              onClick={() => setConfirmDelete(false)}
              disabled={deleting}
            >
              Keep roadmap
            </Button>

            <Button
              variant="danger"
              onClick={removeSelectedRoadmap}
              loading={deleting}
            >
              {deleting ? "Deleting…" : "Delete permanently"}
            </Button>
          </>
        }
      >
        <p>
          Are you sure you want to permanently delete{" "}
          <strong className="text-ink">“{detail?.title}”</strong>?
        </p>

        <p>This action cannot be undone. Other roadmaps will not be affected.</p>
      </Dialog>
    </div>
  );
}
