import test from 'node:test'
import assert from 'node:assert/strict'
import { highlightSegments } from './codeHighlight.js'

test('preserves numbers and every other character in the reported examples', () => {
  for (const line of ['    total = 0', '    result = 1',
    '    for value in range(1, number + 1):', '        frequency[item] += 1',
    '        frequency[item] = 1', 'public int value() { return 42; }',
    'x = -1.25 + 0xff', '    ', '', 'return a < b && b > 0']) {
    assert.equal(highlightSegments(line).map(s => s.text).join(''), line)
  }
  assert.deepEqual(highlightSegments('0'), [{ kind: 'number', text: '0' }])
})

test('comment markers in strings do not swallow literals or following numbers', () => {
  const line = 'url = "https://example.com/#test" + "escaped\\\"quote" # 123'
  const segments = highlightSegments(line)
  assert.equal(segments.map(s => s.text).join(''), line)
  assert.equal(segments.filter(s => s.kind === 'string').length, 2)
  assert.equal(segments.find(s => s.kind === 'comment').text, '# 123')
})
