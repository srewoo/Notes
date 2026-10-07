# Jira fetch — connector details

Read this during Phase 0 (fetch) and Phase 2 (reading the plan and review).

## Fetching the ticket

Fetch via Atlassian Rovo (`getAccessibleAtlassianResources` for the cloud ID,
then `getJiraIssue`); if that connector errors or isn't loaded, retry once on
the Atlassian MCP connector (same tool names). Both fail → stop and say so;
never work from a remembered or guessed ticket.

`getJiraIssue` omits comments, subtasks and links by default, so always pass:

```
fields: ["summary","description","status","issuetype","components","labels",
         "comment","subtasks","issuelinks","attachment","parent","updated"]
responseContentFormat: "markdown"
```

If `fields.comment.total` exceeds the comments returned, say how many were not
read.

## The plan — where to look

- Description and acceptance criteria.
- Grooming sections — match the marker text at any heading level:
  `BEGIN: groom-story-functionally`, `BEGIN: functional-grooming`,
  `BEGIN: technical-grooming`, each ending at its `END:` twin.
- Subtasks. A subtask with grooming → also read its parent's description.
- Linked Confluence/plan docs → `getConfluencePage`.
- Figma links → `get_design_context`, only if the ticket is UI work.

## The review — sources to check

Check each and record what you found in each, even when empty:

- Jira comments that change scope or approach (not status pings or "+1").
- Linked docs whose title or body identifies them as a review (architect /
  design / tech review, ADR).
- Linked MRs (`getJiraIssueRemoteIssueLinks`, or MR keys in the ticket) →
  their review notes via GitLab `get_merge_request_notes`.

No source yields a review → write `Review: none found (checked: comments,
linked docs, MRs)`. Do not promote an ordinary comment to "the review".
