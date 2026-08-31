import 'package:flutter/material.dart';
import 'package:overlay_support/overlay_support.dart';
import 'package:provider/provider.dart';
import '../theme/app_theme.dart';
import '../state/app_state.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  bool _tripReminder = true;
  bool _promoNotif = true;
  bool _delayAlert = true;
  bool _loggingOut = false;

  @override
  Widget build(BuildContext context) {
    final appState = context.watch<AppState>();
    final user = appState.user ?? {};
    final role = appState.role;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Cài đặt & Tài khoản'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.only(bottom: AppSpacing.xxxl),
        child: Column(
          children: [
            _buildProfileCard(user, role),
            _buildGroup('TÀI KHOẢN', [
              _SettingItem(
                icon: '👤',
                label: 'Thông tin cá nhân',
                color: AppColors.teal,
                onTap: () => _toast('Đăng nhập với: ${user['email'] ?? '—'}'),
              ),
              _SettingItem(
                icon: '💳',
                label: 'Phương thức thanh toán',
                color: AppColors.purple,
                onTap: () => _toast('Tính năng đang phát triển'),
              ),
              _SettingItem(
                icon: '📋',
                label: 'Lịch sử đi xe',
                color: AppColors.orange,
                onTap: () => _toast('Tính năng đang phát triển'),
              ),
            ]),
            _buildNotifGroup(),
            _buildGroup('ỨNG DỤNG', [
              _SettingItem(
                icon: '🌐',
                label: 'Ngôn ngữ',
                color: AppColors.teal,
                trailing: 'Tiếng Việt',
                onTap: () {},
              ),
              _SettingItem(
                icon: 'ℹ️',
                label: 'Về ứng dụng',
                color: AppColors.green,
                onTap: () => _showAboutModal(context),
              ),
            ]),
            const SizedBox(height: AppSpacing.lg),
            _buildLogoutBtn(context, appState),
          ],
        ),
      ),
    );
  }

  // ─── PROFILE CARD ──────────────────────────────────────────
  Widget _buildProfileCard(Map<String, dynamic> user, String role) {
    return Container(
      margin: const EdgeInsets.all(AppSpacing.lg),
      padding: const EdgeInsets.all(AppSpacing.lg),
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(AppRadius.md),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 8,
            offset: const Offset(0, 2),
          )
        ],
      ),
      child: Column(
        children: [
          Container(
            width: 80,
            height: 80,
            decoration: BoxDecoration(
              color: role == 'admin' ? AppColors.purpleBg : AppColors.tealBg,
              shape: BoxShape.circle,
            ),
            child: Center(
              child: Text(
                role == 'admin' ? '👑' : '🚌',
                style: const TextStyle(fontSize: 40),
              ),
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            user['full_name'] ?? user['email'] ?? 'Người dùng',
            style: const TextStyle(
              fontSize: 17,
              fontWeight: FontWeight.w700,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            'Vai trò: ${role.toUpperCase()}',
            style: const TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: AppColors.teal,
            ),
          ),
          if (user['phone'] != null) ...[
            const SizedBox(height: 2),
            Text(
              'SĐT: ${user['phone']}',
              style: const TextStyle(fontSize: 12, color: AppColors.textMuted),
            ),
          ],
        ],
      ),
    );
  }

  // ─── LOGOUT BUTTON ─────────────────────────────────────────
  Widget _buildLogoutBtn(BuildContext context, AppState appState) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
      child: SizedBox(
        width: double.infinity,
        child: ElevatedButton.icon(
          onPressed:
              _loggingOut ? null : () => _showLogoutConfirm(context, appState),
          style: ElevatedButton.styleFrom(
            backgroundColor: AppColors.red,
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(AppRadius.md),
            ),
          ),
          icon: const Text('🚪', style: TextStyle(fontSize: 18)),
          label: const Text(
            'Đăng xuất',
            style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
          ),
        ),
      ),
    );
  }

  void _showLogoutConfirm(BuildContext context, AppState appState) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: const [
            Text('🚪', style: TextStyle(fontSize: 44)),
            SizedBox(height: AppSpacing.sm),
            Text(
              'Đăng xuất?',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w700,
                color: AppColors.textPrimary,
              ),
            ),
            SizedBox(height: AppSpacing.sm),
            Text(
              'Bạn có chắc chắn muốn đăng xuất khỏi hệ thống không?',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 13, color: AppColors.textSecondary),
            ),
          ],
        ),
        actions: [
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: () => Navigator.pop(ctx),
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: AppColors.border),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(AppRadius.sm),
                    ),
                    padding:
                        const EdgeInsets.symmetric(vertical: AppSpacing.sm),
                  ),
                  child: const Text('Hủy',
                      style: TextStyle(color: AppColors.textSecondary)),
                ),
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: ElevatedButton(
                  onPressed: () async {
                    Navigator.pop(ctx);
                    setState(() => _loggingOut = true);
                    await appState.logout();
                    if (!mounted) return;
                    setState(() => _loggingOut = false);
                    _toast('👋 Đã đăng xuất khỏi tài khoản!');
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.red,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(AppRadius.sm),
                    ),
                    padding:
                        const EdgeInsets.symmetric(vertical: AppSpacing.sm),
                  ),
                  child: const Text('Đăng xuất'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // ─── SETTINGS GROUP ───────────────────────────────────────
  Widget _buildGroup(String title, List<_SettingItem> items) {
    return Container(
      margin: const EdgeInsets.fromLTRB(
          AppSpacing.lg, 0, AppSpacing.lg, AppSpacing.md),
      padding: const EdgeInsets.all(AppSpacing.lg),
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(AppRadius.md),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 8,
            offset: const Offset(0, 2),
          )
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title,
              style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: AppColors.textMuted,
                  letterSpacing: 0.5)),
          const SizedBox(height: AppSpacing.sm),
          ...items.asMap().entries.map((e) {
            final isLast = e.key == items.length - 1;
            return Column(
              children: [
                _buildSettingRow(e.value),
                if (!isLast) const Divider(height: 1, color: AppColors.border),
              ],
            );
          }),
        ],
      ),
    );
  }

  Widget _buildNotifGroup() {
    return Container(
      margin: const EdgeInsets.fromLTRB(
          AppSpacing.lg, 0, AppSpacing.lg, AppSpacing.md),
      padding: const EdgeInsets.all(AppSpacing.lg),
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(AppRadius.md),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 8,
            offset: const Offset(0, 2),
          )
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('THÔNG BÁO',
              style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: AppColors.textMuted,
                  letterSpacing: 0.5)),
          const SizedBox(height: AppSpacing.sm),
          _buildToggleRow('🔔', 'Nhắc nhở chuyến xe', AppColors.green,
              _tripReminder, (v) => setState(() => _tripReminder = v)),
          const Divider(height: 1, color: AppColors.border),
          _buildToggleRow('🏷️', 'Thông báo khuyến mãi', AppColors.purple,
              _promoNotif, (v) => setState(() => _promoNotif = v)),
          const Divider(height: 1, color: AppColors.border),
          _buildToggleRow('⚠️', 'Cảnh báo trễ xe', AppColors.orange,
              _delayAlert, (v) => setState(() => _delayAlert = v)),
        ],
      ),
    );
  }

  Widget _buildSettingRow(_SettingItem item) {
    return GestureDetector(
      onTap: item.onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
        child: Row(
          children: [
            Container(
              width: 34,
              height: 34,
              decoration: BoxDecoration(
                  color: item.color, borderRadius: BorderRadius.circular(10)),
              child: Center(
                  child: Text(item.icon, style: const TextStyle(fontSize: 15))),
            ),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Text(item.label,
                  style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                      color: AppColors.textPrimary)),
            ),
            if (item.trailing != null)
              Text(item.trailing!,
                  style: const TextStyle(
                      fontSize: 13, color: AppColors.textMuted)),
            const SizedBox(width: AppSpacing.xs),
            const Icon(Icons.chevron_right,
                color: AppColors.textMuted, size: 20),
          ],
        ),
      ),
    );
  }

  Widget _buildToggleRow(String icon, String label, Color color, bool value,
      ValueChanged<bool> onChanged) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
      child: Row(
        children: [
          Container(
            width: 34,
            height: 34,
            decoration: BoxDecoration(
                color: color, borderRadius: BorderRadius.circular(10)),
            child:
                Center(child: Text(icon, style: const TextStyle(fontSize: 15))),
          ),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: Text(label,
                style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                    color: AppColors.textPrimary)),
          ),
          Switch(
            value: value,
            onChanged: onChanged,
            activeThumbColor: AppColors.teal,
            activeTrackColor: AppColors.teal.withValues(alpha: 0.4),
          ),
        ],
      ),
    );
  }

  void _showAboutModal(BuildContext context) {
    showModalBottomSheet(
      context: context,
      backgroundColor: AppColors.white,
      shape: const RoundedRectangleBorder(
          borderRadius:
              BorderRadius.vertical(top: Radius.circular(AppRadius.lg))),
      builder: (ctx) => Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
                width: 40,
                height: 4,
                margin: const EdgeInsets.only(bottom: AppSpacing.lg),
                decoration: BoxDecoration(
                    color: AppColors.border,
                    borderRadius: BorderRadius.circular(AppRadius.full))),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  width: 60,
                  height: 60,
                  decoration: BoxDecoration(
                      color: AppColors.teal,
                      borderRadius: BorderRadius.circular(16)),
                  child: const Center(
                      child: Text('🚌', style: TextStyle(fontSize: 30))),
                ),
                const SizedBox(width: AppSpacing.md),
                const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('MyCTU BUS',
                        style: TextStyle(
                            fontSize: 20,
                            fontWeight: FontWeight.w800,
                            color: AppColors.textPrimary)),
                    Text('Phiên bản 1.0.0',
                        style: TextStyle(
                            fontSize: 13, color: AppColors.textMuted)),
                  ],
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.md),
            const Text(
              'Ứng dụng xe buýt đưa đón sinh viên Trường Đại học Cần Thơ. Cung cấp thông tin lịch trình, đặt vé và theo dõi xe buýt theo thời gian thực.',
              textAlign: TextAlign.center,
              style: TextStyle(
                  fontSize: 13, color: AppColors.textSecondary, height: 1.5),
            ),
            const SizedBox(height: AppSpacing.lg),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                _aboutStat('3', 'Tuyến xe'),
                _aboutStat('15+', 'Trạm dừng'),
                _aboutStat('5000+', 'Sinh viên'),
              ],
            ),
            const SizedBox(height: AppSpacing.md),
            const Text('© 2026 Trường Đại học Cần Thơ',
                style: TextStyle(fontSize: 12, color: AppColors.textMuted)),
            const SizedBox(height: AppSpacing.lg),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton(
                onPressed: () => Navigator.pop(ctx),
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: AppColors.border),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(AppRadius.sm)),
                  padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
                ),
                child: const Text('Đóng',
                    style: TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textSecondary)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _aboutStat(String value, String label) {
    return Column(
      children: [
        Text(value,
            style: const TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.w800,
                color: AppColors.teal)),
        Text(label,
            style: const TextStyle(fontSize: 12, color: AppColors.textMuted)),
      ],
    );
  }

  void _toast(String msg) {
    showSimpleNotification(
      Text(msg, style: const TextStyle(color: Colors.white)),
      background: AppColors.teal,
    );
  }
}

class _SettingItem {
  final String icon, label;
  final Color color;
  final String? trailing;
  final VoidCallback onTap;
  const _SettingItem(
      {required this.icon,
      required this.label,
      required this.color,
      required this.onTap,
      this.trailing});
}
