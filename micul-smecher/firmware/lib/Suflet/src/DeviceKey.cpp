#include "DeviceKey.h"

#include <string.h>

#include "CloudLink.h"

#if defined(ARDUINO)
// ---------------------------------------------------------------- mbedTLS ---
#include <esp_random.h>
#include <mbedtls/bignum.h>
#include <mbedtls/ecdsa.h>
#include <mbedtls/ecp.h>
#include <mbedtls/sha256.h>

namespace suflet {

namespace {

int rng(void*, unsigned char* out, size_t n) {
  esp_fill_random(out, n);  // a true RNG while the radio is on (the key is made after Wi-Fi starts)
  return 0;
}

struct Curve {
  mbedtls_ecp_group grp;
  mbedtls_mpi d;
  mbedtls_ecp_point q;
  Curve() {
    mbedtls_ecp_group_init(&grp);
    mbedtls_mpi_init(&d);
    mbedtls_ecp_point_init(&q);
  }
  ~Curve() {
    mbedtls_ecp_group_free(&grp);
    mbedtls_mpi_free(&d);
    mbedtls_ecp_point_free(&q);
  }
  bool load() { return mbedtls_ecp_group_load(&grp, MBEDTLS_ECP_DP_SECP256R1) == 0; }
  bool pub(uint8_t out[65]) {
    size_t olen = 0;
    return mbedtls_ecp_mul(&grp, &q, &d, &grp.G, rng, nullptr) == 0 &&
           mbedtls_ecp_point_write_binary(&grp, &q, MBEDTLS_ECP_PF_UNCOMPRESSED, &olen, out, 65) == 0 && olen == 65;
  }
};

}  // namespace

bool DeviceKey::generate(uint8_t priv[32], uint8_t pub[65]) {
  Curve c;
  if (!c.load() || mbedtls_ecp_gen_privkey(&c.grp, &c.d, rng, nullptr) != 0) return false;
  if (mbedtls_mpi_write_binary(&c.d, priv, 32) != 0) return false;
  return c.pub(pub);
}

bool DeviceKey::publicFrom(const uint8_t priv[32], uint8_t pub[65]) {
  Curve c;
  if (!c.load() || mbedtls_mpi_read_binary(&c.d, priv, 32) != 0 || mbedtls_ecp_check_privkey(&c.grp, &c.d) != 0)
    return false;
  return c.pub(pub);
}

bool DeviceKey::sign(const uint8_t priv[32], const uint8_t* msg, size_t n, uint8_t sig[64]) {
  uint8_t hash[32];
  if (mbedtls_sha256(msg, n, hash, 0) != 0) return false;
  Curve c;
  mbedtls_mpi r, s;
  mbedtls_mpi_init(&r);
  mbedtls_mpi_init(&s);
  const bool ok = c.load() && mbedtls_mpi_read_binary(&c.d, priv, 32) == 0 &&
                  mbedtls_ecdsa_sign(&c.grp, &r, &s, &c.d, hash, sizeof hash, rng, nullptr) == 0 &&
                  mbedtls_mpi_write_binary(&r, sig, 32) == 0 && mbedtls_mpi_write_binary(&s, sig + 32, 32) == 0;
  mbedtls_mpi_free(&r);
  mbedtls_mpi_free(&s);
  return ok;
}

bool DeviceKey::verify(const uint8_t pub[65], const uint8_t* msg, size_t n, const uint8_t sig[64]) {
  uint8_t hash[32];
  if (mbedtls_sha256(msg, n, hash, 0) != 0) return false;
  Curve c;
  mbedtls_mpi r, s;
  mbedtls_mpi_init(&r);
  mbedtls_mpi_init(&s);
  const bool ok = c.load() && mbedtls_ecp_point_read_binary(&c.grp, &c.q, pub, 65) == 0 &&
                  mbedtls_mpi_read_binary(&r, sig, 32) == 0 && mbedtls_mpi_read_binary(&s, sig + 32, 32) == 0 &&
                  mbedtls_ecdsa_verify(&c.grp, hash, sizeof hash, &c.q, &r, &s) == 0;
  mbedtls_mpi_free(&r);
  mbedtls_mpi_free(&s);
  return ok;
}

}  // namespace suflet

#else
// ---------------------------------------------------------------- OpenSSL ---
#define OPENSSL_SUPPRESS_DEPRECATED  // the EC_KEY API is the short way to a raw P-256 scalar
#include <openssl/bn.h>
#include <openssl/ec.h>
#include <openssl/ecdsa.h>
#include <openssl/obj_mac.h>
#include <openssl/sha.h>

