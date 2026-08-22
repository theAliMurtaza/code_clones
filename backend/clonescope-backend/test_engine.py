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
    print("GraphCodeBERT Engine Smoke Test")
    print("=" * 60)

    from graphcodebert.engine import GraphCodeBERTEngine
    engine = GraphCodeBERTEngine()

    print("\n[1] embed_batch — 4 fragments")
    codes = [PYTHON_A, PYTHON_B, JAVA_A, UNRELATED]
    langs = ["python", "python", "java", "python"]
    vecs  = engine.embed_batch(codes, langs)
    print(f"    Output shape: {vecs.shape}  ✓" if vecs.shape == (4, 768) else f"    UNEXPECTED shape: {vecs.shape}")

    print("\n[2] predict_pair — same algorithm, Python vs Python (expect HIGH)")
    p1 = engine.predict_pair(PYTHON_A, "python", PYTHON_B, "python")
    print(f"    P(clone) = {p1:.4f}  → {'CLONE ✓' if p1 >= 0.5 else 'not clone'}")

    print("\n[3] predict_pair — same algorithm, Python vs Java (expect HIGH, cross-lang)")
    p2 = engine.predict_pair(PYTHON_A, "python", JAVA_A, "java")
    print(f"    P(clone) = {p2:.4f}  → {'CLONE ✓' if p2 >= 0.5 else 'not clone'}")

    print("\n[4] predict_pair — unrelated code (expect LOW)")
    p3 = engine.predict_pair(PYTHON_A, "python", UNRELATED, "python")
    print(f"    P(clone) = {p3:.4f}  → {'clone ?' if p3 >= 0.5 else 'NOT CLONE ✓'}")

    print("\n[5] Full pipeline — run_detection on two uploaded files")
    from detector import run_detection, UploadedFile
    files = [
        UploadedFile(filename="sort.py",  content=PYTHON_A + "\n" + UNRELATED),
        UploadedFile(filename="sort2.py", content=PYTHON_B),
    ]
    result = run_detection(files, threshold=0.50, engine=engine)
    print(f"    Fragments: {result.total_fragments}")
    print(f"    Stage-1 candidates: {result.stage1_pairs}")
    print(f"    Clone pairs found: {result.stage2_pairs}")
    print(f"    Runtime: {result.runtime_seconds}s")
    for pair in result.clone_pairs:
        print(f"    • [{pair.clone_type}] {pair.file_a}:{pair.lines_a} ↔ "
              f"{pair.file_b}:{pair.lines_b}  sim={pair.similarity:.3f}")

    print("\n" + "=" * 60)
    print("All tests passed ✓" if not result.errors else f"Errors: {result.errors}")
    print("=" * 60)


if __name__ == "__main__":
    main()
