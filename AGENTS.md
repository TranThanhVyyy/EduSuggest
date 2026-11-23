# EduSuggest — project instructions

## Project structure and stack

- Existing product; extend the current codebase rather than recreating it.
- Frontend: Vue 3, JavaScript, Vue Router, Vite, Tailwind CSS, and Element Plus. App code and shared UI live under `frontend/src/`.
- Backend: Python, FastAPI, SQLAlchemy, PostgreSQL, and Alembic. API routes, services, repositories, models, and migrations live under `backend/`.
- Design references: `docs/DESIGN_CONSTITUTION.md`, `docs/DESIGN_SYSTEM.md`, and `docs/UI_UX_GUIDELINES.md`.

## UI/UX requirements

- Before any UI work, read all three design documents above.
- Follow the existing warm paper, navy, sage, and copper design tokens. Reuse CSS variables and components in `frontend/src/components/ui/` before adding new ones.
- Choose layout for the role and task; do not force every screen into a sidebar and card dashboard. Avoid generic gradients, excessive cards/shadows/radii, emoji icons, fabricated data, and placeholder content in completed flows.
- Provide truthful loading, empty, error, and success states. Preserve accessible labels, keyboard/focus behavior, and responsive layouts for mobile, tablet, and desktop.

## Roles and authorization

- Roles are ADMIN, EXPERT, PROVIDER, and USER. Enforce permissions in the backend; frontend visibility is not authorization.
- EXPERT alone reviews courses and may approve, reject, or request changes.
- ADMIN may manage visibility only for courses already approved by an EXPERT; ADMIN does not make academic review decisions.
- PROVIDER may manage only content they own. USER may access only approved and visible courses.
- Do not weaken or bypass these rules when changing UI, API, or services.

## Protected areas and data

- Do not recreate the project, replace real APIs with mock data, or overwrite unrelated existing work. Check `git status` and inspect relevant files before editing; preserve uncommitted user changes.
- Do not edit `.env`, initialize/recreate the database, change schema, create/run migrations, or change API contracts, authentication, authorization, or business rules without an explicit task. If a requested change requires one of these, explain the impact and obtain approval before making it.
- Preserve username login, JWT validation and revocation/blacklist behavior, and Argon2id password hashing.
- Never run `git reset --hard`, `git clean`, or commit/push unless explicitly requested.

## Working and validation process

- Read only the project instructions and files relevant to the task. Keep changes scoped and reuse established patterns.
- For UI changes, inspect the related role, API/data source, permissions, and loading/empty/error/success states before implementation.
- Do not claim a build, test, browser check, or runtime check passed unless it was actually run. For frontend changes, run the frontend production build when appropriate and report its result. Do not add or run tests unless requested.
- Report changed files, checks actually performed, and any unresolved limitations concisely.
