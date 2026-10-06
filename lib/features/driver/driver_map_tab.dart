import 'dart:async';
import 'dart:math' show Point;

import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:latlong2/latlong.dart';
import 'package:maplibre_gl/maplibre_gl.dart' as ml;
import '../../services/api_service.dart';
import '../../services/gps_service.dart';
import '../../services/routing_service.dart';
import '../../theme/app_theme.dart';
import '../../config/api_config.dart';

class DriverMapTab extends StatefulWidget {
  const DriverMapTab({
    super.key,
    required this.api,
    this.initialRoute,
    this.user,
  });
  final ApiService api;
  final Map<String, dynamic>? initialRoute;
  final Map<String, dynamic>? user;

  @override
  State<DriverMapTab> createState() => _DriverMapTabState();
}

class _DriverMapTabState extends State<DriverMapTab>
    with SingleTickerProviderStateMixin {
  ml.MapLibreMapController? _goongMapController;
  final DraggableScrollableController _panelController =
      DraggableScrollableController();
  ml.Circle? _gpsCircle;
  StreamSubscription<Position>? _gpsSubscription;
  Position? _currentPosition;
  bool _mapStyleLoaded = false;
  bool _renderingMapAnnotations = false;
  bool _rerenderMapAnnotationsRequested = false;
  bool _panelCollapsed = false;
  late TabController _tabs;
  Map<String, dynamic>? _route;
  List<_Stop> _stops = [];
  List<LatLng> _roadPolylinePoints = [];
  bool _loading = true, _busy = false;
  DateTime _selectedDate = DateTime.now();
  _Stop? _selectedStopForTooltip;
  String? _error;
  Timer? _pendingRouteTimer;

  String? get _id => _route?['id']?.toString();
  String get _routeCode {
    final routeId = _id;
    if (routeId == null || routeId.isEmpty) return 'CT-01';
    if (routeId.length > 5) {
      return 'CT-${routeId.substring(0, 5).toUpperCase()}';
    }
    return 'CT-$routeId';
  }

  String get _status => _route?['status']?.toString() ?? 'pending';

  LatLng get _center =>
      _stops.isEmpty ? const LatLng(10.0302, 105.7721) : _stops.first.point;

  List<_Stop> get _effectiveStops => _stops;

  ml.LatLng _mapPoint(LatLng point) => ml.LatLng(point.latitude, point.longitude);

  void _moveMapTo(LatLng center, double zoom) {
    _goongMapController?.animateCamera(
      ml.CameraUpdate.newLatLngZoom(
        ml.LatLng(center.latitude, center.longitude),
        zoom,
      ),
    );
  }

  List<LatLng> get _effectivePolylinePoints {
    if (_roadPolylinePoints.isEmpty) {
      return _effectiveStops.map((s) => s.point).toList();
    }
    return _roadPolylinePoints;
  }

  void _onPanelExtentChanged() {
    if (!_panelController.isAttached) return;
    final collapsed = _panelController.size <= 0.09;
    if (collapsed != _panelCollapsed && mounted) {
      setState(() => _panelCollapsed = collapsed);
    }
  }

  Future<void> _togglePanel() async {
    if (!_panelController.isAttached) return;
    await _panelController.animateTo(
      _panelCollapsed ? .45 : .06,
      duration: const Duration(milliseconds: 260),
      curve: Curves.easeOutCubic,
    );
  }

  void _onMapCircleTapped(ml.Circle circle) {
    final index = circle.data?['stopIndex'];
    if (index is! int || index < 0 || index >= _effectiveStops.length) return;
    setState(() => _selectedStopForTooltip = _effectiveStops[index]);
    _renderMapAnnotations();
  }

  Future<void> _updateGpsAnnotation(Position position) async {
    final controller = _goongMapController;
    if (!_mapStyleLoaded || controller == null) return;
    if (_renderingMapAnnotations) {
      _rerenderMapAnnotationsRequested = true;
      return;
    }
    final point = LatLng(position.latitude, position.longitude);
    try {
      final current = _gpsCircle;
      if (current == null) {
        _gpsCircle = await controller.addCircle(
          ml.CircleOptions(
            geometry: _mapPoint(point),
            circleRadius: 9,
            circleColor: '#087BCE',
            circleStrokeColor: '#FFFFFF',
            circleStrokeWidth: 3,
          ),
          const {'kind': 'gps'},
        );
      } else {
        await controller.updateCircle(
          current,
          ml.CircleOptions(geometry: _mapPoint(point)),
        );
      }
    } catch (_) {
      // A route refresh or style reload can replace annotations concurrently.
    }
  }

  Future<void> _renderMapAnnotations() async {
    final controller = _goongMapController;
    if (!_mapStyleLoaded || controller == null) return;
    if (_renderingMapAnnotations) {
      _rerenderMapAnnotationsRequested = true;
      return;
    }
    _renderingMapAnnotations = true;
    try {
      await controller.clearLines();
      await controller.clearCircles();
      _gpsCircle = null;

      final points = _effectivePolylinePoints;
      if (points.length > 1) {
        await controller.addLine(
          ml.LineOptions(
            geometry: points.map(_mapPoint).toList(),
            lineColor: '#FFFFFF',
            lineWidth: 7,
            lineJoin: 'round',
          ),
        );
        await controller.addLine(
          ml.LineOptions(
            geometry: points.map(_mapPoint).toList(),
            lineColor: '#EA4335',
            lineWidth: 4.5,
            lineJoin: 'round',
          ),
        );
      }

      for (var i = 0; i < _effectiveStops.length; i++) {
        final stop = _effectiveStops[i];
        final isSelected = _selectedStopForTooltip?.name == stop.name;
        final isActiveDepot = _status == 'in_progress' && i == 0;
        await controller.addCircle(
          ml.CircleOptions(
            geometry: _mapPoint(stop.point),
            circleRadius: 12,
            circleColor: isSelected || isActiveDepot ? '#FFA23B' : '#FF6B4A',
            circleStrokeColor: '#FFFFFF',
            circleStrokeWidth: 2,
          ),
          {'stopIndex': i},
        );
      }

      final position = _currentPosition;
      if (position != null) {
        _gpsCircle = await controller.addCircle(
          ml.CircleOptions(
            geometry: ml.LatLng(position.latitude, position.longitude),
            circleRadius: 9,
            circleColor: '#087BCE',
            circleStrokeColor: '#FFFFFF',
            circleStrokeWidth: 3,
          ),
          const {'kind': 'gps'},
        );
      }
    } catch (error) {
      debugPrint('Unable to render route annotations: $error');
    } finally {
      _renderingMapAnnotations = false;
      if (_rerenderMapAnnotationsRequested && mounted) {
        _rerenderMapAnnotationsRequested = false;
        _renderMapAnnotations();
      }
    }
  }

  String get _displayTitle {
    if (_stops.length < 2) return 'Tuyến được phân công';
    return '${_stops.first.name} - ${_stops.last.name}';
  }

  String get _routeDirection {
    final tripType = _route?['trip_type']?.toString();
    final sessionId = _route?['session_id']?.toString();
    return [
      if (tripType != null) tripType == 'pickup' ? 'Chiều đi' : 'Chiều về',
      if (sessionId != null) sessionId,
    ].join(' • ');
  }

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 3, vsync: this);
    _tabs.addListener(() {
      if (mounted) setState(() {});
    });
    _panelController.addListener(_onPanelExtentChanged);
    _currentPosition = GpsService().lastPosition;
    _gpsSubscription = GpsService().positionStream.listen((position) {
      _currentPosition = position;
      _updateGpsAnnotation(position);
    });
    _route = widget.initialRoute;
    _load();
    _pendingRouteTimer = Timer.periodic(const Duration(seconds: 20), (_) {
      if (_id != null && _id!.isNotEmpty) {
        _pendingRouteTimer?.cancel();
      } else {
        _load();
      }
    });
  }

  @override
  void didUpdateWidget(covariant DriverMapTab oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.initialRoute != oldWidget.initialRoute && widget.initialRoute != null) {
      _route = widget.initialRoute;
      _load();
    }
  }

  @override
  void dispose() {
    _pendingRouteTimer?.cancel();
    _gpsSubscription?.cancel();
    _panelController.removeListener(_onPanelExtentChanged);
    _goongMapController?.onCircleTapped.remove(_onMapCircleTapped);
    _tabs.dispose();
    _panelController.dispose();
    super.dispose();
  }

  List<_Stop> _parseStops(Map<String, dynamic> route) {
    final rawStopsList = (route['stops'] as List<dynamic>? ??
        route['route_stops'] as List<dynamic>? ??
        []);
    final stops = rawStopsList.map((raw) {
      final item = Map<String, dynamic>.from(raw as Map);
      final loc = Map<String, dynamic>.from(item['location'] as Map? ??
          item['locations'] as Map? ??
          item);
      final name = loc['name']?.toString() ??
          item['name']?.toString() ??
          'Trạm ${item['stop_order'] ?? ''}';
      final lat = (loc['latitude'] as num?)?.toDouble() ??
          (item['latitude'] as num?)?.toDouble();
      final lng = (loc['longitude'] as num?)?.toDouble() ??
          (item['longitude'] as num?)?.toDouble();
      if (lat == null || lng == null) return null;
      final date = DateTime.tryParse(item['arrival_time']?.toString() ?? '')
          ?.toLocal();
      final departure = DateTime.tryParse(item['departure_time']?.toString() ?? '')?.toLocal();
      final windowStart = DateTime.tryParse(item['time_window_start']?.toString() ?? '')?.toLocal();
      final windowEnd = DateTime.tryParse(item['time_window_end']?.toString() ?? '')?.toLocal();
      return _Stop(
        name,
        LatLng(lat, lng),
        date == null
            ? 'Đang cập nhật'
            : '${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}',
        (item['stop_order'] as num?)?.toInt() ?? 0,
        departure == null ? null : '${departure.hour.toString().padLeft(2, '0')}:${departure.minute.toString().padLeft(2, '0')}',
        windowStart == null || windowEnd == null ? null : '${windowStart.hour.toString().padLeft(2, '0')}:${windowStart.minute.toString().padLeft(2, '0')}–${windowEnd.hour.toString().padLeft(2, '0')}:${windowEnd.minute.toString().padLeft(2, '0')}',
      );
    }).whereType<_Stop>().toList()
      ..sort((a, b) => a.order.compareTo(b.order));
    return stops;
  }

  Future<void> _fetchRoadPolyline(List<_Stop> stops) async {
    if (stops.length < 2) return;
    try {
      final waypoints = stops.map((s) => s.point).toList();
      final roadPoints = await RoutingService().getDrivingRoute(waypoints);
      if (mounted && roadPoints.isNotEmpty) {
        setState(() {
          _roadPolylinePoints = roadPoints;
        });
        _renderMapAnnotations();
      }
    } catch (_) {}
  }

  Future<void> _load() async {
    if (mounted) setState(() { _loading = true; _error = null; });

    if (_route != null) {
      final initialStops = _parseStops(_route!);
      if (initialStops.isNotEmpty && mounted) {
        setState(() {
          _stops = initialStops;
          _loading = false;
        });
        _moveMapTo(_center, 13.5);
        _fetchRoadPolyline(initialStops);
        _renderMapAnnotations();
      }
    }

    String? routeId = _id;
    if (routeId == null || routeId.isEmpty) {
      try {
        final driverId = widget.user?['id']?.toString() ?? '';
        final routes = await widget.api.fetchDriverRoutes(driverId);
        if (routes.isNotEmpty) {
          _route = Map<String, dynamic>.from(routes.first as Map);
          routeId = _id;
          final stops = _parseStops(_route!);
          if (stops.isNotEmpty && mounted) {
            setState(() {
              _stops = stops;
              _loading = false;
            });
            _moveMapTo(_center, 13.5);
            _fetchRoadPolyline(stops);
            _renderMapAnnotations();
          }
        }
      } catch (_) {}
    }

    if (routeId == null || routeId.isEmpty) {
      if (mounted) {
        setState(() {
          _loading = false;
          _error = 'Chưa có tuyến được phân công.';
        });
      }
      return;
    }

    try {
      final route = await widget.api.fetchRouteDetails(routeId);
      final stops = _parseStops(route);
      if (mounted) {
        setState(() {
          _route = route;
          _stops = stops.isNotEmpty ? stops : _stops;
          _error = null;
          _loading = false;
        });
        if (_stops.isNotEmpty) {
          _moveMapTo(_center, 13.5);
          _fetchRoadPolyline(_stops);
          _renderMapAnnotations();
        }
      }
    } catch (e) {
      if (mounted && _stops.isEmpty) {
        setState(() => _error = 'Không thể tải tuyến: $e');
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _confirmToggle() async {
    final routeId = _id;
    if (routeId == null || routeId.isEmpty || _status == 'completed' || _busy) return;
    final isStarting = _status != 'in_progress';
    final actionText = isStarting ? 'bắt đầu' : 'kết thúc';
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Row(
          children: [
            Icon(
              isStarting ? Icons.play_circle_fill_rounded : Icons.stop_circle_rounded,
              color: isStarting ? AppColors.teal : const Color(0xFFD94E41),
            ),
            const SizedBox(width: 8),
            Text('Xác nhận $actionText chuyến?'),
          ],
        ),
        content: Text(
          isStarting
              ? 'Bạn có chắc chắn muốn BẮT ĐẦU chuyến xe $_routeCode không?'
              : 'Bạn có chắc chắn muốn KẾT THÚC chuyến xe $_routeCode không?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Hủy', style: TextStyle(color: Colors.grey)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: isStarting ? AppColors.teal : const Color(0xFFD94E41),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
            ),
            onPressed: () => Navigator.of(ctx).pop(true),
            child: Text(
              isStarting ? 'Bắt đầu ngay' : 'Xác nhận kết thúc',
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
            ),
          ),
        ],
      ),
    );

    if (confirm == true) {
      _toggle();
    }
  }

  Future<void> _toggle() async {
    final routeId = _id;
    if (routeId == null || routeId.isEmpty || _status == 'completed') return;
    setState(() => _busy = true);
    final wasInProgress = _status == 'in_progress';
    try {
      final updatedRoute = wasInProgress
          ? await widget.api.endRoute(routeId)
          : await widget.api.startRoute(routeId);
      if (wasInProgress) {
        GpsService().stopTracking();
      } else {
        GpsService().startTracking(routeId: routeId, api: widget.api);
      }
      if (mounted) {
        setState(() {
          _route = updatedRoute;
        });
        _renderMapAnnotations();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              wasInProgress
                  ? 'Đã kết thúc chuyến xe $_routeCode.'
                  : 'Đã bắt đầu chuyến xe $_routeCode. Chúc bạn lái xe an toàn!',
            ),
            backgroundColor: wasInProgress ? const Color(0xFFD94E41) : AppColors.teal,
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Chuyển trạng thái thất bại: $e'),
            backgroundColor: Colors.red[700],
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: AppColors.teal))
          : _error != null
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.route_outlined, size: 52, color: AppColors.teal),
                      const SizedBox(height: 12),
                      Text(_error!),
                      TextButton(onPressed: _load, child: const Text('Tải lại')),
                    ],
                  ),
                )
              : Stack(
                  children: [
                    // Basemap and route annotations share the MapLibre camera.
                    ml.MapLibreMap(
                      styleString: ApiConfig.goongMapStyleUrl,
                      initialCameraPosition: ml.CameraPosition(
                        target: ml.LatLng(_center.latitude, _center.longitude),
                        zoom: 13.5,
                      ),
                      attributionButtonPosition: ml.AttributionButtonPosition.topLeft,
                      attributionButtonMargins: const Point(8, 58),
                      onMapCreated: (controller) {
                        _goongMapController = controller;
                        controller.onCircleTapped.add(_onMapCircleTapped);
                      },
                      onStyleLoadedCallback: () {
                        _mapStyleLoaded = true;
                        _renderMapAnnotations();
                      },
                    ),

                    // Layer 2: Floating Controls
                    SafeArea(
                      child: Padding(
                        padding: const EdgeInsets.all(12),
                        child: Row(
                          children: [
                            _circle(Icons.arrow_back, () => Navigator.maybePop(context)),
                            const Spacer(),
                            _circle(Icons.my_location_rounded, () => _moveMapTo(_center, 14)),
                          ],
                        ),
                      ),
                    ),

                    // Layer 3: Tooltip Banner for selected stop
                    if (_selectedStopForTooltip != null) _buildStopTooltipBanner(),

                    // Layer 4: Draggable Bottom Panel matching Student UI
                    _panel(),
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
                  Text('Giờ đón dự kiến: ${stop.time}', style: const TextStyle(fontSize: 14, color: AppColors.teal)),
                  if (stop.timeWindow != null) Text('Khung đón: ${stop.timeWindow}', style: const TextStyle(fontSize: 13, color: AppColors.textSecondary)),
                  if (stop.departureTime != null) Text('Đón xong / rời trạm: ${stop.departureTime}', style: const TextStyle(fontSize: 13, color: AppColors.textSecondary)),
                  const SizedBox(height: 12),
                  const Text('Tọa độ:', style: TextStyle(fontSize: 12, color: AppColors.textMuted)),
                  Text('${stop.point.latitude.toStringAsFixed(5)}, ${stop.point.longitude.toStringAsFixed(5)}',
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
                    Text(
                      stop.name,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: AppColors.textPrimary),
                    ),
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

  Widget _circle(IconData icon, VoidCallback fn) => Material(
        color: Colors.white,
        shape: const CircleBorder(),
        elevation: 2,
        child: IconButton(onPressed: fn, icon: Icon(icon)),
      );

  Widget _panel() => DraggableScrollableSheet(
        controller: _panelController,
        initialChildSize: .45,
        minChildSize: .06,
        maxChildSize: .88,
        snap: true,
        snapSizes: const [.45],
        shouldCloseOnMinExtent: false,
        builder: (_, scroll) => Container(
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(22)),
            boxShadow: [BoxShadow(color: Colors.black26, blurRadius: 12)],
          ),
          child: _panelCollapsed
              ? ListView(
                  controller: scroll,
                  padding: const EdgeInsets.only(bottom: 4),
                  children: [
                    Center(
                      child: InkWell(
                        onTap: _togglePanel,
                        borderRadius: BorderRadius.circular(20),
                        child: Padding(
                          padding: const EdgeInsets.fromLTRB(18, 8, 18, 6),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Container(
                                height: 4,
                                width: 36,
                                decoration: BoxDecoration(
                                  color: const Color(0xFFFFD4C9),
                                  borderRadius: BorderRadius.circular(3),
                                ),
                              ),
                              const SizedBox(width: 10),
                              Text(
                                'Route $_routeCode',
                                style: const TextStyle(
                                  color: Color(0xFF07835A),
                                  fontWeight: FontWeight.w700,
                                  fontSize: 12,
                                ),
                              ),
                              const SizedBox(width: 6),
                              const Icon(Icons.keyboard_arrow_up_rounded, size: 20),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ],
                )
              : ListView(
                  controller: scroll,
                  padding: const EdgeInsets.only(bottom: 24),
                  children: [
              // Drag Handle
              Center(
                child: InkWell(
                  onTap: _togglePanel,
                  borderRadius: BorderRadius.circular(20),
                  child: Padding(
                    padding: const EdgeInsets.all(10),
                    child: Container(
                      height: 4,
                      width: 40,
                      decoration: BoxDecoration(
                        color: const Color(0xFFFFD4C9),
                        borderRadius: BorderRadius.circular(3),
                      ),
                    ),
                  ),
                ),
              ),

              // Header Route Card (Mã + Tiêu đề + Status Chip + Nút Đổi chiều)
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF3F4F6),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: const Color(0xFFE7F5EF),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          _routeCode,
                          style: const TextStyle(
                            color: Color(0xFF07835A),
                            fontWeight: FontWeight.w800,
                            fontSize: 15,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              _displayTitle,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 6),
                      _chip(),
                      const SizedBox(width: 6),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
                        decoration: BoxDecoration(
                          color: const Color(0xFFE6F4EA),
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(color: const Color(0xFF34A853).withValues(alpha: 0.3)),
                        ),
                        child: Text(
                          _routeDirection.isEmpty ? '—' : _routeDirection,
                          style: const TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color: Color(0xFF137333),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),

              // TabBar Navigation (Danh sách trạm | Biểu đồ giờ | Thông tin)
              TabBar(
                controller: _tabs,
                labelColor: const Color(0xFFEA4335),
                unselectedLabelColor: const Color(0xFF343A40),
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

              // Tab Views
              if (_tabs.index == 0) _stopsView(),
              if (_tabs.index == 1) _hoursView(),
              if (_tabs.index == 2) _infoView(),
                  ],
                ),
        ),
      );

  Widget _chip() {
    Color bg;
    Color fg;
    String label;
    if (_status == 'in_progress') {
      bg = const Color(0xFFE7F5EF);
      fg = const Color(0xFF07835A);
      label = 'Đang chạy';
    } else if (_status == 'completed') {
      bg = const Color(0xFFF1F3F5);
      fg = const Color(0xFF495057);
      label = 'Hoàn tất';
    } else {
      bg = const Color(0xFFFFF3BF);
      fg = const Color(0xFFF59F00);
      label = 'Sắp chạy';
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 5,
            height: 5,
            decoration: BoxDecoration(color: fg, shape: BoxShape.circle),
          ),
          const SizedBox(width: 4),
          Text(
            label,
            style: TextStyle(fontSize: 10, color: fg, fontWeight: FontWeight.w700),
          ),
        ],
      ),
    );
  }

  // ─── TAB 1: DANH SÁCH TRẠM ───────────────────────────────────
  Widget _stopsView() {
    final stops = _effectiveStops;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Tuyến $_routeCode',
            style: const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
              color: Color(0xFFEA4335),
            ),
          ),
          const SizedBox(height: 12),
          for (var i = 0; i < stops.length; i++) _stopLine(stops[i], i == stops.length - 1),
          const SizedBox(height: 16),
          _button(),
        ],
      ),
    );
  }

  Widget _stopLine(_Stop s, bool last) {
    final isSelected = _selectedStopForTooltip?.name == s.name;
    return InkWell(
      onTap: () {
        setState(() {
          _selectedStopForTooltip = s;
        });
        _renderMapAnnotations();
        _moveMapTo(s.point, 15.5);
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
                    color: isSelected ? const Color(0xFFEA4335) : const Color(0xFF5F6368),
                    shape: BoxShape.circle,
                  ),
                ),
                if (!last)
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
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      s.name,
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
                        color: isSelected ? const Color(0xFFEA4335) : AppColors.textPrimary,
                      ),
                    ),
                  ),
                  Text(
                    s.time,
                    style: const TextStyle(fontSize: 12, color: Color(0xFF75828B)),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ─── TAB 2: BIỂU ĐỒ GIỜ ─────────────────────────────────────
  Widget _hoursView() {
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
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Text(stop.time, style: const TextStyle(color: AppColors.teal)),
                          if (stop.timeWindow != null) Text('TW ${stop.timeWindow}', style: const TextStyle(fontSize: 10, color: AppColors.textSecondary)),
                        ],
                      ),
                    ],
                  ),
                )),

          const SizedBox(height: 24),
          _button(),
        ],
      ),
    );
  }

  bool _isSameDay(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;

  // ─── TAB 3: THÔNG TIN ────────────────────────────────────────
  Widget _infoView() {
    final totalStops = _effectiveStops.length;
    final distanceKm = (_route?['total_distance'] as num?)?.toStringAsFixed(1) ?? '—';
    final drivingMinutes = (_route?['driving_duration_minutes'] as num?)?.toStringAsFixed(1) ?? '—';

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _line('Depot', 'Đại Học Cần Thơ'),
          _line('Giá vé', '7000Đ'),
          _line('Quãng đường chạy toàn tuyến', '$distanceKm km'),
          _line('Thời gian xe di chuyển (không gồm chờ)', '$drivingMinutes phút'),
          _line('Tổng số trạm của tuyến đang chạy', '$totalStops trạm'),
          _line('Hotlines', '0919 243 170'),
          const SizedBox(height: 16),
          _button(),
        ],
      ),
    );
  }

  Widget _line(String key, String value) => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: RichText(
          text: TextSpan(
            style: const TextStyle(fontSize: 13, color: Color(0xFF273130)),
            children: [
              TextSpan(text: '$key: ', style: const TextStyle(fontWeight: FontWeight.bold)),
              TextSpan(text: value, style: const TextStyle(color: Color(0xFF75828B))),
            ],
          ),
        ),
      );

  Widget _button() {
    final isCompleted = _status == 'completed';
    final isInProgress = _status == 'in_progress';

    if (isCompleted) {
      return SizedBox(
        width: double.infinity,
        child: OutlinedButton.icon(
          onPressed: null,
          icon: const Icon(Icons.check_circle_outline_rounded, color: Colors.grey),
          label: const Text('Chuyến xe đã hoàn tất'),
          style: OutlinedButton.styleFrom(
            padding: const EdgeInsets.symmetric(vertical: 12),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          ),
        ),
      );
    }

    return SizedBox(
      width: double.infinity,
      child: FilledButton.icon(
        onPressed: _busy ? null : _confirmToggle,
        style: FilledButton.styleFrom(
          backgroundColor: isInProgress ? const Color(0xFFD94E41) : AppColors.teal,
          padding: const EdgeInsets.symmetric(vertical: 12),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        ),
        icon: _busy
            ? const SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
              )
            : Icon(isInProgress ? Icons.stop_rounded : Icons.play_arrow_rounded),
        label: Text(
          _busy
              ? 'Đang xử lý...'
              : isInProgress
                  ? 'Kết thúc chuyến'
                  : 'Bắt đầu chuyến',
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
      ),
    );
  }
}

class _Stop {
  const _Stop(this.name, this.point, this.time, this.order, this.departureTime, this.timeWindow);
  final String name, time;
  final String? departureTime, timeWindow;
  final LatLng point;
  final int order;
}
