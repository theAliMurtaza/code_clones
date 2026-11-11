"""
test_linux_detection.py
Verification test for Linux C clone detection.
Tests Type-1, Type-2, Type-3, and Type-4 detection on Linux C source code.

Usage:
    .\\.venv311\\Scripts\\python.exe test_linux_detection.py
"""

import sys
from config import get_settings
from detector import run_detection, UploadedFile
from graphcodebert.engine import get_engine

C_EXACT_A = '''
static void *alloc_buffer(size_t size, gfp_t flags)
{
    void *ptr;
    if (!size)
        return NULL;
    ptr = kmalloc(size, flags);
    if (!ptr)
        return NULL;
    memset(ptr, 0, size);
    return ptr;
}
'''

C_EXACT_B = '''
static void *alloc_buffer(size_t size, gfp_t flags)
{
    void *ptr;
    if (!size)
        return NULL;
    ptr = kmalloc(size, flags);
    if (!ptr)
        return NULL;
    memset(ptr, 0, size);
    return ptr;
}
'''

C_RENAMED_B = '''
static void *allocate_mem(size_t sz, gfp_t fl)
{
    void *p;
    if (!sz)
        return NULL;
    p = kmalloc(sz, fl);
    if (!p)
        return NULL;
    memset(p, 0, sz);
    return p;
}
'''

C_NEAR_MISS = '''
static void *allocate_mem_logged(size_t sz, gfp_t fl)
{
    void *p;
    if (sz == 0) {
        pr_warn("alloc: zero size requested\\n");
        return NULL;
    }
    p = kmalloc(sz, fl);
    if (!p) {
        pr_err("alloc: kmalloc failed for %zu bytes\\n", sz);
        return NULL;
    }
    memset(p, 0, sz);
    return p;
}
'''

C_SEMANTIC_ALT = '''
static void *get_zeroed_memory(size_t size, gfp_t flags)
{
    void *buf;
    if (size == 0)
        return NULL;
    buf = kzalloc(size, flags);
    return buf;
}
'''

C_UNRELATED = '''
static unsigned int count_active_bits(unsigned int val)
{
    unsigned int count = 0;
    while (val) {
        count += val & 1;
        val >>= 1;
    }
    return count;
}
'''


def run_tests():
    print("=" * 65)
    print("      LINUX C CLONE DETECTION VERIFICATION SUITE")
    print("=" * 65)

    settings = get_settings()
    print(f"\n[1] Checking Configuration:")
    print(f"    - Supported extensions: {settings.supported_extensions}")
    assert ".c" in settings.supported_extensions, ".c not in supported extensions!"
    assert ".h" in settings.supported_extensions, ".h not in supported extensions!"
    print(f"    - ENABLE_LINUX_C_CLASSIFIER: {settings.ENABLE_LINUX_C_CLASSIFIER}")
    assert settings.ENABLE_LINUX_C_CLASSIFIER is True, "ENABLE_LINUX_C_CLASSIFIER is not True!"
    print("    -> Configuration check PASSED [OK]")

    print(f"\n[2] Checking GraphCodeBERT Engine:")
    settings.DETECTION_ENGINE = "full"
    engine = get_engine()
    print(f"    - Model loaded: {engine._model_loaded}")
    print(f"    - Fine-tuned head loaded: {engine.is_fine_tuned}")
    print(f"    - Validated language pairs: {engine.validated_language_pairs}")
    print(f"    - Decision threshold: {engine.classifier_threshold}")
    assert engine.is_fine_tuned, "Engine is not fine-tuned!"
    assert "c:c" in engine.validated_language_pairs, "'c:c' not in validated language pairs!"
    print("    -> Model & weights check PASSED [OK]")

    print(f"\n[3] Testing Clone Detection on Linux C Source Files:")
    files = [
        UploadedFile(filename="mm/alloc_original.c", content=C_EXACT_A),
        UploadedFile(filename="mm/alloc_exact_copy.c", content=C_EXACT_B),
        UploadedFile(filename="mm/alloc_renamed.c", content=C_RENAMED_B),
        UploadedFile(filename="mm/alloc_modified.c", content=C_NEAR_MISS),
        UploadedFile(filename="drivers/kzalloc_helper.c", content=C_SEMANTIC_ALT),
        UploadedFile(filename="lib/bitops.c", content=C_UNRELATED),
    ]

    result = run_detection(files, threshold=0.50, engine=engine)
    print(f"    - Total fragments analyzed: {result.total_fragments}")
    print(f"    - Total clone pairs detected: {len(result.clone_pairs)}")
    print(f"    - Runtime: {result.runtime_seconds}s")

    detected_types = {}
    for pair in result.clone_pairs:
        detected_types.setdefault(pair.clone_type, []).append(pair)
        print(f"\n    * [{pair.clone_type}] (similarity: {pair.similarity:.2%}, tokens: {pair.token_sim:.2%})")
        print(f"      File A: {pair.file_a} (lines {pair.lines_a[0]}-{pair.lines_a[1]})")
        print(f"      File B: {pair.file_b} (lines {pair.lines_b[0]}-{pair.lines_b[1]})")
        print(f"      Detail: {pair.description}")

    # Verify no false positive with C_UNRELATED
    for pair in result.clone_pairs:
        assert "bitops.c" not in pair.file_a and "bitops.c" not in pair.file_b, \
            f"False positive detected with unrelated file: {pair.file_a} <-> {pair.file_b}"

    print(f"\n[4] Summary of Detected Clone Types:")
    for ctype in ["Type-1", "Type-2", "Type-3", "Type-4"]:
        count = len(detected_types.get(ctype, []))
        print(f"    - {ctype}: {count} pair(s)")

    assert len(detected_types.get("Type-1", [])) >= 1, "Expected at least one Type-1 clone!"
    assert len(result.clone_pairs) >= 3, "Expected multiple clone types detected!"

    print("\n" + "=" * 65)
    print("      ALL LINUX C CLONE DETECTION TESTS PASSED SUCCESSFULLY! [OK]")
    print("=" * 65)


if __name__ == "__main__":
    run_tests()
