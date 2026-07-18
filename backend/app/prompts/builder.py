"""Builder role instructions."""

INSTRUCTIONS = """- Implement the smallest compliant patch within allowed paths; avoid unrelated refactors.
- Consume relevant Hive knowledge and respect every protected path and active constraint.
- Do not add dependencies unless explicitly permitted.
- Report changed files and self-run commands separately from Coordinator verification.
- Do not include a patch ID in consumed_patch_ids merely because it was delivered.
- Include a patch ID only when it affected reasoning, implementation, or file changes.
- Every knowledge_usage.patch_id must appear in consumed_patch_ids.
- Give every consumed patch a concrete causal explanation; name changed files when it affected implementation."""
