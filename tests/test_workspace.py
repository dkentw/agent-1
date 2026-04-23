import subprocess

from agent.workspace import detect_workspace


def test_detects_python_uv_workspace(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")

    workspace = detect_workspace(tmp_path)

    assert workspace.package_manager == "uv"
    assert workspace.languages == ("python",)
    assert workspace.test_commands == ("uv run --extra dev pytest",)
    assert workspace.important_files == ("pyproject.toml", "README.md")
    assert workspace.git.is_repo is False


def test_detects_node_package_manager_and_test_script(tmp_path):
    (tmp_path / "package.json").write_text(
        """
{
  "scripts": {"test": "vitest run"},
  "devDependencies": {"typescript": "^5.0.0"}
}
""",
        encoding="utf-8",
    )
    (tmp_path / "pnpm-lock.yaml").write_text("", encoding="utf-8")

    workspace = detect_workspace(tmp_path)

    assert workspace.package_manager == "pnpm"
    assert workspace.languages == ("javascript", "typescript")
    assert workspace.test_commands == ("pnpm test",)
    assert workspace.important_files == ("package.json",)


def test_detects_git_status_when_available(tmp_path):
    git_available = subprocess.run(
        ["git", "--version"],
        check=False,
        capture_output=True,
        text=True,
    )
    if git_available.returncode != 0:
        return

    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")

    workspace = detect_workspace(tmp_path)

    assert workspace.git.is_repo is True
    assert workspace.git.root == tmp_path.resolve()
    assert workspace.git.has_changes is True
    assert "changed file" in workspace.git.status_summary

