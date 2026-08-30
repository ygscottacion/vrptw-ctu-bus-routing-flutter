import 'package:flutter/material.dart';
import '../../../theme/app_theme.dart';

class DriverRouteCard extends StatelessWidget {
  const DriverRouteCard({
    super.key,
    required this.isLoading,
    required this.errorMessage,
    required this.nextRoute,
    required this.onRefresh,
    required this.onSelectRoute,
  });

  final bool isLoading;
  final String? errorMessage;
  final Map<String, dynamic>? nextRoute;
  final VoidCallback onRefresh;
  final ValueChanged<Map<String, dynamic>> onSelectRoute;

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return Container(
        padding: const EdgeInsets.symmetric(vertical: 40),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: Colors.grey.shade200, width: 1),
        ),
        child: Center(
          child: Column(
            children: const [
              CircularProgressIndicator(color: AppColors.teal),
              SizedBox(height: 16),
              Text('Đang tải dữ liệu chuyến đi...', style: TextStyle(color: Colors.grey)),
            ],
          ),
        ),
      );
    }

    if (errorMessage != null) {
      return Container(
        padding: const EdgeInsets.symmetric(vertical: 32, horizontal: 20),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: Colors.red.shade200, width: 1),
        ),
        child: Column(
          children: [
            Icon(Icons.error_outline_rounded, size: 48, color: Colors.red[400]),
            const SizedBox(height: 16),
            const Text(
              'Lỗi tải dữ liệu',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: Colors.red,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              errorMessage!,
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontSize: 14,
                color: Colors.grey,
              ),
            ),
            const SizedBox(height: 16),
            OutlinedButton.icon(
              onPressed: onRefresh,
              icon: const Icon(Icons.refresh_rounded, color: AppColors.teal),
              label: const Text('Thử lại', style: TextStyle(color: AppColors.teal)),
              style: OutlinedButton.styleFrom(
                side: const BorderSide(color: AppColors.teal),
              ),
            ),
          ],
        ),
      );
    }

    if (nextRoute != null) {
      return Container(
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: Colors.teal.shade100, width: 1),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.04),
              blurRadius: 12,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'CHUYẾN TIẾP THEO (UP NEXT)',
                      style: TextStyle(
                        color: Colors.grey,
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 0.8,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        Text(
                          'Tuyến #${nextRoute!['id']}',
                          style: const TextStyle(
                            color: AppColors.teal,
                            fontSize: 20,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: const Color(0xFFFFDDB9),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: const Text(
                            '08:00 AM',
                            style: TextStyle(
                              color: Color(0xFF663E00),
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: AppColors.teal.withOpacity(0.1),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(Icons.route_rounded,
                      color: AppColors.teal),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              'Tổng quãng đường: ${nextRoute!['total_distance']} km · ${(nextRoute!['stops'] as List?)?.length ?? 0} trạm dừng',
              style: const TextStyle(
                color: Color(0xFF3D4947),
                fontSize: 14,
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: const Color(0xFFF0F4F4),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.groups_rounded,
                            color: Color(0xFF4858AB), size: 22),
                        const SizedBox(width: 8),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: const [
                            Text(
                              'Dự kiến khách',
                              style: TextStyle(
                                color: Colors.grey,
                                fontSize: 11,
                              ),
                            ),
                            Text(
                              '~45 SV',
                              style: TextStyle(
                                fontSize: 15,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: const Color(0xFFF0F4F4),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.schedule_rounded,
                            color: Color(0xFFD18400), size: 22),
                        const SizedBox(width: 8),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: const [
                            Text(
                              'Thời gian chạy',
                              style: TextStyle(
                                color: Colors.grey,
                                fontSize: 11,
                              ),
                            ),
                            Text(
                              '25 phút',
                              style: TextStyle(
                                fontSize: 15,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: () => onSelectRoute(nextRoute!),
                style: FilledButton.styleFrom(
                  backgroundColor: AppColors.teal,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                icon: const Icon(Icons.map_rounded),
                label: const Text('Bắt đầu / Mở Bản đồ tuyến'),
              ),
            ),
          ],
        ),
      );
    }

    // Empty State
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 32, horizontal: 20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.grey.shade200, width: 1),
      ),
      child: Column(
        children: [
          Icon(Icons.directions_bus_filled_outlined,
              size: 48, color: Colors.grey[400]),
          const SizedBox(height: 16),
          const Text(
            'Chưa có tuyến tiếp theo',
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
              color: Color(0xFF3D4947),
            ),
          ),
          const SizedBox(height: 8),
          const Text(
            'Hiện tại bạn chưa được phân công tuyến xe nào. Hãy nghỉ ngơi hoặc chờ thông báo mới.',
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 14,
              color: Colors.grey,
            ),
          ),
        ],
      ),
    );
  }
}
