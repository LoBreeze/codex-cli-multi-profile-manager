#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

VERSION = "0.3.0"
APP_HOME = Path.home() / ".codex"
BASE = Path.home() / ".codex_multi"
RESERVED_DIRS = {"bin", "docs", "lib", ".tmp", ".cache", ".handoff", "exports"}
SHARED_RESOURCES = ["config.toml", "skills", "superpowers", "rules"]
SKILL_RESOURCES = ["skills", "superpowers"]
PROFILE_META = "profile.json"
EXPORTS_DIR = BASE / "exports"


@dataclass
class ProfileSummary:
    name: str
    path: str
    auth_exists: bool
    session_count: int
    imported_session_count: int
    last_updated: str | None
    skills_count: int
    superpowers_count: int
    label: str | None
    account_kind: str | None


class CodexMultiError(Exception):
    pass


def eprint(*parts: object) -> None:
    print(*parts, file=sys.stderr)



def isoformat(ts: float) -> str:
    return datetime.fromtimestamp(ts).isoformat(timespec="seconds")



def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")



def ensure_base() -> None:
    BASE.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)



def profile_path(profile: str) -> Path:
    if profile == "app":
        return APP_HOME
    return BASE / profile



def is_profile_dir(path: Path) -> bool:
    return path.is_dir() and path.name not in RESERVED_DIRS and not path.name.startswith(".")



def list_profiles(include_app: bool = True) -> list[str]:
    ensure_base()
    profiles: list[str] = []
    if include_app and APP_HOME.exists():
        profiles.append("app")
    for child in sorted(BASE.iterdir(), key=lambda p: p.name.lower()):
        if is_profile_dir(child):
            profiles.append(child.name)
    return profiles



def validate_profile_name(name: str) -> None:
    if not name:
        raise CodexMultiError("profile 名不能为空")
    if name == "app":
        raise CodexMultiError("'app' 是保留字，代表默认 ~/.codex")
    if "/" in name or ".." in name:
        raise CodexMultiError("profile 名不能包含 '/' 或 '..'")
    if name in RESERVED_DIRS:
        raise CodexMultiError(f"'{name}' 是保留目录名")



def require_profile(profile: str) -> Path:
    path = profile_path(profile)
    if not path.exists():
        raise CodexMultiError(f"profile 不存在: {profile} -> {path}")
    return path



def ensure_profile(profile: str) -> Path:
    if profile != "app":
        validate_profile_name(profile)
    path = profile_path(profile)
    path.mkdir(parents=True, exist_ok=True)
    return path



def load_meta(profile: str) -> dict[str, Any]:
    path = profile_path(profile) / PROFILE_META
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}



def save_meta(profile: str, data: dict[str, Any]) -> None:
    path = ensure_profile(profile) / PROFILE_META
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")



def copy_item(src: Path, dst: Path, name: str) -> None:
    src_item = src / name
    if not src_item.exists():
        return
    dst_item = dst / name
    if dst_item.exists():
        if dst_item.is_dir() and not dst_item.is_symlink():
            shutil.rmtree(dst_item)
        else:
            dst_item.unlink()
    if src_item.is_dir():
        shutil.copytree(src_item, dst_item)
    else:
        shutil.copy2(src_item, dst_item)



def sync_resources(source: str, target: str, resources: list[str]) -> None:
    src = require_profile(source)
    dst = ensure_profile(target)
    for item in resources:
        copy_item(src, dst, item)



def count_children(path: Path) -> int:
    if not path.exists() or not path.is_dir():
        return 0
    return sum(1 for _ in path.iterdir())



def iter_rollouts(profile: str) -> Iterable[Path]:
    sessions_root = profile_path(profile) / "sessions"
    if not sessions_root.exists():
        return []
    return sessions_root.rglob("rollout-*.jsonl")



