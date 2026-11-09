import { useState, type FormEvent } from "react";
import { proposeRevision } from "../api/roadmap";
import { errorMessage } from "../api/client";
import type { RoadmapRevisionProposal } from "../api/types";
import { Alert, Button, Field, inputClass } from "./ui";

export default function RevisePanel({
  roadmapId,
  hasProposal,
  onProposal,
  onClose,
}: {
  roadmapId: string;
  hasProposal: boolean;
  onProposal: (p: RoadmapRevisionProposal) => void;
  onClose: () => void;
}) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!text.trim() || busy) return;
    setBusy(true);
    setError(null);
    try {
      onProposal(await proposeRevision(roadmapId, text.trim()));
      setText("");
      onClose();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4 rounded-xl border border-line bg-surface p-5">
      <div>
        <h2 className="font-serif text-lg font-semibold">Ask for a revision</h2>
        <p className="mt-1 text-sm text-muted">
          Describe what to change. You will see a proposal first. Nothing is saved until you accept it.
          {hasProposal && " A new request replaces the proposal you have now."}
        </p>
      </div>
      <Field label="What should change?" htmlFor="revise-instructions">
        <textarea
          id="revise-instructions"
          rows={3}
          required
          maxLength={2000}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="e.g. Add a milestone on testing and make the first milestone shorter"
          className={inputClass}
          disabled={busy}
        />
      </Field>
      {error && <Alert title="No proposal was created">{error}</Alert>}
      <div className="flex flex-wrap gap-2">
        <Button type="submit" disabled={!text.trim()} loading={busy}>{busy ? "Drafting proposal…" : "Create proposal"}</Button>
        <Button type="button" variant="secondary" onClick={onClose} disabled={busy}>Cancel</Button>
      </div>
    </form>
  );
}
