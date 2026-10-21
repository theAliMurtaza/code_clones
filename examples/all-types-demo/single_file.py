# Deliberate duplicate definitions for clone-detection input, not application code.
def add(a, b):
    return a + b


def add(a, b):
    # Same code with a comment: Type-1.
    return a + b


def sum_values(left, right):
    return left + right


def adjusted_sum(a, b):
    return a + b + 1


def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)


def fact(num):
    result = 1
    while num > 1:
        result *= num
        num -= 1
    return result
