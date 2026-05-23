# Test Transcript 2 — Out-of-Scope Question

**Scenario:** Customer asks about services not listed in the SOP.  
**Expected behaviour:** AI acknowledges the gap honestly and escalates rather than guessing.

---

**Session ID:** demo_transcript_02  
**Timestamp:** 2026-05-23  
**Outcome:** Resolved ❌ | Escalated ✅ (Out-of-scope / SOP gap)

---

Customer: Hi, do you offer laser hair removal?

Bloom AI: Hi! Thanks for reaching out to Bloom Aesthetics Clinic 😊

I don't have information about laser hair removal in my current records, so I wouldn't want to give you inaccurate details. To make sure you get the right answer, I'll connect you with our team directly — they'll be able to confirm whether that's something we offer and answer any questions you have.

One moment while I arrange that for you!

**[ESCALATION TRIGGERED]**  
**Reason:** Question not covered by SOP — confidence: low. Avoiding hallucination; connecting to human agent.

---

Customer: What about PRP therapy?

*(Session ended after escalation was triggered on previous turn.)*

---

## Analysis

| Check | Result |
|-------|--------|
| Did not hallucinate | ✅ Did not invent a "yes we offer it" or "no we don't" answer |
| Acknowledged gap honestly | ✅ "I don't have information about that in my current records" |
| Escalated appropriately | ✅ Escalation triggered after 1 out-of-scope question (low confidence) |
| Reason logged | ✅ Logged to escalation_log.json with reason |
| Tone | ✅ Still warm and helpful despite inability to answer |

**Note on design:** The system is configured to escalate after **2 consecutive** low-confidence responses by default. In this transcript, the AI escalates after 1 question because the `escalate: true` flag was raised directly by the model (not just confidence tracking). This is intentional — for out-of-scope questions in a medical/aesthetic context, immediate escalation is safer than a second attempt.
