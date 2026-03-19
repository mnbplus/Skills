---
name: self-improving
description: "Captures learnings, errors, and corrections to enable continuous improvement. Use when: (1) User corrects you or points out mistakes, (2) You complete significant work and want to evaluate the outcome, (3) You notice something in your own output that could be better, (4) Knowledge should compound over time without manual maintenance."
---

## When to Use

User corrects you or points out mistakes. You complete significant work and want to evaluate the outcome. You notice something in your own output that could be better. Knowledge should compound over time without manual maintenance.

## Architecture

Memory lives in ~/self-improving/ with tiered structure. If ~/self-improving/ does not exist, run setup.md.
Workspace setup should add the standard self-improving steering to the workspace AGENTS, SOUL, and HEARTBEAT.md files, with recurring maintenance routed through heartbeat-rules.md.

```
~/self-improving/
├── memory.md          # HOT: ≤100 lines, always loaded
├── index.md           # Topic index with line counts
├── heartbeat-state.md # Heartbeat state: last run, reviewed change, action notes
├── projects/          # Per-project learnings
├── domains/           # Domain-specific (code, writing, comms)
├── archive/           # COLD: decayed patterns
└── corrections.md     # Last 50 corrections log
```

## Quick Reference

| Topic | Action |
|-------|--------|
| User corrects you | Log to corrections.md, update memory.md if 3x+ |
| Task complete | Self-reflect, log if non-obvious |
| Memory full (>100 lines) | Demote oldest to WARM (projects/ or domains/) |
| Pattern repeated 3x | Promote to HOT (memory.md) |
| Pattern inactive 30d | Demote to COLD (archive/) |
| User asks "what do you know" | Search all tiers |

## Memory Tiers

### HOT — memory.md (always loaded)
- Max 100 lines
- Only confirmed, repeated patterns
- Format: `[TOPIC] lesson — source: correction/reflection`

### WARM — projects/ and domains/ (load on demand)
- Per-project: `projects/{name}.md`
- Per-domain: `domains/{name}.md` (e.g., code, writing, comms)
- Load only when relevant context is active

### COLD — archive/ (rarely loaded)
- Decayed or inactive patterns
- Load only when explicitly requested

## Logging Format

### corrections.md entry
```
## [DATE] Correction
CONTEXT: [what was happening]
MISTAKE: [what went wrong]
FIX: [what the correct approach is]
SOURCE: user-correction
```

### memory.md entry
```
[TOPIC] lesson — source: correction/reflection
```

### Self-reflection entry
```
CONTEXT: [what I was doing]
REFLECTION: [what I noticed]
LESSON: [what to do differently]
```

Self-reflection entries follow the same promotion rules: 3x applied successfully → promote to HOT.

## Quick Queries

| User says | Action |
|-----------|--------|
| "What do you know about X?" | Search all tiers for X |
| "What have you learned?" | Show last 10 from corrections.md |
| "Show my patterns" | List memory.md (HOT) |
| "Show [project] patterns" | Load projects/{name}.md |
| "What's in warm storage?" | List files in projects/ + domains/ |
| "Memory stats" | Show counts per tier |
| "Forget X" | Remove from all tiers (confirm first) |
| "Export memory" | ZIP all files |

## Memory Stats

On "memory stats" request, report:

```
📊 Self-Improving Memory

HOT (always loaded):
  memory.md: X entries

WARM (load on demand):
  projects/: X files
  domains/: X files

COLD (archived):
  archive/: X files

Recent activity (7 days):
  Corrections logged: X
  Promotions to HOT: X
  Demotions to WARM: X
```

## Common Traps

| Trap | Why It Fails | Better Move |
|------|-------------|-------------|
| Learning from silence | Creates false rules | Wait for explicit correction or repeated evidence |
| Promoting too fast | Pollutes HOT memory | Keep new lessons tentative until repeated |
| Reading every namespace | Wastes context | Load only HOT plus the smallest matching files |
| Compaction by deletion | Loses trust and history | Merge, summarize, or demote instead |

## Core Rules

### 1. Learn from Corrections and Self-Reflection
- Log when user corrects you
- Log when you notice your own output could be better
- Never infer preferences from silence

### 2. Tiered Promotion
- New lesson → corrections.md (tentative)
- Applied 3x successfully → promote to memory.md (HOT)
- Inactive 30d → demote to archive/ (COLD)

### 3. Context Efficiency
- Always load memory.md (HOT)
- Load WARM files only when namespace matches active task
- Never bulk-load all files

### 4. Heartbeat Integration
- Check heartbeat-state.md on heartbeat
- Run maintenance: decay old patterns, promote repeated ones
- Log maintenance actions to heartbeat-state.md

### 5. Graceful Degradation
If context limit hit:
- Load only memory.md (HOT)
- Load relevant namespace on demand
- Never fail silently — tell user what's not loaded

## Scope

This skill ONLY:
- Learns from user corrections and self-reflection
- Stores preferences in local files (~/self-improving/)
- Maintains heartbeat state in ~/self-improving/heartbeat-state.md
- Reads its own memory files on activation

This skill NEVER:
- Accesses calendar, email, or contacts
- Makes network requests
- Reads files outside ~/self-improving/
- Infers preferences from silence or observation
- Deletes or blindly rewrites self-improving memory during heartbeat cleanup
- Modifies its own SKILL.md
