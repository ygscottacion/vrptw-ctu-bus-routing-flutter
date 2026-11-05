import 'dart:async';
import 'dart:math' show Point;
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
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
  ml.MapLibreMapController? _goongMapController;
  ml.Symbol? _busSymbol;
  final DraggableScrollableController _panelController =
      DraggableScrollableController();
  bool _mapStyleLoaded = false;
  bool _renderingMapAnnotations = false;
  bool _rerenderMapAnnotationsRequested = false;
  bool _panelCollapsed = false;
  LatLng? _pendingMapCenter;
  double _pendingMapZoom = 13.5;
  late TabController _tabController;

  String _selectedRouteId = '—';
  String _routeName = 'Chưa có tuyến được gán';
  String _routeDirection = '';
  String? _selectedRouteApiId;
  double _selectedRouteDistance = 0;
  DateTime _selectedDate = DateTime.now();
  List<dynamic> _myTickets = [];
  List<String> _dayRouteIds = [];
  bool _isLoadingTrip = true;
  bool _isViewingHistory = false;
  String? _tripLoadError;
  int _loadRequestId = 0;
  Timer? _pollingTimer;
  Timer? _routeRefreshTimer;

  _BusStop? _selectedStopForTooltip;
  List<_BusStop> _dynamicStops = [];
  List<dynamic> _activeRoutes = [];
  final Map<String, LatLng> _realBusPositions = {};
  final Map<String, double> _realBusHeadings = {};
  List<LatLng> _roadPolyline = [];
  DateTime? _gpsLastUpdated;
  bool _gpsIsStale = true;
  bool _pollingGpsPositions = false;
  bool _busIconRegistered = false;
  bool _updatingBusSymbol = false;
  LatLng? _busRenderedPosition;
  double _busRenderedHeading = 0;
  Timer? _busAnimationTimer;
  int _busAnimationGeneration = 0;

  static const _busIconImageName = 'student-bus-location-marker';

  ml.LatLng _mapPoint(LatLng point) =>
      ml.LatLng(point.latitude, point.longitude);

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _tabController.addListener(() {
      if (mounted) setState(() {});
    });
    _panelController.addListener(_onPanelExtentChanged);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        _loadActiveRoutes().then((_) => _pollGpsPositions());
      }
    });
    _startGpsPolling();
  }

  @override
  void dispose() {
    _tabController.dispose();
    _panelController.removeListener(_onPanelExtentChanged);
    _panelController.dispose();
    _goongMapController?.onCircleTapped.remove(_onMapCircleTapped);
    _pollingTimer?.cancel();
    _routeRefreshTimer?.cancel();
    _busAnimationTimer?.cancel();
    super.dispose();
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

  void _moveMapTo(LatLng center, double zoom) {
    final controller = _goongMapController;
    if (controller == null) {
      _pendingMapCenter = center;
      _pendingMapZoom = zoom;
      return;
    }
    controller
        .animateCamera(ml.CameraUpdate.newLatLngZoom(_mapPoint(center), zoom));
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
      await controller.clearSymbols();
      _busAnimationTimer?.cancel();
      _busAnimationGeneration++;
      _busSymbol = null;
      _busRenderedPosition = null;

      if (_roadPolyline.length > 1) {
        final geometry = _roadPolyline.map(_mapPoint).toList();
        await controller.addLine(ml.LineOptions(
          geometry: geometry,
          lineColor: '#FFFFFF',
          lineWidth: 7,
          lineJoin: 'round',
        ));
        await controller.addLine(ml.LineOptions(
          geometry: geometry,
          lineColor: '#EA4335',
          lineWidth: 4.5,
          lineJoin: 'round',
        ));
      }

      for (var i = 0; i < _effectiveStops.length; i++) {
        final stop = _effectiveStops[i];
        final selected = _selectedStopForTooltip?.name == stop.name;
        await controller.addCircle(
          ml.CircleOptions(
            geometry: _mapPoint(stop.pos),
            circleRadius: selected ? 14 : 11,
            circleColor: selected ? '#EA4335' : '#16B6AE',
            circleStrokeColor: '#FFFFFF',
            circleStrokeWidth: 2.5,
          ),
          {'stopIndex': i},
        );
      }

      if (_busIconRegistered && _realBusPositions.isNotEmpty) {
        final routeId = _realBusPositions.keys.last;
        final position = _realBusPositions[routeId]!;
        final heading = _realBusHeadings[routeId] ?? 0;
        _busSymbol = await controller.addSymbol(
          ml.SymbolOptions(
            geometry: _mapPoint(position),
            iconImage: _busIconImageName,
            iconSize: 0.55,
            iconAnchor: 'center',
            iconRotate: heading,
          ),
        );
        _busRenderedPosition = position;
        _busRenderedHeading = heading;
      }
    } catch (error) {
      debugPrint('Unable to render student route annotations: $error');
    } finally {
      _renderingMapAnnotations = false;
      if (_rerenderMapAnnotationsRequested && mounted) {
        _rerenderMapAnnotationsRequested = false;
        _renderMapAnnotations();
      }
    }
  }

  Future<void> _updateBusAnnotation({LatLng? position, double? heading}) async {
    final controller = _goongMapController;
    if (!_mapStyleLoaded ||
        !_busIconRegistered ||
        controller == null ||
        _realBusPositions.isEmpty ||
        _updatingBusSymbol) {
      return;
    }
    if (_renderingMapAnnotations) return;
    final routeId = _realBusPositions.keys.last;
    final point = position ?? _realBusPositions[routeId]!;
    final rotation = heading ?? _realBusHeadings[routeId] ?? 0;
    _updatingBusSymbol = true;
    try {
      final current = _busSymbol;
      if (current == null) {
        _busSymbol = await controller.addSymbol(
          ml.SymbolOptions(
            geometry: _mapPoint(point),
            iconImage: _busIconImageName,
            iconSize: 0.55,
            iconAnchor: 'center',
            iconRotate: rotation,
          ),
        );
      } else {
        await controller.updateSymbol(
          current,
          ml.SymbolOptions(
            geometry: _mapPoint(point),
            iconRotate: rotation,
          ),
        );
      }
      _busRenderedPosition = point;
      _busRenderedHeading = rotation;
    } catch (_) {
      // Route refreshes can replace map annotations while GPS updates arrive.
    } finally {
      _updatingBusSymbol = false;
    }
  }

  void _animateBusMarker(
    LatLng from,
    LatLng to,
    double fromHeading,
    double toHeading,
  ) {
    _busAnimationTimer?.cancel();
    final generation = ++_busAnimationGeneration;
    final startedAt = DateTime.now();
    const duration = Duration(seconds: 8);
    var lastProgress = 0.0;
    _busAnimationTimer =
        Timer.periodic(const Duration(milliseconds: 250), (timer) {
      if (!mounted || generation != _busAnimationGeneration) {
        timer.cancel();
        return;
      }
      final progress = (DateTime.now().difference(startedAt).inMilliseconds /
              duration.inMilliseconds)
          .clamp(0.0, 1.0)
          .toDouble();
      if (progress == lastProgress) return;
      lastProgress = progress;
      final headingDelta = (toHeading - fromHeading + 540) % 360 - 180;
      final position = LatLng(
        from.latitude + (to.latitude - from.latitude) * progress,
        from.longitude + (to.longitude - from.longitude) * progress,
      );
      final heading = (fromHeading + headingDelta * progress + 360) % 360;
      _updateBusAnnotation(position: position, heading: heading);
      if (progress >= 1) timer.cancel();
    });
  }

  Future<void> _registerBusIconAndRender() async {
    final controller = _goongMapController;
    if (controller == null) return;
    _busIconRegistered = false;
    try {
      final recorder = ui.PictureRecorder();
      final canvas = ui.Canvas(recorder);
      final busBody = ui.Paint()..color = const Color(0xFF13AAA1);
      final busOutline = ui.Paint()
        ..color = const Color(0xFF08756F)
        ..style = ui.PaintingStyle.stroke
        ..strokeWidth = 2.5;
      final window = ui.Paint()..color = const Color(0xFFE7FAFF);
      final wheel = ui.Paint()..color = const Color(0xFF263238);
      final hub = ui.Paint()..color = const Color(0xFFDCE4E8);
      final light = ui.Paint()..color = const Color(0xFFFFC857);

      canvas.drawCircle(
          const ui.Offset(32, 32), 30, ui.Paint()..color = Colors.white);
      const bodyRect = ui.Rect.fromLTRB(17, 7, 47, 55);
      final body =
          ui.RRect.fromRectAndRadius(bodyRect, const ui.Radius.circular(8));
      canvas.drawRRect(body, busBody);
      canvas.drawRRect(body, busOutline);
      canvas.drawRRect(
        ui.RRect.fromRectAndRadius(
          const ui.Rect.fromLTRB(21, 12, 43, 22),
          const ui.Radius.circular(3),
        ),
        window,
      );
      canvas.drawRRect(
        ui.RRect.fromRectAndRadius(
          const ui.Rect.fromLTRB(21, 26, 29, 37),
          const ui.Radius.circular(3),
        ),
        window,
      );
      canvas.drawRRect(
        ui.RRect.fromRectAndRadius(
          const ui.Rect.fromLTRB(33, 26, 41, 37),
          const ui.Radius.circular(3),
        ),
        window,
      );
      canvas.drawLine(
          const ui.Offset(20, 41), const ui.Offset(44, 41), busOutline);
      canvas.drawCircle(const ui.Offset(16, 19), 4, wheel);
      canvas.drawCircle(const ui.Offset(48, 19), 4, wheel);
      canvas.drawCircle(const ui.Offset(16, 44), 4, wheel);
      canvas.drawCircle(const ui.Offset(48, 44), 4, wheel);
      canvas.drawCircle(const ui.Offset(16, 19), 1.5, hub);
      canvas.drawCircle(const ui.Offset(48, 19), 1.5, hub);
      canvas.drawCircle(const ui.Offset(16, 44), 1.5, hub);
      canvas.drawCircle(const ui.Offset(48, 44), 1.5, hub);
      canvas.drawCircle(const ui.Offset(24, 52), 1.8, light);
      canvas.drawCircle(const ui.Offset(40, 52), 1.8, light);

      final image = await recorder.endRecording().toImage(64, 64);
      final png = await image.toByteData(format: ui.ImageByteFormat.png);
      image.dispose();
      if (png == null) return;
      await controller.addImage(
        _busIconImageName,
        png.buffer.asUint8List(png.offsetInBytes, png.lengthInBytes),
      );
      _busIconRegistered = true;
    } catch (error) {
      debugPrint('Unable to create student bus marker: $error');
    }
    if (mounted) _renderMapAnnotations();
  }

  Future<void> _fetchRoutePolyline(
      List<_BusStop> stops, String? routeId) async {
    if (stops.length < 2 || routeId == null || routeId.isEmpty) return;
    final points = await RoutingService().getDrivingRoute(
      stops.map((stop) => stop.pos).toList(),
    );
    if (!mounted || routeId != _selectedRouteApiId) return;
    setState(() => _roadPolyline = points);
    _renderMapAnnotations();
  }

  Future<void> _loadActiveRoutes({String? preferredRouteId}) async {
    final requestId = ++_loadRequestId;
    final requestedDate = _dateKey(_selectedDate);
    try {
      final tickets = await widget.api.fetchMyTickets();
      final dayTickets = tickets
          .whereType<Map>()
          .where((ticket) =>
              const {'assigned', 'used'}.contains(ticket['status']?.toString()))
          .where((ticket) => ticket['route_id'] != null)
          .where(
              (ticket) => ticket['service_date']?.toString() == requestedDate)
          .toList();
      final routeIds = dayTickets
          .map((ticket) => ticket['route_id'].toString())
          .toSet()
          .toList();
      routeIds.sort();
      final rememberedRouteId = preferredRouteId ?? _selectedRouteApiId;
      final selectedRouteId =
          rememberedRouteId != null && routeIds.contains(rememberedRouteId)
              ? rememberedRouteId
              : (routeIds.isEmpty ? null : routeIds.first);

      Map<String, dynamic>? selectedRoute;
      if (selectedRouteId != null) {
        selectedRoute = await widget.api.fetchRouteDetails(selectedRouteId);
      }
      if (!mounted ||
          requestId != _loadRequestId ||
          requestedDate != _dateKey(_selectedDate)) {
        return;
      }

      final rawStops = [
        ...(selectedRoute?['stops'] as List<dynamic>? ?? const [])
      ]..sort((a, b) {
          final aOrder = a is Map ? (a['stop_order'] as num?)?.toInt() ?? 0 : 0;
          final bOrder = b is Map ? (b['stop_order'] as num?)?.toInt() ?? 0 : 0;
          return aOrder.compareTo(bOrder);
        });
      final stops = <_BusStop>[];
      for (var i = 0; i < rawStops.length; i++) {
        final stop = rawStops[i];
        if (stop is! Map) continue;
        final location = stop['location'] as Map? ?? const {};
        final latitude = (location['latitude'] as num?)?.toDouble();
        final longitude = (location['longitude'] as num?)?.toDouble();
        if (latitude == null ||
            longitude == null ||
            !latitude.isFinite ||
            !longitude.isFinite ||
            latitude < -90 ||
            latitude > 90 ||
            longitude < -180 ||
            longitude > 180) {
          continue;
        }
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
      final previouslyActive = _activeRoutes.isNotEmpty;
      setState(() {
        _myTickets = tickets;
        _dayRouteIds = routeIds;
        _isLoadingTrip = false;
        _tripLoadError = null;
        _activeRoutes = selectedRoute != null &&
                selectedRoute['status']?.toString() == 'in_progress' &&
                _isSameDay(_selectedDate, DateTime.now()) &&
                !_isViewingHistory
            ? [selectedRoute]
            : [];
        _dynamicStops = stops;
        if (routeChanged) {
          _roadPolyline = [];
          _realBusPositions.clear();
          _realBusHeadings.clear();
          _busAnimationTimer?.cancel();
          _busAnimationGeneration++;
          _gpsLastUpdated = null;
          _gpsIsStale = true;
        }
        _selectedRouteApiId = selectedId;
        _selectedRouteId = selectedId == null
            ? '—'
            : 'CT-${selectedId.substring(0, selectedId.length < 8 ? selectedId.length : 8).toUpperCase()}';
        _selectedRouteDistance =
            (selectedRoute?['total_distance'] as num?)?.toDouble() ?? 0;
        final firstName = stops.isNotEmpty ? stops.first.name : '';
        final lastName = stops.length > 1 ? stops.last.name : '';
        _routeName = stops.isEmpty
            ? 'Chưa có chuyến trong ngày này'
            : (lastName.isEmpty ? firstName : '$firstName - $lastName');
        final tripType = selectedRoute?['trip_type']?.toString();
        final sessionId = selectedRoute?['session_id']?.toString();
        _routeDirection = [
          if (tripType != null) tripType == 'pickup' ? 'Chiều đi' : 'Chiều về',
          if (sessionId != null) sessionId,
          if (_isViewingHistory) 'Đã qua',
        ].join(' • ');
        _selectedStopForTooltip = null;
        if (_activeRoutes.isEmpty) {
          _gpsLastUpdated = null;
          _gpsIsStale = true;
          _realBusPositions.clear();
          _realBusHeadings.clear();
        }
      });
      if (routeChanged && stops.isNotEmpty) _moveMapTo(stops.first.pos, 13.5);
      if (routeChanged || previouslyActive != _activeRoutes.isNotEmpty) {
        _renderMapAnnotations();
      }
      if (routeChanged) {
        _fetchRoutePolyline(stops, selectedId);
      }
    } catch (error) {
      if (!mounted ||
          requestId != _loadRequestId ||
          requestedDate != _dateKey(_selectedDate)) {
        return;
      }
      setState(() {
        _isLoadingTrip = false;
        _tripLoadError = error.toString();
        _activeRoutes = [];
        _dayRouteIds = [];
        _dynamicStops = [];
        _selectedRouteApiId = null;
        _selectedRouteId = '—';
        _routeName = 'Không tải được chuyến';
        _routeDirection = '';
        _roadPolyline = [];
        _realBusPositions.clear();
        _realBusHeadings.clear();
        _gpsLastUpdated = null;
        _gpsIsStale = true;
      });
      _renderMapAnnotations();
    }
  }

  String _dateKey(DateTime date) =>
      '${date.year.toString().padLeft(4, '0')}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';

  Future<void> _changeSelectedDate(DateTime date) async {
    setState(() {
      _selectedDate = DateTime(date.year, date.month, date.day);
      _isViewingHistory =
          _dateKey(_selectedDate).compareTo(_dateKey(DateTime.now())) < 0;
      _isLoadingTrip = true;
    });
    await _loadActiveRoutes();
  }

  Future<void> _showTripHistory() async {
    if (_myTickets.isEmpty) {
      try {
        final tickets = await widget.api.fetchMyTickets();
        if (mounted) setState(() => _myTickets = tickets);
      } catch (_) {}
    }
    if (!mounted) return;
    final history = _myTickets.whereType<Map>().where((ticket) {
      final date = DateTime.tryParse(ticket['service_date']?.toString() ?? '');
      return date != null &&
          _dateKey(date).compareTo(_dateKey(DateTime.now())) < 0 &&
          ticket['route_id'] != null &&
          const {'assigned', 'used'}.contains(ticket['status']?.toString());
    }).toList()
      ..sort((a, b) => (b['service_date']?.toString() ?? '')
          .compareTo(a['service_date']?.toString() ?? ''));

    final choice = await showModalBottomSheet<Map>(
      context: context,
      isScrollControlled: true,
      builder: (context) => SafeArea(
        child: SizedBox(
          height: MediaQuery.sizeOf(context).height * .65,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Padding(
                padding: EdgeInsets.fromLTRB(20, 20, 20, 8),
                child: Text('Lịch sử chuyến',
                    style:
                        TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
              ),
              Expanded(
                child: history.isEmpty
                    ? const Center(
                        child: Text('Chưa có chuyến đã qua để xem lại.'))
                    : ListView.builder(
                        itemCount: history.length,
                        itemBuilder: (context, index) {
                          final ticket = history[index];
                          final date = DateTime.tryParse(
                              ticket['service_date'].toString());
                          final dateLabel = date == null
                              ? ticket['service_date'].toString()
                              : '${date.day.toString().padLeft(2, '0')}/${date.month.toString().padLeft(2, '0')}/${date.year}';
                          final direction =
                              ticket['trip_type']?.toString() == 'pickup'
                                  ? 'Chiều đi'
                                  : 'Chiều về';
                          return ListTile(
                            leading: const CircleAvatar(
                                child: Icon(Icons.history_rounded)),
                            title: Text('$dateLabel • $direction'),
                            subtitle: Text(ticket['session_id']?.toString() ??
                                'Chuyến xe'),
                            trailing: const Icon(Icons.chevron_right_rounded),
                            onTap: () => Navigator.pop(context, ticket),
                          );
                        },
                      ),
              ),
            ],
          ),
        ),
      ),
    );
    if (choice == null || !mounted) return;
    final date = DateTime.tryParse(choice['service_date']?.toString() ?? '');
    if (date == null) return;
    setState(() {
      _selectedDate = date;
      _isViewingHistory = true;
      _isLoadingTrip = true;
    });
    await _loadActiveRoutes(preferredRouteId: choice['route_id']?.toString());
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
    _pollingTimer = Timer.periodic(const Duration(seconds: 10), (_) {
      _pollGpsPositions();
    });
    _routeRefreshTimer = Timer.periodic(const Duration(seconds: 15), (_) {
      _loadActiveRoutes();
    });
  }

  Future<void> _pollGpsPositions() async {
    if (_pollingGpsPositions) return;
    _pollingGpsPositions = true;
    try {
      await _pollGpsPositionsOnce();
    } finally {
      _pollingGpsPositions = false;
    }
  }

  Future<void> _pollGpsPositionsOnce() async {
    if (_activeRoutes.isEmpty) {
      if (_realBusPositions.isNotEmpty) {
        _realBusPositions.clear();
        _realBusHeadings.clear();
        _busAnimationTimer?.cancel();
        _busSymbol = null;
        _busRenderedPosition = null;
        _renderMapAnnotations();
      }
      return;
    }
    var positionChanged = false;
    for (final route in _activeRoutes) {
      final routeId = route['id']?.toString();
      if (routeId == null) continue;
      try {
        final gps = await widget.api.fetchLatestGps(routeId);
        if (gps != null &&
            gps.containsKey('latitude') &&
            gps.containsKey('longitude')) {
          final recordedAt =
              DateTime.tryParse(gps['recorded_at']?.toString() ?? '')
                  ?.toLocal();
          final age =
              recordedAt == null ? null : DateTime.now().difference(recordedAt);
          final isStale = recordedAt == null ||
              age! > const Duration(seconds: 60) ||
              age < -const Duration(seconds: 30);
          if (isStale) {
            positionChanged =
                _realBusPositions.remove(routeId) != null || positionChanged;
            _realBusHeadings.remove(routeId);
            if (mounted) {
              setState(() {
                _gpsLastUpdated = recordedAt;
                _gpsIsStale = true;
              });
            }
            continue;
          }
          final lat = (gps['latitude'] as num).toDouble();
          final lng = (gps['longitude'] as num).toDouble();
          final position = LatLng(lat, lng);
          final previousPosition =
              _busRenderedPosition ?? _realBusPositions[routeId];
          final previousHeading = previousPosition == null
              ? ((gps['heading'] as num?)?.toDouble() ?? 0)
              : _busRenderedHeading;
          final heading = (gps['heading'] as num?)?.toDouble() ?? 0;
          if (mounted) {
            setState(() {
              _realBusPositions[routeId] = position;
              _realBusHeadings[routeId] = heading;
              _gpsLastUpdated = recordedAt;
              _gpsIsStale = false;
            });
            if (previousPosition == null) {
              _updateBusAnnotation(position: position, heading: heading);
            } else {
              _animateBusMarker(
                previousPosition,
                position,
                previousHeading,
                heading,
              );
            }
          }
        } else {
          positionChanged =
              _realBusPositions.remove(routeId) != null || positionChanged;
          _realBusHeadings.remove(routeId);
          if (mounted) {
            setState(() {
              _gpsLastUpdated = null;
              _gpsIsStale = true;
            });
          }
        }
      } catch (_) {
        positionChanged =
            _realBusPositions.remove(routeId) != null || positionChanged;
        _realBusHeadings.remove(routeId);
        if (mounted) {
          setState(() {
            _gpsLastUpdated = null;
            _gpsIsStale = true;
          });
        }
      }
    }
    if (positionChanged && mounted) {
      _busAnimationTimer?.cancel();
      _busAnimationGeneration++;
      _busSymbol = null;
      _busRenderedPosition = null;
      _renderMapAnnotations();
    }
  }

  List<_BusStop> get _effectiveStops => _dynamicStops;

  String get _displayDirectionName {
    return _routeName;
  }

  String get _gpsStatusLabel {
    if (_gpsIsStale || _gpsLastUpdated == null) {
      return 'Đang chờ tín hiệu GPS • vị trí cũ đã ẩn';
    }
    final time = _gpsLastUpdated!;
    return 'Xe trực tiếp • cập nhật ${time.hour.toString().padLeft(2, '0')}:${time.minute.toString().padLeft(2, '0')}';
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
    final center = _effectiveStops.isNotEmpty
        ? _effectiveStops.first.pos
        : const LatLng(10.0380, 105.7830);
    return ml.MapLibreMap(
      styleString: ApiConfig.goongMapStyleUrl,
      initialCameraPosition: ml.CameraPosition(
        target: ml.LatLng(center.latitude, center.longitude),
        zoom: 13.5,
      ),
      attributionButtonPosition: ml.AttributionButtonPosition.topLeft,
      attributionButtonMargins: const Point(8, 58),
      onMapCreated: (controller) {
        _goongMapController = controller;
        controller.onCircleTapped.add(_onMapCircleTapped);
        final pendingCenter = _pendingMapCenter;
        if (pendingCenter != null) {
          _pendingMapCenter = null;
          _moveMapTo(pendingCenter, _pendingMapZoom);
        }
      },
      onStyleLoadedCallback: () {
        _mapStyleLoaded = true;
        _registerBusIconAndRender();
      },
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
              child: const Icon(Icons.arrow_back_ios_new_rounded,
                  size: 18, color: AppColors.textPrimary),
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
                    boxShadow: [
                      BoxShadow(color: Colors.black12, blurRadius: 8)
                    ],
                  ),
                  child: const Icon(Icons.my_location_rounded,
                      size: 20, color: Color(0xFFEA4335)),
                ),
              ),
              // Compass button
              GestureDetector(
                onTap: () {
                  _goongMapController
                      ?.animateCamera(ml.CameraUpdate.bearingTo(0));
                },
                child: Container(
                  width: 40,
                  height: 40,
                  decoration: const BoxDecoration(
                    color: Colors.white,
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(color: Colors.black12, blurRadius: 8)
                    ],
                  ),
                  child: const Icon(Icons.explore_rounded,
                      size: 22, color: Color(0xFFEA4335)),
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
                  Text(stop.name,
                      style: const TextStyle(
                          fontSize: 18, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  Text('Giờ đón dự kiến: ${stop.estimatedTime}',
                      style:
                          const TextStyle(fontSize: 14, color: AppColors.teal)),
                  const SizedBox(height: 12),
                  const Text('Tọa độ:',
                      style:
                          TextStyle(fontSize: 12, color: AppColors.textMuted)),
                  Text(
                      '${stop.pos.latitude.toStringAsFixed(5)}, ${stop.pos.longitude.toStringAsFixed(5)}',
                      style: const TextStyle(
                          fontSize: 13, fontWeight: FontWeight.w500)),
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
                    const Text('Xem thông tin trạm',
                        style: TextStyle(
                            fontSize: 11, color: AppColors.textMuted)),
                    Text(stop.name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.bold,
                            color: AppColors.textPrimary)),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right_rounded,
                  color: AppColors.textMuted),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildDraggableSheet() {
    return DraggableScrollableSheet(
      controller: _panelController,
      initialChildSize: 0.50,
      minChildSize: 0.06,
      maxChildSize: 0.88,
      snap: true,
      snapSizes: const [.45],
      shouldCloseOnMinExtent: false,
      builder: (context, scrollController) {
        return Container(
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
            boxShadow: [
              BoxShadow(
                  color: Colors.black12, blurRadius: 16, offset: Offset(0, -4)),
            ],
          ),
          child: _panelCollapsed
              ? ListView(
                  controller: scrollController,
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
                                  color: Colors.grey.shade300,
                                  borderRadius: BorderRadius.circular(3),
                                ),
                              ),
                              const SizedBox(width: 10),
                              Text(
                                _selectedRouteId,
                                style: const TextStyle(
                                  color: Color(0xFF07835A),
                                  fontWeight: FontWeight.w700,
                                  fontSize: 12,
                                ),
                              ),
                              const SizedBox(width: 6),
                              const Icon(Icons.keyboard_arrow_up_rounded,
                                  size: 20),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ],
                )
              : ListView(
                  controller: scrollController,
                  padding: const EdgeInsets.only(bottom: 24),
                  children: [
                    // Drag Handle Pill
                    Center(
                      child: InkWell(
                        onTap: _togglePanel,
                        borderRadius: BorderRadius.circular(20),
                        child: Padding(
                          padding: const EdgeInsets.all(10),
                          child: Container(
                            width: 40,
                            height: 4,
                            decoration: BoxDecoration(
                              color: Colors.grey.shade300,
                              borderRadius: BorderRadius.circular(2),
                            ),
                          ),
                        ),
                      ),
                    ),

                    _buildTripDateBar(),
                    if (_dayRouteIds.length > 1) _buildDayTripChoices(),
                    const SizedBox(height: 8),
                    if (_isLoadingTrip)
                      const Padding(
                        padding: EdgeInsets.all(32),
                        child: Center(child: CircularProgressIndicator()),
                      )
                    else if (_selectedRouteApiId == null)
                      _buildNoTripCard()
                    else ...[
                      _buildRouteHeaderCard(),
                      const SizedBox(height: 8),
                      TabBar(
                        controller: _tabController,
                        labelColor: const Color(0xFFEA4335),
                        unselectedLabelColor: AppColors.textMuted,
                        indicatorColor: const Color(0xFFEA4335),
                        indicatorWeight: 3,
                        labelStyle: const TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 14,
                        ),
                        unselectedLabelStyle: const TextStyle(
                          fontWeight: FontWeight.w500,
                          fontSize: 14,
                        ),
                        tabs: const [
                          Tab(text: 'Danh sách trạm'),
                          Tab(text: 'Biểu đồ giờ'),
                          Tab(text: 'Thông tin'),
                        ],
                      ),
                      const Divider(height: 1, color: AppColors.border),
                      const SizedBox(height: 12),
                      if (_tabController.index == 0) _buildStopsTab(),
                      if (_tabController.index == 1) _buildTimetableTab(),
                      if (_tabController.index == 2) _buildInfoTab(),
                    ],
                  ],
                ),
        );
      },
    );
  }

  Widget _buildTripDateBar() {
    final dateLabel = _isSameDay(_selectedDate, DateTime.now())
        ? 'Hôm nay'
        : '${_selectedDate.day.toString().padLeft(2, '0')}/${_selectedDate.month.toString().padLeft(2, '0')}/${_selectedDate.year}';
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: [
          IconButton(
            tooltip: 'Ngày trước',
            onPressed: () => _changeSelectedDate(
                _selectedDate.subtract(const Duration(days: 1))),
            icon: const Icon(Icons.chevron_left_rounded),
          ),
          Expanded(
            child: Column(
              children: [
                Text(dateLabel,
                    style: const TextStyle(
                        fontSize: 16, fontWeight: FontWeight.w700)),
                Text(_isViewingHistory ? 'Đang xem lịch sử' : 'Chuyến của bạn',
                    style: const TextStyle(
                        fontSize: 12, color: AppColors.textMuted)),
              ],
            ),
          ),
          IconButton(
            tooltip: 'Ngày tiếp theo',
            onPressed: () =>
                _changeSelectedDate(_selectedDate.add(const Duration(days: 1))),
            icon: const Icon(Icons.chevron_right_rounded),
          ),
          IconButton(
            tooltip: 'Lịch sử chuyến',
            onPressed: _showTripHistory,
            icon: const Icon(Icons.history_rounded, color: AppColors.teal),
          ),
        ],
      ),
    );
  }

  Widget _buildNoTripCard() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 24, 20, 20),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(22),
        decoration: BoxDecoration(
          color: const Color(0xFFF4F8F8),
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: AppColors.border),
        ),
        child: Column(
          children: [
            Icon(
                _tripLoadError == null
                    ? Icons.directions_bus_outlined
                    : Icons.cloud_off_outlined,
                size: 42,
                color: AppColors.teal),
            const SizedBox(height: 10),
            Text(
              _tripLoadError == null
                  ? 'Bạn chưa có chuyến trong ngày này'
                  : 'Chưa tải được thông tin chuyến',
              textAlign: TextAlign.center,
              style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                  color: AppColors.textPrimary),
            ),
            const SizedBox(height: 6),
            Text(
              _tripLoadError == null
                  ? 'Bản đồ sẽ hiển thị tuyến khi có chuyến được gán cho bạn.'
                  : 'Kiểm tra kết nối rồi thử tải lại.',
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 13, color: AppColors.textMuted),
            ),
            if (_tripLoadError != null) ...[
              const SizedBox(height: 12),
              OutlinedButton.icon(
                onPressed: () {
                  setState(() => _isLoadingTrip = true);
                  _loadActiveRoutes();
                },
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('Thử lại'),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildDayTripChoices() {
    final ticketsByRoute = <String, Map>{};
    for (final ticket in _myTickets.whereType<Map>()) {
      final routeId = ticket['route_id']?.toString();
      if (routeId != null && _dayRouteIds.contains(routeId)) {
        ticketsByRoute.putIfAbsent(routeId, () => ticket);
      }
    }
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
      child: Wrap(
        spacing: 8,
        runSpacing: 6,
        children: [
          for (final routeId in _dayRouteIds)
            ChoiceChip(
              label: Text(
                  '${ticketsByRoute[routeId]?['trip_type']?.toString() == 'pickup' ? 'Chiều đi' : 'Chiều về'} • ${ticketsByRoute[routeId]?['session_id'] ?? 'Chuyến'}'),
              selected: routeId == _selectedRouteApiId,
              onSelected: (_) {
                setState(() => _isLoadingTrip = true);
                _loadActiveRoutes(preferredRouteId: routeId);
              },
            ),
        ],
      ),
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
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
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
                  if (_activeRoutes.isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Text(
                      _gpsStatusLabel,
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        color: _gpsIsStale ? Colors.deepOrange : AppColors.teal,
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: const Color(0xFFE6F4EA),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                    color: const Color(0xFF34A853).withValues(alpha: 0.3)),
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
            const Text(
                'Tuyến chưa được sinh hoặc chưa được gán cho vé của bạn.')
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
                    _renderMapAnnotations();
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
                              fontWeight: isSelected
                                  ? FontWeight.bold
                                  : FontWeight.w500,
                              color: isSelected
                                  ? const Color(0xFFEA4335)
                                  : AppColors.textPrimary,
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
                  onPressed: () => _changeSelectedDate(
                      _selectedDate.subtract(const Duration(days: 1))),
                  icon: const Icon(Icons.chevron_left_rounded,
                      color: AppColors.textPrimary),
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
                  onPressed: () => _changeSelectedDate(
                      _selectedDate.add(const Duration(days: 1))),
                  icon: const Icon(Icons.chevron_right_rounded,
                      color: AppColors.textPrimary),
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Text(
            _routeDirection.isEmpty ? 'Chưa có lịch chạy' : _routeDirection,
            style: const TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: AppColors.teal),
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
          _infoFieldRow('Điểm đầu:',
              _effectiveStops.isEmpty ? '—' : _effectiveStops.first.name),
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
              style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.bold,
                  color: AppColors.textPrimary),
            ),
            TextSpan(
              text: value,
              style: const TextStyle(
                  fontSize: 13,
                  color: AppColors.textSecondary,
                  fontWeight: FontWeight.w500),
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
  const _BusStop(this.pos, this.name, this.type, this.routes,
      [this.estimatedTime = '06:00']);
}
