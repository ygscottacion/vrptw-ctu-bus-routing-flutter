import 'package:flutter/material.dart';
import 'package:qr_flutter/qr_flutter.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class TicketScreen extends StatefulWidget {
  const TicketScreen({super.key, required this.api});
  final ApiService api;

  @override
  State<TicketScreen> createState() => _TicketScreenState();
}

class _TicketScreenState extends State<TicketScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  String? _selectedRoute; // location.id (UUID string)
  String _sessionId = 'MORNING_1';
  String _tripType = 'pickup';
  late DateTime _serviceDate;

  List<_Route> _routes = [];
  bool _loadingRoutes = true;
  String? _routeError;

  List<_MyTicket> _myTickets = [];
  bool _loadingTickets = true;

  bool _isBuying = false;
  String? _buyError;

  /// Cache Future theo routeId de tranh goi lai API moi lan rebuild widget
  /// (FutureBuilder se goi lai future moi lan build neu khong cache).
  final Map<String, Future<Map<String, dynamic>>> _routeDetailsCache = {};

  Future<Map<String, dynamic>> _routeFuture(String routeId) {
    return _routeDetailsCache.putIfAbsent(
        routeId, () => widget.api.fetchRouteDetails(routeId));
  }

  // ─── Ngày chạy / Deadline 22:00 (Asia/Ho_Chi_Minh) ─────────
  // Ghi chú: Việt Nam không dùng giờ mùa hè (DST) nên lệch cố định UTC+7
  // là đủ chính xác cho MVP. Nếu sau này cần xử lý đa timezone thật sự,
  // nên chuyển sang package `timezone`.
  //
  // QUAN TRONG: _nowVN duoc danh dau isUtc=true (qua .toUtc().add(7h)) de
  // "gia lap" gio VN. De so sanh dung, MOI DateTime khac dung trong tinh
  // deadline (candidate, deadline...) PHAI cung dung DateTime.utc(...),
  // khong duoc dung DateTime(...) (local) - vi Dart so sanh isBefore/
  // isAfter theo epoch tuyet doi, khong theo gio hien thi. Tron 2 kieu
  // se gay lech dung 7 tieng (bug da gap va sua ngay 3).
  static const _vnOffset = Duration(hours: 7);
  DateTime get _nowVN => DateTime.now().toUtc().add(_vnOffset);

  /// Tao DateTime trong "khong gian gio VN" giong _nowVN (danh dau UTC
  /// nhung mang gia tri gio VN) de dam bao so sanh chinh xac.
  DateTime _vn(int year, int month, int day, [int hour = 0, int minute = 0]) =>
      DateTime.utc(year, month, day, hour, minute);

  static const _maxFutureDays = 3;

  List<_ServiceDateOption> _dateOptions = [];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _dateOptions = _buildDateOptions();
    final firstBookable = _dateOptions.firstWhere(
      (d) => d.bookable,
      orElse: () => _dateOptions.first,
    );
    _serviceDate = firstBookable.date;
    _loadRoutes();
    _loadTickets();
  }

  List<_ServiceDateOption> _buildDateOptions() {
    final todayVN = _vn(_nowVN.year, _nowVN.month, _nowVN.day);
    final options = <_ServiceDateOption>[];
    for (var i = 1; i <= _maxFutureDays; i++) {
      final candidate = todayVN.add(Duration(days: i));
      final deadline = candidate
          .subtract(const Duration(days: 1))
          .add(const Duration(hours: 22));
      final bookable = _nowVN.isBefore(deadline);
      options.add(_ServiceDateOption(candidate, deadline, bookable));
    }
    return options;
  }

  Future<void> _loadRoutes() async {
    try {
      final items = await widget.api.fetchLocations();
      if (!mounted) return;

      final List<_Route> loadedRoutes = [];
      final colors = [
        AppColors.teal,
        AppColors.purple,
        AppColors.orange,
        Colors.blue,
        Colors.green,
      ];

      for (var i = 0; i < items.length; i++) {
        final r = items[i] as Map<String, dynamic>;
        final id = r['id'].toString(); // UUID string
        final label = r['name']?.toString() ?? 'Trạm $id';
        // Gia dong 7.000d moi tram: LocationResponse backend khong co field
        // gia (chi co name/lat/lng/time_window/demand) - day la thiet ke
        // hien tai cua backend, khong phai Flutter tu bia.
        loadedRoutes.add(_Route(id, label, 7000, colors[i % colors.length]));
      }

      setState(() {
        _routes = loadedRoutes;
        _routeError = null;
        final selectable = _routes.where((r) => !_isCtuStop(r.label)).toList();
        if (selectable.isNotEmpty) {
          _selectedRoute = selectable.first.id;
        } else if (_routes.isNotEmpty) {
          _selectedRoute = _routes.first.id;
        }
      });
    } catch (e) {
      if (mounted) {
        setState(() {
          _routeError = e.toString();
        });
      }
    } finally {
      if (mounted) setState(() => _loadingRoutes = false);
    }
  }

  /// Backend Ngay 4 da co du 5 trang thai that: reserved/assigned/used/
  /// cancelled/expired - khong con phai suy luan qua route_id nua.
  Future<void> _loadTickets() async {
    try {
      final items = await widget.api.fetchMyTickets();
      if (!mounted) return;
      setState(
        () => _myTickets = items.map((item) {
          final ticket = item as Map<String, dynamic>;
          final status = ticket['status']?.toString() ?? 'expired';
          final routeId = ticket['route_id']?.toString();
          return _MyTicket(
            id: 'BUS${ticket['id']}',
            type: 'Vé điện tử',
            purchasedDate:
                ticket['created_at']?.toString().split('T').first ?? '—',
            status: status,
            routeId: routeId,
            qrData: ticket['qr_code']?.toString() ?? '',
          );
        }).toList(),
      );
    } catch (_) {
      // Người dùng chưa đăng nhập hoặc backend chưa sẵn sàng.
    } finally {
      if (mounted) setState(() => _loadingTickets = false);
    }
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  String _formatVND(int n) {
    return '${n.toString().replaceAllMapped(RegExp(r'(\d{1,3})(?=(\d{3})+(?!\d))'), (m) => '${m[1]}.')}đ';
  }

  String _formatDateShort(DateTime d) =>
      '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}';

  String _weekdayLabel(DateTime d) {
    const labels = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'];
    return labels[d.weekday - 1];
  }

  Map<String, int> get _price {
    if (_routes.isEmpty || _selectedRoute == null) {
      return {'original': 0, 'discount': 0, 'total': 0};
    }
    final route = _routes.firstWhere((r) => r.id == _selectedRoute);
    // MVP chi ban 1 loai ve luot duy nhat, khong giam gia.
    return {'original': route.price, 'discount': 0, 'total': route.price};
  }

  /// Nhan dien tram CTU (diem xuat phat/ket thuc mac dinh, khong can cho
  /// hoc sinh chon: chieu di luon ve CTU, chieu ve luon xuat phat tu CTU).
  bool _isCtuStop(String label) {
    final n = label.toLowerCase();
    return n.contains('ctu') ||
        n.contains('đại học cần thơ') ||
        n.contains('depot');
  }

  /// Danh sach tram hien thi cho hoc sinh chon - da loai tru tram CTU.
  List<_Route> get _selectableRoutes =>
      _routes.where((r) => !_isCtuStop(r.label)).toList();

  bool get _isSelectedDateBookable {
    final match = _dateOptions.where((d) => _isSameDate(d.date, _serviceDate));
    if (match.isEmpty) return false;
    return match.first.bookable;
  }

  bool _isSameDate(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bg,
      appBar: AppBar(
        title: const Text(
          'Vé & Check-in',
          style: TextStyle(fontWeight: FontWeight.w700),
        ),
        elevation: 0,
        backgroundColor: AppColors.white,
        centerTitle: true,
        bottom: TabBar(
          controller: _tabController,
          labelColor: AppColors.teal,
          unselectedLabelColor: AppColors.textMuted,
          indicatorColor: AppColors.teal,
          indicatorWeight: 3.0,
          labelStyle:
              const TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
          tabs: const [
            Tab(text: 'Vé của tôi'),
            Tab(text: 'Mua vé'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [_buildMyTickets(), _buildBuyTicket()],
      ),
    );
  }

  // ─── MY TICKETS ─────────────────────────────────────────────
  Widget _buildMyTickets() {
    if (_loadingTickets) {
      return const Center(
          child: CircularProgressIndicator(color: AppColors.teal));
    }
    if (_myTickets.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.directions_bus_outlined,
                size: 64, color: AppColors.textMuted.withValues(alpha: 0.5)),
            const SizedBox(height: AppSpacing.md),
            Semantics(
              liveRegion: true,
              child: const Text('Bạn chưa có vé nào.',
                  style: TextStyle(color: AppColors.textMuted, fontSize: 16)),
            ),
          ],
        ),
      );
    }
    return ListView.builder(
      padding: const EdgeInsets.all(AppSpacing.lg),
      itemCount: _myTickets.length,
      itemBuilder: (_, i) => _buildTicketCard(_myTickets[i]),
    );
  }

  String _friendlySession(String sessionId) {
    switch (sessionId) {
      case 'MORNING_1':
        return '07:00 sáng';
      case 'MORNING_2':
        return '08:30 sáng';
      case 'NOON_1':
        return '10:00 trưa';
      case 'NOON_2':
        return '11:30 trưa';
      default:
        return sessionId;
    }
  }

  String _friendlyTrip(String tripType) =>
      tripType == 'pickup' ? 'Chiều đi' : 'Chiều về';

  /// Panel chi tiet tuyen, tai lazy qua FutureBuilder khi ve da assigned.
  /// Xu ly rieng truong hop BUG-VRPTW-01: route tra ve thanh cong nhung
  /// route_stops thieu (chi co depot) - khong coi la loi, chi bao "dang cap nhat".
  Widget _buildRouteDetailsPanel(String routeId) {
    return FutureBuilder<Map<String, dynamic>>(
      future: _routeFuture(routeId),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Padding(
            padding: EdgeInsets.symmetric(vertical: AppSpacing.lg),
            child: Center(
              child: SizedBox(
                  height: 20,
                  width: 20,
                  child: CircularProgressIndicator(
                      strokeWidth: 2, color: AppColors.teal)),
            ),
          );
        }

        if (snapshot.hasError) {
          return Padding(
            padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
            child: Column(
              children: [
                const Text('Không thể tải thông tin tuyến.',
                    style: TextStyle(color: Colors.red, fontSize: 13)),
                TextButton(
                  onPressed: () =>
                      setState(() => _routeDetailsCache.remove(routeId)),
                  child: const Text('Thử lại'),
                ),
              ],
            ),
          );
        }

        final route = snapshot.data;
        if (route == null) return const SizedBox.shrink();

        final sessionId = route['session_id']?.toString() ?? '';
        final tripType = route['trip_type']?.toString() ?? '';
        final vehicleId = route['vehicle_id']?.toString();
        final stops = (route['stops'] as List<dynamic>? ?? []);
        final passengerCount = route['passenger_count'] as int? ?? 0;
        // Ky vong: 1 depot + so hanh khach da assigned. Neu thieu -> BUG-VRPTW-01
        // (route_stops chua day du), hien thong bao thay vi coi la loi.
        final incomplete = stops.length < (passengerCount + 1);

        return Padding(
          padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.lg, vertical: AppSpacing.sm),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Thông tin tuyến',
                  style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                      color: AppColors.textPrimary)),
              const SizedBox(height: AppSpacing.xs),
              if (sessionId.isNotEmpty || tripType.isNotEmpty)
                Text(
                  '${_friendlyTrip(tripType)} • ${_friendlySession(sessionId)}',
                  style: const TextStyle(
                      fontSize: 13, color: AppColors.textSecondary),
                ),
              if (vehicleId != null)
                Padding(
                  padding: const EdgeInsets.only(top: 2),
                  child: Text(
                    'Xe: #${vehicleId.length > 8 ? vehicleId.substring(0, 8) : vehicleId}',
                    style: const TextStyle(
                        fontSize: 13, color: AppColors.textSecondary),
                  ),
                ),
              const SizedBox(height: AppSpacing.sm),
              if (incomplete)
                Container(
                  padding: const EdgeInsets.all(AppSpacing.sm),
                  decoration: BoxDecoration(
                    color: AppColors.orange.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(AppRadius.sm),
                  ),
                  child: const Text(
                    'Thông tin điểm dừng đang được hệ thống cập nhật. Vui lòng kiểm tra lại sau.',
                    style: TextStyle(fontSize: 12, color: AppColors.orange),
                  ),
                )
              else
                ...stops.map((s) {
                  final stop = s as Map<String, dynamic>;
                  final location = stop['location'] as Map<String, dynamic>?;
                  final name = location?['name']?.toString() ?? 'Điểm dừng';
                  final order = stop['stop_order']?.toString() ?? '';
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 2),
                    child: Row(
                      children: [
                        Container(
                          width: 18,
                          height: 18,
                          alignment: Alignment.center,
                          decoration: const BoxDecoration(
                              color: AppColors.tealBg, shape: BoxShape.circle),
                          child: Text(order,
                              style: const TextStyle(
                                  fontSize: 9,
                                  fontWeight: FontWeight.bold,
                                  color: AppColors.teal)),
                        ),
                        const SizedBox(width: AppSpacing.sm),
                        Expanded(
                            child: Text(name,
                                style: const TextStyle(
                                    fontSize: 13,
                                    color: AppColors.textPrimary))),
                      ],
                    ),
                  );
                }),
            ],
          ),
        );
      },
    );
  }

  Widget _buildTicketCard(_MyTicket t) {
    return MergeSemantics(
      child: Container(
      margin: const EdgeInsets.only(bottom: AppSpacing.lg),
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        boxShadow: [
          BoxShadow(
              color: AppColors.teal.withValues(alpha: 0.08),
              blurRadius: 15,
              offset: const Offset(0, 4)),
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        children: [
          Container(
            color: t.statusColor,
            padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.lg, vertical: AppSpacing.md),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    const Icon(Icons.directions_bus_rounded,
                        color: Colors.white, size: 24),
                    const SizedBox(width: AppSpacing.sm),
                    Text(
                      t.routeLabel,
                      style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w700,
                          color: Colors.white),
                    ),
                  ],
                ),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(AppRadius.full),
                  ),
                  child: Text(
                    t.statusLabel,
                    style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: Colors.white),
                  ),
                ),
              ],
            ),
          ),

          if (t.status == 'reserved') ...[
            const SizedBox(height: AppSpacing.xl),
            Icon(Icons.hourglass_top_rounded,
                size: 56, color: AppColors.orange.withValues(alpha: 0.7)),
            const SizedBox(height: AppSpacing.md),
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: AppSpacing.lg),
              child: Text(
                'Hệ thống sẽ phân tuyến trước giờ chạy.\nVui lòng kiểm tra lại sau.',
                textAlign: TextAlign.center,
                style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: AppColors.orange),
              ),
            ),
            const SizedBox(height: AppSpacing.lg),
            const Divider(height: 1, color: AppColors.border),
          ],

          // QR - chi hien khi da assigned (co tuyen that).
          if (t.status == 'assigned') ...[
            const SizedBox(height: AppSpacing.xl),
            Container(
              padding: const EdgeInsets.all(AppSpacing.sm),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(AppRadius.md),
                border: Border.all(
                    color: AppColors.teal.withValues(alpha: 0.2), width: 2),
              ),
              child: QrImageView(
                  data: t.qrData,
                  version: QrVersions.auto,
                  size: 200,
                  backgroundColor: Colors.white),
            ),
            const SizedBox(height: AppSpacing.md),
            const Text(
              'Đưa mã này vào máy quét trên xe',
              style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: AppColors.teal),
            ),
            const SizedBox(height: AppSpacing.lg),
            const Divider(height: 1, color: AppColors.border),
            _buildRouteDetailsPanel(t.routeId!),
            const Divider(height: 1, color: AppColors.border),
          ],

          if (t.status == 'used') ...[
            const SizedBox(height: AppSpacing.xl),
            Icon(Icons.check_circle_rounded,
                size: 56, color: Colors.grey.shade400),
            const SizedBox(height: AppSpacing.md),
            const Text('Vé đã được sử dụng cho chuyến đi này.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 13, color: AppColors.textSecondary)),
            const SizedBox(height: AppSpacing.lg),
            const Divider(height: 1, color: AppColors.border),
          ],

          if (t.status == 'cancelled') ...[
            const SizedBox(height: AppSpacing.xl),
            const Icon(Icons.cancel_rounded, size: 56, color: Colors.grey),
            const SizedBox(height: AppSpacing.md),
            const Text('Vé đã bị hủy.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 13, color: AppColors.textSecondary)),
            const SizedBox(height: AppSpacing.lg),
            const Divider(height: 1, color: AppColors.border),
          ],

          if (t.status == 'expired') ...[
            const SizedBox(height: AppSpacing.xl),
            const Icon(Icons.event_busy_rounded, size: 56, color: Colors.red),
            const SizedBox(height: AppSpacing.md),
            const Text('Vé đã hết hạn sử dụng.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 13, color: AppColors.textSecondary)),
            const SizedBox(height: AppSpacing.lg),
            const Divider(height: 1, color: AppColors.border),
          ],

          Padding(
            padding: const EdgeInsets.all(AppSpacing.lg),
            child: Row(
              children: [
                Expanded(child: _detailItem('Mã vé', t.id)),
                Expanded(child: _detailItem('Loại vé', t.type)),
                Expanded(
                    child: _detailItem('Ngày mua', t.purchasedDate,
                        isRight: true)),
              ],
            ),
          ),
        ],
      ),
    ));
  }

  Widget _detailItem(String label, String value,
      {Color? valueColor, bool isRight = false}) {
    return Column(
      crossAxisAlignment:
          isRight ? CrossAxisAlignment.end : CrossAxisAlignment.start,
      children: [
        Text(label,
            style: const TextStyle(
                fontSize: 12,
                color: AppColors.textMuted,
                fontWeight: FontWeight.w500)),
        const SizedBox(height: 4),
        Text(value,
            style: TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.bold,
                color: valueColor ?? AppColors.textPrimary)),
      ],
    );
  }

  // ─── BUY TICKET ─────────────────────────────────────────────
  Widget _buildBuyTicket() {
    if (_loadingRoutes) {
      return const Center(
          child: CircularProgressIndicator(color: AppColors.teal));
    }
    if (_routeError != null) {
      final is401 = _routeError!.contains('401');
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                  is401
                      ? Icons.lock_outline_rounded
                      : Icons.error_outline_rounded,
                  size: 54,
                  color: is401 ? AppColors.orange : Colors.red),
              const SizedBox(height: AppSpacing.md),
              Text(
                is401
                    ? 'Vui lòng đăng nhập tài khoản Sinh viên để mua vé và xem danh sách tuyến.'
                    : 'Lỗi tải dữ liệu: $_routeError',
                textAlign: TextAlign.center,
                style: const TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textPrimary),
              ),
              const SizedBox(height: AppSpacing.lg),
              ElevatedButton.icon(
                onPressed: () {
                  setState(() {
                    _loadingRoutes = true;
                    _routeError = null;
                  });
                  _loadRoutes();
                  _loadTickets();
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.teal,
                  foregroundColor: Colors.white,
                  padding:
                      const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(AppRadius.md)),
                ),
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('Thử tải lại',
                    style: TextStyle(fontWeight: FontWeight.bold)),
              ),
            ],
          ),
        ),
      );
    }

    if (_routes.isEmpty) {
      return const Center(
          child: Text('Không có tuyến đường khả dụng.',
              style: TextStyle(color: AppColors.textMuted)));
    }
    return Column(
      children: [
        Expanded(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(AppSpacing.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _sectionTitle('1. Chọn ngày chạy'),
                _buildDatePicker(),
                _buildDeadlineNotice(),
                const SizedBox(height: AppSpacing.md),
                _sectionTitle('2. Chọn ca chạy'),
                SegmentedButton<String>(
                  segments: const [
                    ButtonSegment(value: 'pickup', label: Text('Chiều đi')),
                    ButtonSegment(value: 'dropoff', label: Text('Chiều về')),
                  ],
                  selected: {_tripType},
                  onSelectionChanged: (value) => setState(() {
                    _tripType = value.first;
                    _sessionId = _tripType == 'pickup' ? 'MORNING_1' : 'NOON_1';
                  }),
                ),
                const SizedBox(height: AppSpacing.sm),
                SegmentedButton<String>(
                  segments: _tripType == 'pickup'
                      ? const [
                          ButtonSegment(
                              value: 'MORNING_1', label: Text('07:00')),
                          ButtonSegment(
                              value: 'MORNING_2', label: Text('08:30')),
                        ]
                      : const [
                          ButtonSegment(value: 'NOON_1', label: Text('10:00')),
                          ButtonSegment(value: 'NOON_2', label: Text('11:30')),
                        ],
                  selected: {_sessionId},
                  onSelectionChanged: (value) =>
                      setState(() => _sessionId = value.first),
                ),
                const SizedBox(height: AppSpacing.md),
                _sectionTitle('3. Chọn trạm đón / trả'),
                Text(
                  _tripType == 'pickup'
                      ? 'Điểm đến mặc định: Trường Đại học Cần Thơ'
                      : 'Điểm xuất phát mặc định: Trường Đại học Cần Thơ',
                  style:
                      const TextStyle(fontSize: 12, color: AppColors.textMuted),
                ),
                const SizedBox(height: AppSpacing.sm),
                if (_selectableRoutes.isEmpty)
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: AppSpacing.md),
                    child: Text('Chưa có trạm dừng khả dụng ngoài CTU.',
                        style: TextStyle(color: AppColors.textMuted)),
                  )
                else
                  ..._selectableRoutes.map((r) => _buildRouteOption(r)),
                if (_buyError != null) ...[
                  const SizedBox(height: AppSpacing.md),
                  Container(
                    padding: const EdgeInsets.all(AppSpacing.md),
                    decoration: BoxDecoration(
                      color: Colors.red.withValues(alpha: 0.08),
                      borderRadius: BorderRadius.circular(AppRadius.sm),
                      border:
                          Border.all(color: Colors.red.withValues(alpha: 0.3)),
                    ),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Icon(Icons.error_outline_rounded,
                            color: Colors.red, size: 20),
                        const SizedBox(width: AppSpacing.sm),
                        Expanded(
                            child: Semantics(
                              liveRegion: true,
                              child: Text(_buyError!,
                                  style: const TextStyle(
                                      color: Colors.red, fontSize: 13)),
                            )),
                      ],
                    ),
                  ),
                ],
                const SizedBox(height: 40),
              ],
            ),
          ),
        ),
        _buildCheckoutBottomBar(),
      ],
    );
  }

  Widget _buildDatePicker() {
    return SizedBox(
      height: 78,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: _dateOptions.length,
        separatorBuilder: (_, __) => const SizedBox(width: AppSpacing.sm),
        itemBuilder: (_, i) {
          final option = _dateOptions[i];
          final isActive = _isSameDate(option.date, _serviceDate);
          final disabled = !option.bookable;
          return GestureDetector(
            onTap: disabled
                ? null
                : () => setState(() {
                      _serviceDate = option.date;
                      _buyError = null;
                    }),
            child: Opacity(
              opacity: disabled ? 0.4 : 1,
              child: Container(
                width: 64,
                padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
                decoration: BoxDecoration(
                  color: isActive ? AppColors.teal : AppColors.white,
                  borderRadius: BorderRadius.circular(AppRadius.md),
                  border: Border.all(
                      color: isActive ? AppColors.teal : AppColors.border,
                      width: isActive ? 2 : 1),
                ),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(_weekdayLabel(option.date),
                        style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color: isActive
                                ? Colors.white
                                : AppColors.textSecondary)),
                    const SizedBox(height: 2),
                    Text(_formatDateShort(option.date),
                        style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.bold,
                            color: isActive
                                ? Colors.white
                                : AppColors.textPrimary)),
                    if (disabled) ...[
                      const SizedBox(height: 2),
                      const Text('Hết hạn',
                          style: TextStyle(fontSize: 9, color: Colors.red)),
                    ],
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildDeadlineNotice() {
    final match = _dateOptions.where((d) => _isSameDate(d.date, _serviceDate));
    final option = match.isEmpty ? null : match.first;
    if (option == null) return const SizedBox.shrink();

    final deadline = option.deadline;
    final deadlineStr =
        '${deadline.hour.toString().padLeft(2, '0')}:${deadline.minute.toString().padLeft(2, '0')} '
        '${deadline.day.toString().padLeft(2, '0')}/${deadline.month.toString().padLeft(2, '0')}';
    final selectedStr = _formatDateShort(_serviceDate);

    if (!option.bookable) {
      return Padding(
        padding: const EdgeInsets.only(top: AppSpacing.sm),
        child: Semantics(
          liveRegion: true,
          child: Text(
              'Chuyến ngày $selectedStr đã quá hạn đặt vé (hạn chót $deadlineStr).',
              style: const TextStyle(
                  color: Colors.red, fontSize: 13, fontWeight: FontWeight.w600)),
        ),
      );
    }

    final remaining = deadline.difference(_nowVN);
    final hours = remaining.inHours;
    final minutes = remaining.inMinutes.remainder(60);
    return Padding(
      padding: const EdgeInsets.only(top: AppSpacing.sm),
      child: Text(
          'Chuyến ngày $selectedStr: hạn đặt vé trước $deadlineStr (còn $hours giờ $minutes phút).',
          style: const TextStyle(color: AppColors.textSecondary, fontSize: 13)),
    );
  }

  Widget _buildCheckoutBottomBar() {
    final p = _price;
    final canBuy = _isSelectedDateBookable && !_isBuying;
    return Container(
      padding: const EdgeInsets.fromLTRB(
          AppSpacing.lg, AppSpacing.md, AppSpacing.lg, 30),
      decoration: BoxDecoration(
        color: AppColors.white,
        boxShadow: [
          BoxShadow(
              color: Colors.black.withValues(alpha: 0.05),
              blurRadius: 10,
              offset: const Offset(0, -4))
        ],
        borderRadius:
            const BorderRadius.vertical(top: Radius.circular(AppRadius.lg)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Tổng thanh toán',
                  style:
                      TextStyle(fontSize: 14, color: AppColors.textSecondary)),
              Text(_formatVND(p['total']!),
                  style: const TextStyle(
                      fontSize: 22,
                      fontWeight: FontWeight.w800,
                      color: AppColors.teal)),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          SizedBox(
            width: double.infinity,
            height: 54,
            child: ElevatedButton(
              onPressed: canBuy ? _handleBuyTicket : null,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.teal,
                foregroundColor: Colors.white,
                disabledBackgroundColor: AppColors.border,
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(AppRadius.md)),
                elevation: 0,
              ),
              child: _isBuying
                  ? const SizedBox(
                      height: 22,
                      width: 22,
                      child: CircularProgressIndicator(
                          color: Colors.white, strokeWidth: 2))
                  : Text(
                      _isSelectedDateBookable
                          ? 'Thanh toán ngay'
                          : 'Ngày đã hết hạn đặt',
                      style: const TextStyle(
                          fontSize: 16, fontWeight: FontWeight.bold)),
            ),
          ),
        ],
      ),
    );
  }

  Widget _sectionTitle(String text) => Padding(
        padding:
            const EdgeInsets.only(bottom: AppSpacing.md, top: AppSpacing.sm),
        child: Semantics(
          header: true,
          child: Text(text,
              style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: AppColors.textPrimary)),
        ),
      );

  Widget _buildRouteOption(_Route r) {
    final isActive = _selectedRoute == r.id;
    return GestureDetector(
      onTap: () => setState(() => _selectedRoute = r.id),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        margin: const EdgeInsets.only(bottom: AppSpacing.md),
        padding: const EdgeInsets.all(AppSpacing.md),
        decoration: BoxDecoration(
          color: isActive
              ? AppColors.teal.withValues(alpha: 0.05)
              : AppColors.white,
          borderRadius: BorderRadius.circular(AppRadius.md),
          border: Border.all(
              color: isActive ? AppColors.teal : AppColors.border,
              width: isActive ? 2.0 : 1.0),
        ),
        child: Row(
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                  color: r.color.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(12)),
              child: Center(child: Icon(Icons.directions_bus, color: r.color)),
            ),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(r.label,
                      style: TextStyle(
                          fontSize: 15,
                          fontWeight:
                              isActive ? FontWeight.bold : FontWeight.w600,
                          color: AppColors.textPrimary)),
                  const SizedBox(height: 2),
                  Text('Giá vé lượt: ${_formatVND(r.price)}',
                      style: const TextStyle(
                          fontSize: 13, color: AppColors.textSecondary)),
                ],
              ),
            ),
            Container(
              width: 24,
              height: 24,
              decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(
                      color: isActive ? AppColors.teal : AppColors.border,
                      width: 2)),
              child: isActive
                  ? Center(
                      child: Container(
                          width: 12,
                          height: 12,
                          decoration: const BoxDecoration(
                              color: AppColors.teal, shape: BoxShape.circle)))
                  : null,
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _handleBuyTicket() async {
    if (_selectedRoute == null) return;
    if (!_isSelectedDateBookable) {
      setState(() => _buyError =
          'Ngày chạy đã chọn đã quá hạn đặt vé (22:00 hôm trước). Vui lòng chọn ngày khác.');
      return;
    }

    setState(() {
      _isBuying = true;
      _buyError = null;
    });

    final route = _routes.firstWhere((r) => r.id == _selectedRoute);
    Map<String, dynamic> ticket;
    try {
      ticket = await widget.api.bookTicket(
        pickupLocationId: _selectedRoute!, // UUID string, khong parse int nua
        serviceDate: _serviceDate,
        sessionId: _sessionId,
        tripType: _tripType,
      );
      await _loadTickets();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isBuying = false;
        _buyError = _friendlyBuyError(e);
      });
      return;
    }

    if (!mounted) return;
    setState(() => _isBuying = false);

    showModalBottomSheet(
      context: context,
      backgroundColor: AppColors.white,
      shape: const RoundedRectangleBorder(
          borderRadius:
              BorderRadius.vertical(top: Radius.circular(AppRadius.full))),
      builder: (ctx) => Padding(
        padding: const EdgeInsets.fromLTRB(
            AppSpacing.lg, AppSpacing.lg, AppSpacing.lg, 40),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 48,
              height: 5,
              margin: const EdgeInsets.only(bottom: AppSpacing.xl),
              decoration: BoxDecoration(
                  color: Colors.grey.shade300,
                  borderRadius: BorderRadius.circular(AppRadius.full)),
            ),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                  color: Colors.green.withValues(alpha: 0.1),
                  shape: BoxShape.circle),
              child: const Icon(Icons.check_circle_rounded,
                  color: Colors.green, size: 64),
            ),
            const SizedBox(height: AppSpacing.md),
            const Text('Thanh toán thành công!',
                style: TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.bold,
                    color: AppColors.textPrimary)),
            const SizedBox(height: AppSpacing.sm),
            const Text('Vé của bạn đã được lưu vào hệ thống.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 14, color: AppColors.textSecondary)),
            const SizedBox(height: AppSpacing.xl),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(AppSpacing.lg),
              decoration: BoxDecoration(
                  color: AppColors.bg,
                  borderRadius: BorderRadius.circular(AppRadius.md)),
              child: Column(
                children: [
                  Text('#BUS${ticket['id']}',
                      style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                          color: AppColors.textPrimary)),
                  const SizedBox(height: 4),
                  Text(route.label,
                      style: const TextStyle(
                          fontSize: 14, color: AppColors.textSecondary)),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.md),
            SizedBox(
              width: double.infinity,
              height: 44,
              child: ElevatedButton(
                onPressed: () {
                  Navigator.pop(ctx);
                  _tabController.animateTo(0);
                },
                style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.teal,
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(AppRadius.md))),
                child: const Text('Xem vé của tôi',
                    style: TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.bold,
                        color: Colors.white)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _friendlyBuyError(Object error) {
    final msg = error.toString();
    if (msg.contains('401'))
      return 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.';
    if (msg.contains('409') || msg.toLowerCase().contains('trùng')) {
      return 'Bạn đã đặt vé cho ca này rồi. Vui lòng kiểm tra ở tab "Vé của tôi".';
    }
    if (msg.toLowerCase().contains('22:00') ||
        msg.toLowerCase().contains('deadline')) {
      return 'Đã quá hạn đặt vé cho ngày này (22:00 hôm trước).';
    }
    if (msg.contains('SocketException') || msg.contains('TimeoutException')) {
      return 'Không thể kết nối máy chủ. Vui lòng kiểm tra mạng và thử lại.';
    }
    return msg.replaceFirst('Exception: ', '');
  }
}

