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

  // CTUPay wallet (test/demo state only — replace with real backend later)
  double _balance = 500000;

  // Tiny overlap of the wallet card into the bottom of the hero image.
  // Uses Transform.translate (not Positioned overflow) so the card's
  // hit-test area stays accurate even though it's only overlapping a
  // couple of points.
  static const double _walletOverlap = 3;

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
              Transform.translate(
                offset: const Offset(0, -_walletOverlap),
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                      horizontal: AppSpacing.lg),
                  child: _buildWalletSection(context),
                ),
              ),
              const SizedBox(height: AppSpacing.lg),
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

  // ─── CTUPay WALLET SECTION ────────────────────────────────
  Widget _buildWalletSection(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md, vertical: AppSpacing.sm),
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: AppColors.border),
        boxShadow: [
          BoxShadow(
              color: Colors.black.withValues(alpha: 0.05),
              blurRadius: 6,
              offset: const Offset(0, 2)),
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 30,
            height: 30,
            decoration: const BoxDecoration(
              color: AppColors.tealBg,
              shape: BoxShape.circle,
            ),
            child: const Center(
                child: Text('💳', style: TextStyle(fontSize: 14))),
          ),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'CTUPay',
                  style: TextStyle(
                      color: AppColors.textSecondary,
                      fontSize: 11,
                      fontWeight: FontWeight.w500),
                ),
                Text(
                  '${_formatCurrency(_balance)} ₫',
                  style: const TextStyle(
                      color: AppColors.textPrimary,
                      fontSize: 16,
                      fontWeight: FontWeight.w700),
                ),
              ],
            ),
          ),
          _walletActionButton(
            'Nạp',
                () => _showAmountDialog(context, isDeposit: true),
          ),
          const SizedBox(width: AppSpacing.sm),
          _walletActionButton(
            'Rút',
                () => _showAmountDialog(context, isDeposit: false),
          ),
        ],
      ),
    );
  }

  Widget _walletActionButton(String label, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.md, vertical: 6),
        decoration: BoxDecoration(
          color: AppColors.tealBg,
          borderRadius: BorderRadius.circular(AppRadius.full),
        ),
        child: Text(
          label,
          style: const TextStyle(
              color: AppColors.teal, fontWeight: FontWeight.w600, fontSize: 12),
        ),
      ),
    );
  }


  void _showAmountDialog(BuildContext context, {required bool isDeposit}) {
    final controller = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.md)),
        title: Text(isDeposit ? 'Nạp tiền vào CTUPay' : 'Rút tiền từ CTUPay'),
        content: TextField(
          controller: controller,
          autofocus: true,
          keyboardType: const TextInputType.numberWithOptions(),
          decoration: const InputDecoration(
            hintText: 'Nhập số tiền (VNĐ)',
            prefixText: '₫ ',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Hủy'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.teal),
            onPressed: () => _handleWalletSubmit(ctx, controller.text, isDeposit),
            child: Text(
              isDeposit ? 'Nạp' : 'Rút',
              style: const TextStyle(color: Colors.white),
            ),
          ),
        ],
      ),
    );
  }

  void _handleWalletSubmit(BuildContext ctx, String rawText, bool isDeposit) {
    final cleaned = rawText.replaceAll('.', '').replaceAll(',', '').trim();
    final amount = double.tryParse(cleaned) ?? 0;

    if (amount <= 0) {
      Navigator.pop(ctx);
      showSimpleNotification(
        const Text('Vui lòng nhập số tiền hợp lệ',
            style: TextStyle(color: Colors.white)),
        background: Colors.redAccent,
      );
      return;
    }

    if (!isDeposit && amount > _balance) {
      Navigator.pop(ctx);
      showSimpleNotification(
        const Text('Số dư không đủ để rút', style: TextStyle(color: Colors.white)),
        background: Colors.redAccent,
      );
      return;
    }

    setState(() {
      _balance += isDeposit ? amount : -amount;
    });
    Navigator.pop(ctx);
    showSimpleNotification(
      Text(
        isDeposit
            ? 'Đã nạp ${_formatCurrency(amount)} ₫'
            : 'Đã rút ${_formatCurrency(amount)} ₫',
        style: const TextStyle(color: Colors.white),
      ),
      background: AppColors.teal,
    );
  }

  String _formatCurrency(double? value) {
    final val = (value ?? 0).toInt();
    return val.toString().replaceAllMapped(
        RegExp(r'(\d{1,3})(?=(\d{3})+(?!\d))'), (m) => '${m[1]}.');
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
                  child: _buildFeatureCard(
                      '🚌', 'Đặt Tuyến Xe', AppColors.tealBg, () {})),
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
        final val = (_co2Animation.value).toInt();
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
}