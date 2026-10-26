from features.musicstudio import genres

DRUMS = {x.id: x.drums for x in genres.ALL}
BASS = {x.id: x.bass for x in genres.ALL}
COMP = {x.id: x.comp for x in genres.ALL}
TEMPO = {x.id: x.tempo for x in genres.ALL}
DEFAULT_KIT = {x.id: x.kit for x in genres.ALL}
DEFAULT_BASS = {x.id: x.bass_i for x in genres.ALL}
DEFAULT_CHORDS = {x.id: x.chords_i for x in genres.ALL}
DEFAULT_LEAD = {x.id: x.lead_i for x in genres.ALL}
RHYTHMS = ("x.x.x..x..x.x...", "x...x.x...x..x..", "x..x..x.x..x..x.", "x.....x.x.x.....", "x.x...x.x...x.x.")
