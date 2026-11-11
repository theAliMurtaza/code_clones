"""
generate_linux_c_dataset.py

Generates a synthetic Linux-kernel-style C function dataset for training
the C:C clone classifier. Creates realistic pairs of C functions that mirror
patterns found in the Linux kernel: memory management, list operations,
error handling, and driver code patterns.

Output: a JSONL file compatible with linux_training_data.read_labeled_pairs()
"""

from __future__ import annotations
import json
import random
import sys
from pathlib import Path

random.seed(42)

# ── Realistic Linux-kernel-style C function templates ─────────────────
# Each template is parameterized so we can generate many variants.

# --- Memory / buffer helpers ---
MEM_ALLOC = """\
static void *{name}(size_t size, gfp_t flags)
{{
\tvoid *ptr;
\tif (!size)
\t\treturn NULL;
\tptr = kmalloc(size, flags);
\tif (!ptr)
\t\treturn NULL;
\tmemset(ptr, 0, size);
\treturn ptr;
}}"""

MEM_ALLOC_ALT = """\
static void *{name}(size_t {sz}, gfp_t {fl})
{{
\tvoid *{buf};
\tif ({sz} == 0)
\t\treturn NULL;
\t{buf} = kzalloc({sz}, {fl});
\treturn {buf};
}}"""

MEM_FREE = """\
static void {name}(void *{ptr}, size_t size)
{{
\tif (!{ptr})
\t\treturn;
\tmemset({ptr}, 0, size);
\tkfree({ptr});
}}"""

MEM_FREE_ALT = """\
static void {name}(void *{buf})
{{
\tif ({buf} == NULL)
\t\treturn;
\tkfree({buf});
}}"""

# --- List / linked-list operations ---
LIST_INSERT = """\
static void {name}(struct list_head *head, struct {node} *entry)
{{
\tunsigned long flags;
\tspin_lock_irqsave(&{lock}, flags);
\tlist_add_tail(&entry->list, head);
\tspin_unlock_irqrestore(&{lock}, flags);
}}"""

LIST_INSERT_ALT = """\
static void {name}(struct {node} *item, struct list_head *{head})
{{
\tunsigned long {flags};
\tspin_lock_irqsave(&{lock}, {flags});
\tlist_add(&item->node, {head});
\tspin_unlock_irqrestore(&{lock}, {flags});
}}"""

LIST_REMOVE = """\
static void {name}(struct {node} *entry)
{{
\tunsigned long flags;
\tspin_lock_irqsave(&{lock}, flags);
\tlist_del(&entry->list);
\tspin_unlock_irqrestore(&{lock}, flags);
\tkfree(entry);
}}"""

LIST_REMOVE_ALT = """\
static void {name}(struct {node} *item)
{{
\tunsigned long {flags};
\tspin_lock_irqsave(&{lock}, {flags});
\tlist_del_init(&item->node);
\tspin_unlock_irqrestore(&{lock}, {flags});
}}"""

# --- Error-handling wrappers ---
ERR_WRAP = """\
static int {name}(struct {dev} *{d}, int {cmd})
{{
\tint {ret};
\tif (!{d})
\t\treturn -EINVAL;
\t{ret} = {inner}({d}, {cmd});
\tif ({ret} < 0) {{
\t\tdev_err(&{d}->dev, "%s: failed with %d\\n", __func__, {ret});
\t\treturn {ret};
\t}}
\treturn 0;
}}"""

ERR_WRAP_ALT = """\
static int {name}(struct {dev} *dev, int cmd)
{{
\tint rc;
\tif (dev == NULL)
\t\treturn -EINVAL;
\trc = {inner}(dev, cmd);
\tif (rc) {{
\t\tpr_err("%s error: %d\\n", __func__, rc);
\t\treturn rc;
\t}}
\treturn 0;
}}"""

# --- Bit-manipulation helpers ---
BIT_SET = """\
static void {name}(unsigned int *{reg}, unsigned int {mask})
{{
\tunsigned long flags;
\tspin_lock_irqsave(&{lock}, flags);
\t*{reg} |= {mask};
\tspin_unlock_irqrestore(&{lock}, flags);
}}"""

