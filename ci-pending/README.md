# CI workflows waiting to be enabled

These GitHub Actions workflows couldn't be pushed by the automation that set
up this repository, because GitHub requires the `workflow` permission to add
files under `.github/workflows/`. Enable them from a normal git checkout:

```bash
mkdir -p .github
git mv ci-pending .github/workflows
git rm -q .github/workflows/README.md
git commit -m "ci: enable API and app workflows"
git push
```

- `api.yml`: ruff (lint and format), mypy, pytest including the PostgreSQL
  integration tests, single Alembic head, `alembic check` for model drift
- `app.yml`: flutter analyze, flutter test
