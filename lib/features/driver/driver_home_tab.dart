import 'package:flutter/material.dart';
import '../../services/api_service.dart';
import '../../theme/app_theme.dart';
import 'widgets/driver_shift_button.dart';
import 'widgets/driver_route_card.dart';
import 'widgets/driver_vehicle_status.dart';

class DriverHomeTab extends StatefulWidget {
  const DriverHomeTab({
    super.key,
    required this.user,
    required this.api,
    required this.onSelectRoute,
  });

  final Map<String, dynamic> user;
  final ApiService api;
  final ValueChanged<Map<String, dynamic>> onSelectRoute;

  @override
  State<DriverHomeTab> createState() => _DriverHomeTabState();
}

class _DriverHomeTabState extends State<DriverHomeTab>
    with SingleTickerProviderStateMixin {
  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;
  bool _isShiftActive = false;
  List<dynamic> _assignedRoutes = [];
  bool _isLoading = true;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);

    _pulseAnimation = Tween<double>(begin: 1.0, end: 1.08).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    _loadDriverRoutes();
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  Future<void> _loadDriverRoutes() async {
    if (!mounted) return;
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    try {
      final routes = await widget.api.fetchDriverRoutes();
      if (mounted) {
        setState(() {
          _assignedRoutes = routes;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = 'Không thể tải danh sách tuyến: $e';
          _isLoading = false;
        });
      }
    }
  }

  void _toggleShift() {
    setState(() => _isShiftActive = !_isShiftActive);
    final msg = _isShiftActive
        ? 'Đã bắt đầu ca làm việc! Hệ thống đang phát vị trí xe buýt.'
        : 'Đã kết thúc ca làm việc.';
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(msg),
        backgroundColor: _isShiftActive ? AppColors.teal : Colors.grey[800],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final driverName =
        widget.user['full_name']?.toString() ?? widget.user['username']?.toString() ?? 'Tài xế';
    final nextRoute = _assignedRoutes.isNotEmpty
        ? Map<String, dynamic>.from(_assignedRoutes.first as Map)
        : null;

    return Scaffold(
      backgroundColor: const Color(0xFFF6FAFA),
      appBar: AppBar(
        backgroundColor: AppColors.teal,
        elevation: 0,
        toolbarHeight: 70,
        automaticallyImplyLeading: false,
        title: Row(
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: Colors.white24,
                border: Border.all(color: Colors.white, width: 1.5),
              ),
              child: const Icon(Icons.person, color: Colors.white, size: 26),
            ),
            const SizedBox(width: 12),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'DRIVER',
                  style: TextStyle(
                    color: Colors.white70,
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 1.2,
                  ),
                ),
                Text(
                  driverName,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const Spacer(),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              mainAxisSize: MainAxisSize.min,
              children: const [
                Text(
                  'MyCTU BUS',
                  style: TextStyle(
                    color: Color(0xFFFFDDB9),
                    fontSize: 18,
                    fontWeight: FontWeight.w900,
                    fontStyle: FontStyle.italic,
                  ),
                ),
                Text(
                  'Driver Mode',
                  style: TextStyle(
                    color: Colors.white60,
                    fontSize: 10,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
      body: RefreshIndicator(
        onRefresh: _loadDriverRoutes,
        color: AppColors.teal,
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Nút bật/tắt Ca làm việc
              DriverShiftButton(
                isShiftActive: _isShiftActive,
                pulseAnimation: _pulseAnimation,
                onToggleShift: _toggleShift,
              ),

              const SizedBox(height: 16),

              // Thẻ hiển thị chuyến xe tiếp theo (Up Next Route)
              DriverRouteCard(
                isLoading: _isLoading,
                errorMessage: _errorMessage,
                nextRoute: nextRoute,
                onRefresh: _loadDriverRoutes,
                onSelectRoute: widget.onSelectRoute,
              ),

              const SizedBox(height: 24),

              // Bento Grid trạng thái phương tiện
              const DriverVehicleStatus(),

              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }
}
