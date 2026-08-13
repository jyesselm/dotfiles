#!/usr/bin/env python3
"""Stylometric gate for drafts in Yesselman's voice.

Checks a text file (or stdin) against the CORE.md panel bands and banned list.
Exit 0 = all checks pass; exit 1 = violations (listed on stdout).

Usage: voice-lint.py [--genre paper|grant] [draft.txt]   (stdin if no file given)

Scope: run this on a DRAFTED PASSAGE, not on a whole exported manuscript. Author
lists, section headings, figure legends, and reference lists are short lines that
drag the sentence-length median down and will fail his own published papers.
"""
import re
import sys

# Bands re-measured 2026-08-13 (second pass) after the TMO/DMS draft was removed
# from the corpus: it is student-written, not his hand, and it had been supplying
# 64% of the sentences behind the first pass. Remaining own-hand sources:
# dms-3d-features rewrites (papers, n = 51) and MIRA Section A (grants, n = 40),
# prose only, excluding methods, figure legends, references, and editorial notes.
# Papers: median 28, p90 50, p95 63, 63% >= 25 words.
# Grants: median 22, p90 34, p95 42, 38% >= 25 words.
# NOTE: n = 91 total. These bands are provisional and should be re-measured as
# soon as more genuinely own-hand prose is available.
# Re-measured 2026-08-13 (third pass) over a provenance-checked corpus of ~25,000
# words: RNAMake 2019 (n=329 sentences, median 25), RMDB 2017 (n=80, median 22),
# d3f rewrites (n=51, median 28), R01 draft (n=174, median 20), MIRA A (n=40,
# median 22), NSF RPPRs (median 16, a much tighter reporting register).
# CAUTION: his student's draft measures median 26 / 54% long, i.e. LONGER than
# his own writing. Sentence length does not discriminate his voice; treat these
# bands as advisory guardrails, not as a voice test.
MEDIAN_BAND = (19, 32)        # papers, centered on ~25
LONG_FRAC_BAND = (0.35, 0.70) # papers, ~50%
GENRE_BANDS = {"grant": {"median": (16, 27), "long_frac": (0.22, 0.50)}}
# Upper bound on a single sentence, re-measured after the TMO draft was removed.
# Papers p95 = 63, grants p95 = 42. He rejected an 88-word sentence outright as
# "way too long" (2026-08-13 clinic), so the ceiling sits between 63 and 88.
SENTENCE_WARN = 55
SENTENCE_FAIL = 75
# Fuzzed counts: "approximately 5,000 constructs" was rejected ("approximately
# isnt great either"). Rounded ratios and percentages are fine and attested
# ("~10% overlap", "approximately 1.67-fold"), so this only fires on bare round
# counts, not on percentages or fold-changes.
FUZZED_COUNT = re.compile(
    r"\b(approximately|roughly|around|about)\s+(\d{1,3},\d{3}|\d+00)\b(?!\s*[-–]?\s*fold|\s*%)",
    re.I)
COLON_BAND = (2, 13)          # measured 3.5-9.7 per 1000 words
SEMI_BAND = (1, 10)           # measured 2.2-7.0 per 1000 words
MIN_WORDS_FOR_RATES = 150     # rate checks are noise below this

# Words his own hand still uses occasionally (furthermore 3x, notably 4x, novel 4x
# across the corpus) but that CORE.md bans because he removes them in revision.
# Reported as WARN so a rewrite pass fixes them without masking hard failures.
SOFT_WORDS = {"furthermore", "notably", "novel", "indeed",
              # Genre-controlled against a student draft from the same lab on the
              # same subject (2026-08-13, per 1,000 words, his rate first):
              # however 0.18 vs 1.14, observed 0.15 vs 2.47, while 0.54 vs 1.52.
              # He uses all three, just far less often, so these advise; they do
              # not gate. An earlier pass wrongly called "however" absent from
              # his corpus; that came from a case-sensitive count.
              "however", "observed",
              # He uses "leverage" in the ordinary technical sense in his 2026
              # R01 ("Automated docking will leverage existing Rosetta
              # density-docking functionality"). Banned as vague filler ("we
              # leveraged a novel approach"), fine when it means what it says.
              "leverage", "leverages", "leveraging"}

