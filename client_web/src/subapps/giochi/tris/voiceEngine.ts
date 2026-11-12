export function parseVoiceMove(raw: string): number | null {
  const text = raw.trim().toLowerCase();

  if (
    (text.includes('alto') && text.includes('sinistra')) ||
    (text.includes('top') && text.includes('left')) ||
    text === 'uno' ||
    text === '1'
  ) {
    return 0;
  }

  if (
    (text.includes('alto') && (text.includes('centro') || text.includes('mezzo'))) ||
    (text.includes('top') && (text.includes('center') || text.includes('middle'))) ||
    text === 'due' ||
    text === '2'
  ) {
    return 1;
  }

  if (
    (text.includes('alto') && text.includes('destra')) ||
    (text.includes('top') && text.includes('right')) ||
    text === 'tre' ||
    text === '3'
  ) {
    return 2;
  }

  if (
    (text.includes('centro') && text.includes('sinistra')) ||
    (text.includes('middle') && text.includes('left')) ||
    text === 'quattro' ||
    text === '4'
  ) {
    return 3;
  }

  if (
    ((text.includes('centro') || text.includes('mezzo')) &&
      !text.includes('alto') &&
      !text.includes('basso') &&
      !text.includes('sinistra') &&
      !text.includes('destra')) ||
    text === 'center' ||
    text === 'middle' ||
    text === 'cinque' ||
    text === '5'
  ) {
    return 4;
  }

  if (
    (text.includes('centro') && text.includes('destra')) ||
    (text.includes('middle') && text.includes('right')) ||
    text === 'sei' ||
    text === '6'
  ) {
    return 5;
  }

  if (
    (text.includes('basso') && text.includes('sinistra')) ||
    (text.includes('bottom') && text.includes('left')) ||
    text === 'sette' ||
    text === '7'
  ) {
    return 6;
  }

  if (
    (text.includes('basso') && (text.includes('centro') || text.includes('mezzo'))) ||
    (text.includes('bottom') && (text.includes('center') || text.includes('middle'))) ||
    text === 'otto' ||
    text === '8'
  ) {
    return 7;
  }

  if (
    (text.includes('basso') && text.includes('destra')) ||
    (text.includes('bottom') && text.includes('right')) ||
    text === 'nove' ||
    text === '9'
  ) {
    return 8;
  }

  return null;
}

export function speakFeedback(text: string, lang = 'it-IT'): void {
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = lang;
  utterance.rate = 1.0;
  window.speechSynthesis.speak(utterance);
}

export function createSpeechRecognizer(
  lang: string,
  onResult: (transcript: string) => void,
  onError: () => void,
  onEnd: () => void
): { start: () => void; stop: () => void } | null {
  if (typeof window === 'undefined') return null;

  const SpeechRecognition =
    (window as unknown as { SpeechRecognition?: any }).SpeechRecognition ||
    (window as unknown as { webkitSpeechRecognition?: any }).webkitSpeechRecognition;

  if (!SpeechRecognition) return null;

  const recognizer = new SpeechRecognition();
  recognizer.lang = lang;
  recognizer.continuous = true;
  recognizer.interimResults = false;

  recognizer.onresult = (event: any) => {
    const lastResult = event.results[event.results.length - 1];
    if (lastResult?.[0]?.transcript) {
      onResult(lastResult[0].transcript);
    }
  };

  recognizer.onerror = () => {
    onError();
  };

  recognizer.onend = () => {
    onEnd();
  };

  return {
    start: () => {
      try {
        recognizer.start();
      } catch {
      }
    },
    stop: () => {
      try {
        recognizer.stop();
      } catch {
      }
    },
  };
}
