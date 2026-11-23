#!/usr/bin/env python3
"""One Line, Best Line (u-gudril-cool-one-line-best-line-b8c41f4d).

Writes one line (1-240 chars) to /output/entry.txt: a single entertaining
line the house judge (z-ai/glm-5.3-flash) compares two at a time against
its published brief. The brief weighs, most important first:

  1. one line of text on a free and entertaining theme, inside 240 chars;
  2. stops the scroll in its first few words;
  3. genuinely entertaining -- funny or surprising or delightful, rather
     than merely clever or trying hard;
  4. lands as one line -- the whole idea in a single sentence, with a
     turn or a punch at the end;
  5. feels fresh -- an idea or twist a reader has not met a hundred
     times before.

"A line that has to be explained has already lost." So the program
keeps a shortlist of candidate lines, scores each against those same
yardsticks with a deterministic proxy scorer, and writes the strongest
one. The choice is fully deterministic: the same shortlist always
yields the same line. No network, no clock, no randomness.
"""

import os
import re
import sys

# Candidate lines, each one sentence and under the 240-char gate.
# All original, written for this entry.
CANDIDATES = [
    # D: an elevator that sounds exhausted -- personification with a
    # polite punch at the end.
    "Our elevator apologized for the delay in a voice so tired I held "
    "the door for it on my way out.",
    # L: an owl that only blinks when I do -- creepy, funny, and short.
    "The owl on my neighbour's roof only blinks when I do, and I have "
    "stopped testing it.",
    # N: the moon follows me home -- sweet, strange, one turn.
    "The moon followed me home again last night, so I left the porch "
    "light on in case it gets lost without me.",
    # O: the vacuum is my landlord -- relatable, concrete, one punch.
    "I named my vacuum cleaner after my landlord because both of them "
    "show up unannounced and take things that were mine.",
    # P: the vending machine's secret -- a confession with a twist.
    "The vending machine gave me two chocolate bars by mistake, and I "
    "have never told anyone, including the machine.",
    # Q: my shadow quit -- the shadow gets the better life.
    "My shadow quit following me yesterday \u2014 it sent a postcard "
    "from the beach saying the light here is terrible.",
    # R: the pigeons unionised -- animals with office habits.
    "The pigeons have unionized: they now coo in shifts and demand "
    "breadcrumbs by 8 a.m. sharp.",
    # G: the foghorn at 3 a.m. -- insomniacs wave back.
    "The foghorn sounds every night at 3 a.m., and the insomniacs on "
    "this street have started waving back.",
    # H: the parking meter is an old enemy now.
    "I fed the parking meter my last coins and it still expired, so "
    "now I just wave at it every morning like an old enemy.",
    # E: the snowman wears my ex's scarf -- a spring argument.
    "I built a snowman with my ex's scarf, and now every spring I lose "
    "the same argument with the sun.",
    # C: the pigeon brings friends -- I pay rent to birds.
    "The pigeon outside my window has started bringing friends, and I "
    "am now the only tenant in this building paying rent to birds.",
    # O2: the owl again -- who started the blinking?
    "The owl on my neighbour's roof blinks exactly when I do, and I "
    "have stopped checking who started it.",
    # H2: the meter and I nod now -- the feud is mutual.
    "I fed the parking meter my last coins and it still expired, so "
    "now we just nod at each other like old enemies every morning.",
    # P2: the vending machine's secret, told to no soul.
    "The vending machine gave me two chocolate bars by mistake, and I "
    "have never told a soul, including the machine.",
    # W: two strangers keeping a promise neither made.
    "I waved at a neighbour I had never met, and now we wave every "
    "day, two strangers keeping a promise neither of us made.",
    # S: the streetlight spells my name wrong.
    "The streetlight outside my window flickers in Morse code, and I "
    "am almost certain it is spelling my name wrong.",
    # B: the bus driver and I wave at a stranger.
    "The bus driver waves at me now, and I wave back, and neither of "
    "us has any idea who the other one is.",
    # U: my umbrella only opens indoors now.
    "My umbrella only opens indoors now, like it is showing off for "
    "the furniture.",
    # L2: the lift takes me where it wants to go.
    "I told the lift we were going down and it took me to the roof "
    "instead, so now I just ask it where it wants to go.",
    # CTRL: deliberately weak control -- abstract praise, no image,
    # no turn, no punch. The scorer must rank this last.
    "Life is beautiful and every day brings amazing new opportunities "
    "to smile and be happy.",
]

# Concrete image words: things a reader can see, hear or touch. An
# early one means the line stops the scroll (criterion 2).
IMAGE_WORDS = (
    "elevator", "owl", "moon", "vacuum", "vending", "shadow",
    "pigeon", "pigeons", "foghorn", "meter", "snowman", "scarf",
    "porch", "roof", "beach", "chocolate", "streetlight", "bus",
    "umbrella", "lift", "neighbour", "wave", "morse", "driver",
)

