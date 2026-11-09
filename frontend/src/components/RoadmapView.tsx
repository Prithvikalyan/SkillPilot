
import { useId, useState } from "react";
import type { RoadmapMilestone } from "../api/types";

type RoadmapViewProps = {
  title: string;
  targetRole: string | null;
  milestones: RoadmapMilestone[];
  meta?: string;
  onToggleTask?: (
    milestoneIndex: number,
    taskIndex: number,
    completed: boolean,
  ) => Promise<void>;
};

function Section({
  title,
  items,
  text,
}: {
  title: string;
  items?: string[];
  text?: string | null;
}) {
  if ((!items || items.length === 0) && !text) return null;

  return (
    <section>
      <h4 className="text-sm font-semibold text-ink">{title}</h4>

      {text ? (
        <p className="mt-1 text-sm leading-relaxed text-muted">{text}</p>
      ) : (
        <ul className="mt-1 list-disc space-y-1 pl-5 text-sm leading-relaxed text-muted marker:text-brand">
          {items!.map((item, index) => (
            <li key={index}>{item}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

function hasDetails(milestone: RoadmapMilestone) {
  return Boolean(
    milestone.description ||
      milestone.topics_to_learn.length ||
      milestone.tasks.length ||
      milestone.project ||
      milestone.completion_criteria.length ||
      milestone.prerequisites.length,
  );
}

function countCompleted(milestone: RoadmapMilestone): number {
  return milestone.tasks.reduce(
    (count, _, index) =>
      count + (milestone.completed_tasks[index] === true ? 1 : 0),
    0,
  );
}

export default function RoadmapView({
  title,
  targetRole,
  milestones,
  meta,
  onToggleTask,
}: RoadmapViewProps) {
  const uid = useId();

  const [open, setOpen] = useState<Set<number>>(
    () => new Set(milestones.length ? [0] : []),
  );

  const [savingTask, setSavingTask] = useState<string | null>(null);
  const [taskError, setTaskError] = useState<string | null>(null);

  const editable = Boolean(onToggleTask);

  const totalTasks = milestones.reduce(
    (sum, milestone) => sum + milestone.tasks.length,
    0,
  );

  const completedTasks = milestones.reduce(
    (sum, milestone) => sum + countCompleted(milestone),
    0,
  );

  const overallProgress =
    totalTasks > 0
      ? Math.round((completedTasks / totalTasks) * 100)
      : 0;

  const allOpen =
    milestones.length > 0 && open.size === milestones.length;

  function toggleMilestone(index: number) {
    setOpen((previous) => {
      const next = new Set(previous);

      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }

      return next;
    });
  }

  async function handleTaskChange(
    milestoneIndex: number,
    taskIndex: number,
    completed: boolean,
  ) {
    if (!onToggleTask || savingTask !== null) return;

    const taskKey = `${milestoneIndex}-${taskIndex}`;

    setSavingTask(taskKey);
    setTaskError(null);

    try {
      await onToggleTask(milestoneIndex, taskIndex, completed);
    } catch (error) {
      setTaskError(
        error instanceof Error
          ? error.message
          : "Could not save task progress. Please try again.",
      );
    } finally {
      setSavingTask(null);
    }
  }

  return (
    <article>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="font-serif text-2xl font-semibold [overflow-wrap:anywhere]">
            {title}
          </h2>

          {targetRole && (
            <p className="mt-1 text-sm text-muted">
              Target role:{" "}
              <span className="font-semibold text-ink">
                {targetRole}
              </span>
            </p>
          )}

          {meta && (
            <p className="mt-0.5 text-xs text-muted">{meta}</p>
          )}
        </div>

        {milestones.length > 1 && (
          <button
            type="button"
            onClick={() =>
              setOpen(
                allOpen
                  ? new Set()
                  : new Set(milestones.map((_, index) => index)),
              )
            }
            className="min-h-11 rounded-lg px-3 text-sm font-semibold text-brand hover:bg-brand-soft"
          >
            {allOpen ? "Collapse all" : "Expand all"}
          </button>
        )}
      </div>

      {totalTasks > 0 && (
        <section className="mt-5 rounded-xl border border-line bg-surface p-4">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-ink">
              Overall progress
            </h3>

            <span className="text-sm font-semibold text-brand">
              {overallProgress}%
            </span>
          </div>

          <div
            className="mt-3 h-2 overflow-hidden rounded-full bg-brand-soft"
            role="progressbar"
            aria-label="Overall roadmap progress"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={overallProgress}
          >
            <div
              className="h-full rounded-full bg-brand transition-all"
              style={{ width: `${overallProgress}%` }}
            />
          </div>

          <p className="mt-2 text-xs text-muted">
            {completedTasks} of {totalTasks} tasks completed
          </p>
        </section>
      )}

      {taskError && (
        <div
          role="alert"
          className="mt-4 rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-700"
        >
          {taskError}
        </div>
      )}

      {milestones.length === 0 ? (
        <p className="mt-6 rounded-lg border border-dashed border-line-strong bg-surface p-6 text-sm text-muted">
          This roadmap has no milestones yet.
        </p>
      ) : (
        <ol className="relative mt-6 space-y-4">
          <span
            className="absolute bottom-6 left-[1.1rem] top-6 w-px bg-line-strong"
            aria-hidden="true"
          />

          {milestones.map((milestone, milestoneIndex) => {
            const isOpen = open.has(milestoneIndex);
            const panelId = `${uid}-m${milestoneIndex}`;

            const milestoneCompleted = countCompleted(milestone);
            const milestoneTotal = milestone.tasks.length;

            const milestoneProgress =
              milestoneTotal > 0
                ? Math.round(
                    (milestoneCompleted / milestoneTotal) * 100,
                  )
                : 0;

            return (
              <li
                key={milestoneIndex}
                className="relative flex gap-3 sm:gap-4"
              >
                <span
                  className="z-10 mt-3 flex size-9 shrink-0 items-center justify-center rounded-full border-2 border-brand bg-surface text-sm font-bold text-brand"
                  aria-hidden="true"
                >
                  {milestoneIndex + 1}
                </span>

                <div className="min-w-0 flex-1 rounded-xl border border-line bg-surface">
                  <h3>
                    <button
                      type="button"
                      aria-expanded={isOpen}
                      aria-controls={panelId}
                      onClick={() => toggleMilestone(milestoneIndex)}
                      className="flex min-h-14 w-full items-center justify-between gap-3 rounded-xl px-4 py-3 text-left hover:bg-brand-soft/60"
                    >
                      <span className="min-w-0">
                        <span className="block font-serif text-lg font-semibold [overflow-wrap:anywhere]">
                          <span className="sr-only">
                            Milestone {milestoneIndex + 1}:{" "}
                          </span>
                          {milestone.title}
                        </span>

                        {milestoneTotal > 0 && (
                          <span className="mt-1 block text-xs text-muted">
                            {milestoneCompleted} / {milestoneTotal} tasks
                            completed ({milestoneProgress}%)
                          </span>
                        )}
                      </span>

                      <svg
                        viewBox="0 0 20 20"
                        className={`size-5 shrink-0 text-muted transition-transform ${
                          isOpen ? "rotate-180" : ""
                        }`}
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        aria-hidden="true"
                      >
                        <path
                          d="m5 8 5 5 5-5"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    </button>
                  </h3>

                  <div
                    id={panelId}
                    hidden={!isOpen}
                    className="space-y-4 border-t border-line px-4 py-4"
                  >
                    {milestone.description && (
                      <p className="text-[0.95rem] leading-relaxed">
                        {milestone.description}
                      </p>
                    )}

                    <Section
                      title="Prerequisites"
                      items={milestone.prerequisites}
                    />

                    <Section
                      title="Topics to learn"
                      items={milestone.topics_to_learn}
                    />

                    {milestone.tasks.length > 0 && (
                      <section>
                        <h4 className="text-sm font-semibold text-ink">
                          Tasks
                        </h4>

                        <div className="mt-3 space-y-3">
                          {milestone.tasks.map((task, taskIndex) => {
                            const checked =
                              milestone.completed_tasks[taskIndex] === true;

                            const taskKey =
                              `${milestoneIndex}-${taskIndex}`;

                            const isSaving = savingTask === taskKey;

                            return (
                              <label
                                key={taskIndex}
                                className="flex items-start gap-3 rounded-lg border border-line p-3"
                              >
                                <input
                                  type="checkbox"
                                  checked={checked}
                                  disabled={!editable || savingTask !== null}
                                  onChange={(event) =>
                                    void handleTaskChange(
                                      milestoneIndex,
                                      taskIndex,
                                      event.target.checked,
                                    )
                                  }
                                  className="mt-1 size-4 shrink-0 accent-brand"
                                />

                                <span className="min-w-0 flex-1">
                                  <span
                                    className={`block text-sm leading-relaxed ${
                                      checked
                                        ? "text-muted line-through"
                                        : "text-ink"
                                    }`}
                                  >
                                    {task}
                                  </span>

                                  {isSaving && (
                                    <span
                                      className="mt-1 block text-xs text-muted"
                                      role="status"
                                    >
                                      Saving...
                                    </span>
                                  )}
                                </span>
                              </label>
                            );
                          })}
                        </div>

                        {!editable && (
                          <p className="mt-2 text-xs text-muted">
                            Read-only roadmap preview
                          </p>
                        )}
                      </section>
                    )}

                    <Section
                      title="Project"
                      text={milestone.project}
                    />

                    <Section
                      title="You're done when"
                      items={milestone.completion_criteria}
                    />

                    {!hasDetails(milestone) && (
                      <p className="text-sm text-muted">
                        No further details for this milestone.
                      </p>
                    )}
                  </div>
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </article>
  );
}
