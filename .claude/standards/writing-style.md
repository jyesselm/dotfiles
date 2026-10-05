# Writing voice: index

Yesselman's scientific writing voice, split by genre. Start with the core, then link the
genre you need. Rebuilt 2026-06-25, evidence-backed: every load-bearing rule in the core
carries a verbatim quote from his own-hand 2025-26 corpus (dms-3d-features rewrites,
TMO/DMS draft, 2026 MIRA renewal). The 2026-06-01 rules-only version and the corpus-only
predecessor are in git history.

- **Core (all genres, sole authority on rules):** `@~/.claude/standards/writing/CORE.md`
- **Exemplars (paragraphs to imitate, by rhetorical job):** `~/.claude/standards/writing/EXEMPLARS.md`
- **Rejection lexicon (never-say → say-instead):** `~/.claude/standards/writing/REJECTIONS.md`
- **Automated gate:** `python3 ~/.claude/standards/writing/bin/voice-lint.py --genre paper|grant <file>`
- **Papers / manuscripts:** `~/.claude/standards/writing/papers.md`
- **Grants & specific aims:** `~/.claude/standards/writing/grants.md`
- **Responses to reviewers:** `~/.claude/standards/writing/reviewer-responses.md`
- **Short-form (email, talks):** `~/.claude/standards/writing/short-form.md`

To write in his voice for a genre, `@import` the matching file (it pulls in the core).

## Voice at a glance
Clear, concise, direct. Active voice and first-person plural; claims stated assertively
(low hedging); concrete with numbers inline (R² = …); technical terms glossed on first use.
Sentences are long and well-articulated (median ~26 words in papers, ~22 in grants;
more than half run 25+ words), structured with colons and semicolons, NOT staccato. One interpretive landing closes each
paragraph. **No em-dashes** (en-dashes fine in Watson–Crick). "We asked whether" is allowed
sparingly, for genuine questions. Genre shifts: papers close understated (utility), grants
go bold (a "first"/field-level claim), reviewer replies concede-first, short-form is
neutral-professional.
