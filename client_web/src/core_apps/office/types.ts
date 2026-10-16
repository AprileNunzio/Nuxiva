export interface DocumentEntry {
  readonly id: string;
  readonly title: string;
  readonly kind: string;
  readonly created: number;
  readonly request: string;
  readonly files: readonly string[];
  readonly summary: string;
  readonly preview?: string;
  readonly seconds?: number;
}

export interface ConversionRecipe {
  readonly conversion: string;
  readonly steps: string;
  readonly uses: number;
  readonly avg_s: number | null;
  readonly last_ok: number | null;
}

export interface DocumentsOverview {
  readonly items: readonly DocumentEntry[];
  readonly root: string;
  readonly office: boolean;
  readonly recipes: readonly ConversionRecipe[];
}
