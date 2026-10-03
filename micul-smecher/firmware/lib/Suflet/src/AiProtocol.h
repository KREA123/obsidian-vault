// SOUL's AI protocol, the same one the web SoulOS speaks (os/index.html,
// "the brain"): whoever answers (Claude, ChatGPT, our relay or the on-device
// rules), the answer is one small JSON object
//
//   {"say": "<what SOUL says>", "face": "<optional>", "actions": [<0..3>]}
//
// with five actions, validated strictly before the device acts on them:
//   {"type": "alarm.set", "time": "HH:MM", "label": "...", "repeat": "once|daily|weekdays|weekend"}
//   {"type": "timer.start", "minutes": 1..180}
//   {"type": "reminder.create", "time": "HH:MM", "day": "today|tomorrow", "text": "..."}
//   {"type": "note.create", "text": "..."}
//   {"type": "focus.start", "minutes": 5..120}
// Unknown types, extra keys, bad times and out-of-range numbers are dropped
// (and counted). Transport-free: this file builds request bodies and parses
// response bodies; the device does the HTTPS (src/net.cpp), the simulator
// and the tests feed recorded bodies.
#pragma once
#include <stddef.h>
#include <stdint.h>

#include <string>
#include <vector>

namespace suflet {

enum class AiMode : uint8_t { None, Claude, ChatGpt, Cloud };  // Offline · your Claude key · your OpenAI key · SOUL Cloud
const char* aiModeName(AiMode m);  // "none" | "claude" | "chatgpt" | "cloud"
AiMode aiModeFrom(const char* s);

enum class AiErr : uint8_t {
  None,
  NoKey,        // no API key / relay URL configured
  BadKey,       // 401 / 403
  RateLimited,  // 429
  Quota,        // out of credit (OpenAI insufficient_quota, Anthropic billing 402)
  Refused,      // stop_reason "refusal"
  Offline,      // no Wi-Fi
  Network,      // DNS / TCP / TLS failed
  Timeout,
  Upstream,     // 5xx, 529 overloaded, unreadable answer
  Truncated,    // stop_reason "max_tokens"
  Count
};
const char* aiErrCode(AiErr e);                 // "bad_key" ...
const char* aiErrText(AiErr e, bool ro);        // one short line that says what to do

struct AiAction {
  enum Type : uint8_t { AlarmSet, TimerStart, ReminderCreate, NoteCreate, FocusStart } type = AlarmSet;
  uint8_t hour = 0, minute = 0;
  uint8_t days = 0;        // alarm repeat as a weekday mask (bit 0 = Monday), 0 = once
  uint16_t minutes = 0;    // timer / focus
  bool tomorrow = false;   // reminder
  uint32_t when = 0;       // reminder at an absolute local time (SOUL Cloud pushes); 0 = hour/minute/tomorrow
  uint32_t seconds = 0;    // timer in seconds (SOUL Cloud pushes); 0 = minutes
  std::string text;        // reminder / note text, alarm label
};

struct AiReply {
  std::string say;
  std::string face;  // "" = none; one of the 10 allowed faces
  std::vector<AiAction> actions;
  int rejected = 0;   // actions dropped by the validation
  bool loose = false;  // not a JSON object: plain text was shown instead
};

// The web parseReply(): JSON (or JSON inside ``` fences / extra text), strict
// action validation, at most three actions. Never fails: plain text becomes say.
AiReply parseReply(const char* raw, size_t n);
inline AiReply parseReply(const std::string& s) { return parseReply(s.data(), s.size()); }

// What the device knows right now, for the standing instructions.
struct AiContext {
  std::string name = "SOUL";
  bool ro = false;            // Romanian UI
  uint32_t now = 0;           // local epoch seconds (0 = unknown)
  std::string alarms;         // "07:30 weekdays \"Gym\" on; ..." or ""
  std::string reminders;      // "17:00 \"Call the bank\"; ..." or ""
  int timerLeftMin = -1;      // countdown minutes left, -1 = none
  int notes = 0;
};
std::string systemPrompt(const AiContext& c);
std::string formatNow(uint32_t localEpoch, bool ro);  // "Friday 2 October 2026, 18:30"

struct ChatTurn {
  bool user;
  std::string text;
};

struct AiConfig {
  AiMode mode = AiMode::None;
  std::string anthropicKey, openaiKey;
  std::string claudeModel = "claude-opus-5-5";
  std::string claudeEffort = "low";  // Opus 5.5 cannot disable thinking; low keeps answers quick
  std::string openaiModel = "gpt-6-luna";  // docs/07 §1.3: the fast, cheap tier for a companion device
  std::string relayUrl, relayToken;  // e.g. https://soul.example.eu + Bearer token
  std::string deviceId;              // relay device id ([A-Za-z0-9_-]{1,64})
  bool useSchema = true;             // Claude structured outputs (output_config.format)
  int maxTokens = 2048;
};

struct HttpRequest {
  std::string url;
  std::vector<std::pair<std::string, std::string>> headers;  // never logged: carries the key
  std::string body;
  uint32_t timeoutMs = 25000;
};

// Build the HTTPS request for one question. Returns AiErr::NoKey when the
// mode needs a key / URL that is not set (nothing to send).
AiErr buildRequest(const AiConfig& cfg, const AiContext& ctx, const std::vector<ChatTurn>& history,
                   const std::string& text, HttpRequest& out);

// Parse the HTTP answer. status < 0 = transport error (see netErr).
struct AiOutcome {
  AiErr err = AiErr::None;
  AiReply reply;
  std::string raw;            // the model's raw text (kept in the chat history)
  bool schemaRejected = false;  // 400 about output_config.format: retry without it
  int httpStatus = 0;
  AiErr note = AiErr::None;  // SOUL Cloud answered with its rules and says why (reply.note: bad_key, allowance...)
  bool noLocal = false;      // do not run the on-device rules (a cloud turn may still be acting: timeout)
};
AiOutcome parseResponse(const AiConfig& cfg, int status, const char* body, size_t n, AiErr netErr = AiErr::None,
                        uint32_t localNow = 0);

// Retry policy: delay before the next attempt (ms), or -1 = give up.
int retryDelayMs(const AiOutcome& o, int attempt);

// The on-device rules: work with no AI, and catch what they can when the AI
// is unreachable (times, alarms, reminders, timers). Returns false when the
// text has nothing they understand.
bool localAct(const std::string& text, uint32_t localNow, bool ro, AiReply& out);
// "No AI" (or AI failed): localAct, else keep the text as a note.
AiReply localReply(const std::string& text, uint32_t localNow, bool ro, bool noAiMode);
std::string cleanLabel(const std::string& text);
// web cleanStr(): control characters -> spaces, collapsed whitespace, cut at maxCp code points
std::string cleanText(const char* s, size_t maxCp);
// "HH:MM" (24 h) -> true + hour/minute
bool parseHhmm(const char* s, int& h, int& m);
// "YYYY-MM-DDTHH:MM[:SS]" local wall time -> local epoch seconds (0 = unreadable)
uint32_t parseLocalStamp(const char* s);

// Masked secret for the screen: "sk-ant-…a1B2".
std::string maskKey(const std::string& k);
bool keyLooksValid(AiMode m, const std::string& k);

}  // namespace suflet
