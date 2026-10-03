// Three tiny games for the round glass (os/APPS.md §Games), the rules and the
// physics only; SoulOS draws them (OsApps*.cpp) and the eyes play along.
//
//   TiltBall   tilt SOUL: a glass marble rolls in the round arena (gravity
//              from the IMU, rolling friction, a bouncy rim); collect the
//              stars, keep away from the two dark holes. 45 s, 3 lives.
//   Rhythm     rings swell from the eyes to the rim on the beat; tap when one
//              reaches the rim. Perfect +-70 ms, good +-150 ms.
//   EyeMemory  "Simon" with the eyes: they look at 4 places on the rim in a
//              sequence, one longer each round; tap them back in order.
//
// Deterministic (a seeded RNG), transport-free, tested on the PC.
#pragma once
#include <stdint.h>

#include <vector>

namespace suflet {
namespace games {

struct Rand {
  uint32_t s = 0x2545F491u;
  uint32_t next() {
    s ^= s << 13;
    s ^= s >> 17;
    s ^= s << 5;
    return s;
  }
  float uniform(float a, float b) { return a + (b - a) * (next() % 100000) / 100000.0f; }
};

// ------------------------------------------------------------ tilt ball ---
class TiltBall {
 public:
  static constexpr float kArena = 196;   // arena radius (design px, centred on the disc)
  static constexpr float kBall = 17, kStar = 15, kHole = 21;
  static constexpr float kTime = 45;
  struct Star {
    float x, y;
  };
  struct Hole {
    float x, y;
  };
  void start(uint32_t seed);
  // gx, gy: gravity in the screen plane (g; +x = right, +y = down); dt seconds. Returns events this step.
  enum Event : uint8_t { None = 0, Got = 1, Bump = 2, Fell = 4, Over = 8 };
  uint8_t step(float dt, float gx, float gy);
  bool running() const { return run_; }
  bool over() const { return over_; }
  float x() const { return x_; }
  float y() const { return y_; }
  float vx() const { return vx_; }
  float vy() const { return vy_; }
  int score() const { return score_; }
  int lives() const { return lives_; }
  float left() const { return left_; }
  const Star& star() const { return star_; }
  const std::vector<Hole>& holes() const { return holes_; }
  float speed() const;

 private:
  void placeStar();
  Rand r_;
  float x_ = 0, y_ = 0, vx_ = 0, vy_ = 0, left_ = 0, safe_ = 0;
  int score_ = 0, lives_ = 3;
  bool run_ = false, over_ = false;
  Star star_{0, 0};
  std::vector<Hole> holes_;
};

// --------------------------------------------------------------- rhythm ---
class Rhythm {
 public:
  static constexpr float kTravel = 1.6f;  // seconds from the eyes to the rim
  static constexpr int kBeats = 32;
  static constexpr float kPerfect = 0.07f, kGood = 0.15f;
  enum Judge : uint8_t { NoBeat, Perfect, Good, Miss };
  void start(uint32_t seed, float bpm = 100);
  // returns how many beats went by untapped (misses) in this step
  int step(float dt);
  Judge tap();  // a tap anywhere: judged against the nearest beat
  bool running() const { return run_; }
  bool over() const { return over_; }
  float t() const { return t_; }
  int score() const { return score_; }
  int combo() const { return combo_; }
  int best() const { return bestCombo_; }
  int perfects() const { return perfects_; }
  int misses() const { return misses_; }
  // the beats on screen: radius fraction 0 (at the eyes) .. 1 (at the rim) for each live beat
  int visible(float* fracs, int max) const;
  Judge lastJudge() const { return last_; }

 private:
  std::vector<float> beats_;  // hit times
  std::vector<uint8_t> done_;
  float t_ = 0;
  int score_ = 0, combo_ = 0, bestCombo_ = 0, perfects_ = 0, misses_ = 0;
  bool run_ = false, over_ = false;
  Judge last_ = NoBeat;
};

// ----------------------------------------------------------- eye memory ---
class EyeMemory {
 public:
  static constexpr int kSpots = 4;  // 0 top, 1 right, 2 bottom, 3 left
  static constexpr float kOn = 0.55f, kGap = 0.22f;
  enum class Phase : uint8_t { Idle, Show, Input, Over };
  void start(uint32_t seed);
  void step(float dt);
  // the spot the eyes look at now while showing (-1 = between cues)
  int cue() const;
  // a tap on spot k while it is your turn: true if it was right
  bool input(int spot);
  Phase phase() const { return phase_; }
  int round() const { return (int)seq_.size(); }
  int score() const { return score_; }  // rounds completed
  int progress() const { return pos_; }
  const std::vector<uint8_t>& sequence() const { return seq_; }
  static int spotAt(float dx, float dy);  // a tap (relative to the centre) -> the nearest spot

 private:
  void grow();
  Rand r_;
  std::vector<uint8_t> seq_;
  int pos_ = 0, score_ = 0;
  float t_ = 0;
  Phase phase_ = Phase::Idle;
};

}  // namespace games
}  // namespace suflet
