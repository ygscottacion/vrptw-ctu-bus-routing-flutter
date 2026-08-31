import 'package:flutter/material.dart';
import '../../../theme/app_theme.dart';

class DriverShiftButton extends StatelessWidget {
  const DriverShiftButton({
    super.key,
    required this.isShiftActive,
    required this.pulseAnimation,
    required this.onToggleShift,
  });

  final bool isShiftActive;
  final Animation<double> pulseAnimation;
  final VoidCallback onToggleShift;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 16),
        child: Column(
          children: [
            ScaleTransition(
              scale: isShiftActive
                  ? pulseAnimation
                  : const AlwaysStoppedAnimation(1.0),
              child: GestureDetector(
                onTap: onToggleShift,
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 300),
                  width: 180,
                  height: 180,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: isShiftActive
                        ? const Color(0xFFD32F2F)
                        : AppColors.teal,
                    boxShadow: [
                      BoxShadow(
                        color: (isShiftActive
                                ? const Color(0xFFD32F2F)
                                : AppColors.teal)
                            .withOpacity(0.4),
                        blurRadius: 24,
                        spreadRadius: 4,
                        offset: const Offset(0, 8),
                      ),
                    ],
                  ),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(
                        Icons.power_settings_new_rounded,
                        size: 54,
                        color: Colors.white,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        isShiftActive ? 'End Shift' : 'Start Shift',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: 12),
            Text(
              isShiftActive
                  ? 'Ca làm việc đang hoạt động (GPS On)'
                  : 'Sẵn sàng cho chuyến xe tiếp theo',
              style: TextStyle(
                color: Colors.grey[700],
                fontSize: 14,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
