import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import '../../services/api_service.dart';
import '../../theme/app_theme.dart';

class DriverProfileTab extends StatefulWidget {
  const DriverProfileTab({
    super.key,
    required this.user,
    required this.api,
    required this.onLogout,
  });

  final Map<String, dynamic> user;
  final ApiService api;
  final VoidCallback onLogout;

  @override
  State<DriverProfileTab> createState() => _DriverProfileTabState();
}

class _DriverProfileTabState extends State<DriverProfileTab> {
  bool _isLoading = true;
  Map<String, dynamic>? _assignedVehicle;
  int _completedRoutesCount = 0;
  int _totalRoutesCount = 0;
  int _scannedTicketsCount = 0;
  double _totalDistanceKm = 0.0;
  String? _driverCode;

  @override
  void initState() {
    super.initState();
    _loadDriverProfileData();
  }

  Future<void> _loadDriverProfileData() async {
    if (!mounted) return;
    setState(() => _isLoading = true);

    try {
      final driverId = widget.user['id']?.toString() ?? '';

      // 1. Fetch assigned vehicle from Supabase
      Map<String, dynamic>? vehicle;
      if (driverId.isNotEmpty) {
        try {
          final res = await Supabase.instance.client
              .from('vehicles')
              .select('*')
              .eq('driver_id', driverId)
              .maybeSingle();
          if (res != null) {
            vehicle = Map<String, dynamic>.from(res);
          }
        } catch (_) {}
      }

      // 2. Fetch driver's routes to calculate stats & fallback vehicle
      int completed = 0;
      int total = 0;
      double distance = 0.0;
      final List<String> routeIds = [];

      if (driverId.isNotEmpty) {
        try {
          final routes = await widget.api.fetchDriverRoutes(driverId);
          total = routes.length;
          for (final r in routes) {
            final routeId = r['id']?.toString() ?? '';
            if (routeId.isNotEmpty) routeIds.add(routeId);

            final status = r['status']?.toString();
            if (status == 'completed') {
              completed++;
            }
            if (r['total_distance'] != null) {
              distance += (r['total_distance'] as num).toDouble();
            }

            // Fallback vehicle assignment if direct driver_id query yielded null
            if (vehicle == null && r['vehicles'] != null) {
              vehicle = Map<String, dynamic>.from(r['vehicles'] as Map);
            }
          }
        } catch (_) {}
      }

      // 3. Fetch scanned tickets for driver's routes
      int scannedTickets = 0;
      if (routeIds.isNotEmpty) {
        try {
          final ticketsRes = await Supabase.instance.client
              .from('tickets')
              .select('id')
              .inFilter('route_id', routeIds)
              .eq('status', 'used');
          scannedTickets = (ticketsRes as List).length;
        } catch (_) {}
      }

      // 4. Generate driver code
      final rawId = widget.user['id']?.toString() ?? 'DRV';
      final code = rawId.length > 6 ? rawId.substring(0, 6).toUpperCase() : rawId.toUpperCase();

      if (mounted) {
        setState(() {
          _assignedVehicle = vehicle;
          _completedRoutesCount = completed;
          _totalRoutesCount = total;
          _scannedTicketsCount = scannedTickets;
          _totalDistanceKm = distance;
          _driverCode = 'DRV-$code';
          _isLoading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _confirmLogout(BuildContext context) {
    showDialog(
      context: context,
      builder: (c) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text('Đăng xuất tài khoản'),
        content: const Text('Bạn có chắc chắn muốn đăng xuất khỏi tài khoản Tài xế?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(c),
            child: const Text('Hủy'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.redAccent),
            onPressed: () {
              Navigator.pop(c);
              widget.onLogout();
            },
            child: const Text('Đăng xuất'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final driverName =
        widget.user['full_name']?.toString() ?? widget.user['username']?.toString() ?? 'Tài xế CTU BUS';
    final email = widget.user['email']?.toString() ?? 'driver@ctu.edu.vn';

    return Scaffold(
      backgroundColor: const Color(0xFFF6FAFA),
      appBar: AppBar(
        backgroundColor: AppColors.teal,
        title: const Text('Hồ sơ Tài xế (Driver Profile)'),
        elevation: 1,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            tooltip: 'Làm mới dữ liệu',
            onPressed: _loadDriverProfileData,
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadDriverProfileData,
        color: AppColors.teal,
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            // Profile Header Card
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(20),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.04),
                    blurRadius: 10,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: Column(
                children: [
                  Stack(
                    children: [
                      Container(
                        width: 84,
                        height: 84,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: AppColors.teal.withValues(alpha: 0.15),
                          border: Border.all(color: AppColors.teal, width: 3),
                        ),
                        child: const Icon(
                          Icons.person_rounded,
                          size: 50,
                          color: AppColors.teal,
                        ),
                      ),
                      Positioned(
                        bottom: 0,
                        right: 0,
                        child: Container(
                          padding: const EdgeInsets.all(4),
                          decoration: const BoxDecoration(
                            color: Colors.green,
                            shape: BoxShape.circle,
                          ),
                          child: const Icon(Icons.check, size: 14, color: Colors.white),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),
                  Text(
                    driverName,
                    style: const TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF181C1D),
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    email,
                    style: const TextStyle(color: Colors.grey, fontSize: 13),
                  ),
                  const SizedBox(height: 10),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                    decoration: BoxDecoration(
                      color: const Color(0xFFFFDDB9),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      'Bằng lái hạng D · Mã TX: ${_driverCode ?? 'DRV-101'}',
                      style: const TextStyle(
                        color: Color(0xFF663E00),
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 20),

            // Performance Stats Grid
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Thống kê ca làm việc hôm nay',
                  style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                ),
                if (_isLoading)
                  const SizedBox(
                    width: 14,
                    height: 14,
                    child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.teal),
                  ),
              ],
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: _statCard(
                    'Chuyến đã chạy',
                    '$_completedRoutesCount/$_totalRoutesCount',
                    Icons.directions_bus_rounded,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _statCard(
                    'Vé đã quét',
                    '$_scannedTicketsCount',
                    Icons.qr_code_scanner_rounded,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _statCard(
                    'Quãng đường',
                    '${_totalDistanceKm.toStringAsFixed(0)} km',
                    Icons.route_rounded,
                  ),
                ),
              ],
            ),

            const SizedBox(height: 24),

            // Assigned Vehicle Info Card
            const Text(
              'Phương tiện được gán (Assigned Bus)',
              style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 10),
            _buildAssignedVehicleCard(),

            const SizedBox(height: 24),

            // Profile Actions List
            Card(
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              child: Column(
                children: [
                  ListTile(
                    leading: const Icon(Icons.lock_outline_rounded, color: AppColors.teal),
                    title: const Text('Đổi mật khẩu'),
                    trailing: const Icon(Icons.chevron_right_rounded),
                    onTap: () {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Tính năng đổi mật khẩu đang mở rộng.')),
                      );
                    },
                  ),
                  const Divider(height: 1),
                  ListTile(
                    leading: const Icon(Icons.help_outline_rounded, color: AppColors.teal),
                    title: const Text('Hướng dẫn sử dụng cho Tài xế'),
                    trailing: const Icon(Icons.chevron_right_rounded),
                    onTap: () {
                      showAboutDialog(
                        context: context,
                        applicationName: 'MyCTU BUS Driver',
                        applicationVersion: 'v2.0.0',
                        applicationLegalese: 'Hệ thống đưa đón sinh viên ĐH Cần Thơ',
                      );
                    },
                  ),
                  const Divider(height: 1),
                  ListTile(
                    leading: const Icon(Icons.logout_rounded, color: Colors.redAccent),
                    title: const Text(
                      'Đăng xuất',
                      style: TextStyle(color: Colors.redAccent, fontWeight: FontWeight.bold),
                    ),
                    onTap: () => _confirmLogout(context),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }

  Widget _buildAssignedVehicleCard() {
    if (_assignedVehicle == null) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.grey.shade300),
        ),
        child: Row(
          children: [
            Container(
              width: 50,
              height: 50,
              decoration: BoxDecoration(
                color: Colors.grey.shade100,
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Icon(
                Icons.directions_bus_outlined,
                color: Colors.grey,
                size: 28,
              ),
            ),
            const SizedBox(width: 14),
            const Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Chưa được gán phương tiện',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 14,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  SizedBox(height: 2),
                  Text(
                    'Phương tiện sẽ tự động hiển thị sau khi Admin phân tuyến xe.',
                    style: TextStyle(color: Colors.grey, fontSize: 12),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
    }

    final plate = _assignedVehicle!['license_plate']?.toString() ?? 'Chưa cập nhật';
    final capacity = _assignedVehicle!['capacity']?.toString() ?? '40';
    final model = _assignedVehicle!['model']?.toString() ?? 'Hyundai County';
    final rawCode = _assignedVehicle!['code']?.toString();
    final code = (rawCode != null && rawCode.isNotEmpty) ? rawCode : plate;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.teal.withValues(alpha: 0.3)),
        boxShadow: [
          BoxShadow(
            color: AppColors.teal.withValues(alpha: 0.05),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 50,
            height: 50,
            decoration: BoxDecoration(
              color: AppColors.teal.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(
              Icons.directions_bus_filled_rounded,
              color: AppColors.teal,
              size: 30,
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Xe buýt #$code (Biển số: $plate)',
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  'Sức chứa: $capacity chỗ ngồi · Loại xe: $model',
                  style: const TextStyle(color: Colors.grey, fontSize: 12),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _statCard(String title, String val, IconData icon) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.grey.shade200),
      ),
      child: Column(
        children: [
          Icon(icon, color: AppColors.teal, size: 22),
          const SizedBox(height: 6),
          Text(
            val,
            style: const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
              color: Color(0xFF181C1D),
            ),
          ),
          const SizedBox(height: 2),
          Text(
            title,
            textAlign: TextAlign.center,
            style: const TextStyle(color: Colors.grey, fontSize: 10),
          ),
        ],
      ),
    );
  }
}
