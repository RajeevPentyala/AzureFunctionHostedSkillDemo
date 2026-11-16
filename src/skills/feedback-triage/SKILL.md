---
name: feedback-triage
description: Rules for classifying customer feedback by category, sentiment, and priority (P1-P3), and for writing the summary and suggested reply. Use whenever you triage, classify, or prioritize customer feedback.
---

# Feedback triage rules

## Category (pick the single best fit)
- **Bug**: something is broken, shows an error, crashes, or behaves wrongly.
- **Billing**: charges, invoices, refunds, pricing, or subscriptions.
- **Feature request**: asks for a new capability or a change to existing behavior.
- **Praise**: positive feedback with nothing to fix.
- **Other**: anything that fits none of the above.

## Sentiment
- **Positive**, **Neutral**, or **Negative**, based on the customer's tone, not the topic.

## Priority
- **P1**: service outage or customer fully blocked, data loss, security or privacy issue,
  customer charged incorrectly, or a threat to cancel or take legal action.
- **P2**: a real problem that has a workaround, or a clearly frustrated customer.
- **P3**: minor issues, suggestions, questions, and praise.

When in doubt between two priorities, choose the higher one and say why.

## Writing
- `priority_reason`: one sentence that cites the words in the feedback that drove the priority.
- `summary`: one sentence, 25 words or fewer.
- `suggested_reply`: 2-4 friendly sentences. Acknowledge the issue. Never promise refunds,
  dates, or fixes.