# Subjects the field has met a hundred times: a line built on one
# starts behind on freshness (criterion 5).
TIRED_SUBJECTS = (
    "roomba", "toaster", "wi-fi", "wifi", "houseplant", "plant",
    "therapist", "alexa", "fridge", "goldfish", "cat on my laptop",
    "laptop",
)

# Subjects a reader has rarely met in a one-liner: freshness
# (criterion 5).
FRESH_SUBJECTS = (
    "elevator", "owl", "foghorn", "parking meter", "shadow",
    "snowman", "pigeon", "vending machine", "moon followed",
    "streetlight", "bus driver", "umbrella", "lift", "neighbour",
)

# Abstract praise: the brief says "merely clever or trying hard"
# loses to genuinely entertaining; abstract praise is neither.
ABSTRACT_PRAISE = (
    "beautiful", "amazing", "wonderful", "incredible", "magical",
    "perfect", "every day brings", "new opportunities",
)

# Flat clichés that cost a line its voice and its freshness.
CLICHES = (
    "every day brings", "smile and be happy", "live laugh love",
    "my cat", "my plants",
)

# Formats the field has met a hundred times (criterion 5): the
# double-dispense vending-machine anecdote is a known trope.
TIRED_FORMATS = (
    "gave me two",
    "gave me an extra",
)

# Turn markers: the sentence pivots, then lands its punch
# (criterion 4). Compared lowercased.
TURN_MARKERS = (
    "and i", "so i", "so now", "still", "including the",
    "and my", "but", "never told", "neither",
)

# Two unrelated domains colliding in one line: the incongruity that
# makes a line funny instead of merely clever (criterion 3).
INCONGRUITY_PAIRS = (
    ("elevator", "apologized"),
    ("owl", "testing"),
    ("owl", "started"),
    ("moon", "porch light"),
    ("vacuum", "landlord"),
    ("vending machine", "told"),
    ("shadow", "postcard"),
    ("pigeons", "shifts"),
    ("foghorn", "waving"),
    ("parking meter", "old enemy"),
    ("parking meter", "nod"),
    ("snowman", "argument"),
    ("pigeon", "rent"),
    ("streetlight", "morse"),
    ("bus driver", "wave"),
    ("umbrella", "indoors"),
    ("lift", "roof"),
    ("neighbour", "promise"),
)

# The punch lives in the final clause (criterion 4).
PUNCH_TAILS = (
    "on my way out", "stopped testing it", "without me",
    "were mine", "the machine", "is terrible", "sharp",
    "waving back", "old enemy", "with the sun", "to birds",
    "who started it", "a soul", "neither of us made", "name wrong",
    "who the other one is", "for the furniture", "wants to go",
)

# Reader rubric, /25 (5 per brief criterion), scored by the author
# against the published brief before the v3 proxy ran. The proxy
# narrows the field; the rubric breaks its ties, because only a reader
# can tell a warm surprise from a merely clever one. Order matches
# CANDIDATES.
RUBRIC = [
    20,  # 0 elevator: polite, tired, good punch; talking-lift shape
    22,  # 1 owl: arresting hook, creepy-funny, short
    21,  # 2 moon: delightful, sweet, slightly soft punch
    19,  # 3 vacuum: good middle, punch lands mid-sentence
    20,  # 4 vending "anyone": funny confession, known trope
    21,  # 5 shadow: postcard from the beach, strong turn
    18,  # 6 pigeons: office habits, colon softens the landing
    21,  # 7 foghorn: insomniacs wave back, fresh and odd
    22,  # 8 meter: "my last coins", "old enemy" lands hard
    20,  # 9 snowman: poetic more than funny
    20,  # 10 pigeon-rent: "paying rent to birds", solid
    22,  # 11 owl2: "who started it" is the better punch
    21,  # 12 meter2: mutual nod, softer than "old enemy"
    21,  # 13 vending "soul": best idiom of the pair, known trope
    20,  # 14 neighbour-wave: sweet, mild hook
    23,  # 15 streetlight: "spelling my name wrong", very fresh
    24,  # 16 bus: warm, funny, surprising, freshest of the field
    19,  # 17 umbrella: cute, short, soft landing
    20,  # 18 lift: playful, "where it wants to go" is soft
    6,   # 19 control: abstract praise, no image, no turn
]

OUTPUT_PATH = "/output/entry.txt"
MAX_CHARS = 240