namespace suflet {

namespace {

EC_KEY* keyFrom(const uint8_t priv[32]) {
  EC_KEY* k = EC_KEY_new_by_curve_name(NID_X9_62_prime256v1);
  BIGNUM* d = BN_bin2bn(priv, 32, nullptr);
  EC_POINT* q = k ? EC_POINT_new(EC_KEY_get0_group(k)) : nullptr;
  const bool ok = k && d && q && EC_KEY_set_private_key(k, d) == 1 &&
                  EC_POINT_mul(EC_KEY_get0_group(k), q, d, nullptr, nullptr, nullptr) == 1 &&
                  EC_KEY_set_public_key(k, q) == 1 && EC_KEY_check_key(k) == 1;
  BN_clear_free(d);
  EC_POINT_free(q);
  if (!ok) {
    EC_KEY_free(k);
    return nullptr;
  }
  return k;
}

bool pubOf(const EC_KEY* k, uint8_t pub[65]) {
  return EC_POINT_point2oct(EC_KEY_get0_group(k), EC_KEY_get0_public_key(k), POINT_CONVERSION_UNCOMPRESSED, pub, 65,
                            nullptr) == 65;
}

}  // namespace

bool DeviceKey::generate(uint8_t priv[32], uint8_t pub[65]) {
  EC_KEY* k = EC_KEY_new_by_curve_name(NID_X9_62_prime256v1);
  const bool ok = k && EC_KEY_generate_key(k) == 1 && BN_bn2binpad(EC_KEY_get0_private_key(k), priv, 32) == 32 &&
                  pubOf(k, pub);
  EC_KEY_free(k);
  return ok;
}

bool DeviceKey::publicFrom(const uint8_t priv[32], uint8_t pub[65]) {
  EC_KEY* k = keyFrom(priv);
  const bool ok = k && pubOf(k, pub);
  EC_KEY_free(k);
  return ok;
}

bool DeviceKey::sign(const uint8_t priv[32], const uint8_t* msg, size_t n, uint8_t sig[64]) {
  uint8_t hash[32];
  SHA256(msg, n, hash);
  EC_KEY* k = keyFrom(priv);
  ECDSA_SIG* s = k ? ECDSA_do_sign(hash, sizeof hash, k) : nullptr;
  const BIGNUM *r = nullptr, *ss = nullptr;
  if (s) ECDSA_SIG_get0(s, &r, &ss);
  const bool ok = s && BN_bn2binpad(r, sig, 32) == 32 && BN_bn2binpad(ss, sig + 32, 32) == 32;
  ECDSA_SIG_free(s);
  EC_KEY_free(k);
  return ok;
}

bool DeviceKey::verify(const uint8_t pub[65], const uint8_t* msg, size_t n, const uint8_t sig[64]) {
  uint8_t hash[32];
  SHA256(msg, n, hash);
  EC_KEY* k = EC_KEY_new_by_curve_name(NID_X9_62_prime256v1);
  EC_POINT* q = k ? EC_POINT_new(EC_KEY_get0_group(k)) : nullptr;
  ECDSA_SIG* s = ECDSA_SIG_new();
  BIGNUM* r = BN_bin2bn(sig, 32, nullptr);
  BIGNUM* ss = BN_bin2bn(sig + 32, 32, nullptr);
  bool ok = k && q && s && r && ss && EC_POINT_oct2point(EC_KEY_get0_group(k), q, pub, 65, nullptr) == 1 &&
            EC_KEY_set_public_key(k, q) == 1 && ECDSA_SIG_set0(s, r, ss) == 1;
  if (ok) r = ss = nullptr;  // owned by s now
  ok = ok && ECDSA_do_verify(hash, sizeof hash, s, k) == 1;
  BN_free(r);
  BN_free(ss);
  ECDSA_SIG_free(s);
  EC_POINT_free(q);
  EC_KEY_free(k);
  return ok;
}

}  // namespace suflet
#endif

namespace suflet {

std::string DeviceKey::pubB64(const uint8_t pub[65]) { return CloudLink::base64url(pub, 65); }

std::string DeviceKey::signB64(const uint8_t priv[32], const std::string& msg) {
  uint8_t sig[64];
  if (!sign(priv, (const uint8_t*)msg.data(), msg.size(), sig)) return std::string();
  return CloudLink::base64url(sig, sizeof sig);
}

void DeviceKey::wipe(void* p, size_t n) {
  volatile uint8_t* v = (volatile uint8_t*)p;
  for (size_t i = 0; i < n; ++i) v[i] = 0;
}

}  // namespace suflet
