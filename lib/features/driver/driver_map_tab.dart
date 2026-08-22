import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../../services/api_service.dart';
import '../../theme/app_theme.dart';

class DriverMapTab extends StatefulWidget {
  const DriverMapTab({
    super.key,
    required this.api,
    this.initialRoute,
  });

  final ApiService api;
  final Map<String, dynamic>? initialRoute;

  @override
  State<DriverMapTab> createState() => _DriverMapTabState();
}

class _DriverMapTabState extends State<DriverMapTab> {
  late MapController _mapController;
  String _selectedFilter = 'all';
  bool _isBusy = false;
  String? _tripStatus;
  
  // Realtime simulated bus movement
  LatLng _busPos = const LatLng(10.0299, 105.7684); // Can Tho CTU Depot
  double _busLat = 10.0299;
  double _busStep = 0.00025;
  Timer? _gpsTimer;

  static const List<_MapStop> _routeStops = [
    _MapStop(LatLng(10.0299, 105.7684), 'Trạm Depot - ĐH Cần Thơ (Khu II)', '08:00 AM', 'passed'),
    _MapStop(LatLng(10.0342, 105.7876), 'Trạm 1 - Bến Ninh Kiều', '08:12 AM', 'active'),
    _MapStop(LatLng(10.0031, 105.7482), 'Trạm 2 - Chợ Cái Răng', '08:25 AM', 'upcoming'),
    _MapStop(LatLng(10.0461, 105.7891), 'Trạm 3 - Công viên Sông Hậu', '08:38 AM', 'upcoming'),
    _MapStop(LatLng(10.0402, 105.7621), 'Trạm 4 - Lotte Mart Cần Thơ', '08:50 AM', 'upcoming'),
  ];

  @override
  void initState() {
    super.initState();
    _mapController = MapController();
    _tripStatus = widget.initialRoute?['status']?.toString() ?? 'pending';

    // Start simulated GPS timer for driver moving on map
    _gpsTimer = Timer.periodic(const Duration(milliseconds: 1500), (_) {
      if (!mounted || _tripStatus != 'in_progress') return;
      setState(() {
        _busLat += _busStep;
        if (_busLat > 10.0460) _busStep = -0.00025;
        if (_busLat < 10.0290) _busStep = 0.00025;
        _busPos = LatLng(_busLat, 105.7684 + (_busLat - 10.0299) * 0.8);
      });
    });
  }

  @override
  void dispose() {
    _gpsTimer?.cancel();
    _mapController.dispose();
    super.dispose();
  }

