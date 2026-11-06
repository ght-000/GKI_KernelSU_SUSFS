#!/usr/bin/env python3
"""Sanitize VINTF config_data for Android 14 FCM compatibility."""

import re
import sys
from pathlib import Path


path = Path(sys.argv[1])
text = path.read_text()

block = r'''define droidspaces_vintf_config_fix
	@echo "kernel: Sanitizing config_data for Android 14 FCM compatibility..."; \
	sed -i 's/^CONFIG_SYSVIPC=y$$/# CONFIG_SYSVIPC is not set/' $@; \
	sed -i 's/^CONFIG_IP6_NF_NAT=y$$/# CONFIG_IP6_NF_NAT is not set/' $@; \
	sed -i 's/^CONFIG_IP6_NF_TARGET_MASQUERADE=y$$/# CONFIG_IP6_NF_TARGET_MASQUERADE is not set/' $@; \
	sed -i 's/^CONFIG_MACVLAN=y$$/# CONFIG_MACVLAN is not set/' $@; \
	sed -i 's/^CONFIG_KSU=y$$/# CONFIG_KSU is not set/' $@; \
	sed -i 's/^CONFIG_KPM=y$$/# CONFIG_KPM is not set/' $@; \
	sed -i 's/^CONFIG_REKERNEL=y$$/# CONFIG_REKERNEL is not set/' $@; \
	sed -i 's/^CONFIG_REKERNEL_NETWORK=y$$/# CONFIG_REKERNEL_NETWORK is not set/' $@; \
	sed -i '/^CONFIG_KSU_/d' $@; \
	sed -i '/^CONFIG_SUSFS/d' $@; \
	echo "kernel: VINTF config_data sanitize complete"
endef'''

if "define droidspaces_vintf_config_fix" not in text:
    marker = "filechk_cat = cat $<"
    if marker not in text:
        raise SystemExit(f"未找到 Makefile 标记: {marker}")
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
