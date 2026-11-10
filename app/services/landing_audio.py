"""The home page's Korean lines (the three cards and the four skill demos) are heard by every
visitor, signed in or not. Their recordings are made ONCE (Chirp, like any other text:
services/text_audio) and then only read back: a visitor never causes a Google call. Only these
texts are voiced here, so this public door cannot be used to turn arbitrary text into paid speech.

Keep LANDING_TEXTS in step with the app: DEMO_CARDS (src/components/site/LandingKit.tsx) and
DEMO_SPOKEN (src/components/site/SkillDemos.tsx). A line that is not here plays with the device's
own voice."""
from __future__ import annotations

LANDING_TEXTS: tuple[str, ...] = (
    "consistently",
    "sustainable development",
    "Every journey begins with a single step.",
    "What did you do yesterday evening?",
    "Oh, you met a friend? Where did you meet?",
    "Great! What did you drink at the cafe?",
    "met a friend",
    "What do you usually do on weekends? Give reasons and examples.",
    "On weekends, I usually exercise because I am too busy during the week. For example, last Saturday I ran in the park with a friend for an hour. Exercising helps me relieve stress and feel refreshed.",
    "Companies should allow more remote work.",
    "Working remotely makes it harder to communicate with colleagues, and teamwork may weaken.",
    "That is a fair point. However, who will train new employees if everyone works from home?",
    "It can be challenging at first, of course, but a structured mentoring programme can help new staff learn effectively.",
    "Public transport is widely available.",
)
VOICE = "en-female-1"
