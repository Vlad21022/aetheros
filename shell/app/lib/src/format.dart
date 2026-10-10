/// Romanian text for dates and times on the ambient screen.
library;

const _weekdays = ['Luni', 'Marți', 'Miercuri', 'Joi', 'Vineri', 'Sâmbătă', 'Duminică'];
const _months = [
  'ianuarie', 'februarie', 'martie', 'aprilie', 'mai', 'iunie',
  'iulie', 'august', 'septembrie', 'octombrie', 'noiembrie', 'decembrie',
];

String _two(int n) => n.toString().padLeft(2, '0');

/// "16:25"
String hourMinute(DateTime t) => '${_two(t.hour)}:${_two(t.minute)}';

/// "Sâmbătă, 10 octombrie"
String romanianDate(DateTime t) => '${_weekdays[t.weekday - 1]}, ${t.day} ${_months[t.month - 1]}';

/// How long until [start], as "în 2 h 05 min" or "în 35 min". Null once the event
/// has started or when it is a day or more away.
String? startsIn(DateTime now, DateTime start) {
  final minutes = (start.difference(now).inSeconds / 60).ceil();
  if (minutes <= 0 || minutes >= 24 * 60) return null;
  if (minutes < 60) return 'în $minutes min';
  return 'în ${minutes ~/ 60} h ${_two(minutes % 60)} min';
}
