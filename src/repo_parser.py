from .utils import datetime_to_iso
from typing import Any


class RepoParser():
    def __init__(self, repo):
        self.repo = repo

    def collect_metadata(self) -> dict[str, Any]:
        """Pull the interesting scalar metadata off a PyGithub Repository."""
        # NOTE: GitHub's `open_issues_count` counts open PRs as well as issues.
        # To split them, count open PRs separately (one extra API call per repo)
        # and subtract; drop this if you don't need the distinction.
        lic = self.repo.license.spdx_id if self.repo.license else None
        open_prs_count = self.repo.get_pulls(state="open").totalCount
        open_issues_count = self.repo.open_issues_count - open_prs_count
        return {
            "full_name": self.repo.full_name,
            "description": self.repo.description,
            "default_branch": self.repo.default_branch,
            "license": lic,
            "open_issues_count": open_issues_count,
            "open_prs_count": open_prs_count,
            "archived": self.repo.archived,
            "created_at": datetime_to_iso(self.repo.created_at),
            "updated_at": datetime_to_iso(self.repo.updated_at),
            "html_url": self.repo.html_url,
        }
