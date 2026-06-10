import 'package:flutter/material.dart';
import 'package:overlay_support/overlay_support.dart';
import '../theme/app_theme.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen>
    with SingleTickerProviderStateMixin {
  // CO2 animation
  late AnimationController _co2Controller;
  late Animation<double> _co2Animation;
  String _selectedLocation = '';

  static const _locations = [
    'Trường ĐH Cần Thơ',
    'Vincom Xuân Khánh',
    'Vincom Hùng Vương',
    'Bến Ninh Kiều',
    'Bến xe Cần Thơ',
  ];

  @override
  void initState() {
    super.initState();
    _co2Controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    );
    _co2Animation = Tween<double>(begin: 0, end: 99626200).animate(
      CurvedAnimation(parent: _co2Controller, curve: Curves.easeOut),
    );
    _co2Controller.forward();

    Future.delayed(const Duration(milliseconds: 800), () {
      if (mounted) {
        showSimpleNotification(
          const Text('🚌 Chào mừng đến với MyCTU BUS!',
              style: TextStyle(color: Colors.white)),
          background: AppColors.teal,
          duration: const Duration(seconds: 2),
        );
      }
    });
  }

  @override
  void dispose() {
    _co2Controller.dispose();
    super.dispose();
  }

  void _selectLocation(String name, BuildContext context) {
    setState(() => _selectedLocation = name);
    showSimpleNotification(
      Text('Đã chọn: $name', style: const TextStyle(color: Colors.white)),
      background: AppColors.teal,
    );
    // Navigate to Map tab via parent (index 1)
    Future.delayed(const Duration(milliseconds: 600), () {
      if (mounted) {
        // Trigger tab switch through the shell
        final scaffold = Scaffold.maybeOf(context);
        if (scaffold != null) {
          DefaultTabController.maybeOf(context);
        }
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bg,
      body: SafeArea(
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildHero(context),
              _buildSearchSection(context),
              _buildBody(context),
            ],
          ),
        ),
      ),
    );
  }

  // ─── HERO ─────────────────────────────────────────────────
  Widget _buildHero(BuildContext context) {
    return SizedBox(
      height: 220,
      child: Stack(
        fit: StackFit.expand,
        children: [
          Image.asset('assets/images/bus_hero.png', fit: BoxFit.cover),
          Container(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  AppColors.teal.withValues(alpha: 0.5),
                  AppColors.teal.withValues(alpha: 0.2),
                ],
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(AppSpacing.lg),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Logo
                RichText(
                  text: const TextSpan(
                    children: [
                      TextSpan(
                        text: 'My',
                        style: TextStyle(
                          fontSize: 28,
                          fontWeight: FontWeight.w800,
                          color: AppColors.amber,
                          fontStyle: FontStyle.italic,
                        ),
                      ),
                      TextSpan(
                        text: 'CTU\n',
                        style: TextStyle(
                          fontSize: 28,
                          fontWeight: FontWeight.w800,
                          color: AppColors.white,
                          fontStyle: FontStyle.italic,
                        ),
                      ),
                      TextSpan(
                        text: 'BUS',
                        style: TextStyle(
                          fontSize: 42,
                          fontWeight: FontWeight.w900,
                          color: AppColors.amber,
                          fontStyle: FontStyle.italic,
                          letterSpacing: 2,
                        ),
                      ),
                    ],
                  ),
                ),
                // Avatar button
                GestureDetector(
                  onTap: () {
                    // Navigate to Settings tab (index 4)
                  },
                  child: Container(
                    width: 50,
                    height: 50,
                    decoration: BoxDecoration(
                      color: AppColors.white,
                      shape: BoxShape.circle,
                      border: Border.all(
                          color: Colors.white.withValues(alpha: 0.8), width: 2),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withValues(alpha: 0.1),
                          blurRadius: 8,
                          offset: const Offset(0, 2),
                        )
                      ],
                    ),
                    child: const Center(
                        child: Text('👤', style: TextStyle(fontSize: 22))),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ─── SEARCH SECTION ───────────────────────────────────────
  Widget _buildSearchSection(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          colors: [AppColors.teal, AppColors.tealDark],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
      ),
      padding: const EdgeInsets.fromLTRB(
          AppSpacing.lg, AppSpacing.md, AppSpacing.lg, AppSpacing.lg),
      child: Column(
        children: [
          // Search bar
          GestureDetector(
            onTap: () => _showSearchModal(context),
            child: Container(
              decoration: BoxDecoration(
                color: AppColors.white,
                borderRadius: BorderRadius.circular(AppRadius.sm),
                boxShadow: [
                  BoxShadow(
                      color: Colors.black.withValues(alpha: 0.08), blurRadius: 8)
                ],
              ),
              padding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.lg, vertical: AppSpacing.md),
              child: Row(
                children: [
                  const Text('🔍', style: TextStyle(fontSize: 16)),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(
                    child: Text(
                      _selectedLocation.isNotEmpty
                          ? '📍 $_selectedLocation'
                          : 'Nhập địa điểm của bạn',
                      style: const TextStyle(
                          color: AppColors.textMuted, fontSize: 14),
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: AppSpacing.md),
          // Quick location chips
          Wrap(
            spacing: AppSpacing.sm,
            children: ['Vincom Xuân Khánh', 'Vincom Hùng Vương'].map((loc) {
              return GestureDetector(
                onTap: () => _selectLocation(loc, context),
                child: Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: AppSpacing.md, vertical: 6),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(AppRadius.full),
                    border: Border.all(
                        color: Colors.white.withValues(alpha: 0.5), width: 1.5),
                  ),
                  child: Text(loc,
                      style: const TextStyle(
                          color: AppColors.white,
                          fontSize: 13,
                          fontWeight: FontWeight.w500)),
                ),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }

  // ─── BODY ─────────────────────────────────────────────────
  Widget _buildBody(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Feature cards
          Row(
            children: [
              Expanded(
                  child: _buildFeatureCard('🚌', 'Tuyến xe', AppColors.tealBg,
                      () {})),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                  child: _buildFeatureCard('🎫', 'Mua vé', AppColors.purpleBg,
                      () {})),
            ],
          ),
          const SizedBox(height: AppSpacing.xl),
          // Eco section
          _buildEcoSection(),
        ],
      ),
    );
  }

  Widget _buildFeatureCard(
      String emoji, String label, Color bgColor, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(AppSpacing.lg),
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
        child: Column(
          children: [
            Container(
              width: 72,
              height: 72,
              decoration:
                  BoxDecoration(color: bgColor, shape: BoxShape.circle),
              child: Center(
                  child: Text(emoji, style: const TextStyle(fontSize: 36))),
            ),
            const SizedBox(height: AppSpacing.sm),
            Text(label,
                style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textPrimary)),
          ],
        ),
      ),
    );
  }

  Widget _buildEcoSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Text('Vì một Việt Nam xanh',
                style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                    color: AppColors.textPrimary)),
            const SizedBox(width: AppSpacing.sm),
            Expanded(
                child: Container(height: 1.5, color: AppColors.border)),
          ],
        ),
        const SizedBox(height: AppSpacing.md),
        Container(
          padding: const EdgeInsets.all(AppSpacing.lg),
          decoration: BoxDecoration(
            color: AppColors.white,
            borderRadius: BorderRadius.circular(AppRadius.md),
            border: Border.all(color: AppColors.border),
            boxShadow: [
              BoxShadow(
                  color: Colors.black.withValues(alpha: 0.06),
                  blurRadius: 8,
                  offset: const Offset(0, 2))
            ],
          ),
          child: Row(
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(32),
                child: Image.asset('assets/images/co2_icon.png',
                    width: 64, height: 64, fit: BoxFit.cover),
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: Row(
                  children: [
                    Expanded(child: _buildEcoStat()),
                    Container(
                        width: 1.5, height: 40, color: AppColors.border),
                    Expanded(child: _buildTreeStat()),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildEcoStat() {
    return AnimatedBuilder(
      animation: _co2Animation,
      builder: (_, __) {
        final val = _co2Animation.value.toInt();
        final formatted = val.toString().replaceAllMapped(
            RegExp(r'(\d{1,3})(?=(\d{3})+(?!\d))'), (m) => '${m[1]}.');
        return _ecoStatItem('Lượng CO2 giảm', '$formatted Kg', AppColors.green);
      },
    );
  }

  Widget _buildTreeStat() {
    return _ecoStatItem(
        'Tương đương với', '4.591.069 cây xanh', AppColors.teal);
  }

  Widget _ecoStatItem(String label, String value, Color valueColor) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.sm),
      decoration: BoxDecoration(
        color: AppColors.bg,
        borderRadius: BorderRadius.circular(AppRadius.sm),
      ),
      child: Column(
        children: [
          Text(label,
              style: const TextStyle(
                  fontSize: 10,
                  color: AppColors.textSecondary,
                  fontWeight: FontWeight.w500),
              textAlign: TextAlign.center),
          const SizedBox(height: 4),
          Text(value,
              style: TextStyle(
                  fontSize: 12, fontWeight: FontWeight.w700, color: valueColor),
              textAlign: TextAlign.center),
        ],
      ),
    );
  }

  // ─── SEARCH MODAL ─────────────────────────────────────────
  void _showSearchModal(BuildContext context) {
    String query = '';
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.white,
      shape: const RoundedRectangleBorder(
        borderRadius:
            BorderRadius.vertical(top: Radius.circular(AppRadius.lg)),
      ),
      builder: (ctx) {
        return StatefulBuilder(builder: (ctx, setModalState) {
          final filtered = _locations
              .where((l) =>
                  query.isEmpty ||
                  l.toLowerCase().contains(query.toLowerCase()))
              .toList();
          return DraggableScrollableSheet(
            expand: false,
            initialChildSize: 0.6,
            builder: (_, scrollCtrl) => Padding(
              padding: EdgeInsets.only(
                  left: AppSpacing.lg,
                  right: AppSpacing.lg,
                  top: AppSpacing.lg,
                  bottom: MediaQuery.of(ctx).viewInsets.bottom +
                      AppSpacing.xxxl),
              child: Column(
                children: [
                  // Handle
                  Container(
                      width: 40,
                      height: 4,
                      margin: const EdgeInsets.only(bottom: AppSpacing.md),
                      decoration: BoxDecoration(
                          color: AppColors.border,
                          borderRadius:
                              BorderRadius.circular(AppRadius.full))),
                  const Align(
                    alignment: Alignment.centerLeft,
                    child: Text('Tìm kiếm địa điểm',
                        style: TextStyle(
                            fontSize: 17,
                            fontWeight: FontWeight.w700,
                            color: AppColors.textPrimary)),
                  ),
                  const SizedBox(height: AppSpacing.md),
                  // Search input
                  Container(
                    decoration: BoxDecoration(
                      color: AppColors.bg,
                      borderRadius: BorderRadius.circular(AppRadius.sm),
                      border: Border.all(color: AppColors.border),
                    ),
                    padding: const EdgeInsets.symmetric(
                        horizontal: AppSpacing.md),
                    child: Row(
                      children: [
                        const Text('🔍', style: TextStyle(fontSize: 16)),
                        const SizedBox(width: AppSpacing.sm),
                        Expanded(
                          child: TextField(
                            autofocus: true,
                            decoration: const InputDecoration(
                              hintText: 'Nhập tên địa điểm...',
                              hintStyle:
                                  TextStyle(color: AppColors.textMuted),
                              border: InputBorder.none,
                            ),
                            onChanged: (v) =>
                                setModalState(() => query = v),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: AppSpacing.md),
                  Expanded(
                    child: ListView.separated(
                      controller: scrollCtrl,
                      itemCount: filtered.length,
                      separatorBuilder: (_, __) => const Divider(
                          height: 1, color: AppColors.border),
                      itemBuilder: (_, i) => ListTile(
                        leading: const Text('📍',
                            style: TextStyle(fontSize: 18)),
                        title: Text(filtered[i],
                            style: const TextStyle(
                                fontSize: 14,
                                fontWeight: FontWeight.w500,
                                color: AppColors.textPrimary)),
                        onTap: () {
                          Navigator.pop(ctx);
                          _selectLocation(filtered[i], context);
                        },
                      ),
                    ),
                  ),
                ],
              ),
            ),
          );
        });
      },
    );
  }
}
