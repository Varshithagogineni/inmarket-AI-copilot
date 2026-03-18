import { FormEvent, useState } from "react";
import type { RefineRunRequest } from "../types";

type RefinementFormProps = {
  disabled: boolean;
  onSubmit: (request: RefineRunRequest) => Promise<void>;
};

export function RefinementForm({ disabled, onSubmit }: RefinementFormProps) {
  const [instruction, setInstruction] = useState("Make the copy feel more energetic and local.");
  const [target, setTarget] = useState<RefineRunRequest["target"]>("copy");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await onSubmit({ instruction, target });
  };

  return (
    <form className="panel refinement-form" onSubmit={handleSubmit}>
      <div className="eyebrow">Refine outputs</div>
      <h2>Iterate without re-running event selection</h2>
      <label className="field">
        <span>Target</span>
        <select value={target} onChange={(event) => setTarget(event.target.value as RefineRunRequest["target"])}>
          <option value="copy">Copy</option>
          <option value="image">Image</option>
          <option value="brief">Brief</option>
        </select>
      </label>
      <label className="field">
        <span>Refinement instruction</span>
        <textarea
          rows={4}
          value={instruction}
          onChange={(event) => setInstruction(event.target.value)}
          placeholder="Describe how the output should change."
        />
      </label>
      <button className="secondary-button" type="submit" disabled={disabled}>
        {disabled ? "Updating..." : "Apply refinement"}
      </button>
    </form>
  );
}
