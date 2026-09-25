// The alarm's sound, as a pattern in time and nothing else: the board layer
// asks "on or off right now?" and drives whatever it has (the 2.8C's
// on/off buzzer, or a tone into an I2S amplifier). Bursts of four short
// beeps, then a pause; it gives up by itself after `maxS` seconds so a
// forgotten alarm doesn't beep all day. Any touch or the side button stops it.
#pragma once

namespace suflet {

class AlarmTone {
 public:
  static constexpr float kBeepS = 0.10f;   // one beep
  static constexpr float kGapS = 0.10f;    // between beeps
  static constexpr int kBeeps = 4;         // per burst
  static constexpr float kPauseS = 0.60f;  // after a burst
  static constexpr float kPeriodS = kBeeps * (kBeepS + kGapS) + kPauseS;  // 1.4 s
  static constexpr float kToneHz = 2000.0f;  // for a speaker (a buzzer has its own pitch)

  float maxS = 60.0f;

  void start() {
    ringing_ = true;
    t_ = 0;
  }
  void stop() { ringing_ = false; }
  bool ringing() const { return ringing_; }
  float elapsed() const { return t_; }

  // Advances the clock; returns whether the sound is on at the new time.
  bool update(float dt) {
    if (!ringing_) return false;
    t_ += dt;
    if (t_ >= maxS) {
      ringing_ = false;
      return false;
    }
    return on();
  }
  bool on() const {
    if (!ringing_) return false;
    float p = t_;
    while (p >= kPeriodS) p -= kPeriodS;
    if (p >= kBeeps * (kBeepS + kGapS)) return false;
    float q = p;
    while (q >= kBeepS + kGapS) q -= kBeepS + kGapS;
    return q < kBeepS;
  }

 private:
  bool ringing_ = false;
  float t_ = 0;
};

}  // namespace suflet