  Future<void> _handleTripAction() async {
    final routeId = widget.initialRoute?['id'] as int? ?? 1;
    setState(() => _isBusy = true);
    try {
      if (_tripStatus == 'in_progress') {
        final res = await widget.api.endRoute(routeId);
        setState(() => _tripStatus = res['status'] ?? 'completed');
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Đã hoàn thành chuyến xe thành công!'),
              backgroundColor: AppColors.teal,
            ),
          );
        }
      } else {
        final res = await widget.api.startRoute(routeId);
        setState(() => _tripStatus = res['status'] ?? 'in_progress');
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Đã BẮT ĐẦU chuyến xe! Tọa độ GPS đang cập nhật.'),
              backgroundColor: AppColors.teal,
            ),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Lỗi cập nhật chuyến: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _isBusy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final routeId = widget.initialRoute?['id']?.toString() ?? '1';

    return Scaffold(
      backgroundColor: const Color(0xFFF6FAFA),
      appBar: AppBar(
        backgroundColor: AppColors.teal,
        title: Text('Tuyến xe #$routeId & Bản đồ realtime'),
        elevation: 1,
        actions: [
          IconButton(
            icon: const Icon(Icons.my_location_rounded),
            onPressed: () {
              _mapController.move(_busPos, 14.5);
            },
          ),
        ],
      ),
      body: Stack(
        children: [
          // FlutterMap Area
          FlutterMap(
            mapController: _mapController,
            options: MapOptions(
              initialCenter: _busPos,
              initialZoom: 14.0,
            ),
            children: [
              TileLayer(
                urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                userAgentPackageName: 'com.myctubus.app',
              ),
              // Route Polyline
              PolylineLayer(
                polylines: [
                  Polyline(
                    points: _routeStops.map((s) => s.pos).toList(),
                    color: AppColors.teal,
                    strokeWidth: 4.5,
                  ),
                ],
              ),
              // Stop Markers
              MarkerLayer(
                markers: [
                  for (final stop in _routeStops)
                    Marker(
                      point: stop.pos,
                      width: 40,
                      height: 40,
                      child: Tooltip(
                        message: stop.name,
                        child: Container(
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: stop.status == 'active'
                                ? Colors.orangeAccent
                                : (stop.status == 'passed'
                                    ? Colors.grey
                                    : AppColors.teal),
                            border: Border.all(color: Colors.white, width: 2),
                            boxShadow: const [
                              BoxShadow(color: Colors.black26, blurRadius: 4),
                            ],
                          ),
                          child: Icon(
                            stop.status == 'active'
                                ? Icons.location_on
                                : Icons.directions_bus_filled,
                            color: Colors.white,
                            size: 20,
                          ),
                        ),
                      ),
                    ),
                  // Realtime Bus Marker
                  Marker(
                    point: _busPos,
                    width: 50,
                    height: 50,
                    child: Container(
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: Colors.white,
                        border: Border.all(color: AppColors.teal, width: 3),
                        boxShadow: const [
                          BoxShadow(color: Colors.black38, blurRadius: 8),
                        ],
                      ),
                      child: const Center(
                        child: Icon(
                          Icons.directions_bus_rounded,
                          color: AppColors.teal,
                          size: 28,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),

          // Top Route Filter Pills
          Positioned(
            top: 12,
            left: 12,
            right: 12,
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  _filterChip('all', 'Tất cả'),
                  const SizedBox(width: 8),
                  _filterChip('r1', 'Tuyến 1 - Khu II'),
                  const SizedBox(width: 8),
                  _filterChip('r2', 'Tuyến 2 - Bến Ninh Kiều'),
                  const SizedBox(width: 8),
                  _filterChip('r3', 'Tuyến 3 - Hòa An'),
                ],
              ),
            ),
          ),

          // Bottom Sheet: Control & Stop Timeline
          DraggableScrollableSheet(
            initialChildSize: 0.38,
            minChildSize: 0.18,
            maxChildSize: 0.70,
            builder: (context, scrollController) {
              return Container(
                decoration: const BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black12,
                      blurRadius: 16,
                      offset: Offset(0, -4),
                    ),
                  ],
                ),
                child: ListView(
                  controller: scrollController,
                  padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                  children: [
                    // Handle Bar
                    Center(
                      child: Container(
                        width: 44,
                        height: 5,
                        decoration: BoxDecoration(
                          color: Colors.grey[300],
                          borderRadius: BorderRadius.circular(10),
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),

                    // Trip Status & Action Button
                    Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Trạng thái: ${_statusLabel(_tripStatus)}',
                                style: TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.bold,
                                  color: _statusColor(_tripStatus),
                                ),
                              ),
                              const SizedBox(height: 2),
                              const Text(
                                'Tốc độ trung bình: 28 km/h',
                                style: TextStyle(fontSize: 12, color: Colors.grey),
                              ),
                            ],
                          ),
                        ),
                        FilledButton.icon(
                          onPressed: _isBusy || _tripStatus == 'completed'
                              ? null
                              : _handleTripAction,
                          style: FilledButton.styleFrom(
                            backgroundColor: _tripStatus == 'in_progress'
                                ? Colors.redAccent
                                : AppColors.teal,
                            padding: const EdgeInsets.symmetric(
                                horizontal: 16, vertical: 12),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12),
                            ),
                          ),
                          icon: Icon(_tripStatus == 'in_progress'
                              ? Icons.stop_rounded
                              : Icons.play_arrow_rounded),
                          label: Text(_tripStatus == 'in_progress'
                              ? 'Kết thúc chuyến'
                              : 'Bắt đầu chuyến'),
                        ),
                      ],
                    ),

                    const Divider(height: 24),

                    // Stops Timeline Title
                    const Text(
                      'Tiến độ các trạm dừng (Stops Timeline)',
                      style: TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF181C1D),
                      ),
                    ),
                    const SizedBox(height: 12),

                    // Timeline items
                    for (int i = 0; i < _routeStops.length; i++) ...[
                      _timelineTile(_routeStops[i], isLast: i == _routeStops.length - 1),
                    ],

                    const SizedBox(height: 20),
                  ],
                ),
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _filterChip(String id, String label) {
    final selected = _selectedFilter == id;
    return ChoiceChip(
      label: Text(label),
      selected: selected,
      selectedColor: AppColors.teal,
      backgroundColor: Colors.white,
      labelStyle: TextStyle(
        color: selected ? Colors.white : Colors.black87,
        fontWeight: FontWeight.w600,
        fontSize: 13,
      ),
      onSelected: (val) {
        if (val) setState(() => _selectedFilter = id);
      },
      elevation: 2,
    );
  }

  Widget _timelineTile(_MapStop stop, {required bool isLast}) {
    Color dotColor = AppColors.teal;
    if (stop.status == 'passed') dotColor = Colors.grey;
    if (stop.status == 'active') dotColor = Colors.orange;

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Column(
          children: [
            Container(
              width: 16,
              height: 16,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: dotColor,
                border: Border.all(color: Colors.white, width: 2),
                boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 2)],
              ),
            ),
            if (!isLast)
              Container(
                width: 2,
                height: 40,
                color: Colors.grey[300],
              ),
          ],
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.only(bottom: 14),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        stop.name,
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: stop.status == 'active'
                              ? FontWeight.bold
                              : FontWeight.w500,
                          color: stop.status == 'passed'
                              ? Colors.grey
                              : Colors.black87,
                        ),
                      ),
                      Text(
                        'Dự kiến: ${stop.time}',
                        style: const TextStyle(fontSize: 12, color: Colors.grey),
                      ),
                    ],
                  ),
                ),
                if (stop.status == 'active')
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: Colors.orange.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: const Text(
                      'Trạm hiện tại',
                      style: TextStyle(
                        color: Colors.orange,
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  String _statusLabel(String? status) {
    switch (status) {
      case 'in_progress':
        return 'Đang di chuyển (In Progress)';
      case 'completed':
        return 'Đã hoàn thành';
      default:
        return 'Chưa bắt đầu';
    }
  }

  Color _statusColor(String? status) {
    switch (status) {
      case 'in_progress':
        return AppColors.teal;
      case 'completed':
        return Colors.green;
      default:
        return Colors.orange;
    }
  }
}

class _MapStop {
  const _MapStop(this.pos, this.name, this.time, this.status);
  final LatLng pos;
  final String name;
  final String time;
  final String status; // passed, active, upcoming
}
