from dataclasses import dataclass
import yaml
from github import GithubException, UnknownObjectException


@dataclass
class FileSpec:
    """A file to fetch from each repo and how to interpret it."""

    path: str
    format: str = "yaml"  # "yaml" | "text"


class FileParser():
    def __init__(self, repo, branch: str = None):
        self.repo = repo
        self.branch = branch or repo.default_branch

    def _get_raw_file_content(self, path):
        try:
            content = self.repo.get_contents(path, ref=self.branch)
        except UnknownObjectException:
            return {"status": "not_found"}
        except GithubException as exc:
            return {"status": "error", "error": str(exc)}

        if isinstance(content, list):
            return {"status": "error", "error": "path is a directory, not a file"}

        try:
            text = content.decoded_content.decode("utf-8")
        except (UnicodeDecodeError, AssertionError) as exc:
            return {"status": "error", "error": f"could not decode: {exc}"}

        return text

    def parse_file(self, file_spec):
        content = self._get_raw_file_content(file_spec.path)
        if file_spec.format == "text":
            return content

        # format == "yaml": support multi-document files.
        try:
            return yaml.safe_load(content)
        except yaml.YAMLError as exc:
            return {"status": "error", "format": "yaml", "error": f"YAML parse: {exc}"}


    def extract_galaxy_metadata(self):
        content = self.parse_file(FileSpec("galaxy.yml", "yaml"))
        return {
            "version": content.get("version", None),
            "name": content.get("name", None),
            "namespace": content.get("namespace", None),
        }

    def extract_runtime_metadata(self):
        content = self.parse_file(FileSpec("meta/runtime.yml", "yaml"))
        return {
            "requires_ansible": content.get("requires_ansible", None)
        }

    def extract_workflow_metadata(self):
        try:
            contents = self.repo.get_contents(".github/workflows", ref=self.branch)
        except (UnknownObjectException, GithubException):
            return []

        if not isinstance(contents, list):
            contents = [contents]

        files = []
        for entry in contents:
            if entry.type != "file":
                continue
            text = self._get_raw_file_content(entry.path)
            if isinstance(text, str):
                files.append({"filename": entry.name, "content": text})
        return files