class _Route {
  final String id, label; // id la UUID string
  final int price;
  final Color color;
  const _Route(this.id, this.label, this.price, this.color);
}

/// Ve theo dung 5 trang thai that tu backend TicketStatus (Ngay 4):
/// reserved | assigned | used | cancelled | expired.
class _MyTicket {
  final String id, type, purchasedDate, qrData;
  final String status;
  final String? routeId; // UUID string, null khi con reserved

  const _MyTicket({
    required this.id,
    required this.type,
    required this.purchasedDate,
    required this.status,
    required this.routeId,
    required this.qrData,
  });

  String get statusLabel {
    switch (status) {
      case 'reserved':
        return 'Đang chờ phân tuyến';
      case 'assigned':
        return 'Sẵn sàng';
      case 'used':
        return 'Đã sử dụng';
      case 'cancelled':
        return 'Đã hủy';
      case 'expired':
        return 'Hết hạn';
      default:
        return status;
    }
  }

  Color get statusColor {
    switch (status) {
      case 'reserved':
        return AppColors.orange;
      case 'assigned':
        return AppColors.teal;
      case 'used':
        return Colors.grey.shade600;
      case 'cancelled':
        return Colors.grey;
      case 'expired':
        return Colors.red.shade300;
      default:
        return Colors.grey;
    }
  }

  String get routeLabel {
    if (routeId == null) return 'Chưa có tuyến';
    // TODO Ngay 5 (TV4): thay bang ten tuyen that qua ApiService.fetchRouteDetails(routeId)
    // thay vi chi hien ID rut gon, dung yeu cau "Hien thong tin tuyen sau assigned".
    final shortId = routeId!.length > 8 ? routeId!.substring(0, 8) : routeId!;
    return 'Tuyến #$shortId';
  }
}

/// Một lựa chọn ngày chạy trong bộ chọn ngày, kèm hạn chót đặt vé (22:00
/// giờ Việt Nam của ngày liền trước) và trạng thái còn đặt được hay không.
class _ServiceDateOption {
  final DateTime date;
  final DateTime deadline;
  final bool bookable;
  const _ServiceDateOption(this.date, this.deadline, this.bookable);
}
