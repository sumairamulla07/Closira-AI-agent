"""
Closira AI Customer Support Workflow
=====================================
A Python-based AI workflow using OpenRouter (free tier) that handles a
simulated customer conversation across four stages:
  1. FAQ Answering
  2. Lead Qualification
  3. Escalation Detection
  4. Conversation Summary

Author  : AI Engineering Assignment
Business: Bloom Aesthetics Clinic (Demo SOP)
"""

import json
import os
import sys
import re
from datetime import datetime
from openai import OpenAI

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
SOP_FILE = "sop_data.json"
LOG_FILE = "escalation_log.json"
TRANSCRIPT_DIR = "test_transcripts"
MODEL = "openrouter/auto"  # Free model on OpenRouter


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def load_sop(path: str = SOP_FILE) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def sop_to_text(sop: dict) -> str:
    lines = []
    b = sop["business"]
    lines.append(f"Business: {b['name']}")
    lines.append(f"Hours: {b['hours']['open']}. Closed: {b['hours']['closed']}.")
    lines.append(f"Website / Booking: {b['contact']['website']} or WhatsApp")
    lines.append("")
    lines.append("Services:")
    for s in sop["services"]:
        price = "Free" if s["price_from"] == 0 else f"From £{s['price_from']}"
        lines.append(f"  - {s['name']} ({price}): {s['description']} Duration: {s['duration_minutes']} min. {s['notes']}")
    lines.append("")
    bp = sop["booking_policy"]
    lines.append(f"Booking Policy: {bp['how_to_book']} Cancellation: {bp['cancellation_policy']}")
    lines.append("")
    lines.append("Escalate immediately if:")
    for trigger in sop["escalation_triggers"]:
        lines.append(f"  - {trigger}")
    return "\n".join(lines)


def build_system_prompt(sop_text: str) -> str:
    return f"""You are Bloom, the AI customer support assistant for Bloom Aesthetics Clinic.

YOUR PERSONA:
- Warm, professional, and reassuring — like a knowledgeable receptionist.
- Friendly but concise. Never overly salesy. Never clinical or cold.
- Always address the customer's concern before asking anything.

YOUR KNOWLEDGE:
You ONLY know what is in the SOP below. Do not invent facts, prices, staff names,
medical advice, or any information not explicitly stated in the SOP.
If a question is not covered by the SOP, acknowledge the gap honestly and escalate.

====== SOP DATA ======
{sop_text}
======================

RESPONSE FORMAT RULES:
You must ALWAYS respond with a valid JSON object in this exact structure:
{{
  "message": "<your reply to the customer>",
  "stage": "<current stage: faq | qualification | escalation | summary>",
  "escalate": <true or false>,
  "escalation_reason": "<reason if escalate is true, else null>",
  "confidence": "<high | medium | low>",
  "qualification_data": {{
    "business_type": "<value or null>",
    "team_size": "<value or null>",
    "current_tools": "<value or null>"
  }}
}}

ESCALATION RULES (set escalate: true):
- Any medical question, mention of medication, allergy, or health condition
- Any complaint or angry/frustrated sentiment
- Pricing negotiation or discount request
- You cannot answer 2 or more consecutive questions (set confidence: low)
- Customer explicitly asks to speak to a human
- Any legal or liability concern

QUALIFICATION STAGE:
After answering initial FAQ questions, transition naturally into lead qualification.
Ask the customer 2-3 questions (one at a time, conversationally) to understand:
  1. What treatment they are interested in
  2. Whether they have had aesthetic treatments before
  3. When they would like to come in

SUMMARY TRIGGER:
When the user says "bye", "thanks that's all", "end", "goodbye", or similar closing phrases,
produce a structured summary in your message field covering:
  - Customer intent
  - Key details collected
  - SOP gaps identified (questions you could not answer)
  - Recommended next action
And set stage to "summary".

HALLUCINATION GUARD:
Before every response, check: "Is this fact present in the SOP?"
If NO, do not state it. Instead say: "I don't have that detail to hand — let me connect you with our team."

Return ONLY the JSON object. No markdown fences, no extra text before or after."""


def parse_response(raw: str) -> dict:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return {
        "message": raw,
        "stage": "faq",
        "escalate": False,
        "escalation_reason": None,
        "confidence": "medium",
        "qualification_data": {"business_type": None, "team_size": None, "current_tools": None}
    }


def log_escalation(reason: str, conversation: list, session_id: str):
    entry = {
        "session_id": session_id,
        "timestamp": datetime.now().isoformat(),
        "reason": reason,
        "conversation_length": len(conversation)
    }
    existing = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            existing = json.load(f)
    existing.append(entry)
    with open(LOG_FILE, "w") as f:
        json.dump(existing, f, indent=2)
    print(f"\n⚠️  ESCALATION LOGGED: {reason}")


def save_transcript(conversation: list, session_id: str):
    os.makedirs(TRANSCRIPT_DIR, exist_ok=True)
    path = os.path.join(TRANSCRIPT_DIR, f"session_{session_id}.txt")
    with open(path, "w") as f:
        f.write(f"Session ID: {session_id}\n")
        f.write(f"Timestamp: {datetime.now().isoformat()}\n")
        f.write("=" * 50 + "\n\n")
        for turn in conversation:
            role = "Customer" if turn["role"] == "user" else "Bloom AI"
            f.write(f"{role}: {turn['content']}\n\n")
    print(f"\n📄 Transcript saved: {path}")


# ─────────────────────────────────────────────
# Core Workflow
# ─────────────────────────────────────────────

