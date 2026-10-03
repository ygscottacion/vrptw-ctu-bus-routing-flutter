import 'dart:async';
import 'dart:math' show Point;
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:maplibre_gl/maplibre_gl.dart' as ml;
import 'package:latlong2/latlong.dart';
import '../theme/app_theme.dart';
import '../services/api_service.dart';
import '../services/routing_service.dart';
import '../config/api_config.dart';

class MapScreen extends StatefulWidget {
  const MapScreen({super.key, required this.api});
  final ApiService api;

  @override
  State<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends State<MapScreen>
    with SingleTickerProviderStateMixin {
  final MapController _mapController = MapController();
  ml.MapLibreMapController? _goongMapController;
  bool _overlayMapReady = false;
  late TabController _tabController;

  String _selectedRouteId = '—';
  String _routeName = 'Chưa có tuyến được gán';
  String _routeDirection = '';
  String? _selectedRouteApiId;
  double _selectedRouteDistance = 0;
  DateTime _selectedDate = DateTime.now();
  Timer? _pollingTimer;

  _BusStop? _selectedStopForTooltip;
  List<_BusStop> _dynamicStops = [];
  List<dynamic> _activeRoutes = [];
  final Map<String, LatLng> _realBusPositions = {};
  final Map<int, List<LatLng>> _roadPolylines = {};

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _tabController.addListener(() {
      if (mounted) setState(() {});
    });
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        _loadActiveRoutes();
      }
    });
    _startGpsPolling();
  }

  @override
  void dispose() {
    _tabController.dispose();
    _pollingTimer?.cancel();
    super.dispose();
  }

  void _syncOverlayCamera([ml.CameraPosition? cameraPosition]) {
    if (!_overlayMapReady) return;
    final camera = cameraPosition ?? _goongMapController?.cameraPosition;
    if (camera == null) return;
    _mapController.move(
      LatLng(camera.target.latitude, camera.target.longitude),
      camera.zoom,
    );
    _mapController.rotate(camera.bearing);
  }

  void _moveMapTo(LatLng center, double zoom) {
    if (_overlayMapReady) _mapController.move(center, zoom);
    _goongMapController?.animateCamera(
      ml.CameraUpdate.newLatLngZoom(
        ml.LatLng(center.latitude, center.longitude),
        zoom,
      ),
    );
  }

  Future<void> _fetchRoadPolylines() async {
    final waypoints = _effectiveStops.map((s) => s.pos).toList();
    if (waypoints.length < 2) return;
    final roadPts = await RoutingService().getDrivingRoute(waypoints);
    if (mounted && roadPts.isNotEmpty) {
      setState(() => _roadPolylines[1] = roadPts);
    }
  }

  Future<void> _loadActiveRoutes() async {
    try {
      final routes = await widget.api.fetchActiveRoutes();
      List<dynamic> tickets = [];
      try {
        tickets = await widget.api.fetchMyTickets();
      } catch (_) {}
      final assignedTickets = tickets
          .whereType<Map>()
          .where((ticket) => ticket['status']?.toString() == 'assigned')
          .where((ticket) => ticket['route_id'] != null)
          .toList()
        ..sort((a, b) => (a['service_date']?.toString() ?? '')
            .compareTo(b['service_date']?.toString() ?? ''));
      final today = DateTime.now().toIso8601String().split('T').first;
      final upcomingTickets = assignedTickets
          .where((ticket) =>
              (ticket['service_date']?.toString() ?? '').compareTo(today) >= 0)
          .toList();
      String? preferredRouteId;
      if (upcomingTickets.isNotEmpty) {
        preferredRouteId = upcomingTickets.first['route_id']?.toString();
      } else if (assignedTickets.isNotEmpty) {
        preferredRouteId = assignedTickets.first['route_id']?.toString();
      }
      final matchingRoutes = routes.whereType<Map>().where((route) {
        return route['id']?.toString() == preferredRouteId;
      }).toList();
      final Map? selectedRoute = matchingRoutes.isNotEmpty
          ? matchingRoutes.first
          : (routes.isNotEmpty ? routes.first as Map : null);

      final rawStops = selectedRoute?['stops'] as List<dynamic>? ?? const [];
      final stops = <_BusStop>[];
      for (var i = 0; i < rawStops.length; i++) {
        final stop = rawStops[i];
        if (stop is! Map) continue;
        final location = stop['location'] as Map? ?? const {};
        final latitude = (location['latitude'] as num?)?.toDouble();
        final longitude = (location['longitude'] as num?)?.toDouble();
        if (latitude == null || longitude == null) continue;
        stops.add(_BusStop(
          LatLng(latitude, longitude),
          location['name']?.toString() ?? 'Trạm ${i + 1}',
          i == 0 ? 'start' : (i == rawStops.length - 1 ? 'end' : 'mid'),
          const [1],
          _formatArrivalTime(stop['arrival_time']?.toString()),
        ));
      }

      if (!mounted) return;
      final selectedId = selectedRoute?['id']?.toString();
      final routeChanged = selectedId != _selectedRouteApiId;
      setState(() {
        _activeRoutes = selectedRoute == null ? [] : [selectedRoute];
        _dynamicStops = stops;
        if (routeChanged) _roadPolylines.clear();
        _selectedRouteApiId = selectedId;
        _selectedRouteId = selectedId == null
            ? '—'
            : 'CT-${selectedId.substring(0, selectedId.length < 8 ? selectedId.length : 8).toUpperCase()}';
        _selectedRouteDistance =
            (selectedRoute?['total_distance'] as num?)?.toDouble() ?? 0;
        final firstName = stops.isNotEmpty ? stops.first.name : '';
        final lastName = stops.length > 1 ? stops.last.name : '';
        _routeName = stops.isEmpty
            ? 'Chưa có tuyến được gán'
            : (lastName.isEmpty ? firstName : '$firstName - $lastName');
        final tripType = selectedRoute?['trip_type']?.toString();
        final sessionId = selectedRoute?['session_id']?.toString();
        _routeDirection = [
          if (tripType != null) tripType == 'pickup' ? 'Chiều đi' : 'Chiều về',
          if (sessionId != null) sessionId,
        ].join(' • ');
        _selectedStopForTooltip = null;
      });
      if (routeChanged && stops.isNotEmpty) _moveMapTo(stops.first.pos, 13.5);
      if ((routeChanged || !_roadPolylines.containsKey(1)) && stops.length >= 2) {
        _fetchRoadPolylines();
      }
    } catch (_) {
      // Keep the last successfully loaded route visible during temporary errors.
    }
  }

  String _formatArrivalTime(String? value) {
    if (value == null || value.isEmpty) return '—';
    try {
      final time = DateTime.parse(value).toLocal();
      return '${time.hour.toString().padLeft(2, '0')}:${time.minute.toString().padLeft(2, '0')}';
    } catch (_) {
      return value;
    }
  }

  void _startGpsPolling() {
    _pollingTimer = Timer.periodic(const Duration(seconds: 20), (_) {
      _loadActiveRoutes();
      _pollGpsPositions();
    });
  }

  Future<void> _pollGpsPositions() async {
    if (_activeRoutes.isEmpty) return;
    for (final route in _activeRoutes) {
      final routeId = route['id']?.toString();
      if (routeId == null) continue;
      try {
        final gps = await widget.api.fetchLatestGps(routeId);
        if (gps != null && gps.containsKey('latitude') && gps.containsKey('longitude')) {
          final lat = (gps['latitude'] as num).toDouble();
          final lng = (gps['longitude'] as num).toDouble();
          if (mounted) {
            setState(() {
              _realBusPositions[routeId] = LatLng(lat, lng);
            });
          }
        }
      } catch (_) {}
    }
  }

  List<_BusStop> get _effectiveStops => _dynamicStops;

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

  String get _displayDirectionName {
    return _routeName;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bg,
      body: SafeArea(
        child: Stack(
          children: [
            // Layer 1: Flutter Map & Controls
            _buildMapLayer(),

            // Layer 2: Top Floating Navigation & Controls
            _buildTopControls(),

            // Layer 3: Selected Stop Banner Tooltip
            if (_selectedStopForTooltip != null) _buildStopTooltipBanner(),

            // Layer 4: Draggable Bottom Sheet with 3 Tabs
            _buildDraggableSheet(),
          ],
        ),
      ),
    );
  }

  Widget _buildMapLayer() {
    final stopPoints = _effectiveStops.map((s) => s.pos).toList();
    final polylineCoords = _roadPolylines.containsKey(1)
        ? _roadPolylines[1]!
        : stopPoints;

    final center = _effectiveStops.isNotEmpty
        ? _effectiveStops.first.pos
        : const LatLng(10.0380, 105.7830);
    return Stack(
      children: [
        ml.MapLibreMap(
          styleString: ApiConfig.goongMapStyleUrl,
          initialCameraPosition: ml.CameraPosition(
            target: ml.LatLng(center.latitude, center.longitude),
            zoom: 13.5,
          ),
          attributionButtonPosition: ml.AttributionButtonPosition.topLeft,
          attributionButtonMargins: const Point(8, 58),
          trackCameraPosition: true,
          onMapCreated: (controller) => _goongMapController = controller,
          onCameraMove: (camera) => _syncOverlayCamera(camera),
          onCameraIdle: _syncOverlayCamera,
        ),
        IgnorePointer(
          child: FlutterMap(
            mapController: _mapController,
            options: MapOptions(
              initialCenter: center,
              initialZoom: 13.5,
              backgroundColor: Colors.transparent,
              onMapReady: () {
                _overlayMapReady = true;
                _syncOverlayCamera();
              },
              interactionOptions: const InteractionOptions(flags: InteractiveFlag.none),
            ),
            children: [
        PolylineLayer(
          polylines: [
            Polyline(
              points: polylineCoords,
              color: const Color(0xFFEA4335), // Signature Red route line as in screenshot
              strokeWidth: 5,
            ),
          ],
        ),
        MarkerLayer(
          markers: [
            ..._effectiveStops.map((s) {
              final isSelected = _selectedStopForTooltip?.name == s.name;
              return Marker(
                point: s.pos,
                width: isSelected ? 42 : 34,
                height: isSelected ? 42 : 34,
                child: GestureDetector(
                  onTap: () {
                    setState(() {
                      _selectedStopForTooltip = s;
                    });
                    _moveMapTo(s.pos, 15.0);
                  },
                  child: Container(
                    decoration: BoxDecoration(
                      color: _stopColor(s.type),
                      shape: BoxShape.circle,
                      border: Border.all(color: Colors.white, width: isSelected ? 3 : 2),
                      boxShadow: [
                        BoxShadow(
                          color: _stopColor(s.type).withValues(alpha: 0.5),
                          blurRadius: 6,
                        )
                      ],
                    ),
                    child: Icon(
                      Icons.directions_bus_rounded,
                      color: Colors.white,
                      size: isSelected ? 20 : 16,
                    ),
                  ),
                ),
              );
            }),
            // Realtime bus markers
            ..._realBusPositions.entries.map((entry) {
              return Marker(
                point: entry.value,
                width: 44,
                height: 44,
                child: Container(
                  decoration: BoxDecoration(
                    color: AppColors.teal,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: Colors.white, width: 2),
                    boxShadow: [
                      BoxShadow(
                        color: AppColors.teal.withValues(alpha: 0.5),
                        blurRadius: 8,
                        offset: const Offset(0, 3),
                      )
                    ],
                  ),
                  child: const Center(child: Text('🚌', style: TextStyle(fontSize: 20))),
                ),
              );
            }),
          ],
        ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildTopControls() {
    return Positioned(
      top: 12,
      left: 16,
      right: 16,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          // Back button
          GestureDetector(
            onTap: () => Navigator.maybePop(context),
            child: Container(
              width: 40,
              height: 40,
              decoration: const BoxDecoration(
                color: Colors.white,
                shape: BoxShape.circle,
                boxShadow: [BoxShadow(color: Colors.black12, blurRadius: 8)],
              ),
              child: const Icon(Icons.arrow_back_ios_new_rounded, size: 18, color: AppColors.textPrimary),
            ),
          ),
          Row(
            children: [
              // Recenter / Location button
              GestureDetector(
                onTap: () {
                  if (_effectiveStops.isNotEmpty) {
                    _moveMapTo(_effectiveStops.first.pos, 14.5);
                  }
                },
                child: Container(
                  width: 40,
                  height: 40,
                  margin: const EdgeInsets.only(right: 8),
                  decoration: const BoxDecoration(
                    color: Colors.white,
                    shape: BoxShape.circle,
                    boxShadow: [BoxShadow(color: Colors.black12, blurRadius: 8)],
                  ),
                  child: const Icon(Icons.my_location_rounded, size: 20, color: Color(0xFFEA4335)),
                ),
              ),
              // Compass button
              GestureDetector(
                onTap: () {
                  _goongMapController?.animateCamera(ml.CameraUpdate.bearingTo(0));
                },
                child: Container(
                  width: 40,
                  height: 40,
                  decoration: const BoxDecoration(
                    color: Colors.white,
                    shape: BoxShape.circle,
                    boxShadow: [BoxShadow(color: Colors.black12, blurRadius: 8)],
                  ),
                  child: const Icon(Icons.explore_rounded, size: 22, color: Color(0xFFEA4335)),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildStopTooltipBanner() {
    final stop = _selectedStopForTooltip!;
    return Positioned(
      top: 64,
      left: 20,
      right: 20,
      child: GestureDetector(
        onTap: () {
          showModalBottomSheet(
            context: context,
            shape: const RoundedRectangleBorder(
              borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
            ),
            builder: (_) => Container(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(stop.name, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  Text('Giờ đón dự kiến: ${stop.estimatedTime}', style: const TextStyle(fontSize: 14, color: AppColors.teal)),
                  const SizedBox(height: 12),
                  const Text('Tọa độ:', style: TextStyle(fontSize: 12, color: AppColors.textMuted)),
                  Text('${stop.pos.latitude.toStringAsFixed(5)}, ${stop.pos.longitude.toStringAsFixed(5)}',
                      style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500)),
                ],
              ),
            ),
          );
        },
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(16),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.12),
                blurRadius: 10,
                offset: const Offset(0, 4),
              )
            ],
          ),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Text('Xem thông tin trạm', style: TextStyle(fontSize: 11, color: AppColors.textMuted)),
                    Text(stop.name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: AppColors.textPrimary)),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right_rounded, color: AppColors.textMuted),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildDraggableSheet() {
    return DraggableScrollableSheet(
      initialChildSize: 0.50,
      minChildSize: 0.22,
      maxChildSize: 0.88,
      builder: (context, scrollController) {
        return Container(
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
            boxShadow: [
              BoxShadow(color: Colors.black12, blurRadius: 16, offset: Offset(0, -4)),
            ],
          ),
          child: ListView(
            controller: scrollController,
            padding: const EdgeInsets.only(bottom: 24),
            children: [
              // Drag Handle Pill
              Center(
                child: Container(
                  margin: const EdgeInsets.only(top: 10, bottom: 12),
                  width: 36,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.grey.shade300,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),

              // Route Card (Mã tuyến + Tên tuyến + Nút Lượt về/Lượt đi)
              _buildRouteHeaderCard(),

              const SizedBox(height: 8),

              // TabBar Navigation (Danh sách trạm | Biểu đồ giờ | Thông tin)
              TabBar(
                controller: _tabController,
                labelColor: const Color(0xFFEA4335), // Primary Red matching designs
                unselectedLabelColor: AppColors.textMuted,
                indicatorColor: const Color(0xFFEA4335),
                indicatorWeight: 3,
                labelStyle: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                unselectedLabelStyle: const TextStyle(fontWeight: FontWeight.w500, fontSize: 14),
                tabs: const [
                  Tab(text: 'Danh sách trạm'),
                  Tab(text: 'Biểu đồ giờ'),
                  Tab(text: 'Thông tin'),
                ],
              ),

              const Divider(height: 1, color: AppColors.border),
              const SizedBox(height: 12),

              // Tab Content Body
              if (_tabController.index == 0) _buildStopsTab(),
              if (_tabController.index == 1) _buildTimetableTab(),
              if (_tabController.index == 2) _buildInfoTab(),
            ],
          ),
        );
      },
    );
  }

  Widget _buildRouteHeaderCard() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: const Color(0xFFF3F4F6),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Row(
          children: [
            // Code badge
            Text(
              _selectedRouteId,
              style: const TextStyle(
                fontSize: 19,
                fontWeight: FontWeight.w900,
                color: Color(0xFF0F8A5F), // Emerald green code font
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                _displayDirectionName,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                  height: 1.25,
                ),
              ),
            ),
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: const Color(0xFFE6F4EA),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: const Color(0xFF34A853).withValues(alpha: 0.3)),
              ),
              child: Text(
                _routeDirection.isEmpty ? '—' : _routeDirection,
                style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: Color(0xFF137333),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ─── TAB 1: DANH SÁCH TRẠM ───────────────────────────────────
  Widget _buildStopsTab() {
    final stops = _effectiveStops;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Tuyến $_selectedRouteId',
            style: const TextStyle(
              fontSize: 17,
              fontWeight: FontWeight.bold,
              color: Color(0xFFEA4335),
            ),
          ),
          const SizedBox(height: 16),
          if (stops.isEmpty)
            const Text('Tuyến chưa được sinh hoặc chưa được gán cho vé của bạn.')
          else
            ListView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: stops.length,
              itemBuilder: (_, i) {
                final stop = stops[i];
                final isSelected = _selectedStopForTooltip?.name == stop.name;
                return InkWell(
                  onTap: () {
                    setState(() => _selectedStopForTooltip = stop);
                    _moveMapTo(stop.pos, 15.5);
                  },
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SizedBox(
                        width: 24,
                        child: Column(
                          children: [
                            Container(
                              width: 12,
                              height: 12,
                              margin: const EdgeInsets.only(top: 4),
                              decoration: BoxDecoration(
                                color: isSelected
                                    ? const Color(0xFFEA4335)
                                    : const Color(0xFF5F6368),
                                shape: BoxShape.circle,
                              ),
                            ),
                            if (i < stops.length - 1)
                              Container(
                                width: 1.5,
                                height: 38,
                                color: Colors.grey.shade300,
                              ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Padding(
                          padding: const EdgeInsets.only(bottom: 16),
                          child: Text(
                            '${stop.name}  •  ${stop.estimatedTime}',
                            style: TextStyle(
                              fontSize: 14,
                              fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
                              color: isSelected ? const Color(0xFFEA4335) : AppColors.textPrimary,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
        ],
      ),
    );
  }

  // ─── TAB 2: BIỂU ĐỒ GIỜ ─────────────────────────────────────
  Widget _buildTimetableTab() {
    final dateStr = _isSameDay(_selectedDate, DateTime.now())
        ? 'Hôm nay'
        : 'Ngày ${_selectedDate.day.toString().padLeft(2, '0')}/${_selectedDate.month.toString().padLeft(2, '0')}/${_selectedDate.year}';

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(
        children: [
          // Date Selector Bar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: const Color(0xFFF1F3F4),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                IconButton(
                  onPressed: () {
                    setState(() {
                      _selectedDate = _selectedDate.subtract(const Duration(days: 1));
                    });
                  },
                  icon: const Icon(Icons.chevron_left_rounded, color: AppColors.textPrimary),
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(),
                ),
                Text(
                  dateStr,
                  style: const TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                    color: AppColors.textPrimary,
                  ),
                ),
                IconButton(
                  onPressed: () {
                    setState(() {
                      _selectedDate = _selectedDate.add(const Duration(days: 1));
                    });
                  },
                  icon: const Icon(Icons.chevron_right_rounded, color: AppColors.textPrimary),
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Text(
            _routeDirection.isEmpty ? 'Chưa có lịch chạy' : _routeDirection,
            style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppColors.teal),
          ),
          const SizedBox(height: 16),

          if (_effectiveStops.isEmpty)
            const Text('Chưa có dữ liệu điểm dừng của tuyến.')
          else
            ..._effectiveStops.map((stop) => Padding(
                  padding: const EdgeInsets.symmetric(vertical: 6),
                  child: Row(
                    children: [
                      Expanded(child: Text(stop.name)),
                      Text(stop.estimatedTime,
                          style: const TextStyle(color: AppColors.teal)),
                    ],
                  ),
                )),
        ],
      ),
    );
  }

  bool _isSameDay(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;

  // ─── TAB 3: THÔNG TIN ────────────────────────────────────────
  Widget _buildInfoTab() {
    final totalStops = _effectiveStops.length;
    final distanceKm = _selectedRouteDistance > 0
        ? '${_selectedRouteDistance.toStringAsFixed(1)} km'
        : '—';

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _infoFieldRow('Điểm đầu:', _effectiveStops.isEmpty ? '—' : _effectiveStops.first.name),
          _infoFieldRow('Giá vé:', '7000Đ'),
          _infoFieldRow('Quãng đường chạy toàn tuyến:', distanceKm),
          _infoFieldRow('Tổng số điểm dừng:', '$totalStops trạm'),
          _infoFieldRow('Hotlines:', '0919 243 170'),
          const SizedBox(height: 16),
        ],
      ),
    );
  }

  Widget _infoFieldRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: RichText(
        text: TextSpan(
          children: [
            TextSpan(
              text: '$label ',
              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppColors.textPrimary),
            ),
            TextSpan(
              text: value,
              style: const TextStyle(fontSize: 13, color: AppColors.textSecondary, fontWeight: FontWeight.w500),
            ),
          ],
        ),
      ),
    );
  }
}

class _BusStop {
  final LatLng pos;
  final String name;
  final String type;
  final List<int> routes;
  final String estimatedTime;
  const _BusStop(this.pos, this.name, this.type, this.routes, [this.estimatedTime = '06:00']);
}
