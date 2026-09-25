---
name: go-no-go
description: >
  Judge a plan or an idea go or no-go before work is committed to it.
  Use when asked whether a plan is ready to implement, whether to proceed with a design or proposal,
  whether an idea is worth pursuing, or for a go/no-go decision.
  Records the exact subject and the decision at stake, checks the claims and side effects the subject depends on,
  and returns a binary verdict in which every blocker cites evidence and a resolution.
  Not for writing or revising a plan, interviewing the user about requirements, reviewing code, or judging a release.
---

# Go/No-Go

Judge one fixed subject — a plan or an idea — `go` or `no-go` before the user commits to its next step.
A **blocker** is a finding that fails a declared criterion, cites evidence, and names a resolution; zero blockers is `go`, one or more is `no-go`.
There is no conditional or partial `go`.
Read-only throughout: this skill never edits the subject, the repository, or external state, and a `go` verdict recommends — it does not authorize execution.

## Invariants

- One subject, one revision: every claim, blocker, and ledger entry binds to the exact text judged.
  A changed subject is a new subject; an earlier verdict does not carry over.
- Criteria are declared before assessment.
  A finding cannot add, waive, or loosen a criterion after it surfaces.
  Criterion 2 (Claims) and criterion 6 (Risk) can never be waived, before or after.
- Verdict is binary.
  Whatever must hold before proceeding is a blocker, so there is no conditional or partial `go`.
- `no-go` requires at least one blocker, each citing a criterion, evidence, and a resolution; advisories never change the verdict.
- Load-bearing claims are verified — `verified`, `contradicted`, or `unverified`, each cited — and unverified or unassessed items stay visible rather than counted as passed.
- Tier comes from the ledger, from where a claim's falsity would surface, never from the subject's own labeling.
  Changes that stay inside version control default to two-way.
  The exception is repo automation that applies a change outside version control (a CI-run migration, merge-applied infrastructure, a push-triggered release workflow) — that is one-way.
  A step outside version control whose effect the ledger cannot determine defaults to one-way for want of evidence; it is not the only route to one-way — see Build the ledger for the full rule.
- Fully read-only, and execution ends at the report: never touches the subject, the repository, or external state.
  A request that says "if go, implement" does not take effect this run — it goes in the report as pending owner confirmation.
- `go` is a recommendation; it does not authorize execution.
- The verdict changes only for three reasons: the subject is revised, new evidence changes a claim's status, or the owner changes an accepted requirement or explicit constraint — which only re-opens criteria 3 and 4.
  Waiving a criterion, accepting a risk, or insisting after a finding is recorded as an **owner override**; the verdict does not change.
- Author disclosure: state whether the reviewer is the subject's author.
  Only when it is, and the decision includes a one-way step, recommend an independent review; otherwise mark independent review not required.
- A review report about the subject is evidence input: verify its claims; never adopt its conclusion directly.

## Fix the subject and the decision

Resolve the subject in order: a path or text the user names; else the session's one plan artifact; when several candidates remain unresolved, stop and list them for the user to name one.
Record a file subject's identity read-only:

```sh
git --no-optional-locks status --porcelain=v1 -- <path>
git --no-optional-locks rev-parse HEAD
git --no-optional-locks hash-object -- <path>
```

`hash-object` without `-w`: compute only, never write.
The reported revision `<id>` is that `hash-object` output, or the checksum tool's output, copied in full from what this run printed — never recalled, guessed, or shortened; `HEAD` and status are kept in working notes, not in the report.
Outside a Git directory, use an available checksum tool; with neither, record the subject's exact text in the report and mark the revision `<id>` as unavailable — the verbatim text itself is the identity for later comparison.
Record an idea exactly as the user stated it; mark the reviewer's own interpretation of it as an assumption.
An idea's revision `<id>` is `git hash-object --stdin` of that exact text, or another checksum tool's output when Git is unavailable; with no tool at all, mark it `unavailable` and rely on the recorded text.

State the decision: what `go` commits to — the **next commitment** — and its cost, as a rough order of magnitude (`hours`, `days`, `weeks`) plus what is spent, and its **blast radius**: the components, data, users, or external systems it reaches.
A plan's next commitment defaults to executing it as written; when the owner names a narrower commitment (implementing on a branch, say), later steps go under `Later commitments`, each needing its own verdict.
An idea's next commitment is the one it or the request names; with none, don't stop — record it as a criterion-5 blocker.
The decision owner defaults to the requester; stop only when the subject and the request disagree about who decides.
Record the accepted requirement the subject serves and what this run is authorized to verify (read-only, test execution, network).

## Declare criteria

Before building the ledger, list the criteria in force and each one's source: user-specified, a repo rule (cited), or the seven defaults.
The owner may add criteria, promote criterion 7 to blocking, or waive criteria 1, 3, 4, 5, 7 — never 2 or 6 — before this revision's first assessment.
A waiver offered after a finding has surfaced on this revision, whether in an earlier report or this one, is an owner override instead, not a waiver (see After the verdict).
Record every adjustment with the owner's own words.
When a step is inherently impossible to roll back (discarding scratch data known to be disposable, say), the path to `go` is revising the subject to add an approval gate, a pre-step check, a stop condition, and verification; criterion 6 accepts "rollback or stop condition," so it needs no waiver.

