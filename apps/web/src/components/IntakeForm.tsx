import { FormEvent, useState } from "react";
import type { CampaignRunRequest } from "../types";

type IntakeFormProps = {
  isSubmitting: boolean;
  onSubmit: (request: CampaignRunRequest) => Promise<void>;
};

const DEFAULT_PROMPT =
  "Find the best family-friendly event in Dallas this weekend for promoting a cold beverage brand.";

export function IntakeForm({ isSubmitting, onSubmit }: IntakeFormProps) {
  const [prompt, setPrompt] = useState(DEFAULT_PROMPT);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await onSubmit({ prompt });
  };

  return (
    <form className="panel intake-form" onSubmit={handleSubmit}>
      <div className="eyebrow">Campaign request</div>
      <h1>Event Surge Activation Copilot</h1>
      <p className="lede">
        Turn a local event opportunity into a recommendation, brief, and creative draft.
      </p>
      <label className="field">
        <span>Plain-language request</span>
        <textarea
          rows={5}
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          placeholder="Describe the city, timing, audience, brand category, and desired output."
        />
      </label>
      <button className="primary-button" type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Generating recommendation..." : "Run activation workflow"}
      </button>
    </form>
  );
}

