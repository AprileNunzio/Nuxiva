import sys
from pathlib import Path

import appearance
import selection

sys.path.append(str(Path(__file__).resolve().parents[1] / "biometrics"))
import face_engine

FEATURE_EVERY = 3
UNKNOWN = "Sconosciuto"


def _identify(vision, track, frame, face, ir_face) -> tuple:
    aligned = vision.recognizer.alignCrop(frame, face)
    feature = vision.recognizer.feature(aligned).flatten()
    track.feature = feature
    track.marks = face_engine.marks_of(aligned)
    track.ir_feature = vision.fusion.feature(ir_face) if ir_face else None
    verdict = vision.gallery.match_ex(feature, track.ir_feature, track.marks)
    track.votes.append((verdict["slug"], verdict["name"], verdict["score"]) if verdict["slug"]
                       else (None, UNKNOWN, verdict["score"]))
    track.ambiguous, track.possible = verdict["ambiguous"], verdict["names"]
    return track.box, feature, face, track.ir_feature


def _liveness(vision, track, face, ir_face, person, minimum: float, now: float) -> None:
    if vision.fusion.active:
        vision.fusion.assess(track, ir_face, vision.size, person, minimum)
        track.live_state = "unknown" if track.live_score is None or track.frames < 3 else (
            "live" if track.live_score >= minimum else "spoof")
        if ir_face and person is not None and track.live_state == "live":
            vision.fusion.learn_offset(track.box, vision.size, ir_face)
        return
    result = track.rgb_live.update([float(v) for v in face[4:14]], now, minimum)
    track.live_score, track.live_state = result.get("score"), result.get("state", "unknown")
    track.live_detail = result


def observe(vision, track, frame, face, now: float, minimum: float) -> tuple | None:
    need = len(track.votes) < 3 or track.frames % FEATURE_EVERY == 0 or vision.enroll_request is not None
    ir_face = vision.fusion.pair(track.box, vision.size) if vision.fusion.active else None
    detection = _identify(vision, track, frame, face, ir_face) if need else None
    slug_now = track.identity()[0]
    track.affect = track.meter.update(frame, face, now) if slug_now and track.facing and selection.affect_enabled() else None
    appearance.observe(track, frame)
    person = vision.gallery.people.get(slug_now) if slug_now else None
    if selection.liveness_mode() != "off":
        _liveness(vision, track, face, ir_face, person, minimum, now)
    return detection
