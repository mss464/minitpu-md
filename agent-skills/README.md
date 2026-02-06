# Agent Skills Directory

This directory contains specialized skills for AI coding agents (Antigravity, Claude Code, GitHub Copilot).

## Structure Standard

We follow the **Centralized Mirrored & Nested** standard for maximum compatibility and extensibility.

### Pattern

```text
agent-skills/
└── <domain>/                # Functionality area (mirrors ./asic, ./tpu, etc.)
    └── <verb-skill-name>/   # Specific action (e.g., synthesize, deploy, test)
        ├── SKILL.md         # Instructions (Context Logic)
        ├── scripts/         # Executable helpers (Tools)
        └── templates/       # Reusable assets (Data)
```

### Why this structure?

1.  **Modularity**: Each skill is a self-contained package.
2.  **Portability**: Supported by Claude Code (`.claude/skills`), VS Code, and others.
3.  **Discovery**: Agents can traverse `domain -> action` to find the right tool.
4.  **Encapsulation**: Helper scripts live *inside* the skill folder, not polluting the main codebase.

## Available Skills

| Domain | Skill | Description | Location | Status |
|--------|-------|-------------|----------|--------|
| **Ultra96-v2** | `validate` | Build bitstream & run board tests | `ultra96-v2/validate/` | ✅ Active |
| **ASIC** | `synthesize` | Synthesis & Tapeout Flow (OpenROAD) | `asic/synthesize/` | 🔄 Planned |
| **FPGA** | `deploy` | Vivado Bitstream & IP Packaging | `fpga/deploy/` | 🔄 Planned |
| **TPU** | `design` | RTL Core Development Rules | `tpu/design/` | 🔄 Planned |
| **Tests** | `validate` | Verification & Testbench Execution | `tests/validate/` | 🔄 Planned |
| **Software** | `develop` | Compiler & Runtime Stack work | `software/develop/` | 🔄 Planned |

## Resources

- [Agent Skills Open Standard](https://github.com/microsoft/agent-skills-standard) (Conceptual)
- [Claude Code Documentation](https://docs.anthropic.com/claude/docs/agents)
- [Context Engineering Patterns](https://www.context.engineering/)