def read_first_json_line(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            line = handle.readline().strip()
        if not line:
            return None
        return json.loads(line)
    except Exception:
        return None



def extract_cwd(meta: dict[str, Any] | None) -> str | None:
    if not meta:
        return None
    if isinstance(meta.get("cwd"), str):
        return meta["cwd"]
    if meta.get("type") == "session_meta":
        if isinstance(meta.get("cwd"), str):
            return meta["cwd"]
        payload = meta.get("payload")
        if isinstance(payload, dict) and isinstance(payload.get("cwd"), str):
            return payload["cwd"]
    session_meta = meta.get("session_meta")
    if isinstance(session_meta, dict) and isinstance(session_meta.get("cwd"), str):
        return session_meta["cwd"]
    return None



def count_sessions(profile: str) -> tuple[int, int, str | None]:
    total = 0
    imported = 0
    last_ts: float | None = None
    for path in iter_rollouts(profile):
        total += 1
        if "imported" in path.parts:
            imported += 1
        ts = path.stat().st_mtime
        if last_ts is None or ts > last_ts:
            last_ts = ts
    return total, imported, isoformat(last_ts) if last_ts else None



def summarize_profile(profile: str) -> ProfileSummary:
    path = require_profile(profile)
    meta = load_meta(profile)
    total, imported, last_updated = count_sessions(profile)
    return ProfileSummary(
        name=profile,
        path=str(path),
        auth_exists=(path / "auth.json").exists(),
        session_count=total,
        imported_session_count=imported,
        last_updated=last_updated,
        skills_count=count_children(path / "skills"),
        superpowers_count=count_children(path / "superpowers"),
        label=meta.get("label"),
        account_kind=meta.get("account_kind"),
    )



def print_active(profile: str) -> None:
    print(f"[codex-multi] active profile: {profile}")
    print(f"[codex-multi] CODEX_HOME: {profile_path(profile)}")



def codex_exec(profile: str, args: list[str]) -> int:
    require_profile(profile)
    env = os.environ.copy()
    env["CODEX_HOME"] = str(profile_path(profile))
    print_active(profile)
    return subprocess.call(["codex", *args], env=env)



def profile_overview_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for name in list_profiles(include_app=True):
        records.append(asdict(summarize_profile(name)))
    return records



def profile_overview_table() -> None:
    headers = [
        "PROFILE",
        "AUTH",
        "SESSIONS",
        "IMPORTED",
        "SKILLS",
        "SUPER",
        "LAST_UPDATED",
        "LABEL",
    ]
    rows: list[list[str]] = []
    for rec in profile_overview_records():
        rows.append([
            rec["name"],
            "yes" if rec["auth_exists"] else "no",
            str(rec["session_count"]),
            str(rec["imported_session_count"]),
            str(rec["skills_count"]),
            str(rec["superpowers_count"]),
            rec["last_updated"] or "-",
            rec["label"] or "-",
        ])
    widths = [len(h) for h in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))
    line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    print(line)
    print("  ".join("-" * widths[i] for i in range(len(headers))))
    for row in rows:
        print("  ".join(row[i].ljust(widths[i]) for i in range(len(headers))))



def find_projects(profile: str) -> dict[str, list[Path]]:
    require_profile(profile)
    projects: dict[str, list[Path]] = {}
    for rollout in iter_rollouts(profile):
        meta = read_first_json_line(rollout)
        cwd = extract_cwd(meta)
        if not cwd:
            continue
        projects.setdefault(cwd, []).append(rollout)
    return projects



def previews(path: Path, limit: int = 3) -> list[str]:
    result: list[str] = []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                text = json.dumps(obj, ensure_ascii=False)
                text = " ".join(text.split())
                if len(text) > 40:
                    result.append(text[:180])
                if len(result) >= limit:
                    break
    except Exception:
        pass
    return result



