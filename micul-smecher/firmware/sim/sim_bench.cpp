// The non-frame work, measured the same way as the frames (firmware/PERF.md, tools/perf_bench.py):
//
//   program <out_dir> bench_json     SOUL Cloud's socket frames (the recorded session) + Claude answers, parsed
//   program <out_dir> bench_memory   SOUL Memory: 200 facts, ranked for 50 questions, the context block built
//   program <out_dir> bench_wifi     the roamer: 40 scans of 30 access points against 8 saved networks
//   program <out_dir> bench_boot     SoulOS begin + the first frame, as the device boots (the aura deferred)
//
//   valgrind --tool=callgrind --toggle-collect='suflet_bench_*' program out bench_json
// Each prints `MICRO <name> ops=<n>`: the per-op cost is the collected instructions / n.
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "../test/test_suflet/cloud_frames.h"
#include "AiProtocol.h"
#include "Alarms.h"
#include "CloudLink.h"
#include "EyeRig.h"
#include "Frame.h"
#include "Memory.h"
#include "Os.h"
#include "WifiRoam.h"

using namespace suflet;

namespace {

std::string claudeAnswer(const char* json) {
  std::string esc;
  for (const char* p = json; *p; ++p) {
    if (*p == '"' || *p == '\\') esc += '\\';
    esc += *p;
  }
  return "{\"id\":\"msg_sim\",\"type\":\"message\",\"role\":\"assistant\",\"model\":\"claude-opus-5-5\",\"content\":["
         "{\"type\":\"text\",\"text\":\"" + esc +
         "\"}],\"stop_reason\":\"end_turn\",\"usage\":{\"input_tokens\":1200,\"output_tokens\":64}}";
}

}  // namespace

extern "C" __attribute__((noinline)) int suflet_bench_json(int rounds) {
  int msgs = 0;
  AiConfig ai;
  ai.mode = AiMode::Claude;
  ai.anthropicKey = "sk-ant-sim-0000000000000000000000";
  const std::string body = claudeAnswer(
      "{\"say\":\"Done: I'll wake you at 7:30 and remind you to call the bank at 10.\",\"face\":\"happy\","
      "\"actions\":[{\"type\":\"alarm\",\"hhmm\":\"07:30\"},{\"type\":\"reminder\",\"text\":\"call the bank\","
      "\"when\":\"2026-10-05T10:00\"}]}");
  for (int r = 0; r < rounds; ++r) {
    CloudLink link;
    for (const RecordedFrame& f : kRecordedFrames) {
      link.feed(f.json, strlen(f.json));
      ++msgs;
    }
    const AiOutcome o = parseResponse(ai, 200, body.data(), body.size(), AiErr::None, 1790359080u);
    msgs += o.err == AiErr::None ? 1 : 0;
  }
  return msgs;
}

extern "C" __attribute__((noinline)) int suflet_bench_memory(SoulMemory& m, int queries) {
  static const char* kQ[] = {"when is Ana's birthday?", "what do I like for breakfast", "where do I work",
                             "remind me what the doctor said", "cine e sora mea?", "what's my plan for saturday"};
  int hits = 0;
  for (int i = 0; i < queries; ++i) {
    const std::string q = kQ[i % 6];
    hits += (int)m.rank(q, 1790359080u, 5).size();
    hits += (int)m.contextBlock(q, 1790359080u, false).size() > 0;
  }
  return hits;
}

extern "C" __attribute__((noinline)) int suflet_bench_wifi(WifiRoamer& r, const std::vector<ScanHit>& hits, int scans) {
  int joins = 0;
  uint32_t now = 1000;
  for (int i = 0; i < scans; ++i) {
    r.kick(now);
    RoamCmd c = r.tick(now, false, 0);
    if (c.kind == RoamCmd::Scan) r.scanDone(now + 1500, hits);
    c = r.tick(now + 1600, false, 0);
    if (c.kind == RoamCmd::Join) {
      ++joins;
      r.joinFailed(now + 1700, JoinFail::NotFound);
    }
    now += 5000;
  }
  return joins;
}

extern "C" __attribute__((noinline)) int suflet_bench_boot(Os& os, FrameComposer& comp, const BirthInfo& b) {
  os.begin(displays::kLcd28, b);
  const Rect r = comp.compose(os);
  return r.w();
}

int microBench(const std::string& which) {
  int ops = 0;
  if (which == "bench_json") {
    ops = 50;
    printf("parsed %d messages\n", suflet_bench_json(ops));
  } else if (which == "bench_memory") {
    SoulMemory m;
    static const char* kWho[] = {"Ana", "Mihai", "Ioana", "the doctor", "Bogdan", "grandma"};
    char t[160];
    for (int i = 0; i < 200; ++i) {
      snprintf(t, sizeof t, "%s %s %d: %s", kWho[i % 6], i % 3 ? "likes" : "said", i,
               i % 4 ? "coffee with oat milk in the morning" : "the appointment is on saturday at noon");
      m.remember(t, i % 5 ? FactKind::Preference : FactKind::Person, FactSrc::User, 1790000000u + (uint32_t)i * 600);
    }
    ops = 50;
    printf("%d facts, %d hits\n", (int)m.size(), suflet_bench_memory(m, ops));
  } else if (which == "bench_wifi") {
    WifiBook book;
    const char* kSaved[] = {"Acasa", "Birou", "Ana’s iPhone", "Hotel Lobby", "Bunica", "Cafenea", "Sala", "Mama"};
    for (int i = 0; i < 8; ++i) {
      WifiNet n;
      n.ssid = kSaved[i];
      n.pass = "parola1234";
      n.kind = i == 2 ? WifiKind::Hotspot : WifiKind::Other;
      book.add(n);
    }
    std::vector<ScanHit> hits;
    for (int i = 0; i < 30; ++i) {
      ScanHit h;
      char s[40];
      snprintf(s, sizeof s, i == 17 ? "ana's iphone" : "Neighbour-%02d", i);
      h.ssid = s;
      h.rssi = -45 - i * 2;
      hits.push_back(h);
    }
    WifiRoamer r;
    r.setBook(&book);
    ops = 40;
    printf("%d joins tried\n", suflet_bench_wifi(r, hits, ops));
  } else if (which == "bench_boot") {
    Alarms alarms;
    Os os(&alarms);
    os.settings().booted = 1;
    os.setDeferGlass(true);  // as the device boots (1.8): the aura is built over the first frames
    std::vector<uint16_t> fb(480 * 480);
    Canvas cv(480, 480, fb.data());
    FrameComposer comp(&cv);
    const uint8_t mac[6] = {0xC0, 0xFF, 0xEE, 0x12, 0x34, 0x56};
    BirthInfo b;
    b.design = eyes::rollFromMac(mac).design;
    b.chip = "C0:FF:EE:12:34:56";
    b.seed = eyes::hashStr(eyes::kDesigns[b.design].id) ^ 0x5eed;
    ops = 1;
    printf("first frame %d px wide\n", suflet_bench_boot(os, comp, b));
  }
  printf("MICRO %s ops=%d\n", which.c_str(), ops);
  return 0;
}
