/// Repository cho ví CTUPay — hiện MVP dùng dữ liệu test/seed, không có nạp tiền thật
/// (theo "Điều kiện quyết định trước ngày 1", mục 2: chủ sản phẩm xác nhận ví điểm là dữ liệu test).
class WalletRepository {
  // TODO: khi backend có endpoint ví (ledger), thêm:
  // Future<int> fetchBalance();
  // Future<void> deposit(int amount);
  // Future<void> withdraw(int amount);
  // Hiện tại home_screen.dart vẫn dùng _balance local — sẽ nối vào đây sau.
}
