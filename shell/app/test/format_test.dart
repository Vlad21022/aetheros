import 'package:aether_shell/src/format.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  final now = DateTime(2026, 10, 10, 16, 25);

  test('formats the date and time in Romanian', () {
    expect(hourMinute(DateTime(2026, 10, 10, 8, 5)), '08:05');
    expect(romanianDate(now), 'Sâmbătă, 10 octombrie');
  });

  test('startsIn counts down in hours and minutes', () {
    expect(startsIn(now, DateTime(2026, 10, 10, 18, 30)), 'în 2 h 05 min');
    expect(startsIn(now, DateTime(2026, 10, 10, 17, 25)), 'în 1 h 00 min');
    expect(startsIn(now, DateTime(2026, 10, 10, 17, 0)), 'în 35 min');
  });

  test('startsIn rounds partial minutes up', () {
    expect(startsIn(DateTime(2026, 10, 10, 16, 25, 30), DateTime(2026, 10, 10, 16, 27)), 'în 2 min');
  });

  test('startsIn is empty for events that started or are a day away', () {
    expect(startsIn(now, now), isNull);
    expect(startsIn(now, DateTime(2026, 10, 10, 16, 0)), isNull);
    expect(startsIn(now, DateTime(2026, 10, 11, 16, 25)), isNull);
  });
}
