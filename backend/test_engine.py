"""
test_engine.py
Quick smoke-test for the GraphCodeBERT engine.
Run this after installing requirements to verify everything is working.

Usage:
    python test_engine.py
"""

import sys, logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

PYTHON_A = '''
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left  = [x for x in arr if x < pivot]
    mid   = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + mid + quicksort(right)
'''

PYTHON_B = '''
def sort_list(items):
    if len(items) <= 1:
        return items
    p    = items[len(items) // 2]
    lo   = [x for x in items if x < p]
    same = [x for x in items if x == p]
    hi   = [x for x in items if x > p]
    return sort_list(lo) + same + sort_list(hi)
'''

# Type-4 semantic clone: recursive vs iterative factorial (different algorithmic implementation)
FACT_REC = '''
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
'''

FACT_ITER = '''
def fact(num):
    result = 1
    while num > 1:
        result *= num
        num -= 1
    return result
'''

JAVA_A = '''
public static int[] quickSort(int[] arr) {
    if (arr.length <= 1) return arr;
    int pivot = arr[arr.length / 2];
    List<Integer> left  = new ArrayList<>();
    List<Integer> mid   = new ArrayList<>();
    List<Integer> right = new ArrayList<>();
    for (int x : arr) {
        if (x < pivot) left.add(x);
        else if (x == pivot) mid.add(x);
        else right.add(x);
    }
    return merge(quickSort(toArray(left)), toArray(mid), quickSort(toArray(right)));
}
'''

UNRELATED = '''
def send_email(recipient, subject, body):
    import smtplib
    with smtplib.SMTP("smtp.gmail.com", 587) as s:
        s.starttls()
        s.login("user@example.com", "password")
        s.sendmail("user@example.com", recipient, f"Subject: {subject}\n\n{body}")
'''


def main():
    print("=" * 60)
    print("GraphCodeBERT Engine & Type-4 Clone Test")
    print("=" * 60)

    from graphcodebert.engine import GraphCodeBERTEngine
    engine = GraphCodeBERTEngine()

    print("\n[1] embed_batch -- 5 fragments")
    codes = [PYTHON_A, PYTHON_B, FACT_REC, FACT_ITER, JAVA_A]
    langs = ["python", "python", "python", "python", "java"]
    vecs  = engine.embed_batch(codes, langs)
    ok_shape = vecs.shape == (5, 768)
    print(f"    Output shape: {vecs.shape}  {'[OK]' if ok_shape else '[FAILED]'}")

    print("\n[2] predict_pair -- same algorithm, Python vs Python (Type-2/3 clone)")
    p1 = engine.predict_pair(PYTHON_A, "python", PYTHON_B, "python")
    print(f"    P(clone) = {p1:.4f}  -> {'[CLONE]' if p1 >= 0.5 else '[NOT CLONE]'}")

    print("\n[3] predict_pair -- Cross-language QuickSort: Python vs Java (Type-4 clone)")
    p2 = engine.predict_pair(PYTHON_A, "python", JAVA_A, "java")
    print(f"    P(clone) = {p2:.4f}  -> {'[CLONE]' if p2 >= 0.5 else '[NOT CLONE]'}")

    print("\n[4] predict_pair -- Different algorithm: Recursive vs Iterative Factorial (Type-4 clone)")
    p3 = engine.predict_pair(FACT_REC, "python", FACT_ITER, "python")
    print(f"    P(clone) = {p3:.4f}  -> {'[CLONE]' if p3 >= 0.5 else '[NOT CLONE]'}")

    print("\n[5] Full pipeline -- run_detection with Type-4 clone classification")
    from detector import run_detection, UploadedFile
    files = [
        UploadedFile(filename="algo.py",      content=PYTHON_A + "\n" + FACT_REC),
        UploadedFile(filename="algo_iter.py", content=FACT_ITER),
        UploadedFile(filename="Sort.java",    content=JAVA_A),
    ]
    result = run_detection(files, threshold=0.50, engine=engine)
    print(f"    Fragments: {result.total_fragments}")
    print(f"    Stage-1 candidates: {result.stage1_pairs}")
    print(f"    Clone pairs found: {result.stage2_pairs}")
    print(f"    Runtime: {result.runtime_seconds}s")

    type_counts = {}
    for pair in result.clone_pairs:
        type_counts[pair.clone_type] = type_counts.get(pair.clone_type, 0) + 1
        print(f"    * [{pair.clone_type}] {pair.file_a}:{pair.lines_a} <-> "
              f"{pair.file_b}:{pair.lines_b}  sim={pair.similarity:.3f} "
              f"tok_sim={pair.token_sim:.3f} ({pair.description})")

    print("\n    Clone counts by type:")
    for ctype in ["Type-1", "Type-2", "Type-3", "Type-4"]:
        print(f"      {ctype}: {type_counts.get(ctype, 0)}")

    print("\n" + "=" * 60)
    has_type4 = type_counts.get("Type-4", 0) > 0
    if has_type4 and not result.errors:
        print("Type-4 clone detection verified successfully! [PASS]")
    else:
        print(f"Verification issue: Type-4 detected={has_type4}, errors={result.errors} [FAIL]")
    print("=" * 60)


if __name__ == "__main__":
    main()

