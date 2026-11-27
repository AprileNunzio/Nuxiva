use crate::tests::resolver;
use crate::{Purpose, Relevance, Request};

fn judge(text: &str) -> Relevance {
    resolver()
        .relevance(&Request {
            text: text.to_owned(),
            ..Request::default()
        })
        .expect("relevance")
}

#[test]
fn conversation_never_reaches_the_home() {
    for text in [
        "Jarvis come va?",
        "ciao jarvis come va? tutto bene?",
        "come stai oggi",
        "che ore sono",
        "raccontami una barzelletta",
        "raccontami qualcosa sulla cucina italiana",
        "chi ha vinto la partita del Napoli?",
        "dimmi le notizie di oggi",
        "come si chiama il presidente della repubblica",
        "che tempo fa domani a Roma?",
        "quanto fa 12 per 7",
        "how are you doing?",
        "what time is it?",
        "tell me a story",
        "who won the match last night?",
        "¿qué tal estás?",
        "¿qué hora es?",
        "cuéntame un chiste",
        "comment ça va ?",
        "quelle heure est-il ?",
        "raconte-moi une histoire",
        "apri il browser",
        "avvia il programma di posta",
        "ho letto un libro bellissimo",
        "grazie mille",
        "come va a casa tua?",
        "sono tornato a casa stanco",
    ] {
        let r = judge(text);
        assert!(!r.home, "{text}: {r:?}");
        assert_eq!(r.purpose, Purpose::Other, "{text}");
    }
}

#[test]
fn home_commands_stay_home() {
    for text in [
        "accendi le luci della camera da letto",
        "Jarvis spegni la luce in cucina",
        "spegni la plafoniera",
        "abbassa la tapparella del soggiorno",
        "spegni tutto",
        "accendi le luci in camera",
        "spegni le luci",
        "accendi il condizionatore dello studio",
        "spegni la macchina del caffè",
        "turn on the bedroom lights",
        "turn off the kitchen lights",
        "enciende las luces del dormitorio",
        "allume les lumières de la chambre",
        "acendi le lucci della camera da leto",
    ] {
        let r = judge(text);
        assert!(r.home, "{text}: {r:?}");
        assert_eq!(r.purpose, Purpose::Command, "{text}: {r:?}");
    }
}

#[test]
fn home_questions_stay_home() {
    for text in [
        "la luce della cucina è accesa?",
        "com'è la temperatura in soggiorno?",
        "che temperatura c'è in casa?",
        "c'è movimento in cucina?",
        "chi c'è in casa?",
        "quali finestre sono aperte?",
        "quanti dispositivi zigbee ho?",
        "quanto sta assorbendo tutta la casa?",
        "quanto consuma la casa adesso?",
        "is the kitchen light on?",
        "¿está encendida la luz de la cocina?",
        "la lumière de la cuisine est allumée ?",
    ] {
        let r = judge(text);
        assert!(r.home, "{text}: {r:?}");
    }
}

#[test]
fn a_room_mentioned_in_passing_is_not_a_request() {
    for text in [
        "la cucina di mia nonna era bellissima",
        "ieri ho pulito il bagno",
        "the bedroom is my favourite place",
    ] {
        assert!(!judge(text).home, "{text}");
    }
}
