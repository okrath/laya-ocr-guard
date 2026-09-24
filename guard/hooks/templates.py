"""
Hook Script Templates for Git and AI Coding Agents.
"""

# Git pre-commit hook: runs guard post to verify build, blast radius, and invariants before allowing commit
GIT_PRE_COMMIT_HOOK = """#!/usr/bin/env sh
# --- LAYA-OCR-GUARD AUTO-GENERATED HOOK ---
echo "🛡️  Running Laya-OCR-Guard Pre-Commit Check..."
guard post
STATUS=$?
if [ $STATUS -ne 0 ]; then
  echo "❌ Guard Verification FAILED! Commit aborted."
  echo "💡 Tip: Review the violations above or run 'guard post' manually."
  exit 1
fi
echo "✅ Guard Verification PASSED. Proceeding with commit."
exit 0
"""

# Git prepare-commit-msg hook: appends post-task verification summary to commit message
GIT_PREPARE_COMMIT_MSG_HOOK = """#!/usr/bin/env sh
# --- LAYA-OCR-GUARD COMMIT MSG HOOK ---
COMMIT_MSG_FILE=$1
COMMIT_SOURCE=$2

# Only append if message is not an amend or merge
if [ "$COMMIT_SOURCE" != "commit" ] && [ -f ".guard/session.json" ]; then
  echo "" >> "$COMMIT_MSG_FILE"
  echo "Approved-by: Laya-OCR-Guard (Muse Verification)" >> "$COMMIT_MSG_FILE"
fi
"""

# Agent wrapper script template (for Claude Code / Agent execution)
AGENT_WRAPPER_SCRIPT = """#!/usr/bin/env sh
# --- LAYA-OCR-GUARD AGENT HARNESS ---
PROMPT="$1"
shift
CMD="$@"

echo "🛡️  [1/3] Triggering Pre-Task Guard..."
guard pre "$PROMPT" || exit 1

echo "🤖 [2/3] Executing Agent Command: $CMD"
$CMD
CMD_STATUS=$?

echo "🧪 [3/3] Triggering Post-Task Guard..."
guard post
POST_STATUS=$?

if [ $CMD_STATUS -ne 0 ]; then
  exit $CMD_STATUS
fi
exit $POST_STATUS
"""
