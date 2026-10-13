#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import yaml
from github import Auth, Github, GithubException, UnknownObjectException

from src.file_parser import FileSpec, FileParser
from src.repo_parser import RepoParser

log = logging.getLogger("github_report")


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
@dataclass
class Config:
    repos: list[str] = field(default_factory=list)
    files: list[FileSpec] = field(default_factory=list)
    branch: str | None = None  # None => each repo's default branch


def load_config(path: str) -> Config:
    """Load config.yaml into a Config. Returns an empty Config if absent."""
    if not os.path.exists(path):
        log.warning("Config file %s not found; relying on CLI args.", path)
        return Config()

    with open(path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    files = [
        FileSpec(path=f["path"], format=f.get("format", "yaml"))
        for f in raw.get("files", [])
    ]
    return Config(
        repos=list(raw.get("repos", [])),
        files=files,
        branch=raw.get("branch"),
    )


def crawl_repo(gh: Github, full_name: str, cfg: Config) -> dict[str, Any]:
    """Build the report entry for a single repo."""
    log.info("Crawling %s", full_name)
    try:
        repo = gh.get_repo(full_name)
    except UnknownObjectException:
        return {"full_name": full_name, "status": "not_found"}
    except GithubException as exc:
        return {"full_name": full_name, "status": "error", "error": str(exc)}

    repo_parser = RepoParser(repo)
    file_parser = FileParser(repo, cfg.branch)
    return {
        "repo_name": full_name,
        "metadata": repo_parser.collect_metadata(),
        "ansible": {
            "galaxy": file_parser.extract_galaxy_metadata(),
            "runtime": file_parser.extract_runtime_metadata(),
        },
        "testing": file_parser.extract_workflow_metadata(),
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("-r", "--repo", action="append", default=[],
                   dest="repos", metavar="OWNER/NAME",
                   help="Add a repo to crawl (repeatable); merged with config")
    p.add_argument("-v", "--verbose", action="store_true",
                   help="Enable info-level logging")
    return p.parse_args(argv)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def main(argv: list[str]) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(message)s",
        stream=sys.stderr,
    )

    cfg = load_config("config.yaml")
    # CLI repos are added to (not replacing) config repos; de-dupe, keep order.
    repos = list(dict.fromkeys(cfg.repos + args.repos))
    if not repos:
        log.error("No repos to crawl. Add some to %s or pass --repo.", args.config)
        return 2

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        log.warning(
            "No GITHUB_TOKEN set; using unauthenticated access (60 req/hr limit). "
            "Set GITHUB_TOKEN to get 5000 req/hr."
        )
    gh = Github(auth=Auth.Token(token)) if token else Github()
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repos": [crawl_repo(gh, name, cfg) for name in repos],
    }

    out = json.dumps(report, indent=2, ensure_ascii=False, default=str)
    print(out)


if __name__ == "__main__":
    main(sys.argv[1:])
