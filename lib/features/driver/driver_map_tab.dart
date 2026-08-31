import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../../services/api_service.dart';
import '../../theme/app_theme.dart';

class DriverMapTab extends StatefulWidget {
  const DriverMapTab({super.key, required this.api, this.initialRoute});
  final ApiService api;
  final Map<String, dynamic>? initialRoute;
  @override
  State<DriverMapTab> createState() => _DriverMapTabState();
}

class _DriverMapTabState extends State<DriverMapTab>
    with SingleTickerProviderStateMixin {
  final _map = MapController();
  late TabController _tabs;
  Map<String, dynamic>? _route;
  List<_Stop> _stops = [];
  bool _loading = true, _busy = false;
  String? _error;
  String? get _id => _route?['id']?.toString();
  String get _routeCode {
    final routeId = _id;
    if (routeId == null || routeId.isEmpty) return '—';
    if (routeId.length > 5) {
      return 'CT-${routeId.substring(0, 5).toUpperCase()}';
    }
    return 'CT-$routeId';
  }
  String get _status => _route?['status']?.toString() ?? 'pending';
  LatLng get _center =>
      _stops.isEmpty ? const LatLng(10.0302, 105.7721) : _stops.first.point;

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 3, vsync: this);
    _route = widget.initialRoute;
    _load();
  }

  @override
  void dispose() {
    _tabs.dispose();
    _map.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final routeId = _id;
    if (routeId == null || routeId.isEmpty) {
      setState(() {
        _loading = false;
        _error = 'Chưa có tuyến được phân công.';
      });
      return;
    }
    try {
      final route = await widget.api.fetchRouteDetails(routeId);
      final stops = (route['stops'] as List<dynamic>? ?? []).map((raw) {
        final item = Map<String, dynamic>.from(raw as Map);
        final loc = Map<String, dynamic>.from(item['location'] as Map? ?? {});
        final date = DateTime.tryParse(item['arrival_time']?.toString() ?? '')
            ?.toLocal();
        return _Stop(
          loc['name']?.toString() ?? 'Trạm ${item['stop_order']}',
          LatLng((loc['latitude'] as num?)?.toDouble() ?? 10.0302,
              (loc['longitude'] as num?)?.toDouble() ?? 105.7721),
          date == null
              ? 'Đang cập nhật'
              : '${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}',
          (item['stop_order'] as num?)?.toInt() ?? 0,
        );
      }).toList()
        ..sort((a, b) => a.order.compareTo(b.order));
      if (mounted)
        setState(() {
          _route = route;
          _stops = stops;
          _error = null;
        });
    } catch (e) {
      if (mounted) setState(() => _error = 'Không thể tải tuyến: $e');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _confirmToggle() async {
    if (_id == 0 || _status == 'completed' || _busy) return;
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
              ? 'Bạn có chắc chắn muốn BẮT ĐẦU chuyến xe CT-${_id.toString().padLeft(2, '0')} không?'
              : 'Bạn có chắc chắn muốn KẾT THÚC chuyến xe CT-${_id.toString().padLeft(2, '0')} không?',
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
      if (mounted) {
        setState(() {
          _route = updatedRoute;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              wasInProgress
                  ? 'Đã kết thúc chuyến xe CT-${_id.toString().padLeft(2, '0')}.'
                  : 'Đã bắt đầu chuyến xe CT-${_id.toString().padLeft(2, '0')}. Chúc bạn lái xe an toàn!',
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
  Widget build(BuildContext context) => Scaffold(
      body: _loading
          ? const Center(
              child: CircularProgressIndicator(color: AppColors.teal))
          : _error != null
              ? Center(
                  child: Column(mainAxisSize: MainAxisSize.min, children: [
                  const Icon(Icons.route_outlined,
                      size: 52, color: AppColors.teal),
                  const SizedBox(height: 12),
                  Text(_error!),
                  TextButton(onPressed: _load, child: const Text('Tải lại'))
                ]))
              : Stack(children: [
                  FlutterMap(
                      mapController: _map,
                      options:
                          MapOptions(initialCenter: _center, initialZoom: 13.5),
                      children: [
                        TileLayer(
                            urlTemplate:
                                'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                            userAgentPackageName: 'com.ctu.myctubus'),
                        if (_stops.length > 1)
                          PolylineLayer(polylines: [
                            Polyline(
                                points: _stops.map((s) => s.point).toList(),
                                color: const Color(0xFFFF5D3D),
                                strokeWidth: 4)
                          ]),
                        MarkerLayer(markers: [
                          for (var i = 0; i < _stops.length; i++)
                            Marker(
                                point: _stops[i].point,
                                width: 38,
                                height: 38,
                                child: _Pin(
                                    active: _status == 'in_progress' && i == 0))
                        ]),
                      ]),
                  SafeArea(
                      child: Padding(
                          padding: const EdgeInsets.all(12),
                          child: Row(children: [
                            _circle(Icons.arrow_back,
                                () => Navigator.maybePop(context)),
                            const Spacer(),
                            _circle(Icons.my_location_rounded,
                                () => _map.move(_center, 14))
                          ]))),
                  _panel(),
                ]));

  Widget _circle(IconData icon, VoidCallback fn) => Material(
      color: Colors.white,
      shape: const CircleBorder(),
      elevation: 2,
      child: IconButton(onPressed: fn, icon: Icon(icon)));
  String get _title => _stops.length < 2
      ? 'Tuyến đã tối ưu'
      : '${_stops.first.name} - ${_stops.last.name}';
  Widget _panel() => DraggableScrollableSheet(
      initialChildSize: .50,
      minChildSize: .24,
      maxChildSize: .86,
      builder: (_, scroll) => Container(
            decoration: const BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.vertical(top: Radius.circular(22)),
                boxShadow: [BoxShadow(color: Colors.black26, blurRadius: 12)]),
            child: Column(children: [
              Container(
                  margin: const EdgeInsets.only(top: 11),
                  height: 4,
                  width: 40,
                  decoration: BoxDecoration(
                      color: const Color(0xFFFFD4C9),
                      borderRadius: BorderRadius.circular(3))),
              Padding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 9),
                  child: Row(children: [
                    Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 7, vertical: 5),
                        decoration: BoxDecoration(
                            color: const Color(0xFFE7F5EF),
                            borderRadius: BorderRadius.circular(5)),
                        child: Text(_routeCode,
                            style: const TextStyle(
                                color: Color(0xFF07835A),
                                fontWeight: FontWeight.w800,
                                fontSize: 16))),
                    const SizedBox(width: 7),
                    Expanded(
                        child: Text(_title,
                            maxLines: 2,
                            style: const TextStyle(
                                fontSize: 12, fontWeight: FontWeight.w600))),
                    _chip(),
                  ])),
              TabBar(
                  controller: _tabs,
                  labelColor: const Color(0xFFFF5D3D),
                  unselectedLabelColor: const Color(0xFF343A40),
                  indicatorColor: const Color(0xFFFF5D3D),
                  tabs: const [
                    Tab(text: 'Danh sách trạm'),
                    Tab(text: 'Biểu đồ giờ'),
                    Tab(text: 'Thông tin')
                  ]),
              Expanded(
                  child: TabBarView(controller: _tabs, children: [
                _stopsView(scroll),
                _hoursView(scroll),
                _infoView(scroll)
              ])),
            ]),
          ));
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
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 6,
            height: 6,
            decoration: BoxDecoration(color: fg, shape: BoxShape.circle),
          ),
          const SizedBox(width: 5),
          Text(
            label,
            style: TextStyle(
              fontSize: 11,
              color: fg,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
  Widget _stopsView(ScrollController scroll) => ListView(
          controller: scroll,
          padding: const EdgeInsets.fromLTRB(24, 15, 16, 24),
          children: [
            Text('Tuyến $_routeCode',
                style: const TextStyle(
                    color: Color(0xFFFF4D32),
                    fontSize: 16,
                    fontWeight: FontWeight.w700)),
            const SizedBox(height: 10),
            for (var i = 0; i < _stops.length; i++)
              _stopLine(_stops[i], i == _stops.length - 1),
            const SizedBox(height: 10),
            _button()
          ]);
  Widget _stopLine(_Stop s, bool last) =>
      Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Column(children: [
          const Icon(Icons.circle, size: 11, color: Color(0xFF788992)),
          if (!last)
            Container(width: 2, height: 27, color: const Color(0xFFD8DFE2))
        ]),
        const SizedBox(width: 11),
        Expanded(
            child: Padding(
                padding: const EdgeInsets.only(bottom: 15),
                child: Row(children: [
                  Expanded(
                      child:
                          Text(s.name, style: const TextStyle(fontSize: 13))),
                  Text(s.time,
                      style: const TextStyle(
                          fontSize: 12, color: Color(0xFF75828B)))
                ])))
      ]);
  Widget _hoursView(ScrollController scroll) => ListView(
          controller: scroll,
          padding: const EdgeInsets.all(20),
          children: [
            const Center(
                child: Text('Hôm nay',
                    style: TextStyle(fontWeight: FontWeight.w700))),
            const SizedBox(height: 18),
            Wrap(
                spacing: 20,
                runSpacing: 14,
                children: _stops
                    .map((s) => SizedBox(
                        width: 75,
                        child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(s.time,
                                  style: const TextStyle(
                                      fontWeight: FontWeight.w700)),
                              Text('Trạm ${s.order}',
                                  style: const TextStyle(
                                      fontSize: 11, color: Color(0xFF75828B)))
                            ])))
                    .toList())
          ]);
  Widget _infoView(ScrollController scroll) => ListView(
          controller: scroll,
          padding: const EdgeInsets.all(20),
          children: [
            _line('Tuyến số', _routeCode),
            _line('Tên tuyến', _title),
            _line(
                'Giờ hoạt động',
                _stops.isEmpty
                    ? 'Đang cập nhật'
                    : '${_stops.first.time} - ${_stops.last.time}'),
            _line('Quãng đường chạy toàn tuyến',
                '${(_route?['total_distance'] as num?)?.toStringAsFixed(1) ?? '—'} km'),
            _line('Số trạm phục vụ', '${_stops.length} trạm'),
            const SizedBox(height: 10),
            _button()
          ]);
  Widget _line(String key, String value) => Padding(
      padding: const EdgeInsets.only(bottom: 15),
      child: RichText(
          text: TextSpan(
              style: const TextStyle(fontSize: 13, color: Color(0xFF273130)),
              children: [
            TextSpan(
                text: '$key: ',
                style: const TextStyle(fontWeight: FontWeight.w700)),
            TextSpan(
                text: value, style: const TextStyle(color: Color(0xFF75828B)))
          ])));
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
  const _Stop(this.name, this.point, this.time, this.order);
  final String name, time;
  final LatLng point;
  final int order;
}

class _Pin extends StatelessWidget {
  const _Pin({required this.active});
  final bool active;
  @override
  Widget build(BuildContext context) => Container(
      decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: active ? const Color(0xFFFFA23B) : const Color(0xFFFF6B4A),
          border: Border.all(color: Colors.white, width: 2),
          boxShadow: const [BoxShadow(color: Colors.black26, blurRadius: 4)]),
      child: const Icon(Icons.directions_bus_rounded,
          size: 20, color: Colors.white));
}
