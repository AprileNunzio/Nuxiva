(function (J) {
  "use strict";
  const H = (J.Holo = J.Holo || {});
  const W = "(?![\\wàáèéìíòóùúçñ])";
  const RULES = {
    greet: new RegExp(`(^|\\s)(ciao|buongiorno|buonasera|buonanotte|salve|bentornat\\w*|benvenut\\w*|hello|hi|hey|good (?:morning|evening|night)|welcome( back)?|hola|buenos días|buenas (?:tardes|noches)|bienvenid\\w*|bonjour|bonsoir|salut|bienvenue)${W}`, "i"),
    deny: new RegExp(`^(no|non sono d'accordo|purtroppo no|temo di no|negativo|i'm afraid not|unfortunately not|i disagree|me temo que no|lamentablemente no|non|malheureusement non|je crains que non)${W}`, "i"),
    agree: new RegExp(`^(sì|si|certo|esatto|perfetto|va bene|d'accordo|ok|fatto|certamente|volentieri|yes|sure|exactly|done|of course|claro|exacto|vale|hecho|por supuesto|oui|bien sûr|exactement|d'accord|c'est fait)${W}`, "i"),
    sad: /(mi dispiace|purtroppo|scusa|scusami|non riesco|errore|non è possibile|i'm sorry|unfortunately|i can't|error|lo siento|lamentablemente|no puedo|désolé|malheureusement|je ne peux pas|erreur)/i,
    surprise: /(wow|incredibile|davvero\?|sorprendente|accidenti|incredible|really\?|amazing|increíble|¿de verdad\?|incroyable|vraiment \?)/i,
    happy: /(!|fantastico|ottimo|benissimo|evviva|felice|che bello|perfetto|great|awesome|wonderful|happy|genial|estupendo|feliz|génial|super|heureux|parfait)/i,
  };

  class Director {
    constructor(avatar) { this.a = avatar; }

    react(text) {
      const a = this.a, s = String(text || "").toLowerCase().trim();
      if (!s) return;
      a.visemes.say(s);
      const head = s.slice(0, 80);
      if (RULES.greet.test(head)) a.play("saluto");
      else if (RULES.deny.test(head)) a.play("disaccordo");
      else if (RULES.agree.test(head)) a.play("annuisce");
      if (RULES.sad.test(s)) a.express("sad", 3);
      else if (RULES.surprise.test(s)) a.express("surprise", 2.5);
      else if (RULES.happy.test(s)) a.express("smile", 3);
      if (/\?\s*$/.test(s)) a.animator.play("sopracciglio");
      if (a.framing) a.framing.suggest(s.length > 160 ? "primo_piano" : s.length > 70 ? "mezzo" : "intera");
    }
  }

  H.Director = Director;
})(window.Nuxiva3D);
