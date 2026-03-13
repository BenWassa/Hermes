export const SAMPLE_BRIEFING = {
  id: '2026-03-09',
  date: 'March 9, 2026',
  today_in_60_seconds: [
    { icon: '🛢️', headline: 'Oil volatility spikes' },
    { icon: '📉', headline: 'Markets reprice inflation risk' },
    { icon: '🤖', headline: 'China accelerates AI push' },
    { icon: '⚖️', headline: 'Pentagon-AI tension emerges' }
  ],
  major_developments: [
    {
      id: 'dev-1',
      domain: 'ENERGY',
      region: 'MIDDLE EAST',
      impact: 'CRITICAL',
      icon: '🛢️',
      headline: 'Oil Shock and War Risk',
      executive_summary:
        'Oil surged nearly 30% before reversing as geopolitical tensions escalated.',
      key_facts: [
        'Brent briefly crossed $100',
        'De-escalation signals caused reversal',
        'Market volatility spread to equities'
      ],
      sources: ['Reuters', 'Bloomberg', 'FT']
    },
    {
      id: 'dev-2',
      domain: 'TECH',
      region: 'GLOBAL',
      impact: 'HIGH',
      icon: '🤖',
      headline: 'Sovereign AI Compute Race',
      executive_summary:
        'Nations are increasingly treating high-tier compute clusters as critical national infrastructure.',
      key_facts: [
        'New export controls proposed on advanced chips',
        'Middle Eastern sovereign wealth funds redirecting capital to domestic datacenters',
        'Talent acquisition becomes state-level priority'
      ],
      sources: ['WSJ', 'TechCrunch', 'State Dept']
    }
  ],
  timeline_context: {
    title: 'Middle East Escalation Sequence',
    events: [
      {
        date: 'MARCH 12',
        headline: 'Shipping disruption reports intensify',
        details:
          'Commercial routing desks flagged new insurance premiums and rerouting pressure across Gulf-linked cargo flows.'
      },
      {
        date: 'MARCH 11',
        headline: 'Energy desks widen hedging activity',
        details:
          'Options flows accelerated as traders repriced tail-risk around supply interruption and retaliatory action.'
      },
      {
        date: 'MARCH 10',
        headline: 'Back-channel diplomacy stalls',
        details:
          'Regional intermediaries reported reduced confidence that maritime security talks would stabilize near-term flows.'
      }
    ]
  },
  risk_matrix: {
    title: '24-Hour Threat Map',
    risks: [
      {
        id: 'risk-1',
        label: 'Hormuz transit shock',
        probability: 0.78,
        impact: 0.95,
        details: 'Would reprice energy, inflation, and shipping risk simultaneously.'
      },
      {
        id: 'risk-2',
        label: 'Oil spike mean reversion',
        probability: 0.64,
        impact: 0.34,
        details: 'Fast diplomatic signaling could unwind the most extreme front-end pricing.'
      },
      {
        id: 'risk-3',
        label: 'ECB hawkish spillover',
        probability: 0.41,
        impact: 0.71,
        details: 'A sustained energy move could harden developed-market rate expectations.'
      }
    ]
  },
  macro_indicators: [
    {
      id: 'ind-01',
      title: 'Brent Crude',
      metric: '7-DAY VOLATILITY',
      currentValue: '$98.40',
      trendValue: '+17.1%',
      trendDirection: 'up',
      data: [84, 86, 87, 89, 93, 96, 98.4],
      details:
        'Risk premium remains embedded as energy desks model further shipping disruption and retaliatory risk.'
    },
    {
      id: 'ind-02',
      title: 'Gold',
      metric: 'SAFE-HAVEN FLOW',
      currentValue: '$2,214',
      trendValue: '+3.1%',
      trendDirection: 'up',
      data: [2148, 2151, 2160, 2178, 2190, 2205, 2214],
      details:
        'Capital rotated into defensive stores of value as geopolitical uncertainty bled into broader macro positioning.'
    }
  ],
  analyst_consensus: {
    consensus: [
      'Energy shock could delay rate cuts globally.',
      'Defense and compute spending will remain non-cyclical.'
    ],
    friction: [
      'Some analysts believe the oil spike will reverse rapidly if conflict cools.',
      "Disagreement on whether the ECB will follow the Fed's hawkish tilt."
    ]
  },
  strategic_context: [
    'Energy shocks are reintroducing geopolitics into macroeconomic expectations.',
    'Persistent oil elevation could force central banks to maintain tighter policy despite slowing growth.',
    'The intersection of AI infrastructure demands and energy scarcity is becoming the defining macroeconomic theme of the decade.'
  ],
  watchlist:
    'Strait of Hormuz shipping flows over the next 48 hours may determine whether energy volatility persists and bleeds into core inflation metrics.'
};
