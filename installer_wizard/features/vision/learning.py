import logging
import os
import time
from pathlib import Path

import numpy as np

import selection

log = logging.getLogger("nuxiva.vision")
AUTO_ENROLL = os.environ.get("NUXIVA_AUTO_ENROLL", "1") != "0"
AUTO_MIN_SECONDS = 2.5
AUTO_MIN_RATIO = 0.09
AUTO_SAMPLES = 8
MERGE_THRESHOLD = 0.30
GUEST_GUARD = 0.10
LEARN_UNTIL = 25
LEARN_EVERY = 1.5
REFINE_EVERY = 60.0
VIEW_EVERY = 4.0
VIEW_MIN_SCORE = 0.55
MERGE_CENTROID = float(os.environ.get("NUXIVA_FACE_MERGE_CENTROID", "0.45"))
REFINE = os.environ.get("NUXIVA_FACE_AUTOIMPROVE", "1") != "0"
SETUP_SESSION = Path(os.environ.get("NUXIVA_SETUP_SESSION", "/var/lib/nuxiva/setup_session.json"))


def setup_running() -> bool:
    return SETUP_SESSION.exists()


def collect_view(vision, track, frame, slug, score, now) -> None:
    views = getattr(vision, "views", None)
    if views is None or track.face is None or score < VIEW_MIN_SCORE or now - track.last_view < VIEW_EVERY:
        return
    track.last_view = now
    views.auto(slug, frame, track.face)


def learn(vision, track, frame, feature) -> None:
    if not AUTO_ENROLL or vision.enroll_request is not None or track.echo_of or track.ambiguous:
        return
    if selection.liveness_mode() != "off" and (track.live_state == "spoof"
                                               or (vision.fusion.active and track.live_state != "live")):
        return
    now = time.time()
    slug, name, score = track.identity()
    ratio = track.box[2] / (vision.size[0] or 640)
    ir = [track.ir_feature] if track.ir_feature is not None else None
    if slug:
        collect_view(vision, track, frame, slug, score, now)
        person = vision.gallery.people.get(slug, {})
        young = person.get("samples", 40) < LEARN_UNTIL
        wait = LEARN_EVERY if young else REFINE_EVERY
        if (young or REFINE) and score > 0.5 and track.facing and now - track.last_learn > wait \
                and vision.gallery.may_learn(slug, feature, track.ir_feature):
            track.last_learn = now
            vision.gallery.add_samples(slug, [feature], ir, [track.marks] if track.marks is not None else None)
        return
    if setup_running() or ratio < AUTO_MIN_RATIO:
        return
    track.samples.append(feature)
    if track.ir_feature is not None:
        track.ir_samples.append(track.ir_feature)
    if track.marks is not None:
        track.mark_samples.append(track.marks)
    if now - track.first_seen < AUTO_MIN_SECONDS or len(track.samples) < AUTO_SAMPLES:
        return
    mean = np.mean([s / np.linalg.norm(s) for s in track.samples], axis=0)
    near_slug, near_score = vision.gallery.closest(mean)
    centroid = vision.gallery.centroid_score(near_slug, mean) if near_slug else None
    centroid_ok = centroid is not None and centroid >= MERGE_CENTROID
    near_named = near_slug is not None and not vision.gallery.people.get(near_slug, {}).get("auto") \
        and near_score >= vision.gallery.people.get(near_slug, {}).get("threshold", MERGE_THRESHOLD) - GUEST_GUARD
    if near_slug and near_score >= MERGE_THRESHOLD and centroid_ok:
        vision.gallery.add_samples(near_slug, track.samples, track.ir_samples or None, track.mark_samples or None)
        log.info("Campioni aggiunti a %s (somiglianza %.2f)", near_slug, near_score)
    elif near_named or track.possible:
        log.info("Volto vicino a %s (%.2f): nessun nuovo ospite per non creare un doppione", near_slug, near_score)
    else:
        guest = vision.gallery.next_guest_name()
        person = vision.gallery.save(guest, track.samples, vision._crop(frame, track.box), auto=True,
                                   slug=f"ospite-{int(now)}", ir=track.ir_samples or None, marks=track.mark_samples or None)
        log.info("Nuova persona registrata automaticamente: %s", person["name"])
    track.samples, track.ir_samples, track.mark_samples = [], [], []
    track.votes.clear()

