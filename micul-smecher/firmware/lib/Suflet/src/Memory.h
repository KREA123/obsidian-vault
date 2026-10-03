// SOUL Memory: the owner's portable memory, living ON the device and handed to
// whichever AI is connected ("the AI changes, the soul stays";
// docs/10-SOUL-MEMORY.md).
//
//   facts      typed (person, preference, plan/date, place, note, conversation summary, other), with
//              timestamps, source, importance 1..5 and a slow decay; at most kMax (512), the least worth
//              keeping goes first when full; secrets (passwords, PINs, card numbers, API keys) are refused
//   retrieval  on-device, no embeddings: folded keywords + a small RO/EN synonym table + recency and
//              importance -> the top facts as a compact "What SOUL knows about you" block (~300 tokens)
//              that goes into every AI request (direct Claude / OpenAI, SOUL Cloud, SOUL Bridge)
//   learning   the AI proposes `memory.remember` / `memory.forget` (validated, AiProtocol), the owner says
//              "remember that..." / "ține minte că...", and the offline rules pick up simple facts
//              (birthdays, names, who is who) and answer from memory ("când e ziua Anei?")
//   storage    a compact binary blob; MemoryFlash keeps it in the `soulmem` partition as two A/B slots
//              (CRC-checked, newest wins, only the sectors in use are erased) and the device writes it in
//              batches, never more than once every kMinSaveMs (flash writes glitch the RGB panel)
//
// Hardware-free and transport-free like the rest of lib/Suflet: unit-tested on the PC.
#pragma once
#include <stddef.h>
#include <stdint.h>

#include <string>
#include <vector>

namespace suflet {

enum class FactKind : uint8_t { Person, Preference, Plan, Place, Note, Summary, Other, Count };
const char* factKindName(FactKind k);          // "person" | "preference" | "plan" | "place" | "note" | "summary" | "other"
bool factKindFrom(const char* s, FactKind& k);  // false for an unknown name
enum class FactSrc : uint8_t { User, Ai, Rule, Cloud, Import, Count };
const char* factSrcName(FactSrc s);  // "user" | "ai" | "rules" | "cloud" | "import"

struct Fact {
  uint16_t id = 0;
  FactKind kind = FactKind::Other;
  FactSrc src = FactSrc::User;
  uint8_t importance = 3;  // 1..5
  bool pinned = false;     // the owner said it in so many words: no decay
  uint32_t created = 0;    // local epoch (0 = clock unknown)
  uint32_t used = 0;       // last time it went into an answer
  uint16_t hits = 0;       // how often it was used
  uint16_t mmdd = 0;       // a yearly date (a birthday): month * 100 + day, 0 = none
  std::string subject;     // who / what it is about ("Ana"), may be empty
  std::string text;        // the fact itself, <= kTextMax bytes
};

// One change proposed by an AI (or the cloud): validated before it is applied.
struct MemOp {
  bool forget = false;
  FactKind kind = FactKind::Other;
  uint8_t importance = 3;
  std::string text;  // remember: the fact; forget: a keyword (>= 3 characters)
};

class SoulMemory {
 public:
  static constexpr size_t kMax = 512, kTextMax = 120, kSubjectMax = 32;
  static constexpr size_t kBudgetChars = 1200;  // ~300 tokens for the context block
  // the blob must fit one 64 KB flash slot: 512 facts of ~70 bytes is ~40 KB; very long facts evict sooner
  static constexpr size_t kMaxBytes = 60 * 1024;
  size_t bytes() const;  // the serialised size
  static constexpr uint32_t kMinSaveMs = 20000, kQuietMs = 4000, kMaxDirtyMs = 120000;

  // Add a fact. Returns its id (> 0), or 0 when refused (empty, a secret). The same fact said again
  // refreshes the one kept (and its id is returned); a full memory drops the least worth keeping.
  int remember(const std::string& text, FactKind kind, FactSrc src, uint32_t now, int importance = 3,
               const std::string& subject = "", uint16_t mmdd = 0);
  bool forgetId(int id);
  int forgetMatching(const std::string& keyword);  // every fact containing it (folded); keyword >= 3 chars
  void clear();
  bool undoLast();  // takes back the last remember() (the "Remembered: … · undo" toast)
  int lastRemembered() const { return lastId_; }

  size_t size() const { return facts_.size(); }
  const Fact& at(size_t i) const { return facts_[i]; }
  const Fact* find(int id) const;
  int indexOf(int id) const;
  // newest first; filter = folded substring (empty = all)
  std::vector<int> list(const std::string& filter = "") const;

  // Retrieval: indexes of the k best facts for this question (score > 0 or, with general, the most
  // important / recent ones when nothing matches).
  std::vector<int> rank(const std::string& query, uint32_t now, size_t k, bool general = true) const;
  float score(const Fact& f, const std::string& query, uint32_t now) const;  // for tests and tuning
  // "What SOUL knows about you" for the AI request: "" when the memory is empty.
  std::string contextBlock(const std::string& query, uint32_t now, bool ro, size_t budget = kBudgetChars) const;
  void touch(const std::vector<int>& idx, uint32_t now);  // these went into an answer

