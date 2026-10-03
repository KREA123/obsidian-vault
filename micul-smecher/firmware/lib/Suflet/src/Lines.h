// SOUL's offline personality lines (docs/10-SOUL-MEMORY.md §8): a few hundred hand-written replies, English
// and Romanian, picked by topic, time of day and a little chance. No model, no internet: when SOUL has no AI
// (or no Wi-Fi) and you say hello, thank it, ask how it is or for a joke, it still answers like itself.
// ~10 KB of flash.
#pragma once
#include <stdint.h>

#include <string>

namespace suflet {

enum class LineTopic : uint8_t {
  Hello,
  Morning,
  Night,
  HowAreYou,
  Thanks,
  Joke,
  WhoAreYou,
  Love,
  Sad,
  Bored,
  Compliment,
  Sorry,
  Bye,
  Offline,  // a question it cannot answer without the internet
  Count
};

// mood: 0 any, 1 bright (day), 2 sleepy (late), 3 cheeky. Deterministic for a seed.
const char* pickLine(LineTopic t, bool ro, uint32_t seed, int mood = 0);
int lineCount();                     // the whole table
int lineCount(LineTopic t, bool ro); // lines for one topic (tests)

// Small talk the offline rules can answer: true + the line + a face name ("happy", "love"...).
// hour: local hour 0..23 (-1 unknown) picks morning / night lines and the mood.
bool smallTalk(const std::string& text, bool ro, int hour, uint32_t seed, std::string& say, std::string& face);

}  // namespace suflet
