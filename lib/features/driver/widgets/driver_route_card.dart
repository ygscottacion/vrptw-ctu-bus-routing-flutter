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

  String _clock(dynamic value) {
    final parsed = DateTime.tryParse(value?.toString() ?? '')?.toLocal();
    if (parsed == null) return '—';
    return '${parsed.hour.toString().padLeft(2, '0')}:${parsed.minute.toString().padLeft(2, '0')}';
  }

  String _serviceDate(dynamic value) {
    final parsed = DateTime.tryParse(value?.toString() ?? '');
    if (parsed == null) return 'Chưa có ngày chạy';
    return 'Ngày ${parsed.day.toString().padLeft(2, '0')}/${parsed.month.toString().padLeft(2, '0')}/${parsed.year}';
  }

  String _sessionLabel(dynamic value) {
    switch (value?.toString()) {
      case 'MORNING_1':
        return 'Ca 07:00';
      case 'MORNING_2':
        return 'Ca 08:30';
      case 'NOON_1':
        return 'Ca 10:00';
      case 'NOON_2':
        return 'Ca 11:30';
      default:
        return value?.toString() ?? 'Chưa có ca';
    }
  }

  String _statusLabel(dynamic value) {
    switch (value?.toString().toLowerCase()) {
      case 'approved':
        return 'Đã duyệt';
      case 'in_progress':
        return 'Đang chạy';
      case 'completed':
        return 'Hoàn tất';
      case 'rejected':
        return 'Bị từ chối';
      case 'pending':
        return 'Chờ duyệt';
      default:
        return 'Sắp chạy';
    }
  }

  Widget _metric({required IconData icon, required String label, required String value}) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: const Color(0xFFF0F4F4),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          children: [
            Icon(icon, color: AppColors.teal, size: 20),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(label, maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Colors.grey, fontSize: 10)),
                  Text(value, maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return _messageCard(
        child: const Column(
          children: [
            CircularProgressIndicator(color: AppColors.teal),
            SizedBox(height: 16),
            Text('Đang tải tuyến được phân công...', style: TextStyle(color: Colors.grey)),
          ],
        ),
      );
    }

    if (errorMessage != null) {
      return _messageCard(
        borderColor: Colors.red.shade200,
        child: Column(
          children: [
            Icon(Icons.error_outline_rounded, size: 44, color: Colors.red[400]),
            const SizedBox(height: 12),
            const Text('Không tải được tuyến', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.red)),
            const SizedBox(height: 8),
            Text(errorMessage!, textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 13, color: Colors.grey)),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: onRefresh,
              icon: const Icon(Icons.refresh_rounded, color: AppColors.teal),
              label: const Text('Tải lại tuyến', style: TextStyle(color: AppColors.teal)),
            ),
          ],
        ),
      );
    }

    final route = nextRoute;
    if (route == null) {
      return _messageCard(
        child: const Column(
          children: [
            Icon(Icons.directions_bus_filled_outlined, size: 44, color: Colors.grey),
            SizedBox(height: 12),
            Text('Chưa có tuyến được phân công',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            SizedBox(height: 8),
            Text('Tuyến sẽ xuất hiện ở đây sau khi hệ thống phân công cho xe của bạn.',
                textAlign: TextAlign.center, style: TextStyle(fontSize: 13, color: Colors.grey)),
          ],
        ),
      );
    }

    final id = route['id']?.toString() ?? '';
    final routeCode = id.length > 5 ? id.substring(0, 5).toUpperCase() : id;
    final status = route['status']?.toString().toLowerCase();
    final statusColor = status == 'in_progress' ? Colors.green :
        status == 'completed' ? Colors.grey :
        status == 'rejected' ? Colors.red : const Color(0xFFB7791F);
    final stops = route['stops'] as List? ?? const [];
    final stationCount = stops.isEmpty ? 0 : stops.length - 1; // Điểm đầu là depot.
    final passengerCount = (route['passenger_count'] as num?)?.toInt();
    final distance = (route['total_distance'] as num?)?.toDouble();
    final drivingMinutes = (route['driving_duration_minutes'] as num?)?.toDouble();
    final departure = _clock(route['departure_time']);
    final schoolArrival = _clock(route['estimated_school_arrival_time']);
    final destinationLabel = route['trip_type']?.toString().toLowerCase() == 'dropoff'
        ? 'Về trường'
        : 'Đến trường';
    final drivingDurationLabel = drivingMinutes == null
        ? '—'
        : '${drivingMinutes.toStringAsFixed(1)} phút';
    final direction = route['trip_type']?.toString().toLowerCase() == 'dropoff'
        ? 'Chiều về' : 'Chiều đi';

    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.teal.shade100),
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.04), blurRadius: 12, offset: const Offset(0, 4))],
      ),
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  const Text('TUYẾN ĐƯỢC PHÂN CÔNG',
                      style: TextStyle(color: Colors.grey, fontSize: 11, fontWeight: FontWeight.bold, letterSpacing: 0.7)),
                  const SizedBox(height: 5),
                  Text('Tuyến #CT-$routeCode',
                      style: const TextStyle(color: AppColors.teal, fontSize: 20, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 4),
                  Text('${_sessionLabel(route['session_id'])} • $direction • ${_serviceDate(route['service_date'])}',
                      style: const TextStyle(fontSize: 12, color: Color(0xFF3D4947))),
                ]),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
                decoration: BoxDecoration(color: statusColor.withOpacity(0.12), borderRadius: BorderRadius.circular(20)),
                child: Text(_statusLabel(status), style: TextStyle(color: statusColor, fontSize: 11, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            'Xuất phát $departure • $destinationLabel $schoolArrival',
            style: const TextStyle(color: Color(0xFF3D4947), fontSize: 13),
          ),
          const SizedBox(height: 12),
          Row(children: [
            _metric(icon: Icons.groups_rounded, label: 'Sinh viên', value: passengerCount?.toString() ?? '—'),
            const SizedBox(width: 8),
            _metric(icon: Icons.place_outlined, label: 'Trạm đón', value: '$stationCount'),
          ]),
          const SizedBox(height: 8),
          Row(children: [
            _metric(icon: Icons.route_rounded, label: 'Quãng đường', value: distance == null ? '—' : '${distance.toStringAsFixed(1)} km'),
            const SizedBox(width: 8),
            _metric(icon: Icons.schedule_rounded, label: 'Xe chạy', value: drivingDurationLabel),
          ]),
          const SizedBox(height: 14),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: () => onSelectRoute(route),
              style: FilledButton.styleFrom(
                backgroundColor: AppColors.teal,
                padding: const EdgeInsets.symmetric(vertical: 12),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              icon: const Icon(Icons.map_rounded),
              label: const Text('Xem lộ trình'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _messageCard({required Widget child, Color? borderColor}) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 32, horizontal: 20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: borderColor ?? Colors.grey.shade200),
      ),
      child: Center(child: child),
    );
  }
}
