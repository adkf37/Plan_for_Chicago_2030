# Contributing to Plan for Chicago 2030

Thank you for your interest in contributing! This project is an open-source
effort to bring data-driven analysis to Chicago's land use and transportation
planning.

## Getting Started

1. **Fork & clone** the repository.
2. Copy `.env.example` → `.env` and add your Socrata app token.
3. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
4. Run the tests: `pytest -q`

## Project Structure

| Directory | Purpose |
|-----------|---------|
| `src/` | Core data processing & analysis modules |
| `viz/` | Visualisation scripts (Folium maps, matplotlib charts) |
| `data/` | Data files (see `data/reference/` for tracked CSVs) |
| `maps/` | Generated HTML map files (gitignored) |
| `reports/` | Generated reports & chart images (gitignored) |
| `site/` | Public-facing static website |
| `docker/` | Dockerfile & docker-compose |
| `tests/` | Pytest test suite |
| `backlog/` | Epic-level to-do files (GitHub Issues style) |

## Workflow

1. Pick an issue from `backlog/` or open a new GitHub Issue.
2. Create a feature branch: `git checkout -b feat/your-topic`
3. Make changes, add tests if applicable.
4. Run `pytest -q` and `ruff check src/ viz/` before pushing.
5. Open a Pull Request against `main`.

## Code Style

- **Python 3.11+**
- Format with **Black** (line length 99).
- Lint with **Ruff**.
- Use **type hints** where practical.
- All paths should use `src/config.py` constants — never hardcode absolute paths.
- API tokens go in `.env`, never in source code.

## Reporting Bugs

Open a GitHub Issue with:
- Steps to reproduce
- Expected vs. actual behaviour
- Python version and OS

## Data & Privacy

- Do **not** commit large data files (> 1 MB). They belong in `data/raw/` or
  `data/geojson/`, both of which are gitignored.
- Tracked reference files in `data/reference/` should remain small (< 100 KB).
- Never commit API tokens, passwords, or personally identifiable information.

## License

By contributing you agree that your contributions will be licensed under the
MIT License (see `LICENSE`).
