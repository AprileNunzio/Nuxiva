use nuxiva_memory_core::{Class, Color, Item, VehicleKind};

use crate::error::AskError;
use crate::query::{AskQuery, QueryLang, QuestionKind, RoleTarget};

fn normalize(s: &str) -> String {
    s.to_lowercase()
        .chars()
        .map(|c| match c {
            'à' | 'á' | 'â' | 'ã' | 'ä' => 'a',
            'è' | 'é' | 'ê' | 'ë' => 'e',
            'ì' | 'í' | 'î' | 'ï' => 'i',
            'ò' | 'ó' | 'ô' | 'õ' | 'ö' => 'o',
            'ù' | 'ú' | 'û' | 'ü' => 'u',
            '¿' | '¡' => ' ',
            _ => c,
        })
        .collect()
}

fn detect_lang(norm: &str) -> QueryLang {
    if norm.contains("yesterday")
        || norm.contains("what time")
        || norm.contains("wearing")
        || norm.contains("courier")
        || norm.contains("delivery")
    {
        QueryLang::En
    } else if norm.contains("hier")
        || norm.contains("livreur")
        || norm.contains("quelle heure")
        || norm.contains("aujourd")
    {
        QueryLang::Fr
    } else if norm.contains("ayer")
        || norm.contains("hoy")
        || norm.contains("repartidor")
        || norm.contains("coche")
        || norm.contains("que hora")
        || norm.contains("vestia")
        || norm.contains("has visto")
        || norm.contains("quien")
    {
        QueryLang::Es
    } else {
        QueryLang::It
    }
}

fn parse_kind(norm: &str) -> QuestionKind {
    if norm.contains("a che ora")
        || norm.contains("quando")
        || norm.contains("when")
        || norm.contains("what time")
        || norm.contains("quelle heure")
        || norm.contains("quand")
        || norm.contains("que hora")
        || norm.contains("cuando")
    {
        QuestionKind::When
    } else if norm.contains("com'era vestit")
        || norm.contains("com era vestit")
        || norm.contains("cosa indossav")
        || norm.contains("wearing")
        || norm.contains("comment vetu")
        || norm.contains("como vestia")
    {
        QuestionKind::WhatLook
    } else if norm.contains("chi e")
        || norm.contains("chi era")
        || norm.starts_with("chi ")
        || norm.contains("who was")
        || norm.contains("who is")
        || norm.starts_with("who ")
        || norm.contains("qui est")
        || norm.contains("quien era")
    {
        QuestionKind::Who
    } else if norm.contains("passat")
        || norm.contains("passo")
        || norm.contains("passed")
        || norm.contains("seen")
        || norm.contains("hai visto")
        || norm.contains("as-tu vu")
        || norm.contains("has visto")
        || norm.contains("venuto")
    {
        QuestionKind::DidPass
    } else {
        QuestionKind::General
    }
}

fn parse_role_and_class(norm: &str) -> (Option<RoleTarget>, Option<Class>) {
    if norm.contains("corriere")
        || norm.contains("fattorino")
        || norm.contains("courier")
        || norm.contains("delivery")
        || norm.contains("livreur")
        || norm.contains("repartidor")
        || norm.contains("amazon")
        || norm.contains("dhl")
        || norm.contains("ups")
    {
        (Some(RoleTarget::Courier), Some(Class::Person))
    } else if norm.contains("ospite")
        || norm.contains("visitatore")
        || norm.contains("guest")
        || norm.contains("visitor")
        || norm.contains("visiteur")
        || norm.contains("invitado")
    {
        (Some(RoleTarget::Visitor), Some(Class::Person))
    } else if norm.contains("furgone")
        || norm.contains("van")
        || norm.contains("camion")
        || norm.contains("truck")
        || norm.contains("auto")
        || norm.contains("macchina")
        || norm.contains("car")
        || norm.contains("voiture")
        || norm.contains("coche")
    {
        (Some(RoleTarget::Vehicle), Some(Class::Vehicle))
    } else if norm.contains("cane")
        || norm.contains("gatto")
        || norm.contains("dog")
        || norm.contains("cat")
        || norm.contains("animale")
        || norm.contains("animal")
    {
        (Some(RoleTarget::Animal), Some(Class::Animal))
    } else if norm.contains("persona")
        || norm.contains("qualcuno")
        || norm.contains("person")
        || norm.contains("someone")
        || norm.contains("personne")
        || norm.contains("alguien")
    {
        (Some(RoleTarget::Unknown), Some(Class::Person))
    } else {
        (None, None)
    }
}

fn parse_color(norm: &str) -> Option<Color> {
    if norm.contains("rosso")
        || norm.contains("rossa")
        || norm.contains("red")
        || norm.contains("rouge")
        || norm.contains("rojo")
    {
        Some(Color::Red)
    } else if norm.contains("blu")
        || norm.contains("azzurr")
        || norm.contains("blue")
        || norm.contains("bleu")
        || norm.contains("azul")
    {
        Some(Color::Blue)
    } else if norm.contains("bianco")
        || norm.contains("bianca")
        || norm.contains("white")
        || norm.contains("blanc")
        || norm.contains("blanco")
    {
        Some(Color::White)
    } else if norm.contains("nero")
        || norm.contains("nera")
        || norm.contains("black")
        || norm.contains("noir")
        || norm.contains("negro")
    {
        Some(Color::Black)
    } else if norm.contains("verde") || norm.contains("green") || norm.contains("vert") {
        Some(Color::Green)
    } else if norm.contains("giallo")
        || norm.contains("gialla")
        || norm.contains("yellow")
        || norm.contains("jaune")
        || norm.contains("amarillo")
    {
        Some(Color::Yellow)
    } else if norm.contains("grigio")
        || norm.contains("grigia")
        || norm.contains("gray")
        || norm.contains("grey")
        || norm.contains("gris")
    {
        Some(Color::Grey)
    } else {
        None
    }
}

