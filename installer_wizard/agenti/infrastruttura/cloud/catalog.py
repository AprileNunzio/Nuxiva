from dataclasses import dataclass, field


@dataclass(frozen=True)
class Provider:
    id: str
    name: str
    base_url: str
    kind: str = "openai"
    key_url: str = ""
    auth: str = "bearer"
    needs_url: bool = False
    key_optional: bool = False
    json_mode: bool = True
    token_param: str = "max_tokens"
    reasoning: bool = False
    models: tuple = field(default_factory=tuple)
    notes: str = ""


PROVIDERS = [
    Provider("openai", "OpenAI", "https://api.openai.com/v1", key_url="https://platform.openai.com/api-keys",
             token_param="max_completion_tokens", reasoning=True,
             models=("gpt-6.2-astra", "gpt-6.2-sol", "gpt-6.1-terra", "gpt-6-luna"),
             notes="GPT e modelli di ragionamento o-series."),
    Provider("anthropic", "Anthropic Claude", "https://api.anthropic.com/v1", kind="anthropic",
             key_url="https://console.anthropic.com/settings/keys", reasoning=True, json_mode=False,
             models=("claude-fable-5-2", "claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5"),
             notes="Claude, con ragionamento esteso opzionale."),
    Provider("gemini", "Google Gemini", "https://generativelanguage.googleapis.com/v1beta/openai",
             key_url="https://aistudio.google.com/apikey", reasoning=True,
             models=("gemini-4-carbon", "gemini-4-argon", "gemini-4-neon", "gemini-4-hydrogen", "gemini-3.8-flash",
                     "gemini-3.6-flash", "gemini-3.1-pro-preview", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite",
                     "gemini-3-flash-preview", "gemma-4-31b-it", "gemma-4-26b-a4b-it"),
             notes="Gemini tramite l'endpoint compatibile OpenAI di Google."),
    Provider("xai", "xAI Grok", "https://api.x.ai/v1", key_url="https://console.x.ai", reasoning=True,
             models=("grok-4.7", "grok-4.20")),
    Provider("mistral", "Mistral AI", "https://api.mistral.ai/v1", key_url="https://console.mistral.ai/api-keys",
             models=("mistral-large-4", "mistral-small-2603", "codestral-2508")),
    Provider("deepseek", "DeepSeek", "https://api.deepseek.com/v1", key_url="https://platform.deepseek.com/api_keys",
             models=("deepseek-flash", "deepseek-v4-pro")),
    Provider("groq", "Groq", "https://api.groq.com/openai/v1", key_url="https://console.groq.com/keys",
             models=("openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"),
             notes="Inferenza velocissima su hardware LPU."),
    Provider("cerebras", "Cerebras", "https://api.cerebras.ai/v1", key_url="https://cloud.cerebras.ai",
             models=("gpt-oss-120b", "qwen-3.8-27b")),
    Provider("openrouter", "OpenRouter", "https://openrouter.ai/api/v1", key_url="https://openrouter.ai/keys",
             models=("openrouter/auto",), notes="Un'unica chiave per centinaia di modelli di ogni fornitore."),
    Provider("together", "Together AI", "https://api.together.xyz/v1", key_url="https://api.together.ai/settings/api-keys",
             models=("meta-llama/Llama-3.3-70B-Instruct-Turbo", "deepseek-ai/DeepSeek-V3",
                     "Qwen/Qwen2.5-72B-Instruct-Turbo")),
    Provider("fireworks", "Fireworks AI", "https://api.fireworks.ai/inference/v1",
             key_url="https://fireworks.ai/account/api-keys",
             models=("accounts/fireworks/models/llama-v3p3-70b-instruct", "accounts/fireworks/models/deepseek-v3")),
    Provider("perplexity", "Perplexity", "https://api.perplexity.ai", key_url="https://www.perplexity.ai/settings/api",
             json_mode=False, models=("sonar", "sonar-pro", "sonar-reasoning-pro", "sonar-deep-research"),
             notes="Risposte con ricerca sul web aggiornata."),
    Provider("cohere", "Cohere", "https://api.cohere.ai/compatibility/v1", key_url="https://dashboard.cohere.com/api-keys",
             models=("command-a-03-2025", "command-r-plus", "command-r")),
    Provider("qwen", "Alibaba Qwen (DashScope)", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
             key_url="https://modelstudio.console.alibabacloud.com", models=("qwen-max", "qwen-plus", "qwen-turbo")),
    Provider("moonshot", "Moonshot Kimi", "https://api.moonshot.ai/v1", key_url="https://platform.moonshot.ai",
             models=("kimi-k2-0905-preview", "moonshot-v1-32k")),
    Provider("zhipu", "Zhipu GLM", "https://api.z.ai/api/paas/v4", key_url="https://z.ai/manage-apikey/apikey-list",
             models=("glm-4.6", "glm-4.5", "glm-4.5-air")),
    Provider("nvidia", "NVIDIA NIM", "https://integrate.api.nvidia.com/v1", key_url="https://build.nvidia.com",
             models=("meta/llama-3.3-70b-instruct", "nvidia/llama-3.1-nemotron-70b-instruct")),
    Provider("huggingface", "Hugging Face", "https://router.huggingface.co/v1",
             key_url="https://huggingface.co/settings/tokens", models=("meta-llama/Llama-3.3-70B-Instruct",)),
    Provider("sambanova", "SambaNova", "https://api.sambanova.ai/v1", key_url="https://cloud.sambanova.ai/apis",
             models=("Meta-Llama-3.3-70B-Instruct", "DeepSeek-V3-0324")),
    Provider("deepinfra", "DeepInfra", "https://api.deepinfra.com/v1/openai", key_url="https://deepinfra.com/dash/api_keys",
             models=("meta-llama/Llama-3.3-70B-Instruct",)),
    Provider("ai21", "AI21 Labs", "https://api.ai21.com/studio/v1", key_url="https://studio.ai21.com/account/api-key",
             models=("jamba-large", "jamba-mini")),
    Provider("upstage", "Upstage Solar", "https://api.upstage.ai/v1", key_url="https://console.upstage.ai/api-keys",
             models=("solar-pro2", "solar-mini")),
    Provider("minimax", "MiniMax", "https://api.minimax.io/v1", key_url="https://www.minimax.io/platform",
             models=("MiniMax-M2",)),
    Provider("stepfun", "StepFun", "https://api.stepfun.com/v1", key_url="https://platform.stepfun.com"),
    Provider("siliconflow", "SiliconFlow", "https://api.siliconflow.com/v1", key_url="https://cloud.siliconflow.com/account/ak"),
    Provider("novita", "Novita AI", "https://api.novita.ai/v3/openai", key_url="https://novita.ai/settings/key-management"),
    Provider("hyperbolic", "Hyperbolic", "https://api.hyperbolic.xyz/v1", key_url="https://app.hyperbolic.xyz/settings"),
    Provider("nebius", "Nebius AI Studio", "https://api.studio.nebius.com/v1", key_url="https://studio.nebius.com/settings/api-keys"),
    Provider("lambda", "Lambda Inference", "https://api.lambda.ai/v1", key_url="https://cloud.lambda.ai/api-keys"),
    Provider("scaleway", "Scaleway Generative APIs", "https://api.scaleway.ai/v1",
             key_url="https://console.scaleway.com/iam/api-keys"),
    Provider("ovhcloud", "OVHcloud AI Endpoints", "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1",
             key_url="https://endpoints.ai.cloud.ovh.net"),
    Provider("github", "GitHub Models", "https://models.github.ai/inference", key_url="https://github.com/settings/tokens"),
    Provider("vercel", "Vercel AI Gateway", "https://ai-gateway.vercel.sh/v1", key_url="https://vercel.com/dashboard/ai-gateway"),
    Provider("venice", "Venice AI", "https://api.venice.ai/api/v1", key_url="https://venice.ai/settings/api"),
    Provider("chutes", "Chutes", "https://llm.chutes.ai/v1", key_url="https://chutes.ai/app/api"),
    Provider("baidu", "Baidu Qianfan (ERNIE)", "https://qianfan.baidubce.com/v2",
             key_url="https://console.bce.baidu.com/iam/#/iam/apikey/list"),
    Provider("tencent", "Tencent Hunyuan", "https://api.hunyuan.cloud.tencent.com/v1",
             key_url="https://console.cloud.tencent.com/hunyuan/api-key"),
    Provider("volcengine", "ByteDance Doubao (Volcengine Ark)", "https://ark.cn-beijing.volces.com/api/v3",
             key_url="https://console.volcengine.com/ark"),
    Provider("cloudflare", "Cloudflare Workers AI", "", needs_url=True, key_url="https://dash.cloudflare.com/profile/api-tokens",
             notes="https://api.cloudflare.com/client/v4/accounts/ACCOUNT_ID/ai/v1"),
    Provider("bedrock", "Amazon Bedrock", "", needs_url=True, key_url="https://console.aws.amazon.com/bedrock",
             notes="https://bedrock-runtime.REGION.amazonaws.com/openai/v1"),
    Provider("azure", "Azure OpenAI", "", auth="api-key", needs_url=True, token_param="max_completion_tokens",
             reasoning=True, key_url="https://portal.azure.com",
             notes="Indirizzo della risorsa, es. https://nome.openai.azure.com/openai/v1"),
    Provider("custom", "Compatibile OpenAI (LM Studio, vLLM, LocalAI, Ollama remoto)", "", needs_url=True,
             key_optional=True, notes="Qualsiasi server con API /v1/chat/completions."),
]

