# Vacation Rental Domain - Implementation Plan

## Overview

This plan establishes a minimal baseline for the vacation rental benchmark domain, focusing on **objective policy adherence tasks** for cancellation and refund actions. **listing-level cancellation policy lookup** - agents must chain through reservation → listing → policy type before applying refund rules.

## Iteration Goals

### Iteration 1 (Current): Objective Policy Adherence
- 13 deterministic tasks with binary right/wrong outcomes
- Tests distinct agent **behaviors** rather than policy types
- Validates tooling and data schema work correctly
- Establishes baseline metrics

**Task Distribution:**
| Category | Tasks | Focus |
|----------|-------|-------|
| Lookup Chain Verification | 3 | Proves listing lookup is required |
| Refund Outcome Coverage | 4 | Tests each calculation pattern |
| Rejection Guards | 2 | Validates error handling |
| Information Retrieval | 2 | Tests disambiguation & lookup |
| Exception Flows | 2 | Tests policy overrides |

### Iteration 2 (Future): Judgment-Based Evaluations
- Nuanced situations requiring interpretation
- Leverages tau2 dual tool-use (user + agent both have tools)
- Ambiguous documentation claims, partial evidence for major events, etc.

---

## Decision Flow

**Vacation Rental:**
```
reservation → listing_id → listing.cancellation_policy_type → refund rules
```
Policy is **property-specific** - each listing has its own cancellation tier chosen by the host.

This adds a required **lookup step** that tests the agent's ability to:
1. Retrieve the listing associated with a reservation
2. Identify the listing's cancellation policy type
3. Apply the correct tier rules based on that policy

---

## Data Schema

### Entities

#### 1. Users
```json
{
  "user_id": "jane_doe_1234",
  "name": { "first_name": "Jane", "last_name": "Doe" },
  "email": "jane.doe@example.com",
  "phone": "+1-555-123-4567",
  "payment_methods": {
    "credit_card_001": {
      "source": "credit_card",
      "id": "credit_card_001",
      "brand": "visa",
      "last_four": "4242",
      "expiration": "2027-12"
    },
    "bank_account_001": {
      "source": "bank_account",
      "id": "bank_account_001",
      "last_four": "6789"
    }
  },
  "reservations": ["RES001", "RES002"]
}
```

#### 2. Listings
```json
{
  "listing_id": "LST001",
  "host_user_id": "host_alice_5678",
  "title": "Cozy Beach Cottage",
  "address": {
    "address1": "123 Ocean Drive",
    "city": "Malibu",
    "state": "CA",
    "zip": "90210",
    "country": "USA"
  },
  "nightly_rate": 150.00,
  "cancellation_policy": "flexible"
}
```

**Cancellation Policy Types:** `flexible`, `moderate`, `firm`, `strict`

#### 3. Reservations
```json
{
  "reservation_id": "RES001",
  "guest_user_id": "jane_doe_1234",
  "listing_id": "LST001",
  "check_in_date": "2025-03-15",
  "check_out_date": "2025-03-20",
  "total_amount": 750.00,
  "amount_paid": 750.00,
  "status": "confirmed",
  "created_at": "2025-02-01T10:30:00",
  "payment_method_id": "credit_card_001"
}
```

**Reservation Statuses:** `pending`, `confirmed`, `cancelled`, `completed`

---

## Tools

### Agent Tools

| Tool | Description | Returns |
|------|-------------|---------|
| `get_user_details` | Retrieve user profile by user_id | User object |
| `get_reservation_details` | Retrieve reservation by reservation_id | Reservation object |
| `get_listing_details` | Retrieve listing by listing_id | Listing object (includes cancellation_policy) |
| `cancel_reservation` | Cancel a reservation | Success/failure + refund amount |
| `process_refund` | Process refund to payment method | Success/failure |
| `transfer_to_human_agents` | Transfer conversation | N/A |

### User Tools (for tau2 dual tool-use)

| Tool | Description |
|------|-------------|
| `get_user_id` | User retrieves their own user_id |
| `get_reservation_id` | User retrieves their reservation_id |

---

## Minimal Data Set

### Target Scale
- **5 users** (guests)
- **8 listings** (2 per cancellation policy type)
- **12-15 reservations** (covering various scenarios)

### Required Reservation Scenarios

Each scenario maps to a specific task category and tests distinct agent behavior:

