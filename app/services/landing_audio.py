"""The home page's Korean lines (the three cards and the four skill demos) are heard by every
visitor, signed in or not. Their recordings are made ONCE (Chirp, like any other text:
services/text_audio) and then only read back: a visitor never causes a Google call. Only these
texts are voiced here, so this public door cannot be used to turn arbitrary text into paid speech.

Keep LANDING_TEXTS in step with the app: DEMO_CARDS (src/components/site/LandingKit.tsx) and
DEMO_SPOKEN (src/components/site/SkillDemos.tsx). A line that is not here plays with the device's
own voice."""
from __future__ import annotations

LANDING_TEXTS: tuple[str, ...] = (
    "꾸준히",
    "일석이조",
    "천 리 길도 한 걸음부터",
    "어제 저녁에 뭐 했어요?",
    "아, 친구를 만났어요? 어디에서 만났어요?",
    "좋아요! 카페에서 뭐 마셨어요?",
    "만났어요",
    "주말에 보통 무엇을 해요? 이유와 예를 들어 말해 보세요.",
    "저는 주말에 보통 운동을 해요. 왜냐하면 평일에는 너무 바빠서 운동할 시간이 없기 때문이에요. 예를 들어 지난 토요일에는 친구와 공원에서 한 시간 동안 뛰었어요. 운동을 하면 스트레스가 풀리고 기분이 좋아져요.",
    "회사는 재택근무를 늘려야 한다.",
    "재택근무를 하면 동료와 소통하기 어려워요. 팀워크가 약해질 수 있어요.",
    "좋은 지적이에요. 그 부분은 인정해요. 하지만 신입 사원은 누구한테 일을 배워요?",
    "물론 처음에는 어려울 수 있어요. 하지만 멘토 제도를 만들면 신입 사원도 잘 배울 수 있어요.",
    "이용하실 수 있습니다",
)
VOICE = "ko-female-1"
