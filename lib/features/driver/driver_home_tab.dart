import 'package:flutter/material.dart';
import '../../services/api_service.dart';
import '../../services/gps_service.dart';
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

    _isShiftActive = GpsService().isTracking;

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
      final driverId = widget.user['id']?.toString() ?? '';
      final routes = await widget.api.fetchDriverRoutes(driverId);
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

  Map<String, dynamic>? _selectAssignedRoute() {
    final today = DateTime.now();
    final todayKey = DateTime(today.year, today.month, today.day);
    final routes = _assignedRoutes
        .whereType<Map>()
        .map((route) => Map<String, dynamic>.from(route))
        .where((route) {
      final serviceDate =
          DateTime.tryParse(route['service_date']?.toString() ?? '');
      if (serviceDate == null) return false;
      final serviceDay =
          DateTime(serviceDate.year, serviceDate.month, serviceDate.day);
      return serviceDay == todayKey;
    }).toList();
    if (routes.isEmpty) return null;

    for (final route in routes) {
      if (route['status']?.toString().toLowerCase() == 'in_progress') {
        return route;
      }
    }

    final available = routes.where((route) {
      final status = route['status']?.toString().toLowerCase();
      return status != 'completed' && status != 'rejected';
    }).toList();
    if (available.isEmpty) return null;

    available.sort((a, b) {
      final aDate = DateTime.tryParse(a['service_date']?.toString() ?? '');
      final bDate = DateTime.tryParse(b['service_date']?.toString() ?? '');
      if (aDate == null) return bDate == null ? 0 : 1;
      if (bDate == null) return -1;
      return aDate.compareTo(bDate);
    });
    return available.first;
  }

  Future<void> _toggleShift() async {
    final nextRoute = _selectAssignedRoute();
    final routeId = nextRoute?['id']?.toString() ?? '';

    final willBeActive = !_isShiftActive;

    if (willBeActive) {
      if (routeId.isEmpty) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Bạn chưa được phân công chuyến xe.')),
        );
        return;
      }
      try {
        await widget.api.startRoute(routeId);
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Không thể bắt đầu chuyến xe: $e'),
              backgroundColor: Colors.red[800],
            ),
          );
        }
        return;
      }
      setState(() => _isShiftActive = true);
      final success = await GpsService().startTracking(
        routeId: routeId,
        api: widget.api,
      );
      if (mounted) {
        final msg = success
            ? 'Đã bắt đầu ca làm việc. Vị trí xe được cập nhật định kỳ.'
            : 'Chuyến đã bắt đầu nhưng chưa gửi được GPS. Hãy bật định vị và cấp quyền vị trí.';
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(msg),
            backgroundColor: success ? AppColors.teal : Colors.orange[800],
          ),
        );
      }
    } else {
      if (routeId.isNotEmpty) {
        try {
          await widget.api.endRoute(routeId);
        } catch (e) {
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text('Không thể kết thúc chuyến xe: $e'),
                backgroundColor: Colors.red[800],
              ),
            );
          }
          return;
        }
      }
      GpsService().stopTracking();
      setState(() => _isShiftActive = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text(
                'Đã kết thúc ca làm việc và chuyển chuyến xe sang trạng thái hoàn tất.'),
            backgroundColor: Colors.grey[800],
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final driverName = widget.user['full_name']?.toString() ??
        widget.user['username']?.toString() ??
        'Tài xế';
    final nextRoute = _selectAssignedRoute();

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
            const Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              mainAxisSize: MainAxisSize.min,
              children: [
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