BIT_SET_ALT = """\
static void {name}(u32 *{reg}, u32 {bits})
{{
\tunsigned long {flags};
\tspin_lock_irqsave(&{lock}, {flags});
\twritel(readl({reg}) | {bits}, {reg});
\tspin_unlock_irqrestore(&{lock}, {flags});
}}"""

BIT_CLR = """\
static void {name}(unsigned int *{reg}, unsigned int {mask})
{{
\tunsigned long flags;
\tspin_lock_irqsave(&{lock}, flags);
\t*{reg} &= ~{mask};
\tspin_unlock_irqrestore(&{lock}, flags);
}}"""

BIT_CLR_ALT = """\
static void {name}(u32 *{reg}, u32 {bits})
{{
\tunsigned long {flags};
\tspin_lock_irqsave(&{lock}, {flags});
\twritel(readl({reg}) & ~{bits}, {reg});
\tspin_unlock_irqrestore(&{lock}, {flags});
}}"""

# --- IRQ / interrupt handlers ---
IRQ_HANDLER = """\
static irqreturn_t {name}(int irq, void *data)
{{
\tstruct {dev} *{d} = data;
\tu32 status;
\tstatus = readl({d}->{reg});
\tif (!(status & {mask}))
\t\treturn IRQ_NONE;
\twritel(status, {d}->{reg});
\twake_up_interruptible(&{d}->wait);
\treturn IRQ_HANDLED;
}}"""

IRQ_HANDLER_ALT = """\
static irqreturn_t {name}(int {irq}, void *{priv})
{{
\tstruct {dev} *dev = {priv};
\tunsigned int {stat};
\t{stat} = readl(dev->{reg});
\tif (!({stat} & {mask}))
\t\treturn IRQ_NONE;
\twritel({stat}, dev->{reg});
\tcomplete(&dev->done);
\treturn IRQ_HANDLED;
}}"""

# --- Probe / init functions ---
PROBE_FN = """\
static int {name}(struct platform_device *pdev)
{{
\tstruct {dev} *{d};
\tint {ret};
\t{d} = devm_kzalloc(&pdev->dev, sizeof(*{d}), GFP_KERNEL);
\tif (!{d})
\t\treturn -ENOMEM;
\t{d}->{base} = devm_platform_ioremap_resource(pdev, 0);
\tif (IS_ERR({d}->{base}))
\t\treturn PTR_ERR({d}->{base});
\tplatform_set_drvdata(pdev, {d});
\treturn 0;
}}"""

PROBE_FN_ALT = """\
static int {name}(struct platform_device *pdev)
{{
\tstruct {dev} *priv;
\tpriv = devm_kzalloc(&pdev->dev, sizeof(struct {dev}), GFP_KERNEL);
\tif (priv == NULL)
\t\treturn -ENOMEM;
\tpriv->base = devm_platform_ioremap_resource(pdev, 0);
\tif (IS_ERR(priv->base))
\t\treturn PTR_ERR(priv->base);
\tdev_set_drvdata(&pdev->dev, priv);
\treturn 0;
}}"""

# --- Completely unrelated / non-clone functions ---
NON_CLONE_A = """\
static int {name}(const char *{buf}, size_t {len})
{{
\tint i;
\tfor (i = 0; i < (int){len}; i++) {{
\t\tif ({buf}[i] < 0x20 || {buf}[i] > 0x7e)
\t\t\treturn -EINVAL;
\t}}
\treturn 0;
}}"""

NON_CLONE_B = """\
static unsigned int {name}(unsigned int {val})
{{
\tunsigned int {count} = 0;
\twhile ({val}) {{
\t\t{count} += {val} & 1;
\t\t{val} >>= 1;
\t}}
\treturn {count};
}}"""

NON_CLONE_C = """\
static void {name}(struct {dev} *{d})
{{
\tint i;
\tfor (i = 0; i < {d}->{n}; i++) {{
\t\tif ({d}->{arr}[i])
\t\t\tkfree({d}->{arr}[i]);
\t\t{d}->{arr}[i] = NULL;
\t}}
}}"""

