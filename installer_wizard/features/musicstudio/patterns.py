DRUMS = {
    "pop": {"kick": "X.......X.x.....", "snare": "....X.......X...", "hat": "x.x.x.x.x.x.x.x.", "open_hat": "......o.......o."},
    "rock": {"kick": "X.....x.X.x.....", "snare": "....X.......X...", "hat": "x.x.x.x.x.x.x.x.", "crash": "X..............."},
    "house": {"kick": "X...X...X...X...", "clap": "....X.......X...", "open_hat": "..x...x...x...x.", "hat": "x.x.x.x.x.x.x.x."},
    "techno": {"kick": "X...X...X...X...", "hat": "xoxoxoxoxoxoxoxo", "perc": "..x...x...x.x...", "clap": "....o.......o..."},
    "hiphop": {"kick": "X.....x...x.....", "snare": "....X.......X...", "hat": "x.x.x.x.x.x.x.xx"},
    "trap": {"kick": "X.......x.x.....", "clap": "........X.......", "hat": "xoxoxoxoxoxxxoxo", "open_hat": "..............o."},
    "lofi": {"kick": "X.....x.....x...", "snare": "....X.......X...", "hat": "x.o.x.o.x.o.x.ox"},
    "reggaeton": {"kick": "X...X...X...X...", "snare": "...X..X....X..X.", "hat": "x.x.x.x.x.x.x.x."},
    "disco": {"kick": "X...X...X...X...", "clap": "....X.......X...", "open_hat": "..x...x...x...x.", "hat": "x.x.x.x.x.x.x.x."},
    "ballad": {"kick": "X.......x.......", "rim": "....x.......x...", "hat": "x.x.x.x.x.x.x.x."},
    "dnb": {"kick": "X.........x.....", "snare": "....X.......X...", "hat": "xxxxxxxxxxxxxxxx"},
    "ambient": {"kick": "X...............", "perc": "........x......."},
    "funk": {"kick": "X..x..X...x.....", "snare": "....X..x.x..X...", "hat": "xoxoxoxoxoxoxoxo"},
    "latin": {"kick": "X..x..x.X..x....", "rim": "..x..x..x..x.x..", "hat": "x.x.x.x.x.x.x.x."},
}
BASS = {
    "pop": "r..r..r.f..r.o..", "rock": "r.r.r.r.r.r.r.r.", "house": "..r...r...r...r.", "techno": "r.r.r.r.r.r.r.r.", "hiphop": "r.....r...f.r...",
    "trap": "r.......r.......", "lofi": "r.....f...r.o...", "reggaeton": "r..r..r.r..r..r.", "disco": "r.o.r.o.r.o.r.o.", "ballad": "r.......f.......",
    "ambient": "r...............", "dnb": "r.....r...r.....", "funk": "r..r.or..f..r.o.", "latin": "r..f..r.r..f..r.",
}
COMP = {
    "pop": "c.......c.......", "rock": "c.c.c.c.c.c.c.c.", "house": "..c...c...c...c.", "techno": "..c.....c.......", "hiphop": "c.....c.........",
    "trap": "c...............", "lofi": "c.....c...c.....", "reggaeton": "c..c..c.c..c..c.", "disco": "c.c.c.c.c.c.c.c.", "ballad": "c...c...c...c...",
    "ambient": "c...............", "dnb": "c.......c.......", "funk": "c..c..c...c.c...", "latin": "c..c..c.c..c..c.",
}
RHYTHMS = ("x.x.x..x..x.x...", "x...x.x...x..x..", "x..x..x.x..x..x.", "x.....x.x.x.....", "x.x...x.x...x.x.")
TEMPO = {"pop": (96, 124), "rock": (110, 150), "house": (120, 128), "techno": (128, 140), "hiphop": (80, 98), "trap": (130, 160), "lofi": (68, 86),
         "reggaeton": (88, 100), "disco": (110, 124), "ballad": (60, 80), "dnb": (168, 178), "ambient": (60, 90), "funk": (96, 116), "latin": (92, 112)}
DEFAULT_KIT = {"pop": "kit_acoustic", "rock": "kit_acoustic", "house": "kit_electro", "techno": "kit_electro", "hiphop": "kit_808", "trap": "kit_808", "lofi": "kit_lofi",
               "reggaeton": "kit_electro", "disco": "kit_electro", "ballad": "kit_acoustic", "dnb": "kit_electro", "ambient": "kit_lofi", "funk": "kit_acoustic", "latin": "kit_acoustic"}
DEFAULT_BASS = {"pop": "bass_pluck", "rock": "bass_pluck", "house": "bass_saw", "techno": "bass_saw", "hiphop": "bass_sub", "trap": "bass_sub", "lofi": "bass_pluck",
                "reggaeton": "bass_sub", "disco": "bass_saw", "ballad": "bass_pluck", "dnb": "bass_sub", "ambient": "bass_sub", "funk": "bass_saw", "latin": "bass_pluck"}
DEFAULT_CHORDS = {"pop": "keys_electric", "rock": "organ", "house": "keys_piano", "techno": "pad_glass", "hiphop": "keys_electric", "trap": "pad_glass", "lofi": "keys_electric",
                  "reggaeton": "keys_piano", "disco": "keys_electric", "ballad": "keys_piano", "dnb": "pad_warm", "ambient": "pad_glass", "funk": "keys_electric", "latin": "keys_piano"}
DEFAULT_LEAD = {"pop": "lead_saw", "rock": "lead_saw", "house": "lead_saw", "techno": "lead_square", "hiphop": "lead_bell", "trap": "lead_bell", "lofi": "lead_bell",
                "reggaeton": "lead_flute", "disco": "lead_saw", "ballad": "lead_flute", "dnb": "lead_saw", "ambient": "lead_bell", "funk": "lead_square", "latin": "lead_flute"}
