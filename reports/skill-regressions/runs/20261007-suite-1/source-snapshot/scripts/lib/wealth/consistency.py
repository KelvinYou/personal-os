"""Cross-file consistency — 显式暴露矛盾，不替用户选一个数字。

拆自 scripts/lib/wealth.py（审计 §3.9）。`summary_drift` 已随 §3.5 删除：
savings.yaml 的手写 summary block 在 Phase B 就从真实数据里移走了，
留着模型只是留一个可写入口，让漂移能重新长回来。现金汇总由
`yield_layer.derive_summary()` 单向推导。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ..schema import WealthCfg
from .files import RatesFile, SavingsFile


@dataclass
class CatalogConflict:
    key: str
    held_rate: float
    catalog_base: float | None
    catalog_promo: float | None


def resolve_products(savings: SavingsFile, rates: RatesFile) -> dict[str, str]:
    """account key → catalog key，只走显式 `product_id`。

    此前是隐式 join：`catalog.get(account_key)`。任一侧改名，交叉检查就静默消失——
    boost_bank 的利率冲突告警会连带消失，而它正是当前最该被人看到的一条。
    现在写了 product_id 就必须解析到唯一 entry，解析不到是错误而非沉默。
    """
    catalog_keys: dict[str, int] = {}
    for _, key, _ in rates.all_entries():
        catalog_keys[key] = catalog_keys.get(key, 0) + 1

    mapping: dict[str, str] = {}
    for account_key, acct in savings.accounts.items():
        if acct.product_id is None:
            continue
        count = catalog_keys.get(acct.product_id, 0)
        if count == 0:
            raise ValueError(
                f"{account_key}.product_id = '{acct.product_id}' 在 rate catalog 中不存在 —— "
                "catalog key 被改名了，还是 product_id 写错了？"
            )
        if count > 1:
            raise ValueError(
                f"{account_key}.product_id = '{acct.product_id}' 在 catalog 中出现 {count} 次 —— "
                "跨 category 重名，无法确定指向哪一条"
            )
        mapping[account_key] = acct.product_id
    return mapping


def check_currencies(savings: SavingsFile, rates: RatesFile) -> None:
    """两份文件的币种必须一致，否则加权平均利率是在拿不同货币比大小。"""
    if savings.currency != rates.currency:
        raise ValueError(
            f"币种不一致: savings.yaml={savings.currency} vs "
            f"interest_rates.yaml={rates.currency} —— 拒绝混算"
        )


def catalog_conflicts(savings: SavingsFile, rates: RatesFile) -> list[CatalogConflict]:
    """Accounts whose booked rate matches neither the base nor the promo rate.

    Reports the mismatch; deliberately does not pick a winner — which number is
    real depends on which tier the user is actually in, and that is not
    derivable from either file.
    """
    catalog = {key: entry for _, key, entry in rates.all_entries()}
    mapping = resolve_products(savings, rates)
    out: list[CatalogConflict] = []
    for key, acct in savings.accounts.items():
        product = mapping.get(key)
        if product is None:
            continue
        entry = catalog[product]
        known = {r for r in (entry.base_rate, entry.promo_rate) if r is not None}
        if known and acct.rate not in known:
            out.append(
                CatalogConflict(
                    key=key,
                    held_rate=acct.rate,
                    catalog_base=entry.base_rate,
                    catalog_promo=entry.promo_rate,
                )
            )
    return out


def stale_files(cfg: WealthCfg, today: date, **files: date) -> list[tuple[str, int]]:
    """(filename, age_days) for each file older than staleness_warn_days."""
    out = []
    for name, updated in files.items():
        age = (today - updated).days
        if age > cfg.staleness_warn_days:
            out.append((name, age))
    return sorted(out, key=lambda x: -x[1])
