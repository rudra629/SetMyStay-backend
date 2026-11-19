"""Roommate profile questionnaire (20 questions, see "SetMyStay Roommate Profile Form").

The same spec lives in the frontend at src/lib/roommate-form.ts (generated from ROOMMATE_SPEC below,
keep both in step). Answers are stored on Property.roommate_details as short keys, e.g.
{"first_name": "Riya", "answers": {"sleep": "early", ...}, "importance": {"sleep": "very"}, "visible": {"sleep": true}}
"""
import re

ROOMMATE_SPEC = {
    "profile": {
        "gender": ["male", "female", "nonbinary"],
        "occupation": ["student", "professional", "freelancer"],
        "open_to": ["male", "female", "anyone"],
        "has_place": ["has_place", "looking"],
    },
    # question key -> allowed answers (order = scale order)
    "answers": {
        "sleep": ["early", "regular", "night"],
        "home_time": ["mostly_home", "mix", "mostly_out"],
        "drink": ["no", "occasionally_outside", "socially", "regularly_home"],
        "smoke": ["no", "outside", "balcony", "inside"],
        "weed": ["no", "rarely", "yes"],
        "ok_with": ["neither", "drinking_only", "both_outside", "dont_mind"],
        "clean": ["spotless", "tidy", "relaxed", "messy"],
        "chores": ["rota", "maid", "whenever", "cleaner"],
        "groceries": ["share_all", "share_basics", "separate"],
        "noise": ["quiet", "moderate", "loud"],
        "social": ["introvert", "ambivert", "extrovert"],
        "friends": ["never", "rarely", "monthly", "often", "daily"],
        "parents": ["never", "rarely", "monthly", "often"],
        "overnight": ["not_ok", "occasionally", "anytime"],
        "diet": ["jain_veg", "veg", "eggetarian", "non_veg"],
        "cooking": ["daily", "sometimes", "order_in"],
        "pets": ["have_pet", "love_pets", "neutral", "allergic"],
        "medical": ["no", "minor", "emergency"],
    },
    # Questions marked with a star: the user picks how much it matters and whether it shows on the profile.
    # "smoke" covers the weed answer too (same question on the form).
    "starred": ["sleep", "home_time", "drink", "smoke", "ok_with", "clean", "chores", "groceries", "noise",
                "social", "friends", "parents", "overnight", "diet", "cooking", "pets", "interests"],
    "importance": ["not_much", "somewhat", "very", "dealbreaker"],
    "interests": ["gym", "cricket", "football", "gaming", "movies", "music", "reading", "cooking", "travel",
                  "trekking", "partying", "spirituality", "coding", "art"],
    "languages": ["hindi", "english", "marathi", "gujarati", "tamil", "telugu", "kannada", "bengali",
                  "malayalam", "punjabi"],
    "prompts": ["best_roommate", "ideal_sunday", "house_rule", "particular_about", "kitchen", "green_flag",
                "pet_peeve", "long_day"],
}

PROFILE_LABELS = {
    "first_name": "First name", "age": "Age", "gender": "Gender", "occupation": "What you do",
    "open_to": "Open to living with", "has_place": "Place status",
}
ANSWER_LABELS = {
    "sleep": "Night person or day person", "home_time": "How much you are at home", "drink": "Drinking",
    "smoke": "Smoking", "weed": "Weed", "ok_with": "Okay with a roommate who drinks / smokes",
    "clean": "How clean you keep your space", "chores": "How chores should work",
    "groceries": "Groceries and bills", "noise": "Noise level", "social": "What kind of roommate you are",
    "friends": "How often friends visit", "parents": "How often parents visit",
    "overnight": "Overnight guests", "diet": "What you eat", "cooking": "Cooking and meals",
    "pets": "Pets", "medical": "Medical issue",
}

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _text(v, n):
    return str(v or "").strip()[:n]


