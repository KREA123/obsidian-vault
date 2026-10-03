#include "QrImage.h"

#include "QrEncode.h"

namespace suflet {

bool QrImage::make(const std::string& text) {
  if (text == text_ && size_) return true;
  size_ = 0;
  bits_.clear();
  text_.clear();
  // byte-mode capacity at ECC M, versions 1..10 (ISO/IEC 18004 table 7)
  static const uint16_t kCap[10] = {14, 26, 42, 62, 84, 106, 122, 152, 180, 213};
  int version = 0;
  for (int v = 1; v <= 10; ++v)
    if (text.size() <= kCap[v - 1]) {
      version = v;
      break;
    }
  if (!version || text.empty()) return false;
  std::vector<uint8_t> buf(qrcode_getBufferSize((uint8_t)version));
  QRCode q;
  if (qrcode_initBytes(&q, buf.data(), (uint8_t)version, ECC_MEDIUM, (uint8_t*)text.data(), (uint16_t)text.size()) != 0)
    return false;
  size_ = q.size;
  bits_.assign((size_t)size_ * size_, 0);
  for (int y = 0; y < size_; ++y)
    for (int x = 0; x < size_; ++x) bits_[(size_t)(y * size_ + x)] = qrcode_getModule(&q, (uint8_t)x, (uint8_t)y) ? 1 : 0;
  text_ = text;
  return true;
}

}  // namespace suflet