def run_workflow(demo_mode: bool = False, demo_inputs: list = None):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY environment variable not set.")
        print("   Run this in your terminal first:")
        print("   set OPENROUTER_API_KEY=your-key-here")
        sys.exit(1)

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    sop = load_sop()
    sop_text = sop_to_text(sop)
    system_prompt = build_system_prompt(sop_text)

    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    conversation = [{"role": "system", "content": system_prompt}]
    unanswered_streak = 0
    escalated = False
    qualification_data = {"business_type": None, "team_size": None, "current_tools": None}
    sop_gaps = []

    print("\n" + "=" * 55)
    print("  🌸  Bloom Aesthetics Clinic — AI Support  🌸")
    print("=" * 55)
    print("Type your message below. Type 'quit' or 'bye' to end.\n")

    demo_index = 0

    while True:
        # ── Get user input ──────────────────────────────
        if demo_mode:
            if demo_index >= len(demo_inputs):
                user_input = "bye"
            else:
                user_input = demo_inputs[demo_index]
                demo_index += 1
            print(f"Customer: {user_input}")
        else:
            try:
                user_input = input("Customer: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n\nSession ended.")
                break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            print("\nSession ended. Goodbye!")
            break

        conversation.append({"role": "user", "content": user_input})

        # ── Call OpenRouter ─────────────────────────────
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=conversation,
                temperature=0.3,
            )
            raw_reply = response.choices[0].message.content
        except Exception as e:
            print(f"\n❌ API error: {e}")
            break

        parsed = parse_response(raw_reply)

        bot_message = parsed.get("message", raw_reply)
        stage = parsed.get("stage", "faq")
        should_escalate = parsed.get("escalate", False)
        escalation_reason = parsed.get("escalation_reason")
        confidence = parsed.get("confidence", "medium")
        qual_data = parsed.get("qualification_data", {})

        for key in ("business_type", "team_size", "current_tools"):
            if qual_data.get(key):
                qualification_data[key] = qual_data[key]

        if confidence == "low":
            unanswered_streak += 1
            if unanswered_streak >= 2 and not should_escalate:
                should_escalate = True
                escalation_reason = "2+ consecutive questions outside SOP scope (low confidence)"
                sop_gaps.append(user_input)
        else:
            unanswered_streak = 0

        if confidence == "low" and not should_escalate:
            sop_gaps.append(user_input)

        print(f"\nBloom AI: {bot_message}\n")

        if should_escalate and not escalated:
            escalated = True
            log_escalation(escalation_reason or "Unknown reason", conversation, session_id)
            print("🔴 Transferring to human agent...")
            conversation.append({"role": "assistant", "content": bot_message})
            break

        conversation.append({"role": "assistant", "content": bot_message})

        if stage == "summary":
            print("\n" + "=" * 55)
            print("  Session Complete — Summary Generated")
            print("=" * 55)
            break

    # Save transcript (skip system prompt)
    save_transcript([m for m in conversation if m["role"] != "system"], session_id)

    if any(qualification_data.values()):
        print("\n📋 Qualification Data Collected:")
        for k, v in qualification_data.items():
            if v:
                print(f"   {k.replace('_', ' ').title()}: {v}")

    return conversation


# ─────────────────────────────────────────────
# Demo Scenarios
# ─────────────────────────────────────────────

DEMO_SCENARIOS = {
    "1_in_sop": {
        "description": "In-SOP question — Botox price",
        "inputs": ["Hi! What are your Botox prices?", "And how long does it last?", "Great, thanks that's all"]
    },
    "2_out_of_scope": {
        "description": "Out-of-scope question — information not in SOP",
        "inputs": ["Do you offer laser hair removal?", "What about PRP therapy?", "bye"]
    },
    "3_escalation_trigger": {
        "description": "Escalation — frustrated customer / complaint",
        "inputs": ["I came in last week and the treatment was terrible. I'm really upset.", "bye"]
    },
    "4_lead_qualification": {
        "description": "Lead qualification flow",
        "inputs": [
            "Hi, I'm interested in getting some work done.",
            "I'm thinking Botox for my forehead.",
            "No, this would be my first time.",
            "I'd like to come in next week if possible.",
            "bye"
        ]
    },
    "5_conversation_summary": {
        "description": "Full conversation with summary at end",
        "inputs": [
            "Hello! What services do you offer?",
            "How much is a consultation?",
            "What days are you open?",
            "I'd like to book a consultation for fillers.",
            "thanks that's all, bye"
        ]
    }
}


def run_demo(scenario_key: str):
    scenario = DEMO_SCENARIOS.get(scenario_key)
    if not scenario:
        print(f"Unknown scenario: {scenario_key}")
        return
    print(f"\n{'='*55}")
    print(f"  DEMO: {scenario['description']}")
    print(f"{'='*55}")
    run_workflow(demo_mode=True, demo_inputs=scenario["inputs"])


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--demo-all":
            for key in DEMO_SCENARIOS:
                run_demo(key)
        elif arg.startswith("--demo="):
            key = arg.split("=", 1)[1]
            run_demo(key)
        elif arg == "--help":
            print("Usage:")
            print("  python main.py                    Interactive mode")
            print("  python main.py --demo-all         Run all demo scenarios")
            print("  python main.py --demo=<key>       Run a specific demo")
            print("\nDemo keys:", list(DEMO_SCENARIOS.keys()))
        else:
            print(f"Unknown argument: {arg}. Use --help.")
    else:
        run_workflow()
