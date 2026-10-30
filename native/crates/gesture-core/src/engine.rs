use crate::duo::{self, DuoAccumulator, DuoPose};
use crate::events::{DuoPhase, GestureEvent};
use crate::gesture::GestureKind;
use crate::landmarks::{Frame, Hand, Handedness};
use crate::motion::MotionTracker;
use crate::pointer::{PinchEdge, PointerTracker};
use crate::pose::{self, Pose};
use crate::profile::{ANY_CONTEXT, Binding, GestureProfile};
use crate::smoothing::HandSmoother;

const TRACKED_HANDS: usize = 2;

#[derive(Debug, Clone, PartialEq, Default)]
struct HandSlot {
    key: (Handedness, usize),
    smoother: HandSmoother,
    motion: MotionTracker,
    pinch: bool,
    pose: Option<Pose>,
    last_seen: u64,
}

#[derive(Debug, Clone, PartialEq)]
struct Observed {
    slot: usize,
    hand: Hand,
    smooth: Hand,
    ratio: f32,
    pose: Pose,
    confidence: f32,
}

#[derive(Debug, Clone, PartialEq, Default)]
pub struct GestureEngine {
    profile: GestureProfile,
    slots: Vec<HandSlot>,
    pointer: PointerTracker,
    duo: Option<DuoPose>,
    accumulator: DuoAccumulator,
    last_ms: u64,
}

fn specificity(binding: &Binding) -> u8 {
    (u8::from(binding.context != ANY_CONTEXT) << 1) | u8::from(binding.modifier.is_some())
}

impl GestureEngine {
    #[must_use]
    pub fn new(profile: GestureProfile) -> Self {
        Self {
            profile,
            ..Self::default()
        }
    }

    #[must_use]
    pub const fn profile(&self) -> &GestureProfile {
        &self.profile
    }

    pub fn set_profile(&mut self, profile: GestureProfile) {
        *self = Self::new(profile);
    }

    fn slot_for(&mut self, key: (Handedness, usize), now: u64) -> usize {
        if let Some(index) = self.slots.iter().position(|s| s.key == key) {
            return index;
        }
        self.slots.push(HandSlot {
            key,
            last_seen: now,
            ..HandSlot::default()
        });
        self.slots.len().saturating_sub(1)
    }

    fn observe(&mut self, frame: &Frame, now: u64) -> Vec<Observed> {
        let lost = u64::from(self.profile.lost_ms);
        self.slots
            .retain(|s| now.saturating_sub(s.last_seen) <= lost);
        let mut hands: Vec<&Hand> = frame.hands.iter().collect();
        hands.sort_by(|a, b| b.score.total_cmp(&a.score));
        hands.truncate(TRACKED_HANDS);
        let mut seen_kinds: Vec<Handedness> = Vec::new();
        let config = self.profile.one_euro();
        let (on, off) = (self.profile.pinch_on, self.profile.pinch_off);
        let mut observed = Vec::new();
        for raw in hands {
            let ordinal = seen_kinds.iter().filter(|h| **h == raw.handedness).count();
            seen_kinds.push(raw.handedness);
            let source = if self.profile.mirror {
                raw.mirrored()
            } else {
                raw.clone()
            };
            let index = self.slot_for((raw.handedness, ordinal), now);
            let Some(slot) = self.slots.get_mut(index) else {
                continue;
            };
            let smooth = slot.smoother.smooth(&source, now, config);
            let ratio = pose::effective_pinch_ratio(&source);
            slot.pinch = if slot.pinch { ratio <= off } else { ratio < on };
            slot.last_seen = now;
            let (pose, confidence) = pose::classify(&source, slot.pinch);
            slot.pose = Some(pose);
            observed.push(Observed {
                slot: index,
                hand: source,
                smooth,
                ratio,
                pose,
                confidence,
            });
        }
        observed
    }

    fn bind(
        &self,
        gesture: GestureKind,
        hand: Handedness,
        modifier: Option<Pose>,
        context: &str,
    ) -> Option<GestureEvent> {
        self.profile
            .bindings
            .iter()
            .filter(|b| b.enabled && b.gesture == gesture)
            .filter(|b| b.hand.accepts(hand, self.profile.dominant))
            .filter(|b| b.context == ANY_CONTEXT || b.context == context)
            .filter(|b| b.modifier.is_none() || b.modifier == modifier)
            .max_by_key(|b| specificity(b))
            .map(|b| GestureEvent::Action {
                action: b.action.clone(),
                args: b.args.clone(),
                gesture,
                hand,
                confirm: b.confirm,
            })
    }

