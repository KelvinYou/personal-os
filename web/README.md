# Tracked Assets — 本地理财仪表盘

**Local only. 不部署。** 本应用读取用户独立的 private `data/` 仓库里的 Tracked Assets 数据（不是完整净资产）；
`repos/ai-stock-analysis` 是 public repo，两者的隔离是有意为之
（见 `../ARCHITECTURE.md` §4）。任何形式的部署都要先解决
private 数据的托管边界。

## 跑起来

```bash
make web          # 仓库根目录，等价于 cd web && npm run dev
```

首次需要 `cd web && npm install`。

## 它不算数

页面**不重新实现任何估值逻辑**。所有数字来自
`scripts/wealth_check.py --json`，也就是 `make wealth` 用的同一份代码。

在 TypeScript 里重写这些数学，会把 Phase B 刚从数据文件里消灭掉的
dual-owner 漂移原样搬到代码层。所以 `lib/report.ts` 只做一件事：
起子进程、解析 JSON、渲染。

改口径 → 改 `scripts/lib/wealth/`，CLI 和网页会一起变。

## 组件来源

`components/shared/` 下的原子组件是从
`repos/ai-stock-analysis/web/components/shared/` **复制**过来的，不是跨 repo import。
两个仓库可见性不同，不建立编译期耦合——否则公开 repo 的改动能 break 这个私有应用。

## Balance-sheet scope

Finance renders report v4: gross tracked assets, known outstanding MYR debt, recorded monthly commitments and assets after known debt. Missing loan balances stay unknown; the adjusted figure is not full net worth. Credit-card `outstanding` requires `as_of`; optional `statement_due` and `payment_due_date` describe a separate payment obligation. Monthly installments are not deducted from assets.

Optional private `data/finance/travel-cash.yaml` wallets are shown in CNY without conversion and excluded from MYR totals. History and allocation retain their gross-asset basis. Appearance controls provide light/dark mode and reduced glass; these settings are local to the browser.

## Interface design

Use [the shared interface design guide](../docs/design-system.md). The dashboard
provides the visual baseline for Personal-OS standalone HTML: palette, typography,
spacing, cards, navigation and appearance controls. Travel exports implement it
through the travel skill's canonical assets, with CSS and selected Lucide SVGs
embedded for offline sharing. Keep the two implementations visually aligned when
changing the shared treatment; content layouts can differ by purpose.