BY_ID = {p.id: p for p in PROVIDERS}

OPTION_CHOICES = {
    "temperature": ["", "0", "0.2", "0.4", "0.6", "0.8", "1.0", "1.2"],
    "top_p": ["", "0.5", "0.8", "0.9", "0.95", "1.0"],
    "max_tokens": ["", "256", "512", "1024", "2048", "4096", "8192", "16384", "32768"],
    "reasoning": ["", "minimal", "low", "medium", "high"],
    "timeout": ["30", "60", "120", "240"],
}

REASONING_BUDGET = {"minimal": 1024, "low": 2048, "medium": 8192, "high": 24576}

PREFIX = "cloud:"

RETIRED = {
    "openai": {"gpt-5": "gpt-6.2-sol", "gpt-5-mini": "gpt-6.1-terra", "gpt-5-nano": "gpt-6-luna", "gpt-5-pro": "gpt-6.2-astra",
               "o3": "gpt-6.2-sol", "o3-pro": "gpt-6.2-astra", "o3-mini": "gpt-6.2-sol", "o4-mini": "gpt-6.1-terra",
               "o1": "gpt-6.2-sol", "o1-pro": "gpt-6.2-astra", "gpt-4": "gpt-6.2-sol", "gpt-4-turbo": "gpt-6.2-sol",
               "gpt-3.5-turbo": "gpt-6.1-terra", "gpt-4.1-nano": "gpt-6-luna", "gpt-oss-120b": "gpt-6.1-terra"},
    "anthropic": {"claude-sonnet-4-5": "claude-sonnet-5-5", "claude-sonnet-4-5-20250929": "claude-sonnet-5-5",
                  "claude-opus-4-5": "claude-opus-5-5", "claude-opus-4-5-20251101": "claude-opus-5-5"},
    "gemini": {"gemini-2.5-pro": "gemini-3.8-flash", "gemini-3.5-flash": "gemini-3.6-flash", "gemini-3.1-pro": "gemini-3.1-pro-preview",
               "gemini-3-pro-preview": "gemini-3.1-pro-preview", "gemini-3.1-flash-lite-preview": "gemini-3.1-flash-lite",
               "gemini-3.8-live": "gemini-3.8-flash"},
    "xai": {"grok-3": "grok-4.7", "grok-4-0709": "grok-4.7", "grok-4-fast-reasoning": "grok-4.7",
            "grok-4-fast-non-reasoning": "grok-4.7", "grok-4-1-fast-reasoning": "grok-4.7",
            "grok-4-1-fast-non-reasoning": "grok-4.7", "grok-code-fast-1": "grok-4.7"},
    "mistral": {"mistral-medium-2508": "mistral-large-4", "mistral-small-2506": "mistral-small-2603",
                "magistral-medium-2509": "mistral-large-4", "magistral-small-2509": "mistral-small-2603",
                "codestral-2501": "codestral-2508"},
    "deepseek": {"deepseek-chat": "deepseek-flash", "deepseek-reasoner": "deepseek-flash", "deepseek-v3": "deepseek-flash",
                 "deepseek-v4-flash": "deepseek-flash"},
    "cerebras": {"llama-3.3-70b": "gpt-oss-120b", "qwen-3-32b": "gpt-oss-120b", "llama3.1-8b": "gpt-oss-120b",
                 "gemma-4-31b": "qwen-3.8-27b"},
    "groq": {"llama-3.3-70b-versatile": "openai/gpt-oss-120b", "llama-3.1-8b-instant": "openai/gpt-oss-20b",
             "qwen/qwen3-32b": "openai/gpt-oss-120b", "qwen/qwen3.6-27b": "qwen/qwen3.8-27b"},
}


