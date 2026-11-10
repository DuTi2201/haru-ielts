# Prompt for the deployment agent

Copy everything below the line into the agent that has full access to the VM and to GitHub.

---

You are deploying **Haru English**, a private IELTS self-study app for one learner, next to an
existing live product on the same Google Cloud VM. Work carefully: the existing product must keep
running and must not be changed.

## Read first
1. `docs/HANDOFF.md` in `github.com/DuTi2201/haru-ielts` — what exists, what is checked, known debt.
2. `scripts/b1/README.md` in the same repo — how the course content is generated.
3. `deploy/README.md` and `deploy/haru-gcp.sh` — how the original product is deployed.

## The two systems
| | Existing: Haru (Korean) — DO NOT CHANGE | New: Haru English (IELTS) |
| --- | --- | --- |
| Backend repo | `DuTi2201/haru-korea` | `DuTi2201/haru-ielts` (fork at `e93bc78` + B1 course) |
| Frontend repo | `DuTi2201/haru-korean-journey` (Lovable) | `DuTi2201/haru-ielts-journey` (untouched fork) |
| On the VM | `/opt/haru/src`, compose project `haru`, containers `haru-api-1`, `haru-worker-1`, `haru-db-1`, `haru-redis-1`, `haru-caddy-1`, database `haru` | nothing yet |

The VM today: 2 vCPU, 2 GB RAM, about 750 MB already in swap, 11 GB disk free. Containers have
memory limits (api 500 MB, worker 700 MB, db 700 MB, redis 220 MB, caddy 100 MB).

## Hard rules
* Never modify, restart, rebuild or migrate anything of the Korean product, except the two things
  listed under "Allowed contact with Haru". Never write to database `haru`. Never push to the two
  Korean repositories.
* Before any step that stops the VM or reloads Caddy, tell the owner what will happen and for how
  long, and wait for a time they choose. The owner agreed to upgrade this VM; they did not agree
  to a time.
* Take a database backup of `haru` and confirm it is readable before the VM is stopped.
* Never print, commit or paste a secret. Secrets live only in an env file on the VM (mode 600).
  Ask the owner whether the new app may reuse the Korean app's Gemini / Google TTS / Azure Speech
  keys or should get its own; do not copy them without that answer.
* If a step fails twice, stop and report; do not improvise around the Korean product.
* Keep notes: update `docs/HANDOFF.md` (state, decisions, what is checked, what is not) in the same
  commit as each piece of work, and push. Other agents continue from those notes.

