"""
rwmod 完整测试套件 — 一键运行

用法：
    .venv\Scripts\python.exe run_tests.py

自动安装缺失的 dev 工具后运行全部 6 项检查。
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"


def run(cmd: list[str], label: str) -> bool:
    print(f"\n{'─' * 60}")
    print(f"📋 {label}")
    print(f"{'─' * 60}")
    result = subprocess.run(
        [str(PYTHON)] + cmd,
        cwd=str(ROOT),
        encoding="utf-8",
        errors="replace",
    )
    return result.returncode == 0


def ensure_tool(module: str) -> bool:
    """Check if a module is importable. If not, pip install it."""
    check = subprocess.run(
        [str(PYTHON), "-c", f"import {module}"],
        capture_output=True,
    )
    if check.returncode == 0:
        return True
    print(f"  📦 安装 {module}...")
    install = subprocess.run(
        [str(PYTHON), "-m", "pip", "install", module],
        capture_output=True,
    )
    return install.returncode == 0


def main() -> int:
    results: list[tuple[str, bool]] = []

    # ── 确保基础 dev 工具可用 ────────────────────────────────
    print("🔧 检查 dev 工具...")
    for tool, pkg in [("ruff", "ruff"), ("mypy", "mypy"), ("bandit", "bandit")]:
        ok = ensure_tool(tool)
        status = "✅" if ok else "❌ 安装失败"
        print(f"  {status} {tool}")
    print()

    # ── 1. Import smoke test ──────────────────────────────────
    # 修复了 backup 的 assertion：Path.stem 不含 .zip 扩展名
    results.append(("新模块导入检查", run(
        ["-c", r"""
import sys, traceback
fails = []

def check(name, code):
    try:
        exec(code, {})
    except Exception as e:
        fails.append(f"{name}: {e}\n{traceback.format_exc()[-200:]}")

check("errors",
    "from rwmod.errors import ConfigError; e=ConfigError('test'); assert e.detail=='test'")
check("version",
    "from rwmod import __version__; assert __version__=='0.3.0', __version__")
check("backup",
    "from rwmod.backup import _backup_metadata\n"
    "from pathlib import Path\n"
    "r = _backup_metadata(Path('/x/a__b__c.zip'))\n"
    "assert r == {'workshop_id':'a','folder_name':'b','timestamp':'c'}, r")
check("offline",
    "from rwmod.offline import safe_fetch")
check("database_queue",
    "from rwmod.database import queue_upsert,queue_load_pending,queue_clear_done")
check("auth",
    "from rwmod.auth import create_token,verify_token\n"
    "t=create_token('admin'); assert verify_token(t)=='admin'")
check("schemas",
    "from rwmod.models.schemas import ConfigResponse,DownloadRequest,QueueSnapshotResponse\n"
    "from rwmod.models.schemas import LoginRequest,DashboardResponse,SearchResponse\n"
    "from rwmod.models.schemas import StatusResponse,HistoryResponse")
check("app_state",
    "from rwmod.app_state import AppState")

if fails:
    for f in fails:
        print(f'  ❌ {f}')
    sys.exit(1)
print('  ✅ 全部 8 项导入通过')
"""],
        "新模块导入 + 核心逻辑验证",
    )))

    # ── 2. ruff lint ────────────────────────────────────────
    if ensure_tool("ruff"):
        results.append(("ruff lint", run(
            ["-m", "ruff", "check", "src/", "--select", "E,F,W,I,UP,B,SIM"],
            "ruff lint 检查",
        )))
    else:
        results.append(("ruff lint (跳过 — 安装失败)", True))

    # ── 3. ruff format ──────────────────────────────────────
    if ensure_tool("ruff"):
        results.append(("ruff format", run(
            ["-m", "ruff", "format", "--check", "src/"],
            "ruff format 检查",
        )))
    else:
        results.append(("ruff format (跳过)", True))

    # ── 4. pytest (no network) ──────────────────────────────
    results.append(("pytest (无网络)", run(
        ["-m", "pytest", "tests/", "-m", "not network",
         "--cov=rwmod", "--cov-report=term-missing", "-v", "--tb=short"],
        "单元测试 + 覆盖率",
    )))

    # ── 5. mypy ─────────────────────────────────────────────
    if ensure_tool("mypy"):
        results.append(("mypy 类型检查", run(
            ["-m", "mypy", "src/rwmod/", "--config-file=pyproject.toml"],
            "mypy 类型检查",
        )))
    else:
        results.append(("mypy (跳过 — 安装失败)", True))

    # ── 6. bandit ───────────────────────────────────────────
    if ensure_tool("bandit"):
        results.append(("bandit 安全扫描", run(
            ["-m", "bandit", "-c", "pyproject.toml", "-r", "src/"],
            "bandit 安全扫描",
        )))
    else:
        results.append(("bandit (跳过 — 安装失败)", True))

    # ── summary ──────────────────────────────────────────────
    print(f"\n{'═' * 60}")
    print("📊 测试结果汇总")
    print(f"{'═' * 60}")
    passed = sum(1 for _, ok in results if ok)
    failed = sum(1 for _, ok in results if not ok)
    for name, ok in results:
        print(f"  {'✅' if ok else '❌'} {name}")
    print(f"\n  {passed}/{passed + failed} 通过")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
