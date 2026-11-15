#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};

use crate::acoustic::DeliveryStyle;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ReflexUtterance {
    pub text: String,
    pub language: String,
    pub delivery_style: DeliveryStyle,
    pub volume_scale: f32,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TaskDomain {
    ThinkingComplex,
    ActionDirect,
    SearchWeb,
    General,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct FillerEngine;

impl FillerEngine {
    fn hash_query(query: &str) -> usize {
        let mut h: u64 = 0xcbf2_9ce4_8422_2325;
        for b in query.as_bytes() {
            h = (h ^ u64::from(*b)).wrapping_mul(0x0100_0000_01b3);
        }
        usize::try_from(h % 7).unwrap_or(0)
    }

    #[must_use]
    pub fn select_utterance(
        query: &str,
        lang: &str,
        style: DeliveryStyle,
        domain: TaskDomain,
    ) -> ReflexUtterance {
        let idx = Self::hash_query(query);
        let (text, volume_scale) = match style {
            DeliveryStyle::Whisper => (Self::whisper_phrase(lang, idx), 0.35),
            DeliveryStyle::NightDiscreet => (Self::night_phrase(lang, idx), 0.55),
            DeliveryStyle::Normal => (Self::normal_phrase(lang, domain, idx), 1.0),
        };

        ReflexUtterance {
            text: text.to_owned(),
            language: lang.to_owned(),
            delivery_style: style,
            volume_scale,
        }
    }

    fn whisper_phrase(lang: &str, idx: usize) -> &'static str {
        match lang {
            "en" => {
                let options = ["One sec...", "Checking...", "On it...", "Right away..."];
                options.get(idx % options.len()).copied().unwrap_or("One sec...")
            }
            "es" => {
                let options = ["Un segundo...", "Revisando...", "Ya voy...", "Enseguida..."];
                options.get(idx % options.len()).copied().unwrap_or("Un segundo...")
            }
            "fr" => {
                let options = ["Un instant...", "Je vérifie...", "Tout de suite...", "Je regarde..."];
                options.get(idx % options.len()).copied().unwrap_or("Un instant...")
            }
            "de" => {
                let options = ["Einen Moment...", "Prüfe...", "Gleich...", "Sekunde..."];
                options.get(idx % options.len()).copied().unwrap_or("Einen Moment...")
            }
            _ => {
                // Default / IT
                let options = ["Un attimo...", "Controllo...", "Subito...", "Sì, arrivo...", "Un secondo..."];
                options.get(idx % options.len()).copied().unwrap_or("Un attimo...")
            }
        }
    }

    fn night_phrase(lang: &str, idx: usize) -> &'static str {
        match lang {
            "en" => {
                let options = [
                    "Checking quietly for you...",
                    "One moment, working on it...",
                    "Right away, looking into this...",
                    "Taking care of it now...",
                ];
                options.get(idx % options.len()).copied().unwrap_or("One moment, working on it...")
            }
            "es" => {
                let options = [
                    "Lo reviso enseguida...",
                    "Un momento, me encargo ahora...",
                    "Comprobándolo enseguida...",
                ];
                options.get(idx % options.len()).copied().unwrap_or("Un momento, me encargo ahora...")
            }
            "fr" => {
                let options = [
                    "Je m'en occupe discrètement...",
                    "Un instant, je vérifie...",
                    "Tout de suite, je regarde...",
                ];
                options.get(idx % options.len()).copied().unwrap_or("Un instant, je vérifie...")
            }
            "de" => {
                let options = [
                    "Ich kümmere mich leise darum...",
                    "Einen Moment, ich prüfe das...",
                    "Sofort, ich sehe nach...",
                ];
                options.get(idx % options.len()).copied().unwrap_or("Einen Moment, ich prüfe das...")
            }
            _ => {
                // Default / IT
                let options = [
                    "Controllo subito per te...",
                    "Un attimo, ci penso io...",
                    "Verifico subito...",
                    "Me ne occupo io, un istante...",
                ];
                options.get(idx % options.len()).copied().unwrap_or("Un attimo, ci penso io...")
            }
        }
    }

    fn normal_phrase(lang: &str, domain: TaskDomain, idx: usize) -> &'static str {
        match (lang, domain) {
            ("en", TaskDomain::ThinkingComplex) => {
                let options = [
                    "Analyzing this for you, one moment...",
                    "Working through the details now...",
                    "Formulating the plan, bear with me...",
                    "Deep in thought, examining all aspects...",
                ];
                options.get(idx % options.len()).copied().unwrap_or("Working through the details now...")
            }
            ("en", TaskDomain::SearchWeb) => {
                let options = [
                    "Searching the web right away...",
                    "Looking up the latest information for you...",
                    "Checking the online sources now...",
                ];
                options.get(idx % options.len()).copied().unwrap_or("Searching the web right away...")
            }
            ("en", _) => {
                let options = [
                    "Right away, on it!",
                    "Consider it done, checking now...",
                    "Working on that right now...",
                ];
                options.get(idx % options.len()).copied().unwrap_or("Right away, on it!")
            }
            ("es", TaskDomain::ThinkingComplex) => {
                let options = [
                    "Analizando los detalles, un momento...",
                    "Elaborando la mejor solución ahora...",
                    "Pensando en la estrategia adecuada...",
                ];
                options.get(idx % options.len()).copied().unwrap_or("Analizando los detalles, un momento...")
            }
            ("es", _) => {
                let options = [
                    "¡Enseguida me pongo con ello!",
                    "Un momento, comprobándolo...",
                    "Trabajando en ello ahora mismo...",
                ];
                options.get(idx % options.len()).copied().unwrap_or("¡Enseguida me pongo con ello!")
            }
            ("fr", TaskDomain::ThinkingComplex) => {
                let options = [
                    "J'analyse la situation, un instant...",
                    "En train d'élaborer la solution complète...",
                    "Je réfléchis à la meilleure approche...",
                ];
                options.get(idx % options.len()).copied().unwrap_or("J'analyse la situation, un instant...")
            }
            ("fr", _) => {
                let options = [
                    "Tout de suite, je m'en occupe !",
                    "C'est noté, je vérifie immédiatement...",
                    "Je travaille dessus à l'instant...",
                ];
                options.get(idx % options.len()).copied().unwrap_or("Tout de suite, je m'en occupe !")
            }
            ("de", TaskDomain::ThinkingComplex) => {
                let options = [
                    "Ich analysiere das im Detail, einen Moment...",
                    "Erstelle gerade den Lösungsansatz...",
                    "Ich prüfe alle Aspekte für Sie...",
                ];
                options.get(idx % options.len()).copied().unwrap_or("Ich analysiere das im Detail, einen Moment...")
            }
            ("de", _) => {
                let options = [
                    "Sofort, ich kümmere mich darum!",
                    "Wird erledigt, ich prüfe das jetzt...",
                    "Ich bin bereits dran...",
                ];
                options.get(idx % options.len()).copied().unwrap_or("Sofort, ich kümmere mich darum!")
            }
            _ => {
                // Default / IT
                match domain {
                    TaskDomain::ThinkingComplex => {
                        let options = [
                            "Sto elaborando l'analisi, un istante...",
                            "Ci penso io, verifico ogni dettaglio...",
                            "Sto ragionando sulla soluzione migliore...",
                            "Un momento, sto valutando la strategia ottimale...",
                        ];
                        options.get(idx % options.len()).copied().unwrap_or("Ci penso io, verifico ogni dettaglio...")
                    }
                    TaskDomain::SearchWeb => {
                        let options = [
                            "Controllo subito sul web per te...",
                            "Cerco subito le informazioni aggiornate...",
                            "Verifico online in questo momento...",
                        ];
                        options.get(idx % options.len()).copied().unwrap_or("Controllo subito sul web per te...")
                    }
                    _ => {
                        let options = [
                            "Subito, me ne occupo io!",
                            "Ricevuto, verifico all'istante...",
                            "Certamente, ci sono già sopra...",
                        ];
                        options.get(idx % options.len()).copied().unwrap_or("Subito, me ne occupo io!")
                    }
                }
            }
        }
    }
}
