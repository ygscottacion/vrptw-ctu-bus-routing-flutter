import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../theme/app_theme.dart';
import '../services/api_service.dart';

class MapScreen extends StatefulWidget {
  const MapScreen({super.key, required this.api});
  final ApiService api;

  @override
  State<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends State<MapScreen> {
  String _selectedRoute = 'all';
  LatLng _busPos = const LatLng(10.0300, 105.7683);
  double _busLat = 10.0300;
  double _busDir = 0.0002;
  Timer? _busTimer;
  List<_BusStop> _dynamicStops = [];

  static const _busStops = [
    _BusStop(LatLng(10.0299, 105.7684), 'Depot - ĐH Cần Thơ (Khu II)', 'start',
        [1, 2, 3]),
    _BusStop(
        LatLng(10.0342, 105.7876), 'Trạm 1 - Bến Ninh Kiều', 'mid', [1, 2]),
    _BusStop(
        LatLng(10.0031, 105.7482), 'Trạm 2 - Chợ Cái Răng', 'mid', [1, 2, 3]),
    _BusStop(LatLng(10.0461, 105.7891), 'Trạm 3 - Công viên Sông Hậu',
        'highlight', [1]),
    _BusStop(LatLng(10.0402, 105.7621), 'Trạm 4 - Siêu thị Lotte Mart', 'mid',
        [1, 3]),
    _BusStop(LatLng(10.0215, 105.7531), 'Trạm 5 - Bệnh viện ĐKTW Cần Thơ',
        'highlight', [2, 3]),
    _BusStop(
        LatLng(10.0435, 105.7820), 'Trạm 6 - Chợ Đêm Trần Phú', 'end', [2]),
    _BusStop(
        LatLng(10.0156, 105.7645), 'Trạm 7 - Siêu thị GO! Cần Thơ', 'mid', [3]),
  ];

  static const _routeInfo = [
    _RouteStop('Trường Đại học Cần Thơ', '06:00', 'start'),
    _RouteStop('Vincom Xuân Khánh', '06:15', 'mid'),
    _RouteStop('Bến Ninh Kiều', '06:25', 'mid'),
    _RouteStop('Vincom Hùng Vương', '06:35', 'mid'),
    _RouteStop('Bến xe Cần Thơ', '06:50', 'end'),
  ];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _loadBackendLocations();
    });
    // TODO Ngay 6: xoa Timer gia lap nay, thay bang polling API vi tri that moi 15 giay
    // (theo audit_lib_screens_day1.md - vi pham yeu cau MVP "khong hien thi xe gia").
    _busTimer = Timer.periodic(const Duration(milliseconds: 1200), (_) {
      if (!mounted) return;
      setState(() {
        _busLat += _busDir;
        if (_busLat > 10.0500) _busDir = -0.0002;
        if (_busLat < 10.0300) _busDir = 0.0002;
        _busPos = LatLng(_busLat, 105.7801 + (_busLat - 10.0300) * 0.5);
      });
    });
  }

  Future<void> _loadBackendLocations() async {
    try {
      final data = await widget.api.fetchLocations();
      if (data.isNotEmpty && mounted) {
        setState(() {
          _dynamicStops = data.map((item) {
            final lat = (item['latitude'] as num).toDouble();
            final lng = (item['longitude'] as num).toDouble();
            final name = item['name'] as String;
            final isDepot = name.toLowerCase().contains('depot');
            return _BusStop(
              LatLng(lat, lng),
              name,
              isDepot ? 'start' : 'mid',
              [1, 2, 3],
            );
          }).toList();
        });
      }
    } catch (_) {
      // Dùng danh sách mặc định nếu chưa lấy được dữ liệu từ Backend
    }
  }

  @override
  void dispose() {
    _busTimer?.cancel();
    super.dispose();
  }

  Color _stopColor(String type) {
    switch (type) {
      case 'start':
        return AppColors.green;
      case 'end':
        return AppColors.red;
      case 'highlight':
        return AppColors.purple;
      default:
        return AppColors.teal;
    }
  }

  List<_BusStop> get _effectiveStops {
    return _dynamicStops.isNotEmpty ? _dynamicStops : _busStops;
  }

  List<_BusStop> get _visibleStops {
    if (_selectedRoute == 'all') return _effectiveStops;
    final n = int.parse(_selectedRoute);
    return _effectiveStops.where((s) => s.routes.contains(n)).toList();
  }

  List<LatLng> _getRouteCoords(int routeNum) {
    return _effectiveStops
        .where((s) => s.routes.contains(routeNum))
        .map((s) => s.pos)
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Bản đồ tuyến xe')),
      body: Column(
        children: [
          _buildFilterBar(),
          Expanded(child: _buildMap()),
          _buildInfoPanel(),
        ],
      ),
    );
  }

  Widget _buildFilterBar() {
    final filters = [
      ('all', 'Tất cả'),
      ('1', 'Tuyến 1'),
      ('2', 'Tuyến 2'),
      ('3', 'Tuyến 3'),
    ];
    return Container(
      color: AppColors.white,
      padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md, vertical: AppSpacing.sm),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: filters.map((f) {
            final isActive = _selectedRoute == f.$1;
            return Padding(
              padding: const EdgeInsets.only(right: AppSpacing.sm),
              child: GestureDetector(
                onTap: () => setState(() => _selectedRoute = f.$1),
                child: Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: AppSpacing.lg, vertical: 7),
                  decoration: BoxDecoration(
                    color: isActive ? AppColors.teal : Colors.transparent,
                    borderRadius: BorderRadius.circular(AppRadius.full),
                    border: Border.all(
                      color: isActive ? AppColors.teal : AppColors.border,
                      width: 1.5,
                    ),
                  ),
                  child: Text(
                    f.$2,
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color:
                          isActive ? AppColors.white : AppColors.textSecondary,
                    ),
                  ),
                ),
              ),
            );
          }).toList(),
        ),
      ),
    );
  }

  Widget _buildMap() {
    return FlutterMap(
      options: const MapOptions(
        initialCenter: LatLng(10.0380, 105.7830),
        initialZoom: 14,
      ),
      children: [
        TileLayer(
          urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
          userAgentPackageName: 'com.ctu.myctubus_flutter',
        ),
        // Route polylines
        PolylineLayer(polylines: [
          if (_selectedRoute == 'all' || _selectedRoute == '1')
            Polyline(
                points: _getRouteCoords(1),
                color: AppColors.teal,
                strokeWidth: 4),
          if (_selectedRoute == 'all' || _selectedRoute == '2')
            Polyline(
                points: _getRouteCoords(2),
                color: AppColors.purple,
                strokeWidth: 4),
          if (_selectedRoute == 'all' || _selectedRoute == '3')
            Polyline(
                points: _getRouteCoords(3),
                color: AppColors.orange,
                strokeWidth: 4),
        ]),
        // Bus stop markers
        MarkerLayer(
          markers: [
            ..._visibleStops.map((s) => Marker(
                  point: s.pos,
                  width: 36,
                  height: 36,
                  child: Tooltip(
                    message: s.name,
                    child: Container(
                      decoration: BoxDecoration(
                        color: _stopColor(s.type),
                        shape: BoxShape.circle,
                        border: Border.all(color: Colors.white, width: 2),
                        boxShadow: [
                          BoxShadow(
                              color: _stopColor(s.type).withValues(alpha: 0.4),
                              blurRadius: 6)
                        ],
                      ),
                      child: const Icon(Icons.circle,
                          color: Colors.white, size: 10),
                    ),
                  ),
                )),
            // Animated bus marker
            Marker(
              point: _busPos,
              width: 44,
              height: 44,
              child: Container(
                decoration: BoxDecoration(
                  color: AppColors.teal,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: Colors.white, width: 2),
                  boxShadow: [
                    BoxShadow(
                        color: AppColors.teal.withValues(alpha: 0.5),
                        blurRadius: 8,
                        offset: const Offset(0, 3))
                  ],
                ),
                child: const Center(
                    child: Text('🚌', style: TextStyle(fontSize: 20))),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildInfoPanel() {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius:
            const BorderRadius.vertical(top: Radius.circular(AppRadius.md)),
        boxShadow: [
          BoxShadow(
              color: Colors.black.withValues(alpha: 0.08),
              blurRadius: 12,
              offset: const Offset(0, -4))
        ],
      ),
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Tuyến đang chọn',
                  style: TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                      color: AppColors.textPrimary)),
              Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.sm, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.teal,
                  borderRadius: BorderRadius.circular(AppRadius.full),
                ),
                child: Text(
                  _selectedRoute == 'all'
                      ? 'Tất cả tuyến'
                      : 'Tuyến $_selectedRoute',
                  style: const TextStyle(
                      color: Colors.white,
                      fontSize: 12,
                      fontWeight: FontWeight.w600),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          SizedBox(
            height: 160,
            child: ListView.builder(
              itemCount: _routeInfo.length,
              itemBuilder: (_, i) {
                final stop = _routeInfo[i];
                final isFirst = stop.role == 'start';
                final isLast = stop.role == 'end';
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SizedBox(
                      width: 28,
                      child: Column(
                        children: [
                          Container(
                            width: 14,
                            height: 14,
                            margin: const EdgeInsets.only(top: 4),
                            decoration: BoxDecoration(
                              color: isFirst
                                  ? AppColors.green
                                  : isLast
                                      ? AppColors.red
                                      : AppColors.teal,
                              shape: BoxShape.circle,
                              border: Border.all(color: Colors.white, width: 2),
                            ),
                          ),
                          if (i < _routeInfo.length - 1)
                            Container(
                                width: 2, height: 36, color: AppColors.border),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(stop.name,
                                style: const TextStyle(
                                    fontSize: 13,
                                    fontWeight: FontWeight.w600,
                                    color: AppColors.textPrimary)),
                            Text(
                              '${stop.time} - ${isFirst ? 'Điểm xuất phát' : isLast ? 'Điểm cuối' : 'Trạm dừng'}',
                              style: const TextStyle(
                                  fontSize: 11, color: AppColors.textMuted),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _BusStop {
  final LatLng pos;
  final String name;
  final String type;
  final List<int> routes;
  const _BusStop(this.pos, this.name, this.type, this.routes);
}

class _RouteStop {
  final String name;
  final String time;
  final String role;
  const _RouteStop(this.name, this.time, this.role);
}
