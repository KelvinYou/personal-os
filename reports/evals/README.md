# `make eval` 输出目录

由 `scripts/session_eval.py` (EVALS_DIR) 写入；AGENTS.md 目录结构声明了本路径，
`make doctor` 会逐条 `test -e` 校验，所以空目录也需要这个占位文件。
