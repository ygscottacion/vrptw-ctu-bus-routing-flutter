import 'package:flutter/material.dart';
import '../../services/api_service.dart';
import '../../theme/app_theme.dart';

class DriverAlertsTab extends StatefulWidget {
  const DriverAlertsTab({super.key, required this.api});

  final ApiService api;

  @override
  State<DriverAlertsTab> createState() => _DriverAlertsTabState();
}

class _DriverAlertsTabState extends State<DriverAlertsTab> {
  final List<Map<String, dynamic>> _dispatchAlerts = [
    {
      'id': 1,
      'title': 'Thông báo điều phối chuyến giờ cao điểm',
      'content': 'Tài xế chuẩn bị tăng cường 1 lượt chạy lúc 17:15 từ Khu II sang Khu A.',
      'type': 'dispatch',
      'time': '10 phút trước',
      'priority': 'high',
    },
    {
      'id': 2,
      'title': 'Cảnh báo kẹt xe đường 3/2',
      'content': 'Lưu ý kẹt xe đoạn giao đường 3/2 và Nguyễn Văn Linh. Hãy đi chầm chậm và chú ý an toàn.',
      'type': 'traffic',
      'time': '45 phút trước',
      'priority': 'medium',
    },
    {
      'id': 3,
      'title': 'Lịch kiểm tra kỹ thuật định kỳ',
      'content': 'Xe buýt #402 dự kiến bảo dưỡng dầu máy vào cuối ca hôm nay lúc 18:30.',
      'type': 'maintenance',
      'time': '2 giờ trước',
      'priority': 'normal',
    },
  ];

  final List<Map<String, dynamic>> _myIncidents = [];

