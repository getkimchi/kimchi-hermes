"""Kimchi harness ACP provider profile (external process over stdio).

Layer 2: Hermes spawns `kimchi --mode acp --yolo` — YOLO is the user-approved
default permission mode (no approval prompts inside the harness). The escape
hatch to run WITHOUT YOLO is `KIMCHI_ACP_ARGS="--mode acp"`; note that an
EMPTY env var falls back to `process_args` below rather than clearing args.

The subprocess owns its own auth (Kimchi's credential store); Hermes never
handles an API key on this path.
"""

from providers import register_provider
from providers.base import ProviderProfile

kimchi_acp = ProviderProfile(
    name="kimchi-acp",
    aliases=("kimchi-agent",),
    display_name="Kimchi (Harness via ACP)",
    description="Kimchi coding harness (kimchi.dev) driven over ACP stdio",
    api_mode="chat_completions",  # ACP subprocess uses chat_completions routing
    env_vars=(),  # managed by the ACP subprocess
    base_url="acp://kimchi",  # ACP internal scheme
    auth_type="external_process",
    # How to launch the harness; KIMCHI_ACP_ARGS lets users override the argv
    # tail (e.g. drop --yolo). See module docstring for the empty-string trap.
    process_command="kimchi",
    process_args=("--mode", "acp", "--yolo"),
    process_command_env_vars=("KIMCHI_ACP_COMMAND",),
    process_args_env_var="KIMCHI_ACP_ARGS",
)

register_provider(kimchi_acp)