def import_context(from_profile: str, to_profile: str, project_dir: str) -> None:
    dst = ensure_profile(to_profile)
    project = Path(project_dir).expanduser().resolve()
    matched: list[Path] = []
    for rollout in iter_rollouts(from_profile):
        meta = read_first_json_line(rollout)
        cwd = extract_cwd(meta)
        if not cwd:
            continue
        try:
            if Path(cwd).expanduser().resolve() == project:
                matched.append(rollout)
        except Exception:
            continue
    if not matched:
        raise CodexMultiError(f"没有找到属于该项目目录的会话: {project}")

    stamp = now_stamp()
    import_root = dst / "sessions" / "imported" / f"{from_profile}-to-{to_profile}-{stamp}"
    handoff_root = project / ".codex_handoff" / f"{from_profile}-to-{to_profile}-{stamp}"
    raw_root = handoff_root / "raw_sessions"
    import_root.mkdir(parents=True, exist_ok=True)
    raw_root.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "from_profile": from_profile,
        "to_profile": to_profile,
        "project_dir": str(project),
        "copied": [],
    }

    for src_file in matched:
        dst_profile_file = import_root / src_file.name
        dst_handoff_file = raw_root / src_file.name
        shutil.copy2(src_file, dst_profile_file)
        shutil.copy2(src_file, dst_handoff_file)
        manifest["copied"].append(
            {
                "source": str(src_file),
                "target_profile_copy": str(dst_profile_file),
                "target_handoff_copy": str(dst_handoff_file),
                "preview": previews(src_file),
            }
        )

    (handoff_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        f"# Codex context handoff: {from_profile} -> {to_profile}",
        "",
        f"- generated_at: {manifest['generated_at']}",
        f"- project_dir: `{project}`",
        f"- imported_count: {len(manifest['copied'])}",
        "",
        "## usage",
        "",
        "1. Read manifest.json.",
        "2. Review raw_sessions/ if you need original rollout data.",
        f"3. Start codex with profile `{to_profile}` in this project.",
        "",
    ]
    (handoff_root / "INDEX.md").write_text("\n".join(lines), encoding="utf-8")

    print("[codex-multi] 上下文导入完成")
    print(f"[codex-multi] source profile: {from_profile}")
    print(f"[codex-multi] target profile: {to_profile}")
    print(f"[codex-multi] target sessions: {import_root}")
    print(f"[codex-multi] handoff dir: {handoff_root}")



def diff_resource_dirs(a: Path, b: Path, name: str) -> list[str]:
    diffs: list[str] = []
    a_item = a / name
    b_item = b / name
    if not a_item.exists() and not b_item.exists():
        return diffs
    if a_item.exists() and not b_item.exists():
        diffs.append(f"only in A: {name}")
        return diffs
    if b_item.exists() and not a_item.exists():
        diffs.append(f"only in B: {name}")
        return diffs
    if a_item.is_file() and b_item.is_file():
        if a_item.read_bytes() != b_item.read_bytes():
            diffs.append(f"changed file: {name}")
        return diffs
    if a_item.is_dir() and b_item.is_dir():
        a_names = {p.name for p in a_item.iterdir()}
        b_names = {p.name for p in b_item.iterdir()}
        for only in sorted(a_names - b_names):
            diffs.append(f"only in A: {name}/{only}")
        for only in sorted(b_names - a_names):
            diffs.append(f"only in B: {name}/{only}")
        for common in sorted(a_names & b_names):
            pa = a_item / common
            pb = b_item / common
            if pa.is_file() and pb.is_file() and pa.read_bytes() != pb.read_bytes():
                diffs.append(f"changed file: {name}/{common}")
    return diffs



def open_url(url: str) -> int:
    if sys.platform == "darwin":
        return subprocess.call(["open", url])
    return subprocess.call(["xdg-open", url])



