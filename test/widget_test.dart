import 'package:flutter_test/flutter_test.dart';
import 'package:myctubus_flutter/main.dart';

void main() {
  testWidgets('App smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const MyCtuBusApp());
    expect(find.byType(MyCtuBusApp), findsOneWidget);
  });
}
