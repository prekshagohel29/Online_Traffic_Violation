# Team ownership and boundaries

Member 1 owns the citizen/authentication user journey; Member 2 owns RTO/video/
evidence review; Member 3 owns Government/Admin/analytics/audit/reporting.

Member 1 and Member 2 folders and ZIPs have not been changed by this preparation.
The shared schema, database utilities, management CLI and fixtures are included as
common dependencies. This does not claim that one member authored every shared
line. Preserve original source credits and record actual subsequent contributions.

Member 3's upload excludes citizen/RTO pages, the video worker/detector, private
runtime data, account credentials, model weights and photos. The integration patch
changes the two shared files only after those files are supplied by the baseline.
The complete project already exists in the member packages; the central repository
becomes a runnable team project when the shared core and all modules are merged.
