#!/usr/bin/env python3
"""Hide the Droidspaces-required SYSVIPC=y from VINTF config_data."""

import re
import sys
from pathlib import Path


path = Path(sys.argv[1])
text = path.read_text()

if "define droidspaces_vintf_config_fix" not in text:
    marker = "filechk_cat = cat $<"
    if marker not in text:
        raise SystemExit(f"未找到 Makefile 标记: {marker}")

    block = r'''define droidspaces_vintf_config_fix
	echo "kernel: Checking config_data for CONFIG_SYSVIPC..."; \
	if grep -q '^CONFIG_SYSVIPC=y' $@; then \
		echo "kernel: Found CONFIG_SYSVIPC=y - modifying exported config_data to 'n'"; \
		sed -i 's/^CONFIG_SYSVIPC=y$$/CONFIG_SYSVIPC=n/' $@; \
		echo "kernel: Successfully modified CONFIG_SYSVIPC display in config_data"; \
	fi; \
	echo "kernel: Final CONFIG_SYSVIPC value in config_data:"; \
	grep '^CONFIG_SYSVIPC=' $@ || echo "kernel: (not present)"
endef'''
    text = text.replace(marker, marker + "\n\n" + block, 1)

rule = re.compile(
    r'(^\$\(obj\)/config_data:[^\n]*FORCE\n\t\$\(call filechk,cat\))',
    re.MULTILINE,
)
match = rule.search(text)
if not match:
    if "$(Q)$(droidspaces_vintf_config_fix)" not in text:
        raise SystemExit("未找到 config_data 生成规则")
else:
    text = text[: match.end()] + "\n\t$(Q)$(droidspaces_vintf_config_fix)" + text[match.end() :]

path.write_text(text)
print(f"已注入 VINTF config_data 修复: {path}")
