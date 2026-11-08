#!/usr/bin/env bash
# Claude Code hook for web/ UI edits. Reads the hook JSON on stdin.
#   pre  : remind the agent of the design-system rules before it writes UI
#   post : run the design-rules ratchet and feed new violations back to the agent
# Always exits 0; the verdict travels in the JSON on stdout.
set -u
mode="${1:-post}"
root="$(cd "$(dirname "$0")/.." && pwd)"
f="$(jq -r '.tool_input.file_path // .tool_response.filePath // empty')"
case "$f" in
  "$root"/web/*.tsx|"$root"/web/*.css|"$root"/web/*.html) ;;
  *) exit 0 ;;
esac
case "$f" in "$root"/web/node_modules/*|"$root"/web/.next*) exit 0 ;; esac
if [ "$mode" = pre ]; then
  jq -n '{hookSpecificOutput:{hookEventName:"PreToolUse",additionalContext:"web/ UI rules (skill ui-design-rules): use Button/buttonClass (components/ui/button.tsx), Input/Textarea (components/ui/input.tsx) and Select (components/shared/select.tsx); never native select/input/textarea/button styling, never hex colours or .design-select-* overrides. make design-check enforces this."}}'
  exit 0
fi
out="$(python3 "$root/scripts/design_rules_check.py" 2>&1)" || \
  jq -n --arg r "$out" '{decision:"block",reason:("design-rules check failed after editing a web/ file:\n"+$r)}'
exit 0
