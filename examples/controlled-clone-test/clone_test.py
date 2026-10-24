def clean_label(text):
    text = text.strip()
    text = text.lower()
    text = text.replace("_", " ")
    words = text.split()
    label = "-".join(words)
    return label


def clean_label(text):
    # Same code; this comment does not change the clone type.
    text = text.strip()
    text = text.lower()
    text = text.replace("_", " ")
    words = text.split()
    label = "-".join(words)
    return label


def squared_distance(point_a, point_b):
    horizontal = point_a[0] - point_b[0]
    vertical = point_a[1] - point_b[1]
    horizontal_squared = horizontal * horizontal
    vertical_squared = vertical * vertical
    distance = horizontal_squared + vertical_squared
    return distance


def separation_squared(first, second):
    delta_x = first[0] - second[0]
    delta_y = first[1] - second[1]
    x_squared = delta_x * delta_x
    y_squared = delta_y * delta_y
    separation = x_squared + y_squared
    return separation


def make_receipt(prices, tax_rate):
    subtotal = 0
    for price in prices:
        subtotal += price
    tax = subtotal * tax_rate
    total = subtotal + tax
    receipt = {}
    receipt["subtotal"] = subtotal
    receipt["tax"] = tax
    receipt["total"] = total
    receipt["items"] = len(prices)
    return receipt


def make_receipt_with_fee(prices, tax_rate):
    subtotal = 0
    for price in prices:
        subtotal += price
    tax = subtotal * tax_rate
    total = subtotal + tax
    total += 5
    receipt = {}
    receipt["subtotal"] = subtotal
    receipt["tax"] = tax
    receipt["total"] = total
    receipt["items"] = len(prices)
    return receipt


def triangular_by_loop(number):
    if number <= 0:
        return 0
    total = 0
    current = 1
    while current <= number:
        total += current
        current += 1
    return total


def triangular_by_formula(limit):
    if limit <= 0:
        return 0
    successor = limit + 1
    product = limit * successor
    triangle = product // 2
    return triangle


def find_maximum(numbers):
    if not numbers:
        return None
    largest = numbers[0]
    for value in numbers[1:]:
        if value > largest:
            largest = value
    return largest


def filter_even(numbers):
    result = []
    for number in numbers:
        if number % 2 == 0:
            result.append(number)
    return result
