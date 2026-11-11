# Iris — front end

Iris is the procurement operations desk for approvals, investigations, and
questions about invoices, purchase orders, vendors, and policy.

The front end is connected to the FastAPI backend in this repository. Auth,
chat, approvals, and decisions are live API calls; there is no mock approval or
chat data in `src/`.

## Run it

```bash
cd frontend
nvm install      # reads .nvmrc (Node 26.13.0 LTS)
nvm use
npm ci
npm start        # http://localhost:3000
```

The API must be running on `http://localhost:8000`:

```bash
cd ..
uv run uvicorn src.procurement_ai.main:app --host 0.0.0.0 --port 8000
```

Production build:

```bash
npm run build
```

## Backend endpoints used

| UI action | Endpoint |
|---|---|
| Sign in | `POST /auth/login` |
| Restore session | `GET /auth/me` |
| Load approvals | `GET /approvals?limit=200` |
| Approve / reject | `POST /approvals/{id}/decide` |
| Chat | `POST /chat` |

The API base defaults to `http://localhost:8000`. Override it with
`REACT_APP_API_BASE_URL`; override the Grafana shortcut with
`REACT_APP_GRAFANA_URL`.

Demo account:

```text
manager@example.com / demo123
```

Use `specialist@example.com / demo123` to see the backend’s department-scoped
read behavior. Payment requests created by the manager cannot be self-approved;
use `finance@example.com / demo123` or `director@example.com / demo123` to test
the approval decision path.

Chats are saved per signed-in user in browser storage. The History menu restores
previous conversations; starting a new chat leaves the old conversation intact.

## Routes

- `/login` — real JWT sign-in.
- `/` — landing page with live pending approvals and shortcuts.
- `/approvals` — searchable, filterable, sortable approval queue backed by the
  approval API; decisions are recorded on the server.
- `/chat` — Iris agent chat backed by `POST /chat`, with multi-turn session
  context and markdown rendering.

## Notes

- Internal workflow/cost/verification metadata is intentionally hidden from the
  chat UI. The backend still stores and logs it for diagnostics.
- Theme and session storage keys use the `iris.*` namespace.
- Fraunces and Public Sans are self-hosted through `@fontsource`.
- The screenshots folder contains reference captures; regenerate with
  `node screenshots/capture_ui.mjs`.