  // An AI's remember / forget (MemOp): applied, return the id remembered (0 = none / forgot something)
  int apply(const MemOp& op, FactSrc src, uint32_t now, int* forgotten = nullptr);

  // ---- persistence -------------------------------------------------------------------------------
  std::vector<uint8_t> serialize() const;
  bool deserialize(const uint8_t* p, size_t n);
  std::string exportJson() const;  // {"v":1,"facts":[...]} (what the owner downloads, and the cloud backup)
  // replace = wipe first. Returns how many facts were added (secrets and bad rows are skipped).
  int importJson(const std::string& json, uint32_t now, bool replace);

  // Batched saving: every change marks the memory dirty; the device saves when saveDue() says so.
  bool dirty() const { return dirty_; }
  bool saveDue(uint32_t nowMs) const;
  void markSaved(uint32_t nowMs) {
    dirty_ = false;
    savedMs_ = nowMs;
    everSaved_ = true;
  }
  void savePostponed(uint32_t nowMs) {  // a write failed: try again after kMinSaveMs, still dirty
    savedMs_ = nowMs;
    everSaved_ = true;
  }
  void setClockMs(uint32_t ms) { nowMs_ = ms; }  // the device's millis(): when a change happened
  uint32_t generation() const { return gen_; }    // bumps on every change (the cloud backup follows it)

  bool backup = false;  // optional encrypted backup to the owner's SOUL Cloud account (off by default)
  void setBackup(bool on) {
    backup = on;
    changed();
  }

  // A password, PIN, card number, API key... (never stored, never answered)
  static bool looksSecret(const std::string& text);
  // lower-case ASCII, Romanian / Latin-1 diacritics folded away, punctuation -> spaces
  static std::string fold(const std::string& s);

 private:
  void changed();
  int evictOne();
  std::vector<Fact> facts_;
  uint16_t nextId_ = 1;
  int lastId_ = 0;
  bool lastWasNew_ = false;
  Fact lastBefore_;  // the fact as it was before a refreshing remember (for undo)
  bool dirty_ = false, everSaved_ = false;
  uint32_t gen_ = 0, nowMs_ = 0, dirtySinceMs_ = 0, changedMs_ = 0, savedMs_ = 0;
};

// The offline rules for memory (work with no AI and no internet):
//   "remember that X" / "ține minte că X" / "reține că X"          -> keep X (pinned)
//   "forget X" / "uită X" (but not "forget everything")            -> forget the facts with X
//   statements: "X's birthday is May 12", "ziua Anei e pe 12 mai", "my sister is Ana", "sora mea e Ana",
//               "my name is…", "mă numesc…", "my wifi is called…"    -> kept (with `implicit`)
//   questions: "când e ziua Anei?", "when is my birthday?", "who is Ana?", "what's my wifi name?",
//              "what do you know about me?"                         -> answered from memory
//   secrets ("what's my wifi password?", "remember my PIN is…")      -> a polite no
struct MemoryAnswer {
  std::string say;
  int remembered = 0;  // id of a fact kept now (the toast offers undo)
  int forgotten = 0;
  bool question = false;  // answered from memory
};
// implicit: also keep simple facts said in passing (offline / No AI); explicit commands always work.
// Returns false when the text is not about memory (or a question memory cannot answer).
bool memoryAct(SoulMemory& m, const std::string& text, uint32_t now, bool ro, bool implicit, MemoryAnswer& out);
// "12 May" / "May 12" / "12 mai" / "12.05" / "12/05" -> month * 100 + day (0 = none)
uint16_t parseDayMonth(const std::string& text);
std::string dayMonthText(uint16_t mmdd, bool ro);  // "12 May" / "12 mai"

// The A/B slot store on a raw flash partition. FlashIo is the partition (esp_partition_* on the
// device, a vector in the tests); each half holds one copy: header {magic, version, seq, len, crc}
// + the blob. save() writes the older half: erases only the sectors it needs, writes the blob, then the
// header (a cut in the middle leaves the other copy as the newest valid one).
struct FlashIo {
  virtual ~FlashIo() = default;
  virtual size_t size() const = 0;
  virtual bool read(size_t off, void* dst, size_t n) = 0;
  virtual bool erase(size_t off, size_t n) = 0;  // n a multiple of kSector
  virtual bool write(size_t off, const void* src, size_t n) = 0;
};

class MemoryFlash {
 public:
  static constexpr size_t kSector = 4096, kHeader = 20;
  static constexpr uint32_t kMagic = 0x4D454D53;  // "SMEM"
  explicit MemoryFlash(FlashIo* io) : io_(io) {}
  bool load(SoulMemory& m);  // false: nothing valid stored (m untouched)
  bool save(const SoulMemory& m);
  size_t capacity() const;  // the largest blob one slot holds
  uint32_t seq() const { return seq_; }
  int slot() const { return slot_; }
  uint32_t writes = 0, erasedSectors = 0;  // wear accounting (tests, serial `MEM`)

 private:
  bool readSlot(int s, uint32_t& seq, std::vector<uint8_t>* blob);
  FlashIo* io_;
  uint32_t seq_ = 0;
  int slot_ = -1;  // the slot holding the newest copy
};

uint32_t crc32(const uint8_t* p, size_t n, uint32_t crc = 0);

}  // namespace suflet