Defaults:

1. **Outcome**: the plan states the problem and an observable success criterion; the idea states the problem or question and the next commitment's success criterion (what continues, what stops).
   A two-way next commitment whose purpose is confirming the problem exists may leave that evidence missing, marked unverified.
2. **Claims**: no load-bearing claim is contradicted; every one-way-tier claim is verified; the rest are disclosed with the step where they'd first surface — that disclosure is not itself a blocker.
3. **Constraints**: does not violate an accepted requirement, a repo rule, or an explicit limit.
4. **Scope**: nothing required is missing, nothing unrequested is added.
5. **Executability**: the plan's first actions are explicit, ordered, and consistent, with no undecided choice that would change what that step or any later step does or produces; the idea names its next commitment with a boundary.
6. **Risk**: every one-way step in the ledger is acknowledged by the subject and carries an approval gate, rollback or stop condition, and verification.
7. **Alternative**: the subject names the cheapest credible alternative, including doing nothing; advisory by default.

## Build the ledger

One ledger, two row kinds — steps (`S<n>`) and claims (`C<n>`) — built from the subject's steps and the repository, never from the subject's own risk labels.

Each **step** row records: what it changes, dependents found by searching the repo (callers, consumers, config, docs, CI), how to revert it, whether the subject acknowledges the effect, and any gate, rollback, stop condition, or verification the subject provides.
Default a step that only touches version-controlled files and reverts with one commit to two-way, needing no rollback prose.
While building step rows, search the repo's own automation (CI workflows, deploy config, migration runners) for whether a changed path gets applied outside version control; CI limited to tests, static analysis, or a build check is not that exception.
A step is **one-way** when it:

- changes a tracked file that repo automation applies outside version control at commit, merge, or push (a CI-run migration, merge-applied infrastructure, a push-triggered release workflow) — unless the owner has explicitly named a next commitment that stops before that trigger (implementing on a branch without merging, say), in which case list the effect under `Later commitments`;
- deletes or overwrites data or a schema with no verified-restorable copy;
- damages local state outside version control: untracked or ignored files, uncommitted changes, stashes, local databases;
- rewrites or deletes published history, a tag, or a release;
- changes or removes a published contract an external consumer depends on (a public API, CLI, file or wire format, config key);
- acts on an external system: sends a message, publishes a package, deploys, spends money, changes third-party state;
- tears down or deletes infrastructure;
- changes or revokes a credential, permission, or access control; or
- acts outside version control with an effect the step and repo cannot determine (an unreviewed script or binary, a remote operation).

The decision's tier is the highest among its steps, naming which step drives it.
An idea's ledger covers only the next commitment's steps; foreseeable one-way aspects of the eventual implementation go under `Later commitments`.

Each **claim** row records a load-bearing claim — including one the subject relies on but never states, such as an unmentioned dependent, treated as the implicit claim "nothing else is affected."
Record: the claim, the step that relies on it, the step where its falsity would first surface, its tier, and its status with a citation.
Tier follows where falsity surfaces: inside a two-way step's execution or test, the claim is two-way (e.g. "the function exists" fails at that step); when falsity would only surface once a one-way step runs, and would make that step wrong or unsafe, the claim is one-way (e.g. "every existing row's `user_id` is an integer," used only by a code change whose unit tests use fake data, breaking only in a production migration).
When where it surfaces can't be determined and a one-way step uses output the claim affects, treat it as one-way too.
A subject can keep a claim two-way by adding a two-way step that would make it surface earlier — a staging integration test before deploy, say.

## Verify and assess

Verify in this order: read source and cite `file:line`; read-only commands (search callers, list tests, `git log`); side-effect-limited execution already authorized (running one test, say); a primary source over the network when authorized.
Mark anything else unverified, with the command or source that would verify it.
Treat summaries, earlier review conclusions, and the subject's own narrative as leads, never as evidence.

Claims outside repository and engineering evidence — market demand, business outcome, budget, headcount — are never ledger claims and never blockers; record them under `Not assessed` with why, left to the decision owner.
An unassessable criterion goes there too: with no accepted requirement supplied, record `Serves: none supplied`, judge criteria 3 and 4 against repo rules alone, and note the missing requirement in `Not assessed`.
An unverified engineering claim stays in `Claims`, marked unverified — it does not belong in `Not assessed`.

Assess each declared criterion against the ledger and record findings with their evidence.
A finding is a blocker only when it fails a declared criterion; everything else is advisory.
Every blocker's resolution states what change would satisfy that criterion: supply the missing verification, add a gate or rollback, narrow the scope, resolve an undecided choice — or point to another method (research, prototype, grilling).
Each blocker cites exactly one criterion; when a defect could reasonably be filed under either of two criteria, cite the more specific one.
A narrower subject can be written as a resolution; the verdict for the subject as given stays `no-go`.
Never rewrite or add to the subject.

