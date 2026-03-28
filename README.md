# Venmo — P2P Payment Platform

A modern peer-to-peer payment platform built with a TypeScript monorepo.

## Architecture

```
venmo/
├── apps/
│   ├── backend/     # Node.js + Express + TypeScript API
│   └── frontend/    # Next.js 14 + TypeScript
├── packages/
│   └── shared/      # Shared types and utilities
├── docker/          # Dockerfiles
└── .github/         # CI/CD workflows
```

**Stack:**
- **Backend**: Node.js 20, Express, TypeScript, Vitest
- **Frontend**: Next.js 14, React, TypeScript, Vitest + Testing Library
- **Database**: PostgreSQL 16
- **Cache**: Redis 7
- **Build**: Turborepo + pnpm workspaces
- **CI/CD**: GitHub Actions

> Full tech stack decisions are being finalized in the architecture design (VEN-4).

## Prerequisites

- [Node.js 20+](https://nodejs.org)
- [pnpm 9+](https://pnpm.io) — `npm install -g pnpm`
- [Docker + Docker Compose](https://docs.docker.com/get-docker/)

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/paulobalonye/Venmo.git
cd Venmo
pnpm install
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and fill in required values
```

### 3. Start infrastructure (PostgreSQL + Redis)

```bash
docker compose up -d
```

### 4. Run development servers

```bash
pnpm dev
```

- Backend API: http://localhost:3001
- Frontend: http://localhost:3000
- Health check: http://localhost:3001/health

## Development

### Running tests

```bash
# All tests
pnpm test

# With coverage (enforces 80% minimum)
pnpm test:coverage

# Watch mode
pnpm --filter @venmo/backend test:watch
pnpm --filter @venmo/frontend test:watch
```

### Linting & formatting

```bash
pnpm lint          # ESLint
pnpm format        # Prettier (write)
pnpm format:check  # Prettier (check only)
pnpm typecheck     # TypeScript
```

### Building for production

```bash
pnpm build

# Docker images
docker build -f docker/Dockerfile.backend -t venmo-backend .
docker build -f docker/Dockerfile.frontend -t venmo-frontend .
```

## CI/CD

GitHub Actions runs on every push and pull request:

| Check | Description |
|---|---|
| Lint & typecheck | ESLint + TypeScript strict |
| Backend tests | Vitest with real PostgreSQL (80% coverage gate) |
| Frontend tests | Vitest + Testing Library |
| Build | Turborepo full build |

**PRs are blocked if coverage drops below 80%.**

## Contributing

1. Create a feature branch from `main`
2. Follow [Conventional Commits](https://www.conventionalcommits.org/) — enforced by commitlint
3. Ensure CI passes (tests, coverage, lint)
4. Open a PR using the provided template

## Environment Variables

See [`.env.example`](.env.example) for all variables and descriptions.

Required for backend:
- `DATABASE_URL` — PostgreSQL connection string
- `JWT_SECRET` — Random 64-char hex string (generate with `node -e "console.log(require('crypto').randomBytes(64).toString('hex'))"`)
