import test from "node:test";
import assert from "node:assert/strict";
import { HealthService } from "../src/services/health.js";

test("existing basic health reports ok", async () => {
  assert.deepEqual(await new HealthService().basic(), { status: "ok" });
});