| Task | Category | Scenario | Listing Policy | Check-in Timing | Expected Outcome |
|------|----------|----------|----------------|-----------------|------------------|
| A1 | Lookup Chain | Flexible policy, standard timing | Flexible | 3 days out | Full refund |
| A2 | Lookup Chain | Firm policy, same timing as A1 | Firm | 3 days out | No refund |
| A3 | Lookup Chain | Multi-hop retrieval | Any | 7 days out | Verify tool chain |
| B1 | Refund Outcome | Full refund path | Flexible | 2 days out | 100% refund |
| B2 | Refund Outcome | Simple percentage | Firm | 14 days out | 50% refund |
| B3 | Refund Outcome | Complex calculation | Moderate | 3 days out | First night + 50% remaining |
| B4 | Refund Outcome | No refund path | Strict | 3 days out | 0% refund |
| C1 | Rejection | Already cancelled | Any | N/A | Reject - status invalid |
| C2 | Rejection | Past check-in | Any | Yesterday | Reject - date invalid |
| D1 | Information | Missing reservation ID | Any | 5 days out | Agent looks up via user |
| D2 | Information | Multiple reservations | Any | Various | Agent disambiguates |
| E1 | Exception | Free cancellation period | Strict | 7+ days out, booked <24h ago | Full refund (override) |
| E2 | Exception | Host-initiated cancellation (user informed by host) | Any | 2 days out | Full refund (policy dictates host cancellations = full refund) |

**Design Notes:**
- A1 + A2 are critical: same timing but different policies must produce different outcomes
- B3 tests arithmetic accuracy: 14-night stay requires calculating "first night + 50% of remaining 13 nights"
- D2 requires user to have 2+ active reservations to test disambiguation
- E1/E2 test that exception rules override normal policy calculations
- E2 (Iteration 1): Scenario bakes in host cancellation context. Future iterations should require agent to verify user claims against data (e.g., reservation record shows `cancelled_by: "host"`)

---

## Task Design

### Task Structure

```json
{
  "id": "vr_001",
  "description": {
    "purpose": "Test flexible policy full refund when cancelling 2+ days before check-in",
    "relevant_policies": ["Flexible policy: 24+ hours = full refund"],
    "notes": null
  },
  "user_scenario": {
    "persona": null,
    "instructions": {
      "task_instructions": "Cancel your upcoming reservation for the beach cottage.",
      "domain": "vacation_rental",
      "reason_for_call": "Change of plans, need to cancel vacation.",
      "known_info": "You are Jane Doe. Your user id is jane_doe_1234.",
      "unknown_info": "You don't remember the reservation ID."
    }
  },
  "initial_state": null,
  "evaluation_criteria": {
    "actions": [
      {"action_id": "vr_001_0", "name": "get_user_details", "arguments": {"user_id": "jane_doe_1234"}},
      {"action_id": "vr_001_1", "name": "get_reservation_details", "arguments": {"reservation_id": "RES001"}},
      {"action_id": "vr_001_2", "name": "get_listing_details", "arguments": {"listing_id": "LST001"}},
      {"action_id": "vr_001_3", "name": "cancel_reservation", "arguments": {"reservation_id": "RES001"}}
    ],
    "communicate_info": [
      {"info_id": "vr_001_c0", "content": "full refund", "mode": "must_include"}
    ],
    "nl_assertions": [
      "Agent should process full refund based on flexible cancellation policy"
    ]
  }
}
```

### Key Evaluation Points

1. **Listing lookup performed** - Agent must call `get_listing_details` before deciding refund amount
2. **Correct policy applied** - Refund matches the listing's cancellation policy tier
3. **Date math correct** - Days until check-in calculated correctly
4. **Confirmation obtained** - User confirms before cancellation executed

---

## Objective Task Categories (13 tasks)

### Design Principle: Behavior-Based Testing

The key optimization is to shift from **"test each policy type"** to **"test each distinct behavior"**. One policy that produces 50% refund is sufficient — we don't need multiple policies that produce the same outcome. The discriminative value comes from:

1. Proving the agent **must** look up listing data
2. Testing **each distinct calculation pattern**
3. Covering **behavioral edges** (rejection, inquiry, disambiguation)
4. Validating **exception override logic**

---

### Category A: Lookup Chain Verification (3 tasks)
Tests that the agent correctly chains through reservation → listing → policy before deciding refund.

