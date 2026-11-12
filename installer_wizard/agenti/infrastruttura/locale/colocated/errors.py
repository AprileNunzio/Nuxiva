class I18nError(Exception):
    status_code = 500
    code = "i18n_error"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class ScopeRejected(I18nError):
    status_code = 400
    code = "i18n_scope_rejected"


class ScopeForbidden(I18nError):
    status_code = 403
    code = "i18n_scope_forbidden"


class LocaleRejected(I18nError):
    status_code = 400
    code = "i18n_locale_rejected"


class BundleNotFound(I18nError):
    status_code = 404
    code = "i18n_bundle_not_found"


class BundleCorrupted(I18nError):
    status_code = 500
    code = "i18n_bundle_corrupted"


class BundleUnreadable(I18nError):
    status_code = 503
    code = "i18n_bundle_unreadable"
