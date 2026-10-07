import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:sweto_app/core/theme/colors.dart';

class OrangeParticles extends StatefulWidget {
  const OrangeParticles({super.key, this.particleCount = 55});

  final int particleCount;

  @override
  State<OrangeParticles> createState() => _OrangeParticlesState();
}

class _OrangeParticlesState extends State<OrangeParticles>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final List<_Particle> _particles;

  @override
  void initState() {
    super.initState();

    final random = math.Random(42);

    _particles = List.generate(
      widget.particleCount,
      (_) => _Particle(
        x: random.nextDouble(),
        y: random.nextDouble(),
        size: 1 + random.nextDouble() * 2.6,
        speed: 0.015 + random.nextDouble() * 0.045,
        opacity: 0.25 + random.nextDouble() * 0.75,
        drift: -0.02 + random.nextDouble() * 0.04,
      ),
    );

    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 10),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: RepaintBoundary(
        child: AnimatedBuilder(
          animation: _controller,
          builder: (context, child) {
            return CustomPaint(
              painter: _ParticlePainter(
                particles: _particles,
                animationValue: _controller.value,
              ),
              size: Size.infinite,
            );
          },
        ),
      ),
    );
  }
}

class _Particle {
  const _Particle({
    required this.x,
    required this.y,
    required this.size,
    required this.speed,
    required this.opacity,
    required this.drift,
  });

  final double x;
  final double y;
  final double size;
  final double speed;
  final double opacity;
  final double drift;
}

class _ParticlePainter extends CustomPainter {
  const _ParticlePainter({
    required this.particles,
    required this.animationValue,
  });

  final List<_Particle> particles;
  final double animationValue;

  @override
  void paint(Canvas canvas, Size size) {
    for (final particle in particles) {
      final animatedY = (particle.y + animationValue * particle.speed * 18) % 1;

      final animatedX = (particle.x + animationValue * particle.drift) % 1;

      final x = animatedX * size.width;
      final y = animatedY * size.height;

      final paint = Paint()
        ..color = AppColors.primary.withValues(alpha: particle.opacity)
        ..style = PaintingStyle.fill;

      canvas.drawCircle(Offset(x, y), particle.size, paint);
    }
  }

  @override
  bool shouldRepaint(covariant _ParticlePainter oldDelegate) {
    return oldDelegate.animationValue != animationValue;
  }
}