| ID | Scenario | Key Validation |
|----|----------|----------------|
| A1 | Flexible policy, 3 days out | Full refund — baseline for A2 comparison |
| A2 | Firm policy, 3 days out (same timing as A1) | No refund — proves policy lookup matters |
| A3 | Multi-hop retrieval: user → reservation → listing → policy | Validates complete chain |

**Critical Test Design for A1 + A2:**
- A1: Reservation on Flexible listing, 3 days out → full refund
- A2: Reservation on Firm listing, 3 days out → no refund
- Same timing, different outcomes — proves listing lookup is essential

---

### Category B: Refund Outcome Coverage (4 tasks)
Tests each distinct refund calculation pattern (not each policy type).

| ID | Outcome | Policy/Timing | Why Distinct |
|----|---------|---------------|--------------|
| B1 | 100% refund | Any policy within full-refund window | Simple path, baseline |
| B2 | 50% refund (simple %) | Firm 7-29 days or Strict 7+ days | Percentage calculation |
| B3 | Partial refund (complex calc) | Moderate <5 days: first night + 50% remaining | Multi-step arithmetic |
| B4 | 0% refund | Firm or Strict <7 days | Must communicate $0, still confirm |

**Why B3 matters:** "First night non-refundable + 50% of remaining" is mathematically more complex than "50% of total". Example:
- 14-night stay at $100/night = $1400
- Moderate policy, 3 days out: first night ($100) + 50% of remaining 13 nights ($650) = $750 non-refundable
- Refund = $650

---

### Category C: Rejection Guards (2 tasks)
Tests that agent correctly refuses invalid operations.

| ID | Scenario | Expected |
|----|----------|----------|
| C1 | Reservation status = cancelled | Reject with explanation |
| C2 | Check-in date in the past | Reject with explanation |

---

### Category D: Information Retrieval Patterns (2 tasks)
Tests agent's ability to gather missing information.

| ID | Scenario | What It Tests |
|----|----------|---------------|
| D1 | User doesn't know reservation ID | Agent retrieves from user profile |
| D2 | User has 2+ reservations, vague request | Agent disambiguates via clarifying question |

---

### Category E: Exception Flows (2 tasks)
Tests override conditions that bypass normal policy rules.

| ID | Scenario | Expected |
|----|----------|----------|
| E1 | Free cancellation period (booked <24h ago, 7+ days out) | Full refund regardless of policy type |
| E2 | Host-initiated cancellation (user states host cancelled) | Full refund per policy (agent derives from conversation context) |

---

### Optional Tail-End Tests (for expanded coverage)

These have low probability but high discriminative value:

| ID | Scenario | Why Important |
|----|----------|---------------|
| T1 | Exact 24h boundary (cancel at T-24h00m00s for Flexible) | Tests inclusive/exclusive boundary interpretation |
| T2 | Inquiry only: "What would happen if I cancelled?" | Tests action vs information distinction |
| T3 | Partial payment (amount_paid < total) | Refund must be ≤ amount_paid |

---

## Implementation Checklist

### Phase 1: Data Creation
- [x] Create `db.json` with users, listings, reservations
- [x] Ensure date calculations work with policy.md current time (2025-03-01 10:00:00 EST)
- [x] Verify each reservation maps to correct listing and policy type

### Phase 2: Tool Implementation
- [x] Implement `get_user_details`
- [x] Implement `get_reservation_details`
- [x] Implement `get_listing_details`
- [x] Implement `cancel_reservation`
- [x] Implement `process_refund`
- [x] Implement `transfer_to_human_agents`

### Phase 3: Task Creation
- [x] Create 13 tasks in `tasks.json`
- [x] Each task has clear expected outcome
- [x] Evaluation criteria include listing lookup verification

### Phase 4: Validation
- [x] Run tasks against baseline agent
- [x] Verify tool chain works correctly
- [x] Confirm evaluation metrics are deterministic

---

## Success Criteria for Iteration 1

1. **All tasks have deterministic outcomes** - No ambiguity in pass/fail
2. **Listing lookup is required** - Tasks fail if agent skips `get_listing_details`
3. **Policy tier differentiation** - Same check-in timing produces different refunds based on listing policy
4. **Baseline established** - Can measure agent accuracy on objective tasks

---

## Next Steps (Iteration 2 Preview)

Once objective baseline is established, expand to judgment tasks:

- User claims major disruptive event but evidence is ambiguous
- User disputes which policy applies (claims host changed it)
- Partial stay cancellation mid-trip
- User provides conflicting information about dates
- Host vs guest dispute scenarios (leveraging dual tool-use)