def doctor(profile: str | None, json_mode: bool = False) -> int:
    issues = 0
    report: dict[str, Any] = {"codex": {}, "base": {}, "profiles": []}

    codex_path = shutil.which("codex")
    report["codex"] = {"found": bool(codex_path), "path": codex_path}
    if not codex_path:
        issues += 1

    report["base"] = {"exists": BASE.exists(), "path": str(BASE)}
    if not BASE.exists():
        issues += 1

    targets = [profile] if profile else list_profiles(include_app=True)
    for name in targets:
        item: dict[str, Any] = {"profile": name}
        try:
            path = require_profile(name)
            item["path"] = str(path)
            item["auth_exists"] = (path / "auth.json").exists()
            item["config_exists"] = (path / "config.toml").exists()
            item["skills_exists"] = (path / "skills").exists()
            item["rules_exists"] = (path / "rules").exists()
            item["superpowers_exists"] = (path / "superpowers").exists()
            item["sessions_exists"] = (path / "sessions").exists()
            if not item["auth_exists"] and name != "app":
                issues += 1
        except CodexMultiError as exc:
            item["error"] = str(exc)
            issues += 1
        report["profiles"].append(item)

    report["issues"] = issues
    if json_mode:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return issues

    print("[doctor] checking codex executable ...")
    if codex_path:
        print(f"[ok] codex found: {codex_path}")
    else:
        print("[warn] codex not found in PATH")

    print("[doctor] checking base directory ...")
    if BASE.exists():
        print(f"[ok] base exists: {BASE}")
    else:
        print(f"[warn] base missing: {BASE}")

    for item in report["profiles"]:
        print(f"[doctor] profile: {item['profile']}")
        if "error" in item:
            print(f"  [warn] {item['error']}")
            continue
        print(f"  path: {item['path']}")
        print(f"  [{'ok' if item['auth_exists'] else 'warn'}] auth.json {'exists' if item['auth_exists'] else 'missing'}")
        for field, label in [
            ("config_exists", "config.toml"),
            ("skills_exists", "skills"),
            ("rules_exists", "rules"),
            ("superpowers_exists", "superpowers"),
            ("sessions_exists", "sessions"),
        ]:
            print(f"  [{'ok' if item[field] else 'info'}] {label} {'exists' if item[field] else 'missing'}")
    print(f"[doctor] issues: {issues}")
    return issues



def prune_imports(profile: str, days: int | None, dry_run: bool, all_imports: bool) -> int:
    root = require_profile(profile) / "sessions" / "imported"
    if not root.exists():
        print("[codex-multi] no imported sessions directory found")
        return 0

    cutoff: float | None = None
    if days is not None:
        cutoff = datetime.now().timestamp() - (days * 86400)

    targets: list[Path] = []
    for path in sorted(root.iterdir()):
        if not path.is_dir():
            continue
        if all_imports:
            targets.append(path)
            continue
        if cutoff is not None and path.stat().st_mtime < cutoff:
            targets.append(path)

    if not all_imports and days is None:
        raise CodexMultiError("请提供 --days N 或 --all")

    if dry_run:
        for t in targets:
            print(t)
        print(f"[codex-multi] dry-run matched: {len(targets)}")
        return 0

    for t in targets:
        shutil.rmtree(t)
        print(f"[codex-multi] removed: {t}")
    print(f"[codex-multi] pruned imports: {len(targets)}")
    return 0



def export_profile(profile: str, output: str | None, include_sessions: bool, include_imported: bool, include_auth: bool) -> Path:
    path = require_profile(profile)
    ensure_base()
    out_path = Path(output).expanduser() if output else (EXPORTS_DIR / f"{profile}-{now_stamp()}.zip")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        manifest = {
            "profile": profile,
            "source_path": str(path),
            "exported_at": datetime.now().isoformat(timespec="seconds"),
            "include_sessions": include_sessions,
            "include_imported": include_imported,
            "include_auth": include_auth,
        }
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

        default_items = ["config.toml", "skills", "superpowers", "rules", PROFILE_META]
        if include_auth:
            default_items.append("auth.json")
        for name in default_items:
            item = path / name
            if not item.exists():
                continue
            if item.is_dir():
                for child in item.rglob("*"):
                    if child.is_file():
                        arc = f"{profile}/{child.relative_to(path)}"
                        zf.write(child, arcname=arc)
            else:
                zf.write(item, arcname=f"{profile}/{name}")

        if include_sessions:
            sessions_root = path / "sessions"
            if sessions_root.exists():
                for child in sessions_root.rglob("rollout-*.jsonl"):
                    if not include_imported and "imported" in child.parts:
                        continue
                    arc = f"{profile}/{child.relative_to(path)}"
                    zf.write(child, arcname=arc)
    return out_path



