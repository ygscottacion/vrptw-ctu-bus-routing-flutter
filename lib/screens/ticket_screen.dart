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
  String? _selectedRoute;
  String _selectedType = 'single';
  String _sessionId = 'MORNING_1';
  String _tripType = 'pickup';
  late DateTime _serviceDate;

  List<_Route> _routes = [];
  bool _loadingRoutes = true;
  String? _routeError;

  // Vé lượt: mỗi vé tương ứng một chiều của một ca chạy.
  static const _types = [
    _TicketType('single', '1 vé lượt', 1, null),
  ];

  List<_MyTicket> _myTickets = [];
  bool _loadingTickets = true;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    final now = DateTime.now();
    _serviceDate =
        DateTime(now.year, now.month, now.day).add(const Duration(days: 1));
    _loadRoutes();
    _loadTickets();
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
        final id = r['id'].toString();
        final label = r['name']?.toString() ?? 'Trạm $id';
        loadedRoutes.add(_Route(id, label, 7000, colors[i % colors.length]));
      }

      setState(() {
        _routes = loadedRoutes;
        _routeError = null;
        if (_routes.isNotEmpty) {
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

  Future<void> _loadTickets() async {
    try {
      final items = await widget.api.fetchMyTickets();
      if (!mounted) return;
      setState(
        () => _myTickets = items.map((item) {
          final ticket = item as Map<String, dynamic>;
          final status = ticket['status']?.toString() ?? 'reserved';
          final isValid = status == 'reserved' || status == 'assigned';
          
          String routeLabel = 'Chưa phân tuyến';
          Color cardColor = AppColors.teal;
          
          if (status == 'reserved') {
            routeLabel = 'Đang chờ phân tuyến';
            cardColor = AppColors.orange;
          } else if (status == 'assigned') {
            final routeId = ticket['route_id']?.toString() ?? '';
            final shortId = routeId.length > 5 ? routeId.substring(0, 5).toUpperCase() : routeId;
            routeLabel = 'Tuyến CT-$shortId';
            cardColor = AppColors.teal;
          } else if (status == 'used') {
            routeLabel = 'Đã đi chuyến';
            cardColor = Colors.grey.shade600;
          } else if (status == 'cancelled') {
            routeLabel = 'Đã hủy vé';
            cardColor = Colors.red.shade600;
          } else {
            routeLabel = 'Hết hạn';
            cardColor = Colors.grey.shade600;
          }
          
          final ticketIdStr = ticket['id']?.toString() ?? '';
          final shortTicketId = ticketIdStr.length > 5 
              ? ticketIdStr.substring(0, 5).toUpperCase() 
              : ticketIdStr;

          return _MyTicket(
            'BUS-$shortTicketId',
            routeLabel,
            'Vé lượt',
            ticket['service_date']?.toString() ?? '—',
            status == 'used' ? 0 : 1,
            isValid,
            cardColor,
            ticket['qr_code']?.toString() ?? '',
            status,
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

  double _discountRateFor(String typeId) => 0.0;

  Map<String, int> get _price {
    if (_routes.isEmpty || _selectedRoute == null) {
      return {'original': 0, 'discount': 0, 'total': 0};
    }
    final route = _routes.firstWhere((r) => r.id == _selectedRoute);
    final type = _types.firstWhere((t) => t.id == _selectedType);
    final base = type.flatPrice ?? (route.price * type.multiplier).round();
    final rate = _discountRateFor(type.id);
    final discount = (base * rate).round();
    final total = base - discount;
    return {'original': base, 'discount': discount, 'total': total};
  }

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
          labelStyle: const TextStyle(
            fontWeight: FontWeight.bold,
            fontSize: 15,
          ),
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

  // ─── MY TICKETS (Tối ưu UI cho việc quét QR nhanh) ─────────
  Widget _buildMyTickets() {
    if (_loadingTickets)
      return const Center(
        child: CircularProgressIndicator(color: AppColors.teal),
      );
    if (_myTickets.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.directions_bus_outlined,
              size: 64,
              color: AppColors.textMuted.withValues(alpha: 0.5),
            ),
            const SizedBox(height: AppSpacing.md),
            const Text(
              'Bạn chưa có vé nào.',
              style: TextStyle(color: AppColors.textMuted, fontSize: 16),
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

  Widget _buildTicketCard(_MyTicket t) {
    return Container(
      margin: const EdgeInsets.only(bottom: AppSpacing.lg),
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        boxShadow: [
          BoxShadow(
            color: AppColors.teal.withValues(alpha: 0.08),
            blurRadius: 15,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        children: [
          // Header tuyến xe
          Container(
            color: t.color,
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.lg,
              vertical: AppSpacing.md,
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    const Icon(
                      Icons.directions_bus_rounded,
                      color: Colors.white,
                      size: 24,
                    ),
                    const SizedBox(width: AppSpacing.sm),
                    Text(
                      t.route,
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                        color: Colors.white,
                      ),
                    ),
                  ],
                ),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(AppRadius.full),
                  ),
                  child: Text(
                    t.status == 'assigned' 
                        ? 'Sẵn sàng' 
                        : t.status == 'reserved' 
                            ? 'Chờ xếp xe' 
                            : t.status == 'used' 
                                ? 'Đã đi' 
                                : t.status == 'cancelled' 
                                    ? 'Đã hủy' 
                                    : 'Hết hạn',
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      color: Colors.white,
                    ),
                  ),
                ),
              ],
            ),
          ),

          // Khu vực trung tâm: Hiển thị tuỳ theo trạng thái vé
          if (t.status == 'assigned') ...[
            const SizedBox(height: AppSpacing.xl),
            Container(
              padding: const EdgeInsets.all(AppSpacing.sm),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(AppRadius.md),
                border: Border.all(
                  color: AppColors.teal.withValues(alpha: 0.2),
                  width: 2,
                ),
              ),
              child: QrImageView(
                data: t.qrData,
                version: QrVersions.auto,
                size: 200,
                backgroundColor: Colors.white,
              ),
            ),
            const SizedBox(height: AppSpacing.md),
            const Text(
              'Đưa mã này vào máy quét trên xe',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: AppColors.teal,
              ),
            ),
            const SizedBox(height: AppSpacing.lg),
            const Divider(height: 1, color: AppColors.border),
          ] else if (t.status == 'reserved') ...[
            const SizedBox(height: AppSpacing.xl),
            Container(
              padding: const EdgeInsets.all(20),
              margin: const EdgeInsets.symmetric(horizontal: 24),
              decoration: BoxDecoration(
                color: AppColors.orange.withOpacity(0.06),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: AppColors.orange.withOpacity(0.2),
                  width: 1.5,
                ),
              ),
              child: Column(
                children: [
                  const Icon(
                    Icons.hourglass_empty_rounded,
                    color: AppColors.orange,
                    size: 48,
                  ),
                  const SizedBox(height: 12),
                  const Text(
                    'Đang tính toán tối ưu lộ trình',
                    style: TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.bold,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Hệ thống sẽ tự động gán xe và giờ đón chi tiết sau mốc 22:00 của ngày trước ngày chạy.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 13,
                      color: Colors.grey.shade700,
                      height: 1.4,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.xl),
            const Divider(height: 1, color: AppColors.border),
          ] else if (t.status == 'used') ...[
            const SizedBox(height: AppSpacing.xl),
            const Icon(
              Icons.check_circle_rounded,
              color: Colors.green,
              size: 54,
            ),
            const SizedBox(height: 10),
            const Text(
              'Đã điểm danh lên xe',
              style: TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.bold,
                color: Colors.green,
              ),
            ),
            const SizedBox(height: AppSpacing.lg),
            const Divider(height: 1, color: AppColors.border),
          ],

          // Thông tin phụ
          Padding(
            padding: const EdgeInsets.all(AppSpacing.lg),
            child: Row(
              children: [
                Expanded(child: _detailItem('Mã vé', t.id)),
                Expanded(child: _detailItem('Loại vé', t.type)),
                Expanded(
                  child: _detailItem(
                    'Lượt còn lại',
                    '${t.trips}',
                    valueColor: t.trips > 0 ? AppColors.teal : Colors.red,
                    isRight: true,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _detailItem(
    String label,
    String value, {
    Color? valueColor,
    bool isRight = false,
  }) {
    return Column(
      crossAxisAlignment:
          isRight ? CrossAxisAlignment.end : CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(
            fontSize: 12,
            color: AppColors.textMuted,
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          value,
          style: TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.bold,
            color: valueColor ?? AppColors.textPrimary,
          ),
        ),
      ],
    );
  }

  // ─── BUY TICKET (Tối ưu UI dạng Form & Checkout Botom Bar) ───
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
                color: is401 ? AppColors.orange : Colors.red,
              ),
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
        // Phần thân form cuộn được
        Expanded(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(AppSpacing.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _sectionTitle('1. Chọn trạm đón / trả'),
                ..._routes.map((r) => _buildRouteOption(r)),
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
                              value: 'MORNING_2', label: Text('08:30'))
                        ]
                      : const [
                          ButtonSegment(value: 'NOON_1', label: Text('10:00')),
                          ButtonSegment(value: 'NOON_2', label: Text('11:30'))
                        ],
                  selected: {_sessionId},
                  onSelectionChanged: (value) =>
                      setState(() => _sessionId = value.first),
                ),
                const SizedBox(height: AppSpacing.md),
                _sectionTitle('3. Vé lượt'),
                _buildTypeBtn(_types.first),
                const SizedBox(height: AppSpacing.sm),
                const Text(
                    'Đặt trước 22:00 ngày hôm trước để hệ thống tối ưu tuyến.',
                    style: TextStyle(
                        color: AppColors.textSecondary, fontSize: 13)),
                const SizedBox(height: 40), // Spacing padding
              ],
            ),
          ),
        ),
        // Phần thanh toán cố định ở đáy
        _buildCheckoutBottomBar(),
      ],
    );
  }

  Widget _buildCheckoutBottomBar() {
    final p = _price;
    return Container(
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.lg,
        AppSpacing.md,
        AppSpacing.lg,
        30,
      ), // Padding cho SafeArea
      decoration: BoxDecoration(
        color: AppColors.white,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 10,
            offset: const Offset(0, -4),
          ),
        ],
        borderRadius: const BorderRadius.vertical(
          top: Radius.circular(AppRadius.lg),
        ),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Tổng thanh toán',
                style: TextStyle(fontSize: 14, color: AppColors.textSecondary),
              ),
              Text(
                _formatVND(p['total']!),
                style: const TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w800,
                  color: AppColors.teal,
                ),
              ),
            ],
          ),
          if (p['discount']! > 0)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'Đã áp dụng ưu đãi',
                    style: TextStyle(fontSize: 12, color: Colors.green),
                  ),
                  Text(
                    '-${_formatVND(p['discount']!)}',
                    style: const TextStyle(fontSize: 12, color: Colors.green),
                  ),
                ],
              ),
            ),
          const SizedBox(height: AppSpacing.md),
          SizedBox(
            width: double.infinity,
            height: 54, // Nút to, dễ bấm
            child: ElevatedButton(
              onPressed: _handleBuyTicket,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.teal,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(AppRadius.md),
                ),
                elevation: 0,
              ),
              child: const Text(
                'Thanh toán ngay',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _sectionTitle(String text) => Padding(
        padding:
            const EdgeInsets.only(bottom: AppSpacing.md, top: AppSpacing.sm),
        child: Text(
          text,
          style: const TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.bold,
            color: AppColors.textPrimary,
          ),
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
            width: isActive ? 2.0 : 1.0,
          ),
        ),
        child: Row(
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: r.color.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Center(child: Icon(Icons.directions_bus, color: r.color)),
            ),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    r.label,
                    style: TextStyle(
                      fontSize: 15,
                      fontWeight: isActive ? FontWeight.bold : FontWeight.w600,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    'Giá vé lượt: ${_formatVND(r.price)}',
                    style: const TextStyle(
                      fontSize: 13,
                      color: AppColors.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
            // Nút Radio giả
            Container(
              width: 24,
              height: 24,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(
                  color: isActive ? AppColors.teal : AppColors.border,
                  width: 2,
                ),
              ),
              child: isActive
                  ? Center(
                      child: Container(
                        width: 12,
                        height: 12,
                        decoration: const BoxDecoration(
                          color: AppColors.teal,
                          shape: BoxShape.circle,
                        ),
                      ),
                    )
                  : null,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTypeBtn(_TicketType t) {
    final isActive = _selectedType == t.id;
    final route = _routes.firstWhere((r) => r.id == _selectedRoute);
    final basePrice = t.flatPrice ?? route.price * t.multiplier;
    final rate = _discountRateFor(t.id);
    final finalPrice = basePrice - (basePrice * rate);
    return GestureDetector(
      onTap: () => setState(() => _selectedType = t.id),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        margin: const EdgeInsets.only(
          right: AppSpacing.sm,
          bottom: AppSpacing.sm,
        ),
        padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
        decoration: BoxDecoration(
          color: isActive ? AppColors.teal : AppColors.white,
          borderRadius: BorderRadius.circular(AppRadius.md),
          border: Border.all(
            color: isActive ? AppColors.teal : AppColors.border,
          ),
          boxShadow: isActive
              ? [
                  BoxShadow(
                    color: AppColors.teal.withValues(alpha: 0.2),
                    blurRadius: 8,
                    offset: const Offset(0, 3),
                  ),
                ]
              : null,
        ),
        child: Column(
          children: [
            Text(
              t.label,
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.bold,
                color: isActive ? Colors.white : AppColors.textPrimary,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              _formatVND(finalPrice.round()),
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w500,
                color: isActive
                    ? Colors.white.withValues(alpha: 0.9)
                    : AppColors.teal,
              ),
            ),
            if (rate > 0)
              Text(
                '-${(rate * 100).round()}%',
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                  color: isActive
                      ? Colors.white.withValues(alpha: 0.85)
                      : Colors.green,
                ),
              ),
          ],
        ),
      ),
    );
  }

  Future<void> _handleBuyTicket() async {
    if (_selectedRoute == null) return;
    final route = _routes.firstWhere((r) => r.id == _selectedRoute);
    final routeLabel = route.label.split(': ').last;
    Map<String, dynamic> ticket;
    try {
      ticket = await widget.api.bookTicket(
        pickupLocationId: _selectedRoute!,
        serviceDate: _serviceDate,
        sessionId: _sessionId,
        tripType: _tripType,
      );
      await _loadTickets();
    } catch (e) {
      if (mounted)
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Không thể mua vé: $e')));
      return;
    }
    if (!mounted) return;
    showModalBottomSheet(
      context: context,
      backgroundColor: AppColors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(
          top: Radius.circular(AppRadius.full),
        ),
      ),
      builder: (ctx) => Padding(
        padding: const EdgeInsets.fromLTRB(
          AppSpacing.lg,
          AppSpacing.lg,
          AppSpacing.lg,
          40,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 48,
              height: 5,
              margin: const EdgeInsets.only(bottom: AppSpacing.xl),
              decoration: BoxDecoration(
                color: Colors.grey.shade300,
                borderRadius: BorderRadius.circular(AppRadius.full),
              ),
            ),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.green.withValues(alpha: 0.1),
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.check_circle_rounded,
                color: Colors.green,
                size: 64,
              ),
            ),
            const SizedBox(height: AppSpacing.md),
            const Text(
              'Thanh toán thành công!',
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.bold,
                color: AppColors.textPrimary,
              ),
            ),
            const SizedBox(height: AppSpacing.sm),
            const Text(
              'Vé của bạn đã được lưu vào hệ thống.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 14, color: AppColors.textSecondary),
            ),
            const SizedBox(height: AppSpacing.xl),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(AppSpacing.lg),
              decoration: BoxDecoration(
                color: AppColors.bg,
                borderRadius: BorderRadius.circular(AppRadius.md),
              ),
              child: Column(
                children: [
                  Text(
                    '#BUS${ticket['id']}',
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    routeLabel,
                    style: const TextStyle(
                      fontSize: 14,
                      color: AppColors.textSecondary,
                    ),
                  ),
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
                    borderRadius: BorderRadius.circular(AppRadius.md),
                  ),
                ),
                child: const Text(
                  'Mở mã QR ngay',
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Route {
  final String id, label;
  final int price;
  final Color color;
  const _Route(this.id, this.label, this.price, this.color);
}

class _TicketType {
  final String id, label;
  final int multiplier;
  final int? flatPrice;
  const _TicketType(this.id, this.label, this.multiplier, this.flatPrice);
}

class _MyTicket {
  final String id, route, type, expiry, qrData, status;
  final int trips;
  final bool isValid;
  final Color color;
  const _MyTicket(
    this.id,
    this.route,
    this.type,
    this.expiry,
    this.trips,
    this.isValid,
    this.color,
    this.qrData,
    this.status,
  );
}
