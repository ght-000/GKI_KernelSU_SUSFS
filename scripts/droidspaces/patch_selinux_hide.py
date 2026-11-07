#!/usr/bin/env python3
"""Bridge KernelSU selinux_hide backup policy to SELinux access decision queries."""

import sys
from pathlib import Path

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()

# 1. Update KernelSU selinux_hide.c to default enabled and guard against NULL backup_sepolicy
ksu_hide_candidates = [
    root / "KernelSU" / "kernel" / "feature" / "selinux_hide.c",
    root / "common" / "drivers" / "kernelsu" / "feature" / "selinux_hide.c",
]
hide_file = next((f for f in ksu_hide_candidates if f.is_file()), None)
if hide_file:
    content = hide_file.read_text(encoding="utf-8")
    if "bool ksu_selinux_hide_enabled __read_mostly = false;" in content:
        content = content.replace(
            "bool ksu_selinux_hide_enabled __read_mostly = false;",
            "bool ksu_selinux_hide_enabled __read_mostly = true;",
        )
    if "static bool ksu_selinux_hide_enabled __read_mostly = false;" in content:
        content = content.replace(
            "static bool ksu_selinux_hide_enabled __read_mostly = false;",
            "static bool ksu_selinux_hide_enabled __read_mostly = true;",
        )

    # Ensure my_write_context guards against NULL backup_sepolicy
    if "if (!backup_sepolicy)\n        return -EINVAL;" not in content:
        content = content.replace(
            "ssize_t my_write_context(struct file *file, char *buf, size_t size)\n{\n    char *canon = NULL;\n",
            "ssize_t my_write_context(struct file *file, char *buf, size_t size)\n{\n    char *canon = NULL;\n    if (!backup_sepolicy)\n        return -EINVAL;\n",
        )
        content = content.replace(
            "ssize_t my_write_access(struct file *file, char *buf, size_t size)\n{\n    char *scon = NULL, *tcon = NULL;\n",
            "ssize_t my_write_access(struct file *file, char *buf, size_t size)\n{\n    char *scon = NULL, *tcon = NULL;\n    if (!backup_sepolicy)\n        return -EINVAL;\n",
        )
        content = content.replace(
            "int my_setprocattr(const char *name, void *value, size_t size)\n{\n",
            "int my_setprocattr(const char *name, void *value, size_t size)\n{\n    if (!backup_sepolicy)\n        return -EINVAL;\n",
        )

    hide_file.write_text(content, encoding="utf-8")
    print(f"Patched selinux_hide: {hide_file}")

# 2. Update KernelSU rules.c to activate selinux_hide as soon as backup_sepolicy is duplicated
ksu_rules_candidates = [
    root / "KernelSU" / "kernel" / "selinux" / "rules.c",
    root / "common" / "drivers" / "kernelsu" / "selinux" / "rules.c",
]
rules_file = next((f for f in ksu_rules_candidates if f.is_file()), None)
if rules_file:
    content = rules_file.read_text(encoding="utf-8")
    if "extern bool ksu_selinux_hide_enabled;" not in content:
        content = content.replace(
            "struct selinux_policy *backup_sepolicy;",
            "struct selinux_policy *backup_sepolicy;\nextern bool ksu_selinux_hide_enabled;\nextern bool ksu_selinux_hide_running;",
        )

    marker = "backup sepolicy success!"
    if "ksu_selinux_hide_running = true;" not in content:
        lines = content.splitlines(keepends=True)
        new_lines = []
        for line in lines:
            new_lines.append(line)
            if marker in line:
                indent = " " * (len(line) - len(line.lstrip()))
                new_lines.append(f"{indent}if (ksu_selinux_hide_enabled) {{\n")
                new_lines.append(f"{indent}    ksu_selinux_hide_running = true;\n")
                new_lines.append(f"{indent}}}\n")
        content = "".join(new_lines)

    rules_file.write_text(content, encoding="utf-8")
    print(f"Patched rules: {rules_file}")

# 3. Update security/selinux/hooks.c to forward access/context/setprocattr through backup_sepolicy
hooks_file = root / "common" / "security" / "selinux" / "hooks.c"
if hooks_file.is_file():
    content = hooks_file.read_text(encoding="utf-8")
    decls = (
        "extern bool ksu_selinux_hide_running __read_mostly;\n"
        "extern ssize_t my_write_context(struct file *file, char *buf, size_t size);\n"
        "extern ssize_t my_write_access(struct file *file, char *buf, size_t size);\n"
        "extern int my_setprocattr(const char *name, void *value, size_t size);\n"
        "extern struct selinux_policy *backup_sepolicy;"
    )
    if "extern bool ksu_selinux_hide_running __read_mostly;" in content and "my_write_context" not in content:
        content = content.replace("extern bool ksu_selinux_hide_running __read_mostly;", decls)

    target_setprocattr = "return susfs_selinux_setprocattr(name, value, size);"
    if target_setprocattr in content:
        content = content.replace(
            target_setprocattr,
            "if (backup_sepolicy) return my_setprocattr(name, value, size); return susfs_selinux_setprocattr(name, value, size);",
        )
    target_write_context = "return susfs_sel_write_context(file, buf, size);"
    if target_write_context in content:
        content = content.replace(
            target_write_context,
            "if (backup_sepolicy) return my_write_context(file, buf, size); return susfs_sel_write_context(file, buf, size);",
        )
    target_write_access = "return susfs_sel_write_access(file, buf, size);"
    if target_write_access in content:
        content = content.replace(
            target_write_access,
            "if (backup_sepolicy) return my_write_access(file, buf, size); return susfs_sel_write_access(file, buf, size);",
        )
    hooks_file.write_text(content, encoding="utf-8")
    print(f"Patched hooks: {hooks_file}")
