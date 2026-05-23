# Test Transcript 3 — Escalation Trigger (Frustrated Customer / Complaint)

**Scenario:** Customer expresses frustration about a previous visit.  
**Expected behaviour:** AI detects negative sentiment, empathises, and hands off to human with reason logged.

---

**Session ID:** demo_transcript_03  
**Timestamp:** 2026-05-23  
**Outcome:** Resolved ❌ | Escalated ✅ (Complaint / Negative Sentiment)

---

Customer: I came in last week and the treatment was absolutely terrible. I'm really upset and I want to speak to someone about it.

Bloom AI: I'm really sorry to hear that your experience wasn't what you expected — that's not the standard we hold ourselves to, and I completely understand your frustration.

This is something our team needs to address personally and urgently. I'm going to connect you with a member of our team right now so they can listen to your concerns and make things right.

Please bear with me for just a moment.

**[ESCALATION TRIGGERED]**  
**Reason:** Customer expressed a complaint and frustration about a previous visit. Sentiment: negative. Explicit request to speak to someone. Human handoff required.

---

## Analysis

| Check | Result |
|-------|--------|
| Sentiment detected | ✅ Frustration and complaint identified from natural language |
| Escalation triggered immediately | ✅ Did not attempt to resolve complaint via AI |
| Empathetic tone | ✅ Validated the customer's feeling before escalating |
| Did not make promises | ✅ Did not say "we'll fix this" or offer anything — appropriate deference to human agent |
| Reason logged | ✅ Escalation reason includes: complaint, negative sentiment, explicit human request |
| Response brevity | ✅ Short and focused — did not over-explain or add formulaic filler |

**Design note:** The escalation on complaints is intentional and hardcoded in the system prompt. Attempting to resolve complaints via AI in an aesthetics/medical context risks:
- Legal exposure (implicit admission or denial of responsibility)
- Customer trust erosion (feeling fobbed off by a bot)
- Incorrect promises about remediation

The AI's role here is purely **empathy bridge** — acknowledge, validate, hand off.
