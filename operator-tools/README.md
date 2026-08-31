# KpopWins operator tools

This standalone local project maintains an offline win catalogue, search schedule,
and reviewed reference candidates. It does not search providers or change the
public KpopWins database directly.

## Install

From `operator-tools/`, install the locked Python 3.13 environment:

```console
uv sync --frozen
```

Runtime data defaults to the repository's ignored `.ignore/operator-tools/`
directory. Set `KPOPWINS_OPERATOR_HOME` or `KPOPWINS_API_BASE_URL` to override
the defaults.

## Use

Initialize local state:

```console
uv run kpopwins-operator init
```

Refresh the complete win catalogue from a local KpopWins API:

```console
uv run kpopwins-operator refresh-wins
```

View local counts or list due work for a provider:

```console
uv run kpopwins-operator status
uv run kpopwins-operator due --provider youtube --limit 100
```

Export approved candidates for current wins:

```console
uv run kpopwins-operator export-approved
```

The default manifest is written to
`.ignore/operator-tools/manifests/win-references-v1.json`. Import it into a local
Django environment from the repository root:

```console
uv run python manage.py import_win_references .ignore/operator-tools/manifests/win-references-v1.json
```
