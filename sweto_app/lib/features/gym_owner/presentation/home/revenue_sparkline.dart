import 'package:flutter/material.dart';
import 'package:sweto_app/core/theme/colors.dart';

/// Running total of this month's revenue, drawn as a small rising line.
class RevenueSparkline extends StatelessWidget {
  const RevenueSparkline({required this.daily, super.key});

  final List<double> daily;

  @override
  Widget build(BuildContext context) => CustomPaint(
    painter: _SparklinePainter(_runningTotal(daily)),
    size: const Size(double.infinity, 56),
  );

  static List<double> _runningTotal(List<double> daily) {
    var total = 0.0;
    return [for (final amount in daily) total += amount];
  }
}

class _SparklinePainter extends CustomPainter {
  _SparklinePainter(this.points);

  final List<double> points;

  @override
  void paint(Canvas canvas, Size size) {
    if (points.length < 2) return;
    final top = points.reduce((a, b) => a > b ? a : b);
    if (top <= 0) return;
    final dx = size.width / (points.length - 1);
    Offset at(int i) =>
        Offset(i * dx, size.height - (points[i] / top) * (size.height - 4) - 2);
    final line = Path()..moveTo(at(0).dx, at(0).dy);
    for (var i = 1; i < points.length; i++) {
      line.lineTo(at(i).dx, at(i).dy);
    }
    final fill = Path.from(line)
      ..lineTo(size.width, size.height)
      ..lineTo(0, size.height)
      ..close();
    canvas.drawPath(
      fill,
      Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            AppColors.primary.withValues(alpha: .35),
            AppColors.primary.withValues(alpha: 0),
          ],
        ).createShader(Offset.zero & size),
    );
    canvas.drawPath(
      line,
      Paint()
        ..color = AppColors.primary
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.5
        ..strokeCap = StrokeCap.round
        ..strokeJoin = StrokeJoin.round,
    );
  }

  @override
  bool shouldRepaint(_SparklinePainter old) => old.points != points;
}
