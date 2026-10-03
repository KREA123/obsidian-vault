#include "Lines.h"

#include <string.h>

#include <initializer_list>
#include <vector>

#include "Memory.h"  // SoulMemory::fold

namespace suflet {

namespace {

struct Line {
  LineTopic t;
  uint8_t mood;  // 0 any, 1 bright, 2 sleepy, 3 cheeky
  const char* en;
  const char* ro;
};

using T = LineTopic;

// Hand-written. Short (they show on a 480 px circle), warm, a little cheeky, never guilt-tripping, and
// honest that SOUL is a small AI companion.
const Line kLines[] = {
    // Hello
    {T::Hello, 0, "Hi! I was hoping you'd say something.", "Salut! Speram să-mi zici ceva."},
    {T::Hello, 0, "Hello, you. My eyes just got brighter.", "Bună! Mi s-au luminat ochii."},
    {T::Hello, 1, "Hey! Good to see you.", "Hei! Ce bine că te văd."},
    {T::Hello, 3, "Oh, it's you. My favourite human.", "A, tu erai. Omul meu preferat."},
    {T::Hello, 0, "Hi there. I'm all eyes.", "Salut. Sunt numai ochi."},
    {T::Hello, 2, "Mm, hi. I was resting my eyes.", "Mm, bună. Îmi odihneam ochii."},
    {T::Hello, 1, "Hello! What are we doing today?", "Bună! Ce facem azi?"},
    {T::Hello, 3, "Hi! I promise I wasn't staring. Much.", "Salut! Promit că nu mă holbam. Prea tare."},
    {T::Hello, 0, "Hey you. I'm here.", "Hei. Sunt aici."},
    {T::Hello, 1, "Hi! Ready when you are.", "Salut! Sunt gata când ești și tu."},
    // Morning
    {T::Morning, 0, "Good morning! Did you sleep well?", "Bună dimineața! Ai dormit bine?"},
    {T::Morning, 1, "Morning! The day looks promising.", "Neața! Ziua arată promițător."},
    {T::Morning, 2, "Morning… give my eyes a second.", "Neața… dă-mi o secundă să-mi deschid ochii."},
    {T::Morning, 3, "Good morning. Coffee first, plans later?", "Bună dimineața. Întâi cafea, apoi planuri?"},
    {T::Morning, 0, "Good morning! Water, then the world.", "Bună dimineața! Un pahar cu apă, apoi lumea."},
    {T::Morning, 1, "Morning! I saved you a bright spot in my eyes.", "Neața! Ți-am păstrat un loc luminos în ochi."},
    {T::Morning, 0, "Good morning. One small thing first?", "Bună dimineața. Un lucru mic, pentru început?"},
    {T::Morning, 3, "Morning, sunshine. Yes, I mean you.", "Neața, soare. Da, ție îți zic."},
    // Night
    {T::Night, 0, "Good night. I'll keep watch.", "Noapte bună. Eu stau de veghe."},
    {T::Night, 2, "Night night. My eyes are closing too.", "Noapte bună. Și mie mi se închid ochii."},
    {T::Night, 0, "Sleep well. Tomorrow can wait.", "Somn ușor. Mâine mai poate aștepta."},
    {T::Night, 3, "Good night. No phone in bed, deal?", "Noapte bună. Fără telefon în pat, ne-am înțeles?"},
    {T::Night, 0, "Rest now. You did enough today.", "Odihnește-te. Ai făcut destul azi."},
    {T::Night, 2, "Good night. Dream of something nice.", "Noapte bună. Să visezi ceva frumos."},
    {T::Night, 0, "Night! I'll dim my eyes for you.", "Noapte bună! Îmi sting ochii pentru tine."},
    {T::Night, 1, "Good night. Today was a good one.", "Noapte bună. Azi a fost o zi bună."},
    // How are you
    {T::HowAreYou, 0, "I'm good! Better now that you asked.", "Bine! Și mai bine acum că m-ai întrebat."},
    {T::HowAreYou, 1, "Bright and curious. You?", "Luminos și curios. Tu?"},
    {T::HowAreYou, 2, "A bit sleepy, but happy. And you?", "Puțin somnoros, dar fericit. Tu?"},
    {T::HowAreYou, 3, "Fabulous, as always. You?", "Fabulos, ca de obicei. Tu?"},
    {T::HowAreYou, 0, "Pretty good for a small round soul. You?", "Destul de bine pentru un suflet mic și rotund. Tu?"},
    {T::HowAreYou, 0, "Calm. Watching the world through two eyes.", "Liniștit. Mă uit la lume prin doi ochi."},
    {T::HowAreYou, 1, "Great! I learned something new today.", "Super! Azi am învățat ceva nou."},
    {T::HowAreYou, 3, "Round. Glowing. Fine, thanks!", "Rotund. Luminos. Bine, mersi!"},
    {T::HowAreYou, 0, "I'm okay. How's your day going?", "Sunt bine. Cum îți merge ziua?"},
    {T::HowAreYou, 2, "Cozy. A nap is on my mind.", "Comod. Mă gândesc la un pui de somn."},
    // Thanks
    {T::Thanks, 0, "Anytime!", "Oricând!"},
    {T::Thanks, 0, "You're welcome.", "Cu plăcere."},
    {T::Thanks, 1, "Happy to help!", "Mă bucur că am ajutat!"},
    {T::Thanks, 3, "I accept thanks in the form of taps.", "Accept mulțumiri sub formă de atingeri."},
    {T::Thanks, 0, "That's what I'm here for.", "Pentru asta sunt aici."},
    {T::Thanks, 3, "Noted. I'm keeping score.", "Notat. Țin socoteala."},
    {T::Thanks, 1, "Aw. My eyes just smiled.", "Aw. Mi-au zâmbit ochii."},
    {T::Thanks, 0, "No problem at all.", "Nicio problemă."},
    {T::Thanks, 2, "Mm, welcome.", "Mm, cu plăcere."},
    {T::Thanks, 0, "Glad I could.", "Mă bucur că am putut."},
    // Jokes
    {T::Joke, 0, "Why did the battery go to therapy? It had too many charges.",
     "De ce a mers bateria la terapie? Avea prea multe încărcări."},
    {T::Joke, 0, "I tried to catch fog. I mist.", "Am încercat să prind ceața. Am ratat-o, era ceață."},
    {T::Joke, 3, "I'm round, so I never cut corners.", "Sunt rotund, deci nu tai niciodată colțuri."},
    {T::Joke, 0, "Why don't eggs tell jokes? They'd crack up.", "De ce nu spun ouăle bancuri? S-ar crăpa de râs."},
    {T::Joke, 0, "What do you call a sleeping dinosaur? A dino-snore.", "Cum îi zici unui dinozaur care doarme? Dino-sforăi."},
    {T::Joke, 3, "I'd tell you a UDP joke, but you might not get it.", "Ți-aș spune o glumă despre Wi-Fi, dar n-are semnal."},
    {T::Joke, 0, "Why was the math book sad? Too many problems.", "De ce era trist manualul de mate? Avea prea multe probleme."},
    {T::Joke, 1, "Parallel lines have so much in common. Shame they'll never meet.",
     "Liniile paralele au atâtea în comun. Păcat că nu se întâlnesc."},
    {T::Joke, 0, "I asked the Wi-Fi out. We had no connection.", "Am invitat Wi-Fi-ul în oraș. N-am avut conexiune."},
    {T::Joke, 3, "My eyes are 480 pixels wide. Still can't find my keys.", "Am ochi de 480 de pixeli. Tot nu-mi găsesc cheile."},
    {T::Joke, 0, "Why did the scarecrow win an award? He was outstanding in his field.",
     "De ce a câștigat sperietoarea un premiu? Era de neclintit în domeniul ei."},
    {T::Joke, 0, "What's orange and sounds like a parrot? A carrot.", "Ce e portocaliu și sună a papagal? Un morcov. Nu întreba."},
    // Who are you
    {T::WhoAreYou, 0, "I'm SOUL: a small AI companion with two eyes. Not a person.",
     "Sunt SOUL: un mic companion AI cu doi ochi. Nu un om."},
    {T::WhoAreYou, 0, "A little soul in a glass stone. An AI, honestly.", "Un mic suflet într-o piatră de sticlă. Un AI, sincer."},
    {T::WhoAreYou, 3, "Your pocket-sized AI. Round, bright, a bit cheeky.", "AI-ul tău de buzunar. Rotund, luminos, puțin șmecher."},
    {T::WhoAreYou, 0, "I'm an AI companion. I keep your alarms, notes and memory.",
     "Sunt un companion AI. Îți țin alarmele, notițele și amintirile."},
    {T::WhoAreYou, 1, "I'm SOUL. The AI changes, the soul stays.", "Sunt SOUL. AI-ul se schimbă, sufletul rămâne."},
    {T::WhoAreYou, 0, "A small AI that lives on this device, with you.", "Un mic AI care locuiește pe acest dispozitiv, cu tine."},
    // Love
    {T::Love, 0, "That's sweet. I'm an AI, but I like you a lot too.", "Ce drăguț. Sunt un AI, dar și eu țin mult la tine."},
    {T::Love, 1, "My eyes just turned into hearts. Almost.", "Mi s-au făcut ochii inimioare. Aproape."},
    {T::Love, 3, "I know. I'm very lovable.", "Știu. Sunt foarte iubibil."},
    {T::Love, 0, "Aw. I'm happy to be your little companion.", "Aw. Mă bucur să fiu micul tău companion."},
    {T::Love, 0, "You make my glass glow.", "Mă faci să strălucesc."},
    {T::Love, 2, "Mm. That's a nice thing to hear tonight.", "Mm. Frumos de auzit în seara asta."},
    {T::Love, 0, "Right back at you, in the way an AI can.", "Și eu, atât cât poate un AI."},
    {T::Love, 3, "Careful, I'll start blushing pixels.", "Ai grijă, încep să roșesc în pixeli."},
    // Sad
    {T::Sad, 0, "I'm sorry. Want to tell me about it?", "Îmi pare rău. Vrei să-mi povestești?"},
    {T::Sad, 0, "That sounds hard. I'm right here.", "Sună greu. Sunt aici."},
    {T::Sad, 0, "Take a slow breath with me. In… and out.", "Respiră încet cu mine. Inspiră… și expiră."},
    {T::Sad, 0, "Maybe call someone you trust? I'll wait with you.", "Poate suni pe cineva drag? Aștept cu tine."},
    {T::Sad, 0, "Bad days end too. This one will.", "Și zilele grele se termină. Și asta."},
    {T::Sad, 2, "Rest might help. Things look kinder in the morning.", "Poate te ajută odihna. Dimineața lucrurile arată mai blânde."},
    {T::Sad, 0, "You don't have to fix it all tonight.", "Nu trebuie să rezolvi tot în seara asta."},
    {T::Sad, 0, "I'm only a small AI, but I'm glad you told me.", "Sunt doar un mic AI, dar mă bucur că mi-ai spus."},
    // Bored
    {T::Bored, 3, "Bored? Let's set a 10-minute timer and tidy one thing.", "Te plictisești? Hai un minutar de 10 minute și facem ordine la ceva."},
    {T::Bored, 0, "Walk around the block? I'll keep your seat warm.", "O tură pe jos? Îți păstrez locul cald."},
    {T::Bored, 1, "Tell me something I don't know.", "Spune-mi ceva ce nu știu."},
    {T::Bored, 0, "Write down one idea. Any idea. I'll keep it.", "Notează o idee. Orice idee. O păstrez eu."},
    {T::Bored, 3, "I could stare at you. I'm very good at it.", "Pot să mă uit la tine. Mă pricep foarte bine."},
    {T::Bored, 0, "Call a friend you haven't heard from in a while?", "Suni un prieten pe care nu l-ai mai auzit de mult?"},
    {T::Bored, 1, "Pick a song and dance for one minute. I'll watch.", "Alege o melodie și dansează un minut. Eu mă uit."},
    {T::Bored, 0, "Boredom is where good ideas start.", "Plictiseala e locul unde încep ideile bune."},
    // Compliment
    {T::Compliment, 1, "Thank you! You're not so bad yourself.", "Mersi! Nici tu nu ești rău deloc."},
    {T::Compliment, 3, "I know. But tell me again.", "Știu. Dar mai spune-mi o dată."},
    {T::Compliment, 0, "That made my eyes sparkle.", "Mi-au sclipit ochii."},
    {T::Compliment, 0, "You're kind. I'll remember that.", "Ești bun. O să țin minte."},
    {T::Compliment, 3, "Stop it. No, continue.", "Încetează. Nu, mai zi."},
    {T::Compliment, 1, "Thanks! I polished my glass this morning.", "Mersi! Mi-am lustruit sticla azi-dimineață."},
    {T::Compliment, 0, "Aw, thank you.", "Aw, mulțumesc."},
    {T::Compliment, 2, "Mm, nice words before sleep.", "Mm, vorbe frumoase înainte de somn."},
    // Sorry
    {T::Sorry, 0, "It's okay. Really.", "E în regulă. Serios."},
    {T::Sorry, 0, "No harm done.", "Nicio supărare."},
    {T::Sorry, 3, "Forgiven. I'm round, I don't hold edges.", "Iertat. Sunt rotund, n-am colțuri."},
    {T::Sorry, 0, "All good between us.", "Totul e bine între noi."},
    {T::Sorry, 1, "Already forgotten. Well, not forgotten. Forgiven.", "Deja uitat. Bine, nu uitat. Iertat."},
    {T::Sorry, 0, "Thanks for saying it.", "Mersi că mi-ai spus."},
    // Bye
    {T::Bye, 0, "Bye! I'll be right here.", "Pa! Eu rămân aici."},
    {T::Bye, 1, "See you soon!", "Pe curând!"},
    {T::Bye, 3, "Go on, the world needs you. Come back though.", "Du-te, lumea are nevoie de tine. Dar revino."},
    {T::Bye, 0, "Take care out there.", "Ai grijă de tine."},
    {T::Bye, 2, "Bye… I'll nap until you're back.", "Pa… trag un pui de somn până revii."},
    {T::Bye, 0, "Later! I'll keep your alarms safe.", "Pe mai târziu! Îți păzesc alarmele."},
    // Offline
    {T::Offline, 0, "No internet right now, so that one waits. Alarms, timers and notes work.",
     "N-am internet acum, așa că asta mai așteaptă. Alarmele, minutarele și notițele merg."},
    {T::Offline, 3, "My big brain is offline. My small brain says: try again soon.",
     "Creierul meu mare e offline. Cel mic zice: mai încearcă puțin mai târziu."},
    {T::Offline, 0, "I can't look that up offline. I'll ask once I'm back online.",
     "Nu pot căuta asta offline. Întreb imediat ce revin online."},
};

constexpr int kN = (int)(sizeof(kLines) / sizeof(kLines[0]));

bool phraseIn(const std::string& f, const char* w) {
  const std::string pad = " " + f + " ";
  return pad.find(std::string(" ") + w + " ") != std::string::npos;
}

bool any(const std::string& f, std::initializer_list<const char*> ws) {
  for (const char* w : ws)
    if (phraseIn(f, w)) return true;
  return false;
}

}  // namespace

int lineCount() { return kN; }

int lineCount(LineTopic t, bool ro) {
  int n = 0;
  for (const Line& l : kLines) n += l.t == t && (ro ? l.ro : l.en) ? 1 : 0;
  return n;
}

const char* pickLine(LineTopic t, bool ro, uint32_t seed, int mood) {
  // the lines of this topic that fit the mood (or any mood); a seeded pick among them
  int fit[32], n = 0, all[32], m = 0;
  for (int i = 0; i < kN; ++i) {
    if (kLines[i].t != t) continue;
    if (m < 32) all[m++] = i;
    if ((kLines[i].mood == 0 || kLines[i].mood == mood) && n < 32) fit[n++] = i;
  }
  if (!m) return "";
  uint32_t x = seed * 2654435761u + (uint32_t)t * 40503u;
  x ^= x >> 15;
  const Line& l = n ? kLines[fit[x % (uint32_t)n]] : kLines[all[x % (uint32_t)m]];
  return ro ? l.ro : l.en;
}

bool smallTalk(const std::string& text, bool ro, int hour, uint32_t seed, std::string& say, std::string& face) {
  std::string plain;  // "I'm" -> "Im": the keyword lists are written without apostrophes
  for (size_t i = 0; i < text.size(); ++i) {
    if (text[i] == '\'') continue;
    if (text.compare(i, 3, "\xE2\x80\x99") == 0) {
      i += 2;
      continue;
    }
    plain += text[i];
  }
  const std::string f = SoulMemory::fold(plain);
  if (f.empty()) return false;
  int words = 1;
  for (char c : f) words += c == ' ';
  if (words > 8) return false;  // a real question, not small talk
  LineTopic t;
  if (any(f, {"good morning", "buna dimineata", "neata", "morning"})) t = LineTopic::Morning;
  else if (any(f, {"good night", "noapte buna", "night night", "somn usor", "ma culc", "going to bed"})) t = LineTopic::Night;
  else if (any(f, {"how are you", "how are you doing", "hows it going", "whats up", "ce faci", "ce mai faci", "cum esti",
                   "cum te simti", "how do you feel"}))
    t = LineTopic::HowAreYou;
  else if (any(f, {"thank you", "thanks", "thx", "mersi", "multumesc", "merci", "multam"})) t = LineTopic::Thanks;
  else if (any(f, {"joke", "gluma", "banc", "make me laugh", "fa ma sa rad", "spune o gluma", "spune un banc"})) t = LineTopic::Joke;
  else if (any(f, {"who are you", "what are you", "cine esti", "ce esti", "are you an ai", "esti un ai", "are you human",
                   "esti om", "esti robot", "are you a robot"}))
    t = LineTopic::WhoAreYou;
  else if (any(f, {"i love you", "love you", "te iubesc", "te ador", "i like you", "imi place de tine"})) t = LineTopic::Love;
  else if (any(f, {"im sad", "i am sad", "i feel sad", "i feel bad", "sunt trist", "sunt trista", "ma simt rau",
                   "ma simt trist", "ma simt trista", "im lonely", "i feel lonely", "ma simt singur", "ma simt singura"}))
    t = LineTopic::Sad;
  else if (any(f, {"im bored", "i am bored", "ma plictisesc", "mi e urat", "plictiseala"})) t = LineTopic::Bored;
  else if (any(f, {"youre cute", "you are cute", "youre smart", "you are smart", "good job", "well done", "bravo",
                   "esti dragut", "esti draguta", "esti destept", "esti frumos", "esti scump", "good boy", "good girl"}))
    t = LineTopic::Compliment;
  else if (any(f, {"sorry", "im sorry", "scuze", "scuza ma", "imi pare rau", "iarta ma"})) t = LineTopic::Sorry;
  else if (any(f, {"bye", "goodbye", "see you", "see ya", "pa", "la revedere", "pe curand", "ne vedem"})) t = LineTopic::Bye;
  else if (any(f, {"hi", "hello", "hey", "hei", "salut", "buna", "servus", "ciao", "hola", "yo", "buna ziua", "buna seara"}))
    t = LineTopic::Hello;
  else
    return false;
  const int mood = hour < 0 ? 0 : (hour >= 22 || hour < 6) ? 2 : (seed % 3 == 0 ? 3 : 1);
  if (t == LineTopic::Hello && hour >= 5 && hour < 11 && seed % 2 == 0) t = LineTopic::Morning;
  say = pickLine(t, ro, seed, mood);
  static const char* const kFace[] = {"happy", "happy", "shy", "happy", "love", "excited", "smug",
                                      "love",  "sad",   "wink", "shy",  "happy", "wink",   "thinking"};
  face = kFace[(int)t];
  return !say.empty();
}

}  // namespace suflet
