# BeanBay

> **⚠️ Work in Progress** — This project is under active development and not yet ready for general use.

**Self-hosted coffee optimization powered by Bayesian learning.**

BeanBay is a phone-first web app for dialing in espresso recipes. It uses [BayBE](https://github.com/emdgroup/baybe) (Bayesian optimization) to learn from each brew and recommend better recipes over time. The loop: get a recommendation → brew → taste → rate → repeat. BayBE improves its suggestions with every shot.

Runs as a single Docker container. No cloud, no accounts — just your espresso machine and a browser.

**Stack:** FastAPI · Jinja2/htmx · SQLite · BayBE · Docker

---

## Quick Start (Docker)

```bash
docker run -d \
  --name beanbay \
  -p 8000:8000 \
  -v beanbay-data:/data \
  ghcr.io/grzonka/beanbay:latest
```

Then open [http://localhost:8000](http://localhost:8000) in your browser (or phone).

Or with `docker-compose`:

```bash
docker compose up -d
```

---

## Development Setup

```bash
git clone https://github.com/grzonka/beanbay.git
cd beanbay
uv sync
alembic upgrade head
uvicorn app.main:app --reload
```

App runs at [http://localhost:8000](http://localhost:8000).

Run tests:

```bash
pytest
```

---

## License

Apache 2.0 — see [LICENSE](./LICENSE).
