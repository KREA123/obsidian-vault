// A QR code as a module grid, for the screens that hand something to a
// phone camera: the SOUL Cloud pairing link and the setup Wi-Fi (the
// "WIFI:T:WPA;S:...;P:...;;" form that iOS and Android cameras join).
// Wraps the vendored encoder (QrEncode, MIT) with the capacity check it
// lacks: text that does not fit a version would overrun its buffers.
#pragma once
#include <stdint.h>

#include <string>
#include <vector>

namespace suflet {

class QrImage {
 public:
  // ECC level M, the smallest version 1..10 that holds `text` (byte mode).
  // false (and empty) when it is longer than 213 bytes.
  bool make(const std::string& text);
  bool empty() const { return size_ == 0; }
  int size() const { return size_; }  // modules per side (21, 25 ... 57)
  bool at(int x, int y) const {
    return x >= 0 && y >= 0 && x < size_ && y < size_ && bits_[(size_t)(y * size_ + x)];
  }
  const std::string& text() const { return text_; }

 private:
  int size_ = 0;
  std::vector<uint8_t> bits_;
  std::string text_;
};

}  // namespace suflet
