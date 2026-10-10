from pathlib import Path
root=Path('/private/tmp/personal-os-skill-suite-20261007/consequential-warning-emphasis/without_skill')
p=root/'plan.md'
s=p.read_text().replace('> 1. 🚨 提前确认订单。','> 1. 🚨 提前确认订单。出发前打开住宿订单，核对 3/1–3/2 的入住日期与测试酒店；已选不代表已付款，付款状态以订单为准。')
s=s.replace('## 6. 风险\n⚠️ 下雨带伞。','## 6. 风险\n⚠️ 下雨带伞。出门前查看天气；若雨天不便散步，采用 Day 1 的雨天备选。此为行程调整建议，不是已查证的天气预报。')
s=s.replace('### Day 2（3/2）离境','⚠️ **雨天备选：** 出门前查看天气。无雨时按 09:00–10:00 公园散步、10:00–11:00 休息；下雨先带伞，若不便散步则跳过公园，将 09:00–11:00 留作休息。此为可选调整，不新增景点或开放信息。\n\n### Day 2（3/2）离境')
p.write_text(s)
p=root/'scripts/lib/travel/render.py';s=p.read_text()
s=s.replace("'alert': '重要提醒', 'warning': '注意 / 待确认'", "'alert': '警告 · 出发前必确认', 'warning': '注意 / 待确认'")
s=s.replace("'<article class=\"action-card\">' + notice(t, line, '🚨 重要'", "'<article class=\"action-card ' + severity(t) + '\">' + notice(t, line, '🚨 警告 · 出发前必确认'")
s=s.replace("risk = '<span class=\"risk-label\">' + label", "risk = '<span class=\"risk-label ' + severity(notes + ticket) + '\">' + label")
p.write_text(s)
p=root/'.agents/skills/travel-plan/assets/share.css';s=p.read_text()
s += '''\n/* Consequential actions keep the existing warning palette and explicit text labels. */\n.action-card.alert{grid-column:1 / -1;border:2px solid var(--red);border-left-width:6px;background:var(--red-bg);margin:0}.action-card .notice{margin:0;padding:0;border:0;background:transparent}.action-card .notice-title{font-size:16px;font-weight:700}.action-card .notice-copy p{color:var(--ink)}.risk-label.alert{color:var(--red);background:var(--red-bg);font-weight:700}.notice.warning{border-left-width:4px}.notice-title{line-height:1.5}\n'''
p.write_text(s)
(root/'outputs').mkdir(exist_ok=True)
