---
name: install
description: Install project dependencies for backend and/or frontend
---

Install project dependencies based on the argument: $ARGUMENTS

Rules:
- If argument is "backend": install only backend dependencies
- If argument is "frontend": install only frontend dependencies
- If argument is "all" or empty: install both

## Backend install command
```bash
cd /home/adbrum/workspace/babel/new-dadosgov/backend && uv sync --extra dev --extra test
```

## Frontend install command
```bash
cd /home/adbrum/workspace/babel/new-dadosgov/frontend && npm install
```

Run both in parallel when installing all. Report the result of each installation (success or errors).
