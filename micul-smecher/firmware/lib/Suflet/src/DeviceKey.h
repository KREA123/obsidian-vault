// The SOUL device key (docs/07-CONNECT-AI.md §6.1-6.2): ECDSA P-256.
//
//   private  32-byte scalar d, made on the device with the hardware RNG, never
//            printed, never sent (NVS partition `soulid`, key `priv`)
//   public   65-byte uncompressed SEC1 point 0x04||X||Y; on the wire b64u (87 chars)
//   sign     ECDSA over SHA-256(message), raw r||s (32 + 32 bytes); b64u (86 chars)
//
// On the device this is mbedTLS (ESP-IDF); on the PC (native tests, the
// simulator) OpenSSL's libcrypto. Both produce the same wire format, checked
// in `native` against ai/tests/vectors/device_auth.json.
#pragma once
#include <stddef.h>
#include <stdint.h>

#include <string>

namespace suflet {

struct DeviceKey {
  // a new key pair from the RNG; false if the RNG or the curve failed
  static bool generate(uint8_t priv[32], uint8_t pub[65]);
  static bool publicFrom(const uint8_t priv[32], uint8_t pub[65]);
  static bool sign(const uint8_t priv[32], const uint8_t* msg, size_t n, uint8_t sig[64]);
  static bool verify(const uint8_t pub[65], const uint8_t* msg, size_t n, const uint8_t sig[64]);
  // wire helpers: b64u of the public point / of the signature of `msg`
  static std::string pubB64(const uint8_t pub[65]);
  static std::string signB64(const uint8_t priv[32], const std::string& msg);
  // SHA-256 of `s`, lowercase hex (SOUL Bridge keeps only the hashes of the tokens it issued)
  static std::string sha256Hex(const std::string& s);
  static void wipe(void* p, size_t n);
};

}  // namespace suflet