## Allowed contact with Haru
1. Resizing the VM (one stop/start, in the owner's chosen window). After the start, check that all
   five `haru-*` containers are healthy and `https://<haru domain>/healthz` answers before going on.
2. One added site block in the Caddy configuration for the new hostname, then a config reload
   (`caddy reload`, not a container restart). Validate the config first (`caddy validate`).
   If you would rather not touch Haru's Caddy at all, run the new stack on its own port behind its
   own Caddy and say so; either is acceptable, choose the one with less risk and explain.

## Target layout
* VM: 4 GB RAM (for example e2-medium). Confirm the machine type and the monthly price difference
  with the owner before resizing.
* `/opt/haru-ielts/src` — clone of `DuTi2201/haru-ielts`; `/opt/haru-ielts/compose.env` — secrets.
* Compose project name `haru-ielts`, its own network, its own containers, its own volumes.
  Suggested limits: api 400 MB, worker 500 MB, db 350 MB, redis 64 MB. A separate Postgres container
  is preferred to a second database inside `haru-db-1`, because it needs no change to Haru.
* Database `haru_ielts`, its own role and password, its own `JWT_SECRET`.
* Hostname: ask the owner. If they have none, an `sslip.io` name on the VM's address is fine
  (the Korean frontend already uses that pattern).
* A daily database backup for the new database, in the same manner as the Korean one, to a
  separate path.

## Code work needed before it can boot
The fork still contains Korean-only code and data. Do the minimum to boot cleanly first, then the
rename. Each item is its own commit on a branch, merged when tests pass.

1. **Boot with the B1 seed.** `app/seed/lessons` now holds 42 `b1-*.json` lessons and
   `app/seed/exercises/b1/`. Other seed folders are still Korean (`nikl`, `exams`, `passages`,
   `editorial`, `placement`, `images.json`, `practice_*.json`, `word_icons.json`) and several
   services expect Korean lesson slugs (the Hangul lesson first, TOPIK banks, deck lessons,
   daily reading passages tied to grammar cards). Remove or switch off what cannot work without
   Korean content; do not leave a route that returns Korean data. Keep a list in HANDOFF.md of
   what you switched off.
2. **Migrations.** Run `alembic upgrade head` on the empty new database. If a migration seeds
   Korean rows (question types, product settings), add a new migration that removes them or adds
   the English equivalents; do not edit old migrations that are already applied on Haru.
3. **Voices.** `app/services/azure_tts.py` only accepts `ko-KR-…Neural` voices and sends text
   through `korean_g2p`. Add English voices (en-GB and en-US neural), skip the Korean
   pronunciation step, and make the default voice configurable. Google Chirp voice defaults are
   also Korean. Vietnamese lecture voice stays.
4. **Billing and abuse controls.** This is a single-user private app: disable payments, trials and
   signup throttling; keep login. One account for the owner; registration closed after that.
5. **Tests.** Make the suite pass on the fork. 31 tests in `tests/test_lesson_seed.py` and one in
   `tests/test_lesson_sessions.py` assert Korean content: rewrite them for the B1 seed where the
   rule still matters (sittings teach in order, a sitting is not too heavy, learner voice), delete
   the ones about Hangul, hanja and TOPIK. Report the before/after counts.
6. **Rename (after it runs).** `hangul` → `headword`, `*_ko` → `*_en`, `topik_tip_vi` →
   `exam_tip_vi`, in models, schemas, seeds (`scripts/b1/build.py` writes them), a new migration,
   and the frontend types. One mechanical commit per repo; no behaviour change.

## Frontend
* Lovable cannot import an existing repository (its Git sync only exports). Do not spend the
  owner's Lovable credits recreating the app. Build `DuTi2201/haru-ielts-journey` and serve it
  from the VM under the new hostname, or ask the owner whether they want a Lovable remix of the
  Korean project instead.
* `.env` in that repo still points `VITE_API_BASE_URL` at the Korean API. Change it to the new
  API before any build. The app must never call the Korean API.
* Replace Korean and TOPIK wording in the UI with IELTS wording only where a screen is reachable;
  hide screens whose backend you switched off.

## Order of work
1. Read, then write a short plan into `docs/HANDOFF.md` and show it to the owner.
2. Code work items 1–5 on a branch, tested locally with docker compose (not on the VM).
3. Ask the owner for the resize window. Backup, resize, verify Haru.
4. Bring up the new stack, run migrations, let the seed load, create the owner's account.
5. Caddy site block or separate Caddy; TLS; health check.
6. Frontend build pointed at the new API; open it and study one lesson end to end.
7. Rename (item 6), redeploy.
8. Final notes in HANDOFF.md; push everything.

## Done means
* `https://<new host>/healthz` answers; the frontend loads; the owner can log in.
* Lesson list shows the 42 B1 units in order; Unit 1 opens; its cards, a multiple-choice question,
  a sentence-building question, a dictation with an English voice and the speaking task all work.
* Review queue offers B1 cards the day after they are studied.
* All `haru-*` containers healthy, Korean site unchanged, `free -m` shows no swap pressure.
* Test suite of `haru-ielts` passes; the counts are in HANDOFF.md.
* Nothing Korean is reachable from the new frontend.

## Report back to the owner
What you did, what you switched off, what you could not verify, the new URLs, where the env file
and backups are, memory use after deployment, and the next three items from HANDOFF.md.
