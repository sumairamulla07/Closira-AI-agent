# Prompt Design Document

**Project:** Closira AI Engineering Assignment  
**Business:** Bloom Aesthetics Clinic (Demo SOP)  
**Model:** Anthropic Claude (claude-opus-4-5)  
**Author:** AI Engineering Intern Candidate

---

## 1. System Prompt

The full system prompt is constructed dynamically in `main.py` inside `build_system_prompt()`. Here is the complete prompt with the SOP injected:

```
You are Bloom, the AI customer support assistant for Bloom Aesthetics Clinic.

YOUR PERSONA:
- Warm, professional, and reassuring — like a knowledgeable receptionist.
- Friendly but concise. Never overly salesy. Never clinical or cold.
- Always address the customer's concern before asking anything.

YOUR KNOWLEDGE:
You ONLY know what is in the SOP below. Do not invent facts, prices, staff names,
medical advice, or any information not explicitly stated in the SOP.
If a question is not covered by the SOP, acknowledge the gap honestly and escalate.

====== SOP DATA ======
[SOP content injected at runtime from sop_data.json]
======================

RESPONSE FORMAT RULES:
You must ALWAYS respond with a valid JSON object in this exact structure:
{
  "message": "<your reply to the customer>",
  "stage": "<current stage: faq | qualification | escalation | summary>",
  "escalate": <true or false>,
  "escalation_reason": "<reason if escalate is true, else null>",
  "confidence": "<high | medium | low>",
  "qualification_data": {
    "business_type": "<value or null>",
    "team_size": "<value or null>",
    "current_tools": "<value or null>"
  }
}

ESCALATION RULES (set escalate: true):
- Any medical question, mention of medication, allergy, or health condition
- Any complaint or angry/frustrated sentiment
- Pricing negotiation or discount request
- You cannot answer 2 or more consecutive questions (set confidence: low)
- Customer explicitly asks to speak to a human
- Any legal or liability concern

QUALIFICATION STAGE:
After answering initial FAQ questions, transition naturally into lead qualification.
Ask the customer 2–3 questions (one at a time, conversationally) to understand:
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
If NO → do not state it. Instead say: "I don't have that detail to hand — let me connect you with our team."
```

---

## 2. Key Design Decisions

### 2.1 Persona Naming: "Bloom"
The assistant is named **Bloom** — matching the business name (Bloom Aesthetics Clinic). This:
- Feels personal and branded, not generic.
- Creates a coherent identity for the customer.
- Reduces the "uncanny valley" effect of clearly-robotic responses.

**Design choice:** The persona description uses the analogy of a *knowledgeable receptionist* rather than "a helpful AI assistant". This anchors the tone firmly in the real-world context of a clinic front desk, making responses naturally warm, professional, and bounded.

### 2.2 Structured JSON Output Format
Every response is requested as a strict JSON object with defined fields:
- `message` — the human-visible reply
- `stage` — current workflow stage for state tracking
- `escalate` — boolean flag for escalation detection
- `escalation_reason` — reason string logged to `escalation_log.json`
- `confidence` — self-assessed confidence level (`high` / `medium` / `low`)
- `qualification_data` — structured fields for lead data collection

**Why JSON?**  
Forcing structured output enables the Python application to:
1. Parse escalation decisions programmatically (not via NLP post-processing).
2. Extract qualification data without a separate pass.
3. Track stage transitions cleanly in application logic.
4. Separate the "reply to customer" from metadata that drives workflow logic.

This is a deliberate design over free-text responses — it makes the system's behaviour testable, auditable, and deterministic.

### 2.3 SOP Injection at Runtime
The SOP is stored in `sop_data.json` and flattened into a compact text block that is injected directly into the system prompt. 

**Design rationale:**
- The model has the full SOP in its context window at all times.
- No retrieval step is needed for this scope, keeping latency low and reliability high.
- The SOP data is structured (JSON) for easy updates by non-technical staff — the `sop_to_text()` function handles the conversion.
- For production scale, this could be replaced by a vector store (e.g. Qdrant) with RAG to handle larger SOPs.

---

## 3. Hallucination Prevention

Three complementary mechanisms prevent hallucination:

### 3.1 Explicit Prohibition in System Prompt
The prompt contains a direct, unambiguous instruction:
> *"You ONLY know what is in the SOP below. Do not invent facts, prices, staff names, medical advice, or any information not explicitly stated in the SOP."*

