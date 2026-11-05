import 'dart:async';

import 'package:flutter/material.dart';
import 'package:overlay_support/overlay_support.dart';

import '../services/api_service.dart';
import '../theme/app_theme.dart';

class NotificationScreen extends StatefulWidget {
  const NotificationScreen({
    super.key,
    required this.api,
    required this.isActive,
  });
  final ApiService api;
  final bool isActive;

  @override
  State<NotificationScreen> createState() => _NotificationScreenState();
}

class _NotificationScreenState extends State<NotificationScreen> {
  String _filter = 'all';
  List<_Notif> _notifications = [];
  bool _loading = true;
  String? _error;
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _loadNotifications();
    _refreshTimer = Timer.periodic(const Duration(seconds: 30), (_) {
      if (mounted) _loadNotifications(silent: true);
    });
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  @override
  void didUpdateWidget(covariant NotificationScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!oldWidget.isActive && widget.isActive) {
      _loadNotifications();
    }
  }

  List<_Notif> get _filtered {
    if (_filter == 'all') return _notifications;
    if (_filter == 'unread') return _notifications.where((n) => !n.isRead).toList();
    return _notifications.where((n) => n.type == _filter).toList();
  }

  Future<void> _loadNotifications({bool silent = false}) async {
    if (!silent) {
      setState(() {
        _loading = true;
        _error = null;
      });
    }
    try {
      final rows = await widget.api.fetchMyNotifications();
      if (!mounted) return;
      setState(() {
        _notifications = rows
            .whereType<Map>()
            .map((row) => _Notif.fromJson(Map<String, dynamic>.from(row)))
            .toList();
        _loading = false;
        _error = null;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString().replaceFirst('Exception: ', '');
        _loading = false;
      });
    }
  }

  Future<void> _setRead(_Notif notification, bool isRead) async {
    final index = _notifications.indexWhere((n) => n.id == notification.id);
    if (index < 0 || notification.isRead == isRead) return;
    final previous = _notifications[index];
    setState(() => _notifications[index] = previous.copyWith(isRead: isRead));
    try {
      await widget.api.markNotificationRead(notification.id, isRead);
    } catch (e) {
      if (!mounted) return;
      final currentIndex =
          _notifications.indexWhere((item) => item.id == notification.id);
      if (currentIndex >= 0) {
        setState(() => _notifications[currentIndex] = previous);
      }
      showSimpleNotification(
        Text('Không thể cập nhật thông báo: ${e.toString().replaceFirst('Exception: ', '')}',
            style: const TextStyle(color: Colors.white)),
        background: AppColors.orange,
      );
    }
  }

  Future<void> _markAllRead() async {
    final unread = _notifications.where((n) => !n.isRead).toList();
    for (final notification in unread) {
      await _setRead(notification, true);
    }
    if (mounted && unread.isNotEmpty) {
      showSimpleNotification(
        const Text('Đã đánh dấu tất cả là đã đọc', style: TextStyle(color: Colors.white)),
        background: AppColors.teal,
      );
    }
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
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _error != null
                    ? Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(_error!, textAlign: TextAlign.center),
                            const SizedBox(height: AppSpacing.md),
                            OutlinedButton.icon(
                              onPressed: _loadNotifications,
                              icon: const Icon(Icons.refresh),
                              label: const Text('Thử lại'),
                            ),
                          ],
                        ),
                      )
                    : filtered.isEmpty
                        ? _buildEmpty()
                        : RefreshIndicator(
                            onRefresh: _loadNotifications,
                            child: ListView.separated(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: AppSpacing.lg,
                                  vertical: AppSpacing.sm),
                              itemCount: filtered.length,
                              separatorBuilder: (_, __) =>
                                  const SizedBox(height: AppSpacing.xs),
                              itemBuilder: (_, i) => _buildNotifItem(filtered[i]),
                            ),
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
      ('trip', 'Chuyến đi'),
      ('transaction', 'Giao dịch'),
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
    final color = switch (n.type) {
      'trip' => AppColors.teal,
      'transaction' => AppColors.green,
      _ => AppColors.purple,
    };
    final icon = switch (n.type) {
      'trip' => '🚌',
      'transaction' => '💳',
      _ => '🔔',
    };
    return GestureDetector(
      onTap: () => _setRead(n, true),
      child: Container(
        padding: const EdgeInsets.all(AppSpacing.md),
        margin: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
        decoration: BoxDecoration(
          color: !n.isRead ? const Color(0xFFF0FDFC) : AppColors.white,
          borderRadius: BorderRadius.circular(AppRadius.sm),
          border: !n.isRead
              ? const Border(left: BorderSide(color: AppColors.teal, width: 3))
              : null,
          boxShadow: [
            BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 6)
          ],
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(color: color, shape: BoxShape.circle),
              child: Center(child: Text(icon, style: const TextStyle(fontSize: 16))),
            ),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(n.title,
                      style: TextStyle(
                          fontSize: 13,
                          fontWeight: !n.isRead ? FontWeight.w700 : FontWeight.w600,
                          color: AppColors.textPrimary)),
                  const SizedBox(height: 3),
                  Text(n.body,
                      maxLines: 3,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                          fontSize: 12,
                          color: AppColors.textSecondary,
                          height: 1.4)),
                  const SizedBox(height: 4),
                  Text(_formatTime(n.createdAt),
                      style: const TextStyle(fontSize: 11, color: AppColors.textMuted)),
                ],
              ),
            ),
            if (!n.isRead)
              Container(
                width: 10,
                height: 10,
                margin: const EdgeInsets.only(top: 4, left: 8),
                decoration: const BoxDecoration(color: AppColors.teal, shape: BoxShape.circle),
              ),
          ],
        ),
      ),
    );
  }

  String _formatTime(DateTime time) {
    final difference = DateTime.now().difference(time.toLocal());
    if (difference.isNegative || difference.inMinutes < 1) return 'Vừa xong';
    if (difference.inMinutes < 60) return '${difference.inMinutes} phút trước';
    if (difference.inHours < 24) return '${difference.inHours} giờ trước';
    if (difference.inDays < 7) return '${difference.inDays} ngày trước';
    return '${time.toLocal().day.toString().padLeft(2, '0')}/${time.toLocal().month.toString().padLeft(2, '0')}/${time.toLocal().year}';
  }

  Widget _buildEmpty() => Center(
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

class _Notif {
  const _Notif({
    required this.id,
    required this.type,
    required this.title,
    required this.body,
    required this.isRead,
    required this.createdAt,
  });

  final String id;
  final String type;
  final String title;
  final String body;
  final bool isRead;
  final DateTime createdAt;

  factory _Notif.fromJson(Map<String, dynamic> json) => _Notif(
        id: json['id'].toString(),
        type: json['type']?.toString() ?? 'general',
        title: json['title']?.toString() ?? '',
        body: json['body']?.toString() ?? '',
        isRead: json['is_read'] == true,
        createdAt: DateTime.tryParse(json['created_at']?.toString() ?? '') ?? DateTime.now(),
      );

  _Notif copyWith({bool? isRead}) => _Notif(
        id: id,
        type: type,
        title: title,
        body: body,
        isRead: isRead ?? this.isRead,
        createdAt: createdAt,
      );
}
