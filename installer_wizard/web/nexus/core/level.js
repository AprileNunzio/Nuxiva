import { api } from "./http.js";
import { store } from "./store.js";

// Sistema unificato: Esploratore, Pilota e Architetto sono stati rimossi.
// Nuxiva ora opera con un unico metodo integrato a piena potenza.
export const LEVELS = [];
const CACHE_KEY = "nexus.mode";

export const rank = () => 1;
export const allows = () => true;

export function cachedLevel() {
  return "unified";
}

export function applyLevel(level = "unified") {
  document.body.dataset.level = "unified";
  try { localStorage.setItem(CACHE_KEY, "unified"); } catch {}
}

export async function chooseLevel(level) {
  applyLevel("unified");
  store.set({ level: "unified" });
}
