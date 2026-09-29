
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
