# Sentence-based homework approvals

- Upload a `.txt`, `.docx`, or text-based `.pdf` via **Upload Sentences**.
- The app detects sentence-ending `.`, `!`, `?` punctuation and stores a proposed count on the homework task.
- **Approvals** already exists in the parent/manager navigation. Review the file and adjust the verified count as needed.
- Approval awards **one point per verified sentence** into the existing point ledger; no points on upload or redo.
- Image uploads, scanned PDFs, `.doc` files and unreadable files cannot be reliably auto-counted without OCR. A parent enters the verified count on Approvals.
- Existing homework tasks with no submitted file retain their original fixed-point approval behavior.
- Counts rely on punctuation, not linguistic interpretation; abbreviations and unusual writing require review.
- An additive SQLite migration adds `homework.sentence_count` and retains existing data.

## Manager self-verification

Managers (including Jasmin) can verify and approve **their own** uploaded sentence assignments, as well as other household submissions. Each verified sentence awards one point. The audit trail records the reviewer and the points ledger records who issued the award. This does not change the separate point-request self-approval policy.