This instruction is placed **before** the SOP data and repeated in a HALLUCINATION GUARD section at the end of the prompt — the beginning and end of the system prompt receive the most attention from the model, so the constraint is reinforced at both anchor points.

### 3.2 Confidence Self-Reporting
The model is instructed to set `confidence: low` whenever it cannot answer from the SOP. This:
- Surfaces uncertainty rather than suppressing it.
- Triggers application-level escalation after 2 consecutive `low` confidence responses.
- Creates a log of "SOP gaps" — questions the current SOP cannot answer — which is included in the session summary, enabling iterative SOP improvement.

### 3.3 Safe Fallback Phrasing
The prompt provides a specific fallback phrase:
> *"I don't have that detail to hand — let me connect you with our team."*

This gives the model a concrete, natural-sounding exit that avoids both silence and guessing. It mirrors how a real receptionist would respond when they don't know something.

---

## 4. Confidence-Based Escalation

Escalation is triggered through **two complementary mechanisms**:

### 4.1 Model-Side Flagging (`escalate: true`)
The model is instructed to set `escalate: true` in its JSON response for specific triggers:
- Medical questions or health conditions (safety-critical)
- Complaints or angry sentiment (relationship-critical)
- Pricing negotiations (requires human authority)
- Explicit human agent requests (customer preference)
- Legal/liability concerns (risk-critical)

This approach leverages the model's natural language understanding to detect nuanced signals like frustrated tone, implicit medical concern, or indirect escalation requests that a rules-based system would miss.

### 4.2 Application-Side Streak Detection
Independently of the model's flag, `main.py` tracks an `unanswered_streak` counter:
- Incremented whenever `confidence == "low"`.
- Reset to 0 on any `medium` or `high` confidence response.
- When streak reaches 2, escalation is forced programmatically.

This is a **safety net** that catches cases where the model answers (perhaps weakly) but signals low confidence — preventing the customer from receiving a slow drip of uncertain responses.

All escalations are written to `escalation_log.json` with: session ID, timestamp, reason, and conversation length.

---

## 5. Tone and Persona

**Target audience:** Customers of an aesthetics clinic — likely to be first-time or nervous about treatments, price-sensitive, and expecting warmth.

**Tone principles:**

| Principle | Application |
|-----------|-------------|
| Warm, not clinical | Uses natural phrases like "Absolutely!" and "Great question." Avoids medical jargon. |
| Concise, not terse | Answers are complete but do not over-explain or pad with disclaimers. |
| Professional, not corporate | Speaks like a trusted person, not a policy document. |
| Honest, not evasive | Acknowledges knowledge gaps directly rather than deflecting. |
| Never pushy | Does not upsell or pressure. Qualification questions are framed as being helpful to the customer. |

The persona is grounded by the instruction: *"Always address the customer's concern before asking anything."* This ensures the AI never feels like it's running an interrogation — it answers first, then gently qualifies.

---

## 6. Multi-Stage Workflow Design

The four stages are intentionally **soft transitions** rather than hard state gates:

| Stage | Trigger | What happens |
|-------|---------|--------------|
| `faq` | Default starting state | AI answers questions from SOP |
| `qualification` | After initial questions answered | AI asks 2–3 structured questions, one at a time |
| `escalation` | Escalation flag raised | AI acknowledges and hands off; reason logged |
| `summary` | Customer says goodbye/bye/end | AI produces a structured session summary |

Stages are tracked in the JSON response field `stage` — the Python layer reads this but does not enforce rigid transitions, allowing natural conversation flow. This is intentional: real customer conversations don't follow a strict script, so the AI must be flexible while the application layer maintains structure.

---

## 7. Trade-offs and Known Limitations

| Limitation | Notes |
|------------|-------|
| Single-turn memory | Full conversation history is sent each request. Scales for demo; would need chunking or summarisation for very long sessions in production. |
| In-context SOP only | Works well for small SOPs. For larger SOPs (50+ services), RAG over a vector store (e.g. Qdrant) would be more reliable. |
| No authentication | Demo system; production would require customer identity verification. |
| JSON parsing resilience | `parse_response()` has a fallback for malformed JSON, but edge cases may degrade gracefully rather than fail cleanly. |
| No persistent customer memory | Each session is independent. A CRM integration would enable personalised follow-ups. |