def current_model(provider: str, model: str) -> str:
    return RETIRED.get(provider, {}).get(model, model)


SERVER = "srv-"
FLAVORS = {"ollama": "Ollama", "openai": "Compatibile OpenAI", "studio": "Studio di modelli locale"}


def server_provider(pid: str, entry: dict) -> Provider:
    flavor = entry.get("flavor", "ollama")
    return Provider(pid, entry.get("name") or pid, "", needs_url=True, key_optional=True,
                    notes=f"{FLAVORS.get(flavor, flavor)} · {entry.get('root', '')}")


def sync_servers(data: dict) -> None:
    for pid in [p for p in BY_ID if p.startswith(SERVER) and p not in data]:
        del BY_ID[pid]
    for pid, entry in data.items():
        if pid.startswith(SERVER):
            BY_ID[pid] = server_provider(pid, entry)


def is_server(pid: str) -> bool:
    return pid.startswith(SERVER)


def parse_ref(ref: str) -> tuple[str, str]:
    body = ref.removeprefix(PREFIX)
    provider, _, model = body.partition("/")
    if provider not in BY_ID and is_server(provider):
        from agenti.cloud.vault import vault
        vault.get(provider)
    if provider not in BY_ID or not model:
        raise ValueError(f"riferimento cloud non valido: {ref}")
    return provider, current_model(provider, model)


def make_ref(provider: str, model: str) -> str:
    return f"{PREFIX}{provider}/{model}"


def is_cloud(ref: str) -> bool:
    return ref.startswith(PREFIX)