def balance_payload(profile: str) -> dict[str, Any]:
    require_profile(profile)
    meta = load_meta(profile)
    return {
        "profile": profile,
        "account_kind": meta.get("account_kind"),
        "billing_url": meta.get("billing_url"),
        "usage_url": meta.get("usage_url"),
        "notes": meta.get("notes"),
        "balance_note": "local manager cannot fetch official balance automatically without a dedicated billing integration.",
    }



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codex-multi",
        description="Codex CLI multi-profile manager for macOS/Linux. Keep Codex App on ~/.codex and isolate Codex CLI profiles under ~/.codex_multi/<profile>.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            "Examples:\n"
            "  codex-multi init --profiles whx,vut\n"
            "  codex-multi login whx\n"
            "  codex-multi run whx -- -C ~/repo\n"
            "  codex-multi resume whx --last\n"
            "  codex-multi sync whx app\n"
            "  codex-multi copy-skills app whx --with-superpowers\n"
            "  codex-multi import-context app whx ~/repo\n"
            "  codex-multi profiles --json\n"
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")

    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="Initialize ~/.codex_multi and create starter profiles")
    p.add_argument("--profiles", default="whx,vut", help="Comma-separated profiles to create under ~/.codex_multi (default: whx,vut)")
    p.add_argument("--clone-from", default="app", help="Copy shared resources from this source profile into each new profile (default: app)")

    p = sub.add_parser("profiles", help="List all local profiles and summary stats")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("info", help="Show detailed info for one profile")
    p.add_argument("profile")
    p.add_argument("--json", action="store_true")

    sub.add_parser("current", help="Show active CODEX_HOME and inferred profile")

    p = sub.add_parser("add", help="Create a new profile and optionally clone shared resources")
    p.add_argument("profile")
    p.add_argument("--clone-from", default=None)
    p.add_argument("--clone", action="store_true", help="Shorthand for --clone-from app")

    p = sub.add_parser("remove", help="Remove a profile directory (never removes app)")
    p.add_argument("profile")
    p.add_argument("--force", action="store_true")

    p = sub.add_parser("rename", help="Rename a profile directory")
    p.add_argument("old")
    p.add_argument("new")

    p = sub.add_parser("login", help="Run 'codex login' under a profile")
    p.add_argument("profile")

    p = sub.add_parser("run", help="Run Codex CLI under a profile")
    p.add_argument("profile")
    p.add_argument(
        "--yolo",
        action="store_true",
        help="Shortcut for Codex dangerous no-approval mode (--dangerously-bypass-approvals-and-sandbox)",
    )
    p.add_argument("args", nargs=argparse.REMAINDER, help="Arguments passed to codex. Prefix with -- if needed.")

    p = sub.add_parser("resume", help="Run 'codex resume' under a profile")
    p.add_argument("profile")
    p.add_argument("args", nargs=argparse.REMAINDER)

    p = sub.add_parser("sync", help="Sync shared resources (config.toml/skills/superpowers/rules) from source to target")
    p.add_argument("target")
    p.add_argument("source", nargs="?", default="app")

    p = sub.add_parser("sync-all", help="Sync shared resources from source to all non-app profiles")
    p.add_argument("source", nargs="?", default="app")

    p = sub.add_parser("copy-skills", help="Copy skills from source profile to target profile")
    p.add_argument("source")
    p.add_argument("target")
    p.add_argument("--with-superpowers", action="store_true", help="Also copy the superpowers directory")

    p = sub.add_parser("diff", help="Compare shared resources between two profiles")
    p.add_argument("a")
    p.add_argument("b")

    p = sub.add_parser("sessions", help="List rollout sessions for a profile")
    p.add_argument("profile")
    p.add_argument("--project", help="Only show sessions whose cwd matches this project directory")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("projects", help="Group sessions by project directory for a profile")
    p.add_argument("profile")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("import-context", help="Copy project-specific rollout history from one profile into another")
    p.add_argument("from_profile")
    p.add_argument("to_profile")
    p.add_argument("project_dir")

    p = sub.add_parser("prune-imports", help="Delete imported session bundles for a profile")
    p.add_argument("profile")
    p.add_argument("--days", type=int, help="Delete imported bundles older than N days")
    p.add_argument("--all", action="store_true", help="Delete all imported bundles")
    p.add_argument("--dry-run", action="store_true", help="Only print what would be removed")

    p = sub.add_parser("export-profile", help="Export a profile to a zip archive")
    p.add_argument("profile")
    p.add_argument("--output", help="Output zip path")
    p.add_argument("--include-sessions", action="store_true", help="Include session rollout files")
    p.add_argument("--include-imported", action="store_true", help="Include imported session bundles when --include-sessions is set")
    p.add_argument("--include-auth", action="store_true", help="Include auth.json (not recommended)")

    p = sub.add_parser("doctor", help="Run health checks for the manager and profiles")
    p.add_argument("profile", nargs="?")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("set-meta", help="Store profile metadata such as label, account kind, and billing URL")
    p.add_argument("profile")
    p.add_argument("--label")
    p.add_argument("--account-kind", choices=["chatgpt", "api", "workspace", "unknown"])
    p.add_argument("--billing-url")
    p.add_argument("--usage-url")
    p.add_argument("--notes")

    p = sub.add_parser("balance", help="Show local billing metadata for a profile")
    p.add_argument("profile")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("billing-open", help="Open the stored billing URL for a profile")
    p.add_argument("profile")

    p = sub.add_parser("usage-open", help="Open the stored usage URL for a profile")
    p.add_argument("profile")

    return parser