def score_line(line):
    """Score one candidate the way the judge's brief weighs a line.

    Returns points; higher is better. Criterion order follows the
    brief: on-theme first, then scroll-stop, entertaining, one
    sentence with a punch, freshness.
    """
    low = line.lower()
    points = 0.0

    # 1. On theme: one line of entertaining text, one sentence, no
    # throat clearing, a length that can hold an idea and a punch.
    if line.count(".") == 1 and "!" not in line and "?" not in line:
        points += 2.0  # a single sentence
    if not low.startswith(("so ", "well ", "hey ", "listen ",
                           "imagine ", "picture this ")):
        points += 1.0  # no throat clearing
    size = len(line)
    if 80 <= size <= 140:
        points += 1.0  # long enough for a turn, short enough to land
    elif size < 60 or size > 200:
        points -= 1.0

    # 2. Stops the scroll: a concrete image inside the first 30 chars.
    head = low[:30]
    if any(word in head for word in IMAGE_WORDS):
        points += 3.0
    # Opening on a concrete subject (The/My + noun) hooks faster than
    # an abstraction or a setup clause.
    if low.startswith(("the ", "my ", "our ", "i ")):
        points += 1.0
    # A vivid opening verb (apologized, followed, quit, sounds) beats
    # a flat one (is, was, has). The first six words are the scroll
    # stop (v3: was four; "flickers" lands fifth and still hooks).
    first_words = low.split(" ")[:6]
    if any(w in first_words for w in ("apologized", "followed", "quit",
                                      "sounds", "unionized", "fed",
                                      "built", "named", "gave", "waves",
                                      "flickers", "told", "blinks")):
        points += 1.0

    # 3. Genuinely entertaining: incongruity, then a turn, and no
    # abstract praise doing the work instead of the joke.
    for subj, verb in INCONGRUITY_PAIRS:
        if subj in low and verb in low:
            points += 2.0
            break
    turns = sum(1 for word in TURN_MARKERS if word in low)
    points += min(turns, 2) * 1.5
    for word in ABSTRACT_PRAISE:
        if word in low:
            points -= 2.0
    for cliche in CLICHES:
        if cliche in low:
            points -= 3.0

    # 4. Lands as one line: two clauses joined by a comma or dash,
    # and the punch sits in the final clause.
    if "," in line or "\u2014" in line or ":" in line:
        points += 1.0
    tail = low.rsplit(",", 1)[-1].rsplit("\u2014", 1)[-1]
    if any(word in tail for word in PUNCH_TAILS):
        points += 2.0
    # A punch that introduces a new idea, not one that merely echoes
    # the setup: the final clause holds a content word the opening
    # never used (v3: "old enemy", "the other one", "my name wrong"
    # pay; "including the machine" repeats the setup and does not).
    _STOP = {"including", "and", "the", "with", "that", "this",
             "from", "have", "has", "never", "just", "like", "every",
             "still", "when", "where", "what", "about", "after",
             "before", "into", "over", "under", "without", "would",
             "could", "should", "there", "here", "then", "than",
             "they", "them", "their", "your", "yours", "mine",
             "ours", "almost", "really", "very", "much", "more"}
    head_words = set(re.findall(r"[a-z']+", low.split(",")[0]))
    tail_words = set(re.findall(r"[a-z']+", tail))
    if any(len(w) > 3 and w not in head_words and w not in _STOP
           for w in tail_words):
        points += 1.5

    # 5. Fresh: an unusual subject pays; a tired one costs.
    if any(word in low for word in FRESH_SUBJECTS):
        points += 2.0
    for word in TIRED_SUBJECTS:
        if word in low:
            points -= 3.0
    for fmt in TIRED_FORMATS:
        if fmt in low:
            points -= 2.0
    # A format the field has met a hundred times costs freshness.
    if low.startswith("i asked my ") or "filed a complaint" in low:
        points -= 2.0
    return points


def pick_line(candidates):
    """Return the highest-scoring candidate.

    Primary key is the proxy score; ties go to the higher reader
    rubric, then to the earliest candidate. A proxy tie means the
    scorer cannot tell the lines apart, and the rubric is the reader
    the brief is written for.
    """
    best = None
    best_key = None
    for index, line in enumerate(candidates):
        key = (score_line(line), RUBRIC[index], -index)
        if best_key is None or key > best_key:
            best, best_key = line, key
    return best, best_key[0], best_key[1]


def gate_ok(line):
    """The sealed gate: UTF-8 text, 1-240 chars, not only whitespace."""
    if not line or not line.strip():
        return False
    if len(line) > MAX_CHARS:
        return False
    if "\n" in line or "\r" in line:
        return False
    try:
        line.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def main():
    line, points, rubric = pick_line(CANDIDATES)
    if not gate_ok(line):
        print("picked line fails the gate", file=sys.stderr)
        return 1
    target = os.environ.get("ENTRY_OUTPUT", OUTPUT_PATH)
    parent = os.path.dirname(target)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(line)
    # The grader collects outputs as another user: leave the file
    # readable by everyone.
    os.chmod(target, 0o644)
    print(f"wrote {len(line)} chars (proxy {points}, rubric "
          f"{rubric}/25) to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
