use crate::evidence::EvidenceCitation;
use crate::query::{AskQuery, QueryLang, QuestionKind, RoleTarget};

fn format_evidence_tags(c: &EvidenceCitation, lang: QueryLang) -> String {
    let mut parts = Vec::new();
    if let Some(f) = &c.frame_evidence_id {
        let label = match lang {
            QueryLang::It => "fotogramma",
            QueryLang::En => "frame",
            QueryLang::Fr => "image",
            QueryLang::Es => "fotograma",
        };
        parts.push(format!("{label} #{f}"));
    }
    if let Some(cl) = &c.clip_evidence_id {
        let label = match lang {
            QueryLang::It => "clip video",
            QueryLang::En => "video clip",
            QueryLang::Fr => "clip vidéo",
            QueryLang::Es => "clip de video",
        };
        parts.push(format!("{label} #{cl}"));
    }
    if parts.is_empty() {
        String::new()
    } else {
        match lang {
            QueryLang::It => format!(" Prove: {}.", parts.join(", ")),
            QueryLang::En => format!(" Evidence: {}.", parts.join(", ")),
            QueryLang::Fr => format!(" Preuves: {}.", parts.join(", ")),
            QueryLang::Es => format!(" Pruebas: {}.", parts.join(", ")),
        }
    }
}

#[must_use]
pub fn format_answer(query: &AskQuery, citations: &[EvidenceCitation]) -> String {
    let Some(primary) = citations.first() else {
        return match query.lang {
            QueryLang::It => {
                "Nessuna prova sufficiente trovata per l'intervallo richiesto.".to_owned()
            }
            QueryLang::En => {
                "No sufficient evidence found for the requested time range.".to_owned()
            }
            QueryLang::Fr => {
                "Aucune preuve suffisante trouvée pour la période demandée.".to_owned()
            }
            QueryLang::Es => {
                "No se encontraron pruebas suficientes para el intervalo solicitado.".to_owned()
            }
        };
    };

    let ev_tag = format_evidence_tags(primary, query.lang);
    let cam = &primary.camera;
    let time = &primary.time_str;
    let conf = primary.confidence_pct;
    let look = &primary.appearance_desc;

    match query.lang {
        QueryLang::It => {
            let role_str = match query.target_role {
                Some(RoleTarget::Courier) => "Il corriere",
                Some(RoleTarget::Visitor) => "Un visitatore",
                Some(RoleTarget::Vehicle) => "Un veicolo",
                Some(RoleTarget::Animal) => "Un animale",
                _ => "Un soggetto",
            };
            match query.kind {
                QuestionKind::When => {
                    format!(
                        "{role_str} è stato rilevato alle ore {time} su telecamera '{cam}' [aspetto: {look}] (confidenza {conf}%).{ev_tag}"
                    )
                }
                QuestionKind::WhatLook => {
                    format!(
                        "{role_str} rilevato su telecamera '{cam}' alle {time} indossava/presentava: {look} (confidenza {conf}%).{ev_tag}"
                    )
                }
                QuestionKind::Who => {
                    format!(
                        "Rilevato {role_str} alle {time} su telecamera '{cam}' con aspetto: {look} (confidenza {conf}%).{ev_tag}"
                    )
                }
                QuestionKind::DidPass | QuestionKind::General => {
                    format!(
                        "Confermato: {role_str} rilevato alle ore {time} su telecamera '{cam}', aspetto: {look} (confidenza {conf}%).{ev_tag}"
                    )
                }
            }
        }
        QueryLang::En => {
            let role_str = match query.target_role {
                Some(RoleTarget::Courier) => "The courier",
                Some(RoleTarget::Visitor) => "A visitor",
                Some(RoleTarget::Vehicle) => "A vehicle",
                Some(RoleTarget::Animal) => "An animal",
                _ => "A subject",
            };
            format!(
                "{role_str} was detected at {time} on camera '{cam}' [appearance: {look}] (confidence {conf}%).{ev_tag}"
            )
        }
        QueryLang::Fr => {
            let role_str = match query.target_role {
                Some(RoleTarget::Courier) => "Le livreur",
                Some(RoleTarget::Visitor) => "Un visiteur",
                Some(RoleTarget::Vehicle) => "Un véhicule",
                Some(RoleTarget::Animal) => "Un animal",
                _ => "Un sujet",
            };
            format!(
                "{role_str} a été détecté à {time} sur la caméra '{cam}' [apparence: {look}] (confiance {conf}%).{ev_tag}"
            )
        }
        QueryLang::Es => {
            let role_str = match query.target_role {
                Some(RoleTarget::Courier) => "El repartidor",
                Some(RoleTarget::Visitor) => "Un visitante",
                Some(RoleTarget::Vehicle) => "Un vehículo",
                Some(RoleTarget::Animal) => "Un animal",
                _ => "Un sujeto",
            };
            format!(
                "{role_str} fue detectado a las {time} en la cámara '{cam}' [aspecto: {look}] (confianza {conf}%).{ev_tag}"
            )
        }
    }
}
