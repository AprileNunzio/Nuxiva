from textwrap import dedent


def _clean(text: str) -> str:
    return dedent(text).lstrip("\n")


def php_site(name: str) -> dict:
    return {
        "public/index.php": _clean("""
            <?php
            declare(strict_types=1);

            require __DIR__ . '/../src/bootstrap.php';

            App\\Core\\Kernel::run();
        """),
        "public/.htaccess": "RewriteEngine On\nRewriteCond %{REQUEST_FILENAME} !-f\nRewriteRule ^ index.php [L]\nOptions -Indexes\n",
        "src/bootstrap.php": _clean("""
            <?php
            declare(strict_types=1);

            spl_autoload_register(static function (string $class): void {
                $path = dirname(__DIR__) . '/src/' . str_replace(['App\\\\', '\\\\'], ['', '/'], $class) . '.php';
                if (is_file($path)) {
                    require $path;
                }
            });

            App\\Core\\ErrorHandler::register();
            App\\Core\\Session::start();
            App\\Core\\Headers::send();
        """),
        "src/Core/ErrorHandler.php": _clean("""
            <?php
            declare(strict_types=1);

            namespace App\\Core;

            final class ErrorHandler
            {
                public static function register(): void
                {
                    set_error_handler(static function (int $level, string $message, string $file, int $line): bool {
                        throw new \\ErrorException($message, 0, $level, $file, $line);
                    });
                    set_exception_handler(static function (\\Throwable $error): void {
                        error_log($error::class . ': ' . $error->getMessage());
                        http_response_code($error instanceof HttpError ? $error->status : 500);
                        header('Content-Type: text/plain; charset=utf-8');
                        echo $error instanceof HttpError ? $error->getMessage() : 'error';
                    });
                }
            }
        """),
        "src/Core/HttpError.php": _clean("""
            <?php
            declare(strict_types=1);

            namespace App\\Core;

            final class HttpError extends \\RuntimeException
            {
                public function __construct(string $message, public readonly int $status)
                {
                    parent::__construct($message);
                }
            }
        """),
        "src/Core/Session.php": _clean("""
            <?php
            declare(strict_types=1);

            namespace App\\Core;

            final class Session
            {
                public static function start(): void
                {
                    session_set_cookie_params(['httponly' => true, 'secure' => !empty($_SERVER['HTTPS']), 'samesite' => 'Strict']);
                    session_start();
                }
            }
        """),
        "src/Core/Headers.php": _clean("""
            <?php
            declare(strict_types=1);

            namespace App\\Core;

            final class Headers
            {
                public static function send(): void
                {
                    header("Content-Security-Policy: default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'");
                    header('X-Content-Type-Options: nosniff');
                    header('Referrer-Policy: no-referrer');
                    header('Permissions-Policy: camera=(), microphone=(), geolocation=()');
                    header('Cross-Origin-Opener-Policy: same-origin');
                }
            }
        """),
        "src/Core/Csrf.php": _clean("""
            <?php
            declare(strict_types=1);

            namespace App\\Core;

            final class Csrf
            {
                public static function token(): string
                {
                    return $_SESSION['csrf'] ??= bin2hex(random_bytes(32));
                }

                public static function verify(?string $sent): void
                {
                    if (!is_string($sent) || !hash_equals(self::token(), $sent)) {
                        throw new HttpError('forbidden', 403);
                    }
                }
            }
        """),
        "src/Core/Lang.php": _clean("""
            <?php
            declare(strict_types=1);

            namespace App\\Core;

            final class Lang
            {
                private const SUPPORTED = ['it', 'en'];

                public static function current(): string
                {
                    $asked = substr((string) ($_GET['lang'] ?? $_SESSION['lang'] ?? $_SERVER['HTTP_ACCEPT_LANGUAGE'] ?? 'it'), 0, 2);
                    return $_SESSION['lang'] = in_array($asked, self::SUPPORTED, true) ? $asked : 'it';
                }

                public static function load(string $page): array
                {
                    $file = dirname(__DIR__, 2) . '/pages/' . $page . '/lang/' . self::current() . '.php';
                    return is_file($file) ? require $file : [];
                }
            }
        """),
        "src/Core/View.php": _clean("""
            <?php
            declare(strict_types=1);

            namespace App\\Core;

            final class View
            {
                public static function render(string $page, array $data = []): void
                {
                    $t = Lang::load($page);
                    $lang = Lang::current();
                    $csrf = Csrf::token();
                    $e = static fn (mixed $value): string => htmlspecialchars((string) $value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
                    extract($data, EXTR_SKIP);
                    require dirname(__DIR__, 2) . '/pages/' . $page . '/view.phtml';
                }
            }
        """),
        "src/Core/Kernel.php": _clean("""
            <?php
            declare(strict_types=1);

            namespace App\\Core;

            final class Kernel
            {
                private const PAGES = ['' => 'home', 'home' => 'home'];

                public static function run(): void
                {
                    $path = trim((string) parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH), '/');
                    if (preg_match('#^assets/([a-z0-9-]+)\\\\.css$#', $path, $match) && in_array($match[1], self::PAGES, true)) {
                        header('Content-Type: text/css; charset=utf-8');
                        readfile(dirname(__DIR__, 2) . '/pages/' . $match[1] . '/style.css');
                        return;
                    }
                    $page = self::PAGES[$path] ?? throw new HttpError('not found', 404);
                    $controller = require dirname(__DIR__, 2) . '/pages/' . $page . '/controller.php';
                    View::render($page, $controller());
                }
            }
        """),
        "pages/home/controller.php": _clean("""
            <?php
            declare(strict_types=1);

            return static fn (): array => ['title' => 'home'];
        """),
        "pages/home/view.phtml": _clean("""
            <!doctype html>
            <html lang="<?= $e($lang) ?>">
            <head>
              <meta charset="utf-8">
              <meta name="viewport" content="width=device-width, initial-scale=1">
              <title><?= $e($t['title']) ?></title>
              <link rel="stylesheet" href="/assets/home.css">
            </head>
            <body>
              <main>
                <h1><?= $e($t['heading']) ?></h1>
                <p><?= $e($t['intro']) ?></p>
              </main>
            </body>
            </html>
        """),
        "pages/home/style.css": _clean("""
            :root { color-scheme: light dark; }
            * { box-sizing: border-box; }
            body { margin: 0; font-family: system-ui, sans-serif; line-height: 1.5; }
            main { max-width: 60rem; margin: 0 auto; padding: 2rem 1rem; }
            @media (min-width: 48rem) { main { padding: 4rem 2rem; } }
        """),
        "pages/home/lang/it.php": f"<?php\ndeclare(strict_types=1);\n\nreturn ['title' => '{name}', 'heading' => '{name}', 'intro' => 'Benvenuto'];\n",
        "pages/home/lang/en.php": f"<?php\ndeclare(strict_types=1);\n\nreturn ['title' => '{name}', 'heading' => '{name}', 'intro' => 'Welcome'];\n",
        ".gitignore": "*.log\n.env\n",
    }