def clean_roommate_details(raw):
    """Keep only known keys and allowed values. Returns (clean_dict, list_of_missing_required_labels)."""
    if not isinstance(raw, dict):
        raw = {}
    spec = ROOMMATE_SPEC
    out = {"v": 1}
    out["first_name"] = _text(raw.get("first_name"), 40)
    try:
        age = int(raw.get("age"))
        out["age"] = age if 18 <= age <= 99 else None
    except (TypeError, ValueError):
        out["age"] = None
    for k, allowed in spec["profile"].items():
        v = raw.get(k)
        out[k] = v if v in allowed else ""
    out["workplace"] = _text(raw.get("workplace"), 80)
    mv = _text(raw.get("move_in"), 10)
    out["move_in"] = mv if _DATE.match(mv) else ""

    answers_in = raw.get("answers") if isinstance(raw.get("answers"), dict) else {}
    out["answers"] = {k: (answers_in.get(k) if answers_in.get(k) in allowed else "")
                      for k, allowed in spec["answers"].items()}
    out["medical_note"] = _text(raw.get("medical_note"), 300)

    def pick(key):
        vals = raw.get(key) if isinstance(raw.get(key), list) else []
        return [v for v in dict.fromkeys(vals) if v in spec[key]]
    out["interests"] = pick("interests")
    out["languages"] = pick("languages")

    prompts = []
    for p in (raw.get("prompts") if isinstance(raw.get("prompts"), list) else []):
        if isinstance(p, dict) and p.get("q") in spec["prompts"] and _text(p.get("a"), 150):
            if p["q"] not in [x["q"] for x in prompts]:
                prompts.append({"q": p["q"], "a": _text(p.get("a"), 150)})
    out["prompts"] = prompts[:3]

    imp_in = raw.get("importance") if isinstance(raw.get("importance"), dict) else {}
    vis_in = raw.get("visible") if isinstance(raw.get("visible"), dict) else {}
    out["importance"] = {k: (imp_in.get(k) if imp_in.get(k) in spec["importance"] else "somewhat") for k in spec["starred"]}
    out["visible"] = {k: (vis_in.get(k) is not False) for k in spec["starred"]}

    missing = [PROFILE_LABELS[k] for k in ("first_name", "age", "gender", "occupation", "open_to", "has_place") if not out.get(k)]
    missing += [ANSWER_LABELS[k] for k, v in out["answers"].items() if not v]
    return out, missing


def public_roommate_details(d, can_see_private=False):
    """What other visitors see: answers the user marked visible. Medical details only after unlocking."""
    if not isinstance(d, dict) or not d:
        return {}
    vis = d.get("visible") or {}
    answers = dict(d.get("answers") or {})
    for k in list(answers.keys()):
        if k == "medical":
            continue
        key = "smoke" if k == "weed" else k
        if vis.get(key) is False:
            answers.pop(k, None)
    out = {k: d.get(k) for k in ("v", "first_name", "age", "gender", "occupation", "workplace", "open_to",
                                   "has_place", "move_in", "prompts")}
    out["languages"] = d.get("languages") or []
    out["interests"] = (d.get("interests") or []) if vis.get("interests") is not False else []
    if not can_see_private:
        answers.pop("medical", None)
    else:
        out["medical_note"] = d.get("medical_note") or ""
    out["answers"] = answers
    out["importance"] = {k: v for k, v in (d.get("importance") or {}).items() if vis.get(k) is not False}
    return out


def flatten_details(d):
    """{'answers': {'sleep': 'early'}} -> {'roommate.answers.sleep': 'early'} for change tracking."""
    flat = {}
    if not isinstance(d, dict):
        return flat
    for k, v in d.items():
        if k == "v":
            continue
        if isinstance(v, dict):
            for k2, v2 in v.items():
                flat[f"roommate.{k}.{k2}"] = v2
        elif isinstance(v, list):
            if k == "prompts":
                flat["roommate.prompts"] = " | ".join(f"{p.get('q')}: {p.get('a')}" for p in v if isinstance(p, dict))
            else:
                flat[f"roommate.{k}"] = ", ".join(str(x) for x in v)
        else:
            flat[f"roommate.{k}"] = v
    return flat