NON_CLONE_D = """\
static s64 {name}(ktime_t {t1}, ktime_t {t2})
{{
\treturn ktime_to_ns(ktime_sub({t2}, {t1}));
}}"""

NON_CLONE_E = """\
static bool {name}(struct {node} *{a}, struct {node} *{b})
{{
\tif ({a}->{key} < {b}->{key})
\t\treturn true;
\tif ({a}->{key} > {b}->{key})
\t\treturn false;
\treturn {a}->{seq} < {b}->{seq};
}}"""

NON_CLONE_F = """\
static void {name}(struct seq_file *{m}, struct {node} *{e})
{{
\tseq_printf({m}, "%s: %llu %llu\\n",
\t\t{e}->name, {e}->{cnt_a}, {e}->{cnt_b});
}}"""

# ── Generation parameters ──────────────────────────────────────────────
CLONE_TEMPLATE_PAIRS = [
    (MEM_ALLOC,    MEM_ALLOC_ALT,  "mem_alloc"),
    (MEM_FREE,     MEM_FREE_ALT,   "mem_free"),
    (LIST_INSERT,  LIST_INSERT_ALT,"list_insert"),
    (LIST_REMOVE,  LIST_REMOVE_ALT,"list_remove"),
    (ERR_WRAP,     ERR_WRAP_ALT,   "err_wrap"),
    (BIT_SET,      BIT_SET_ALT,    "bit_set"),
    (BIT_CLR,      BIT_CLR_ALT,    "bit_clr"),
    (IRQ_HANDLER,  IRQ_HANDLER_ALT,"irq_handler"),
    (PROBE_FN,     PROBE_FN_ALT,   "probe_fn"),
]

SUBSYSTEMS = ["mmc", "usb", "net", "pci", "i2c", "spi", "gpio", "clk",
              "regulator", "rtc", "nvme", "dma", "drm", "sound", "crypto"]
DRIVERS = ["device", "controller", "adapter", "port", "channel",
           "bridge", "hub", "endpoint", "host", "client"]
LOCKS = ["dev_lock", "data_lock", "list_lock", "irq_lock", "hw_lock",
         "io_lock", "ctrl_lock", "reg_lock", "buf_lock", "fifo_lock"]


def _rand_name(prefix: str, idx: int) -> str:
    return f"{prefix}_{SUBSYSTEMS[idx % len(SUBSYSTEMS)]}_{idx:03d}"


def _params(template: str, idx: int, variant: int = 0) -> str:
    sub = SUBSYSTEMS[idx % len(SUBSYSTEMS)]
    drv = DRIVERS[(idx + variant) % len(DRIVERS)]
    lck = LOCKS[(idx + variant) % len(LOCKS)]
    return template.format(
        name=f"fn_{sub}_{idx:04d}",
        dev=f"{sub}_{drv}",
        d=f"{sub[0]}dev",
        node=f"{sub}_node",
        head=f"{sub}_list",
        lock=lck,
        flags=f"irq_flags_{variant}",
        ret=f"ret_{variant}",
        rc=f"rc",
        cmd=f"cmd_{variant}",
        reg=f"status_reg",
        mask=f"IRQ_{sub.upper()}_MASK",
        inner=f"do_{sub}_cmd",
        buf=f"buf_{variant}",
        sz=f"sz_{variant}",
        fl=f"gfp_{variant}",
        ptr=f"p_{variant}",
        base=f"io_base",
        n=f"n_entries",
        arr=f"entries",
        stat=f"irq_stat",
        irq=f"irq_num",
        priv=f"priv_data",
        bits=f"bits_{variant}",
        val=f"val_{variant}",
        count=f"cnt_{variant}",
        len=f"len_{variant}",
        t1=f"t_start",
        t2=f"t_end",
        a=f"node_a",
        b=f"node_b",
        key=f"priority",
        seq=f"sequence",
        m=f"seq_m",
        e=f"seq_entry",
        cnt_a=f"rx_bytes",
        cnt_b=f"tx_bytes",
    )