fn parse_item(norm: &str) -> Option<Item> {
    if norm.contains("pacco")
        || norm.contains("parcel")
        || norm.contains("colis")
        || norm.contains("paquete")
        || norm.contains("scatola")
    {
        Some(Item::Parcel)
    } else if norm.contains("zaino")
        || norm.contains("backpack")
        || norm.contains("sac a dos")
        || norm.contains("mochila")
    {
        Some(Item::Backpack)
    } else if norm.contains("borsa")
        || norm.contains("bag")
        || norm.contains("sac")
        || norm.contains("bolso")
    {
        Some(Item::Bag)
    } else if norm.contains("ombrello")
        || norm.contains("umbrella")
        || norm.contains("parapluie")
        || norm.contains("paraguas")
    {
        Some(Item::Umbrella)
    } else {
        None
    }
}

fn parse_vehicle_kind(norm: &str) -> Option<VehicleKind> {
    if norm.contains("furgone") || norm.contains("van") {
        Some(VehicleKind::Van)
    } else if norm.contains("camion") || norm.contains("truck") {
        Some(VehicleKind::Truck)
    } else if norm.contains("moto") || norm.contains("scooter") {
        Some(VehicleKind::Motorbike)
    } else if norm.contains("bici")
        || norm.contains("bicicletta")
        || norm.contains("bicycle")
        || norm.contains("bike")
    {
        Some(VehicleKind::Bicycle)
    } else if norm.contains("auto")
        || norm.contains("macchina")
        || norm.contains("car")
        || norm.contains("voiture")
        || norm.contains("coche")
    {
        Some(VehicleKind::Car)
    } else {
        None
    }
}

fn parse_location(norm: &str) -> Option<String> {
    if norm.contains("cancello") || norm.contains("gate") || norm.contains("portail") {
        Some("cancello".to_owned())
    } else if norm.contains("porta")
        || norm.contains("door")
        || norm.contains("porte")
        || norm.contains("puerta")
    {
        Some("porta".to_owned())
    } else if norm.contains("ingresso")
        || norm.contains("entrance")
        || norm.contains("entree")
        || norm.contains("entrada")
    {
        Some("ingresso".to_owned())
    } else if norm.contains("giardino") || norm.contains("garden") || norm.contains("jardin") {
        Some("giardino".to_owned())
    } else if norm.contains("garage") {
        Some("garage".to_owned())
    } else {
        None
    }
}

fn parse_time(norm: &str, now_ms: u64) -> (u64, u64) {
    const DAY_MS: u64 = 86_400_000;
    if norm.contains("ieri")
        || norm.contains("yesterday")
        || norm.contains("hier")
        || norm.contains("ayer")
    {
        let to = now_ms.saturating_sub(DAY_MS);
        let from = now_ms.saturating_sub(DAY_MS.saturating_mul(2));
        (from, to)
    } else if norm.contains("stamattina")
        || norm.contains("this morning")
        || norm.contains("ce matin")
        || norm.contains("esta manana")
    {
        (now_ms.saturating_sub(43_200_000), now_ms)
    } else if norm.contains("pomeriggio")
        || norm.contains("afternoon")
        || norm.contains("apres-midi")
        || norm.contains("tarde")
    {
        (
            now_ms.saturating_sub(28_800_000),
            now_ms.saturating_sub(3_600_000),
        )
    } else if norm.contains("stasera")
        || norm.contains("this evening")
        || norm.contains("ce soir")
        || norm.contains("esta noche")
    {
        (now_ms.saturating_sub(21_600_000), now_ms)
    } else {
        (now_ms.saturating_sub(DAY_MS), now_ms)
    }
}

pub fn parse(text: &str, now_ms: u64) -> Result<AskQuery, AskError> {
    let raw = text.trim();
    if raw.is_empty() {
        return Err(AskError::EmptyQuery);
    }
    let norm = normalize(raw);
    let lang = detect_lang(&norm);
    let kind = parse_kind(&norm);
    let (target_role, class) = parse_role_and_class(&norm);
    let color = parse_color(&norm);
    let item = parse_item(&norm);
    let vehicle_kind = parse_vehicle_kind(&norm);
    let camera_or_zone = parse_location(&norm);
    let (from_ms, to_ms) = parse_time(&norm, now_ms);

    let (upper_color, vehicle_color) = match class {
        Some(Class::Vehicle) => (None, color),
        _ => (color, None),
    };

    Ok(AskQuery {
        lang,
        kind,
        from_ms,
        to_ms,
        target_role,
        class,
        upper_color,
        lower_color: None,
        headwear: None,
        item,
        vehicle_kind,
        vehicle_color,
        camera_or_zone,
    })
}
