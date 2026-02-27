---
status: complete
phase: 18-brewer-capability-model
source: 18-01-SUMMARY.md, 18-02-SUMMARY.md
started: 2026-02-26T12:00:00Z
updated: 2026-02-26T12:08:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Create Brewer with Default Capabilities
expected: Navigate to Equipment page, click to add a new Brewer. Enter only a name and submit. The brewer should be created successfully with default capabilities. The brewer card should show a tier badge of T2.
result: pass

### 2. Tier Badge Visible on Brewer Card
expected: On the Equipment page, each brewer card shows a small T1-T5 tier badge next to the brewer name, indicating its capability level at a glance.
result: pass

### 3. Edit Brewer — Progressive Disclosure Form
expected: Click edit on a brewer. The form shows basic fields (name, brew method). Capability fields (temperature, pre-infusion, pressure, flow) are in a collapsible "Advanced Capabilities" section. For a default brewer, the advanced section should be collapsed.
result: pass

### 4. Set Advanced Capabilities — Pre-infusion
expected: In the brewer edit form, expand Advanced Capabilities. Change pre-infusion type from "none" to "timed" and set a max time (e.g., 15s). Save. The brewer card should now show T3 tier badge (pre-infusion capable).
result: pass

### 5. Set Advanced Capabilities — Flow Control
expected: Edit a brewer, set flow_control_type to "programmable". Save. The brewer card should now show T5 tier badge (full programmable).
result: pass

### 6. Capability Persistence After Edit
expected: After setting capabilities on a brewer, navigate away and come back to the Equipment page. Click edit on that brewer again — the previously saved capability values should still be there (not reset to defaults).
result: pass

### 7. Existing Brewers Retain Data After Migration
expected: Any brewers that existed before Phase 18 still appear on the Equipment page with their original names and associations intact. They should have default capability values (T2 badge).
result: pass

## Summary

total: 7
passed: 7
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
