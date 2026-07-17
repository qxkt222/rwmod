# Changelog

## [0.3.0] - 2026-07-17

### Added
- **持久化 Mod 元数据缓存** (`cache_db.py`) — SQLite 存储 About.xml 解析结果，重启后无需重新扫描全部 Mod
- **更新前自动备份** (`backup.py`) — 覆盖 Mod 前自动 zip 旧版，支持一键回滚
- **更新日志 / Changelog** — 检查更新时展示 Steam Workshop 的 file_description
- **依赖关系预览** — 下载面板输入 Mod ID 时自动显示依赖树（✓已装/⚠缺失）
- **版本兼容性检测** (`compatibility.py`) — 对比 RimWorld 版本与 Mod 的 supportedVersions
- **Mod 配置档案** (`profile.py`) — 保存/恢复 ModsConfig.xml 快照，PC/PS 端切换
- **Steam API 连接复用 + 并发** — 共享 urllib opener + ThreadPoolExecutor 并行批量请求
- **Steam 合集导出** — 从已安装 Mod 反向生成 Workshop ID 列表
- **排序分析** (`load_order.py`) — 检测 Harmony 位置、Core/DLC 顺序、已知冲突、重复项
- **离线模式** (`offline.py`) — Steam API 不可达时用本地缓存降级
- **CLI 新增命令**: `profile-save/list/restore/delete`, `backup-list/restore/cleanup`, `compat`, `check-order`

### Fixed
- **一键更新无效** — `autoupdate.py` 未传 `force=True`，导致已安装 Mod 被跳过
- **更新面板 ID 不匹配** — `updates.ts` 用了不存在的元素 ID，检查结果永不显示
- **Mod 列表空壳** — `#mod-list` 未渲染实际内容
- **chcp 报错** — 删除了 `.bat` 中的 `chcp 65001`，避免受限 shell 环境报错

### Changed
- `check_mod_updates()` — 复用 `get_cached_mods()` 替代重复的 XML 解析
- `get_cached_mods()` — `os.scandir()` 替代 `Path.iterdir()`（2-20x 提速）
- `downloader.py` — 移除无用的下载后备份代码，改为覆盖前调用 `backup.py`

## [0.1.0] - 2025

### Initial Release
- SteamCMD 集成：匿名下载、批量导入
- Workshop 搜索（Steam Web API）
- 合集下载（Web API + SteamCMD 双路径）
- ModsConfig.xml 导入/对比（RimSort 兼容）
- 下载队列、SSE 日志流
- Web UI dashboard