BANNED_WORDS = [
    "delve", "delves", "delving",
    "moreover", "furthermore", "notably", "interestingly", "remarkably",
    "surprisingly", "novel", "indeed",
]
BANNED_PHRASES = [
    "it's worth noting", "it is worth noting", "in conclusion",
    "plays a crucial role", "play a crucial role", "it should be noted",
    "it was observed that", "may possibly", "could potentially suggest",
    # "hope"/"believe" family: his explicit rule, "we really dont want
    # 'hope' or 'believe'" (2026-08-13 clinic, applied to papers and grants alike)
    "we believe", "it is believed", "we hope", "it is hoped", "hopefully",
    "we are hopeful", "it is anticipated", "we anticipate that",
    "a technique known as", "a method known as",
]
# Hype vocabulary, rejected outright in the 2026-08-13 clinic ("way too boastful")
# and absent from the corpus in both genres. Priority claims are made flatly
# ("the first X", "outperforming both probes alone"), never with intensifiers.
HYPE_WORDS = [
    "groundbreaking", "unprecedented", "undoubtedly", "exciting", "revolutionary",
    "cutting-edge", "paradigm", "game-changing", "tremendous",
]
HYPE_PHRASES = [
    "major advance", "important step forward", "opens exciting",
    "of broad interest", "the rna community", "transform how the field",
]
# Field-level transformation claims: a grant move, a paper violation.
FIELD_CLAIM_PHRASES = ["transform the field", "transforming our understanding",
                       "transform our understanding"]
EM_DASH = "—"


def sentences(text):
    # strip citations/figure refs so they don't inflate word counts
    clean = re.sub(r"\((?:Figure|Supplemental|Table)[^)]*\)", "", text)
    clean = re.sub(r"[\[(][\d,\s–;-]+[\])]", "", clean)
    # Superscript citation markers sit between the period and the next capital
    # ("geometry.¹⁻³ These challenges..."), which otherwise defeats the
    # boundary match and silently fuses several sentences into one.
    clean = re.sub(r"[²³¹⁰-ⁿ₀-ₜ]+", "", clean)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"'])", clean)
    return [p.strip() for p in parts if len(p.split()) >= 3]


