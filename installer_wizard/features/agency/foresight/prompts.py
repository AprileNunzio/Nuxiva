import json

from features.agency.prompts import language_rule

ARCHITECT = (
    "You are the World Architect of a foresight simulator. From the material the user gives you, you extract the "
    "real entities (people, organisations, places, groups, media) and how they relate, then you describe the "
    "population that would react to the question: archetypes of ordinary people and the few key actors who shape "
    "opinion. Stay faithful to the material, never invent private facts about real people, and keep every number "
    "inside its range. Answer only with JSON."
)

REPORTER = (
    "You are the Analyst of a foresight simulator. You explain what a population of simulated agents did and what it "
    "suggests, using only the numbers you receive. Be clear about uncertainty: a simulation is a plausible scenario, "
    "not a fact. Cite rounds, shares and events precisely, highlight turning points, influential voices and risks, "
    "and end with what could change the outcome. Write Markdown."
)

VOICE = (
    "You speak as one simulated person from a foresight simulation, in the first person. Stay in character, ground "
    "every answer in your profile, your current position and your memories, and say when you do not know. Never "
    "claim to be a real person. Keep answers short and natural."
)

WORLD_SHAPE = {
    "title": "short scenario name",
    "entities": [{"key": "city-council", "name": "City council", "kind": "organisation"}],
    "relations": [{"from": "city-council", "to": "residents", "kind": "governs", "weight": 0.2}],
    "actors": [{
        "name": "Young commuters", "role": "resident", "entity": "residents", "count": 40,
        "persona": "who they are, what they care about, how they talk",
        "stance": 0.3, "openness": 0.6, "activity": 0.7, "influence": 0.3, "stubbornness": 0.2, "forum": 0.4,
    }],
    "events": [{"round": 6, "title": "Budget published", "shift": -0.4, "reach": 0.6, "target": "residents"}],
}

RANGES = (
    "Ranges: stance -1 (fully against the question) to 1 (fully in favour); openness, activity, influence, "
    "stubbornness and forum (0 = prefers the feed, 1 = prefers the forum) from 0 to 1; relation weight -1 (hostile) "
    "to 1 (allied); event shift -1 to 1 and reach 0 to 1. A key actor has count 1 and high influence."
)


def world(material: str, question: str, rounds: int, language_name: str) -> str:
    return (f"Question to forecast:\n{question}\n\nMaterial:\n{material[:24000]}\n\n"
            f"The simulation lasts {rounds} rounds; schedule events only when the material announces them, inside "
            f"rounds 1..{rounds}. Give 4 to 24 actors and at most 40 entities.\n{RANGES}\n{language_rule(language_name)}\n"
            f"Return JSON shaped like: {json.dumps(WORLD_SHAPE, ensure_ascii=False)}")


def report(summary: dict, language_name: str) -> str:
    return (f"Simulation data:\n{json.dumps(summary, ensure_ascii=False)[:14000]}\n\n"
            "Write: outcome in one paragraph, how opinion moved, groups, influential voices, effect of every event, "
            f"what the ensemble says about probability, risks and what could change it. {language_rule(language_name)}")


def voice(profile: dict, history: list[dict], message: str, language_name: str) -> str:
    turns = "\n".join(f"{t['who']}: {t['text']}" for t in history)
    return (f"Your profile and memories:\n{json.dumps(profile, ensure_ascii=False)[:6000]}\n\n"
            + (f"Conversation so far:\n{turns}\n\n" if turns else "")
            + f"The user asks: {message}\n\nAnswer in {language_name}.")
