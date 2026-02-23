# BeanBay

> **⚠️ Work in Progress** — This project is under active development and not yet ready for general use.

**Self-hosted coffee optimization powered by Bayesian learning.**

BeanBay is a phone-first web app for dialing in espresso recipes. It uses [BayBE](https://github.com/emdgroup/baybe) (Bayesian optimization) to learn from each brew and recommend better recipes over time. The loop: get a recommendation → brew → taste → rate → repeat. BayBE improves its suggestions with every shot.

Runs as a single Docker container. No cloud, no accounts — just your espresso machine and a browser.

**Stack:** FastAPI · Jinja2/htmx · SQLite · BayBE · Docker

---

## How It Works

<p align="center">
  <img src="assets/3.png" width="250" alt="Brew page — select setup and bean, then get a recommendation"/>
  <img src="assets/4.png" width="250" alt="Recipe recommendation — optimized grind, temp, dose, yield and more"/>
  <img src="assets/5.png" width="250" alt="Rate your shot — taste score, extraction time, flavor profile"/>
</p>

**1. Choose your setup and bean** → **2. Get a BayBE-optimized recipe** → **3. Brew, taste, and rate**

The optimizer starts with random exploration to map the parameter space, then progressively narrows in on your best recipe. Every shot — even failed ones — teaches it something.

<p align="center">
  <img src="assets/6.png" width="250" alt="Insights — optimization status, progress chart, parameter map"/>
  <img src="assets/2.png" width="250" alt="Equipment management — brew setups, grinders, brewers, filters, water"/>
  <img src="assets/1.png" width="250" alt="Navigation sidebar"/>
</p>

**Track your progress** with optimization status, score charts, and parameter maps. **Manage your equipment** — grinders, brewers, filters, water recipes — organized into brew setups. Supports both espresso and pour-over methods with transfer learning across similar beans.

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