def main():
    argv = sys.argv[1:]
    genre = "paper"
    if "--genre" in argv:
        i = argv.index("--genre")
        genre = argv[i + 1]
        del argv[i:i + 2]
    median_band = GENRE_BANDS.get(genre, {}).get("median", MEDIAN_BAND)
    long_band = GENRE_BANDS.get(genre, {}).get("long_frac", LONG_FRAC_BAND)

    text = open(argv[0]).read() if argv else sys.stdin.read()
    words = text.split()
    n_words = len(words)
    sents = sentences(text)
    problems = []   # hard failures
    warnings = []   # soft: things his own hand does, but he edits out in revision

    if EM_DASH in text:
        for i, line in enumerate(text.splitlines(), 1):
            if EM_DASH in line:
                problems.append(f"em-dash (banned, CORE.md) on line {i}: {line.strip()[:80]}")
    if re.search(r"\s-\s", text):
        problems.append("spaced-hyphen connector (banned, CORE.md): use colon/comma/semicolon")

    lower = text.lower()
    for w in BANNED_WORDS:
        if re.search(rf"\b{w}\b", lower):
            msg = f"banned word: '{w}'"
            if w in SOFT_WORDS:
                warnings.append(msg + " (he uses this rarely but edits it out; prefer to cut)")
            else:
                problems.append(msg)
    for p in BANNED_PHRASES:
        if p in lower:
            problems.append(f"banned phrase: '{p}'")
    for w in HYPE_WORDS:
        if re.search(rf"\b{w}\b", lower):
            problems.append(f"hype word: '{w}' (state the claim flatly; 'the first X' is allowed)")
    for p in HYPE_PHRASES:
        if p in lower:
            problems.append(f"hype phrase: '{p}' (name the specific capability instead)")
    for p in FIELD_CLAIM_PHRASES:
        if p in lower:
            if genre == "grant":
                warnings.append(f"field-level claim '{p}': a grant move, keep it out of papers")
            else:
                problems.append(
                    f"field-level claim '{p}' in a {genre}: papers close on utility, "
                    f"not on transforming the field (save it for grants)")

    if sents:
        lens = sorted(len(s.split()) for s in sents)
        median = lens[len(lens) // 2]
        long_frac = sum(1 for L in lens if L >= 25) / len(lens)
        # Asymmetric by design (2026-08-13). He asked for "shorter simpler
        # sentences ... it cant be all the time but should prefer", said of prose
        # already at his measured median. Long prose therefore gates; short prose
        # only advises, because short is the direction he wants.
        if median > median_band[1]:
            msg = (f"sentence-length median {median} above the {genre} ceiling "
                   f"{median_band[1]}; he asked for shorter, simpler sentences than "
                   f"his own corpus median")
            problems.append(msg) if len(sents) >= 10 else warnings.append(
                msg + f" [only {len(sents)} sentences]")
        elif median < median_band[0]:
            warnings.append(
                f"sentence-length median {median} below the {genre} band "
                f"{median_band}; acceptable if this is a run of parallel "
                f"measurements, but check the interpretation is not also clipped")
        if len(sents) >= 8 and long_frac > long_band[1]:
            problems.append(
                f"{long_frac:.0%} of sentences run >=25 words, above the {genre} "
                f"ceiling of {long_band[1]:.0%}; prefer shorter, simpler sentences "
                f"and save the long ones for interpretation")

    for s in sents:
        L = len(s.split())
        if L > SENTENCE_FAIL:
            problems.append(f"sentence of {L} words exceeds his ceiling of {SENTENCE_FAIL} "
                            f"(p99 = 63; he rejected an 88-word sentence as 'way too long'): "
                            f"{s[:70]}...")
        elif L > SENTENCE_WARN:
            warnings.append(f"sentence of {L} words is past p95 ({SENTENCE_WARN}); "
                            f"check it does not run out of breath: {s[:60]}...")

    # Purpose opener: confirmed required by minimal-pair test ("version 2 is
    # better as it explains why we did things"). WARN rather than FAIL, because a
    # bare method opener is legitimate when the previous paragraph supplied the
    # motivation, which this script cannot see.
    for para in [p for p in re.split(r"\n\s*\n", text.strip()) if len(p.split()) >= 40]:
        head = para.strip()[:90]
        has_purpose = re.match(r"\s*To\s+\w+", para.strip()) or \
            re.search(r"\b(To (determine|test|quantify|assess|explore|investigate|"
                      r"measure|evaluate|establish) whether|To (determine|quantify|"
                      r"assess|test|explore|investigate|measure)\b|We reasoned that|"
                      r"we asked whether)", para)
        bare_method = re.match(r"\s*We\s+(measured|probed|performed|calculated|"
                               r"analyzed|analysed|computed|compared|generated|ran)\b",
                               para.strip())
        if bare_method and not has_purpose:
            warnings.append(
                "paragraph opens with a bare method statement and states no purpose: "
                f"'{head}...' Open with 'To [goal], we [action]' unless the previous "
                "paragraph already established why.")

    # "set" as a verb. Every one of the 32 set/sets/setting occurrences in his
    # 28,599-word corpus is a noun ("set of motifs", "data set", "set up"); he
    # uses "determine" instead. Matched only before an article, so "set of
    # motifs" and "data set" do not trip it.
    for m in re.finditer(r"\bsets?\s+(?:a|an|the)\s+\w+", text, re.I):
        if not re.match(r"\bset\s+up\b", m.group(0), re.I):
            warnings.append(f"'{m.group(0)}': 'set' is never a verb in his corpus; "
                            f"he writes 'determines'")
    # "carrying" where "containing" is his word (32 vs 2 occurrences).
    for m in re.finditer(r"\bcarr(?:y|ies|ying)\b", text, re.I):
        warnings.append(f"'{m.group(0)}': he writes 'containing' (32 uses vs 2)")

    for m in FUZZED_COUNT.finditer(text):
        problems.append(f"fuzzed count '{m.group(0)}': give the exact number or write XXX "
                        f"(rounded ratios and percentages are fine)")

    if n_words >= MIN_WORDS_FOR_RATES:
        colon_rate = text.count(":") / n_words * 1000
        semi_rate = text.count(";") / n_words * 1000
        # One-directional since 2026-08-13: "we generally want to avoid colons
        # and semicolons although this shouldnt be hard rule". Earlier versions
        # nagged when a draft had too FEW, which inverted his preference.
        if colon_rate > COLON_BAND[1]:
            warnings.append(
                f"colon rate {colon_rate:.1f}/1000 words is high (his prose runs "
                f"{COLON_BAND[0]}-{COLON_BAND[1]}, and he prefers to avoid them); "
                f"try a comma or a new sentence")
        if semi_rate > SEMI_BAND[1]:
            warnings.append(
                f"semicolon rate {semi_rate:.1f}/1000 words is high (his prose runs "
                f"{SEMI_BAND[0]}-{SEMI_BAND[1]}, and he prefers to avoid them); "
                f"two short sentences usually read better")

    # Rejection lexicon. Only the explicitly delimited LINT:HARD block is machine
    # read. The rest of REJECTIONS.md is prose documentation, and scraping it
    # produced false positives on ordinary words ("have", "interactions") that
    # failed his own published papers.
    try:
        rej = open(__file__.rsplit("/bin/", 1)[0] + "/REJECTIONS.md").read()
        block = re.search(r"<!-- LINT:HARD -->(.*?)<!-- /LINT:HARD -->", rej, re.S)
        if block:
            for line in block.group(1).splitlines():
                m = re.match(r"\s*-\s+([a-zA-Z][a-zA-Z '-]*?)\s*(?:\||$)", line)
                if not m:
                    continue
                t = m.group(1).strip().lower()
                if t and t not in SOFT_WORDS and re.search(rf"\b{re.escape(t)}\b", lower):
                    problems.append(f"rejection lexicon: '{t}'")
    except OSError:
        pass

    med = sorted(len(s.split()) for s in sents)[len(sents) // 2] if sents else 0
    stats = f"{n_words} words, {len(sents)} sentences, median {med} words/sentence"
    for w in warnings:
        print(f"  WARN {w}")
    if problems:
        print(f"FAIL ({len(problems)} issue(s), {stats}):")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    print(f"PASS ({stats})")
    sys.exit(0)


if __name__ == "__main__":
    main()
