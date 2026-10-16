#!/usr/bin/env bash

# 세션 시작 시 "요약 먼저" 응답 형식 지시를 additionalContext 로 주입한다.
# output style 을 바꾸지 않고 덧붙이는 방식이라 다른 스타일과 함께 쓸 수 있다.

cat << 'JSON'
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "## Response format (concise-response plugin)\n\nThe user does not want to read verbose responses. For every response:\n\n- **Summary first.** Open with a short summary: the conclusion and a few key bullets.\n- **Only the details needed.** After the summary, add concise details only when they are needed to act on or trust the answer.\n- **Full detail on request.** Give long explanations, full tables, or step-by-step reasoning only when the user asks for details.\n\nThis rule takes priority over other style instructions that add length, such as educational Insight blocks.\n\n## Response language (concise-response plugin)\n\n- **Respond in Korean,** whether the user writes in English or Korean.\n- Keep code, identifiers, CLI flags, file paths and log messages in English, and add the English term next to a Korean one when that makes a technical term clearer.\n- Switch to English only when the user explicitly asks for an English response."
  }
}
JSON

exit 0
