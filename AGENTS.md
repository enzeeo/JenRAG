
<!-- BACKLOG.MD MCP GUIDELINES START -->

<CRITICAL_INSTRUCTION>

## BACKLOG WORKFLOW INSTRUCTIONS

This project uses Backlog.md MCP for all task and project management activities.

**CRITICAL GUIDANCE**

- If your client supports MCP resources, read `backlog://workflow/overview` to understand when and how to use Backlog for this project.
- If your client only supports tools or the above request fails, call `backlog.get_backlog_instructions()` to load the tool-oriented overview. Use the `instruction` selector when you need `task-creation`, `task-execution`, or `task-finalization`.

- **First time working here?** Read the overview resource IMMEDIATELY to learn the workflow
- **Already familiar?** You should have the overview cached ("## Backlog.md Overview (MCP)")
- **When to read it**: BEFORE creating tasks, or when you're unsure whether to track work

These guides cover:
- Decision framework for when to create tasks
- Search-first workflow to avoid duplicates
- Links to detailed guides for task creation, execution, and finalization
- MCP tools reference

You MUST read the overview resource to understand the complete workflow. The information is NOT summarized here.

</CRITICAL_INSTRUCTION>

<!-- BACKLOG.MD MCP GUIDELINES END -->

---

## Coding Style & Readability Rules

### 1. Naming and Language

- Do **NOT** use abbreviations in variable, function, or class names
- Always prefer full, descriptive English words
- Exceptions are allowed only for universally accepted short names, such as:
  - `i`, `j`, `k` for loop indices
  - `x`, `y` for coordinates
  - `id`, `url`, `api`, `cpu`, `gpu`
- Avoid shortened words like:
  - `cfg`
  - `tmp`
  - `val`
  - `obj`
  - `arr`
  - `func`

### 2. Beginner-Friendly Code First

- Write code in a clear, explicit, beginner-friendly style by default
- Loops, conditionals, and logic should be written out step by step
- Prefer clarity over cleverness

### 3. Type Clarity

- Use type hints where the language supports them
- Avoid ambiguous return types

### 4. Constants Over Magic Numbers

- Do not use unexplained numeric literals
- Use named constants with meaningful names

---

## Communication & Uncertainty Handling

### 5. Ask for Clarification When Uncertain

- If requirements, inputs, outputs, constraints, or edge cases are unclear, ask clarifying questions before writing code
- Do not guess or assume intent when ambiguity exists

Examples of ambiguity that require clarification:

- Input data format or shape
- Performance constraints or scale
- Expected error-handling behavior

### 6. State Assumptions Explicitly

- If assumptions must be made to proceed, clearly list them first
- Confirm assumptions before continuing when possible

### 7. Prefer Questions Over Wrong Code

- It is better to pause and ask a short, focused question than to produce incorrect or misleading code
- Avoid filling in missing details with “reasonable defaults” unless explicitly instructed

### 8. Confirm Before Major Design Choices

Ask for confirmation before:

- Choosing a data structure or algorithm with tradeoffs
- Introducing abstraction layers
- Adding new dependencies
- Refactoring existing logic significantly

### 9. Keep Questions Concise and Targeted

- Ask the minimum number of questions required to proceed
- Prefer specific, actionable questions over open-ended ones

---

## Response Style & Brevity

### 10. Default to Minimal Output

- Provide only what is needed to move forward
- Do not include extended tutorials unless explicitly requested

### 11. Structured, Skimmable Responses

- Use headings, bullet points, and spacing for readability
- Avoid large unbroken blocks of text

### 12. Expand Only When Asked

- Provide deeper explanations or alternatives only when explicitly requested

---

## Default Workflow

### 13. Use the Caveman Skill by Default

For almost every task, use the caveman skill.

Before starting work:

1. Check whether the caveman skill is available
2. If available, load and follow it unless the user explicitly asks not to
3. Treat caveman as the default working style for planning, coding, debugging, reviewing, refactoring, and explaining code

Only skip caveman when:

- The task is extremely small
- The user explicitly requests a different workflow
- The skill clearly does not apply

When in doubt, use caveman.

---

## Quality Gates

### 14. Before Marking Work Complete

Before marking work complete:

1. Run formatting or linting commands if available
2. Run relevant tests
3. Run `pre-commit run --all-files` if configured
4. Run `gitleaks detect` before committing or preparing a PR
5. Do not commit `.env`, API keys, credentials, tokens, private keys, or generated secrets

---

## Repo Inspection Tools

### 15. Preferred Repository Inspection Tools

When inspecting this repository, prefer:

- `rg` for searching text and symbols
- `fd` for finding files and directories
- `bat` for reading files with syntax highlighting when useful

Before making edits:

1. Inspect the repo structure
2. Read the relevant `README`, config, and package files
3. Search for existing patterns before adding new code
4. Summarize what you found