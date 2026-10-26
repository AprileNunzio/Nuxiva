from features.musicstudio.model import Instrument as I, breath, kit, osc, synth, vib

KITS = (
    I("kit_jazz", "Batteria jazz (spazzole)", "drums", "#fb923c", kit(56, 200, 5200, 0.4, 0.3, 0.6, 0.05), ("jazz", "spazzole", "brush", "swing", "bossa")),
    I("kit_rock", "Batteria rock potente", "drums", "#ea580c", kit(50, 180, 8000, 1.0, 0.9, 0.45, 0.35), ("rock", "hard", "metal", "punk", "potente")),
    I("kit_909", "Batteria 909", "drums", "#f43f5e", kit(55, 220, 10000, 0.95, 0.85, 0.7, 0.25), ("909", "house", "techno", "trance", "club")),
    I("kit_breaks", "Batteria breakbeat", "drums", "#e11d48", kit(54, 205, 9400, 0.85, 1.0, 0.55, 0.45), ("breakbeat", "jungle", "dnb", "break")),
    I("kit_latin", "Percussioni latine", "drums", "#d97706", kit(60, 260, 7000, 0.5, 0.8, 0.9, 0.1), ("latin", "salsa", "timbales", "conga", "cumbia", "samba")),
    I("kit_world", "Percussioni a mano", "drums", "#b45309", kit(70, 240, 6000, 0.45, 0.6, 1.0, 0.15), ("djembe", "darbuka", "tabla", "afro", "arabo", "indiano")),
    I("kit_taiko", "Tamburi taiko", "drums", "#92400e", kit(40, 140, 4000, 1.0, 0.3, 0.3, 0.4), ("taiko", "epico", "orchestrale", "giapponese")),
    I("kit_marching", "Rullante da banda", "drums", "#a16207", kit(48, 230, 6500, 0.7, 1.0, 0.8, 0.2), ("marcia", "banda", "militare", "polka")),
)
BASSES = (
    I("bass_upright", "Contrabbasso", "bass", "#7c3aed", synth([osc("triangle", 1.0), osc("sine", 0.5, 0, 1)], 0.006, 0.45, 0.25, 0.18, 900, 0.9, 700, True), ("contrabbasso", "upright", "jazz", "swing", "bossa", "bluegrass")),
    I("bass_fretless", "Basso fretless", "bass", "#8b5cf6", vib(synth([osc("sawtooth", 0.6), osc("triangle", 0.6)], 0.01, 0.4, 0.6, 0.2, 1400, 1.0, 600, True, 0.04), 5, 12), ("fretless", "soul", "fusion", "jazz")),
    I("bass_slap", "Basso slap", "bass", "#6d28d9", synth([osc("square", 0.7), osc("sawtooth", 0.4, 0, 1)], 0.001, 0.12, 0.1, 0.06, 2600, 2.0, 3000, True), ("slap", "funk", "disco", "pop")),
    I("bass_acid", "Basso acid", "bass", "#a21caf", synth([osc("sawtooth", 1.0)], 0.002, 0.18, 0.4, 0.05, 700, 12, 3200, True, 0.03), ("acid", "303", "house", "techno", "trance")),
    I("bass_reese", "Basso reese", "bass", "#5b21b6", synth([osc("sawtooth", 0.7, -14), osc("sawtooth", 0.7, 14), osc("sawtooth", 0.5, 0, -1)], 0.01, 0.3, 0.9, 0.2, 1100, 1.5, 500, True), ("reese", "dnb", "dubstep", "jungle")),
    I("bass_dub", "Basso dub", "bass", "#4c1d95", synth([osc("sine", 1.0), osc("triangle", 0.3, 0, 1)], 0.01, 0.4, 0.8, 0.3, 500, 0.8, 0, True), ("dub", "reggae", "ska", "dancehall")),
    I("bass_synthwave", "Basso synthwave", "bass", "#9333ea", synth([osc("sawtooth", 0.8), osc("square", 0.4, 3, -1)], 0.004, 0.15, 0.7, 0.08, 1500, 3.0, 1200, True), ("synthwave", "retrowave", "eighties", "electro")),
    I("bass_tuba", "Tuba", "bass", "#6b21a8", breath(synth([osc("square", 0.6), osc("sawtooth", 0.5, 0, -1)], 0.04, 0.2, 0.8, 0.12, 700, 0.9, 200, True), 0.1), ("tuba", "polka", "marcia", "banda", "dixieland")),
)
CHORDS = (
    I("keys_rhodes", "Rhodes", "chords", "#0284c7", synth([osc("sine", 1.0), osc("sine", 0.3, 4, 2)], 0.003, 1.2, 0.3, 0.6, 4500, 0.8, 1200), ("rhodes", "soul", "neo soul", "jazz", "lofi")),
    I("keys_clav", "Clavinet", "chords", "#0369a1", synth([osc("square", 0.6), osc("sawtooth", 0.5, 0, 1)], 0.001, 0.14, 0.15, 0.05, 3800, 3.5, 2500), ("clavinet", "funk", "disco")),
    I("keys_vibes", "Vibrafono", "chords", "#0891b2", vib(synth([osc("sine", 0.9), osc("sine", 0.3, 0, 2)], 0.002, 1.6, 0.0, 1.1, 6500), 5.5, 8), ("vibrafono", "vibes", "jazz", "lounge")),
    I("keys_harpsichord", "Clavicembalo", "chords", "#0e7490", synth([osc("sawtooth", 0.6), osc("square", 0.4, 0, 1)], 0.001, 0.5, 0.02, 0.1, 5200, 1.4, 3000), ("clavicembalo", "harpsichord", "barocco", "classica")),
    I("keys_accordion", "Fisarmonica", "chords", "#155e75", vib(synth([osc("sawtooth", 0.5, -6), osc("sawtooth", 0.5, 6), osc("square", 0.3, 0, 1)], 0.04, 0.1, 0.9, 0.12, 2600, 1.0, 200), 5, 6), ("fisarmonica", "accordion", "tango", "musette", "polka", "folk", "napoletana")),
    I("keys_celesta", "Celesta", "chords", "#22d3ee", synth([osc("sine", 0.8), osc("sine", 0.4, 0, 2), osc("sine", 0.15, 0, 3)], 0.002, 1.4, 0.0, 0.9, 9000), ("celesta", "carillon", "magico", "natalizio")),
    I("keys_synth_stab", "Stab synth", "chords", "#38bdf8", synth([osc("sawtooth", 0.6, -9), osc("sawtooth", 0.6, 9), osc("square", 0.3)], 0.002, 0.2, 0.1, 0.12, 4800, 2.0, 3200), ("stab", "house", "trance", "rave")),
    I("guitar_acoustic", "Chitarra acustica", "chords", "#ca8a04", synth([osc("sawtooth", 0.5), osc("triangle", 0.5, 2, 1)], 0.002, 0.9, 0.12, 0.3, 3800, 1.0, 2400), ("chitarra", "acustica", "folk", "country", "pop", "cantautore")),
    I("guitar_nylon", "Chitarra classica", "chords", "#d4a017", synth([osc("triangle", 0.8), osc("sine", 0.5, 0, 1)], 0.002, 1.0, 0.08, 0.35, 3000, 0.9, 1800), ("nylon", "classica", "flamenco", "bossa", "spagnola")),
    I("guitar_clean", "Chitarra pulita", "chords", "#eab308", synth([osc("sawtooth", 0.45), osc("sine", 0.5, 0, 1)], 0.003, 0.7, 0.3, 0.3, 4200, 0.8, 1500), ("chitarra", "pulita", "clean", "indie", "surf", "country")),
    I("guitar_muted", "Chitarra muted", "chords", "#a16207", synth([osc("square", 0.5), osc("sawtooth", 0.4)], 0.001, 0.07, 0.0, 0.04, 1800, 1.5, 1000), ("palm", "muted", "funk", "reggae", "metal", "punk")),
    I("guitar_distorted", "Chitarra distorta", "chords", "#854d0e", synth([osc("square", 0.7, -5), osc("sawtooth", 0.6, 5)], 0.002, 0.3, 0.7, 0.12, 2800, 1.2, 800), ("distorta", "power", "rock", "metal", "punk", "grunge")),
    I("banjo", "Banjo", "chords", "#facc15", synth([osc("sawtooth", 0.5), osc("square", 0.4, 0, 1)], 0.001, 0.3, 0.0, 0.1, 5200, 2.0, 3000), ("banjo", "bluegrass", "country", "dixieland")),
    I("mandolin", "Mandolino", "chords", "#fbbf24", synth([osc("square", 0.5, -4), osc("square", 0.5, 4), osc("triangle", 0.4, 0, 1)], 0.001, 0.35, 0.05, 0.12, 4800, 1.2, 2200), ("mandolino", "napoletana", "folk", "bluegrass", "celtic")),
    I("ukulele", "Ukulele", "chords", "#fde047", synth([osc("triangle", 0.8), osc("sine", 0.5, 0, 1)], 0.001, 0.5, 0.05, 0.15, 4000, 0.8, 1600), ("ukulele", "hawaii", "estate", "folk")),
    I("harp", "Arpa", "chords", "#c4b5fd", synth([osc("sine", 0.9), osc("triangle", 0.4, 0, 1)], 0.002, 1.8, 0.0, 0.9, 6500, 0.7, 1800), ("arpa", "harp", "celtica", "classica", "fiaba")),
)
PADS = (
    I("pad_choir", "Coro", "pad", "#34d399", breath(synth([osc("sawtooth", 0.4, -7), osc("sawtooth", 0.4, 7), osc("triangle", 0.5, 0, 1)], 0.6, 0.6, 0.85, 1.2, 1800, 1.5, 400), 0.15), ("coro", "choir", "gospel", "epico", "sacro")),
    I("pad_analog", "Pad analogico", "pad", "#4ade80", synth([osc("sawtooth", 0.5, -12), osc("sawtooth", 0.5, 12), osc("square", 0.2, 0, -1)], 0.5, 0.7, 0.8, 1.0, 2200, 1.0, 900), ("analogico", "synth", "synthwave", "eighties")),
    I("pad_dark", "Pad oscuro", "pad", "#22c55e", synth([osc("sawtooth", 0.6, -6, -1), osc("square", 0.3, 6)], 1.0, 1.2, 0.8, 2.0, 900, 1.6, 300), ("oscuro", "dark", "cinematografico", "horror", "techno")),
    I("brass_section", "Sezione fiati", "pad", "#16a34a", synth([osc("sawtooth", 0.6, -5), osc("sawtooth", 0.6, 5)], 0.06, 0.2, 0.85, 0.2, 2400, 1.0, 1800), ("ottoni", "fiati", "brass", "funk", "soul", "ska", "salsa")),
    I("strings_pizz", "Archi pizzicati", "pad", "#15803d", synth([osc("triangle", 0.9), osc("sawtooth", 0.2)], 0.001, 0.25, 0.0, 0.1, 3000, 0.9, 1800), ("pizzicato", "archi", "classica", "film")),
    I("drone", "Bordone", "pad", "#166534", synth([osc("sawtooth", 0.5, -4, -1), osc("sawtooth", 0.5, 4, -1), osc("sine", 0.4, 0, 0)], 1.2, 0.5, 1.0, 1.5, 700, 1.0, 100), ("bordone", "drone", "indiano", "cornamusa", "ambient")),
)
LEADS = (
    I("lead_sax", "Sassofono", "lead", "#dc2626", vib(breath(synth([osc("sawtooth", 0.7), osc("square", 0.3, 0, 0)], 0.03, 0.15, 0.85, 0.12, 2400, 1.8, 900, True, 0.03), 0.12), 5.2, 14), ("sax", "sassofono", "jazz", "soul", "smooth")),
    I("lead_trumpet", "Tromba", "lead", "#ea580c", vib(synth([osc("sawtooth", 0.8), osc("square", 0.3)], 0.025, 0.12, 0.85, 0.1, 3200, 1.5, 2000, True, 0.02), 5.5, 10), ("tromba", "trumpet", "jazz", "mariachi", "ska", "salsa")),
    I("lead_trombone", "Trombone", "lead", "#c2410c", vib(synth([osc("sawtooth", 0.8), osc("square", 0.2)], 0.04, 0.15, 0.85, 0.12, 1800, 1.2, 1200, True, 0.06), 5, 12), ("trombone", "jazz", "ska", "dixieland")),
    I("lead_violin", "Violino", "lead", "#be123c", vib(synth([osc("sawtooth", 0.8), osc("sawtooth", 0.3, 6)], 0.07, 0.1, 0.9, 0.15, 4800, 1.0, 1200, True, 0.03), 5.8, 20), ("violino", "violin", "classica", "folk", "celtica", "zingaro")),
    I("lead_cello", "Violoncello", "lead", "#9f1239", vib(synth([osc("sawtooth", 0.8), osc("triangle", 0.4, 0, 0)], 0.1, 0.2, 0.9, 0.2, 2200, 0.9, 700, True, 0.03), 5, 16), ("violoncello", "cello", "classica", "cinematografico")),
    I("lead_clarinet", "Clarinetto", "lead", "#f97316", vib(breath(synth([osc("square", 0.6), osc("triangle", 0.4, 0, 1)], 0.04, 0.1, 0.9, 0.1, 2800, 0.8, 300, True), 0.08), 5, 8), ("clarinetto", "klezmer", "jazz", "classica")),
    I("lead_oboe", "Oboe", "lead", "#fb7185", vib(breath(synth([osc("sawtooth", 0.6), osc("square", 0.4)], 0.05, 0.1, 0.85, 0.12, 3400, 3.0, 500, True), 0.1), 5, 10), ("oboe", "classica", "pastorale")),
    I("lead_sitar", "Sitar", "lead", "#b91c1c", synth([osc("sawtooth", 0.7), osc("square", 0.5, 7, 1)], 0.002, 1.0, 0.1, 0.4, 4200, 5.0, 3500, True, 0.08), ("sitar", "indiano", "raga", "bollywood")),
    I("lead_oud", "Oud", "lead", "#a16207", synth([osc("triangle", 0.8), osc("sawtooth", 0.4, 3)], 0.002, 0.6, 0.05, 0.25, 3200, 1.2, 2200, True, 0.02), ("oud", "arabo", "maqam", "turco")),
    I("lead_kalimba", "Kalimba", "lead", "#d97706", synth([osc("sine", 0.9), osc("sine", 0.3, 0, 3)], 0.001, 0.9, 0.0, 0.5, 7000), ("kalimba", "mbira", "africa", "lofi")),
    I("lead_marimba", "Marimba", "lead", "#b45309", synth([osc("sine", 0.9), osc("sine", 0.25, 0, 2)], 0.001, 0.4, 0.0, 0.25, 5000), ("marimba", "latin", "afro", "caraibico")),
    I("lead_steelpan", "Steel drum", "lead", "#0d9488", synth([osc("sine", 0.8), osc("triangle", 0.4, 6, 1), osc("sine", 0.2, 0, 2)], 0.002, 0.8, 0.05, 0.5, 6000), ("steelpan", "steel drum", "calypso", "caraibi", "reggae")),
    I("lead_shakuhachi", "Shakuhachi", "lead", "#65a30d", vib(breath(synth([osc("sine", 0.9), osc("triangle", 0.2, 0, 1)], 0.1, 0.2, 0.8, 0.3, 3500, 0.7, 0, True, 0.08), 0.35), 4.5, 25), ("shakuhachi", "giapponese", "zen", "flauto")),
    I("lead_bagpipe", "Cornamusa", "lead", "#15803d", synth([osc("sawtooth", 0.7), osc("square", 0.5, 4)], 0.02, 0.05, 1.0, 0.06, 2600, 3.0, 0, True), ("cornamusa", "bagpipe", "celtico", "scozzese")),
    I("lead_erhu", "Erhu", "lead", "#be185d", vib(synth([osc("sawtooth", 0.7), osc("square", 0.2)], 0.08, 0.1, 0.85, 0.15, 3500, 2.5, 600, True, 0.05), 5.5, 28), ("erhu", "cinese", "orientale")),
    I("lead_duduk", "Duduk", "lead", "#9a3412", vib(breath(synth([osc("sawtooth", 0.5), osc("triangle", 0.5)], 0.08, 0.1, 0.85, 0.2, 1800, 1.5, 300, True, 0.04), 0.2), 4.8, 14), ("duduk", "armeno", "mediorientale", "cinematografico")),
    I("lead_panflute", "Flauto di Pan", "lead", "#84cc16", breath(synth([osc("sine", 1.0), osc("triangle", 0.2, 0, 1)], 0.05, 0.1, 0.85, 0.2, 4200, 0.6, 0, True), 0.3), ("pan", "ande", "flauto", "andino")),
    I("lead_whistle", "Fischio", "lead", "#fde047", vib(synth([osc("sine", 1.0)], 0.04, 0.05, 0.9, 0.1, 8000, 0.5, 0, True, 0.05), 5.5, 15), ("fischio", "whistle", "western", "ottimista")),
    I("lead_acid", "Lead acid", "lead", "#c026d3", synth([osc("sawtooth", 1.0)], 0.002, 0.15, 0.5, 0.06, 900, 10, 3000, True, 0.02), ("acid", "303", "trance", "techno")),
    I("lead_supersaw", "Supersaw", "lead", "#e11d48", synth([osc("sawtooth", 0.5, -18), osc("sawtooth", 0.5, -8), osc("sawtooth", 0.5, 8), osc("sawtooth", 0.5, 18)], 0.01, 0.3, 0.8, 0.3, 6000, 0.9, 1800), ("supersaw", "trance", "edm", "dance")),
    I("lead_pluck", "Pluck synth", "lead", "#f472b6", synth([osc("sawtooth", 0.6), osc("square", 0.3, 5)], 0.001, 0.22, 0.0, 0.15, 4500, 1.4, 3500, True), ("pluck", "edm", "future", "pop")),
    I("lead_synthwave", "Lead synthwave", "lead", "#d946ef", vib(synth([osc("sawtooth", 0.6, -6), osc("square", 0.5, 6)], 0.02, 0.3, 0.7, 0.3, 3800, 1.6, 1200, True, 0.03), 5, 10), ("synthwave", "retrowave", "eighties")),
)
ARPS = (
    I("arp_harp", "Arpeggio arpa", "arp", "#a78bfa", synth([osc("sine", 0.9), osc("triangle", 0.35, 0, 1)], 0.002, 1.2, 0.0, 0.6, 6500), ("arpa", "arpeggio", "fiaba", "classica")),
    I("arp_guitar", "Arpeggio chitarra", "arp", "#c084fc", synth([osc("triangle", 0.8), osc("sawtooth", 0.3, 0, 1)], 0.002, 0.7, 0.05, 0.25, 3600, 0.9, 1800), ("chitarra", "arpeggio", "folk", "ballad")),
    I("arp_synthwave", "Arpeggio synthwave", "arp", "#e879f9", synth([osc("sawtooth", 0.6), osc("square", 0.4, 4)], 0.002, 0.2, 0.2, 0.1, 3000, 2.5, 2500), ("synthwave", "arpeggio", "retro", "eighties")),
    I("arp_marimba", "Arpeggio marimba", "arp", "#f0abfc", synth([osc("sine", 0.9), osc("sine", 0.25, 0, 2)], 0.001, 0.35, 0.0, 0.2, 5000), ("marimba", "arpeggio", "minimal", "latin")),
)
MORE = KITS + BASSES + CHORDS + PADS + LEADS + ARPS
