import { useState, type FormEvent } from "react";
import { generateRoadmap } from "../api/roadmap";
import { errorMessage } from "../api/client";
import type { CareerRoadmap, RoadmapGenerateRequest } from "../api/types";
import { Alert, Button, Dialog, Field, inputClass } from "./ui";

function parseSkills(raw: string): string[] {
  const seen = new Set<string>();
  for (const part of raw.split(/[,\n]/)) {
    const s = part.trim();
    if (s) seen.add(s);
  }
  return [...seen];
}

export default function GenerateForm({
  onCreated,
  onCancel,
}: {
  onCreated: (r: CareerRoadmap) => void;
  onCancel: () => void;
}) {
  const [role, setRole] = useState("");
  const [skills, setSkills] = useState("");
  const [background, setBackground] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const payload = (): RoadmapGenerateRequest => ({
    target_role: role.trim(),
    current_skills: parseSkills(skills),
    background: background.trim() || null,
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!role.trim() || busy) return;
    setError(null);
    setConfirming(true);
  }

  async function confirm() {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const created = await generateRoadmap(payload());
      setConfirming(false);
      onCreated(created);
    } catch (err) {
      setConfirming(false);
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <form onSubmit={onSubmit} className="space-y-5 rounded-xl border border-line bg-surface p-5 sm:p-6">
        <div>
          <h2 className="font-serif text-xl font-semibold">Generate a new roadmap</h2>
          <p className="mt-1 text-sm text-muted">Tell SkillPilot where you want to go. It will draft a sequence of milestones for you.</p>
        </div>

        <Field label="Target role" htmlFor="target-role">
          <input id="target-role" required maxLength={200} value={role} onChange={(e) => setRole(e.target.value)} placeholder="e.g. Backend developer" className={inputClass} disabled={busy} />
        </Field>

        <Field label="Skills you already have" htmlFor="skills" hint="Optional. Separate them with commas or new lines.">
          <textarea id="skills" rows={2} value={skills} onChange={(e) => setSkills(e.target.value)} aria-describedby="skills-hint" placeholder="Python basics, Git, SQL" className={inputClass} disabled={busy} />
        </Field>

        <Field label="Background" htmlFor="background" hint="Optional. Study, work experience, or how much time you have each week.">
          <textarea id="background" rows={3} value={background} onChange={(e) => setBackground(e.target.value)} aria-describedby="background-hint" className={inputClass} disabled={busy} />
        </Field>

        {error && <Alert title="The roadmap wasn't created">{error}</Alert>}

        <div className="flex flex-wrap gap-2">
          <Button type="submit" disabled={!role.trim()}>Review and generate</Button>
          <Button type="button" variant="secondary" onClick={onCancel} disabled={busy}>Cancel</Button>
        </div>
      </form>

      <Dialog
        open={confirming}
        onClose={() => setConfirming(false)}
        busy={busy}
        title="Generate and save this roadmap?"
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirming(false)} disabled={busy}>Go back</Button>
            <Button onClick={confirm} loading={busy}>{busy ? "Generating…" : "Generate and save"}</Button>
          </>
        }
      >
        <p>
          SkillPilot will create a roadmap for <strong className="text-ink">{role.trim()}</strong> and <strong className="text-ink">save it</strong> alongside your existing roadmaps. Your existing roadmaps are not changed.
        </p>
        <p>This can take a minute or two while the model writes it.</p>
      </Dialog>
    </>
  );
}
