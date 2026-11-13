use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Lang {
    It,
    En,
    Fr,
    Es,
}

impl Lang {
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::It => "it",
            Self::En => "en",
            Self::Fr => "fr",
            Self::Es => "es",
        }
    }

    #[must_use]
    pub fn labels(self) -> &'static Labels {
        match self {
            Self::It => &IT,
            Self::En => &EN,
            Self::Fr => &FR,
            Self::Es => &ES,
        }
    }
}

#[derive(Debug)]
pub struct Labels {
    pub family: &'static str,
    pub guest: &'static str,
    pub call: &'static str,
    pub years: &'static str,
    pub work: &'static str,
    pub relations: &'static str,
    pub food_likes: &'static str,
    pub food_dislikes: &'static str,
    pub drinks: &'static str,
    pub music: &'static str,
    pub movies: &'static str,
    pub sports: &'static str,
    pub hobbies: &'static str,
    pub listening: &'static str,
    pub today: &'static str,
    pub allergies: &'static str,
    pub diet: &'static str,
    pub mood: &'static str,
    pub mood_positive: &'static str,
    pub mood_negative: &'static str,
    pub mood_neutral: &'static str,
    pub energetic: &'static str,
    pub calm: &'static str,
}

static IT: Labels = Labels {
    family: "famiglia",
    guest: "ospite",
    call: "chiamalo/a",
    years: "anni",
    work: "lavoro",
    relations: "relazioni",
    food_likes: "cibi graditi",
    food_dislikes: "cibi non graditi",
    drinks: "bevande",
    music: "musica",
    movies: "film",
    sports: "sport",
    hobbies: "hobby",
    listening: "ascolti recenti",
    today: "oggi",
    allergies: "allergie",
    diet: "dieta",
    mood: "umore",
    mood_positive: "positivo",
    mood_negative: "negativo",
    mood_neutral: "neutro",
    energetic: "energico",
    calm: "calmo",
};

static EN: Labels = Labels {
    family: "family",
    guest: "guest",
    call: "call them",
    years: "years old",
    work: "work",
    relations: "relations",
    food_likes: "liked foods",
    food_dislikes: "disliked foods",
    drinks: "drinks",
    music: "music",
    movies: "movies",
    sports: "sports",
    hobbies: "hobbies",
    listening: "recent listening",
    today: "today",
    allergies: "allergies",
    diet: "diet",
    mood: "mood",
    mood_positive: "positive",
    mood_negative: "negative",
    mood_neutral: "neutral",
    energetic: "energetic",
    calm: "calm",
};

static FR: Labels = Labels {
    family: "famille",
    guest: "invité",
    call: "appelle-le/la",
    years: "ans",
    work: "travail",
    relations: "relations",
    food_likes: "aliments appréciés",
    food_dislikes: "aliments non appréciés",
    drinks: "boissons",
    music: "musique",
    movies: "films",
    sports: "sports",
    hobbies: "loisirs",
    listening: "écoutes récentes",
    today: "aujourd'hui",
    allergies: "allergies",
    diet: "régime",
    mood: "humeur",
    mood_positive: "positive",
    mood_negative: "négative",
    mood_neutral: "neutre",
    energetic: "énergique",
    calm: "calme",
};

static ES: Labels = Labels {
    family: "familia",
    guest: "invitado",
    call: "llámalo/a",
    years: "años",
    work: "trabajo",
    relations: "relaciones",
    food_likes: "comidas preferidas",
    food_dislikes: "comidas no preferidas",
    drinks: "bebidas",
    music: "música",
    movies: "películas",
    sports: "deportes",
    hobbies: "aficiones",
    listening: "escuchas recientes",
    today: "hoy",
    allergies: "alergias",
    diet: "dieta",
    mood: "ánimo",
    mood_positive: "positivo",
    mood_negative: "negativo",
    mood_neutral: "neutro",
    energetic: "enérgico",
    calm: "tranquilo",
};