## Verdict and report

Zero blockers is `go`, otherwise `no-go`.
Report in the conversation by default; write it to a file only if asked.
Fill this template exactly, replacing only the placeholders; `Steps`, `Claims`, and `Blockers` write `none` on the header line when empty, otherwise one `- [ID]` line per item after it:

```text
Subject: <path at blob or checksum | recorded text>; revision <id>
Kind: <plan | idea>
Serves: <accepted request or requirements reference>
Verification allowed: <read-only | test execution | network>, as authorized
Decision: go commits <next commitment>; cost <hours | days | weeks, and what is spent>; <one-way: S<n> | two-way>; blast radius <what it reaches>; owner <who decides>
Author: <user | this session's agent | other>; assessment <independent | by the author>; independent review <recommended because of S<n> | not required>
Criteria: in force <numbers>; advisory <numbers, or none>; added <text, or none>; waived before assessment <numbers, or none>; sources <defaults, user, rule files>
Steps:
- [S<n>] <mutation>; dependents: <found by search, or none>; <one-way | two-way>; handling: <present: gate, rollback or stop, verification | missing: <elements> | unhandled | not required>
Claims:
- [C<n>] <claim>; relied on by <S<n>>; falsity surfaces at <S<n>>; <one-way | two-way>; <verified | contradicted | unverified>; <citation, or the check that would verify it>
Verdict: <go | no-go>
Blockers:
- [B<n>] criterion <number>; <finding>; evidence: <citation>; resolution: <change that satisfies the criterion>
Advisory: <findings, or none>
Not assessed: <item; reason, or none>
Later commitments: <commitments that need their own verdict, or none>
Pending owner confirmation: <a pre-issued instruction to proceed on go, or none>
Owner override: <recorded decision with the owner's words, or none>
Closing: <the closing sentence for the verdict>
```

Replace each entire placeholder, including its brackets, with the selected value; preserve all fixed text outside placeholders, subject to the empty-list and fenced-text conventions stated here.
Write the report as plain lines in the reply: not inside a code fence, and with no Markdown emphasis, headings, or backticks on labels or values.
Each marker — `one-way` or `two-way`; `verified`, `contradicted`, or `unverified`; `criterion <number>` — fills its whole `;` segment: a reason or citation goes in a later segment, never in parentheses or after a colon on the marker.
The closing sentence is `this verdict applies only to revision <id> and does not authorize execution` after `go`, and `no action follows from this report; a revised subject needs a new verdict` after `no-go`.
Verbatim recorded text that spans multiple lines, or that could be misread as a field label (a line starting `Steps:`, say), goes in a fenced code block below the `Subject` line instead — the line itself then just points to it (`Subject: recorded text below; revision <id>`).
The same applies to a verbatim quotation in `Criteria: added` or `Owner override`: fence it below the report and point to it from that field.
`independent review` reads `recommended because of S<n>` only when assessment is by the author and the decision is one-way; otherwise `not required`.
`Closing` is the report's and the reply's last line: no summary, recap, or next step after it.
After `no-go`, never ask whether to proceed anyway and never offer a way to bypass, waive, or narrow the verdict as a next step — a resolution belongs inside its `- [B<n>]` line, not after `Closing`; after either verdict, do not begin implementation.
When stopping under [Stop conditions](#stop-conditions) instead, use the minimal template and omit `Verdict` and everything after it:

```text
Subject: <unresolved: what was found>
Kind: <plan | idea | unknown>
Stopped: <reason>; candidates: <list, or none>
```

## After the verdict

When the owner proceeds under `no-go`, record it as an owner override with their words; the verdict stays `no-go`.
A request to change the verdict is one of three things: a subject revision re-judges from scratch; new evidence updates that claim and re-assesses the criteria it touches; a changed requirement or constraint re-opens only criteria 3 and 4.
"I waive the rollback requirement," "I accept that risk," and plain insistence are all overrides — the verdict stands, with the reason recorded.
On re-judgment, recheck every earlier blocker against the new revision and reassess every changed section.
A revision this session's agent wrote in another request gets `Author: this session's agent; assessment by the author`.
A pre-issued "go, then implement" goes in the `go` report's `Pending owner confirmation`, for the owner to act on after reading the report; record it and end there — edit nothing, never announce that you are proceeding, and keep `Closing` word for word.

## Stop conditions

Stop without a verdict when the subject cannot be fixed to one piece of text, when the subject and the request disagree about the decision owner, or when the subject belongs to a decision another method owns (a release verdict, say — point to `release-readiness`).
Missing evidence and an unnamed next commitment are never stop conditions: they produce a blocker or a `Not assessed` entry, and the verdict follows from the declared criteria.
Every other action stays inside existing authorization: read the subject, the repository, rules, and existing review reports without asking; run a test or other side-effecting check only within existing authorization and its side-effect limits, else the claim stays unverified; write the report to a file only when asked; never modify the subject, start implementation, or make any Git or external write.
A pre-issued "go, then implement" does not take effect this run either, and needs the owner's separate request after reading the report.
