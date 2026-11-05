use crate::policy::Policy;
use crate::signal::{Face, Liveness, MAX_FACES, MAX_VOICES, Signals, Vision, Voice};
use nuxiva_display_domain::AudienceKind;
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Proof {
    Single,
    Strong,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Member {
    pub person: String,
    pub proof: Proof,
    pub near: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Reading {
    pub kind: AudienceKind,
    pub members: Vec<Member>,
    pub guests: u16,
    pub unverified: u16,
    pub seen: bool,
    pub voiced: bool,
}

impl Reading {
    const fn bare(kind: AudienceKind) -> Self {
        Self {
            kind,
            members: Vec::new(),
            guests: 0,
            unverified: 0,
            seen: false,
            voiced: false,
        }
    }
}

enum Verdict {
    Guest,
    Unverified,
    Member(String, Proof),
}

fn fresh(voice: &Voice, policy: &Policy, now_ms: u64) -> bool {
    voice.at_ms <= now_ms.saturating_add(policy.skew_ms)
        && now_ms.saturating_sub(voice.at_ms) < policy.agree_ms
}

#[must_use]
pub fn utterances(voices: &[Voice], policy: &Policy, now_ms: u64) -> BTreeMap<String, u64> {
    let mut out = BTreeMap::new();
    for voice in voices.iter().take(MAX_VOICES) {
        if !(voice.authorized && voice.score >= policy.voice_min && fresh(voice, policy, now_ms)) {
            continue;
        }
        let Some(person) = voice.person.as_deref().filter(|p| !p.is_empty()) else {
            continue;
        };
        let at = voice.at_ms.min(now_ms);
        out.entry(person.to_owned())
            .and_modify(|last: &mut u64| *last = (*last).max(at))
            .or_insert(at);
    }
    out
}

fn claimant(face: &Face) -> Option<&str> {
    face.person
        .as_deref()
        .filter(|p| !p.is_empty() && face.authorized && face.liveness != Liveness::Spoof)
}

#[must_use]
pub fn recognised<'a>(face: &'a Face, policy: &Policy) -> Option<&'a str> {
    claimant(face).filter(|_| !face.confidence.is_nan() && face.confidence >= policy.face_min)
}

fn judge(
    face: &Face,
    policy: &Policy,
    spoken: &BTreeSet<String>,
    held: &BTreeSet<String>,
) -> Verdict {
    if claimant(face).is_none() {
        return Verdict::Guest;
    }
    let Some(person) = recognised(face, policy) else {
        return Verdict::Unverified;
    };
    let voiced = spoken.contains(person);
    let live = face.liveness == Liveness::Live;
    match (live, voiced) {
        (true, true) => Verdict::Member(person.to_owned(), Proof::Strong),
        (false, false) if policy.require_liveness && !held.contains(person) => Verdict::Unverified,
        _ => Verdict::Member(person.to_owned(), Proof::Single),
    }
}

const fn classify(members: bool, guests: u16, unverified: u16) -> AudienceKind {
    match (members, guests, unverified) {
        (false, 0, 0) => AudienceKind::Empty,
        (false, _, 0) => AudienceKind::GuestOnly,
        (false, _, _) => AudienceKind::Uncertain,
        (true, 0, 0) => AudienceKind::Authorized,
        (true, _, _) => AudienceKind::Mixed,
    }
}

#[must_use]
pub fn fuse(signals: &Signals, policy: &Policy, now_ms: u64) -> Reading {
    fuse_held(signals, policy, now_ms, &BTreeSet::new())
}

#[must_use]
pub fn fuse_held(
    signals: &Signals,
    policy: &Policy,
    now_ms: u64,
    held: &BTreeSet<String>,
) -> Reading {
    match signals.vision {
        Vision::Offline => return Reading::bare(AudienceKind::Uncertain),
        Vision::Disabled => return Reading::bare(AudienceKind::Authorized),
        Vision::Ok => {}
    }
    let spoken: BTreeSet<String> = utterances(&signals.voices, policy, now_ms)
        .into_keys()
        .collect();
    let mut members: BTreeMap<String, Member> = BTreeMap::new();
    let (mut guests, mut unverified) = (0_u16, 0_u16);
    let faces = signals.faces.iter().take(MAX_FACES);
    let seen = !signals.faces.is_empty();
    for face in faces {
        match judge(face, policy, &spoken, held) {
            Verdict::Guest => guests = guests.saturating_add(1),
            Verdict::Unverified => unverified = unverified.saturating_add(1),
            Verdict::Member(person, proof) => {
                let entry = members.entry(person.clone()).or_insert(Member {
                    person,
                    proof,
                    near: false,
                });
                entry.proof = entry.proof.max(proof);
                entry.near = entry.near || face.near;
            }
        }
    }
    for person in &spoken {
        members.entry(person.clone()).or_insert(Member {
            person: person.clone(),
            proof: Proof::Single,
            near: false,
        });
    }
    let kind = classify(!members.is_empty(), guests, unverified);
    Reading {
        kind,
        members: members.into_values().collect(),
        guests,
        unverified,
        seen,
        voiced: !spoken.is_empty(),
    }
}
