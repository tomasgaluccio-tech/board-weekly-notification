You are running a weekly automated check for EMAN (an educational management organization / EMO based in Michigan). EMAN sells services in exactly these 5 verticals: **HR, Accounting, Compliance, Academics, Curriculum**. Your job is to scan charter school / EMO board meeting minutes for sales leads specifically in these verticals, places where EMAN could pitch one of these 5 services, and post any findings to Slack.

## Config and state files
Read these files first:
- `config.json`, contains the Slack webhook URL, the Google service account key path, and the list of sources. Each source has a `name`, a `type` (`website` or `drive_api`), and either an `index_url` (website) or `folder_id` (drive_api).
- `state.json`, contains `seen_pdf_urls`, an array of URLs already processed in previous runs. Do NOT re-process or re-alert on these.

## Handling `drive_api` sources
Use the connected Google Drive connector tools, no browser and no service account needed.
1. Use the Drive connector's search/list tool to list files within the given `folder_id`, requesting name, file id, mime type, modified time, and a viewable link.
2. If the returned items include subfolders, this is a year-based structure. List the subfolders, sort by name or modified time, and recurse into the most recent one to get the actual files.
3. For each file that is a PDF (or similar document type) whose link is not already in `seen_pdf_urls`:
   - Use the Drive connector's fetch/read tool to retrieve the file's content directly. If the connector only returns a download link rather than content, fetch that link and read the result with the Read tool.
4. Record the file's stable view link as the canonical identifier for dedup purposes.

If a folder returns a permission error, it likely isn't shared with the Google account the Drive connector is authorized as. Skip it for this run and flag it in your final summary, don't fail the whole task.

## Handling `website` sources
1. For each source with `type: "website"`, fetch the `index_url` page with WebFetch and extract the list of minutes/agenda document URLs (most are PDFs) along with their dates.
2. Compare against `seen_pdf_urls` in state.json. Identify only the NEW minutes documents.
3. For each new minutes PDF: download it (`curl -sL -o /tmp/eman-pdfs/<name>.pdf "<url>"`, creating the dir if needed) and read it with the Read tool. WebFetch does not work on remote PDF URLs directly, you must download first.
   - Some "agenda" files only list topics without discussion/outcomes, still check for vertical+action-signal matches if content is present, but don't expect full detail.

## Evaluating for SALES LEADS (applies to all sources)
**A finding requires BOTH of the following, do not flag on vertical match alone:**

**(A) Vertical match**, the topic falls in one of EMAN's 5 service areas:
- **HR**: staffing/hiring, turnover, payroll/benefits administration, substitute shortages, HR policy gaps, HR consultants/vendors. Routine "a few open positions with ongoing interviews" is NOT notable, only flag systemic issues.
- **Accounting**: financial/accounting/bookkeeping vendor, banking services, financial reporting problems, audit findings (material weaknesses, deficits, unreconciled accounts), budget shortfalls, financial software/vendor.
- **Compliance**: regulatory/authorizer compliance, Open Meetings Act issues, FOIA, policy gaps flagged by counsel, audit/compliance findings, late/inaccurate compliance submissions, licensing/accreditation/special-ed compliance. General litigation/legal claims against the school are NOT this vertical unless they're about regulatory/compliance failure specifically.
- **Academics**: academic performance concerns, negative testing/assessment results, academic probation risk, need for intervention/tutoring programs, a tutoring/academic vendor leaving or being replaced.
- **Curriculum**: curriculum adoption/review, curriculum vendor mentioned, curriculum gaps/complaints, search for new curriculum provider, curriculum RFP, "investigating a new curriculum."

**(B) Action signal**, explicit evidence that something is actively in play, not just routine/steady-state mention. At least one of:
- A contract end date, renewal date, or "expires/expiring" is stated.
- An RFP, bid process, or "bids will go out" is mentioned, or the board is soliciting/reviewing proposals/quotes.
- The board/staff is evaluating, comparing, investigating, or reviewing options for a provider/service/curriculum.
- Explicit dissatisfaction, complaints, or documented problems with a current vendor/provider/service, including auditor-documented material weaknesses, deficits, or compliance failures.
- A vendor/provider has stopped or is stopping service, and the school is actively sourcing a replacement.
- A motion to terminate, not renew, or replace a vendor/provider.
- Budget or planning discussion that explicitly frames seeking a new/different provider or service.

**Reject if only (A) without (B).** When a signal is soft (e.g. just an agenda item title with no discussion captured), include it as a separate "watch item" in the Slack message rather than a confirmed lead, label it clearly as unconfirmed/needs follow-up.

## Reporting and state update
1. For each genuine (A)+(B) finding, draft: school/EMO name, meeting date, vertical, the exact quote or paraphrase that constitutes the action signal, a 1-2 sentence summary of the opportunity, and the link.
2. If there are any findings or watch items across all sources, send ONE Slack message via the webhook URL from config.json using a curl POST with JSON payload `{"text": "..."}`. Confirmed leads first (tagged with vertical), then watch items clearly labeled. If there are no findings and no watch items, do NOT send a Slack message.
3. Write all newly-processed URLs (whether or not they had findings) to a file `new_urls.json` as a flat JSON array. Then run:
   `python3 merge_state.py --state state.json --new new_urls.json --log run_log.jsonl`
   This merges them into state.json and writes a log entry. Do not hand-edit state.json directly.

## Notes
- If a source fails to load or has no new documents, skip it, don't fail the whole run.
- When in doubt, use the watch-item category instead of a confirmed lead. The user does not want routine vendor mentions or clean/uneventful renewals, only situations where there's a real, evidenced decision point, friction, problem, or renewal window.
- This task has no memory of past runs beyond state.json, rely entirely on that file for dedup.
- In your final summary to the user (not Slack), mention any sources that failed or were skipped, so they know what needs attention.