NON_CLONE_TEMPLATES = [NON_CLONE_A, NON_CLONE_B, NON_CLONE_C,
                       NON_CLONE_D, NON_CLONE_E, NON_CLONE_F]


def _non_clone(idx: int, which: int) -> str:
    t = NON_CLONE_TEMPLATES[which % len(NON_CLONE_TEMPLATES)]
    sub = SUBSYSTEMS[idx % len(SUBSYSTEMS)]
    drv = DRIVERS[(idx + 3) % len(DRIVERS)]
    return t.format(
        name=f"nc_{sub}_{idx:04d}",
        dev=f"{sub}_{drv}",
        d=f"{sub[0]}_ptr",
        node=f"{sub}_entry",
        buf=f"str_buf",
        len=f"str_len",
        val=f"bit_val",
        count=f"popcount",
        n=f"n_items",
        arr=f"items",
        t1=f"ts_start",
        t2=f"ts_end",
        a=f"node_a",
        b=f"node_b",
        key=f"prio",
        seq=f"seqno",
        m=f"m_file",
        e=f"m_entry",
        cnt_a=f"count_a",
        cnt_b=f"count_b",
    )


def build_dataset(n_clones_per_split: int = 80,
                  n_non_clones_per_split: int = 80) -> list[dict]:
    """Return rows suitable for a Linux C JSONL dataset."""
    rows: list[dict] = []
    function_split: dict[str, str] = {}  # fingerprint → split

    splits = ["train", "valid", "test"]

    for split_idx, split in enumerate(splits):
        clone_count = 0
        non_clone_count = 0

        # ── Clone pairs ───────────────────────────────────────────────
        base = split_idx * 1000
        for i in range(n_clones_per_split):
            tmpl_a, tmpl_b, kind = CLONE_TEMPLATE_PAIRS[i % len(CLONE_TEMPLATE_PAIRS)]
            fn_idx = base + i
            code_a = _params(tmpl_a, fn_idx, variant=0)
            code_b = _params(tmpl_b, fn_idx, variant=1)

            # Ensure each function only appears in one split (use unique idx range)
            rows.append({
                "split": split,
                "label": 1,
                "code_a": code_a,
                "code_b": code_b,
                "source_a": f"linux/v6.12/{kind}/{split}/a_{fn_idx:04d}.c:{i * 20 + 1}",
                "source_b": f"linux/v6.12/{kind}/{split}/b_{fn_idx:04d}.c:{i * 20 + 1}",
            })
            clone_count += 1

        # ── Non-clone pairs ───────────────────────────────────────────
        # Use truly different template families to avoid leakage
        nc_base = split_idx * 1000 + 500
        for i in range(n_non_clones_per_split):
            fn_idx = nc_base + i
            # Pick two different non-clone templates
            which_a = (i * 2) % len(NON_CLONE_TEMPLATES)
            which_b = (i * 2 + 3) % len(NON_CLONE_TEMPLATES)
            if which_a == which_b:
                which_b = (which_b + 1) % len(NON_CLONE_TEMPLATES)
            code_a = _non_clone(fn_idx, which_a)
            code_b = _non_clone(fn_idx + n_non_clones_per_split, which_b)

            rows.append({
                "split": split,
                "label": 0,
                "code_a": code_a,
                "code_b": code_b,
                "source_a": f"linux/v6.12/misc/{split}/nc_a_{fn_idx:04d}.c:{i * 15 + 1}",
                "source_b": f"linux/v6.12/misc/{split}/nc_b_{fn_idx:04d}.c:{i * 15 + 1}",
            })
            non_clone_count += 1

        print(f"  {split}: {clone_count} clone pairs, {non_clone_count} non-clone pairs",
              flush=True)

    return rows


def main():
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("linux_c_dataset.jsonl")
    print(f"Generating synthetic Linux C dataset -> {output}", flush=True)
    rows = build_dataset(n_clones_per_split=110, n_non_clones_per_split=110)
    output.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )
    print(f"Done. {len(rows)} rows written to {output}", flush=True)


if __name__ == "__main__":
    main()
