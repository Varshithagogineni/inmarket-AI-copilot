import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const root = process.cwd();

function verifyRequiredFiles() {
  const requiredFiles = [
    "apps/api/app/main.py",
    "apps/api/app/application/orchestrators/activation_run.py",
    "apps/api/app/application/services/refinement_service.py",
    "apps/mcp/app/server.py",
    "apps/mcp/app/tools/strategy.py",
    "apps/web/src/App.tsx",
    "apps/web/src/components/RefinementForm.tsx",
    "apps/web/src/components/RunHistoryPanel.tsx",
    "packages/shared-schemas/jsonschema/workflow-run.schema.json",
  ];

  for (const file of requiredFiles) {
    assert.equal(fs.existsSync(path.join(root, file)), true, `${file} should exist`);
  }
}

function verifySchemaContract() {
  const schemaPath = path.join(
    root,
    "packages/shared-schemas/jsonschema/workflow-run.schema.json",
  );
  const schema = JSON.parse(fs.readFileSync(schemaPath, "utf8"));

  assert.deepEqual(schema.required, [
    "run_id",
    "status",
    "created_at",
    "updated_at",
    "steps",
    "events",
    "normalized_intent",
    "selected_event",
    "alternative_events",
    "campaign_brief",
    "copy_assets",
    "image_concept",
    "generated_asset",
    "revision_id",
    "refinement_history",
    "asset_versions",
  ]);
}

verifyRequiredFiles();
verifySchemaContract();
console.log("Scaffold validation passed.");
