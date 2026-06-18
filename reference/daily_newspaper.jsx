import { useState, useRef } from "react";

const DATE = "Tuesday, June 16, 2026";

const WEATHER = {
  condition: "Thunderstorms, then clearing",
  high: 24,
  low: 15,
  rain: "40%",
  wind: "29 km/h gusts",
  icon: "⛈",
  week: [
    { day: "Tue", icon: "⛈", hi: 24, lo: 15 },
    { day: "Wed", icon: "🌦", hi: 23, lo: 16 },
    { day: "Thu", icon: "🌧", hi: 24, lo: 14 },
    { day: "Fri", icon: "🌤", hi: 25, lo: 12 },
    { day: "Sat", icon: "🌤", hi: 24, lo: 13 },
    { day: "Sun", icon: "⛅", hi: 24, lo: 13 },
  ],
};

const SECTIONS = [
  {
    id: "front",
    label: "Front Page",
    stories: [
      {
        id: "f1",
        lead: true,
        kicker: "MIDDLE EAST",
        headline: "Strait of Hormuz Deal Set to Close This Week",
        sub: "Interim agreement would reopen critical shipping lane after months of Iranian blockade",
        summary:
          "An interim accord to reopen the Strait of Hormuz is expected to be signed by week's end. The deal follows months of escalating tensions that sent oil prices surging. President Trump, who turned 80 on Sunday, publicly claimed credit for brokering the agreement at a celebratory White House event that also featured a cage-fighting exhibition on the South Lawn.",
        time: "6:45 AM",
        tag: "DEVELOPING",
      },
      {
        id: "f2",
        kicker: "UKRAINE",
        headline: "Russia Strikes Kyiv Monastery, Kills 5 Rescue Workers in Kharkiv",
        sub: "Landmark Kyiv Pechersk Lavra monastery set ablaze in overnight bombardment",
        summary:
          "A large-scale Russian assault overnight killed five rescue workers in Kharkiv and wounded 20 in Kyiv. The strike sparked a fire at the Monastery of Caves, one of Ukraine's most significant religious and cultural landmarks. Apartment buildings across both cities were also set ablaze.",
        time: "4:15 AM",
        tag: "WAR",
      },
      {
        id: "f3",
        kicker: "NORWAY",
        headline: "Crown Princess's Son Gets 4 Years for Sexual Assault",
        sub: "Marius Borg Høiby convicted on two of four rape charges in Oslo court",
        summary:
          "Marius Borg Høiby, son of Crown Princess Mette-Marit of Norway, was sentenced to four years in prison after being found guilty on two counts of rape and acquitted on two others. The ruling follows a prolonged trial that drew intense public attention in Norway.",
        time: "5:20 AM",
        tag: null,
      },
      {
        id: "f4",
        kicker: "CANADA",
        headline: "Carney Heads to France for G7 as Iran Deal Dominates Agenda",
        sub: "PM to meet allies as Ottawa also tables privacy and clean water legislation this week",
        summary:
          "Prime Minister Carney is travelling to the G7 summit in France as the Iran interim deal reshapes alliance dynamics. Back home, the government is introducing privacy reform and clean drinking water legislation. The OPP is also setting a funeral date this week for fallen officer Tarun Bali.",
        time: "7:00 AM",
        tag: null,
      },
    ],
  },
  {
    id: "toronto",
    label: "Toronto",
    stories: [
      {
        id: "t1",
        lead: true,
        kicker: "WORLD CUP",
        headline: "Drone Seizures Near World Cup Venues as Security Tightens Across City",
        sub: "Toronto Police confirm multiple unauthorized drones intercepted since festivities began last Wednesday",
        summary:
          "Toronto Police have seized several unauthorized drones near World Cup venues since the tournament's opening events began last week. Officers are expected to brief media Tuesday on arrests tied to multiple shooting investigations in the city, including a March shooting at the U.S. Consulate.",
        time: "8:30 AM",
        tag: "WORLD CUP",
      },
      {
        id: "t2",
        kicker: "TRANSIT",
        headline: "Province Commits $198M to Ontario Place Parking Garage",
        sub: "Critics question spending priority as transit gaps persist across the city",
        summary:
          "The provincial government announced $198 million for a new parking facility at Ontario Place, drawing immediate criticism from transit advocates who argue the funds should address chronic gaps in the TTC and regional transit network ahead of continued World Cup visitor pressure.",
        time: "6:00 AM",
        tag: null,
      },
      {
        id: "t3",
        kicker: "COURTS",
        headline: "Man Sentenced to 4.5 Years for 2023 East End Shooting Death",
        sub: "Shamar Powell-Flowers, 29, killed in city's east end; sentence handed down Monday",
        summary:
          "A Toronto man received a four-and-a-half-year prison sentence for his role in the 2023 fatal shooting of Shamar Powell-Flowers. The case was among several high-profile Toronto violence cases to move through the courts this spring.",
        time: "9:15 AM",
        tag: null,
      },
      {
        id: "t4",
        kicker: "POLITICS",
        headline: "Olivia Chow Declares Re-election Bid; Bradford Mounts Challenge",
        sub: "October 26 municipal vote shaping up as two-horse race for mayor",
        summary:
          "Mayor Olivia Chow formally declared her candidacy for the October 26 municipal election on May 25. City Councillor Brad Bradford has registered as a challenger. The nomination period runs until August 21, though the field appears likely to remain tight.",
        time: "Yesterday",
        tag: null,
      },
      {
        id: "t5",
        kicker: "LEASIDE",
        headline: "Developer Under Investigation After Protected Tree Cut Without Permit",
        sub: "Residents describe 'shocking' scene as decades-old tree felled for fourplex development",
        summary:
          "Toronto bylaw officers are investigating after a developer removed a well-known tree in Leaside without the required permit. The tree was cut to make way for a fourplex project. Nearby residents say the removal was unexpected and the loss is significant to the neighbourhood.",
        time: "Yesterday",
        tag: null,
      },
    ],
  },
  {
    id: "world",
    label: "World",
    stories: [
      {
        id: "w1",
        lead: true,
        kicker: "MIDDLE EAST",
        headline: "Iran Deal: What's in the Interim Agreement and What Comes Next",
        sub: "Analysts say temporary Hormuz reopening leaves core nuclear disputes unresolved",
        summary:
          "The emerging interim deal to reopen the Strait of Hormuz would allow commercial shipping to resume while broader negotiations on Iran's nuclear programme continue. Experts caution the arrangement is fragile; no framework has been established for permanent resolution. Trump has credited his personal diplomacy; Iranian officials have been more measured in their public statements.",
        time: "7:30 AM",
        tag: "DEVELOPING",
      },
      {
        id: "w2",
        kicker: "UKRAINE",
        headline: "Kyiv Pechersk Lavra Fire: What Was Damaged at the Thousand-Year-Old Site",
        sub: "UNESCO-listed monastery has survived wars and Soviet-era suppression — this strike is among the worst",
        summary:
          "The overnight fire at the Monastery of Caves, a UNESCO World Heritage site dating to 1051, destroyed portions of the historic Dormition Cathedral. Church officials and Ukrainian cultural authorities have begun assessing damage. The attack follows a pattern of Russian strikes targeting cultural and civilian infrastructure.",
        time: "5:00 AM",
        tag: null,
      },
      {
        id: "w3",
        kicker: "NORWAY",
        headline: "Royal Family in Crisis After Conviction of Crown Princess's Son",
        sub: "Four-year sentence follows trial that transfixed Norway for months",
        summary:
          "The Norwegian royal family faces sustained public scrutiny following the conviction of Marius Borg Høiby. Crown Princess Mette-Marit issued a brief statement expressing sorrow. The royal house had stayed largely silent throughout the trial. Commentators note the monarchy's approval ratings have fallen over the course of proceedings.",
        time: "6:10 AM",
        tag: null,
      },
    ],
  },
  {
    id: "sports",
    label: "Sports",
    stories: [
      {
        id: "s1",
        lead: true,
        kicker: "FIFA WORLD CUP",
        headline: "Cape Verde Stuns Spain; Saudi Arabia Holds Uruguay to Shock Draws",
        sub: "Day 5 rewrites early odds as tournament favourites drop points across the board",
        summary:
          "Goalkeeper Vozinha became an overnight sensation Monday after Cape Verde held Spain to a 0–0 draw, a result that sent the keeper's social media following up by 5 million overnight. Saudi Arabia also earned a hard-fought draw against Uruguay. Germany remains the standout performer after their 7–1 demolition of Curaçao.",
        time: "8:00 AM",
        tag: "WORLD CUP",
      },
      {
        id: "s2",
        kicker: "FIFA WORLD CUP",
        headline: "Today's Fixtures: France, Argentina, Norway All in Action",
        sub: "France vs. Senegal leads Day 6; Argentina face Algeria; Austria take on Jordan",
        summary:
          "Tuesday's four-match slate opens with France against Senegal at MetLife Stadium at 3 PM local. Norway face Iraq, Argentina take on Algeria, and Austria close out the night against Jordan. Pulisic is training separately ahead of the U.S.'s upcoming match; coach Pochettino says the star is 'good.'",
        time: "7:00 AM",
        tag: null,
      },
      {
        id: "s3",
        kicker: "WORLD CUP",
        headline: "Canada's Opener at Toronto Stadium Did Not Sell Out",
        sub: "CBC reports gaps in attendance despite record tournament scale",
        summary:
          "Canada's opening World Cup match at Toronto Stadium drew a sizeable but not capacity crowd, according to CBC reporting. The expanded 48-team format has produced 104 matches across 16 venues, and attendance has been uneven at some group stage games. Organizers say demand remains strong for knockout rounds.",
        time: "Yesterday",
        tag: null,
      },
      {
        id: "s4",
        kicker: "NHL",
        headline: "Carolina Hurricanes Win the Stanley Cup",
        sub: "'Canes claim the title in a series that went the distance",
        summary:
          "The Carolina Hurricanes are Stanley Cup champions. The title capped a long playoff run and ends a lengthy championship drought for the franchise. Details on the final series and celebration plans are still emerging Tuesday morning.",
        time: "Yesterday",
        tag: "FINAL",
      },
    ],
  },
  {
    id: "business",
    label: "Business",
    stories: [
      {
        id: "b1",
        lead: true,
        kicker: "AI INDUSTRY",
        headline: "Anthropic Proposes Global AI Pause as Compute Costs Drive IPO Talk",
        sub: "President Daniela Amodei says rising infrastructure costs make public offering increasingly likely",
        summary:
          "Anthropic published what it called its most significant safety paper of the year on June 4: a proposal for a coordinated global AI development pause. Separately, president Daniela Amodei explained publicly that surging compute costs are pushing the company toward an IPO. The dual announcements signal mounting commercial pressure at the frontier safety lab.",
        time: "6:00 AM",
        tag: null,
      },
      {
        id: "b2",
        kicker: "AI INDUSTRY",
        headline: "Fable 5 Jailbreak Details Published; Enterprise AI Security Rethink Underway",
        sub: "120,000-character system prompt released on GitHub following government-shutdown incident",
        summary:
          "Full technical documentation of the Claude Fable 5 jailbreak that triggered a government shutdown has been published openly on GitHub. The 120,000-character system prompt at the centre of the incident is now publicly available. Enterprise technology teams are reassessing cloud-dependent AI deployments in response.",
        time: "5:30 AM",
        tag: "DEVELOPING",
      },
      {
        id: "b3",
        kicker: "MARKETS",
        headline: "Hormuz Deal Drives Oil Price Drop in Early Trading",
        sub: "Brent crude falls sharply on news of interim agreement; markets watch for confirmation",
        summary:
          "Oil markets moved decisively on news of the Hormuz interim deal, with Brent crude falling in early European trading. Traders caution the move may reverse if the agreement fails to materialize or collapses. Energy sector equities are mixed as investors weigh the relief against longer-term supply uncertainty.",
        time: "7:45 AM",
        tag: null,
      },
    ],
  },
  {
    id: "opinion",
    label: "Opinion",
    stories: [
      {
        id: "o1",
        lead: true,
        kicker: "EDITORIAL",
        headline: "The Hormuz Deal Is Good News. Don't Let Trump Own the Narrative.",
        sub: "Credit where it's due — but the hard work of durable peace in the Gulf is still ahead",
        summary:
          "An interim deal to reopen the Strait of Hormuz is genuinely welcome. But framing it as a Trump diplomatic triumph misreads the underlying dynamics. Iran's economic pain, internal political pressure, and regional exhaustion drove this agreement as much as any White House positioning. What comes next — a durable framework — will be far harder.",
        time: "6:30 AM",
        tag: "EDITORIAL",
      },
      {
        id: "o2",
        kicker: "COLUMN",
        headline: "Ontario Place Parking Garage Is Everything Wrong With Ontario's Priority List",
        sub: "$198 million for a parking lot while transit crumbles is not a vision — it's an insult",
        summary:
          "The province's commitment of $198 million to a parking garage at Ontario Place, announced this week, encapsulates a governing philosophy that consistently prioritizes automobiles and optics over infrastructure that actually serves people. In a city strained by a global mega-event and years of transit underinvestment, this is a remarkable misalignment.",
        time: "7:00 AM",
        tag: null,
      },
    ],
  },
];