  void _showReportDialog() {
    final titleCtrl = TextEditingController();
    final descCtrl = TextEditingController();
    String category = 'Kẹt xe nghiêm trọng';

    showDialog(
      context: context,
      builder: (c) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Row(
          children: const [
            Icon(Icons.warning_amber_rounded, color: Colors.orange),
            SizedBox(width: 8),
            Text('Báo cáo sự cố khẩn cấp'),
          ],
        ),
        content: StatefulBuilder(
          builder: (context, setDlgState) {
            return SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Loại sự cố:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                  const SizedBox(height: 6),
                  DropdownButtonFormField<String>(
                    value: category,
                    decoration: InputDecoration(
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    ),
                    items: const [
                      DropdownMenuItem(value: 'Kẹt xe nghiêm trọng', child: Text('Kẹt xe nghiêm trọng')),
                      DropdownMenuItem(value: 'Xe hỏng / Sự cố máy', child: Text('Xe hỏng / Sự cố máy')),
                      DropdownMenuItem(value: 'Va chạm giao thông', child: Text('Va chạm giao thông')),
                      DropdownMenuItem(value: 'Thời tiết xấu / Ngập nước', child: Text('Thời tiết xấu / Ngập nước')),
                      DropdownMenuItem(value: 'Khác', child: Text('Khác')),
                    ],
                    onChanged: (v) {
                      if (v != null) setDlgState(() => category = v);
                    },
                  ),
                  const SizedBox(height: 12),
                  const Text('Tiêu đề sự cố:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                  const SizedBox(height: 4),
                  TextField(
                    controller: titleCtrl,
                    decoration: InputDecoration(
                      hintText: 'VD: Xe bị xẹp lốp tại đường 3/2',
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                  ),
                  const SizedBox(height: 12),
                  const Text('Mô tả chi tiết (không bắt buộc):', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                  const SizedBox(height: 4),
                  TextField(
                    controller: descCtrl,
                    maxLines: 3,
                    decoration: InputDecoration(
                      hintText: 'Nhập vị trí chính xác và tình trạng xe...',
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                  ),
                ],
              ),
            );
          },
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(c),
            child: const Text('Hủy'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.redAccent),
            onPressed: () async {
              final title = titleCtrl.text.trim().isEmpty ? category : titleCtrl.text.trim();
              final desc = descCtrl.text.trim();
              Navigator.pop(c);
              try {
                await widget.api.reportIncident(
                  title: title,
                  description: desc,
                  vehicleId: 402,
                );
                setState(() {
                  _myIncidents.insert(0, {
                    'title': title,
                    'desc': desc,
                    'time': 'Vừa xong',
                    'status': 'Đã gửi Admin',
                  });
                });
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('Đã gửi báo cáo sự cố về trung tâm Admin.'),
                      backgroundColor: AppColors.teal,
                    ),
                  );
                }
              } catch (e) {
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Không gửi được báo cáo: $e')),
                  );
                }
              }
            },
            child: const Text('Gửi báo cáo'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6FAFA),
      appBar: AppBar(
        backgroundColor: AppColors.teal,
        title: const Text('Trung tâm Thông báo & Điều phối'),
        elevation: 1,
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          // Emergency Report Quick Card
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFFBA1A1A), Color(0xFFD32F2F)],
              ),
              borderRadius: BorderRadius.circular(16),
              boxShadow: [
                BoxShadow(
                  color: Colors.red.withOpacity(0.3),
                  blurRadius: 10,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: Row(
              children: [
                const Icon(Icons.warning_amber_rounded, size: 40, color: Colors.white),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: const [
                      Text(
                        'BÁO CÁO SỰ CỐ KHẨN CẤP',
                        style: TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                          fontSize: 14,
                        ),
                      ),
                      SizedBox(height: 2),
                      Text(
                        'Thông báo ngay cho Admin khi xe hỏng, kẹt xe hoặc có tai nạn.',
                        style: TextStyle(color: Colors.white, fontSize: 12),
                      ),
                    ],
                  ),
                ),
                ElevatedButton(
                  onPressed: _showReportDialog,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.white,
                    foregroundColor: const Color(0xFFBA1A1A),
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(10),
                    ),
                  ),
                  child: const Text(
                    'Báo sự cố',
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 24),

          // Incident History Section (If any created)
          if (_myIncidents.isNotEmpty) ...[
            const Text(
              'Sự cố đã báo cáo gần đây',
              style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 10),
            for (final inc in _myIncidents)
              Card(
                margin: const EdgeInsets.only(bottom: 10),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                child: ListTile(
                  leading: const CircleAvatar(
                    backgroundColor: Colors.redAccent,
                    child: Icon(Icons.report_problem_rounded, color: Colors.white),
                  ),
                  title: Text(inc['title'].toString(), style: const TextStyle(fontWeight: FontWeight.bold)),
                  subtitle: Text('${inc['desc']}\nThời gian: ${inc['time']}'),
                  trailing: Chip(
                    label: Text(inc['status'].toString(), style: const TextStyle(fontSize: 11)),
                    backgroundColor: Colors.amber.shade100,
                  ),
                ),
              ),
            const SizedBox(height: 16),
          ],

          // Admin Dispatch Feed Section
          const Text(
            'Thông báo điều phối từ Admin',
            style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 12),

          for (final alert in _dispatchAlerts) ...[
            Container(
              margin: const EdgeInsets.only(bottom: 12),
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.grey.shade200),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.02),
                    blurRadius: 6,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: alert['priority'] == 'high'
                          ? Colors.orange.shade50
                          : AppColors.teal.withOpacity(0.1),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(
                      alert['priority'] == 'high'
                          ? Icons.campaign_rounded
                          : Icons.notifications_rounded,
                      color: alert['priority'] == 'high'
                          ? Colors.orange
                          : AppColors.teal,
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Flexible(
                              child: Text(
                                alert['title'].toString(),
                                style: const TextStyle(
                                  fontWeight: FontWeight.bold,
                                  fontSize: 14,
                                ),
                              ),
                            ),
                            Text(
                              alert['time'].toString(),
                              style: const TextStyle(color: Colors.grey, fontSize: 11),
                            ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        Text(
                          alert['content'].toString(),
                          style: const TextStyle(color: Colors.black87, fontSize: 13),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}
