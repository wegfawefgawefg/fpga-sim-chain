# Editor Setup (VSCode)

This repo includes a local SHDL formatter and a local VSCode syntax highlighter.

## SHDL Syntax Highlighting
Install the local VSCode extension:

```bash
code --install-extension ./tools/vscode-shdl/shdl-syntax-0.0.1.vsix
```

Then reload VSCode and make sure the language mode is `SHDL`.

## Format on Save (SHDL)
The repo includes `scripts/format_shdl.py` and a Run On Save config in `.vscode/settings.json`.

If you installed the **Run On Save** extension (`emeraldwalk.runonsave`), saving a `.shdl` file will run:

```bash
PYTHONPATH=src .venv/bin/python scripts/format_shdl.py <file>
```

You can also run it manually:

```bash
PYTHONPATH=src .venv/bin/python scripts/format_shdl.py docs/examples
```

## Notes
- The formatter is simple and rewrites files by parsing SHDL.
- Line comments start with `;`.
