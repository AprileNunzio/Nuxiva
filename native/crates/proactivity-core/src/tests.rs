mod basics;
mod learning;
mod prediction;
mod privacy;
mod validation;

use crate::{Context, Engine, Ruleset, Settings, Signal, Situation};

pub const DAY: u64 = 1_699_920_000_000;
pub const HOUR: u64 = 3_600_000;
pub const MIN: u64 = 60_000;

pub const RULES: &str = r#"{"rules":{
"meeting_soon":{"domain":"calendar","trigger":{"domain":"calendar","key":"event_in_minutes","cmp":"le","threshold":15},
 "audience":"subject","privacy":"household","urgency":"normal","level":"propose","base_confidence":800,"min_confidence":500,"value":900,
 "summary_key":"proactive.meeting_soon",
 "action":{"kind":"calendar.prepare","class":"interactive","priority":5,"budget":{"wall_ms":30000,"tokens":2000,"tool_calls":4,"cpu_ms":5000},"risk_max":"low","input_template":"event:{subject}"}},
"weak_hint":{"domain":"home","trigger":{"domain":"home","key":"hint","cmp":"present"},
 "audience":"household","privacy":"public","urgency":"normal","level":"propose","base_confidence":300,"min_confidence":600,"value":900,
 "summary_key":"proactive.weak_hint",
 "action":{"kind":"home.note","class":"background","priority":3,"budget":{"wall_ms":10000,"tokens":0,"tool_calls":1,"cpu_ms":1000},"risk_max":"none","input_template":"{subject}"}},
"heart_alert":{"domain":"health","trigger":{"domain":"health","key":"heart_rate","cmp":"ge","threshold":140},
 "audience":"subject","privacy":"private","urgency":"normal","level":"propose","base_confidence":900,"min_confidence":600,"value":1000,
 "summary_key":"proactive.heart_alert",
 "action":{"kind":"health.check","class":"interactive","priority":8,"budget":{"wall_ms":20000,"tokens":1000,"tool_calls":2,"cpu_ms":3000},"risk_max":"low","input_template":"person:{subject}"}},
"intruder":{"domain":"security","trigger":{"domain":"security","key":"intrusion","cmp":"ge","threshold":1},
 "audience":"household","privacy":"household","urgency":"critical","level":"propose","base_confidence":950,"min_confidence":700,"value":1000,
 "summary_key":"proactive.intruder",
 "action":{"kind":"security.alert","class":"voice","priority":10,"budget":{"wall_ms":15000,"tokens":500,"tool_calls":2,"cpu_ms":2000},"risk_max":"low","input_template":"zone:{subject}"}},
"window_open":{"domain":"home","trigger":{"domain":"home","key":"window_open","cmp":"ge","threshold":1},
 "when":[{"domain":"presence","key":"home","cmp":"le","threshold":0}],
 "audience":"household","privacy":"household","urgency":"normal","level":"notify","base_confidence":850,"min_confidence":500,"value":700,
 "summary_key":"proactive.window_open",
 "action":{"kind":"home.note","class":"background","priority":4,"budget":{"wall_ms":10000,"tokens":0,"tool_calls":1,"cpu_ms":1000},"risk_max":"none","input_template":"window:{subject}"}},
"lights":{"domain":"home","trigger":{"domain":"home","key":"dusk","cmp":"ge","threshold":1},
 "when":[{"domain":"presence","key":"home","cmp":"ge","threshold":1,"same_person":true}],
 "window":{"start_min":1020,"end_min":1380},
 "audience":"subject","privacy":"household","urgency":"normal","level":"do_and_tell","base_confidence":900,"min_confidence":500,"value":900,
 "summary_key":"proactive.lights",
 "action":{"kind":"lights.on","class":"background","priority":4,"budget":{"wall_ms":10000,"tokens":0,"tool_calls":1,"cpu_ms":1000},"risk_max":"low","input_template":"room:{subject}",
  "undo":{"kind":"lights.off","input_template":"room:{subject}","window_ms":600000}}},
"briefing":{"domain":"schedule","trigger":{"domain":"schedule","key":"wake","cmp":"present"},
 "window":{"start_min":330,"end_min":600},
 "audience":"subject","privacy":"household","urgency":"normal","level":"propose","base_confidence":800,"min_confidence":500,"value":900,
 "summary_key":"proactive.briefing","habit":{"lead_ms":600000,"min_days":3,"min_permille":600},
 "action":{"kind":"briefing.compose","class":"interactive","priority":5,"budget":{"wall_ms":30000,"tokens":2000,"tool_calls":3,"cpu_ms":4000},"risk_max":"low","input_template":"person:{subject}"}},
"mail_important":{"domain":"email","trigger":{"domain":"email","key":"important","cmp":"ge","threshold":800},
 "audience":"subject","privacy":"private","urgency":"normal","level":"propose","base_confidence":800,"min_confidence":500,"value":800,
 "summary_key":"proactive.mail_important",
 "action":{"kind":"email.summarize","class":"interactive","priority":5,"budget":{"wall_ms":30000,"tokens":3000,"tool_calls":3,"cpu_ms":4000},"risk_max":"medium","input_template":"mail:{subject}"}}
}}"#;

pub fn engine() -> Engine {
    Engine::new(
        Settings::default(),
        Ruleset::from_json(RULES).expect("rules"),
    )
    .expect("engine")
}

pub fn ctx(situation: Situation, present: &[&str], guests: bool, voice: bool) -> Context {
    Context {
        situation,
        voice_free: voice,
        guests_present: guests,
        present: present.iter().map(|p| (*p).to_owned()).collect(),
        tz_offset_min: 0,
    }
}

pub fn idle(present: &[&str]) -> Context {
    ctx(Situation::Idle, present, false, false)
}

pub fn sig(
    domain: &str,
    key: &str,
    person: Option<&str>,
    subject: &str,
    value: i32,
    at: u64,
) -> Signal {
    let person = person.map_or_else(|| "null".to_owned(), |p| format!("\"{p}\""));
    let text = format!(
        r#"{{"domain":"{domain}","key":"{key}","person":{person},"subject":"{subject}","value":{value},"at":{at}}}"#
    );
    Engine::signal_from_json(&text).expect("signal")
}
