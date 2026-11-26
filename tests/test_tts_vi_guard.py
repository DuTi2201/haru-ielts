"""The Vietnamese Chirp voice of the lectures: no comma before "và" in what it reads, and a take that runs
far longer than its text (the voice has spoken nonsense) is asked for again. Pure tests: no network."""
from app.services import google_tts, lecture_voice, tts


def test_comma_before_va_is_dropped_only_there():
    assert tts.vi_speakable("Người viết đổi cách gọi, và người đọc phải tự nối lại.") == \
        "Người viết đổi cách gọi và người đọc phải tự nối lại."
    assert tts.vi_speakable("tên câu lạc bộ,và các con số") == "tên câu lạc bộ và các con số"
    assert tts.vi_speakable("Mốc đầu, Và rồi") == "Mốc đầu Và rồi"
    # other commas, and words that only begin with "và", are left alone
    assert tts.vi_speakable("Bước một, đọc lại; hai, vào bài, vàng") == "Bước một, đọc lại; hai, vào bài, vàng"


def test_a_take_is_too_long_only_when_far_beyond_its_text():
    sound = [("Người viết đổi cách gọi và người đọc phải tự nối lại.", 3.9),
             ("Đó chính là công nghệ mới vừa nhắc ở câu trước. Người viết đổi cách gọi và người đọc phải tự nối lại.", 7.1),
             ("Hết buổi từ thứ hai. Tiếp theo là cách đọc những câu dài nhất của bài và cách theo mạch thông tin từ đoạn này sang đoạn khác.", 6.3),
             ("là sơ khai,", 1.4)]
    garbled = [("Đó chính là công nghệ mới vừa nhắc ở câu trước. Người viết đổi cách gọi, và người đọc phải tự nối lại.", 13.6),
               ("Hết buổi từ thứ hai. Tiếp theo là cách đọc những câu dài nhất của bài, và cách theo mạch thông tin từ đoạn này sang đoạn khác.", 15.7),
               ("là phát triển thành, và", 5.9)]
    for text, sec in sound:
        assert not tts.vi_take_too_long(text, sec, 0.95), text
    for text, sec in garbled:
        assert tts.vi_take_too_long(text, sec, 0.95), text
    # a word or two is not checked: Chirp pads short takes (measured "là" at 1.5 s)
    assert not tts.vi_take_too_long("là", 1.5, 0.95) and not tts.vi_take_too_long("thì chữ", 1.8, 0.95)


def _pcm(seconds: float, rate: int = 24000) -> bytes:
    return b"\0\0" * int(seconds * rate)


def test_the_vietnamese_voice_reads_the_safe_text_and_a_long_take_is_redone(monkeypatch):
    heard: list[str] = []
    lengths = iter([20.0, 6.0])  # first take garbled, second sound

    def fake(text, client=None, voice=None, rate=1.0):
        heard.append(text)
        return _pcm(next(lengths)), 24000

    monkeypatch.setattr(google_tts, "synthesize_pcm", fake)
    one = tts._lecture_request(lecture_voice.VI, {lecture_voice.VI: "vi-x", lecture_voice.KO: "en-x"})
    pcm, rate = one("Đó chính là công nghệ mới vừa nhắc ở câu trước. Người viết đổi cách gọi, và người đọc phải tự nối lại.")
    assert heard == ["Đó chính là công nghệ mới vừa nhắc ở câu trước. Người viết đổi cách gọi và người đọc phải tự nối lại."] * 2
    assert len(pcm) == len(_pcm(6.0)) and rate == 24000


def test_the_shortest_take_is_kept_when_every_take_is_long(monkeypatch):
    lengths = iter([20.0, 15.0, 18.0])
    monkeypatch.setattr(google_tts, "synthesize_pcm", lambda text, client=None, voice=None, rate=1.0: (_pcm(next(lengths)), 24000))
    one = tts._lecture_request(lecture_voice.VI, {lecture_voice.VI: "vi-x", lecture_voice.KO: "en-x"})
    pcm, _ = one("là phát triển thành, và")
    assert len(pcm) == len(_pcm(15.0))


def test_the_english_voice_is_left_as_it_is(monkeypatch):
    heard: list[str] = []

    def fake(text, client=None, voice=None, rate=1.0):
        heard.append(text)
        return _pcm(30.0), 24000

    monkeypatch.setattr(google_tts, "synthesize_pcm", fake)
    one = tts._lecture_request(lecture_voice.KO, {lecture_voice.VI: "vi-x", lecture_voice.KO: "en-x"})
    one("Steam, and power.")
    assert heard == ["Steam, and power."]
