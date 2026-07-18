# AI Accountant

A personal-finance assistant built as a [Claude Code](https://docs.claude.com/claude-code)
**skill**. You share your statements or expenses (CSV, PDF, image, or typed text); it keeps a
running ledger, tracks your spending against your goals and debt, generates a YTD/monthly/daily
report, and can email the latest report to you.

The workflow is: **drop statements → run `/accountant` → get a report → optionally email it.**
Because it keeps a persistent ledger, totals accumulate correctly across days rather than
resetting each session.

## How it works

1. You drop new statements into `statements/inbox/` (or just type an expense in chat).
2. You invoke the skill with `/accountant`.
3. The skill reads your profile + running ledger, parses the new statements, appends the
   transactions to `data/ledger.csv` (deduplicating), and archives the processed files.
4. It writes a Markdown report to `reports/snapshot_<date>/report.md`.
5. If you ask, it emails that report to you via `scripts/send_report.py`.

The **ledger is the source of truth**; the report is a snapshot computed from it.

## Repository layout

```
AI_Accountant/
├── .claude/skills/accountant/SKILL.md   # The skill definition (the "brain"): persona,
│                                        #   daily flow, and report format. Invoked via /accountant.
├── data/
│   ├── ledger.csv                       # Append-only running ledger — one row per transaction.
│   └── profile.json                     # Income, debt, goals, recurring expenses (created on first run).
├── statements/
│   ├── inbox/                           # Drop new statements here to be processed.
│   └── archive/                         # Processed statements are moved here (date-prefixed).
├── reports/
│   └── snapshot_<YYYY_MM_DD>/report.md  # Generated reports, one folder per run.
├── scripts/
│   ├── send_report.py                   # Emails a report via Gmail SMTP (no dependencies).
│   └── .env.example                     # Template for email credentials — copy to .env.
├── .gitignore                           # Keeps data/, statements/, reports/, and .env out of git.
└── README.md
```

### The ledger (`data/ledger.csv`)

Append-only, one row per money event. Columns:

| Column | Meaning |
|---|---|
| `date` | Transaction date, `YYYY-MM-DD` |
| `type` | `income` \| `expense` \| `saving` \| `debt` (direction of money) |
| `category` | Grouping used in reports (groceries, rent, salary…) |
| `description` | Human-readable label |
| `amount` | Always **positive**; `type` gives the direction |
| `source` | Account/instrument (checking, credit_card…) |
| `statement_file` | Origin file — used for tracing and dedup |

Dedup key: same `date` + `amount` + `description` is treated as already-logged.

## Prerequisites

- [Claude Code](https://docs.claude.com/claude-code) installed and this repo opened as the working directory.
- Python 3.8+ (`python3 --version`) — only needed for the email feature.
- A Gmail account (only if you want automatic emailing).

## Setup

### 1. Clone and open

```bash
git clone <your-repo-url> AI_Accountant
cd AI_Accountant
```

Because `data/`, `statements/`, and `reports/` are gitignored (they hold sensitive financial
data), a fresh clone won't include them. Create the runtime folders and seed the ledger:

```bash
mkdir -p statements/inbox statements/archive reports data
printf 'date,type,category,description,amount,source,statement_file\n' > data/ledger.csv
```

### 2. Configure email (optional)

Only needed if you want the skill to email reports.

1. Enable **2-Step Verification** on your Google account.
2. Create a **Gmail App Password**: https://myaccount.google.com/apppasswords
3. Copy the template and fill it in:

   ```bash
   cp scripts/.env.example scripts/.env
   ```

   Set `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD` (the 16-char app password, **not** your login
   password), and `REPORT_RECIPIENT` in `scripts/.env`.

`scripts/.env` is gitignored — never commit real credentials.

## Usage

### First run (one-time profile setup)

Open the repo in Claude Code and run:

```
/accountant
```

If `data/profile.json` doesn't exist yet, the skill interviews you for your income, debt,
goals, and recurring expenses, then saves them.

### Daily flow

1. Add today's statements to `statements/inbox/` (CSV, PDF, image, or a text file). You can
   also just type expenses directly to the skill.
2. Run `/accountant`.
3. Review the report it generates under `reports/snapshot_<today>/report.md`.
4. When prompted, choose whether to email it.

### Emailing a report manually

```bash
python3 scripts/send_report.py reports/snapshot_2026_07_18/report.md
```

The report is sent as both a plaintext body and a `.md` attachment.

## What's in each report

- **YTD summary** — total spent, saved, and debt accumulated/paid this year.
- **Money available for expenses** for the current period.
- **Goal tracking** — progress, on-track/behind, and monthly saving needed per goal.
- **Spending breakdown** by category, with biggest movers highlighted.
- **Pitfalls to avoid** — personalized warnings.

## Privacy & data safety

- `data/`, `statements/`, `reports/`, and `scripts/.env` are **gitignored** — real financial
  data and credentials never enter version control.
- The ledger is append-only; history is never silently overwritten.
- Keep backups of `data/ledger.csv` and `data/profile.json` — they are your source of truth
  and are not tracked by git.

## Extending

- **Automatic daily reports:** add a `cron` job that runs the skill/report each morning
  (currently the flow is manual — you invoke `/accountant`).
- **Signed amounts:** the ledger stores positive amounts with direction in `type`; switch to
  signed amounts (e.g. `-86.40` for expenses) if you prefer.
- **Other email providers:** `scripts/send_report.py` uses Gmail SMTP; adapt it for SES or
  another provider by changing the SMTP host/auth.
