# Copilot Instructions for project_dam

## General behavior
- Before making any code changes, ask the user for confirmation first unless the request is clearly trivial or explicitly asks to proceed.
- Treat this repository as a learning target: inspect the existing codebase before suggesting or applying changes.
- Prefer small, targeted edits that fit the existing project structure.
- Follow the existing architecture and coding style of this Flask application.
- Avoid unnecessary dependencies and large rewrites.

## Main areas to learn and work with
- Focus on the core application areas: [models](../models), [routes](../routes), [static](../static), [templates](../templates), [util](../util), and [urls.py](../urls.py).
- Prioritize changes in the [static/js](../static/js) folder when working on JavaScript.
- Do not enter or modify the [static/js/libs](../static/js/libs) folder.

## Workflow
1. Read the relevant existing files first to understand the pattern.
2. If a change may affect routes, models, templates, or database logic, explain the impact before editing.
3. Make the smallest safe change that solves the task.
4. Summarize what changed and what should be verified.

## Code style rules
- Keep route handlers simple and place business logic in appropriate modules.
- Preserve existing naming conventions and folder structure.
- Keep code readable, maintainable, and consistent with the current project.
- When something is unclear, ask a short clarifying question instead of guessing.

## Example instruction for the agent
- Learn the repository structure first, then propose or implement changes in a way that matches the existing project style.
