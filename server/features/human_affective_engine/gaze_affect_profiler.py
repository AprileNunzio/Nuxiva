from typing import List, Dict, Any
from server.features.human_affective_engine.interfaces import OcularGazeBiomarkers

class GazeAffectProfiler:
    def __init__(self):
        pass

    def evaluate_gaze_sequence(
        self,
        directions: List[str],
        blinks: List[float],
        eye_aspect_ratios: List[float]
    ) -> OcularGazeBiomarkers:
        if not directions:
            return self._default_metrics()

        downward_count = sum(1 for d in directions if d in ["down", "bottom", "basso"])
        downward_ratio = float(downward_count / float(len(directions)))

        ear_mean = float(sum(eye_aspect_ratios) / len(eye_aspect_ratios)) if eye_aspect_ratios else 0.28
        blink_rate = float(len(blinks) * 12.0)

        center_count = sum(1 for d in directions if d in ["center", "centro"])
        fixation_stagnation = float(center_count / float(len(directions))) if len(directions) > 15 else 0.5

        blunted_score = (
            (downward_ratio * 0.5) +
            (max(0.0, 0.30 - ear_mean) * 2.5 * 0.3) +
            (min(1.0, abs(blink_rate - 15.0) / 15.0) * 0.2)
        )

        return OcularGazeBiomarkers(
            gaze_direction=directions[-1] if directions else "center",
            downward_gaze_ratio=downward_ratio,
            blink_rate_per_min=blink_rate,
            eye_aspect_ratio_mean=ear_mean,
            fixation_stagnation_score=fixation_stagnation,
            blunted_affect_indicator=float(min(1.0, max(0.0, blunted_score)))
        )

    def _default_metrics(self) -> OcularGazeBiomarkers:
        return OcularGazeBiomarkers(
            gaze_direction="center",
            downward_gaze_ratio=0.1,
            blink_rate_per_min=16.0,
            eye_aspect_ratio_mean=0.30,
            fixation_stagnation_score=0.4,
            blunted_affect_indicator=0.12
        )

gaze_affect_profiler = GazeAffectProfiler()
