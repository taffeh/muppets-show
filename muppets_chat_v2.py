"""
muppets_chat_v2.py — local runner for the v2 multi-agent architecture.

Run: python3 /workspace/muppets_chat_v2.py
"""

import asyncio
import os
import sys

os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "FALSE"
os.environ["GOOGLE_API_KEY"] = os.environ.get("GEMINI_API_KEY") or os.environ["GOOGLE_API_KEY"]
os.environ.pop("GEMINI_API_KEY", None)

sys.path.insert(0, "/workspace/muppets_agent_v2")
from agent import tell_joke, heckle_topic, HELP_TEXT, DEFAULT_TOPICS
import random

async def main():
    print("=" * 60)
    print("  THE MUPPET SHOW v2  —  Genuine multi-agent")
    print("  Joke: SequentialAgent (listeners)")
    print("  Heckle: AgentTool orchestration")
    print(HELP_TEXT)
    print("=" * 60)

    while True:
        try:
            raw = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            raw = "quit"

        if not raw:
            continue

        parts = raw.split(maxsplit=1)
        cmd = parts[0].lower()
        topic = parts[1] if len(parts) > 1 else random.choice(DEFAULT_TOPICS)

        if cmd in ("quit", "exit", "q"):
            print("\nStatler: Well, that's finally over!")
            print("Waldorf: It was terrible! Do-ho-ho-ho!")
            print("Kermit: *sigh* ...and that's the Muppet Show. It's not easy being green.")
            break
        elif cmd == "joke":
            print("\n[Running SequentialAgent — agents share session, each listens to the stage...]")
            result = await tell_joke(topic)
            print(f"\n{result}")
        elif cmd == "heckle":
            print("\n[Running AgentTool orchestration — LLM drives the back-and-forth...]")
            result = await heckle_topic(topic)
            print(f"\n{result}")
        elif cmd == "help":
            print(HELP_TEXT)
        else:
            print("  Unknown command. Try: joke [topic] | heckle [topic] | help | quit")

if __name__ == "__main__":
    asyncio.run(main())