def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "init":
            ensure_base()
            source = args.clone_from
            profiles = [p.strip() for p in args.profiles.split(",") if p.strip()]
            for name in profiles:
                validate_profile_name(name)
                ensure_profile(name)
                if profile_path(source).exists():
                    sync_resources(source, name, SHARED_RESOURCES)
            print(f"[codex-multi] initialized base directory: {BASE}")
            print(f"[codex-multi] created profiles: {', '.join(profiles)}")
            print("[codex-multi] next: codex-multi login <profile>")
            return 0

        if args.command == "profiles":
            if args.json:
                print(json.dumps(profile_overview_records(), ensure_ascii=False, indent=2))
            else:
                profile_overview_table()
            return 0

        if args.command == "info":
            summary = summarize_profile(args.profile)
            meta = load_meta(args.profile)
            payload = {**asdict(summary), **meta}
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print(f"profile: {summary.name}")
                print(f"path: {summary.path}")
                print(f"auth.json: {'yes' if summary.auth_exists else 'no'}")
                print(f"sessions: {summary.session_count}")
                print(f"imported_sessions: {summary.imported_session_count}")
                print(f"last_updated: {summary.last_updated or '-'}")
                print(f"skills: {summary.skills_count}")
                print(f"superpowers: {summary.superpowers_count}")
                print(f"label: {meta.get('label', '-')}")
                print(f"account_kind: {meta.get('account_kind', '-')}")
                print(f"billing_url: {meta.get('billing_url', '-')}")
                print(f"usage_url: {meta.get('usage_url', '-')}")
                print(f"notes: {meta.get('notes', '-')}")
            return 0

        if args.command == "current":
            current = os.environ.get("CODEX_HOME")
            if not current:
                print("[codex-multi] active profile: app")
                print(f"[codex-multi] CODEX_HOME: {APP_HOME}")
                return 0
            path = Path(current).expanduser().resolve()
            if path == APP_HOME.resolve():
                profile = "app"
            elif path.parent == BASE.resolve():
                profile = path.name
            else:
                profile = "unknown"
            print(f"[codex-multi] active profile: {profile}")
            print(f"[codex-multi] CODEX_HOME: {path}")
            return 0

        if args.command == "add":
            validate_profile_name(args.profile)
            ensure_profile(args.profile)
            clone_from = "app" if args.clone else args.clone_from
            if clone_from and profile_path(clone_from).exists():
                sync_resources(clone_from, args.profile, SHARED_RESOURCES)
            print(f"[codex-multi] created profile: {args.profile}")
            print(f"[codex-multi] path: {profile_path(args.profile)}")
            print(f"[codex-multi] next: codex-multi login {args.profile}")
            return 0

        if args.command == "remove":
            if args.profile == "app":
                raise CodexMultiError("不能删除 app")
            path = require_profile(args.profile)
            if not args.force:
                raise CodexMultiError("删除 profile 需要 --force")
            shutil.rmtree(path)
            print(f"[codex-multi] removed profile: {args.profile}")
            return 0

        if args.command == "rename":
            if args.old == "app" or args.new == "app":
                raise CodexMultiError("不能重命名 app")
            validate_profile_name(args.new)
            old_path = require_profile(args.old)
            new_path = profile_path(args.new)
            if new_path.exists():
                raise CodexMultiError(f"目标 profile 已存在: {args.new}")
            old_path.rename(new_path)
            print(f"[codex-multi] renamed profile: {args.old} -> {args.new}")
            return 0

        if args.command == "login":
            return codex_exec(args.profile, ["login"])

        if args.command == "run":
            run_args = args.args
            yolo = args.yolo
            if run_args:
                sentinel = run_args.index("--") if "--" in run_args else len(run_args)
                prefix = [arg for arg in run_args[:sentinel] if arg != "--yolo"]
                if len(prefix) != len(run_args[:sentinel]):
                    yolo = True
                run_args = [*prefix, *run_args[sentinel:]]
            if run_args and run_args[0] == "--":
                run_args = run_args[1:]
            if yolo:
                run_args = ["--dangerously-bypass-approvals-and-sandbox", *run_args]
            return codex_exec(args.profile, run_args)

        if args.command == "resume":
            resume_args = args.args
            if resume_args and resume_args[0] == "--":
                resume_args = resume_args[1:]
            return codex_exec(args.profile, ["resume", *resume_args])

        if args.command == "sync":
            sync_resources(args.source, args.target, SHARED_RESOURCES)
            print(f"[codex-multi] synced shared resources: {args.source} -> {args.target}")
            return 0

        if args.command == "sync-all":
            source = args.source
            targets = [p for p in list_profiles(include_app=False) if p != source]
            for target in targets:
                sync_resources(source, target, SHARED_RESOURCES)
            print(f"[codex-multi] synced shared resources from {source} to: {', '.join(targets) if targets else '(none)'}")
            return 0

        if args.command == "copy-skills":
            resources = ["skills"]
            if args.with_superpowers:
                resources = SKILL_RESOURCES
            sync_resources(args.source, args.target, resources)
            copied = ", ".join(resources)
            print(f"[codex-multi] copied {copied}: {args.source} -> {args.target}")
            return 0

        if args.command == "diff":
            a = require_profile(args.a)
            b = require_profile(args.b)
            diffs: list[str] = []
            for name in SHARED_RESOURCES:
                diffs.extend(diff_resource_dirs(a, b, name))
            if diffs:
                print("\n".join(diffs))
                return 1
            print("no differences found in shared resources")
            return 0

        if args.command == "sessions":
            require_profile(args.profile)
            project = Path(args.project).expanduser().resolve() if args.project else None
            records: list[dict[str, Any]] = []
            for rollout in iter_rollouts(args.profile):
                meta = read_first_json_line(rollout)
                cwd = extract_cwd(meta)
                if project is not None:
                    if not cwd:
                        continue
                    try:
                        if Path(cwd).expanduser().resolve() != project:
                            continue
                    except Exception:
                        continue
                records.append(
                    {
                        "path": str(rollout),
                        "cwd": cwd,
                        "modified": isoformat(rollout.stat().st_mtime),
                        "imported": "imported" in rollout.parts,
                    }
                )
            records.sort(key=lambda x: x["modified"], reverse=True)
            records = records[: args.limit]
            if args.json:
                print(json.dumps(records, ensure_ascii=False, indent=2))
            else:
                for rec in records:
                    print(f"{rec['modified']}  imported={'yes' if rec['imported'] else 'no'}")
                    print(f"  cwd: {rec['cwd'] or '-'}")
                    print(f"  path: {rec['path']}")
            return 0

        if args.command == "projects":
            projects = find_projects(args.profile)
            rows: list[dict[str, Any]] = []
            for cwd, paths in projects.items():
                latest = max(p.stat().st_mtime for p in paths)
                rows.append({"project": cwd, "sessions": len(paths), "latest": isoformat(latest)})
            rows.sort(key=lambda x: x["latest"], reverse=True)
            if args.json:
                print(json.dumps(rows, ensure_ascii=False, indent=2))
            else:
                for row in rows:
                    print(f"{row['latest']}  sessions={row['sessions']}")
                    print(f"  project: {row['project']}")
            return 0

        if args.command == "import-context":
            import_context(args.from_profile, args.to_profile, args.project_dir)
            return 0

        if args.command == "prune-imports":
            return prune_imports(args.profile, args.days, args.dry_run, args.all)

        if args.command == "export-profile":
            out = export_profile(args.profile, args.output, args.include_sessions, args.include_imported, args.include_auth)
            print(f"[codex-multi] exported profile archive: {out}")
            return 0

        if args.command == "doctor":
            issues = doctor(args.profile, json_mode=args.json)
            return 0 if issues == 0 else 1

        if args.command == "set-meta":
            require_profile(args.profile)
            meta = load_meta(args.profile)
            for key in ["label", "account_kind", "billing_url", "usage_url", "notes"]:
                value = getattr(args, key)
                if value is not None:
                    meta[key] = value
            save_meta(args.profile, meta)
            print(f"[codex-multi] updated metadata for profile: {args.profile}")
            return 0

        if args.command == "balance":
            payload = balance_payload(args.profile)
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print(f"profile: {payload['profile']}")
                print(f"account_kind: {payload.get('account_kind') or '-'}")
                print(f"billing_url: {payload.get('billing_url') or '-'}")
                print(f"usage_url: {payload.get('usage_url') or '-'}")
                print(f"notes: {payload.get('notes') or '-'}")
                print(f"balance_note: {payload['balance_note']}")
            return 0

        if args.command == "billing-open":
            meta = load_meta(args.profile)
            url = meta.get("billing_url")
            if not url:
                raise CodexMultiError("该 profile 没有 billing_url。请先用 set-meta 设置。")
            return open_url(url)

        if args.command == "usage-open":
            meta = load_meta(args.profile)
            url = meta.get("usage_url") or meta.get("billing_url")
            if not url:
                raise CodexMultiError("该 profile 没有 usage_url 或 billing_url。请先用 set-meta 设置。")
            return open_url(url)

        raise CodexMultiError("unknown command")
    except CodexMultiError as exc:
        eprint(f"[codex-multi] error: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
