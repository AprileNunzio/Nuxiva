export interface GoogleService {
  readonly id: string;
  readonly name: string;
  readonly icon: string;
  readonly workspace: boolean;
}

export interface GooglePerson {
  readonly slug: string;
  readonly name: string;
  readonly role: string;
  readonly linked: boolean;
  readonly email: string;
  readonly granted: readonly string[];
  readonly status: string;
  readonly unread: number | null;
}

export interface GoogleOverview {
  readonly enabled: boolean;
  readonly has_credentials: boolean;
  readonly redirect_uri: string;
  readonly default_services: readonly string[];
  readonly services: readonly GoogleService[];
  readonly people: readonly GooglePerson[];
  readonly pending: readonly { readonly slug: string; readonly expires_in: number }[];
}

export type GooglePreview = Readonly<Record<string, readonly Readonly<Record<string, unknown>>[]>>;