    fn announce(
        &self,
        gesture: GestureKind,
        hand: Handedness,
        confidence: f32,
        modifier: Option<Pose>,
        context: &str,
        out: &mut Vec<GestureEvent>,
    ) {
        out.push(GestureEvent::Gesture {
            gesture,
            hand,
            confidence,
            modifier,
        });
        out.extend(self.bind(gesture, hand, modifier, context));
    }

    fn duo_event(&self, phase: DuoPhase, pose: DuoPose, step: duo::DuoDelta) -> GestureEvent {
        let at = PointerTracker::to_screen(&self.profile, pose.mid);
        GestureEvent::Duo {
            phase,
            x: at.x,
            y: at.y,
            scale: step.scale,
            rotate: step.rotate,
            pan_x: step.pan.x,
            pan_y: step.pan.y,
        }
    }

    fn end_duo(&mut self, out: &mut Vec<GestureEvent>) {
        if let Some(last) = self.duo.take() {
            out.push(self.duo_event(DuoPhase::End, last, duo::DuoDelta::IDLE));
            self.pointer.lock_after_duo();
        }
    }

    fn run_duo(&mut self, hands: &[Observed], context: &str, out: &mut Vec<GestureEvent>) {
        let pinching = |o: &Observed| self.slots.get(o.slot).is_some_and(|s| s.pinch);
        let [a, b] = hands else {
            self.end_duo(out);
            return;
        };
        if !(pinching(a) && pinching(b)) {
            self.end_duo(out);
            return;
        }
        let current = duo::pair(&a.hand, &b.hand);
        let Some(last) = self.duo else {
            out.extend(self.pointer.release(&self.profile));
            self.duo = Some(current);
            self.accumulator.start();
            out.push(self.duo_event(DuoPhase::Start, current, duo::DuoDelta::IDLE));
            return;
        };
        let tuning = self.profile.duo;
        let next = duo::blend(Some(last), current, tuning.smooth);
        let step = duo::delta(Some(last), next, &tuning);
        self.duo = Some(next);
        out.push(self.duo_event(DuoPhase::Update, next, step));
        if let Some(motion) = self.accumulator.push(step, &tuning) {
            self.announce(
                GestureKind::Duo(motion),
                Handedness::Unknown,
                1.0,
                None,
                context,
                out,
            );
        }
    }

    fn primary(&self, hands: &[Observed]) -> Option<usize> {
        hands
            .iter()
            .position(|o| o.hand.handedness == self.profile.dominant)
            .or(if hands.is_empty() { None } else { Some(0) })
    }

    pub fn feed(&mut self, frame: &Frame, context: &str) -> Vec<GestureEvent> {
        let now = frame.timestamp_ms.max(self.last_ms);
        self.last_ms = now;
        let hands = self.observe(frame, now);
        let mut out = Vec::new();
        if hands.is_empty() {
            out.extend(self.pointer.lost(now, &self.profile));
            if now.saturating_sub(self.slots.iter().map(|s| s.last_seen).max().unwrap_or(0))
                > u64::from(self.profile.lost_ms)
            {
                self.end_duo(&mut out);
            }
            return out;
        }
        self.run_duo(&hands, context, &mut out);
        let primary = self.primary(&hands);
        let tuning = self.profile.motion;
        for (position, seen) in hands.iter().enumerate() {
            let modifier = hands
                .iter()
                .enumerate()
                .find(|(p, o)| *p != position && !matches!(o.pose, Pose::Unknown | Pose::Pinch))
                .map(|(_, o)| o.pose);
            let mut found = Vec::new();
            if Some(position) == primary && self.profile.pointer {
                let (events, edge) = self.pointer.track(
                    &seen.hand,
                    seen.ratio,
                    now,
                    self.duo.is_some(),
                    &self.profile,
                );
                out.extend(events);
                if let Some(slot) = self.slots.get_mut(seen.slot) {
                    let at = seen.smooth.palm_center();
                    found.extend(edge.and_then(|e| {
                        slot.motion
                            .pinch_edge(now, e == PinchEdge::Pressed, at, &tuning)
                    }));
                }
            }
            if self.duo.is_none() {
                if let Some(slot) = self.slots.get_mut(seen.slot) {
                    found.extend(slot.motion.update(
                        now,
                        seen.smooth.palm_center(),
                        seen.pose,
                        &tuning,
                    ));
                }
            }
            for gesture in found {
                self.announce(
                    gesture,
                    seen.hand.handedness,
                    seen.confidence,
                    modifier,
                    context,
                    &mut out,
                );
            }
        }
        out
    }
}
