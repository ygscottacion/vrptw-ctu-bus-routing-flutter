import 'package:flutter/material.dart';
import 'package:overlay_support/overlay_support.dart';
import '../theme/app_theme.dart';

class NotificationScreen extends StatefulWidget {
  const NotificationScreen({super.key});

  @override
  State<NotificationScreen> createState() => _NotificationScreenState();
}

class _NotificationScreenState extends State<NotificationScreen> {
  String _filter = 'all';

  final List<_Notif> _notifications = [
    _Notif(1, 'schedule', true, 'Xe buýt tuyến 1 đang đến',
        'Xe buýt tuyến 1 sẽ đến trạm CTU trong khoảng 5 phút. Hãy chuẩn bị!',
        '5 phút trước', AppColors.teal, '⏰'),
    _Notif(2, 'promo', true, '🎉 Ưu đãi đặc biệt sinh viên CTU!',
        'Mua vé tháng tháng 3/2026 được giảm 20%. Áp dụng đến 28/02/2026.',
        '2 giờ trước', AppColors.purple, '🏷️'),
    _Notif(3, 'schedule', false, 'Thay đổi lịch trình tuyến 2',
        'Tuyến 2 sẽ thay đổi điểm dừng từ ngày 01/03/2026. Vui lòng xem chi tiết.',
        'Hôm qua', AppColors.teal, '🚌'),
    _Notif(4, 'schedule', false, 'Xe buýt bị trễ 10 phút',
        'Tuyến 3 (7:00) bị trễ do ùn tắc giao thông. Thời gian đến dự kiến: 7:10.',
        '2 ngày trước', AppColors.orange, '⚠️'),
    _Notif(5, 'promo', false, 'Chương trình thân thiện môi trường',
        'Dùng xe buýt CTU giúp giảm 99 triệu kg CO2. Cùng chung tay bảo vệ môi trường!',
        '1 tuần trước', AppColors.green, '🌳'),
  ];

  List<_Notif> get _filtered {
    if (_filter == 'all') return _notifications;
    if (_filter == 'unread') return _notifications.where((n) => n.isUnread).toList();
    return _notifications.where((n) => n.type == _filter).toList();
  }

  void _markRead(int id) {
    setState(() {
      final idx = _notifications.indexWhere((n) => n.id == id);
      if (idx != -1) _notifications[idx] = _notifications[idx].copyWith(isUnread: false);
    });
  }

  void _markAllRead() {
    setState(() {
      for (int i = 0; i < _notifications.length; i++) {
        _notifications[i] = _notifications[i].copyWith(isUnread: false);
      }
    });
    showSimpleNotification(
      const Text('Đã đánh dấu tất cả là đã đọc',
          style: TextStyle(color: Colors.white)),
      background: AppColors.teal,
    );
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _filtered;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Thông báo'),
        actions: [
          IconButton(
            icon: const Icon(Icons.done_all_rounded, color: Colors.white),
            onPressed: _markAllRead,
            tooltip: 'Đánh dấu tất cả đã đọc',
          ),
        ],
      ),
      body: Column(
        children: [
          _buildFilterBar(),
          Expanded(
            child: filtered.isEmpty
                ? _buildEmpty()
                : ListView.separated(
                    padding: const EdgeInsets.symmetric(
                        horizontal: AppSpacing.lg,
                        vertical: AppSpacing.sm),
                    itemCount: filtered.length,
                    separatorBuilder: (_, __) =>
                        const SizedBox(height: AppSpacing.xs),
                    itemBuilder: (_, i) => _buildNotifItem(filtered[i]),
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildFilterBar() {
    final filters = [
      ('all', 'Tất cả'),
      ('unread', 'Chưa đọc'),
      ('schedule', 'Lịch trình'),
      ('promo', 'Khuyến mãi'),
    ];
    return Container(
      color: AppColors.white,
      padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md, vertical: AppSpacing.sm),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: filters.map((f) {
            final isActive = _filter == f.$1;
            return Padding(
              padding: const EdgeInsets.only(right: AppSpacing.sm),
              child: GestureDetector(
                onTap: () => setState(() => _filter = f.$1),
                child: Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: AppSpacing.lg, vertical: 7),
                  decoration: BoxDecoration(
                    color: isActive ? AppColors.teal : Colors.transparent,
                    borderRadius: BorderRadius.circular(AppRadius.full),
                    border: Border.all(
                        color: isActive ? AppColors.teal : AppColors.border,
                        width: 1.5),
                  ),
                  child: Text(f.$2,
                      style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: isActive
                              ? AppColors.white
                              : AppColors.textSecondary)),
                ),
              ),
            );
          }).toList(),
        ),
      ),
    );
  }

  Widget _buildNotifItem(_Notif n) {
    return GestureDetector(
      onTap: () => _markRead(n.id),
      child: Container(
        padding: const EdgeInsets.all(AppSpacing.md),
        margin: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
        decoration: BoxDecoration(
          color: n.isUnread ? const Color(0xFFF0FDFC) : AppColors.white,
          borderRadius: BorderRadius.circular(AppRadius.sm),
          border: n.isUnread
              ? const Border(
                  left: BorderSide(color: AppColors.teal, width: 3))
              : null,
          boxShadow: [
            BoxShadow(
                color: Colors.black.withValues(alpha: 0.04), blurRadius: 6)
          ],
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                  color: n.iconColor, shape: BoxShape.circle),
              child: Center(
                  child: Text(n.icon,
                      style: const TextStyle(fontSize: 16))),
            ),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(n.title,
                      style: TextStyle(
                          fontSize: 13,
                          fontWeight: n.isUnread
                              ? FontWeight.w700
                              : FontWeight.w600,
                          color: AppColors.textPrimary)),
                  const SizedBox(height: 3),
                  Text(n.body,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                          fontSize: 12,
                          color: AppColors.textSecondary,
                          height: 1.4)),
                  const SizedBox(height: 4),
                  Text(n.time,
                      style: const TextStyle(
                          fontSize: 11, color: AppColors.textMuted)),
                ],
              ),
            ),
            if (n.isUnread)
              Container(
                width: 10,
                height: 10,
                margin: const EdgeInsets.only(top: 4, left: 8),
                decoration: const BoxDecoration(
                    color: AppColors.teal, shape: BoxShape.circle),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmpty() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: const [
          Text('🔔', style: TextStyle(fontSize: 48)),
          SizedBox(height: AppSpacing.md),
          Text('Không có thông báo',
              style: TextStyle(
                  fontSize: 15,
                  color: AppColors.textMuted,
                  fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }
}

class _Notif {
  final int id;
  final String type, title, body, time, icon;
  final bool isUnread;
  final Color iconColor;

  const _Notif(this.id, this.type, this.isUnread, this.title, this.body,
      this.time, this.iconColor, this.icon);

  _Notif copyWith({bool? isUnread}) => _Notif(
      id, type, isUnread ?? this.isUnread, title, body, time, iconColor, icon);
}