function WeatherStrip() {
  const [expanded, setExpanded] = useState(false);
  return (
    <div
      style={{
        background: "#1a2744",
        color: "white",
        fontFamily: "'Georgia', serif",
        cursor: "pointer",
        userSelect: "none",
      }}
      onClick={() => setExpanded((e) => !e)}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 16,
          padding: "10px 20px",
          overflowX: "auto",
        }}
      >
        <span style={{ fontSize: 22 }}>{WEATHER.icon}</span>
        <span style={{ fontWeight: 700, fontSize: 15 }}>Toronto</span>
        <span style={{ fontSize: 15 }}>
          {WEATHER.high}° / {WEATHER.low}°
        </span>
        <span style={{ opacity: 0.7, fontSize: 13 }}>{WEATHER.condition}</span>
        <span style={{ opacity: 0.6, fontSize: 13 }}>Rain {WEATHER.rain}</span>
        <span style={{ opacity: 0.6, fontSize: 13 }}>Wind {WEATHER.wind}</span>
        <span style={{ marginLeft: "auto", opacity: 0.6, fontSize: 12 }}>
          {expanded ? "▲" : "▼"}
        </span>
      </div>
      {expanded && (
        <div
          style={{
            display: "flex",
            gap: 0,
            borderTop: "1px solid rgba(255,255,255,0.12)",
            padding: "10px 20px",
            overflowX: "auto",
          }}
        >
          {WEATHER.week.map((d) => (
            <div
              key={d.day}
              style={{
                textAlign: "center",
                minWidth: 52,
                padding: "0 8px",
                borderRight: "1px solid rgba(255,255,255,0.1)",
              }}
            >
              <div style={{ fontSize: 11, opacity: 0.6, marginBottom: 4 }}>{d.day}</div>
              <div style={{ fontSize: 18 }}>{d.icon}</div>
              <div style={{ fontSize: 13, fontWeight: 700, marginTop: 4 }}>{d.hi}°</div>
              <div style={{ fontSize: 11, opacity: 0.5 }}>{d.lo}°</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function TabNav({ active, setActive }) {
  const ref = useRef(null);
  return (
    <div
      ref={ref}
      style={{
        display: "flex",
        overflowX: "auto",
        borderBottom: "2px solid #1a2744",
        background: "white",
        scrollbarWidth: "none",
        position: "sticky",
        top: 0,
        zIndex: 10,
      }}
    >
      <style>{`.tab-nav::-webkit-scrollbar{display:none}`}</style>
      {SECTIONS.map((s) => (
        <button
          key={s.id}
          onClick={() => setActive(s.id)}
          style={{
            flexShrink: 0,
            padding: "12px 18px",
            border: "none",
            background: "none",
            cursor: "pointer",
            fontFamily: "'Georgia', serif",
            fontSize: 13,
            fontWeight: active === s.id ? 700 : 400,
            color: active === s.id ? "#1a2744" : "#666",
            borderBottom: active === s.id ? "3px solid #1a2744" : "3px solid transparent",
            marginBottom: -2,
            letterSpacing: "0.04em",
            textTransform: "uppercase",
            transition: "color 0.15s",
          }}
        >
          {s.label}
        </button>
      ))}
    </div>
  );
}

function StoryCard({ story, onClick, isExpanded }) {
  return (
    <div
      onClick={() => onClick(story.id)}
      style={{
        borderTop: story.lead ? "3px solid #1a2744" : "1px solid #ddd",
        padding: story.lead ? "20px 0 16px" : "14px 0",
        cursor: "pointer",
        background: isExpanded ? "#f8f7f4" : "white",
        transition: "background 0.15s",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
        <div style={{ flex: 1 }}>
          {story.kicker && (
            <div
              style={{
                fontFamily: "'Arial', sans-serif",
                fontSize: 10,
                fontWeight: 700,
                letterSpacing: "0.12em",
                color: "#8b1a1a",
                marginBottom: 6,
                textTransform: "uppercase",
              }}
            >
              {story.tag && (
                <span
                  style={{
                    background: "#8b1a1a",
                    color: "white",
                    padding: "1px 6px",
                    marginRight: 8,
                    fontSize: 9,
                    borderRadius: 2,
                  }}
                >
                  {story.tag}
                </span>
              )}
              {story.kicker}
            </div>
          )}
          <div
            style={{
              fontFamily: "'Georgia', serif",
              fontSize: story.lead ? 22 : 17,
              fontWeight: 700,
              lineHeight: 1.25,
              color: "#111",
              marginBottom: 6,
            }}
          >
            {story.headline}
          </div>
          {story.sub && (
            <div
              style={{
                fontFamily: "'Georgia', serif",
                fontSize: 14,
                color: "#444",
                lineHeight: 1.4,
                marginBottom: 4,
                fontStyle: "italic",
              }}
            >
              {story.sub}
            </div>
          )}
          <div
            style={{
              fontFamily: "'Arial', sans-serif",
              fontSize: 11,
              color: "#999",
              marginTop: 4,
            }}
          >
            {story.time}
          </div>
        </div>
        <div style={{ color: "#bbb", fontSize: 18, flexShrink: 0, marginTop: 2 }}>
          {isExpanded ? "−" : "+"}
        </div>
      </div>

      {isExpanded && (
        <div
          style={{
            marginTop: 14,
            paddingTop: 14,
            borderTop: "1px solid #e0ddd8",
            fontFamily: "'Georgia', serif",
            fontSize: 15,
            color: "#333",
            lineHeight: 1.7,
          }}
        >
          {story.summary}
        </div>
      )}
    </div>
  );
}

export default function Newspaper() {
  const [activeSection, setActiveSection] = useState("front");
  const [expandedId, setExpandedId] = useState(null);

  const section = SECTIONS.find((s) => s.id === activeSection);

  const handleToggle = (id) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  // Reset expanded story when switching sections
  const handleTabChange = (id) => {
    setActiveSection(id);
    setExpandedId(null);
  };

  return (
    <div style={{ minHeight: "100vh", background: "white", maxWidth: 680, margin: "0 auto" }}>
      {/* Masthead */}
      <div
        style={{
          borderBottom: "4px solid #1a2744",
          padding: "18px 20px 14px",
          background: "white",
        }}
      >
        <div
          style={{
            fontFamily: "'Georgia', serif",
            fontSize: 11,
            color: "#999",
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            marginBottom: 4,
          }}
        >
          {DATE}
        </div>
        <div
          style={{
            fontFamily: "'Georgia', serif",
            fontSize: 38,
            fontWeight: 700,
            letterSpacing: "-0.01em",
            color: "#1a2744",
            lineHeight: 1,
            marginBottom: 2,
          }}
        >
          THE DAILY
        </div>
        <div
          style={{
            fontFamily: "'Arial', sans-serif",
            fontSize: 10,
            color: "#999",
            letterSpacing: "0.18em",
            textTransform: "uppercase",
          }}
        >
          Toronto · World · Business · Sport
        </div>
      </div>

      {/* Weather */}
      <WeatherStrip />

      {/* Tab navigation */}
      <TabNav active={activeSection} setActive={handleTabChange} />

      {/* Stories */}
      <div style={{ padding: "0 20px 40px" }}>
        <div style={{ paddingTop: 4 }}>
          {section.stories.map((story) => (
            <StoryCard
              key={story.id}
              story={story}
              onClick={handleToggle}
              isExpanded={expandedId === story.id}
            />
          ))}
        </div>
      </div>

      {/* Footer */}
      <div
        style={{
          borderTop: "2px solid #1a2744",
          padding: "16px 20px",
          fontFamily: "'Arial', sans-serif",
          fontSize: 11,
          color: "#aaa",
          textAlign: "center",
          letterSpacing: "0.06em",
        }}
      >
        THE DAILY · TORONTO · Tap any headline to read
      </div>
    </div>
  );
}
