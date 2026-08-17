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
  String _selectedRoute = '1';
  String _selectedType = '20';

  static const _routes = [
    _Route('1', 'Tuyến 1: CTU → Vincom Xuân Khánh', 7000, AppColors.teal),
    _Route('2', 'Tuyến 2: CTU → Bến xe Cần Thơ', 9000, AppColors.purple),
    _Route('3', 'Tuyến 3: CTU → Ninh Kiều', 8000, AppColors.orange),
  ];

  static const _types = [
    _TicketType('20', '20 lượt', 20, null),
    _TicketType('40', '40 lượt', 40, null),
    _TicketType('month', 'Vé tháng', 0, 150000),
  ];

  List<_MyTicket> _myTickets = [];
  bool _loadingTickets = true;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _loadTickets();
  }

  Future<void> _loadTickets() async {
    try {
      final items = await widget.api.fetchMyTickets();
      if (!mounted) return;
      setState(() => _myTickets = items.map((item) {
        final ticket = item as Map<String, dynamic>;
        final active = ticket['status'] == 'active';
        return _MyTicket(
          'BUS${ticket['id']}', 'Tuyến #${ticket['route_id'] ?? 'Chưa chọn'}',
          'Vé điện tử', ticket['created_at']?.toString().split('T').first ?? '—',
          active ? 1 : 0, active, active ? AppColors.teal : AppColors.purple,
          ticket['qr_code']?.toString() ?? '',
        );
      }).toList());
    } catch (_) {
      // Người dùng chưa đăng nhập hoặc backend chưa sẵn sàng: giữ danh sách trống.
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

  Map<String, int> get _price {
    final route = _routes.firstWhere((r) => r.id == _selectedRoute);
    final type = _types.firstWhere((t) => t.id == _selectedType);
    final original =
        type.flatPrice ?? (route.price * type.multiplier).round();
    final discount = (original * 0.1).round();
    return {'original': (original / 0.9).round(), 'discount': discount, 'total': original};
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Vé xe'),
        bottom: TabBar(
          controller: _tabController,
          labelColor: AppColors.teal,
          unselectedLabelColor: AppColors.textMuted,
          indicatorColor: AppColors.teal,
          indicatorWeight: 2.5,
          tabs: const [
            Tab(text: 'Vé của tôi'),
            Tab(text: 'Mua vé'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildMyTickets(),
          _buildBuyTicket(),
        ],
      ),
    );
  }

  // ─── MY TICKETS ───────────────────────────────────────────
  Widget _buildMyTickets() {
    if (_loadingTickets) return const Center(child: CircularProgressIndicator());
    if (_myTickets.isEmpty) return const Center(child: Text('Bạn chưa có vé nào.'));
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
        borderRadius: BorderRadius.circular(AppRadius.md),
        boxShadow: [
          BoxShadow(
              color: Colors.black.withValues(alpha: 0.06),
              blurRadius: 8,
              offset: const Offset(0, 2))
        ],
      ),
      clipBehavior: Clip.hardEdge,
      child: Column(
        children: [
          // Ticket header
          Container(
            color: t.color,
            padding: const EdgeInsets.all(AppSpacing.md),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Tuyến xe buýt',
                        style: TextStyle(
                            fontSize: 11,
                            color: Colors.white70,
                            fontWeight: FontWeight.w500)),
                    Text(t.route,
                        style: const TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w700,
                            color: Colors.white)),
                  ],
                ),
                Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: AppSpacing.sm, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: t.isValid ? 0.2 : 0.15),
                    borderRadius: BorderRadius.circular(AppRadius.full),
                  ),
                  child: Text(
                    t.isValid ? 'Còn hiệu lực' : 'Hết hạn',
                    style: const TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        color: Colors.white),
                  ),
                ),
              ],
            ),
          ),
          // Ticket body
          Padding(
            padding: const EdgeInsets.all(AppSpacing.md),
            child: Column(
              children: [
                Row(children: [
                  Expanded(child: _detailItem('Mã vé', '#${t.id}')),
                  Expanded(child: _detailItem('Loại vé', t.type)),
                ]),
                const SizedBox(height: AppSpacing.sm),
                Row(children: [
                  Expanded(child: _detailItem('Ngày hết hạn', t.expiry)),
                  Expanded(
                    child: _detailItem('Lượt còn lại', '${t.trips} lượt',
                        valueColor: t.trips > 0 ? AppColors.teal : AppColors.red),
                  ),
                ]),
                if (t.isValid) ...[
                  const SizedBox(height: AppSpacing.md),
                  Container(
                    padding: const EdgeInsets.all(AppSpacing.sm),
                    decoration: BoxDecoration(
                      border: Border.all(color: AppColors.border),
                      borderRadius: BorderRadius.circular(AppRadius.sm),
                    ),
                    child: QrImageView(
                      data: t.qrData,
                      version: QrVersions.auto,
                      size: 110,
                      backgroundColor: Colors.white,
                    ),
                  ),
                  const SizedBox(height: 6),
                  const Text('Quét mã để sử dụng vé',
                      style: TextStyle(
                          fontSize: 11, color: AppColors.textMuted)),
                ],
              ],
            ),
          ),
          // Tear line
          Stack(
            children: [
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: Row(
                  children: List.generate(
                      30,
                      (idx) => Expanded(
                            child: Container(
                                height: 1.5,
                                color: idx % 2 == 0
                                    ? AppColors.border
                                    : Colors.transparent),
                          )),
                ),
              ),
              Positioned(
                left: 0,
                child: Container(
                    width: 20,
                    height: 20,
                    decoration: const BoxDecoration(
                        color: AppColors.bg, shape: BoxShape.circle)),
              ),
              Positioned(
                right: 0,
                child: Container(
                    width: 20,
                    height: 20,
                    decoration: const BoxDecoration(
                        color: AppColors.bg, shape: BoxShape.circle)),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _detailItem(String label, String value, {Color? valueColor}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label,
            style: const TextStyle(
                fontSize: 11,
                color: AppColors.textMuted,
                fontWeight: FontWeight.w500)),
        const SizedBox(height: 2),
        Text(value,
            style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w700,
                color: valueColor ?? AppColors.textPrimary)),
      ],
    );
  }

  // ─── BUY TICKET ───────────────────────────────────────────
  Widget _buildBuyTicket() {
    final p = _price;
    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _sectionTitle('Chọn tuyến xe'),
          ..._routes.map((r) => _buildRouteOption(r)),
          _sectionTitle('Chọn loại vé'),
          Row(
            children: _types
                .map((t) => Expanded(child: _buildTypeBtn(t)))
                .toList(),
          ),
          const SizedBox(height: AppSpacing.lg),
          // Payment summary
          Container(
            decoration: BoxDecoration(
              color: AppColors.white,
              borderRadius: BorderRadius.circular(AppRadius.sm),
              boxShadow: [
                BoxShadow(
                    color: Colors.black.withValues(alpha: 0.06), blurRadius: 8)
              ],
            ),
            padding: const EdgeInsets.all(AppSpacing.md),
            child: Column(
              children: [
                _summaryRow('Giá vé gốc', _formatVND(p['original']!)),
                const SizedBox(height: AppSpacing.sm),
                _summaryRow('Giảm giá sinh viên (10%)',
                    '-${_formatVND(p['discount']!)}',
                    valueColor: AppColors.green),
                const Divider(height: AppSpacing.xl, color: AppColors.border),
                _summaryRow('Tổng cộng', _formatVND(p['total']!),
                    isBold: true, valueColor: AppColors.teal),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.lg),
          // Buy button
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _handleBuyTicket,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.teal,
                foregroundColor: Colors.white,
                padding:
                    const EdgeInsets.symmetric(vertical: AppSpacing.md),
                shape: RoundedRectangleBorder(
                    borderRadius:
                        BorderRadius.circular(AppRadius.md)),
                elevation: 4,
              ),
              icon: const Text('✅', style: TextStyle(fontSize: 18)),
              label: const Text('Mua vé ngay',
                  style: TextStyle(
                      fontSize: 15, fontWeight: FontWeight.w700)),
            ),
          ),
        ],
      ),
    );
  }

  Widget _sectionTitle(String text) => Padding(
        padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
        child: Text(text,
            style: const TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w700,
                color: AppColors.textPrimary)),
      );

  Widget _buildRouteOption(_Route r) {
    final isActive = _selectedRoute == r.id;
    return GestureDetector(
      onTap: () => setState(() => _selectedRoute = r.id),
      child: Container(
        margin: const EdgeInsets.only(bottom: AppSpacing.sm),
        padding: const EdgeInsets.all(AppSpacing.md),
        decoration: BoxDecoration(
          color: isActive ? const Color(0xFFF0FDFC) : AppColors.white,
          borderRadius: BorderRadius.circular(AppRadius.sm),
          border: Border.all(
              color: isActive ? AppColors.teal : AppColors.border,
              width: 1.5),
          boxShadow: [
            BoxShadow(
                color: Colors.black.withValues(alpha: 0.04), blurRadius: 6)
          ],
        ),
        child: Row(
          children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                  color: r.color,
                  borderRadius: BorderRadius.circular(10)),
              child: const Center(
                  child: Text('🚌', style: TextStyle(fontSize: 16))),
            ),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(r.label,
                      style: const TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: AppColors.textPrimary)),
                  Text('Giá: ${_formatVND(r.price)}/lượt',
                      style: const TextStyle(
                          fontSize: 12, color: AppColors.textSecondary)),
                ],
              ),
            ),
            Container(
              width: 20,
              height: 20,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(
                    color: isActive ? AppColors.teal : AppColors.border,
                    width: 2),
              ),
              child: isActive
                  ? Center(
                      child: Container(
                          width: 10,
                          height: 10,
                          decoration: const BoxDecoration(
                              color: AppColors.teal,
                              shape: BoxShape.circle)))
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
    final price = t.flatPrice ?? route.price * t.multiplier;
    return GestureDetector(
      onTap: () => setState(() => _selectedType = t.id),
      child: Container(
        margin: const EdgeInsets.only(right: AppSpacing.sm),
        padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.sm, vertical: AppSpacing.sm),
        decoration: BoxDecoration(
          color: isActive ? AppColors.teal : AppColors.white,
          borderRadius: BorderRadius.circular(AppRadius.sm),
          border: Border.all(
              color: isActive ? AppColors.teal : AppColors.border,
              width: 1.5),
        ),
        child: Column(
          children: [
            Text(t.label,
                style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: isActive ? Colors.white : AppColors.textPrimary)),
            Text(_formatVND(price.round()),
                style: TextStyle(
                    fontSize: 11,
                    color: isActive ? Colors.white70 : AppColors.textSecondary)),
          ],
        ),
      ),
    );
  }

  Widget _summaryRow(String label, String value,
      {bool isBold = false, Color? valueColor}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label,
            style: TextStyle(
                fontSize: isBold ? 15 : 13,
                color: AppColors.textSecondary,
                fontWeight:
                    isBold ? FontWeight.w700 : FontWeight.w400)),
        Text(value,
            style: TextStyle(
                fontSize: isBold ? 15 : 13,
                fontWeight:
                    isBold ? FontWeight.w700 : FontWeight.w600,
                color: valueColor ?? AppColors.textPrimary)),
      ],
    );
  }

  Future<void> _handleBuyTicket() async {
    final route = _routes.firstWhere((r) => r.id == _selectedRoute);
    final routeLabel = route.label.split(': ').last;
    Map<String, dynamic> ticket;
    try {
      ticket = await widget.api.bookTicket(int.parse(_selectedRoute));
      await _loadTickets();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Không thể mua vé: $e')));
      return;
    }
    if (!mounted) return;
    showModalBottomSheet(
      context: context,
      backgroundColor: AppColors.white,
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(
              top: Radius.circular(AppRadius.lg))),
      builder: (ctx) => Padding(
        padding: const EdgeInsets.fromLTRB(
            AppSpacing.lg, AppSpacing.lg, AppSpacing.lg, 40),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
                width: 40,
                height: 4,
                margin: const EdgeInsets.only(bottom: AppSpacing.lg),
                decoration: BoxDecoration(
                    color: AppColors.border,
                    borderRadius:
                        BorderRadius.circular(AppRadius.full))),
            const Text('✅', style: TextStyle(fontSize: 56)),
            const SizedBox(height: AppSpacing.sm),
            const Text('Mua vé thành công!',
                style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                    color: AppColors.textPrimary)),
            const SizedBox(height: AppSpacing.sm),
            const Text(
                'Vé của bạn đã được kích hoạt và có thể sử dụng ngay.',
                textAlign: TextAlign.center,
                style: TextStyle(
                    fontSize: 13, color: AppColors.textSecondary)),
            const SizedBox(height: AppSpacing.md),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(AppSpacing.lg),
              decoration: BoxDecoration(
                  color: AppColors.bg,
                  borderRadius: BorderRadius.circular(AppRadius.sm)),
              child: Column(
                children: [
                  Text('#BUS${ticket['id']}',
                      style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                          color: AppColors.textPrimary)),
                  Text(routeLabel,
                      style: const TextStyle(
                          fontSize: 13,
                          color: AppColors.textSecondary)),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.md),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () {
                  Navigator.pop(ctx);
                  _tabController.animateTo(0);
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.teal,
                  foregroundColor: Colors.white,
                  padding:
                      const EdgeInsets.symmetric(vertical: AppSpacing.md),
                  shape: RoundedRectangleBorder(
                      borderRadius:
                          BorderRadius.circular(AppRadius.sm)),
                ),
                child: const Text('Xem vé của tôi',
                    style: TextStyle(
                        fontSize: 15, fontWeight: FontWeight.w700)),
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
  final String id, route, type, expiry, qrData;
  final int trips;
  final bool isValid;
  final Color color;
  const _MyTicket(this.id, this.route, this.type, this.expiry, this.trips,
      this.isValid, this.color, this.qrData);
}
