# py-crawler

Crawls public GitHub repos and produces a JSON report combining:

- **Repo metadata** from the GitHub API (stars, forks, open issues/PRs, license, topics, timestamps, …)
- **Parsed file contents** — named files pulled from each repo's branch and parsed as YAML or kept as text

Built on the [PyGithub](https://github.com/PyGithub/PyGithub) SDK rather than calling the REST API directly.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Authentication (recommended)

Unauthenticated requests are limited to 60/hour. A token raises this to 5000/hour:

```bash
export GITHUB_TOKEN=ghp_your_token   # a classic token with no scopes works for public repos
```

## Usage

```bash
python github_report.py                       # uses config.yaml, prints JSON to stdout
python github_report.py -o report.json        # write to a file
python github_report.py --repo python/cpython # add repos on top of the config
python github_report.py -v                    # show progress on stderr
```

## Configuration

Edit `config.yaml`:

```yaml
repos:
  - owner/name
files:
  - path: .pre-commit-config.yaml
    format: yaml      # parsed into structured data
  - path: README.md
    format: text      # kept as raw text
# branch: main        # optional; defaults to each repo's default branch
```

Repos passed with `--repo` are merged with the config list.

## Output shape

```jsonc
{
  "generated_at": "2026-10-13T...",
  "config": { "files": [...], "branch": null },
  "repos": [
    {
      "full_name": "owner/name",
      "status": "ok",
      "metadata": { "stargazers_count": 123, "open_issues_and_prs_count": 7, ... },
      "files": {
        ".pre-commit-config.yaml": { "status": "ok", "format": "yaml", "data": {...} },
        "missing.yml": { "status": "not_found" }
      }
    }
  ]
}
```

### Notes

- `open_issues_and_prs_count` mirrors GitHub's `open_issues_count`, which **includes open PRs**. See the note in `collect_metadata` if you need issues only.
- Per-repo and per-file errors are captured in the report (`status: "error" | "not_found"`) so one bad repo won't abort the run.
